"""
JS渲染引擎模块
=============
使用Selenium + Chrome Headless渲染JavaScript动态页面。
用于BiliWiki等需要JS渲染才能获取数据的站点。

功能：
- 渲染指定URL并返回BeautifulSoup对象
- 支持滚动加载（懒加载）
- 智能等待元素出现
- 自动管理浏览器实例池
"""

import time
import logging
from typing import Optional, List, Callable
from urllib.parse import unquote
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from ..config import REQUEST_CONFIG

logger = logging.getLogger(__name__)

# 全局浏览器实例（复用）
_driver: Optional[webdriver.Chrome] = None


def _create_driver() -> webdriver.Chrome:
    """创建Chrome Headless浏览器实例"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=zh-CN")
    options.add_argument("--disable-gpu")
    # 禁用图片加载（加快速度）
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    return webdriver.Chrome(options=options)


def get_driver() -> webdriver.Chrome:
    """获取或创建全局浏览器实例"""
    global _driver
    if _driver is None:
        _driver = _create_driver()
    return _driver


def close_driver():
    """关闭全局浏览器实例"""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None


def render_page(
    url: str,
    wait_selector: Optional[str] = None,
    wait_time: int = 3,
    scroll_times: int = 0,
    scroll_pause: float = 1.0,
) -> Optional[BeautifulSoup]:
    """
    渲染页面并返回BeautifulSoup对象。

    Args:
        url: 目标URL
        wait_selector: 等待特定CSS选择器出现
        wait_time: 基础等待时间（秒）
        scroll_times: 滚动次数（懒加载）
        scroll_pause: 滚动间隔（秒）

    Returns:
        BeautifulSoup对象，失败返回None
    """
    driver = get_driver()

    try:
        logger.debug(f"正在渲染: {url}")
        driver.get(url)

        # 等待指定选择器
        if wait_selector:
            try:
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            except TimeoutException:
                logger.debug(f"等待选择器超时: {wait_selector}")
        else:
            time.sleep(wait_time)

        # 滚动加载
        for i in range(scroll_times):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            # 滚动到顶部
            if i == scroll_times - 1:
                driver.execute_script("window.scrollTo(0, 0);")

        # 获取页面HTML，确保UTF-8编码正确
        html = driver.execute_script("return document.documentElement.outerHTML")
        # 获取实际字符集(页面可能在head中有meta charset)
        charset = driver.execute_script(
            "try { return document.characterSet || document.charset || 'UTF-8'; } catch(e) { return 'UTF-8'; }"
        )
        if charset and charset.upper() != "UTF-8" and charset.upper() != "UTF8":
            try:
                html_bytes = html.encode("latin-1")
                html = html_bytes.decode(charset)
            except Exception:
                pass
        # 构建完整HTML文档
        full_html = f"<!DOCTYPE html><html>{html}</html>"
        return BeautifulSoup(full_html, "lxml")

    except WebDriverException as e:
        logger.error(f"渲染失败 [{url}]: {e}")
        return None


def render_page_with_retry(
    url: str,
    max_retries: int = 3,
    **kwargs,
) -> Optional[BeautifulSoup]:
    """带重试的页面渲染"""
    for attempt in range(max_retries):
        result = render_page(url, **kwargs)
        if result is not None:
            return result
        logger.warning(f"渲染重试 [{attempt + 1}/{max_retries}]: {url}")
        time.sleep(REQUEST_CONFIG["retry_delay"])
    return None


def extract_pet_names_from_listing(
    force_refresh: bool = False,
) -> List[dict]:
    """
    从精灵图鉴列表页提取所有精灵名称（中英文映射）。

    通过渲染页面并解析精灵网格中的图片alt文本和链接。

    Returns:
        [{"pinyin": "banban", "chinese": "斑斑", "url_name": "斑斑"}, ...]
    """
    from ..config import DATA_SOURCES
    base = DATA_SOURCES["biliwiki"]["base"]
    list_path = DATA_SOURCES["biliwiki"]["pet_list"]
    url = f"{base}/{list_path}"

    # 渲染列表页（滚动以加载全部精灵）
    soup = render_page(url, scroll_times=5, scroll_pause=1.0)
    if not soup:
        logger.error("无法渲染精灵列表页")
        return []

    import re

    # 方法1: 从图片alt提取pinyin名
    pinyin_names = set()
    for img in soup.select("img[alt]"):
        alt = img.get("alt", "")
        if alt.startswith("JL "):
            name = alt[3:].replace(".png", "").strip()
            # 去除变体后缀
            name = re.sub(r"( yise| tuipi| caiyuqiu| duanmaoqiu| xiangyaqiu)$", "", name)
            if name:
                pinyin_names.add(name)

    # 方法2: 从链接提取中文名
    chinese_names = set()
    nav_pages = {"精灵图鉴", "首页", "图鉴", "地图", "技能", "工具",
                  "攻略", "帮助", "特殊", "模板", "分类", "其他", "MediaWiki"}
    for a in soup.select("a[href*='/rocom/']"):
        href = a.get("href", "")
        title = a.get("title", "")
        name = href.split("/rocom/")[-1].split("/")[0].split("#")[0]
        if name and name not in nav_pages:
            decoded = unquote(name)
            if decoded not in nav_pages and len(decoded) >= 2:
                chinese_names.add(decoded)

    # 方法3: 通过JS执行获取精灵数据
    # 尝试执行页面中的JS函数来获取数据映射
    driver = get_driver()
    js_data = None
    try:
        js_data = driver.execute_script(
            "try { return window.__spriteData || window.spriteData || null; } catch(e) { return null; }"
        )
    except Exception:
        pass

    # 构建结果
    # 由于中文名和拼音的映射无法直接从页面获取，分别返回
    result = {
        "pinyin_names": sorted(pinyin_names),
        "chinese_names": sorted(chinese_names),
        "total_pinyin": len(pinyin_names),
        "total_chinese": len(chinese_names),
        "js_data": js_data,
    }

    logger.info(
        f"精灵列表提取完成: "
        f"{len(pinyin_names)} pinyin + {len(chinese_names)} 中文"
    )

    return result


def extract_pet_detail(pet_url_name: str) -> Optional[dict]:
    """
    提取单个精灵的详细信息。

    Args:
        pet_url_name: 精灵名的URL编码形式（中文或pinyin）

    Returns:
        结构化字典或None
    """
    from ..config import DATA_SOURCES
    base = DATA_SOURCES["biliwiki"]["base"]
    import urllib.parse
    url = f"{base}/{urllib.parse.quote(pet_url_name)}"

    soup = render_page(url, wait_time=2)
    if not soup:
        return None

    data = {}

    # 标题（中文名）
    title_el = soup.select_one("h1#firstHeading")
    if title_el:
        data["name"] = title_el.get_text(strip=True)

    # 属性 - 从 .sprite_type 精确提取（备用：属性图标alt文本）
    elements = []
    type_el = soup.select_one(".sprite_type")
    if type_el:
        text = type_el.get_text(strip=True)
        for elem in ["火", "水", "草", "光", "普通", "机械", "地", "冰",
                       "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "幻"]:
            if elem in text:
                elements.append(elem)
    if not elements:
        for img in soup.select("img[alt*='属性']"):
            alt = img.get("alt", "")
            for elem in ["火", "水", "草", "光", "普通", "机械", "地", "冰",
                           "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "幻"]:
                if elem in alt and elem not in elements:
                    elements.append(elem)
    if elements:
        data["element"] = elements

    # 种族值 - 从 .sprite-info-attrlist 中一次性提取
    stats = {}
    attrlist = soup.select_one(".sprite-info-attrlist")
    if attrlist:
        text = attrlist.get_text(strip=True)
        import re
        patterns = [
            (r"生命[：:]\s*(\d+)", "hp"),
            (r"精力[：:]\s*(\d+)", "hp"),
            (r"物攻[：:]\s*(\d+)", "attack"),
            (r"物防[：:]\s*(\d+)", "defense"),
            (r"魔攻[：:]\s*(\d+)", "magic_attack"),
            (r"魔防[：:]\s*(\d+)", "magic_defense"),
            (r"速度[：:]\s*(\d+)", "speed"),
        ]
        for pattern, key in patterns:
            m = re.search(pattern, text)
            if m:
                stats[key] = int(m.group(1))

    # 总种族资质
    totalsum = soup.select_one(".sprite-info-attrsum")
    if totalsum:
        t_text = totalsum.get_text(strip=True)
        m = re.search(r"(\d+)", t_text)
        if m:
            stats["total"] = int(m.group(1))
    elif stats:
        stats["total"] = sum(v for v in stats.values())

    if stats:
        data["stats"] = stats

    # 描述
    desc_el = soup.select_one(".sprite-info-desc, .detail-des")
    if desc_el:
        data["description"] = desc_el.get_text(strip=True)

    # 稀有度
    rarity_el = soup.select_one(".sprite-nametitle, .sprite-typename")
    if rarity_el:
        data["rarity"] = rarity_el.get_text(strip=True)

    # 技能列表（完整字段）
    skills = []
    for skill_el in soup.select(".skill-single"):
        skill = _parse_skill_card(skill_el)
        if skill and skill.get("name"):
            skills.append(skill)
    if skills:
        data["skills"] = skills
        data["skills_count"] = len(skills)

    return data if data.get("name") else None


def _parse_skill_card(card) -> Optional[dict]:
    """
    解析单个技能卡片，提取完整技能信息。

    从BiliWiki技能卡片的HTML结构中提取：
    - name: 技能名称
    - element: 技能系别（光/火/水/普通...）
    - category: 技能分类（物攻/魔攻/状态/防御）
    - cost: 能耗（PP值）
    - power: 威力（状态技能为null）
    - effect: 技能效果描述
    - source: 解锁条件

    Args:
        card: BeautifulSoup Tag (div.skill-single)

    Returns:
        dict 或 None
    """
    import re

    # ---- 从data-attribute提取 ----
    category = card.get("data-param2", "")  # 魔攻/物攻/状态/防御
    element = card.get("data-param3", "")   # 系别

    # ---- 技能名称 ----
    name_el = card.select_one(".skill-name")
    if not name_el:
        return None
    name = name_el.get_text(strip=True)
    if not name:
        return None

    # ---- 能耗 (PP值) ----
    cost = None
    cost_el = card.select_one(".imgtext-row span:last-child")
    if cost_el:
        cost_text = cost_el.get_text(strip=True)
        if cost_text.isdigit():
            cost = int(cost_text)

    # ---- 威力 ----
    power = None
    # 分类为物攻/魔攻的技能有威力值
    if category in ("物攻", "魔攻"):
        # 从typelist的最后一个子span提取威力
        typelist = card.select_one(".skill-head-typelist")
        if typelist:
            children = list(typelist.find_all("span", recursive=False))
            # 结构: [耗能, 分类, 系别, 威力标签, imgtext-row, 分类图, 系别图, 威力值]
            if len(children) >= 8:
                power_text = children[7].get_text(strip=True)
                if power_text.isdigit():
                    power = int(power_text)

    # ---- 技能效果描述 ----
    effect = None
    for sel in [".skill-desc-atk", ".skill-desc"]:
        desc_el = card.select_one(sel)
        if desc_el:
            text = desc_el.get_text(strip=True)
            if text:
                effect = text
                break

    # ---- 解锁条件 ----
    source = None
    source_el = card.select_one(".skill-source")
    if source_el:
        source_text = source_el.get_text(strip=True)
        if source_text:
            source = source_text

    # ---- 来源类型 ----
    source_type = card.get("data-param1", "")

    skill = {
        "name": name,
        "element": element or None,
        "category": category or None,
        "cost": cost,
        "power": power,
        "effect": effect,
        "source": source,
        "source_type": source_type or None,
    }
    return skill


class RenderedBiliWikiScraper:
    """
    基于Selenium渲染的BiliWiki采集器。
    用于补充基础爬虫无法获取的JS渲染数据。
    """

    def __init__(self):
        self.pet_cache = {}

    def get_pet_list(self) -> dict:
        """获取精灵列表"""
        return extract_pet_names_from_listing()

    def get_pet_detail(self, name: str) -> Optional[dict]:
        """获取精灵详情"""
        if name in self.pet_cache:
            return self.pet_cache[name]
        detail = extract_pet_detail(name)
        if detail:
            self.pet_cache[name] = detail
        return detail

    def batch_get_details(self, names: List[str]) -> List[dict]:
        """批量获取精灵详情"""
        results = []
        total = len(names)
        for i, name in enumerate(names):
            logger.info(f"采集详情 [{i+1}/{total}]: {name}")
            detail = self.get_pet_detail(name)
            if detail:
                results.append(detail)
        return results

    def close(self):
        """清理资源"""
        close_driver()
