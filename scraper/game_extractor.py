#!/usr/bin/env python3
"""
洛克王国世界 - 游戏安装文件数据提取器
======================================
从游戏安装目录中扫描并提取精灵、技能、属性等数据，
整理为产品数据格式 (product_data.json)。

使用方式:
  python scraper/game_extractor.py <游戏目录路径> [选项]

选项:
  --dry-run        只扫描不输出，预览发现的文件
  --output PATH    指定输出路径 (默认 data/product/product_data.json)
  --merge PATH     与现有数据合并 (以新数据为准)
  --verbose        详细日志

工作流程:
  1. 递归扫描目标目录
  2. 按文件扩展名和内容签名识别数据文件
  3. 尝试用对应解析器提取结构化数据
  4. 映射到产品数据格式
  5. 输出为 product_data.json

注意: 对于 Unity 项目可能需要安装 UnityPy:
  pip install UnityPy
"""

import os
import sys
import json
import re
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Set
from datetime import datetime
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# 1. 文件扫描器
# ============================================================

class FileScanner:
    """递归扫描游戏目录，按特征分类文件"""

    # 已知的游戏数据文件扩展名 (按可信度排序)
    DATA_EXTENSIONS = {
        '.json': 'json',
        '.bytes': 'binary_json',   # Unity TextAsset 常以 .bytes 结尾但内容是 JSON
        '.txt': 'text',
        '.csv': 'csv',
        '.xml': 'xml',
        '.lua': 'lua',
        '.ab': 'assetbundle',
        '.unity3d': 'assetbundle',
        '.dat': 'binary',
        '.bin': 'binary',
    }

    # 内容签名检测
    MAGIC_SIGNATURES = [
        (b'{', 'json_likely'),
        (b'[', 'array_likely'),
        (b'return ', 'lua_likely'),
        (b'-- ', 'lua_comment'),
        (b'UnityFS', 'unity_fs'),
        (b'PK\x03\x04', 'zip_archive'),  # Unity 资源
    ]

    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        if not self.root.exists():
            raise FileNotFoundError(f"目录不存在: {root_dir}")

    def scan(self) -> Dict[str, List[Path]]:
        """扫描并分类所有数据文件"""
        result = defaultdict(list)

        for filepath in self.root.rglob('*'):
            if not filepath.is_file():
                continue

            # 按扩展名分类
            ext = filepath.suffix.lower()
            if ext in self.DATA_EXTENSIONS:
                ftype = self.DATA_EXTENSIONS[ext]
                result[ftype].append(filepath)
                continue

            # 无扩展名文件: 尝试内容签名
            try:
                with open(filepath, 'rb') as f:
                    header = f.read(16)
                    for magic, ftype in self.MAGIC_SIGNATURES:
                        if header.startswith(magic):
                            result[ftype].append(filepath)
                            break
            except (IOError, OSError):
                pass

            # 小文件（< 1MB）无扩展名也列为候选
            if ext == '' and filepath.stat().st_size < 1024 * 1024:
                result['unknown_small'].append(filepath)

        return result


# ============================================================
# 2. 文件解析器
# ============================================================

