# models.py
# 定义游戏中的数据模型

from dataclasses import dataclass, field, replace
from typing import Optional, List, Dict, Any

@dataclass
class Item:
    """物品数据模型"""
    id: str
    name: str
    type: str  # 丹药, 材料, 法器, 功法
    rank: str  # 凡品, 珍品, 极品, 仙品, 圣品, 帝品 
    description: str
    price: int
    effect: Optional[Dict[str, Any]] = None

@dataclass
class Player:
    """玩家数据模型"""
    user_id: str
    level_index: int = 0  
    spiritual_root: str = "未知"
    experience: int = 0
    gold: int = 0
    last_check_in: float = 0.0
    state: str = '空闲'
    state_start_time: float = 0.0
    sect_id: Optional[int] = None
    sect_name: Optional[str] = None
    hp: int = 100
    max_hp: int = 100
    attack: int = 10
    defense: int = 5
    realm_id: Optional[str] = None
    realm_floor: int = 0

    @property
    def level(self) -> str:
        # 为了兼容旧代码和方便模板渲染，提供一个 level 属性的只读方法
        # 注意: 这需要 config_manager 先被加载
        from .config_manager import config
        if 0 <= self.level_index < len(config.level_data):
            return config.level_data[self.level_index]['level_name']
        return "未知境界"

    def clone(self) -> 'Player':
        return replace(self)

@dataclass
class PlayerEffect:
    """用于原子化更新玩家状态的数据模型"""
    experience: int = 0
    gold: int = 0
    hp: int = 0

@dataclass
class Boss:
    """Boss 数据模型"""
    id: str
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    cooldown_minutes: int
    rewards: dict

@dataclass
class Monster:
    """普通怪物数据模型"""
    id: str
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    rewards: dict

@dataclass
class AttackResult:
    """封装一次攻击的结果"""
    success: bool
    message: str
    battle_over: bool = False
    updated_players: List[Player] = field(default_factory=list)