#!/usr/bin/env python3
"""
Unreal Engine 4/5 PAK 文件浏览器 & 数据提取器
=============================================
用于从 洛克王国：世界 的 PAK 文件中提取数据文件。
"""

import os
import sys
import struct
import json
import zlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, BinaryIO, Iterator

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# UE4 PAK 文件格式解析
# ============================================================

# UE4 PAK 文件头部
def parse_pak_header(f: BinaryIO) -> Optional[dict]:
    """解析 PAK 文件头部"""
    magic = f.read(4)
    if len(magic) < 4:
        return None
    magic_val = struct.unpack('<I', magic)[0]

    # UE4 PAK magic: 0x5A6F12E1
    if magic_val not in (0x5A6F12E1, 0x5A6F12E2):
        logger.debug("非 PAK 文件 (magic: 0x%08X)", magic_val)
        return None

    version = struct.unpack('<I', f.read(4))[0]
    sub_version = struct.unpack('<Q', f.read(8))[0]

    # 文件索引偏移和大小
    index_offset = struct.unpack('<Q', f.read(8))[0]
    index_size = struct.unpack('<Q', f.read(8))[0]
    index_hash = f.read(20)  # SHA1

    # 是否加密
    encrypted = magic_val == 0x5A6F12E2

    # 压缩块大小
    block_size = struct.unpack('<I', f.read(4))[0]

    return {
        'magic': magic_val,
        'version': version,
        'sub_version': sub_version,
        'index_offset': index_offset,
        'index_size': index_size,
        'encrypted': encrypted,
        'block_size': block_size,
    }


def read_fname(f: BinaryIO) -> str:
    """读取 UE4 FString (长度前缀的 UTF-16)"""
    length = struct.unpack('<I', f.read(4))[0]
    if length == 0:
        return ''
    # 负数 = UTF-16, 正数 = ANSI
    if length < 0:
        # UTF-16
        length = -length
        raw = f.read(length * 2)
        return raw.decode('utf-16-le', errors='replace').rstrip('\0')
    else:
        raw = f.read(length)
        return raw.decode('utf-8', errors='replace').rstrip('\0')


def read_pak_entry(f: BinaryIO) -> Optional[dict]:
    """读取一个 PAK 文件条目"""
    name = read_fname(f)
    if not name:
        return None

    offset = struct.unpack('<Q', f.read(8))[0]
    size = struct.unpack('<Q', f.read(8))[0]
    uncompressed_size = struct.unpack('<Q', f.read(8))[0]

    # 压缩块信息 (UE4 内部压缩)
    compress_method = struct.unpack('<I', f.read(4))[0]

    # 压缩块列表
    num_blocks = struct.unpack('<I', f.read(4))[0]
    blocks = []
    for _ in range(num_blocks):
        block_start = struct.unpack('<Q', f.read(8))[0]
        block_end = struct.unpack('<Q', f.read(8))[0]
        blocks.append((block_start, block_end))

    # 标志位
    flags = struct.unpack('<I', f.read(4))[0]

    return {
        'name': name,
        'offset': offset,
        'size': size,
        'uncompressed_size': uncompressed_size,
        'compress_method': compress_method,
        'blocks': blocks,
        'flags': flags,
        'is_compressed': compress_method != 0,
    }


def list_pak(pak_path: str, max_items: int = 0) -> List[dict]:
    """列出 PAK 文件中的所有文件"""
    entries = []
    with open(pak_path, 'rb') as f:
        header = parse_pak_header(f)
        if not header:
            return entries

        logger.info("PAK: %s (v%d, %d 文件条目)",
                     Path(pak_path).name, header['version'], header.get('file_count', '?'))

        # 跳转到索引区
        f.seek(header['index_offset'])

        # 索引区头
        magic2 = struct.unpack('<I', f.read(4))[0]
        version = struct.unpack('<I', f.read(4))[0]
        # 文件条目数
        entry_count = struct.unpack('<I', f.read(4))[0]

        logger.info("  文件数: %d", entry_count)

        for i in range(entry_count):
            entry = read_pak_entry(f)
            if entry:
                entries.append(entry)
                if max_items and len(entries) >= max_items:
                    break

    return entries


# ============================================================
# 文件类型识别
# ============================================================

