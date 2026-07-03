"""
综合精灵数据采集器
=================
整合三种数据源，按优先级自动选择：

1. BiliWiki 渲染采集（Selenium）— 最完整的实时数据
2. 种子数据（内置） — 离线可用的基础数据层
3. 补充来源（9game等）— 备用采集
"""

import logging
from typing import List, Optional, Dict, Set
from datetime import datetime

from ..models import Pet, PetStats
from ..seed_data import get_seed_pets, get_seed_skills
from .renderer import RenderedBiliWikiScraper, extract_pet_names_from_listing, close_driver

logger = logging.getLogger(__name__)


class IntegratedPetScraper:
    """
    综合精灵数据采集器。

    工作流程：
    1. 尝试从BiliWiki渲染获取数据
    2. 如果失败，回退到种子数据
    3. 支持多级回退，保证至少返回基础数据
    """

    def __init__(self):
        self.renderer = RenderedBiliWikiScraper()
        self.seed_pets = get_seed_pets()
        self.seed_pet_map = {p["name"]: p for p in self.seed_pets}

    def fetch_pet_list(self) -> Dict:
        """
        获取精灵列表。
        优先从BiliWiki渲染获取，失败使用种子数据。
        """
        try:
            logger.info("尝试从BiliWiki渲染获取精灵列表...")
            result = extract_pet_names_from_listing()
            if result and result.get("chinese_names"):
                logger.info(f"BiliWiki渲染成功: {len(result['chinese_names'])} 只")
                return result
            else:
                logger.info("BiliWiki渲染未获取到中文名，使用种子数据补充")
        except Exception as e:
            logger.warning(f"BiliWiki渲染失败: {e}")

        # 回退到种子数据
        logger.info(f"使用种子数据: {len(self.seed_pets)} 只精灵")
        return {
            "seed_pets": [p["name"] for p in self.seed_pets],
            "total_seed": len(self.seed_pets),
            "source": "seed",
        }

    def fetch_pet_detail(self, name: str) -> Optional[Dict]:
        """
        获取精灵详情。
        优先从BiliWiki渲染，失败使用种子数据。
        """
        # 尝试BiliWiki
        try:
            detail = self.renderer.get_pet_detail(name)
            if detail:
                return detail
        except Exception as e:
            logger.debug(f"BiliWiki渲染详情失败 [{name}]: {e}")

        # 回退到种子数据
        if name in self.seed_pet_map:
            seed = self.seed_pet_map[name]
            logger.info(f"使用种子数据: {name}")
            return seed

        logger.warning(f"未找到精灵数据: {name}")
        return None

    def fetch_all_pets(self, use_renderer: bool = False) -> Dict:
        """
        全量采集精灵数据。

        Args:
            use_renderer: 是否使用Selenium渲染（较慢但数据更全）

        Returns:
            {"pets": [...], "source": "...", ...}
        """
        result = {"fetched_at": datetime.now().isoformat()}

        # 获取列表
        list_result = self.fetch_pet_list()
        result["list_source"] = list_result.get("source", "unknown")

        # 获取精灵数据
        if use_renderer:
            # 从渲染页面获取中文名并爬取详情
            chinese_names = list_result.get("chinese_names", [])
            if chinese_names:
                pets = self.renderer.batch_get_details(chinese_names)
                result["pets"] = pets
                result["pets_count"] = len(pets)
                result["source"] = "biliwiki_rendered"
            else:
                # 使用种子数据
                result["pets"] = self.seed_pets
                result["pets_count"] = len(self.seed_pets)
                result["source"] = "seed"
        else:
            # 只使用种子数据
            result["pets"] = self.seed_pets
            result["pets_count"] = len(self.seed_pets)
            result["source"] = "seed"

        return result

    def close(self):
        """清理渲染器资源"""
        self.renderer.close()