class FileParser:
    """多后端文件解析器"""

    @staticmethod
    def try_parse(filepath: Path) -> Optional[Any]:
        """尝试用多种方式解析文件，返回结构化数据或 None"""
        ext = filepath.suffix.lower()

        # JSON 系
        if ext in ('.json', '.bytes'):
            result = FileParser._parse_json(filepath)
            if result is not None:
                return result

        # CSV
        if ext == '.csv':
            result = FileParser._parse_csv(filepath)
            if result is not None:
                return result

        # XML
        if ext == '.xml':
            result = FileParser._parse_xml(filepath)
            if result is not None:
                return result

        # Lua (简单解析赋值语句)
        if ext == '.lua':
            result = FileParser._parse_lua_simple(filepath)
            if result is not None:
                return result

        # 纯文本 (尝试解析 key=value 或 行数据)
        if ext in ('.txt', '.dat', '.bin'):
            result = FileParser._parse_text(filepath)
            if result is not None:
                return result

        # 尝试 Unity AssetBundle
        if ext in ('.ab', '.unity3d') or FileParser._check_unity_fs(filepath):
            result = FileParser._parse_unity_asset(filepath)
            if result is not None:
                return result

        return None

    @staticmethod
    def _parse_json(filepath: Path) -> Optional[Any]:
        """尝试 JSON 解析，支持带 BOM 和不完整文件"""
        try:
            raw = filepath.read_bytes()
            # 去掉可能的 BOM
            if raw[:3] == b'\xef\xbb\xbf':
                raw = raw[3:]
            # 尝试 UTF-8
            text = raw.decode('utf-8', errors='replace')
            return json.loads(text)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        return None

    @staticmethod
    def _parse_csv(filepath: Path) -> Optional[List[Dict]]:
        """解析 CSV 文件为字典列表"""
        import csv
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = [row for row in reader]
                return rows if rows else None
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_xml(filepath: Path) -> Optional[Dict]:
        """简单 XML 解析"""
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(filepath)
            root = tree.getroot()
            return FileParser._xml_to_dict(root)
        except Exception:
            return None

    @staticmethod
    def _xml_to_dict(element) -> Dict:
        result = {}
        for child in element:
            if len(child) == 0:
                result[child.tag] = child.text or ''
            else:
                result[child.tag] = FileParser._xml_to_dict(child)
        return result

    @staticmethod
    def _parse_lua_simple(filepath: Path) -> Optional[Dict]:
        """
        简单 Lua 解析: 提取 return {...} 的顶级表。
        只能处理简单的 key=value 和 嵌套表，不执行 Lua 代码。
        """
        try:
            text = filepath.read_text('utf-8', errors='replace')
            # 查找 return { ... }
            m = re.search(r'return\s*(\{)', text, re.DOTALL)
            if not m:
                return None
            # 用正则简单提取键值对
            data = {}
            for kv in re.finditer(r'(\w+)\s*=\s*("[^"]*"|\'[^\']*\'|true|false|\d+(?:\.\d+)?)', text):
                key = kv.group(1)
                val = kv.group(2)
                if val.startswith('"') or val.startswith("'"):
                    val = val[1:-1]
                elif val in ('true', 'false'):
                    val = val == 'true'
                else:
                    try:
                        val = int(val) if '.' not in val else float(val)
                    except ValueError:
                        pass
                data[key] = val
            return data if data else None
        except Exception:
            return None

    @staticmethod
    def _parse_text(filepath: Path) -> Optional[Any]:
        """按行解析文本文件，尝试 JSON 或 key=value"""
        try:
            text = filepath.read_text('utf-8', errors='replace')
            # 尝试逐行 JSON (每个对象一行)
            lines = [l.strip() for l in text.split('\n') if l.strip() and not l.strip().startswith(('#', '//', '--'))]
            if not lines:
                return None
            # 如果第一行是 {，尝试整个文件作为 JSON
            if lines[0].startswith('{'):
                return json.loads('\n'.join(lines))
            # 尝试每行一个 JSON 对象
            objects = []
            for line in lines:
                if line.startswith('{') or line.startswith('['):
                    try:
                        objects.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            if objects:
                return objects
            # 尝试 key=value 格式
            kv = {}
            for line in lines:
                if '=' in line:
                    k, v = line.split('=', 1)
                    kv[k.strip()] = v.strip()
            return kv if kv else None
        except Exception:
            return None

    @staticmethod
    def _check_unity_fs(filepath: Path) -> bool:
        """检查文件是否为 UnityFS 格式"""
        try:
            with open(filepath, 'rb') as f:
                return f.read(7) == b'UnityFS'
        except Exception:
            return False

    @staticmethod
    def _parse_unity_asset(filepath: Path) -> Optional[Dict]:
        """使用 UnityPy 解析 Unity AssetBundle"""
        try:
            import UnityPy
            env = UnityPy.load(str(filepath))
            result = {}
            for obj in env.objects:
                if obj.type.name == 'TextAsset':
                    data = obj.read()
                    text = data.text
                    if text:
                        try:
                            parsed = json.loads(text)
                            name = data.name or obj.path_id
                            result[str(name)] = parsed
                        except json.JSONDecodeError:
                            result[data.name or str(obj.path_id)] = text
                elif obj.type.name == 'MonoBehaviour':
                    try:
                        tree = obj.read_typetree()
                        result[str(obj.path_id)] = tree
                    except Exception:
                        pass
            return result if result else None
        except ImportError:
            logger.warning("UnityPy 未安装 (pip install UnityPy)，跳过 Unity 文件: %s", filepath.name)
            return None
        except Exception as e:
            logger.debug("Unity 解析失败 %s: %s", filepath.name, e)
            return None


