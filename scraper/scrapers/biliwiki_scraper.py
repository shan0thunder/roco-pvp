#!/usr/bin/env python3
"""
BiliWiki 精准爬虫 — 轻量版
==========================
直接使用 requests + BeautifulSoup（无需 Selenium）
提取精灵详情、技能、种族值等数据。

为什么不用 Selenium：
- BiliWiki 页面是服务端渲染的 HTML
- requests 足够，速度快 10 倍，更稳定

使用方式：
  python -c "from scraper.scrapers.biliwiki_scraper import BiliWikiScraper;
              s = BiliWikiScraper();
              print(s.get_pet('迪莫'))"
"""

import re
import json
import logging
import time
from typing import Optional, Dict, List
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 已知的 18 种属性
ALL_ELEMENTS = {"火", "水", "草", "光", "普通", "机械", "地", "冰",
                "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "幻"}

# 中文 stat 字段名 → 产品字段名
STAT_MAP = {
    "生命": "hp", "体力": "hp", "精力": "hp",
    "物攻": "attack", "攻击": "attack",
    "物防": "defense", "防御": "defense",
    "魔攻": "magic_attack",
    "魔防": "magic_defense",
    "速度": "speed",
}


class BiliWikiScraper:
    """BiliWiki 精准爬虫"""

    BASE = "https://wiki.biligame.com/rocom"

    # 种子数据名 → BiliWiki 页面名映射（名称不匹配时）
    NAME_MAP = {
        "火狗": "火狗",
        "冰猪": "冰猪",
        "天鹅": "天鹅",
        "羚羊": "羚羊",
    }

    def __init__(self, timeout: int = 15):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://wiki.biligame.com/rocom/",
            "Cache-Control": "max-age=0",
        })
        self.timeout = timeout
        # 缓存已抓取的页面，避免重复请求
        self._cache: Dict[str, BeautifulSoup] = {}
        # 请求计数，用于自动限速
        self._req_count = 0

    def _fetch(self, url: str, retry: int = 1) -> Optional[BeautifulSoup]:
        """获取并解析页面，带重试和反封禁"""
        if url in self._cache:
            return self._cache[url]

        # 限速: 每 3 次请求后额外等待 0.5s
        self._req_count += 1
        if self._req_count > 0 and self._req_count % 3 == 0:
            import time
            time.sleep(0.5)

        for attempt in range(retry + 1):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                # 567 等状态码说明被封/限流，换 User-Agent 重试
                if resp.status_code in (567, 429, 503):
                    import time
                    wait = 3 * (attempt + 1)
                    logger.warning(f"限流 (HTTP {resp.status_code})，等待 {wait}s 后重试...")
                    time.sleep(wait)
                    # 换 UA
                    self.session.headers.update({
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                      "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                    })
                    continue

                if resp.status_code == 404:
                    return None

                resp.raise_for_status()
                resp.encoding = 'utf-8'
                soup = BeautifulSoup(resp.text, 'lxml')
                for tag in soup(['style', 'script']):
                    tag.decompose()
                self._cache[url] = soup
                return soup

            except requests.RequestException as e:
                if attempt < retry:
                    import time
                    wait = 2 * (attempt + 1)
                    logger.debug(f"重试 [{attempt+1}/{retry}] {wait}s: {url}")
                    time.sleep(wait)
                else:
                    logger.warning(f"请求失败 [{url}]: {e}")
                    return None

        return None

    # ================================================================
    # 精灵详情
    # ================================================================

    def get_pet(self, name: str) -> Optional[Dict]:
        """
        获取精灵完整信息。

        Args:
            name: 精灵名（中文），如 "迪莫"

        Returns:
            dict 包含精灵的所有数据，或 None
        """
        import urllib.parse
        # 使用名称映射（种子数据名 → BiliWiki页面名）
        page_name = self.NAME_MAP.get(name, name)
        url = f"{self.BASE}/{urllib.parse.quote(page_name)}"
        soup = self._fetch(url)
        if not soup:
            return None

        data = {}

        # ---- 名称 ----
        title_el = soup.select_one("h1#firstHeading")
        data["name"] = title_el.get_text(strip=True) if title_el else name

        # ---- 属性 ----
        elements = self._extract_elements(soup)
        if elements:
            data["element"] = elements

        # ---- 种族值 ----
        stats = self._extract_stats(soup)
        if stats:
            data["stats"] = stats

        # ---- 主题图片 ----
        img_url = self._extract_image(soup)
        if img_url:
            data["image"] = img_url

        # ---- 描述 ----
        desc = self._extract_description(soup)
        if desc:
            data["description"] = desc

        # ---- 技能 ----
        skills = self._extract_skills(soup)
        if skills:
            data["skills"] = skills
            data["skills_count"] = len(skills)

        # ---- 来源 URL ----
        data["source_url"] = url
        data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        return data

    def _extract_elements(self, soup: BeautifulSoup) -> List[str]:
        """
        提取属性。

        页面结构: <span class="sprite_type">光</span>
        双属性精灵有两个 .sprite_type 元素。
        """
        elements = []
        for el in soup.select(".sprite_type"):
            text = el.get_text(strip=True)
            for elem in ALL_ELEMENTS:
                if elem in text and elem not in elements:
                    elements.append(elem)
        return elements

    def _extract_stats(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        提取种族值。

        页面结构:
          <div class="sprite-info-attr">
            <span class="sprite-info-attrname">生命</span>
            ...
            <span class="sprite-info-attrnum">120</span>
          </div>
        """
        stats = {}
        for attr in soup.select(".sprite-info-attr"):
            name_el = attr.select_one(".sprite-info-attrname")
            num_el = attr.select_one(".sprite-info-attrnum")
            if not name_el or not num_el:
                continue
            # 属性名在第一个 <span> 中（跳过图片后的文字）
            name_span = name_el.find("span")
            name = name_span.get_text(strip=True) if name_span else name_el.get_text(strip=True)
            # 去掉可能的冒号后缀
            name = name.rstrip(":：")
            num = num_el.get_text(strip=True)
            # 映射到产品字段名
            field = STAT_MAP.get(name)
            if field and num.isdigit():
                stats[field] = int(num)

        # 种族总和
        total_el = soup.select_one(".sprite-info-attrsum")
        if total_el:
            text = total_el.get_text(strip=True)
            m = re.search(r"(\d+)", text)
            if m:
                stats["total"] = int(m.group(1))
        elif stats:
            stats["total"] = sum(v for v in stats.values())

        return stats if stats else None

    def _extract_image(self, soup: BeautifulSoup) -> Optional[str]:
        """提取精灵主题图片"""
        for img in soup.select('img[alt*="JL "]'):
            src = img.get('src', '')
            if '/thumb/' in src and 'px-JL_' in src:
                # 转换为原始图片URL:
                # 输入: .../thumb/X/Y/hash.png/180px-JL_name.png
                # 输出: .../X/Y/hash.png
                no_thumb = src.replace('/thumb/', '/')
                last_slash = no_thumb.rfind('/')
                if last_slash > 0:
                    return no_thumb[:last_slash]
        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """提取精灵描述"""
        for sel in [".sprite-info-desc", ".detail-des", ".sprite-desc"]:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text:
                    return text
        return None

    def _extract_skills(self, soup: BeautifulSoup) -> List[Dict]:
        """
        提取所有技能。

        页面结构:
          <div class="skill-single" data-param1="默认" data-param2="魔攻" data-param3="光">
            <div class="skill-name">光之冲击</div>
            <div class="skill-head-typelist">
              <span>分类</span> <span>物攻</span> ...
              <span class="imgtext-row">能耗值</span>
              <span>威力值</span>
            </div>
            <div class="skill-desc-atk">技能效果描述</div>
            <div class="skill-source">解锁条件</div>
          </div>
        """
        skills = []
        for card in soup.select(".skill-single"):
            skill = self._parse_skill(card)
            if skill:
                skills.append(skill)
        return skills

    def _parse_skill(self, card) -> Optional[Dict]:
        """解析单个技能卡片"""
        # 名称
        name_el = card.select_one(".skill-name")
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name:
            return None

        # data 属性
        category = card.get("data-param2", "") or ""
        element = card.get("data-param3", "") or ""

        # 能耗（PP值）
        cost = None
        cost_el = card.select_one(".imgtext-row span:last-child")
        if cost_el:
            text = cost_el.get_text(strip=True)
            if text.isdigit():
                cost = int(text)

        # 威力
        power = None
        if category in ("物攻", "魔攻"):
            typelist = card.select_one(".skill-head-typelist")
            if typelist:
                spans = typelist.find_all("span", recursive=False)
                # 结构: [分类名, 分类值, 系别名, 系别值, imgtext-row, 空, 空, 威力值]
                if len(spans) >= 8:
                    power_text = spans[7].get_text(strip=True)
                    if power_text.isdigit():
                        power = int(power_text)

        # 效果描述
        effect = None
        for sel in [".skill-desc-atk", ".skill-desc"]:
            desc_el = card.select_one(sel)
            if desc_el:
                text = desc_el.get_text(strip=True)
                if text:
                    effect = text
                    break

        # 解锁条件
        source = None
        source_el = card.select_one(".skill-source")
        if source_el:
            text = source_el.get_text(strip=True)
            if text:
                source = text

        return {
            "name": name,
            "element": element or None,
            "category": category or None,
            "cost": cost,
            "power": power,
            "effect": effect or "",
            "source": source or "",
        }

    # ================================================================
    # 批量操作
    # ================================================================

    def batch_get_pets(self, names: List[str], delay: float = 0.5) -> List[Dict]:
        """
        批量获取精灵数据。

        Args:
            names: 精灵名列表
            delay: 请求间隔（秒），避免被封

        Returns:
            成功提取的精灵列表
        """
        results = []
        total = len(names)
        for i, name in enumerate(names):
            logger.info(f"采集 [{i+1}/{total}]: {name}")
            pet = self.get_pet(name)
            if pet:
                results.append(pet)
                logger.info(f"  ✅ {name} — {len(pet.get('skills',[]))} 个技能")
            else:
                logger.warning(f"  ❌ {name} — 获取失败")
            if i < total - 1:
                time.sleep(delay)
        return results

    def get_pet_list_from_category(self) -> List[str]:
        """
        从分类页面获取所有精灵名。

        访问 BiliWiki 的分类:精灵 页面。
        """
        url = f"{self.BASE}/分类:精灵"
        soup = self._fetch(url)
        if not soup:
            return []

        names = []
        # 分类页面中的精灵列表链接
        for a in soup.select("#mw-pages a[href*='/rocom/']"):
            href = a.get("href", "")
            title = a.get("title", "")
            if title and not title.startswith("分类"):
                names.append(title)

        # 去重
        seen = set()
        unique = []
        for n in names:
            if n not in seen:
                seen.add(n)
                unique.append(n)
        return unique


# ================================================================
# 快捷测试
# ================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    scraper = BiliWikiScraper()
    pet = scraper.get_pet("迪莫")
    if pet:
        print(json.dumps(pet, ensure_ascii=False, indent=2))
