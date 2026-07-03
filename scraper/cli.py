"""
CLI 命令行入口
=============
采集命令:
  python cli.py fetch-pets      采集精灵数据
  python cli.py fetch-skills    采集技能数据
  python cli.py fetch-all       全量采集
  python cli.py fetch-teams     采集PVP阵容数据
  python cli.py list-data       查看已采集数据
  python cli.py export-all      导出所有数据
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# Windows GBK编码兼容
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn,
)
from rich.panel import Panel

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scraper.config import OUTPUT_CONFIG
from scraper.storage.json_storage import JsonStorage
from scraper.scrapers.biliwiki import BiliWikiScraper
from scraper.scrapers.pvp_teams import PvpTeamScraper
from scraper.scrapers.pet_scraper import IntegratedPetScraper
from scraper.seed_data import get_seed_pets, get_seed_skills, get_seed_summary
from scraper.product_exporter import (
    export_product_data, ProductUpdater, print_product_summary,
    normalize_pet, normalize_skill,
)
from scraper.models import PetBase, Pet, Skill, PvpTeam


console = Console()


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)],
    )


logger = logging.getLogger("cli")


# ================================================================
# 数据采集命令
# ================================================================

def cmd_fetch_pets(
    include_details: bool = False,
    max_pets: Optional[int] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """采集精灵数据"""
    setup_logging(verbose)
    console.print(Panel.fit("[bold]洛克王国世界 - 精灵数据采集[/bold]", border_style="blue"))

    storage = JsonStorage()
    scraper = BiliWikiScraper()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False,
    ) as progress:

        task1 = progress.add_task("正在采集精灵列表...", total=None)
        result = scraper.scrape(
            include_pets=True,
            include_skills=False,
            include_details=include_details,
            max_pets=max_pets,
        )
        progress.update(task1, completed=True)
        console.print(f"  OK: 采集到 [bold]{result['pets_count']}[/bold] 只精灵")

        list_path = storage.save(result["pets"], "pet_list.json")
        console.print(f"  列表已保存: {list_path}")

        if include_details and result.get("pet_details"):
            pets_full = result["pet_details"]
            detail_path = storage.save(pets_full, OUTPUT_CONFIG["pets_file"])
            console.print(f"  详情已保存: {detail_path}")
            console.print(f"  共采集 [bold]{len(pets_full)}[/bold] 只精灵的详细数据")

    console.print()
    summary_table = Table(title="精灵数据摘要", show_header=False)
    summary_table.add_column("项目", style="cyan")
    summary_table.add_column("数值", style="green")
    summary_table.add_row("精灵总数", str(result["pets_count"]))
    if result.get("pet_details_count"):
        summary_table.add_row("已采集详情", str(result["pet_details_count"]))
    console.print(summary_table)

    return result


def cmd_fetch_skills(verbose: bool = False) -> Dict[str, Any]:
    """采集技能数据"""
    setup_logging(verbose)
    console.print(Panel.fit("[bold]洛克王国世界 - 技能数据采集[/bold]", border_style="yellow"))

    storage = JsonStorage()
    scraper = BiliWikiScraper()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("正在采集技能数据...", total=None)
        result = scraper.scrape(include_pets=False, include_skills=True)
        progress.update(task, completed=True)

    console.print(f"  OK: 采集到 [bold]{result['skills_count']}[/bold] 个技能")

    filepath = storage.save(result["skills"], OUTPUT_CONFIG["skills_file"])
    console.print(f"  已保存: {filepath}")

    from collections import Counter
    element_counts = Counter(
        s["element"] for s in result["skills"] if s.get("element")
    )
    console.print()
    console.print("[bold]技能属性分布:[/bold]")
    for elem, count in element_counts.most_common():
        console.print(f"  {elem}: {count}")

    return result


def cmd_fetch_teams(verbose: bool = False) -> Dict[str, Any]:
    """采集PVP阵容数据"""
    setup_logging(verbose)
    console.print(Panel.fit("[bold]洛克王国世界 - PVP阵容采集[/bold]", border_style="magenta"))

    storage = JsonStorage()
    scraper = PvpTeamScraper()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("正在采集和分析PVP阵容...", total=None)
        result = scraper.scrape(use_web_sources=True, include_builtin=True)
        progress.update(task, completed=True)

    console.print(f"  OK: 获取到 [bold]{result['teams_count']}[/bold] 套阵容")

    filepath = storage.save(result["teams"], OUTPUT_CONFIG["teams_file"])
    console.print(f"  已保存: {filepath}")

    if result.get("rising_pets"):
        storage.save(result["rising_pets"], "rising_pets.json", backup=False)
        console.print(f"  新兴精灵数据已保存")

    console.print()
    console.print("[bold]阵容梯队分布:[/bold]")
    teams_by_rank = {}
    for team in result["teams"]:
        rank = team.get("rank", "T?")
        teams_by_rank.setdefault(rank, []).append(team["name"])

    for rank in sorted(teams_by_rank.keys(), reverse=True):
        teams_list = ", ".join(teams_by_rank[rank])
        console.print(f"  {rank}: {teams_list}")

    return result


def cmd_fetch_all(
    include_details: bool = False,
    max_pets: Optional[int] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """全量采集：精灵 + 技能 + 阵容"""
    setup_logging(verbose)
    console.print(Panel.fit(
        "[bold]洛克王国世界 - 全量数据采集[/bold]\n"
        "  采集: 精灵图鉴 + 技能数据库 + PVP阵容",
        border_style="green",
    ))

    result = {}
    start_time = datetime.now()

    console.print("\n[bold]--- 阶段 1/3: 精灵数据 ---[/bold]")
    pet_result = cmd_fetch_pets(
        include_details=include_details,
        max_pets=max_pets,
        verbose=verbose,
    )
    result["pets"] = pet_result

    console.print("\n[bold]--- 阶段 2/3: 技能数据 ---[/bold]")
    skill_result = cmd_fetch_skills(verbose=verbose)
    result["skills"] = skill_result

    console.print("\n[bold]--- 阶段 3/3: PVP阵容 ---[/bold]")
    team_result = cmd_fetch_teams(verbose=verbose)
    result["teams"] = team_result

    elapsed = (datetime.now() - start_time).total_seconds()
    console.print()
    console.print(Panel.fit(
        f"[bold green]OK: 全量采集完成！[/bold green]\n"
        f"  耗时: {elapsed:.1f} 秒\n"
        f"  精灵: {pet_result.get('pets_count', 0)} 只\n"
        f"  技能: {skill_result.get('skills_count', 0)} 个\n"
        f"  阵容: {team_result.get('teams_count', 0)} 套\n"
        f"  数据目录: {OUTPUT_CONFIG['data_dir']}",
        border_style="green",
    ))

    summary = {
        "fetched_at": datetime.now().isoformat(),
        "elapsed_seconds": elapsed,
        "pets_count": pet_result.get("pets_count", 0),
        "skills_count": skill_result.get("skills_count", 0),
        "teams_count": team_result.get("teams_count", 0),
    }
    storage = JsonStorage()
    storage.save(summary, "summary.json", backup=False)

    return result


# ================================================================
# 数据管理命令
# ================================================================

def cmd_list_data(verbose: bool = False):
    """列出已采集的数据文件"""
    setup_logging(verbose)
    console.print(Panel.fit("[bold]已采集数据文件[/bold]", border_style="cyan"))

    storage = JsonStorage()
    data_dir = storage.data_dir

    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        console.print("  还没有采集过数据，运行 fetch 命令开始采集")
        return

    table = Table(
        title=f"数据文件 ({len(json_files)} 个)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("文件名", style="cyan")
    table.add_column("记录数", style="green", justify="right")
    table.add_column("大小", style="yellow", justify="right")
    table.add_column("更新时间", style="white")

    total_records = 0
    for fp in json_files:
        data = storage.load(fp.name)
        records = len(data) if isinstance(data, list) else 1
        total_records += records
        stats = fp.stat()
        size_str = f"{stats.st_size / 1024:.1f} KB"
        mtime = datetime.fromtimestamp(stats.st_mtime).strftime("%m-%d %H:%M")
        table.add_row(fp.name, str(records), size_str, mtime)

    console.print(table)
    console.print(f"\n总计: {total_records} 条记录")


def cmd_export_all(output_file: str = "all_data.json", verbose: bool = False):
    """导出所有数据到单个JSON文件"""
    setup_logging(verbose)
    console.print(Panel.fit("[bold]导出全量数据[/bold]", border_style="green"))

    storage = JsonStorage()

    pets = storage.load(OUTPUT_CONFIG["pets_file"]) or []
    pet_list = storage.load("pet_list.json") or []
    skills = storage.load(OUTPUT_CONFIG["skills_file"]) or []
    teams = storage.load(OUTPUT_CONFIG["teams_file"]) or []
    type_chart = storage.load(OUTPUT_CONFIG["type_chart_file"])
    rising_pets = storage.load("rising_pets.json") or []

    export = {
        "exported_at": datetime.now().isoformat(),
        "version": "1.0.0",
        "game": "洛克王国世界",
        "data": {
            "pets": pets if pets else pet_list,
            "skills": skills,
            "pvp_teams": teams,
            "type_chart": type_chart,
            "rising_pets": rising_pets,
        },
        "statistics": {
            "pets_count": len(pets) if pets else len(pet_list),
            "skills_count": len(skills),
            "teams_count": len(teams),
            "rising_pets_count": len(rising_pets),
        },
    }

    export_path = storage.data_dir / output_file
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    stats = export_path.stat()
    console.print(f"  OK: 已导出: {export_path}")
    console.print(f"  数据量: {stats.st_size / 1024:.1f} KB")
    console.print(f"  包含: {export['statistics']}")

    return str(export_path)


# ================================================================
# 产品数据导出命令
# ================================================================

def cmd_export_product(verbose: bool = False, check_updates: bool = False):
    """导出标准化产品数据"""
    setup_logging(verbose)
    console.print(Panel.fit(
        "[bold]导出产品标准化数据[/bold]\n"
        "  数据格式: 字段完整 + 编码统一 + 标准索引",
        border_style="green",
    ))

    updater = ProductUpdater()

    if check_updates:
        status = updater.check_updates()
        if status["has_updates"]:
            console.print("  [yellow]检测到数据变更:[/yellow]")
            for change in status["changes"]:
                console.print(f"    {change['type']}: {change['before']} → {change['after']} (+{change['delta']})")
        else:
            console.print("  数据无变更，使用缓存版本")
            return

    output_path = updater.export_with_version()
    print_product_summary(output_path, verbose=verbose)

    return output_path


# ================================================================
# 属性克制数据导出
# ================================================================

def cmd_export_type_chart(verbose: bool = False):
    """导出属性克制数据"""
    setup_logging(verbose)

    from scraper.config import TYPE_CHART, ELEMENTS

    data = {
        "elements": ELEMENTS,
        "chart": TYPE_CHART,
        "description": "攻方->守方：2.0=克制, 1.0=普通, 0.5=被抗, 0=免疫",
    }

    storage = JsonStorage()
    filepath = storage.save(data, OUTPUT_CONFIG["type_chart_file"])
    console.print(f"  OK: 已保存: {filepath}")

    console.print(f"\n[bold]属性列表 ({len(ELEMENTS)} 种):[/bold]")
    console.print("  " + ", ".join(ELEMENTS[:9]))
    console.print("  " + ", ".join(ELEMENTS[9:]))


# ================================================================
# 种子数据命令
# ================================================================

def cmd_use_seed(verbose: bool = False):
    """加载种子数据到存储"""
    setup_logging(verbose)
    console.print(Panel.fit("[bold]加载种子数据[/bold]", border_style="green"))

    storage = JsonStorage()
    seed_summary = get_seed_summary()

    # 保存种子精灵数据
    pets = get_seed_pets()
    storage.save(pets, "seed_pets.json", backup=False)
    console.print(f"  种子精灵: {len(pets)} 只已保存")

    # 保存种子技能数据
    skills = get_seed_skills()
    storage.save(skills, "seed_skills.json", backup=False)
    console.print(f"  种子技能: {len(skills)} 个已保存")

    # 合并到主数据集（不覆盖已有数据）
    storage.merge_and_save(pets, OUTPUT_CONFIG["pets_file"], key_field="name")
    storage.merge_and_save(skills, OUTPUT_CONFIG["skills_file"], key_field="name")

    console.print()
    console.print("[bold]种子数据摘要:[/bold]")
    console.print(f"  精灵: {seed_summary['pets_count']} 只")
    console.print(f"  技能: {seed_summary['skills_count']} 个")
    console.print(f"  属性: {', '.join(sorted(seed_summary['pet_elements']))}")


# ================================================================
# BiliWiki 精准爬虫 (轻量版, 无需Selenium)
# ================================================================

def cmd_fetch_biliwiki(names: List[str] = None, all_pets: bool = False,
                       max_pets: int = None, verbose: bool = False):
    """使用轻量 BiliWiki 爬虫采集精灵数据"""
    setup_logging(verbose)
    from scraper.scrapers.biliwiki_scraper import BiliWikiScraper
    from scraper.seed_data import get_seed_pets

    scraper = BiliWikiScraper()

    # 确定要采集的精灵列表
    if names:
        pet_names = names
    elif all_pets:
        # 从种子数据中获取全部精灵名
        seed_pets = get_seed_pets()
        pet_names = [p["name"] for p in seed_pets]
    else:
        console.print("[yellow]请指定 --names 或 --all[/yellow]")
        return

    if max_pets:
        pet_names = pet_names[:max_pets]

    console.print(f"将从 BiliWiki 采集 [bold]{len(pet_names)}[/bold] 只精灵的数据")
    console.print(f"（使用轻量 HTTP 爬虫，无需 Selenium）\n")

    pets = []
    total = len(pet_names)
    for i, name in enumerate(pet_names):
        console.print(f"  [{i+1}/{total}] {name}...", end="")
        pet = scraper.get_pet(name)
        if pet:
            sk = len(pet.get("skills", []))
            st = pet.get("stats", {})
            console.print(f" ✅ {sk} 技能, 种族 {st.get('total', '?')}")
            pets.append(pet)
        else:
            console.print(f" ❌ 失败")
        # 防止请求过快被 ban
        if i < total - 1:
            import time
            time.sleep(0.3)

    # 保存
    if pets:
        from scraper.storage.json_storage import JsonStorage
        storage = JsonStorage()
        filepath = storage.save(pets, "biliwiki_pets.json")
        console.print(f"\n✅ 已保存 {len(pets)} 只精灵数据: {filepath}")
    else:
        console.print("\n❌ 未采集到任何数据")


def cmd_export_from_biliwiki(verbose: bool = False):
    """从 BiliWiki 采集全部精灵并直接导出为产品数据"""
    from scraper.scrapers.biliwiki_scraper import BiliWikiScraper
    from scraper.seed_data import get_seed_pets
    from scraper.product_exporter import export_product_data, print_product_summary
    from scraper.storage.json_storage import JsonStorage
    from scraper.config import OUTPUT_CONFIG
    import time

    setup_logging(verbose)
    console.print(Panel.fit(
        "[bold]BiliWiki 全量采集 → 导出产品数据[/bold]\n"
        "  从 BiliWiki 采集所有精灵数据，直接生成 product_data.json",
        border_style="green",
    ))

    # 获取精灵列表（种子数据 + 额外已知精灵）
    seed_pets = get_seed_pets()
    pet_names = [p["name"] for p in seed_pets]
    # 添加种子数据中缺失的重要精灵
    EXTRA_PETS = ["迪莫", "火神", "水灵", "草系精灵", "小鹬", "呆火鸟"]
    for name in EXTRA_PETS:
        if name not in pet_names:
            pet_names.append(name)
    console.print(f"将从 BiliWiki 采集 [bold]{len(pet_names)}[/bold] 只精灵\n")

    scraper = BiliWikiScraper()
    pets = []
    total = len(pet_names)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("采集精灵数据...", total=total)

        for i, name in enumerate(pet_names):
            pet = scraper.get_pet(name)
            if pet:
                pets.append(pet)
            progress.update(task, advance=1, description=f"采集: {name}")
            if i < total - 1:
                time.sleep(0.3)

    console.print(f"\n✅ 采集完成: [bold]{len(pets)}[/bold] 只精灵")

    # 保存到存储文件（供产品导出器使用）
    storage = JsonStorage()
    storage.save(pets, OUTPUT_CONFIG["pets_file"])
    console.print(f"  已保存到存储: {OUTPUT_CONFIG['pets_file']}")

    # 调用产品导出器生成最终数据
    console.print(f"  正在生成产品数据...")
    export_path = export_product_data()
    print_product_summary(export_path, verbose=verbose)

def cmd_render_list(verbose: bool = False):
    """使用Selenium渲染精灵列表页并提取数据"""
    setup_logging(verbose)
    console.print(Panel.fit(
        "[bold]BiliWiki渲染采集 - 精灵列表[/bold]\n"
        "  使用Selenium渲染JS页面以获取完整精灵列表",
        border_style="blue",
    ))

    from scraper.scrapers.renderer import extract_pet_names_from_listing, close_driver

    try:
        result = extract_pet_names_from_listing()
        if result:
            console.print(f"  Pinyin名: {result['total_pinyin']} 个")
            console.print(f"  中文名: {result['total_chinese']} 个")

            # 保存
            storage = JsonStorage()
            storage.save(result, "rendered_pet_list.json", backup=False)

            # 预览
            if result.get("chinese_names"):
                console.print(f"\n[bold]中文名预览 (前20):[/bold]")
                for name in result["chinese_names"][:20]:
                    console.print(f"  {name}")

            if result.get("pinyin_names"):
                console.print(f"\n[bold]Pinyin名预览 (前20):[/bold]")
                for name in result["pinyin_names"][:20]:
                    console.print(f"  {name}")
        else:
            console.print("[yellow]未获取到数据，可使用种子数据代替[/yellow]")
    finally:
        close_driver()


def cmd_render_details(names: List[str] = None, verbose: bool = False):
    """使用Selenium渲染精灵详情页"""
    setup_logging(verbose)
    console.print(Panel.fit(
        "[bold]BiliWiki渲染采集 - 精灵详情[/bold]",
        border_style="blue",
    ))

    from scraper.scrapers.renderer import RenderedBiliWikiScraper, close_driver

    scraper = RenderedBiliWikiScraper()

    try:
        if not names:
            # 如果没有指定，使用种子数据中的精灵名
            names = [p["name"] for p in get_seed_pets()]
            console.print(f"  使用种子数据中的 {len(names)} 只精灵")

        details = []
        total = len(names)
        for i, name in enumerate(names):
            console.print(f"  [{i+1}/{total}] 采集: {name}")
            detail = scraper.get_pet_detail(name)
            if detail:
                details.append(detail)

        # 保存
        if details:
            storage = JsonStorage()
            filepath = storage.save(details, "rendered_pet_details.json")
            console.print(f"\n  OK: 已保存 {len(details)} 只详情: {filepath}")

            # 合并到主数据集
            storage.merge_and_save(details, OUTPUT_CONFIG["pets_file"], key_field="name")
            console.print(f"  已合并到主数据集")
    finally:
        scraper.close()


# ================================================================
# 主入口
# ================================================================

def main():
    """CLI主入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="洛克王国世界 PVP 数据采集器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python cli.py use-seed               加载种子数据（71只精灵+31技能）
  python cli.py fetch-teams            采集PVP阵容（10套）
  python cli.py render-details 火神    渲染精灵详情（含完整技能）
  python cli.py export-product         导出标准化产品数据
  python cli.py export-product --check 带变更检测导出
  python cli.py list-data              查看已采集数据
  python cli.py fetch-all              全量采集
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    p_pets = subparsers.add_parser("fetch-pets", help="采集精灵数据")
    p_pets.add_argument("--details", action="store_true", help="同时采集每只精灵的详细信息")
    p_pets.add_argument("--max", type=int, default=None, help="最多采集多少只详情")
    p_pets.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    p_skills = subparsers.add_parser("fetch-skills", help="采集技能数据")
    p_skills.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    p_teams = subparsers.add_parser("fetch-teams", help="采集PVP阵容数据")
    p_teams.add_argument("--no-web", action="store_true", help="不使用网页抓取，仅用内置数据")
    p_teams.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    p_all = subparsers.add_parser("fetch-all", help="全量采集（精灵+技能+阵容）")
    p_all.add_argument("--details", action="store_true", help="同时采集精灵详情")
    p_all.add_argument("--max", type=int, default=None, help="最多采集多少只精灵详情")
    p_all.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    subparsers.add_parser("list-data", help="查看已采集数据")

    p_export = subparsers.add_parser("export-all", help="导出全量数据为JSON")
    p_export.add_argument("-o", "--output", default="all_data.json", help="输出文件名")
    p_export.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    subparsers.add_parser("export-type-chart", help="导出属性克制数据")

    # Product data export
    p_prod = subparsers.add_parser("export-product", help="导出标准化产品数据（字段完整+编码统一）")
    p_prod.add_argument("--check", action="store_true", help="检查数据变更后导出")
    p_prod.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    # Seed data
    p_seed = subparsers.add_parser("use-seed", help="加载种子数据")
    p_seed.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    # Render commands
    p_rlist = subparsers.add_parser("render-list", help="使用Selenium渲染精灵列表")
    p_rlist.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    p_rdetail = subparsers.add_parser("render-details", help="使用Selenium渲染精灵详情")
    p_rdetail.add_argument("names", nargs="*", default=None, help="精灵名（不提供则使用种子数据中的精灵）")
    p_rdetail.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    # BiliWiki 精准爬虫 (轻量版)
    p_bwiki = subparsers.add_parser("fetch-biliwiki", help="从BiliWiki采集精灵数据（轻量HTTP，无需Selenium）")
    p_bwiki.add_argument("names", nargs="*", default=None, help="精灵名（空格分隔）")
    p_bwiki.add_argument("--all", action="store_true", help="采集种子数据中所有精灵")
    p_bwiki.add_argument("--max", type=int, default=None, help="最多采集多少只")
    p_bwiki.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    p_bwexport = subparsers.add_parser("export-from-biliwiki", help="从BiliWiki全量采集并直接导出为产品数据")
    p_bwexport.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        console.print("\n[bold yellow]提示:[/bold yellow] 运行 [bold]python cli.py use-seed[/bold] 加载种子数据")
        console.print("  或 [bold]python cli.py fetch-teams[/bold] 采集PVP阵容数据")
        console.print("  或 [bold]python cli.py fetch-all[/bold] 全量采集")
        return

    commands = {
        "fetch-pets": lambda: cmd_fetch_pets(
            include_details=getattr(args, "details", False),
            max_pets=getattr(args, "max", None),
            verbose=getattr(args, "verbose", False),
        ),
        "fetch-skills": lambda: cmd_fetch_skills(
            verbose=getattr(args, "verbose", False),
        ),
        "fetch-teams": lambda: cmd_fetch_teams(
            verbose=getattr(args, "verbose", False),
        ),
        "fetch-all": lambda: cmd_fetch_all(
            include_details=getattr(args, "details", False),
            max_pets=getattr(args, "max", None),
            verbose=getattr(args, "verbose", False),
        ),
        "list-data": lambda: cmd_list_data(
            verbose=getattr(args, "verbose", False),
        ),
        "export-all": lambda: cmd_export_all(
            output_file=getattr(args, "output", "all_data.json"),
            verbose=getattr(args, "verbose", False),
        ),
        "export-type-chart": lambda: cmd_export_type_chart(
            verbose=getattr(args, "verbose", False),
        ),
        "export-product": lambda: cmd_export_product(
            verbose=getattr(args, "verbose", False),
            check_updates=getattr(args, "check", False),
        ),
        "use-seed": lambda: cmd_use_seed(
            verbose=getattr(args, "verbose", False),
        ),
        "render-list": lambda: cmd_render_list(
            verbose=getattr(args, "verbose", False),
        ),
        "render-details": lambda: cmd_render_details(
            names=getattr(args, "names", None),
            verbose=getattr(args, "verbose", False),
        ),
        "fetch-biliwiki": lambda: cmd_fetch_biliwiki(
            names=getattr(args, "names", None),
            all_pets=getattr(args, "all", False),
            max_pets=getattr(args, "max", None),
            verbose=getattr(args, "verbose", False),
        ),
        "export-from-biliwiki": lambda: cmd_export_from_biliwiki(
            verbose=getattr(args, "verbose", False),
        ),
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        cmd_fn()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
