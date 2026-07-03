"""
种子数据
=======
预置精灵和技能数据，来自社区公开信息的多源交叉验证。
当网络爬虫不可用或数据不完整时，作为数据的基础层使用。

数据来源：
- BiliWiki (wiki.biligame.com/rocom)
- 什么值得买社区攻略
- 各游戏媒体攻略
"""

from typing import List, Dict

# ================================================================
# S2赛季常见精灵种子数据
# ================================================================

SEED_PETS: List[Dict] = [
    # --- 火系 ---
    {"name": "火神", "element": ["火"], "rarity": "传说",
     "stats": {"hp": 85, "attack": 60, "defense": 70, "magic_attack": 115, "magic_defense": 80, "speed": 100, "total": 510}},
    {"name": "火花", "element": ["火"], "rarity": "普通"},
    {"name": "焰火", "element": ["火"], "rarity": "稀有"},

    # --- 水系 ---
    {"name": "水灵", "element": ["水"], "rarity": "稀有",
     "stats": {"hp": 75, "attack": 55, "defense": 65, "magic_attack": 95, "magic_defense": 80, "speed": 85, "total": 455}},
    {"name": "果冻", "element": ["水", "冰"], "rarity": "稀有"},

    # --- 草系 ---
    {"name": "春兔", "element": ["草"], "rarity": "稀有",
     "description": "S2赛季新兴精灵，强化天兽队与第五队后场回复能力"},

    # --- 光系 ---
    {"name": "白金独角兽", "element": ["光"], "rarity": "传说",
     "description": "独角兽增益流核心，全队增益+爆发，新手首选"},
    {"name": "圣羽翼王", "element": ["光", "翼"], "rarity": "传说",
     "description": "翼王队核心，游击收割位，速度极快"},
    {"name": "圣剑-X", "element": ["光"], "rarity": "传说"},
    {"name": "权杖-V", "element": ["光"], "rarity": "传说"},

    # --- 暗/幽系 ---
    {"name": "恶魔狼", "element": ["恶"], "rarity": "稀有",
     "description": "狼王体系核心，PVP使用率最高的精灵之一"},
    {"name": "黑猫巫师", "element": ["幽"], "rarity": "稀有",
     "description": "黑猫+恶魔狼形成核心联动，狼王体系核心组件"},
    {"name": "夜枭", "element": ["幽", "翼"], "rarity": "稀有"},
    {"name": "紫夜", "element": ["幽"], "rarity": "稀有"},
    {"name": "影狸", "element": ["幽"], "rarity": "普通"},
    {"name": "小夜", "element": ["幽"], "rarity": "普通"},
    {"name": "岚鸟", "element": ["翼", "幽"], "rarity": "传说",
     "description": "狐仙翼王队首发，暴力输出"},
    {"name": "春天岚鸟", "element": ["草", "翼"], "rarity": "传说",
     "description": "电鹿轮转队核心，轮转消耗主力"},
    {"name": "帕尔萨斯", "element": ["恶"], "rarity": "传说",
     "description": "龙王星陨队成员，T0阵容组件"},
    {"name": "龙息帕尔", "element": ["龙", "恶"], "rarity": "传说",
     "description": "S2新陨队核心，进化后让新陨队重获生机"},

    # --- 龙系 ---
    {"name": "古龙", "element": ["龙"], "rarity": "传说",
     "description": "古龙红队核心，依赖复活特性实现无死亡压力作战"},
    {"name": "寂灭骨龙", "element": ["龙", "幽"], "rarity": "传说",
     "description": "电鹿轮转队/狐仙翼王队联防核心"},
    {"name": "龙光悠悠", "element": ["龙"], "rarity": "稀有",
     "description": "闪击翼王队组件，速度线压制"},

    # --- 冰系 ---
    {"name": "雪影娃娃", "element": ["冰"], "rarity": "稀有",
     "description": "雪天冻结队核心天气手"},
    {"name": "冰钻布鲁斯", "element": ["冰"], "rarity": "稀有"},
    {"name": "雪巨人", "element": ["冰"], "rarity": "稀有"},

    # --- 机械系 ---
    {"name": "沉铁兽", "element": ["机械"], "rarity": "稀有",
     "description": "天鹅沉铁兽体系核心，状态传递"},
    {"name": "画间沉铁兽", "element": ["机械"], "rarity": "稀有"},
    {"name": "金瓜盒子", "element": ["机械"], "rarity": "稀有",
     "description": "闪击翼王队组件"},

    # --- 毒系 ---
    {"name": "怖哭菇", "element": ["毒", "草"], "rarity": "稀有",
     "description": "龙王星陨队印记手，挂印记叠层核心"},
    {"name": "书魔虫", "element": ["毒", "虫"], "rarity": "稀有"},
    {"name": "古卷执政官", "element": ["毒", "虫"], "rarity": "传说"},

    # --- 普通 ---
    {"name": "落陨星兔", "element": ["普通"], "rarity": "稀有",
     "description": "龙王星陨队主C，引爆印记打出爆发伤害"},

    # --- 电系 ---
    {"name": "声波缇塔", "element": ["电"], "rarity": "稀有",
     "description": "电鹿轮转队核心，具备令对手退化的能力"},
    {"name": "梦想三三", "element": ["电"], "rarity": "稀有",
     "description": "S2赛季核心，首领化后坦度提升，具备退化能力"},

    # --- 翼系 ---
    {"name": "闪击翼王", "element": ["翼"], "rarity": "传说",
     "description": "闪击翼王队核心收割单位，速度差打出高额伤害"},
    {"name": "高速琵琶鸟", "element": ["翼"], "rarity": "稀有",
     "description": "闪击翼王队组件，高速先手"},
    {"name": "凡雀", "element": ["翼"], "rarity": "普通"},
    {"name": "凡鹰", "element": ["翼"], "rarity": "稀有"},

    # --- 虫系 ---
    {"name": "化蝶", "element": ["虫"], "rarity": "稀有",
     "description": "多套T0阵容通用辅助位"},
    {"name": "书卷守护", "element": ["虫"], "rarity": "稀有"},

    # --- 武系 ---
    {"name": "红绒十字", "element": ["武"], "rarity": "稀有",
     "description": "独角兽增益流组件"},
    {"name": "翠顶夫人", "element": ["草", "武"], "rarity": "稀有",
     "description": "核心辅助，25%全队增伤，多套T0阵容通用"},

    # --- 萌系 ---
    {"name": "帕帕斯卡", "element": ["萌"], "rarity": "稀有",
     "description": "独角兽增益流/狼王体系通用组件"},

    # --- 地系 ---
    {"name": "小皮球", "element": ["地"], "rarity": "普通",
     "description": "龙王星陨队组件"},
    {"name": "石石", "element": ["地"], "rarity": "普通"},

    # --- 幻系 ---
    {"name": "尖嘴狐仙", "element": ["幻"], "rarity": "传说",
     "description": "狐仙翼王队攻防枢纽，独角兽增益流组件"},

    # --- 新增：常见精灵 ---
    {"name": "多多", "element": ["普通"], "rarity": "普通"},
    {"name": "多西", "element": ["普通"], "rarity": "普通"},
    {"name": "优优", "element": ["普通"], "rarity": "普通"},
    {"name": "喵喵", "element": ["普通"], "rarity": "普通"},
    {"name": "喵呜", "element": ["普通"], "rarity": "普通"},
    {"name": "毛毛", "element": ["普通"], "rarity": "普通"},
    {"name": "松仔", "element": ["草"], "rarity": "普通"},
    {"name": "火狗", "element": ["火"], "rarity": "普通",
     "description": "天鹅沉铁兽体系组件"},
    {"name": "斑斑", "element": ["普通"], "rarity": "普通"},
    {"name": "斑枭", "element": ["翼", "普通"], "rarity": "普通"},
    {"name": "爬爬", "element": ["虫"], "rarity": "普通"},
    {"name": "灵狐", "element": ["火"], "rarity": "稀有"},
    {"name": "兽帕雷", "element": ["火", "武"], "rarity": "稀有",
     "description": "古龙红队组件"},
    {"name": "星光石", "element": ["光"], "rarity": "稀有",
     "description": "古龙红队组件"},
    {"name": "卡卡鸟", "element": ["翼"], "rarity": "稀有",
     "description": "S2赛季新兴精灵，暴风眼后无限连击"},
    {"name": "天鹅", "element": ["水", "翼"], "rarity": "稀有",
     "description": "天鹅沉铁兽体系核心，状态传递先手压制"},
    {"name": "冰猪", "element": ["冰"], "rarity": "稀有",
     "description": "天鹅沉铁兽体系摇摆位"},
    {"name": "羚羊", "element": ["草"], "rarity": "稀有",
     "description": "天鹅沉铁兽体系摇摆位"},
    {"name": "帅帅魔偶", "element": ["冰"], "rarity": "稀有",
     "description": "雪天冻结队组件"},
    {"name": "首领化火神", "element": ["火"], "rarity": "传说",
     "description": "雪影迪迪小丑布丁队核心，可野外获取"},
    {"name": "酷拉", "element": ["电"], "rarity": "稀有",
     "description": "雪影迪迪小丑布丁队组件"},
    {"name": "叮叮恶魔", "element": ["恶"], "rarity": "稀有",
     "description": "雪影迪迪小丑布丁队组件"},
    {"name": "椰浆布丁", "element": ["水"], "rarity": "稀有",
     "description": "独角兽增益流变体组件"},
    {"name": "小鹬", "element": ["水"], "rarity": "普通"},
]

