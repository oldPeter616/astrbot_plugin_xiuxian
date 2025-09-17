# models.py

import json
from dataclasses import dataclass, field, replace, asdict
from typing import Optional, List, Dict, Any

@dataclass
class Item:
    """物品数据模型"""
    id: str
    name: str
    type: str
    rank: str
    description: str
    price: int
    effect: Optional[Dict[str, Any]] = None

@dataclass
class FloorEvent:
    """秘境楼层事件数据模型"""
    type: str
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
    realm_data: Optional[str] = None

    @property
    def level(self) -> str:
        # 使用此种方式导入，以避免循环依赖
        from .config_manager import config
        if 0 <= self.level_index < len(config.level_data):
            return config.level_data[self.level_index]['level_name']
        return "未知境界"
        
    def get_realm_instance(self) -> Optional[RealmInstance]:
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
        if instance is None:
            self.realm_data = None
        else:
            self.realm_data = json.dumps(asdict(instance))

    def clone(self) -> 'Player':
        return replace(self)

@dataclass
class PlayerEffect:
    experience: int = 0
    gold: int = 0
    hp: int = 0

@dataclass
class Boss:
    """Boss 模板数据模型"""
    id: str
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    cooldown_minutes: int
    rewards: dict

@dataclass
class ActiveWorldBoss:
    """活跃的世界Boss实例数据模型"""
    boss_id: str
    current_hp: int
    max_hp: int
    spawned_at: float
    level_index: int

@dataclass
class Monster:
    id: str
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    rewards: dict

@dataclass
class AttackResult:
    success: bool
    message: str
    battle_over: bool = False
    updated_players: List[Player] = field(default_factory=list)