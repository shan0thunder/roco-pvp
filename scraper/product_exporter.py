"""
产品数据集成层
=============
将原始爬虫数据转化为产品可直接消费的标准格式。

输出特点：
1. 编码统一为 UTF-8 （无乱码）
2. 每个精灵技能字段完整（含威力/能耗/分类/效果）
3. 数据模型与PRD中定义的模型一致
4. 支持增量更新和差异比对
"""

import json
import logging
import re
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

from .config import OUTPUT_CONFIG
from .storage.json_storage import JsonStorage

logger = logging.getLogger(__name__)


# ================================================================
# 产品数据格式标准化
# ================================================================

def normalize_skill(raw: Dict) -> Dict:
    """
    标准化技能数据，确保字段完整。

    输入可能来自渲染爬虫（全字段）或种子数据（部分字段），
    输出保证包含产品需要的所有字段。

    Args:
        raw: 原始技能数据

    Returns:
        标准化技能数据
    """
    return {
        "name": raw.get("name", ""),
        "element": raw.get("element") or "",
        "category": raw.get("category") or "",
        "cost": raw.get("cost") if raw.get("cost") is not None else (
            raw.get("能耗") or raw.get("pp")),
        "power": raw.get("power") if raw.get("power") is not None else (
            raw.get("威力")),
        "effect": raw.get("effect") or raw.get("description") or "",
        "source": raw.get("source") or raw.get("来源") or raw.get("解锁条件") or "",
        "source_type": raw.get("source_type") or raw.get("sourceType", "默认"),
    }


def normalize_stats(raw: Dict) -> Dict:
    """标准化种族值数据"""
    return {
        "hp": raw.get("hp") or raw.get("生命") or 0,
        "attack": raw.get("attack") or raw.get("物攻") or 0,
        "defense": raw.get("defense") or raw.get("物防") or 0,
        "magic_attack": raw.get("magic_attack") or raw.get("魔攻") or 0,
        "magic_defense": raw.get("magic_defense") or raw.get("魔防") or 0,
        "speed": raw.get("speed") or raw.get("速度") or 0,
        "total": raw.get("total") or 0,
    }


def _clean_rarity_from_sources(raw_rarity: Optional[str], seed_rarity: Optional[str] = None) -> str:
    """
    从多个来源清理和合并稀有度。

    优先级:
    1. 直接在 raw 中识别出已知关键词（传说/稀有/普通）
    2. 种子数据中的稀有度（回退）
    3. 空字符串
    """
    value = raw_rarity or ""

    # 尝试从原始文本中识别关键词
    for k in ["传说", "稀有", "普通", "精良", "史诗", "神话"]:
        if k in value:
            return k

    # 回退到种子数据
    if seed_rarity:
        return seed_rarity

    return ""


def _build_seed_rarity_map() -> Dict[str, str]:
    """从种子数据构建稀有度映射"""
    from .seed_data import get_seed_pets
    return {p["name"]: p.get("rarity", "") for p in get_seed_pets()}


def normalize_pet(raw: Dict) -> Dict:
    """
    标准化精灵数据。

    产品格式：
    {
        "name": "白金独角兽",
        "pet_id": null,
        "element": ["光"],
        "rarity": "传说",
        "stats": {"hp": 99, "attack": 61, ...},
        "skills": [
            {"name": "许愿星", "element": "普通", "category": "魔攻",
             "cost": 3, "power": 110, "effect": "...", "source": "Lv.1"}
        ],
        "description": "...",
        "evolutions": [],
        "obtain_method": null
    }
    """
    stats_raw = raw.get("stats") or {}
    skills_raw = raw.get("skills") or []

    return {
        "name": raw.get("name", ""),
        "pet_id": raw.get("pet_id") or raw.get("id"),
        "element": raw.get("element") or raw.get("elements") or [],
        "image": raw.get("image") or None,
        "stats": normalize_stats(stats_raw) if stats_raw else None,
        "skills": [normalize_skill(s) for s in skills_raw] if skills_raw else [],
        "skills_count": len(skills_raw),
        "description": raw.get("description") or raw.get("desc") or "",
        "evolutions": raw.get("evolution") or raw.get("evolutions") or [],
        "evolution_chain": raw.get("evolution_chain") or [],
        "obtain_method": raw.get("obtain_method") or raw.get("获取方式") or "",
        "source_url": raw.get("source_url") or "",
        "updated_at": datetime.now().isoformat(),
    }


def normalize_team(raw: Dict) -> Dict:
    """标准化阵容数据"""
    return {
        "name": raw.get("name", ""),
        "rank": raw.get("rank", "T?"),
        "core_pets": raw.get("core_pets") or [],
        "flex_pets": raw.get("flex_pets") or [],
        "description": raw.get("description") or "",
        "mechanics": raw.get("mechanics") or "",
        "pros": raw.get("pros") or [],
        "cons": raw.get("cons") or [],
        "counters": raw.get("counters") or [],
        "target_users": raw.get("target_users") or "",
        "season": raw.get("season") or "",
    }


# ================================================================
# 产品数据导出
# ================================================================