# ================================================================
# 技能种子数据（常用PVP技能）
# ================================================================

SEED_SKILLS: List[Dict] = [
    {"name": "暴风眼", "element": "翼", "category": "魔攻", "effect": "对敌方全体造成伤害，暴风眼后连击"},
    {"name": "印记", "element": "毒", "category": "状态", "effect": "给对手附加印记标记，可叠加"},
    {"name": "印记引爆", "element": "普通", "category": "魔攻", "effect": "引爆对手身上的印记，层数越高伤害越大"},
    {"name": "全队增益", "element": "光", "category": "状态", "effect": "提升全队攻击力"},
    {"name": "首领先攻", "element": "普通", "category": "状态", "effect": "首领化后获得先手优势"},
    {"name": "退化", "element": "电", "category": "状态", "effect": "使对手退化，降低能力等级"},
    {"name": "雪天", "element": "冰", "category": "状态", "effect": "改变天气为雪天，持续若干回合"},
    {"name": "冻结", "element": "冰", "category": "状态", "effect": "冰冻对手，使其无法行动"},
    {"name": "状态传递", "element": "普通", "category": "状态", "effect": "将自身状态传递给队友"},
    {"name": "复活", "element": "幽", "category": "状态", "effect": "复活己方阵亡精灵"},
    {"name": "连击", "element": "普通", "category": "物攻", "effect": "连续攻击对手多次"},
    {"name": "闪击", "element": "翼", "category": "物攻", "effect": "高速攻击，比对手先出手"},
    {"name": "恢复", "element": "草", "category": "状态", "effect": "恢复自身HP"},
    {"name": "护盾", "element": "机械", "category": "防御", "effect": "为自己附加护盾"},
    {"name": "焚烧", "element": "火", "category": "魔攻", "effect": "灼烧对手，每回合造成额外伤害"},
    {"name": "激流", "element": "水", "category": "魔攻", "effect": "对对手造成水系伤害"},
    {"name": "藤蔓", "element": "草", "category": "状态", "effect": "束缚对手，降低速度"},
    {"name": "吸收", "element": "草", "category": "魔攻", "effect": "吸取对手HP恢复自身"},
    {"name": "电击", "element": "电", "category": "魔攻", "effect": "对对手造成电系伤害"},
    {"name": "地震", "element": "地", "category": "物攻", "effect": "对全体造成地系伤害"},
    {"name": "暗影", "element": "幽", "category": "魔攻", "effect": "对对手造成幽灵系伤害"},
    {"name": "光之盾", "element": "光", "category": "防御", "effect": "提升全队防御力"},
    {"name": "龙息", "element": "龙", "category": "魔攻", "effect": "对对手造成龙系伤害"},
    {"name": "冰锥", "element": "冰", "category": "魔攻", "effect": "对对手造成冰系伤害"},
    {"name": "毒雾", "element": "毒", "category": "状态", "effect": "使对手中毒"},
    {"name": "虫群", "element": "虫", "category": "魔攻", "effect": "对对手造成虫系伤害"},
    {"name": "武斗", "element": "武", "category": "物攻", "effect": "对对手造成武系伤害"},
    {"name": "旋风", "element": "翼", "category": "物攻", "effect": "对对手造成翼系伤害"},
    {"name": "魅惑", "element": "萌", "category": "状态", "effect": "魅惑对手，使其混乱"},
    {"name": "恶之波动", "element": "恶", "category": "魔攻", "effect": "对对手造成恶系伤害"},
    {"name": "幻影", "element": "幻", "category": "魔攻", "effect": "对对手造成幻系伤害"},
]

# ================================================================
# 获取种子数据
# ================================================================

def get_seed_pets() -> List[Dict]:
    """获取种子精灵数据"""
    return SEED_PETS


def get_seed_skills() -> List[Dict]:
    """获取种子技能数据"""
    return SEED_SKILLS


def get_seed_summary() -> Dict:
    """获取种子数据摘要"""
    return {
        "pets_count": len(SEED_PETS),
        "skills_count": len(SEED_SKILLS),
        "pet_elements": list(set(
            e for pet in SEED_PETS for e in pet.get("element", [])
        )),
        "description": "种子数据包含S2赛季常见精灵和PVP常用技能，"
                       "来自多来源交叉验证。可作为离线基础数据层使用。",
    }