# ============================================================
# 3. 数据映射器
# ============================================================

class DataMapper:
    """
    将原始游戏数据映射到产品数据格式。

    由于不同游戏版本的数据结构不同，映射规则可能需要
    根据实际文件内容调整。这里提供可自定义的映射管线。
    """

    # 已知可能的字段名映射 (游戏字段 → 产品字段)
    PET_NAME_KEYS = {'name', 'Name', 'NAME', 'pet_name', 'PetName', '宠物名', '名称', '名字', '精灵名'}
    PET_ELEMENT_KEYS = {'element', 'Element', 'elem', '属性', '属性1', 'attr', 'type', 'Type', 'pet_type'}
    PET_ELEMENT2_KEYS = {'element2', 'Element2', '属性2', 'attr2'}
    PET_HP_KEYS = {'hp', 'HP', 'Hp', '生命', '体力', '精力'}
    PET_ATK_KEYS = {'attack', 'Attack', '物攻', '物理攻击'}
    PET_DEF_KEYS = {'defense', 'Defense', '物防', '物理防御'}
    PET_MATK_KEYS = {'magic_attack', 'sp_attack', 'spatk', '魔攻', '魔法攻击'}
    PET_MDEF_KEYS = {'magic_defense', 'sp_defense', 'spdef', '魔防', '魔法防御'}
    PET_SPD_KEYS = {'speed', 'Speed', '速度'}
    PET_RARITY_KEYS = {'rarity', 'Rarity', '稀有度', '品质', 'grade', 'Grade'}
    PET_DESC_KEYS = {'description', 'desc', 'Description', '描述', '介绍', 'intro'}
    PET_SKILL_KEYS = {'skills', 'Skills', 'skill_list', '技能', '技能列表', 'skillset'}
    SKILL_NAME_KEYS = {'name', 'Name', 'skill_name', '技能名', '技能名称', '名称'}
    SKILL_ELEMENT_KEYS = {'element', 'Element', '属性', 'type', 'Type'}
    SKILL_CATEGORY_KEYS = {'category', 'Category', '分类', 'type', '技能类型', 'skill_type'}
    SKILL_COST_KEYS = {'cost', 'Cost', 'pp', 'PP', '能耗', '消耗'}
    SKILL_POWER_KEYS = {'power', 'Power', '威力', '伤害'}
    SKILL_EFFECT_KEYS = {'effect', 'Effect', 'desc', 'description', '描述', '效果', '描述'}
    SKILL_SOURCE_KEYS = {'source', 'Source', '来源', '获取', '解锁'}

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw = raw_data

    def extract_pets(self) -> List[Dict]:
        """从原始数据中提取精灵列表"""
        pets_data = self._find_list_data(self.raw, [
            'pets', 'Pets', 'pet_list', 'PetList', '精灵', 'spirit',
            'spirits', 'pet_data', 'PetData', 'character', 'Character',
            'monster', 'Monster', 'pokemon', 'role', 'Role',
            '对象', '角色', 'unit', 'Unit',
        ])
        if not pets_data:
            return []

        result = []
        for item in pets_data:
            if not isinstance(item, dict):
                continue
            pet = self._map_pet(item)
            if pet and pet.get('name'):
                result.append(pet)
        return result

    def extract_skills(self) -> List[Dict]:
        """从原始数据中提取技能列表"""
        skills_data = self._find_list_data(self.raw, [
            'skills', 'Skills', 'skill_list', 'SkillList', '技能',
            'skill_data', 'SkillData', 'ability', 'Ability',
            'spell', 'Spell', 'skill_config',
        ])
        if not skills_data:
            return []

        result = []
        for item in skills_data:
            if not isinstance(item, dict):
                continue
            skill = self._map_skill(item)
            if skill and skill.get('name'):
                result.append(skill)
        return result

    def extract_elements(self) -> List[str]:
        """提取属性列表"""
        elements = self._find_value(self.raw, [
            'elements', 'Elements', 'types', 'Types', '属性', '属性列表',
            'element_list', 'attr_list',
        ])
        if isinstance(elements, list):
            return elements
        return []

    def extract_type_chart(self) -> Dict[str, Dict[str, float]]:
        """提取属性克制表"""
        chart = self._find_value(self.raw, [
            'type_chart', 'TypeChart', 'type_effect', 'damage_multiplier',
            'effectiveness', '克制', '克制表', 'damage_relation',
        ])
        if isinstance(chart, dict):
            return chart
        return {}

    def _find_list_data(self, data: Any, keys: List[str]) -> List:
        """在嵌套 dict 中找第一个匹配的列表数据"""
        if isinstance(data, list):
            return data

        if not isinstance(data, dict):
            return []

        # 优先匹配指定 key
        for key in keys:
            val = data.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                # 可能是 { "1": {...}, "2": {...} } 格式
                inner = list(val.values())
                if inner and isinstance(inner[0], dict):
                    return inner

        # 递归查找
        for val in data.values():
            if isinstance(val, (dict, list)):
                result = self._find_list_data(val, keys)
                if result:
                    return result
        return []

    def _find_value(self, data: Any, keys: List[str]) -> Optional[Any]:
        """在嵌套 dict 中找第一个匹配的字段值"""
        if not isinstance(data, dict):
            return None
        for key in keys:
            if key in data:
                return data[key]
        for val in data.values():
            if isinstance(val, dict):
                result = self._find_value(val, keys)
                if result is not None:
                    return result
        return None

    def _get_field(self, item: Dict, key_sets: List[Set[str]]) -> Optional[Any]:
        """从 item 中用多组 key 取第一个存在的字段"""
        for key_set in key_sets:
            for key in key_set:
                if key in item:
                    return item[key]
        return None

    def _map_pet(self, item: Dict) -> Optional[Dict]:
        """映射单个精灵"""
        name = self._get_field(item, [self.PET_NAME_KEYS])
        if not name:
            return None

        elements = self._get_field(item, [self.PET_ELEMENT_KEYS])
        if isinstance(elements, str):
            elements = [elements]
        elif not isinstance(elements, list):
            elements = []

        elem2 = self._get_field(item, [self.PET_ELEMENT2_KEYS])
        if elem2:
            if isinstance(elem2, str) and elem2 not in elements:
                elements.append(elem2)
            elif isinstance(elem2, list):
                elements.extend(e for e in elem2 if e not in elements)

        stats = {}
        hp = self._get_field(item, [self.PET_HP_KEYS])
        if hp is not None: stats['hp'] = int(hp)
        atk = self._get_field(item, [self.PET_ATK_KEYS])
        if atk is not None: stats['attack'] = int(atk)
        defense = self._get_field(item, [self.PET_DEF_KEYS])
        if defense is not None: stats['defense'] = int(defense)
        matk = self._get_field(item, [self.PET_MATK_KEYS])
        if matk is not None: stats['magic_attack'] = int(matk)
        mdef = self._get_field(item, [self.PET_MDEF_KEYS])
        if mdef is not None: stats['magic_defense'] = int(mdef)
        spd = self._get_field(item, [self.PET_SPD_KEYS])
        if spd is not None: stats['speed'] = int(spd)
        if stats:
            stats['total'] = sum(v for v in stats.values())
        if not stats:
            stats = None

        rarity = self._get_field(item, [self.PET_RARITY_KEYS])
        if rarity is not None:
            rarity = str(rarity)

        # 尝试提取技能
        skills = []
        raw_skills = self._get_field(item, [self.PET_SKILL_KEYS])
        if isinstance(raw_skills, list):
            for sk in raw_skills:
                if isinstance(sk, dict):
                    mapped = self._map_skill(sk)
                    if mapped:
                        skills.append(mapped)
                elif isinstance(sk, (int, str)):
                    # 可能是技能 ID，留待后续关联
                    pass

        desc = self._get_field(item, [self.PET_DESC_KEYS])

        return {
            'name': str(name),
            'element': elements,
            'stats': stats,
            'rarity': rarity,
            'skills': skills,
            'skills_count': len(skills),
            'description': desc or '',
            'source': 'game_files',
        }

    def _map_skill(self, item: Dict) -> Optional[Dict]:
        """映射单个技能"""
        name = self._get_field(item, [self.SKILL_NAME_KEYS])
        if not name:
            return None

        element = self._get_field(item, [self.SKILL_ELEMENT_KEYS])
        if element and not isinstance(element, str):
            element = str(element)

        category = self._get_field(item, [self.SKILL_CATEGORY_KEYS])
        if category and not isinstance(category, str):
            category = str(category)

        cost = self._get_field(item, [self.SKILL_COST_KEYS])
        if cost is not None:
            cost = int(cost)

        power = self._get_field(item, [self.SKILL_POWER_KEYS])
        if power is not None:
            power = int(power)

        effect = self._get_field(item, [self.SKILL_EFFECT_KEYS])
        if effect is not None:
            effect = str(effect)

        source = self._get_field(item, [self.SKILL_SOURCE_KEYS])
        if source is not None:
            source = str(source)

        return {
            'name': str(name),
            'element': element or '',
            'category': category or '',
            'cost': cost,
            'power': power,
            'effect': effect or '',
            'source': source or '',
        }