def _build_skill_index_inplace(pets: List[Dict], product_data: Dict) -> None:
    """从精灵嵌入的技能中构建完整技能索引"""
    from collections import defaultdict
    skill_map = {}
    skill_to_pets = defaultdict(list)

    for pet in pets:
        pname = pet.get("name", "")
        for s in pet.get("skills", []):
            sname = s.get("name", "")
            if not sname:
                continue
            if sname not in skill_map:
                skill_map[sname] = {
                    "name": sname,
                    "element": s.get("element") or "",
                    "category": s.get("category") or "",
                    "cost": s.get("cost"),
                    "power": s.get("power"),
                    "effect": s.get("effect", ""),
                }
            skill_to_pets[sname].append(pname)

    by_element = defaultdict(list)
    by_category = defaultdict(list)
    for sname, s in skill_map.items():
        by_element[s.get("element") or "无"].append(sname)
        by_category[s.get("category") or "无"].append(sname)

    # 注入到 product_data
    product_data["index"]["skills_by_element"] = dict(by_element)
    product_data["index"]["skills_by_category"] = dict(by_category)
    product_data["index"]["skill_to_pets"] = dict(skill_to_pets)
    product_data["index"]["skill_details"] = skill_map
    product_data["_meta"]["total_records"]["skills_total_unique"] = len(skill_map)

def export_product_data(
    output_file: str = "product_data.json",
    pretty: bool = True,
) -> str:
    """
    导出产品可直接使用的完整数据集。

    数据流：
    1. 从 storage 加载原始数据
    2. 标准化每个记录
    3. 输出为产品标准格式

    Args:
        output_file: 输出文件名（默认 product_data.json）
        pretty: 是否美化格式

    Returns:
        输出文件路径
    """
    storage = JsonStorage()

    # 加载原始数据
    raw_pets = storage.load(OUTPUT_CONFIG["pets_file"]) or []
    raw_skills = storage.load(OUTPUT_CONFIG["skills_file"]) or []
    raw_teams = storage.load(OUTPUT_CONFIG["teams_file"]) or []
    raw_type_chart = storage.load(OUTPUT_CONFIG["type_chart_file"]) or {}
    raw_rising = storage.load("rising_pets.json") or []

    # 构建种子稀有度映射（用于回退）
    seed_rarity_map = _build_seed_rarity_map()

    # 标准化（注入种子稀有度作为回退）
    def _normalize_with_seed(p):
        seed_rarity = seed_rarity_map.get(p.get("name", ""))
        p["_seed_rarity"] = seed_rarity
        return normalize_pet(p)

    pets = [_normalize_with_seed(p) for p in raw_pets]
    skills = [normalize_skill(s) for s in raw_skills]
    teams = [normalize_team(t) for t in raw_teams]

    # 产品输出格式
    product_data = {
        # 元信息
        "_meta": {
            "game": "洛克王国世界",
            "version": "1.0.0",
            "exported_at": datetime.now().isoformat(),
            "data_sources": {
                "pets": "seed_data + BiliWiki渲染",
                "skills": "seed_data + BiliWiki渲染",
                "teams": "社区攻略交叉验证",
                "type_chart": "游戏内数据整理",
            },
            "total_records": {
                "pets": len(pets),
                "skills": len(skills),
                "teams": len(teams),
                "skills_total_unique": len(set(s["name"] for s in skills)),
            },
        },

        # 业务数据
        "pets": pets,
        "skills": skills,
        "pvp_teams": teams,
        "type_chart": raw_type_chart.get("chart") or raw_type_chart,
        "type_elements": raw_type_chart.get("elements") or [],
        "rising_pets": raw_rising,

        # 索引（按属性分类，方便产品快速查找）
        "index": {
            "pets_by_element": _build_element_index(pets),
            "teams_by_rank": _build_rank_index(teams),
            "teams_by_pet": _build_pet_index(teams),
        },
    }

    # 自动构建技能索引（从精灵嵌入技能中提取）
    _build_skill_index_inplace(pets, product_data)

    # 保存产品文件
    product_dir = Path(OUTPUT_CONFIG["data_dir"]) / "product"
    product_dir.mkdir(parents=True, exist_ok=True)

    output_path = product_dir / output_file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(product_data, f, ensure_ascii=False, indent=2 if pretty else None)

    file_size = output_path.stat().st_size
    logger.info(
        f"产品数据已导出: {output_path} "
        f"({len(pets)} pets, {len(skills)} skills, {len(teams)} teams, "
        f"{file_size/1024:.1f} KB)"
    )

    return str(output_path)


def _build_element_index(pets: List[Dict]) -> Dict[str, List[str]]:
    """按属性构建精灵索引"""
    index = {}
    for p in pets:
        elements = p.get("element", []) or []
        for e in elements:
            if e not in index:
                index[e] = []
            index[e].append(p["name"])
    return index


def _build_rank_index(teams: List[Dict]) -> Dict[str, List[str]]:
    """按梯队构建阵容索引"""
    index = {}
    for t in teams:
        rank = t.get("rank", "T?")
        if rank not in index:
            index[rank] = []
        index[rank].append(t["name"])
    return index


