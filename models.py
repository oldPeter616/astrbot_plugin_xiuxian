# models.py
# 定义游戏中的数据模型

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Player:
    """
    玩家数据模型
    """
    user_id: str               # 用户唯一ID
    level: str = "炼气一层"        # 境界等级
    spiritual_root: str = "未知" # 灵根
    experience: int = 0          # 当前修为
    gold: int = 0                # 灵石数量
    last_check_in: float = 0.0   # 上次签到时间戳