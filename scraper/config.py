"""
爬虫配置文件
============
集中管理所有目标URL、请求头、选择器表达式等配置项。
"""

from typing import Dict, List, Optional

# ============================================================
# 网络请求配置
# ============================================================
REQUEST_CONFIG = {
    "timeout": 30,                      # 请求超时（秒）
    "retries": 3,                       # 失败重试次数
    "retry_delay": 2,                   # 重试间隔（秒）
    "concurrency": 5,                   # 并发请求数
    "delay_between_requests": 1.0,      # 请求间隔（秒），避免被封
}

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

# ============================================================
# 数据源URL
# ============================================================
DATA_SOURCES = {
    # --- 精灵图鉴 ---
    "biliwiki": {
        "base": "https://wiki.biligame.com/rocom",
        "pet_list": "精灵图鉴",
        "pet_detail_template": "{pet_name}",
        "skill_list": "技能查询",
        "skill_overview": "技能一览",
        "type_chart": "属性克制",
    },
    "huiji_wiki": {
        "base": "https://rocokingdom.huijiwiki.com",
        "pet_list": "/wiki/宠物图鉴",
        "pet_detail_template": "/wiki/{pet_name}",
    },
    "backup_ninegame": {
        "base": "https://www.9game.cn",
        "pet_list": "/lkwgsy/11772841.html",
    },
    # --- PVP阵容数据 ---
    "pvp_sources": [
        {
            "name": "smzdm_S2",
            "url": "https://post.smzdm.com/p/axkpo054/",
            "type": "article",
        },
        {
            "name": "smzdm_weekly",
            "url": "https://post.smzdm.com/p/aggm7w3w/",
            "type": "article",
        },
        {
            "name": "52pk_high_winrate",
            "url": "https://m.52pk.com/pc/miji/7610146.shtml",
            "type": "article",
        },
        {
            "name": "biubiu_strong",
            "url": "https://www.biubiu001.com/news/178004.html",
            "type": "article",
        },
    ],
}

# ============================================================
# BiliWiki 页面选择器（基于MediaWiki通用结构）
# ============================================================
BILIWIKI_SELECTORS = {
    # 精灵列表页 - 表格选择器
    "pet_list_table": "table.wikitable, table.sortable, table.table-bordered",
    "pet_list_rows": "tbody tr",
    "pet_name_cell": "td:nth-child(2) a, td:nth-child(1) a",
    "pet_detail_link": "td:nth-child(1) a, td:nth-child(2) a",

    # 精灵详情页 - 信息框
    "pet_infobox": "table.infobox, .wikitable.infobox, div.infoBox",
    "pet_name_title": "h1#firstHeading, .page-header__title",
    "pet_element": (
        ".infobox td:contains('属性') + td, "
        "td:has(> b:contains('属性')) + td, "
        "th:contains('属性') + td"
    ),
    "pet_rarity": (
        ".infobox td:contains('稀有度') + td, "
        "th:contains('稀有度') + td"
    ),
    "pet_basic_stats": "table.basic-stats, .stat-table",

    # 技能列表页
    "skill_table": "table.wikitable, table.sortable",
    "skill_rows": "tbody tr",
    "skill_name": "td:nth-child(1) a, td:nth-child(1)",
    "skill_element": "td:nth-child(2)",
    "skill_category": "td:nth-child(3)",
    "skill_power": "td:nth-child(4)",
    "skill_cost": "td:nth-child(5)",
    "skill_effect": "td:nth-child(6)",

    # 属性克制表
    "type_chart_table": "table.wikitable",
}

# ============================================================
# 属性克制关系（游戏内完整属性列表）
# ============================================================
# 洛克王国世界共有 18 种属性
ELEMENTS = [
    "普通", "草", "火", "水", "光", "机械", "地", "冰",
    "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "幻",
]

# 属性克制矩阵（攻方→守方）：2.0 = 克制, 0.5 = 被抗, 0 = 免疫
# 数据基于游戏内实际设定
TYPE_CHART: Dict[str, Dict[str, float]] = {
    "普通": {"幽": 0, "机械": 0.5, "萌": 0.5},
    "草": {"火": 0.5, "水": 2.0, "草": 0.5, "地": 2.0, "冰": 0.5, "毒": 0.5, "虫": 0.5, "龙": 0.5, "翼": 0.5, "幽": 0.5},
    "火": {"火": 0.5, "水": 0.5, "草": 2.0, "冰": 2.0, "虫": 2.0, "龙": 0.5, "机械": 2.0, "地": 0.5},
    "水": {"火": 2.0, "水": 0.5, "草": 0.5, "地": 2.0, "龙": 0.5, "冰": 0.5},
    "光": {"幽": 2.0, "恶": 2.0, "光": 0.5, "萌": 0.5},
    "机械": {"冰": 2.0, "机械": 0.5, "火": 0.5, "水": 0.5, "电": 0.5, "虫": 0.5, "草": 0.5, "武": 0.5, "地": 0.5, "毒": 0.5, "幽": 0.5, "幻": 0.5},
    "地": {"火": 2.0, "电": 2.0, "毒": 2.0, "草": 0.5, "虫": 0.5, "水": 0.5, "冰": 0.5, "地": 0.5, "翼": 0},
    "冰": {"草": 2.0, "地": 2.0, "冰": 0.5, "龙": 2.0, "水": 0.5, "火": 0.5, "武": 0.5, "机械": 0.5},
    "龙": {"龙": 2.0, "萌": 2.0, "幻": 0.5, "冰": 0.5, "机械": 0.5},
    "电": {"水": 2.0, "电": 0.5, "草": 0.5, "地": 0.5, "龙": 0.5, "翼": 2.0},
    "毒": {"草": 2.0, "毒": 0.5, "地": 0.5, "萌": 2.0, "幽": 0.5, "虫": 0.5},
    "虫": {"草": 2.0, "火": 0.5, "虫": 0.5, "毒": 0.5, "翼": 0.5, "幽": 0.5, "恶": 2.0, "萌": 2.0, "幻": 0.5},
    "武": {"冰": 2.0, "武": 0.5, "毒": 0.5, "翼": 0.5, "幽": 0.5, "恶": 2.0, "普通": 2.0, "机械": 2.0, "萌": 0.5, "虫": 0.5},
    "翼": {"草": 2.0, "虫": 2.0, "武": 2.0, "电": 0.5, "冰": 0.5, "地": 0},
    "萌": {"武": 2.0, "毒": 0.5, "幽": 0.5, "恶": 0, "萌": 0.5, "虫": 0.5},
    "幽": {"萌": 2.0, "幽": 2.0, "恶": 0.5, "普通": 0},
    "恶": {"幽": 2.0, "恶": 0.5, "萌": 2.0, "虫": 0.5, "武": 0.5},
    "幻": {"龙": 2.0, "武": 2.0, "虫": 2.0, "幻": 0.5, "恶": 0.5, "萌": 0.5, "冰": 0.5, "毒": 0.5},
}

# ============================================================
# 输出路径配置
# ============================================================
OUTPUT_CONFIG = {
    "data_dir": "data",
    "pets_file": "pets.json",
    "skills_file": "skills.json",
    "teams_file": "pvp_teams.json",
    "type_chart_file": "type_chart.json",
    "backup_dir": "data/backup",
    "log_file": "logs/scraper.log",
}