def _build_pet_index(teams: List[Dict]) -> Dict[str, List[Dict]]:
    """按精灵名构建阵容索引（快速查某个精灵在哪些阵容中）"""
    index = {}
    for t in teams:
        all_pets = t.get("core_pets", []) + t.get("flex_pets", [])
        for pet_name in all_pets:
            if pet_name not in index:
                index[pet_name] = []
            index[pet_name].append({
                "team": t["name"],
                "rank": t.get("rank", "T?"),
                "role": "核心" if pet_name in (t.get("core_pets") or []) else "摇摆",
            })
    return index


# ================================================================
# 增量更新
# ================================================================

class ProductUpdater:
    """
    产品数据更新器。

    管理数据版本，支持增量更新和变更通知。
    """

    def __init__(self):
        self.storage = JsonStorage()

    def check_updates(self) -> Dict:
        """
        检查自上次导出后的数据变更。

        Returns:
            {"has_updates": true/false, "changes": [...]}
        """
        current_pets = self.storage.load(OUTPUT_CONFIG["pets_file"]) or []
        current_teams = self.storage.load(OUTPUT_CONFIG["teams_file"]) or []
        current_skills = self.storage.load(OUTPUT_CONFIG["skills_file"]) or []

        # 读取上次导出版本
        version_file = Path(OUTPUT_CONFIG["data_dir"]) / "product" / ".version.json"
        if version_file.exists():
            with open(version_file, "r", encoding="utf-8") as f:
                last_version = json.load(f)
        else:
            last_version = {}

        # 比较差异
        changes = []
        prev_pets_count = last_version.get("pets_count", 0)
        prev_teams_count = last_version.get("teams_count", 0)
        prev_skills_count = last_version.get("skills_count", 0)

        if len(current_pets) != prev_pets_count:
            changes.append({
                "type": "pets",
                "before": prev_pets_count,
                "after": len(current_pets),
                "delta": len(current_pets) - prev_pets_count,
            })
        if len(current_teams) != prev_teams_count:
            changes.append({
                "type": "teams",
                "before": prev_teams_count,
                "after": len(current_teams),
                "delta": len(current_teams) - prev_teams_count,
            })
        if len(current_skills) != prev_skills_count:
            changes.append({
                "type": "skills",
                "before": prev_skills_count,
                "after": len(current_skills),
                "delta": len(current_skills) - prev_skills_count,
            })

        has_updates = len(changes) > 0

        return {
            "has_updates": has_updates,
            "changes": changes,
            "current": {
                "pets": len(current_pets),
                "teams": len(current_teams),
                "skills": len(current_skills),
            },
        }

    def export_with_version(self) -> str:
        """
        导出并记录版本号。

        每次导出时记录数据状态，下次可据此检测变更。
        """
        output_path = export_product_data()

        # 记录版本
        version_dir = Path(OUTPUT_CONFIG["data_dir"]) / "product"
        version_dir.mkdir(parents=True, exist_ok=True)

        current_pets = self.storage.load(OUTPUT_CONFIG["pets_file"]) or []
        current_teams = self.storage.load(OUTPUT_CONFIG["teams_file"]) or []
        current_skills = self.storage.load(OUTPUT_CONFIG["skills_file"]) or []

        version_info = {
            "exported_at": datetime.now().isoformat(),
            "pets_count": len(current_pets),
            "teams_count": len(current_teams),
            "skills_count": len(current_skills),
            "file": output_path,
        }

        with open(version_dir / ".version.json", "w", encoding="utf-8") as f:
            json.dump(version_info, f, ensure_ascii=False, indent=2)

        return output_path


# ================================================================
# CLI 输出展示
# ================================================================

def print_product_summary(output_path: str, verbose: bool = False):
    """打印产品数据摘要"""
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("_meta", {})
    stats = meta.get("total_records", {})
    indexes = data.get("index", {})

    print(f"\n{'='*50}")
    print(f"  产品数据导出完成")
    print(f"{'='*50}")
    print(f"  文件: {output_path}")
    print(f"  大小: {Path(output_path).stat().st_size / 1024:.1f} KB")
    print(f"  时间: {meta.get('exported_at', '')[:19]}")
    print()
    print(f"  [精灵] {stats.get('pets', 0)} 只")
    print(f"  [技能] {stats.get('skills', 0)} 个 ({stats.get('skills_total_unique', 0)} 唯一)")
    print(f"  [阵容] {stats.get('teams', 0)} 套")
    print()

    if verbose:
        print(f"  [属性索引] {len(indexes.get('pets_by_element', {}))} 个属性:")
        for elem, names in sorted(indexes.get("pets_by_element", {}).items()):
            print(f"    {elem}: {len(names)} 只", end="")
            if len(names) <= 5:
                print(f" ({', '.join(names)})")
            else:
                print(f" ({', '.join(names[:3])}...等{len(names)}只)")

        print(f"\n  [阵容梯队]")
        for rank, teams in sorted(
            indexes.get("teams_by_rank", {}).items(), reverse=True
        ):
            print(f"    {rank}: {', '.join(teams)}")

        print(f"\n  [精灵查阵容] 快速查找: python product_query.py <精灵名>")