def classify_entry(name: str) -> str:
    """根据文件名判断文件类型"""
    lower = name.lower()
    ext = Path(lower).suffix

    if ext in ('.json',): return 'json'
    if ext in ('.csv',): return 'csv'
    if ext in ('.lua', '.luac'): return 'lua'
    if ext in ('.xml',): return 'xml'
    if ext in ('.txt', '.ini', '.cfg'): return 'text'
    if ext in ('.uasset', '.uexp', '.ubulk'): return 'uasset'
    if ext in ('.umap',): return 'umap'
    if ext in ('.png', '.jpg', '.jpeg', '.tga', '.dds'): return 'image'
    if ext in ('.wav', '.ogg', '.mp3', '.flac'): return 'audio'
    if ext in ('.fbx', '.psk', '.pskx'): return 'model'

    # 根据路径关键词判断
    if '/datatable/' in lower or '/data/' in lower:
        return 'likely_data'
    if '/config/' in lower:
        return 'likely_config'
    if '/localization/' in lower or '/loc/' in lower:
        return 'localization'
    if '/blueprint/' in lower or '/bp/' in lower:
        return 'blueprint'

    return 'other'


# ============================================================
# UE4 资产读取器 (支持 TextAsset / DataTable)
# ============================================================

def extract_asset_text(f: BinaryIO, size: int) -> Optional[str]:
    """
    从 UE4 资产文件中提取可读文本。
    UE4 的 TextAsset/DataTable 内部包含 JSON 数据。
    """
    raw = f.read(size)
    if not raw:
        return None

    # 尝试找到 JSON 起始位置（跳过 UE4 二进制头）
    # UE4 的 uasset 文件：先有 FObjectExport 头，然后是数据
    # 对于 TextAsset 和 DataTable，数据通常在文件末尾附近

    # 直接从后往前找 JSON 结构
    text = raw.decode('utf-8', errors='replace')

    # 清理 null 字符
    text = text.replace('\0', '').strip()

    # 尝试找 JSON 对象
    brace_start = text.find('{')
    bracket_start = text.find('[')

    start = -1
    if brace_start >= 0 and bracket_start >= 0:
        start = min(brace_start, bracket_start)
    elif brace_start >= 0:
        start = brace_start
    elif bracket_start >= 0:
        start = bracket_start

    if start >= 0:
        # 尝试找到匹配的结束
        json_text = text[start:]
        # 找最后一个 } 或 ]
        end = max(json_text.rfind('}'), json_text.rfind(']'))
        if end >= 0:
            json_text = json_text[:end + 1]
            # 验证 JSON
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError:
                pass

    # 如果不是 JSON，返回可读文本（去掉不可见字符）
    readable = ''.join(c if c.isprintable() or c in '\n\r\t' else ' ' for c in text)
    readable = ' '.join(readable.split())
    if len(readable) > 50:
        return readable[:5000]

    return None


def extract_data_from_pak(pak_path: str, output_dir: str = 'data/extracted',
                          type_filter: str = None) -> Dict[str, List[str]]:
    """
    从 PAK 文件中提取数据文件到磁盘

    Args:
        pak_path: PAK 文件路径
        output_dir: 输出目录
        type_filter: 文件类型筛选 ('json', 'csv', 'lua', 'text', etc.)

    Returns:
        Dict[type, List[paths]] 提取的文件路径
    """
    entries = list_pak(pak_path)
    extracted = {}
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for entry in entries:
        ftype = classify_entry(entry['name'])
        if type_filter and ftype != type_filter:
            continue

        # 只提取文本类文件
        if ftype not in ('json', 'csv', 'lua', 'text', 'likely_data', 'likely_config', 'localization'):
            continue

        # 构建输出路径
        rel = entry['name'].lstrip('/').lstrip('\\')
        outpath = out / rel
        outpath.parent.mkdir(parents=True, exist_ok=True)

        # 大小限制 (只提取 < 50MB 的文件)
        total_size = entry['uncompressed_size'] or entry['size']
        if total_size > 50 * 1024 * 1024:
            continue

        if ftype not in extracted:
            extracted[ftype] = []
        extracted[ftype].append(rel)

    return extracted


# ============================================================
# 快速搜索 — 在 PAK 中文本搜索关键词
# ============================================================

def search_in_pak(pak_path: str, keywords: List[str], max_results: int = 20) -> List[dict]:
    """
    在 PAK 文件条目名中搜索关键词，找到可能包含数据的文件。

    Args:
        pak_path: PAK 文件路径
        keywords: 搜索关键词 (如 ['pet', 'skill', 'sprite', '精灵'])
        max_results: 最大返回数

    Returns:
        List[dict] 匹配的文件条目
    """
    entries = list_pak(pak_path)
    results = []

    for entry in entries:
        lower_name = entry['name'].lower()
        for kw in keywords:
            if kw.lower() in lower_name:
                entry['match_type'] = classify_entry(entry['name'])
                results.append(entry)
                break

    results.sort(key=lambda e: e.get('uncompressed_size', 0), reverse=True)
    return results[:max_results]


