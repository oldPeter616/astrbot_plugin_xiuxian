# models.py
# 定义游戏中的数据模型

import json
from dataclasses import dataclass, field, replace, asdict
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
class FloorEvent:
    """秘境楼层事件数据模型"""
    type: str  # "monster", "boss", "treasure", "empty"
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RealmInstance:
    """一次具体的、动态生成的秘境探索实例"""
    id: str
    total_floors: int
    floors: List[FloorEvent]

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
    realm_data: Optional[str] = None # 用于存储序列化的RealmInstance

    @property
    def level(self) -> str:
        from .config_manager import config
        if 0 <= self.level_index < len(config.level_data):
            return config.level_data[self.level_index]['level_name']
        return "未知境界"
        
    def get_realm_instance(self) -> Optional[RealmInstance]:
        """从realm_data反序列化RealmInstance对象"""
        if not self.realm_data:
            return None
        try:
            data = json.loads(self.realm_data)
            floors = [FloorEvent(**f) for f in data.get("floors", [])]
            data["floors"] = floors
            return RealmInstance(**data)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_realm_instance(self, instance: Optional[RealmInstance]):
        """序列化RealmInstance对象并存储到realm_data"""
        if instance is None:
            self.realm_data = None
        else:
            self.realm_data = json.dumps(asdict(instance))


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

@dataclass
class WorldBossStatus:
    """世界Boss状态的数据模型"""
    id: int
    boss_template_id: str
    current_hp: int
    max_hp: int
    generated_at: float