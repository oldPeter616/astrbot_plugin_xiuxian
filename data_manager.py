# data_manager.py
# 数据管理模块，负责所有数据库操作

import sqlite3
from pathlib import Path
from typing import Optional

# 修改点：导入 StarTools 和 logger
from astrbot.api import logger
from astrbot.api.star import StarTools

from .config_manager import config
from .models import Player

# 修改点：使用框架提供的API获取并创建数据目录
DATA_DIR = StarTools.get_data_dir("xiuxian")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / config.DATABASE_FILE

logger.info(f"修仙插件数据将存储在: {DB_PATH}")

def init_database():
    """初始化数据库，如果表不存在则创建。"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id TEXT PRIMARY KEY,
                level TEXT NOT NULL,
                spiritual_root TEXT NOT NULL,
                experience INTEGER NOT NULL,
                gold INTEGER NOT NULL,
                last_check_in REAL NOT NULL
            )
        """)
        conn.commit()

# ... (get_player_by_id, create_player, update_player 函数保持不变)
def get_player_by_id(user_id: str) -> Optional[Player]:
    """通过用户ID获取玩家数据"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return Player(**dict(row)) if row else None

def create_player(player: Player):
    """创建新玩家"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO players (user_id, level, spiritual_root, experience, gold, last_check_in)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            player.user_id,
            player.level,
            player.spiritual_root,
            player.experience,
            player.gold,
            player.last_check_in
        ))
        conn.commit()

def update_player(player: Player):
    """更新玩家数据"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE players
            SET level = ?, spiritual_root = ?, experience = ?, gold = ?, last_check_in = ?
            WHERE user_id = ?
        """, (
            player.level,
            player.spiritual_root,
            player.experience,
            player.gold,
            player.last_check_in,
            player.user_id
        ))
        conn.commit()