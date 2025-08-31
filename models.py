# models.py
# 定义游戏中的数据模型

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class Player:
    """玩家数据模型"""
    user_id: str
    level: str = "炼气一层"
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