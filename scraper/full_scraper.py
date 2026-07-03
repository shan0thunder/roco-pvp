#!/usr/bin/env python3
"""
BiliWiki 全量精灵采集器
========================
从 BiliWiki 采集所有精灵的完整数据（名称、属性、种族值、技能、图片）。

工作流程:
  1. 访问 BiliWiki 精灵列表页，获取所有精灵的 pinyin 名和中文名
  2. 构建 pinyin→中文→图片 映射
  3. 逐个访问精灵详情页，提取属性、种族值、技能
  4. 输出为产品数据格式

使用方式:
  python scraper/full_scraper.py
  python scraper/full_scraper.py --max 50        # 仅采集前50只
  python scraper/full_scraper.py --resume         # 从上次中断处继续
"""

import sys
import os
import json
import time
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup

# 项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 已知的 18 种属性
ALL_ELEMENTS = {"火", "水", "草", "光", "普通", "机械", "地", "冰",
                "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "幻"}

# stat 名映射
STAT_MAP = {
    "生命": "hp", "体力": "hp", "精力": "hp",
    "物攻": "attack", "攻击": "attack",
    "物防": "defense", "防御": "defense",
    "魔攻": "magic_attack",
    "魔防": "magic_defense",
    "速度": "speed",
}

# 需要跳过的变体关键词
SKIP_VARIANTS = ["异色", "首领化"]


class FullScraper:
    """全量 BiliWiki 爬虫"""

    BASE = "https://wiki.biligame.com/rocom"

    def __init__(self, delay: float = 0.3):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": f"{self.BASE}/",
        })
        self.delay = delay
        self._cache: Dict[str, BeautifulSoup] = {}

    # ================================================================
    # Step 1: 获取精灵列表（含图片）
    # ================================================================
    def get_all_pets(self) -> List[Dict]:
        """从列表页获取所有精灵"""
        url = f"{self.BASE}/%E7%B2%BE%E7%81%B5%E5%9B%BE%E9%89%B4"
        resp = self.session.get(url, timeout=30)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'lxml')

        entries = []
        seen_pinyin = set()

        for a in soup.select('a[title]'):
            title = a.get('title', '').strip()
            href = a.get('href', '')
            img = a.select_one('img[alt*="JL "]')
            if not img or not title:
                continue

            # Extract page name from href
            if '/rocom/' not in href:
                continue
            page_name = href.split('/rocom/')[-1].split('/')[0].split('#')[0]
            # URL decode
            decoded_name = requests.utils.unquote(page_name)

            src = img.get('src', '')
            alt = img.get('alt', '')
            if '/thumb/' not in src or 'px-JL_' not in src:
                continue

            # Pinyin from alt (for dedup)
            pinyin = alt.replace('JL ', '').replace('.png', '').strip()
            if not pinyin or pinyin in seen_pinyin:
                continue
            seen_pinyin.add(pinyin)

            # 跳过变体（主形态优先）
            is_variant = any(v in title for v in SKIP_VARIANTS)
            if is_variant:
                continue

            # Clean Chinese name: remove (xxx) 后缀
            clean_name = re.sub(r'[（(][^）)]*[）)]', '', title).strip()

            # Image URL
            no_thumb = src.replace('/thumb/', '/')
            last_slash = no_thumb.rfind('/')
            img_url = no_thumb[:last_slash] if last_slash > 0 else ''

            entries.append({
                "pinyin": pinyin,
                "title": title,
                "name": clean_name,
                "page_name": decoded_name,  # BiliWiki URL name
                "image": img_url,
            })

        logger.info(f"列表页获取到 {len(entries)} 只精灵")
        return entries

    # ================================================================
    # Step 2: 爬取精灵详情
    # ================================================================
    def fetch_detail(self, page_name: str, max_retries: int = 3) -> Optional[Dict]:
        """爬取单个精灵详情，带限流重试"""
        import urllib.parse
        url = f"{self.BASE}/{urllib.parse.quote(page_name)}"

        for attempt in range(max_retries):
            try:
                resp = self.session.get(url, timeout=15)

                # 限流处理
                if resp.status_code in (429, 503, 567):
                    wait = 5 * (attempt + 1)
                    logger.warning(f"限流 (HTTP {resp.status_code})，等待 {wait}s...")
                    time.sleep(wait)
                    # 换 UA
                    ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/{537.36 + attempt}"
                    self.session.headers.update({"User-Agent": ua})
                    continue

                if resp.status_code == 404:
                    return None

                resp.raise_for_status()
                resp.encoding = 'utf-8'
                break

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait = 3 * (attempt + 1)
                    logger.debug(f"重试 [{attempt+1}/{max_retries}] {wait}s: {e}")
                    time.sleep(wait)
                else:
                    logger.warning(f"请求失败 [{pinyin}]: {e}")
                    return None
        else:
            return None

        soup = BeautifulSoup(resp.text, 'lxml')
        data = {}

        # 名称
        title_el = soup.select_one("h1#firstHeading")
        page_name = title_el.get_text(strip=True) if title_el else pinyin

        # ---- 属性 ----
        elements = []
        for el in soup.select(".sprite_type"):
            text = el.get_text(strip=True)
            for elem in ALL_ELEMENTS:
                if elem in text and elem not in elements:
                    elements.append(elem)
        if elements:
            data["element"] = elements

        # ---- 种族值 ----
        stats = {}
        for attr in soup.select(".sprite-info-attr"):
            name_el = attr.select_one(".sprite-info-attrname")
            num_el = attr.select_one(".sprite-info-attrnum")
            if not name_el or not num_el:
                continue
            name_span = name_el.find("span")
            name = name_span.get_text(strip=True) if name_span else name_el.get_text(strip=True)
            name = name.rstrip(":：")
            num = num_el.get_text(strip=True)
            field = STAT_MAP.get(name)
            if field and num.isdigit():
                stats[field] = int(num)

        total_el = soup.select_one(".sprite-info-attrsum")
        if total_el:
            m = re.search(r"(\d+)", total_el.get_text(strip=True))
            if m:
                stats["total"] = int(m.group(1))
        elif stats:
            stats["total"] = sum(v for v in stats.values())
        if stats:
            data["stats"] = stats

        # ---- 描述 ----
        for sel in [".sprite-info-desc", ".detail-des"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                data["description"] = el.get_text(strip=True)
                break

        # ---- 技能 ----
        skills = []
        for card in soup.select(".skill-single"):
            skill = self._parse_skill(card)
            if skill:
                skills.append(skill)
        if skills:
            data["skills"] = skills
            data["skills_count"] = len(skills)

        return {
            "name": page_name,
            **data,
            "source_url": url,
            "updated_at": datetime.now().isoformat(),
        }

    def _parse_skill(self, card) -> Optional[Dict]:
        """解析技能卡片"""
        name_el = card.select_one(".skill-name")
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name:
            return None

        category = card.get("data-param2", "") or ""
        element = card.get("data-param3", "") or ""

        cost = None
        cost_el = card.select_one(".imgtext-row span:last-child")
        if cost_el and cost_el.get_text(strip=True).isdigit():
            cost = int(cost_el.get_text(strip=True))

        power = None
        if category in ("物攻", "魔攻"):
            typelist = card.select_one(".skill-head-typelist")
            if typelist:
                spans = typelist.find_all("span", recursive=False)
                if len(spans) >= 8 and spans[7].get_text(strip=True).isdigit():
                    power = int(spans[7].get_text(strip=True))

        effect = None
        for sel in [".skill-desc-atk", ".skill-desc"]:
            el = card.select_one(sel)
            if el and el.get_text(strip=True):
                effect = el.get_text(strip=True)
                break

        source = None
        src_el = card.select_one(".skill-source")
        if src_el and src_el.get_text(strip=True):
            source = src_el.get_text(strip=True)

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
    # Step 3: 全量采集管线
    # ================================================================
    def run(self, max_pets: int = None, resume_file: str = None,
            batch_size: int = 30, checkpoint: str = None) -> List[Dict]:
        """执行全量采集，分批进行，支持断点续传"""
        # 获取列表
        all_pets = self.get_all_pets()
        if max_pets:
            all_pets = all_pets[:max_pets]

        logger.info(f"开始采集 {len(all_pets)} 只精灵（每批 {batch_size} 只）...")

        # 恢复状态
        results = []
        done_names = set()
        if checkpoint and os.path.exists(checkpoint):
            with open(checkpoint, 'r', encoding='utf-8') as f:
                results = json.load(f)
            done_names = {p.get("name", "") for p in results}
            logger.info(f"从检查点恢复: 已有 {len(done_names)} 只")

        total = len(all_pets)
        request_count = 0

        for i, entry in enumerate(all_pets):
            name = entry.get("name", "")
            page_name = entry.get("page_name", name)

            if name in done_names:
                continue

            logger.info(f"[{i+1}/{total}] {name}")
            detail = self.fetch_detail(page_name)

            if detail:
                if entry.get("image") and not detail.get("image"):
                    detail["image"] = entry["image"]
                results.append(detail)
                logger.info(f"  ✅ {len(detail.get('skills', []))} 技能")
            else:
                # 列表信息保底
                results.append({
                    "name": name,
                    "image": entry.get("image", ""),
                })
                logger.info(f"  ⚠️ 详情不可用，保存基础信息")

            request_count += 1

            # 每批完成后保存检查点 + 暂停
            if request_count > 0 and request_count % batch_size == 0:
                if checkpoint:
                    with open(checkpoint, 'w', encoding='utf-8') as f:
                        json.dump(results, f, ensure_ascii=False)
                    logger.info(f"💾 检查点保存: {len(results)} 只")
                logger.info(f"⏸️ 暂停 8 秒避免限流...")
                time.sleep(8)

            time.sleep(self.delay)

        # 最终保存检查点
        if checkpoint:
            with open(checkpoint, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False)

        return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BiliWiki 全量精灵采集器")
    parser.add_argument("--max", type=int, default=None, help="最多采集数")
    parser.add_argument("--resume", action="store_true", help="从上次中断处继续")
    parser.add_argument("--output", default="data/product/product_data.json", help="输出路径")
    parser.add_argument("--delay", type=float, default=0.3, help="请求间隔（秒）")
    args = parser.parse_args()

    from scraper.storage.json_storage import JsonStorage
    from scraper.config import OUTPUT_CONFIG

    # 检查点路径
    checkpoint = "data/.scraper_checkpoint.json"
    if not args.resume:
        if os.path.exists(checkpoint):
            os.remove(checkpoint)
            logger.info("已清除旧检查点")

    # 全量采集
    scraper = FullScraper(delay=args.delay)
    all_pets = scraper.run(max_pets=args.max, checkpoint=checkpoint, resume_file=checkpoint)

    # 过滤无效项
    valid_pets = [p for p in all_pets if p.get("skills") or p.get("element")]
    logger.info(f"\n有效精灵: {len(valid_pets)}/{len(all_pets)}")

    # 保存到 storage
    storage = JsonStorage()
    storage.save(valid_pets, OUTPUT_CONFIG["pets_file"])
    logger.info(f"已保存 {len(valid_pets)} 只到 {OUTPUT_CONFIG['pets_file']}")

    # 导出产品数据
    from scraper.product_exporter import export_product_data, print_product_summary
    export_path = export_product_data()
    print_product_summary(export_path)

    # 验证图片覆盖
    with open(export_path, 'r', encoding='utf-8') as f:
        product = json.load(f)
    with_img = sum(1 for p in product.get("pets", []) if p.get("image"))
    logger.info(f"有图精灵: {with_img}/{len(product.get('pets', []))}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    main()
