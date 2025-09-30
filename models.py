# models.py

import json
from dataclasses import dataclass, field, replace, asdict
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .config_manager import ConfigManager

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
    subtype: Optional[str] = None  # 装备子类型，如'武器', '防具'
    equip_effects: Optional[Dict[str, Any]] = None  # 装备属性加成

@dataclass
class FloorEvent:
    """秘境层级事件数据模型"""

    type: str
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RealmInstance:
    """秘境实例数据模型"""

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
    state: str = "空闲"
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
    
    # 装备槽位
    equipped_weapon: Optional[str] = None
    equipped_armor: Optional[str] = None
    equipped_accessory: Optional[str] = None

    def get_level(self, config_manager: "ConfigManager") -> str:
        if 0 <= self.level_index < len(config_manager.level_data):
            return config_manager.level_data[self.level_index]["level_name"]
        return "未知境界"

    def get_combat_stats(self, config_manager: "ConfigManager") -> Dict[str, Any]:
        """计算并返回玩家的最终战斗属性（基础属性+装备加成）"""
        stats = {
            "hp": self.hp,
            "max_hp": self.max_hp,
            "attack": self.attack,
            "defense": self.defense,
        }
        
        equipment_ids = [self.equipped_weapon, self.equipped_armor, self.equipped_accessory]
        
        for item_id in equipment_ids:
            if item_id:
                item = config_manager.item_data.get(str(item_id))
                if item and item.equip_effects:
                    for key, value in item.equip_effects.items():
                        if key in stats:
                            stats[key] += value
        return stats

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

    def clone(self) -> "Player":
        return replace(self)

@dataclass
class PlayerEffect:
    experience: int = 0
    gold: int = 0
    hp: int = 0

@dataclass
class Boss:
    """世界Boss数据模型"""

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
    """当前活跃的世界Boss数据模型"""

    boss_id: str
    current_hp: int
    max_hp: int
    spawned_at: float
    level_index: int

@dataclass
class Monster:
    """怪物数据模型"""

    id: str
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    rewards: dict

@dataclass
class AttackResult:
    """战斗结果数据模型"""

    success: bool
    message: str
    battle_over: bool = False
    updated_players: List[Player] = field(default_factory=list)