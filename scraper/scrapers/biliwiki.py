"""
BiliWiki 洛克王国世界 爬虫
=========================
采集目标：
1. 精灵图鉴（含属性、种族值、进化链、获取方式）
2. 技能数据库（含属性、威力、能耗、效果）
3. 属性克制表

B站BWIKI使用MediaWiki引擎，页面结构统一，便于结构化抽取。
"""

import re
import logging
from typing import List, Optional, Dict, Set

from bs4 import BeautifulSoup, Tag

from . import BaseScraper
from ..config import DATA_SOURCES, BILIWIKI_SELECTORS, OUTPUT_CONFIG
from ..models import (
    Pet, PetBase, PetStats, Skill,
    EvolutionInfo, PetListResponse, SkillListResponse,
)

logger = logging.getLogger(__name__)


class BiliWikiScraper(BaseScraper):
    """BiliWiki 洛克王国世界数据采集器"""

    def __init__(self):
        super().__init__(source_name="biliwiki")
        self.base_url = DATA_SOURCES["biliwiki"]["base"]

    # ================================================================
    # 宠物图鉴采集
    # ================================================================

    def fetch_pet_list(self) -> List[PetBase]:
        """
        从精灵图鉴列表页获取所有精灵的基础信息（编号、名称、属性链接）。
        返回 PetBase 列表，后续可据此抓取详情。
        """
        url = f"{self.base_url}/{DATA_SOURCES['biliwiki']['pet_list']}"
        logger.info(f"正在获取精灵列表: {url}")

        soup = self.fetch_page(url)
        if not soup:
            logger.error("无法获取精灵列表页面")
            return []

        pets = []
        seen_names: Set[str] = set()

        # 尝试多种表格选择器
        for selector in [
            "table.wikitable",
            "table.sortable",
            "table.table-bordered",
            "table",
        ]:
            # 查找所有表格
            for table in soup.select(selector):
                rows = table.select("tbody tr")
                if not rows:
                    continue

                for row in rows:
                    try:
                        pet = self._parse_pet_list_row(row)
                        if pet and pet.name and pet.name not in seen_names:
                            seen_names.add(pet.name)
                            pets.append(pet)
                    except Exception as e:
                        logger.debug(f"解析行失败: {e}")
                        continue

                if pets:
                    break  # 找到有数据的表格就停止

            if pets:
                break

        logger.info(f"采集到 {len(pets)} 只精灵")
        return pets

    def _parse_pet_list_row(self, row: Tag) -> Optional[PetBase]:
        """解析精灵列表的一行"""
        cells = row.select("td")
        if not cells:
            return None

        # 尝试提取精灵编号（通常在第一列）
        pet_id = None
        name = None
        element = None

        text_content = row.get_text(strip=True)

        # 尝试找名称和链接
        for cell in cells:
            link = cell.select_one("a")
            if link and link.get("title"):
                name_candidate = link.get("title").strip()
                # 跳过非精灵链接（如"编辑"、"刷新"等）
                if name_candidate and len(name_candidate) > 0 and name_candidate not in [
                    "编辑", "刷新", "删除",
                ]:
                    name = name_candidate
                    break

        if not name:
            # 如果title不行，用文本
            for cell in cells:
                text = cell.get_text(strip=True)
                if text and len(text) >= 2 and not text.isdigit():
                    name = text
                    break

        if not name:
            return None

        # 提取编号
        for cell in cells:
            text = cell.get_text(strip=True)
            if text.isdigit():
                pet_id = int(text)
                break

        # 提取属性标记（如果有图片或文字）
        elements = []
        for cell in cells:
            cell_text = cell.get_text(strip=True)
            for elem in ["火", "水", "草", "光", "暗", "龙", "冰", "电",
                          "地", "毒", "虫", "武", "翼", "萌", "幽", "恶",
                          "幻", "机械", "普通"]:
                if elem in cell_text and elem not in elements:
                    elements.append(elem)

        return PetBase(
            name=name,
            pet_id=pet_id or 0,
            element=elements if elements else None,
        )

    # ================================================================
    # 精灵详情采集
    # ================================================================

    def fetch_pet_detail(self, pet_name: str) -> Optional[Pet]:
        """
        抓取单个精灵的详细数据。
        根据精灵名称拼接URL并解析详情页。
        """
        # URL编码处理
        import urllib.parse
        encoded_name = urllib.parse.quote(pet_name)
        url = f"{self.base_url}/{encoded_name}"
        logger.info(f"正在获取精灵详情: {url}")

        soup = self.fetch_page(url)
        if not soup:
            # 尝试备用URL格式
            url = f"{self.base_url}/wiki/{encoded_name}"
            soup = self.fetch_page(url)
            if not soup:
                logger.warning(f"无法获取精灵详情: {pet_name}")
                return None

        try:
            pet = self._parse_pet_detail(soup, pet_name, url)
            return pet
        except Exception as e:
            logger.error(f"解析精灵详情失败 [{pet_name}]: {e}")
            return None

    def _parse_pet_detail(self, soup: BeautifulSoup, pet_name: str, url: str) -> Optional[Pet]:
        """解析精灵详情页面"""
        # 基本信息
        elements = self._extract_elements(soup)
        rarity = self._extract_rarity(soup)

        # 种族值
        stats = self._extract_stats(soup)

        # 可学技能
        skills = self._extract_skills_from_detail(soup)

        # 进化信息
        evolution = self._extract_evolution(soup)

        # 获取方式
        obtain = self._extract_obtain_method(soup)

        # 描述
        description = self._extract_description(soup)

        return Pet(
            name=pet_name,
            element=elements,
            rarity=rarity,
            stats=stats,
            skills=skills,
            evolution=evolution,
            obtain_method=obtain,
            description=description,
            source_url=url,
        )

    def _extract_elements(self, soup: BeautifulSoup) -> Optional[List[str]]:
        """从详情页提取精灵属性"""
        elements = []

        # 尝试多种选择器模式匹配属性
        patterns = [
            "td:contains('属性') + td",
            "th:contains('属性') + td",
            "td:has(> b:contains('属性')) + td",
            "th:contains('属性') ~ td",
        ]

        for pattern in patterns:
            try:
                cells = soup.select(pattern)
                for cell in cells:
                    text = cell.get_text(strip=True)
                    for elem in [
                        "火", "水", "草", "光", "普通", "机械", "地", "冰",
                        "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "幻",
                    ]:
                        if elem in text and elem not in elements:
                            elements.append(elem)
            except Exception:
                continue

        # 如果上面找不到，从infobox图片alt文本提取
        if not elements:
            for img in soup.select("img[alt*='属性']"):
                alt = img.get("alt", "")
                match = re.search(r"(火|水|草|光|普通|机械|地|冰|龙|电|毒|虫|武|翼|萌|幽|恶|幻)", alt)
                if match and match.group(1) not in elements:
                    elements.append(match.group(1))

        return elements if elements else None

    def _extract_rarity(self, soup: BeautifulSoup) -> Optional[str]:
        """提取稀有度"""
        patterns = [
            "td:contains('稀有度') + td",
            "th:contains('稀有度') + td",
            "td:contains('稀有') + td",
            "th:contains('稀有') + td",
        ]
        for pattern in patterns:
            try:
                cell = soup.select_one(pattern)
                if cell:
                    text = cell.get_text(strip=True)
                    if text:
                        return text
            except Exception:
                continue
        return None

    def _extract_stats(self, soup: BeautifulSoup) -> Optional[PetStats]:
        """提取种族值"""
        # 查找种族值表格
        stat_table = None
        for selector in [
            "table.basic-stats",
            "table:has(td:contains('种族值'))",
            "table:has(th:contains('种族值'))",
            "table.wikitable:has(td:contains('生命'))",
        ]:
            stat_table = soup.select_one(selector)
            if stat_table:
                break

        if not stat_table:
            # 尝试从行内文本提取
            return self._extract_stats_from_text(soup)

        stats = {}
        for row in stat_table.select("tr"):
            cells = row.select("td, th")
            texts = [cell.get_text(strip=True) for cell in cells]

            for i, text in enumerate(texts):
                stat_name = None
                if "生命" in text or "精力" in text:
                    stat_name = "hp"
                elif "物攻" in text:
                    stat_name = "attack"
                elif "物防" in text or "防御" in text:
                    stat_name = "defense"
                elif "魔攻" in text:
                    stat_name = "magic_attack"
                elif "魔防" in text:
                    stat_name = "magic_defense"
                elif "速度" in text:
                    stat_name = "speed"

                if stat_name and i + 1 < len(texts):
                    value = self.extract_numbers(texts[i + 1])
                    if value is not None:
                        stats[stat_name] = value

        if not stats:
            return None

        total = sum(v for v in stats.values() if v is not None)
        return PetStats(
            hp=stats.get("hp"),
            attack=stats.get("attack"),
            defense=stats.get("defense"),
            magic_attack=stats.get("magic_attack"),
            magic_defense=stats.get("magic_defense"),
            speed=stats.get("speed"),
            total=total,
        )

    def _extract_stats_from_text(self, soup: BeautifulSoup) -> Optional[PetStats]:
        """从页面文本中提取种族值"""
        page_text = soup.get_text()
        stats = {}

        patterns = [
            (r"生命[值力]*[：:]\s*(\d+)", "hp"),
            (r"精力[：:]\s*(\d+)", "hp"),
            (r"物攻[：:]\s*(\d+)", "attack"),
            (r"物防[：:]\s*(\d+)", "defense"),
            (r"防御[：:]\s*(\d+)", "defense"),
            (r"魔攻[：:]\s*(\d+)", "magic_attack"),
            (r"魔防[：:]\s*(\d+)", "magic_defense"),
            (r"速度[：:]\s*(\d+)", "speed"),
        ]

        for pattern, key in patterns:
            match = re.search(pattern, page_text)
            if match:
                stats[key] = int(match.group(1))

        if not stats:
            return None

        total = sum(stats.values())
        return PetStats(
            hp=stats.get("hp"),
            attack=stats.get("attack"),
            defense=stats.get("defense"),
            magic_attack=stats.get("magic_attack"),
            magic_defense=stats.get("magic_defense"),
            speed=stats.get("speed"),
            total=total,
        )

    def _extract_skills_from_detail(self, soup: BeautifulSoup) -> List[Skill]:
        """从精灵详情页提取可学技能"""
        skills = []

        # 查找技能表格
        skill_tables = soup.select("table:has(th:contains('技能'))")
        if not skill_tables:
            skill_tables = soup.select("table.wikitable")

        for table in skill_tables:
            if not any("技能" in th.get_text() for th in table.select("th")):
                continue

            rows = table.select("tbody tr")
            for row in rows:
                cells = row.select("td")
                if len(cells) < 3:
                    continue

                try:
                    texts = [cell.get_text(strip=True) for cell in cells]
                    name = texts[0] if len(texts) > 0 else ""
                    element = texts[1] if len(texts) > 1 else None
                    category = texts[2] if len(texts) > 2 else None

                    power = None
                    cost = None
                    if len(texts) > 3:
                        power = self.extract_numbers(texts[3])
                    if len(texts) > 4:
                        cost = self.extract_numbers(texts[4])

                    effect = texts[-1] if len(texts) > 5 else None

                    if name and len(name) < 20:
                        skill = Skill(
                            name=name,
                            element=element,
                            category=category,
                            power=power,
                            cost=cost,
                            effect=effect,
                        )
                        skills.append(skill)

                except Exception as e:
                    logger.debug(f"解析技能行失败: {e}")
                    continue

        return skills

    def _extract_evolution(self, soup: BeautifulSoup) -> Optional[EvolutionInfo]:
        """提取进化信息"""
        # 查找进化相关表格或文本
        page_text = soup.get_text()

        # 模式：A → B
        match = re.search(r"([一-鿿]+)\s*[→➜>]\s*([一-鿿]+)", page_text)
        if match:
            return EvolutionInfo(
                from_form=match.group(1),
                to_form=match.group(2),
            )

        # 模式："XX级进化"
        match = re.search(r"(\d+)\s*级\s*进化[为成]\s*([一-鿿]+)", page_text)
        if match:
            return EvolutionInfo(
                condition=f"{match.group(1)}级进化",
                to_form=match.group(2),
            )

        return None

    def _extract_obtain_method(self, soup: BeautifulSoup) -> Optional[str]:
        """提取获取方式"""
        patterns = [
            r"获取[方式途径来源：:]\s*(.+?)[。\n]",
            r"获得[方式途径来源：:]\s*(.+?)[。\n]",
            r"捕捉[地点：:]\s*(.+?)[。\n]",
            r"出处[：:]\s*(.+?)[。\n]",
        ]

        page_text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, page_text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """提取精灵描述"""
        # 查找描述段落
        for selector in [
            "div.description",
            "p.description",
            "td:contains('描述') + td",
            ".desc",
            ".summary",
        ]:
            elem = soup.select_one(selector)
            if elem:
                text = self.clean_text(elem.get_text())
                if text and len(text) > 5:
                    return text
        return None

    # ================================================================
    # 技能数据库采集
    # ================================================================

    def fetch_skill_list(self) -> List[Skill]:
        """
        从技能查询页面采集所有技能数据。
        返回完整技能列表。
        """
        url = f"{self.base_url}/{DATA_SOURCES['biliwiki']['skill_list']}"
        logger.info(f"正在获取技能列表: {url}")

        soup = self.fetch_page(url)
        if not soup:
            logger.error("无法获取技能列表页面")
            return []

        skills = []
        seen_skills: Set[str] = set()

        for table in soup.select("table.wikitable, table.sortable"):
            rows = table.select("tbody tr")
            for row in rows:
                try:
                    skill = self._parse_skill_row(row)
                    if skill and skill.name not in seen_skills:
                        seen_skills.add(skill.name)
                        skills.append(skill)
                except Exception as e:
                    logger.debug(f"解析技能行失败: {e}")
                    continue

        logger.info(f"采集到 {len(skills)} 个技能")
        return skills

    def _parse_skill_row(self, row: Tag) -> Optional[Skill]:
        """解析技能表格中的一行"""
        cells = row.select("td")
        if not cells:
            return None

        texts = [cell.get_text(strip=True) for cell in cells]

        # 至少要有名称
        name = texts[0] if len(texts) > 0 else ""
        if not name or len(name) > 20:
            return None

        element = texts[1] if len(texts) > 1 else None
        category = texts[2] if len(texts) > 2 else None
        power = self.extract_numbers(texts[3]) if len(texts) > 3 else None
        cost = self.extract_numbers(texts[4]) if len(texts) > 4 else None
        effect = texts[5] if len(texts) > 5 else None

        return Skill(
            name=name,
            element=element,
            category=category,
            power=power,
            cost=cost,
            effect=effect,
            source_url=f"{self.base_url}/{DATA_SOURCES['biliwiki']['skill_list']}",
        )

    # ================================================================
    # 批量采集
    # ================================================================

    def scrape(
        self,
        include_pets: bool = True,
        include_skills: bool = True,
        include_details: bool = False,
        max_pets: Optional[int] = None,
    ) -> Dict:
        """
        全量数据采集入口。

        Args:
            include_pets: 是否采集精灵列表
            include_skills: 是否采集技能列表
            include_details: 是否采集每只精灵的详情（较慢）
            max_pets: 最多采集多少只精灵的详情（None为全部）

        Returns:
            {
                "pets": [...],
                "skills": [...],
                "pet_details": [...],  # 仅当 include_details=True
            }
        """
        result = {}

        # 采采集精灵列表
        if include_pets:
            pets = self.fetch_pet_list()
            result["pets"] = [p.model_dump() for p in pets]
            result["pets_count"] = len(pets)

            # 采集详情（可选）
            if include_details:
                detail_limit = max_pets or len(pets)
                details = []
                for i, pet in enumerate(pets[:detail_limit]):
                    logger.info(f"采集详情 [{i+1}/{detail_limit}]: {pet.name}")
                    detail = self.fetch_pet_detail(pet.name)
                    if detail:
                        details.append(detail.model_dump())
                result["pet_details"] = details
                result["pet_details_count"] = len(details)

        # 采集技能列表
        if include_skills:
            skills = self.fetch_skill_list()
            result["skills"] = [s.model_dump() for s in skills]
            result["skills_count"] = len(skills)

        return result
