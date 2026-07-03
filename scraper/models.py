"""
数据模型定义
===========
使用Pydantic定义结构化数据模型，支持序列化和校验。
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SkillBase(BaseModel):
    """技能基础模型"""
    name: str = Field(..., description="技能名称")
    element: Optional[str] = Field(None, description="技能属性")
    category: Optional[str] = Field(None, description="技能分类：物攻/魔攻/状态/防御")
    power: Optional[int] = Field(None, description="技能威力")
    cost: Optional[int] = Field(None, description="技能能耗（PP值）")
    effect: Optional[str] = Field(None, description="技能效果描述")
    target: Optional[str] = Field(None, description="技能目标：单体/群体/自身")
    source_url: Optional[str] = Field(None, description="数据来源URL")


class Skill(SkillBase):
    """完整技能模型"""
    skill_id: Optional[str] = Field(None, description="技能唯一标识")
    learn_type: Optional[str] = Field(None, description="学习方式：升级/技能石/遗传")


class PetBase(BaseModel):
    """精灵基础模型 (用于列表展示)"""
    name: str = Field(..., description="精灵名称")
    pet_id: Optional[int] = Field(None, description="精灵编号")
    element: Optional[List[str]] = Field(None, description="属性（可双属性）")
    rarity: Optional[str] = Field(None, description="稀有度")


class PetStats(BaseModel):
    """精灵种族值"""
    hp: Optional[int] = Field(None, description="生命")
    attack: Optional[int] = Field(None, description="物攻")
    defense: Optional[int] = Field(None, description="物防")
    magic_attack: Optional[int] = Field(None, description="魔攻")
    magic_defense: Optional[int] = Field(None, description="魔防")
    speed: Optional[int] = Field(None, description="速度")
    total: Optional[int] = Field(None, description="总和")


class EvolutionInfo(BaseModel):
    """进化信息"""
    from_form: Optional[str] = Field(None, description="进化前形态")
    to_form: Optional[str] = Field(None, description="进化后形态")
    condition: Optional[str] = Field(None, description="进化条件")


class Pet(PetBase):
    """完整精灵模型"""
    nicknames: List[str] = Field(default_factory=list, description="别名/俗称")
    stats: Optional[PetStats] = Field(None, description="种族值")
    skills: List[Skill] = Field(default_factory=list, description="可学技能列表")
    skill_ids: List[str] = Field(default_factory=list, description="技能ID列表")
    evolution: Optional[EvolutionInfo] = Field(None, description="进化信息")
    evolution_chain: List[str] = Field(default_factory=list, description="进化链")
    obtain_method: Optional[str] = Field(None, description="获取方式")
    description: Optional[str] = Field(None, description="精灵描述/背景")
    source_url: Optional[str] = Field(None, description="数据来源URL")
    updated_at: Optional[str] = Field(None, description="数据更新时间")


class TeamPetSlot(BaseModel):
    """阵容中的精灵位"""
    pet_name: str = Field(..., description="精灵名称")
    position: int = Field(..., description="位置序号")
    role: Optional[str] = Field(None, description="角色定位（首发/主力/收割/辅助）")
    skill_set: Optional[List[str]] = Field(None, description="推荐技能搭配")


class PvpTeam(BaseModel):
    """PVP阵容模型"""
    name: str = Field(..., description="阵容名称/标签")
    rank: Optional[str] = Field(None, description="适用段位/梯队")
    core_pets: List[str] = Field(..., description="核心精灵列表")
    flex_pets: List[str] = Field(default_factory=list, description="摇摆位/替补精灵")
    pets: List[TeamPetSlot] = Field(default_factory=list, description="完整队伍配置")
    win_rate: Optional[float] = Field(None, description="胜率")
    usage_rate: Optional[float] = Field(None, description="出场率")
    description: Optional[str] = Field(None, description="阵容描述")
    mechanics: Optional[str] = Field(None, description="核心机制说明")
    pros: List[str] = Field(default_factory=list, description="优点")
    cons: List[str] = Field(default_factory=list, description="缺点")
    counters: List[str] = Field(default_factory=list, description="被克制阵容")
    target_users: Optional[str] = Field(None, description="适合人群")
    source_url: Optional[str] = Field(None, description="数据来源URL")
    season: Optional[str] = Field(None, description="适用赛季")
    updated_at: Optional[str] = Field(None, description="更新时间")


class TypeEffectiveness(BaseModel):
    """属性克制关系"""
    attacker: str = Field(..., description="攻击方属性")
    defender: str = Field(..., description="防御方属性")
    multiplier: float = Field(..., description="克制倍率")
    effect: str = Field(..., description="效果描述：克制/被抗/免疫/普通")


class PetListResponse(BaseModel):
    """精灵列表响应"""
    total: int
    pets: List[PetBase]
    source: str
    fetched_at: str


class SkillListResponse(BaseModel):
    """技能列表响应"""
    total: int
    skills: List[Skill]
    source: str
    fetched_at: str


class TeamListResponse(BaseModel):
    """阵容列表响应"""
    total: int
    teams: List[PvpTeam]
    source: str
    fetched_at: str