# ============================================================
# 4. 主提取管线
# ============================================================

class GameExtractor:
    """游戏文件数据提取器"""

    def __init__(self, game_dir: str):
        self.game_dir = game_dir
        self.scanner = FileScanner(game_dir)
        self.parser = FileParser()

    def extract(self) -> Dict[str, Any]:
        """
        完整提取管线:
        1. 扫描文件
        2. 逐个解析
        3. 映射到产品格式
        4. 合并所有结果
        """
        logger.info("扫描游戏目录: %s", self.game_dir)
        files = self.scanner.scan()

        total = sum(len(v) for v in files.values())
        logger.info("发现 %d 个候选文件", total)
        for ftype, flist in files.items():
            if flist:
                logger.info("  %s: %d 个", ftype, len(flist))

        # 优先解析 JSON 类文件 (最高效)
        all_data = {}
        priority_types = ['json', 'binary_json', 'json_likely', 'array_likely', 'csv', 'lua']

        for ftype in priority_types:
            for filepath in files.get(ftype, []):
                data = self.parser.try_parse(filepath)
                if data:
                    key = filepath.stem.lower()
                    all_data[f"{key}_{filepath.suffix}"] = data
                    # 也尝试直接映射
                    if isinstance(data, (dict, list)):
                        all_data[f"mapped_{key}"] = data
                    logger.info("  ✅ %s", filepath.relative_to(self.game_dir))

        # 再解析其他类型
        remaining = [t for t in files if t not in priority_types]
        for ftype in remaining:
            for filepath in files.get(ftype, []):
                data = self.parser.try_parse(filepath)
                if data:
                    key = filepath.stem.lower()
                    all_data[f"{key}_{filepath.suffix}"] = data
                    logger.info("  ✅ %s", filepath.relative_to(self.game_dir))

        logger.info("成功解析 %d 个文件", len(all_data))

        # 用 DataMapper 映射
        mapper = DataMapper(all_data)
        result = {}

        pets = mapper.extract_pets()
        if pets:
            result['pets'] = pets
            logger.info("提取精灵: %d 只", len(pets))

        skills = mapper.extract_skills()
        if skills:
            result['skills'] = skills
            logger.info("提取技能: %d 个", len(skills))

        elements = mapper.extract_elements()
        if elements:
            result['type_elements'] = elements
            logger.info("提取属性: %d 种", len(elements))

        type_chart = mapper.extract_type_chart()
        if type_chart:
            result['type_chart'] = type_chart
            logger.info("提取克制表: %d 条", len(type_chart))

        # 如果没有显式元素列表，从精灵数据中收集
        if not elements and result.get('pets'):
            all_elems = set()
            for p in result['pets']:
                for e in (p.get('element') or []):
                    all_elems.add(e)
            if all_elems:
                result['type_elements'] = sorted(all_elems)

        result['_meta'] = {
            'extracted_at': datetime.now().isoformat(),
            'source': 'game_files',
            'game_dir': self.game_dir,
            'files_parsed': len(all_data),
            'pets_count': len(result.get('pets', [])),
            'skills_count': len(result.get('skills', [])),
        }

        return result

    def dry_run(self) -> Dict[str, List[str]]:
        """预览模式: 只列出文件不解析"""
        files = self.scanner.scan()
        result = {}
        for ftype, flist in sorted(files.items()):
            if flist:
                result[ftype] = [str(f.relative_to(self.game_dir)) for f in flist]
        return result