# ============================================================
# 批量扫描所有 PAK
# ============================================================

def scan_all_paks(pak_dir: str, keywords: List[str] = None) -> Dict[str, List[dict]]:
    """
    扫描目录下所有 PAK 文件，搜索数据文件。

    Args:
        pak_dir: PAK 文件目录
        keywords: 可选，搜索关键词

    Returns:
        Dict[pak_file, List[entries]]
    """
    pak_dir = Path(pak_dir)
    result = {}

    for pak_file in sorted(pak_dir.glob('*.pak')):
        # 跳过补丁文件（_0_P, _P 等），先扫描基础包
        if '_P.pak' in pak_file.name and pak_file.stat().st_size < 1024 * 1024:
            continue

        size_mb = pak_file.stat().st_size / (1024 * 1024)
        if size_mb > 5000:  # 跳过 > 5GB 的包（全是纹理/模型）
            continue

        logger.info("扫描: %s (%.1f MB)", pak_file.name, size_mb)

        try:
            entries = list_pak(str(pak_file))
        except Exception as e:
            logger.warning("  跳过: %s", e)
            continue

        if keywords:
            matched = []
            for entry in entries:
                lower = entry['name'].lower()
                if any(kw.lower() in lower for kw in keywords):
                    entry['pak'] = pak_file.name
                    matched.append(entry)
            if matched:
                result[pak_file.name] = matched
        else:
            # 列出数据文件
            data_files = []
            for entry in entries:
                ftype = classify_entry(entry['name'])
                if ftype in ('json', 'csv', 'lua', 'text', 'likely_data', 'likely_config'):
                    entry['pak'] = pak_file.name
                    data_files.append(entry)
            if data_files:
                result[pak_file.name] = data_files

    return result


# ============================================================
# CLI
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='UE4 PAK 文件浏览器 & 数据提取器')
    parser.add_argument('path', help='PAK 文件路径或包含 PAK 的目录')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有文件')
    parser.add_argument('--search', '-s', nargs='+', default=[], help='搜索关键词')
    parser.add_argument('--max', '-n', type=int, default=30, help='最大显示数')
    parser.add_argument('--extract', '-e', help='提取匹配文件到目录')

    args = parser.parse_args()

    path = Path(args.path)

    if path.is_dir():
        # 扫描目录下所有 PAK
        logger.info("扫描目录: %s", path)
        result = scan_all_paks(str(path), keywords=args.search or
                               ['pet', 'skill', 'sprite', '精灵', '技能', 'DataTable', 'Table'])

        total = sum(len(v) for v in result.values())
        if args.search:
            logger.info("找到 %d 个匹配文件（关键词: %s）", total, args.search)
        else:
            logger.info("找到 %d 个数据文件", total)

        for pak_name, entries in sorted(result.items()):
            print(f"\n[{pak_name}] ({len(entries)} 个)")
            for e in entries[:args.max]:
                size = e.get('uncompressed_size', e.get('size', 0))
                size_str = f"{size / 1024:.0f}K" if size > 1024 else f"{size}B"
                ftype = classify_entry(e['name'])
                print(f"  [{ftype:12s}] {size_str:>8s}  {e['name'][:120]}")
            if len(entries) > args.max:
                print(f"  ... 还有 {len(entries) - args.max} 个")

    elif path.is_file():
        # 分析单个 PAK
        logger.info("分析: %s", path)
        entries = list_pak(str(path), max_items=0)
        logger.info("共 %d 个文件", len(entries))

        if args.search:
            matched = search_in_pak(str(path), args.search, args.max)
            print(f"\n匹配 \"{' '.join(args.search)}\": {len(matched)} 个")
            for e in matched:
                size = e.get('uncompressed_size', e.get('size', 0))
                size_str = f"{size / 1024:.0f}K" if size > 1024 else f"{size}B"
                print(f"  {size_str:>8s}  {e['name']}")
        elif args.list:
            for e in entries[:args.max]:
                ftype = classify_entry(e['name'])
                size = e.get('uncompressed_size', e.get('size', 0))
                size_str = f"{size / 1024:.0f}K" if size > 1024 else f"{size}B"
                print(f"  [{ftype:12s}] {size_str:>8s}  {e['name']}")
            if len(entries) > args.max:
                print(f"  ... 还有 {len(entries) - args.max} 个")


if __name__ == '__main__':
    main()
