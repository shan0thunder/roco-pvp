"""
JSON数据存储模块
===============
提供数据持久化：写入JSON文件、读取、备份、合并。
"""

import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
from copy import deepcopy

from ..config import OUTPUT_CONFIG

logger = logging.getLogger(__name__)


class JsonStorage:
    """
    JSON文件存储器。

    特点：
    - 美观格式化输出，方便人工查阅
    - 自动备份旧数据
    - 数据合并而非覆盖
    - 支持导出版本快照
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or OUTPUT_CONFIG["data_dir"])
        self.backup_dir = self.data_dir / "backup"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保数据目录存在"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _get_filepath(self, filename: str) -> Path:
        """获取文件完整路径"""
        return self.data_dir / filename

    # ================================================================
    # 写入操作
    # ================================================================

    def save(
        self,
        data: Any,
        filename: str,
        backup: bool = True,
        pretty: bool = True,
    ) -> str:
        """
        保存数据到JSON文件。

        Args:
            data: 要保存的数据
            filename: 文件名（如 'pets.json'）
            backup: 是否先备份旧文件
            pretty: 是否美化格式

        Returns:
            保存的文件路径
        """
        filepath = self._get_filepath(filename)

        # 备份旧文件
        if backup and filepath.exists():
            self._backup(filepath)

        # 写入新数据
        with open(filepath, "w", encoding="utf-8") as f:
            kwargs = {
                "ensure_ascii": False,
                "indent": 2 if pretty else None,
                "separators": (",", ": ") if pretty else (",", ":"),
            }
            json.dump(data, f, **kwargs)

        logger.info(f"数据已保存: {filepath} ({self._size_str(filepath)})")
        return str(filepath)

    def _backup(self, filepath: Path):
        """备份旧文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{filepath.stem}_{timestamp}{filepath.suffix}"
        try:
            import shutil
            shutil.copy2(filepath, backup_path)
            logger.debug(f"已备份旧数据: {backup_path}")
        except Exception as e:
            logger.warning(f"备份失败: {e}")

    # ================================================================
    # 读取操作
    # ================================================================

    def load(self, filename: str) -> Optional[Any]:
        """
        从JSON文件加载数据。

        Args:
            filename: 文件名

        Returns:
            解析后的数据，文件不存在时返回 None
        """
        filepath = self._get_filepath(filename)
        if not filepath.exists():
            logger.warning(f"文件不存在: {filepath}")
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 [{filepath}]: {e}")
            return None
        except Exception as e:
            logger.error(f"读取失败 [{filepath}]: {e}")
            return None

    # ================================================================
    # 合并操作
    # ================================================================

    def merge_and_save(
        self,
        new_data: List[Dict],
        filename: str,
        key_field: str = "name",
        merge_strategy: str = "update",
    ) -> int:
        """
        合并新数据到已有数据集。

        Args:
            new_data: 新数据列表
            filename: 目标文件名
            key_field: 用于去重的关键字段
            merge_strategy: 'update'=更新现有, 'append'=仅追加不重复的

        Returns:
            新增/更新的记录数
        """
        existing = self.load(filename) or []

        # 构建已有数据的索引
        existing_map = {}
        for item in existing:
            key = item.get(key_field)
            if key:
                existing_map[key] = item

        changes = 0
        for item in new_data:
            key = item.get(key_field)
            if not key:
                continue

            if key in existing_map:
                if merge_strategy == "update":
                    # 更新现有记录
                    existing_map[key].update(item)
                    changes += 1
                # 'append'策略下已存在则不处理
            else:
                existing_map[key] = item
                changes += 1

        # 转回列表
        merged = list(existing_map.values())
        self.save(merged, filename)

        logger.info(f"合并完成: {changes} 条变更（共 {len(merged)} 条记录）")
        return changes

    # ================================================================
    # 快照管理
    # ================================================================

    def create_snapshot(self, tag: str) -> Dict[str, str]:
        """
        创建当前数据的快照（备份所有文件）。

        Args:
            tag: 快照标签，如 'before_update_v1'

        Returns:
            快照文件路径字典 {filename: snapshot_path}
        """
        snapshot_dir = self.backup_dir / f"snapshot_{tag}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        import shutil
        snapshots = {}
        for filepath in self.data_dir.glob("*.json"):
            if filepath.name == "backup":
                continue
            dest = snapshot_dir / filepath.name
            shutil.copy2(filepath, dest)
            snapshots[filepath.name] = str(dest)

        logger.info(f"快照已创建: {snapshot_dir} ({len(snapshots)} 文件)")
        return snapshots

    # ================================================================
    # 导出数据摘要
    # ================================================================

    def summary(self, filename: str) -> Dict:
        """
        生成数据集摘要信息。

        Returns:
            {
                "file": filename,
                "records": N,
                "size_kb": N.N,
                "last_updated": "YYYY-MM-DD HH:MM:SS",
            }
        """
        data = self.load(filename)
        filepath = self._get_filepath(filename)

        return {
            "file": filename,
            "records": len(data) if isinstance(data, list) else 1,
            "size_kb": round(filepath.stat().st_size / 1024, 2) if filepath.exists() else 0,
            "last_updated": (
                datetime.fromtimestamp(filepath.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                if filepath.exists() else None
            ),
        }

    def _size_str(self, filepath: Path) -> str:
        """文件大小可读字符串"""
        size = filepath.stat().st_size
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        else:
            return f"{size / 1024 / 1024:.1f}MB"
