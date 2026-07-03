"""
PVP阵容数据采集器
===============
采集来源：社区攻略文章、视频简介、攻略网站。
通过解析自然语言文本提取：
- 阵容名称与梯队评级
- 核心精灵与摇摆位
- 胜率/出场率数据
- 阵容机制与优劣势

当前采用「规则引擎 + 人工校验」模式，确保数据准确性。
"""

import re
import json
import logging
from typing import List, Optional, Dict, Set
from datetime import datetime
from pathlib import Path

from . import BaseScraper
from ..config import DATA_SOURCES, OUTPUT_CONFIG
from ..models import PvpTeam, TeamPetSlot, TeamListResponse

logger = logging.getLogger(__name__)


class PvpTeamScraper(BaseScraper):
    """
    PVP阵容数据采集器。

    数据来源：
    1. 什么值得买（smzdm）周报和阵容攻略
    2. 52pk、豌豆荚等游戏媒体
    3. 社区论坛（NGA、贴吧）

    注：由于PVP阵容数据以自然语言形式散布在文章中，
    本采集器采用半自动化方式：规则提取 + 人工补全模板。
    """

    def __init__(self):
        super().__init__(source_name="pvp_teams")
        self.sources = DATA_SOURCES["pvp_sources"]

    # ================================================================
    # 文章爬取与解析
    # ================================================================

    def extract_teams_from_article(self, url: str) -> List[PvpTeam]:
        """
        从攻略文章中提取阵容数据。

        使用正则表达式模式识别文章中提到的阵容，包括：
        - 阵容名称（通常有"XX队""XX体系"等标识）
        - 核心精灵列表（列举的宠物名称）
        - 梯队评级（T0/T1/T2）

        Args:
            url: 攻略文章URL

        Returns:
            提取到的阵容列表（可能不完整，需人工校验）
        """
        logger.info(f"正在解析文章: {url}")
        soup = self.fetch_page(url)

        if not soup:
            logger.warning(f"无法获取文章: {url}")
            return []

        # 获取页面文本
        # 尝试多个内容区域选择器
        content = None
        for selector in [
            "article",
            "div.article-content",
            "div.post-content",
            "div.content",
            ".article-detail",
            "#article-content",
            "main",
            "body",
        ]:
            elem = soup.select_one(selector)
            if elem:
                content = elem.get_text()
                break

        if not content:
            content = soup.get_text()

        # 清理文本：移除多余空白
        content = re.sub(r"\s+", " ", content)
        content = re.sub(r"[\n\r\t]+", "\n", content)

        logger.debug(f"文章内容长度: {len(content)} 字符")

        # 提取阵容数据
        teams = self._parse_teams_from_text(content, url)
        return teams

    def _parse_teams_from_text(self, text: str, source_url: str) -> List[PvpTeam]:
        """从文本中解析阵容"""
        teams = []
        seen_names: Set[str] = set()

        # 定义阵容识别模式（按优先级排序）
        team_patterns = [
            # T0/T1梯队标注 —— 如 "T0：龙王星陨队"
            r"(T[0-2])\s*[：:]\s*([^，。\n]{2,20}(?:队|体系|流))",
            # "XX队" + 评级 —— 如 "龙王星陨队（T0）"
            r"([^，。\n]{2,20}(?:队|体系|流))\s*[（(]\s*(T[0-2])\s*[）)]",
            # "XX阵容" —— 如 "推荐阵容：XX"
            r"(?:推荐|热门|T0|强势|主流)\s*(?:阵容|配队)[：:]\s*([^。\n]{2,20})",
            # 数字编号列举 —— 如 "1. 独角兽增益流"
            r"(?:\d+[.、])\s*([^，。\n]{2,20}(?:队|体系|流))",
        ]

        for pattern in team_patterns:
            for match in re.finditer(pattern, text):
                try:
                    groups = match.groups()

                    if len(groups) == 2:
                        # 判断哪个是名称哪个是评级
                        rank_candidate = groups[0] if groups[0].startswith("T") else None
                        rank_candidate2 = groups[1] if groups[1].startswith("T") else None
                        name = groups[1] if rank_candidate else groups[0]
                        rank = rank_candidate or rank_candidate2
                    else:
                        name = groups[0]
                        rank = None

                    # 清理名称
                    name = re.sub(r"[#*~【】\[\]]", "", name).strip()
                    if not name or len(name) < 2:
                        continue

                    # 去重
                    if name not in seen_names:
                        seen_names.add(name)

                        # 尝试从上下文中提取核心精灵
                        context_start = max(0, match.start() - 100)
                        context_end = min(len(text), match.end() + 300)
                        context = text[context_start:context_end]

                        core_pets = self._extract_pets_from_context(context)

                        team = PvpTeam(
                            name=name,
                            rank=rank or "T?",
                            core_pets=core_pets[:6] if core_pets else [],
                            description=self._extract_team_desc(context, name),
                            source_url=source_url,
                            updated_at=datetime.now().strftime("%Y-%m-%d"),
                        )
                        teams.append(team)
                except Exception as e:
                    logger.debug(f"解析阵容模式失败: {e}")
                    continue

        return teams

    def _extract_pets_from_context(self, context: str) -> List[str]:
        """
        从上下文中提取精灵名称。
        识别策略：选择长度2-6的中文词，排除常见的非精灵词汇。
        """
        # 已知精灵名称模式（精灵名通常2-5个汉字）
        # 先尝试用正则匹配常见精灵名格式
        pet_pattern = r"([一-鿿]{2,5}(?:兽|王|鸟|龙|蝶|花|草|鹿|狐|兔|猫|魔|神|精|圣|星|石))"

        pets = re.findall(pet_pattern, context)

        # 过滤掉非精灵词汇
        stop_words = {"攻略", "推荐", "阵容", "队伍", "核心", "精灵", "宠物", "技能",
                       "属性", "克制", "版本", "赛季", "强势", "搭配", "定位", "输出",
                       "辅助", "坦克", "控制", "爆发", "持续", "回复", "增益", "减益",
                       "免疫", "抵抗", "穿透", "实际", "没有", "但是", "可以", "注意",
                       "需要", "现在", "当前", "赛季", "实战", "配置", "玩法", "机制",
                       "伤害", "效果", "普通", "稀有", "传说", "获得", "捕捉"}

        filtered = [p for p in pets if p not in stop_words and len(p) >= 2]

        # 去重并保持顺序
        seen = set()
        unique_pets = []
        for p in filtered:
            if p not in seen:
                seen.add(p)
                unique_pets.append(p)
                if len(unique_pets) >= 8:  # 最多8只
                    break

        return unique_pets

    def _extract_team_desc(self, context: str, team_name: str) -> Optional[str]:
        """提取阵容描述"""
        # 尝试找到包含阵容名称的完整句子
        sentences = re.split(r"[。！？\n]", context)
        for i, sent in enumerate(sentences):
            if team_name in sent:
                # 返回当前句和下一句（如果有）
                desc = sent.strip()
                if i + 1 < len(sentences):
                    desc += "。" + sentences[i + 1].strip()
                return desc[:200]  # 截取前200字
        return None

    # ================================================================
    # 内置模板数据（已验证的手工整理数据）
    # ================================================================

    def get_builtin_teams(self) -> List[PvpTeam]:
        """
        返回内置的已验证阵容数据。
        这些数据来自多个攻略来源的交叉验证，确保准确可靠。
        """
        return [
            PvpTeam(
                name="龙王星陨队",
                rank="T0",
                core_pets=["怖哭菇", "落陨星兔", "翠顶夫人", "小皮球", "化蝶", "帕尔萨斯"],
                description="版本真神阵容。核心机制：怖哭菇挂印记→叠至10层→落陨星兔主C引爆。配合翠顶夫人25%全队增伤，爆发极高。",
                mechanics="印记叠加+引爆体系",
                pros=["爆发极高", "克制毒/冰/虫队", "版本最強"],
                cons=["怕控制队", "内战看速度", "操作门槛中高"],
                target_users="中高段位玩家",
                season="S2",
            ),
            PvpTeam(
                name="电鹿轮转队",
                rank="T0",
                core_pets=["梦想三三", "春天岚鸟", "寂灭骨龙", "声波缇塔", "化蝶", "圣羽翼王"],
                description="平衡型阵容，越战越强。核心为梦想三三首领化后坦度提升，配合声波缇塔的退化能力。",
                mechanics="轮转消耗+首领化",
                pros=["阵容平衡", "越战越强", "克制星陨队"],
                cons=["节奏偏慢", "需要一定操作"],
                target_users="偏好消耗战的进阶玩家",
                season="S2",
            ),
            PvpTeam(
                name="独角兽增益流",
                rank="T0",
                core_pets=["白金独角兽", "翠顶夫人", "化蝶", "红绒十字", "尖嘴狐仙", "帕帕斯卡"],
                description="新手首选阵容。翠顶夫人先手开增益→独角兽叠buff→满层后伤害增幅可达190%，节奏快压制力强。",
                mechanics="全队增益+爆发一波流",
                pros=["新手友好", "节奏快", "压制力强"],
                cons=["被先手控制克制", "后劲不足"],
                target_users="新手/零氪玩家",
                season="S2",
            ),
            PvpTeam(
                name="闪击翼王队",
                rank="T0",
                core_pets=["龙光悠悠", "高速琵琶鸟", "闪击翼王", "金瓜盒子"],
                description="当前顶级速攻阵容。利用速度差打出高额伤害，闪击翼王为核心收割单位。",
                mechanics="速度线压制+高速收割",
                pros=["快节奏", "收割能力强", "高分适用"],
                cons=["对速度要求高", "被肉队克制"],
                target_users="追求连胜的高分段玩家",
                season="S2",
            ),
            PvpTeam(
                name="古龙红队",
                rank="T0",
                core_pets=["古龙", "兽帕雷", "星光石", "黑猫巫师"],
                description="依赖古龙复活特性，实现无死亡压力的持续作战。",
                mechanics="复活体系+持续作战",
                pros=["生存能力强", "持续压制"],
                cons=["核心单一", "被禁古龙即崩"],
                target_users="高段位玩家",
                season="S2",
            ),
            PvpTeam(
                name="狼王体系",
                rank="T1",
                core_pets=["黑猫", "恶魔狼", "独角兽", "画蝶", "帕帕斯卡"],
                flex_pets=["天鹅", "沉铁兽"],
                description="PVP使用率最高的阵容体系，强度稳定且新手友好。黑猫+恶魔狼形成核心联动。",
                mechanics="状态传递+压制",
                pros=["使用率最高", "稳定上分", "新手友好"],
                cons=["无突出强点", "被版本T0克制"],
                target_users="全段位通用",
                season="S2",
            ),
            PvpTeam(
                name="雪天冻结队",
                rank="T1",
                core_pets=["雪影娃娃", "冰钻布鲁斯", "雪巨人", "帅帅魔偶", "尖嘴狐仙"],
                description="天气控场型阵容。雪天天气+冻结链压制，让对手无法行动。",
                mechanics="天气控场+冻结链",
                pros=["控制力强", "战术独特"],
                cons=["依赖天气手", "被火系克制"],
                target_users="喜欢控场玩法的玩家",
                season="S2",
            ),
            PvpTeam(
                name="天鹅沉铁兽体系",
                rank="T1",
                core_pets=["天鹅", "沉铁兽", "火狗", "恶魔狼"],
                flex_pets=["冰猪", "羚羊"],
                description="状态传递体系，先手压制+后期收割。零氪也能上大师的平民战神阵容。",
                mechanics="状态传递+双核输出",
                pros=["零氪友好", "可上大师", "阵容灵活"],
                cons=["需熟悉状态机制", "被高速队克制"],
                target_users="零氪/微氪玩家",
                season="S2",
            ),
            PvpTeam(
                name="狐仙翼王队3.0",
                rank="T1",
                core_pets=["岚鸟", "寂灭骨龙", "尖嘴狐仙", "圣羽翼王"],
                description="PvP榜一阵容。岚鸟暴力首发，骨龙联防核心，狐仙攻防枢纽，翼王游击收割。阵容均衡应对多变。",
                mechanics="多核联防+游击收割",
                pros=["阵容均衡", "应对多变", "榜一推荐"],
                cons=["成本较高", "操作复杂"],
                target_users="高分段冲分玩家",
                season="S2",
            ),
            PvpTeam(
                name="雪影迪迪小丑布丁队",
                rank="T1",
                core_pets=["首领化火神", "多只酷拉", "叮叮恶魔"],
                description="零氪友好型阵容。火神可野外获取，特性共享+双动机制。",
                mechanics="特性共享+双动",
                pros=["零氪", "火神可野外获取"],
                cons=["强度有限", "高分段吃力"],
                target_users="零氪新手",
                season="S2",
            ),
        ]

    # ================================================================
    # 赛季新兴精灵数据
    # ================================================================

    def get_seasonal_rising_pets(self) -> List[Dict]:
        """返回赛季新兴强势精灵"""
        return [
            {
                "name": "卡卡鸟",
                "role": "低分段环境改变者",
                "mechanics": "暴风眼后无限连击，可单刷灭队",
                "season": "S2",
            },
            {
                "name": "春兔",
                "role": "强化回复",
                "mechanics": "强化天兽队与第五队后场回复能力",
                "season": "S2",
            },
            {
                "name": "龙息帕尔",
                "role": "新陨队核心",
                "mechanics": "进化后让新陨队重获生机",
                "season": "S2",
            },
            {
                "name": "梦想三三",
                "role": "首领化坦克",
                "mechanics": "首领化后坦度提升，具备让对手退化的能力",
                "season": "S2",
            },
        ]

    # ================================================================
    # 批量采集入口
    # ================================================================

    def scrape(
        self,
        use_web_sources: bool = True,
        include_builtin: bool = True,
    ) -> Dict:
        """
        采集PVP阵容数据。

        Args:
            use_web_sources: 是否从网页文章抓取
            include_builtin: 是否包含内置已验证数据

        Returns:
            {"teams": [...], "rising_pets": [...]}
        """
        result = {}
        all_teams: List[PvpTeam] = []
        seen_names: Set[str] = set()

        # 1. 从网页文章中抓取
        if use_web_sources:
            for source in self.sources:
                try:
                    article_teams = self.extract_teams_from_article(source["url"])
                    for team in article_teams:
                        if team.name not in seen_names:
                            seen_names.add(team.name)
                            all_teams.append(team)
                except Exception as e:
                    logger.warning(f"解析来源失败 [{source['name']}]: {e}")
                    continue

        # 2. 内置验证数据
        if include_builtin:
            builtin = self.get_builtin_teams()
            for team in builtin:
                if team.name not in seen_names:
                    seen_names.add(team.name)
                    all_teams.append(team)

        # 3. 转换为dict
        result["teams"] = [t.model_dump() for t in all_teams]
        result["teams_count"] = len(all_teams)
        result["rising_pets"] = self.get_seasonal_rising_pets()

        return result