# ============================================================
# 5. 输出
# ============================================================

def save_product_data(data: Dict[str, Any], output_path: str):
    """保存为产品数据格式"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    logger.info("数据已输出: %s (%d KB)", path, len(json.dumps(data)) / 1024)


def merge_with_existing(new_data: Dict[str, Any], existing_path: str) -> Dict[str, Any]:
    """与现有数据合并 (以新数据为准)"""
    existing_path = Path(existing_path)
    if not existing_path.exists():
        logger.info("无现有数据可合并")
        return new_data

    try:
        existing = json.loads(existing_path.read_text(encoding='utf-8'))
        logger.info("读取现有数据: %s", existing_path)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("读取现有数据失败: %s", e)
        return new_data

    # 逐字段合并
    for key in ('pets', 'skills', 'type_elements', 'type_chart', 'pvp_teams'):
        if key in new_data and new_data[key]:
            existing[key] = new_data[key]
            logger.info("合并 %s: %d 条 (新数据)", key, len(new_data[key]))
        elif key in existing:
            logger.info("保留 %s: %d 条 (现有)", key, len(existing.get(key, [])))

    # 更新元数据
    if '_meta' not in existing:
        existing['_meta'] = {}
    existing['_meta']['merged_at'] = datetime.now().isoformat()
    existing['_meta']['pets_count'] = len(existing.get('pets', []))
    existing['_meta']['skills_count'] = len(existing.get('skills', []))

    return existing


# ============================================================
# 6. CLI
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='洛克王国世界 - 游戏安装文件数据提取器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scraper/game_extractor.py "D:/RocoKingdom/游戏目录"
  python scraper/game_extractor.py "D:/RocoKingdom/游戏目录" --dry-run
  python scraper/game_extractor.py "D:/RocoKingdom/游戏目录" --output my_data.json
  python scraper/game_extractor.py "D:/RocoKingdom/游戏目录" --merge data/product/product_data.json
        """,
    )

    parser.add_argument('game_dir', help='游戏安装目录路径')
    parser.add_argument('--dry-run', action='store_true', help='仅预览文件，不提取')
    parser.add_argument('--output', default='data/product/product_data.json', help='输出路径')
    parser.add_argument('--merge', metavar='PATH', help='与现有数据文件合并')
    parser.add_argument('--verbose', action='store_true', help='详细日志')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        extractor = GameExtractor(args.game_dir)
    except FileNotFoundError as e:
        logger.error(e)
        sys.exit(1)

    if args.dry_run:
        logger.info("=== 预览模式 ===")
        files = extractor.dry_run()
        for ftype, flist in files.items():
            print(f"\n[{ftype}] ({len(flist)} 个)")
            for f in flist[:20]:
                print(f"  {f}")
            if len(flist) > 20:
                print(f"  ... 还有 {len(flist) - 20} 个")
        return

    # 提取
    logger.info("=== 开始提取 ===")
    data = extractor.extract()

    if not data.get('pets') and not data.get('skills'):
        logger.warning("未提取到有效数据")
        logger.info("尝试 --dry-run 查看可解析的文件列表")
        sys.exit(1)

    # 合并
    if args.merge:
        data = merge_with_new(data, args.merge)

    # 输出
    save_product_data(data, args.output)
    logger.info("完成!")


if __name__ == '__main__':
    main()
