# data_manager.py
# 数据管理模块，负责所有数据库操作

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from astrbot.api import logger
from astrbot.api.star import StarTools

from .config_manager import config
from .models import Player

DATA_DIR = StarTools.get_data_dir("xiuxian")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / config.DATABASE_FILE

logger.info(f"修仙插件数据将存储在: {DB_PATH}")

def init_database():
    """初始化数据库，如果表不存在则创建。"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # 新增 sects 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                leader_id TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 1,
                funds INTEGER NOT NULL DEFAULT 0
            )
        """)
        
        # 修改 players 表, 增加 sect_id 和 sect_name
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id TEXT PRIMARY KEY,
                level TEXT NOT NULL,
                spiritual_root TEXT NOT NULL,
                experience INTEGER NOT NULL,
                gold INTEGER NOT NULL,
                last_check_in REAL NOT NULL,
                state TEXT NOT NULL,
                state_start_time REAL NOT NULL,
                sect_id INTEGER,
                sect_name TEXT,
                FOREIGN KEY (sect_id) REFERENCES sects (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES players (user_id)
            )
        """)
        conn.commit()

def get_player_by_id(user_id: str) -> Optional[Player]:
    """通过用户ID获取玩家数据"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        # Manually create Player instance to handle missing columns gracefully
        player_data = dict(row)
        return Player(
            user_id=player_data.get('user_id'),
            level=player_data.get('level', '炼气一层'),
            spiritual_root=player_data.get('spiritual_root', '未知'),
            experience=player_data.get('experience', 0),
            gold=player_data.get('gold', 0),
            last_check_in=player_data.get('last_check_in', 0.0),
            state=player_data.get('state', '空闲'),
            state_start_time=player_data.get('state_start_time', 0.0),
            sect_id=player_data.get('sect_id'),
            sect_name=player_data.get('sect_name')
        )

def create_player(player: Player):
    """创建新玩家"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO players (user_id, level, spiritual_root, experience, gold, last_check_in, state, state_start_time, sect_id, sect_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player.user_id, player.level, player.spiritual_root, player.experience,
            player.gold, player.last_check_in, player.state, player.state_start_time,
            player.sect_id, player.sect_name
        ))
        conn.commit()

def update_player(player: Player):
    """更新玩家数据"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE players
            SET level = ?, spiritual_root = ?, experience = ?, gold = ?, last_check_in = ?, 
                state = ?, state_start_time = ?, sect_id = ?, sect_name = ?
            WHERE user_id = ?
        """, (
            player.level, player.spiritual_root, player.experience, player.gold,
            player.last_check_in, player.state, player.state_start_time,
            player.sect_id, player.sect_name, player.user_id
        ))
        conn.commit()

# --- 新增的宗门相关函数 ---

def create_sect(sect_name: str, leader_id: str) -> int:
    """创建新宗门并返回宗门ID"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sects (name, leader_id) VALUES (?, ?)",
            (sect_name, leader_id)
        )
        conn.commit()
        return cursor.lastrowid

def get_sect_by_name(sect_name: str) -> Optional[Dict[str, Any]]:
    """根据名称查找宗门"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sects WHERE name = ?", (sect_name,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_sect_by_id(sect_id: int) -> Optional[Dict[str, Any]]:
    """根据ID查找宗门"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sects WHERE id = ?", (sect_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_sect_members(sect_id: int) -> List[Player]:
    """获取宗门所有成员"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE sect_id = ?", (sect_id,))
        rows = cursor.fetchall()
        return [get_player_by_id(row['user_id']) for row in rows] # Reuse get_player_by_id for consistency

def update_player_sect(user_id: str, sect_id: Optional[int], sect_name: Optional[str]):
    """更新玩家的宗门信息"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE players SET sect_id = ?, sect_name = ? WHERE user_id = ?", (sect_id, sect_name, user_id))
        conn.commit()


# --- 背包相关函数 (保持不变) ---
def get_inventory_by_user_id(user_id: str) -> List[Dict[str, Any]]:
    """获取指定用户的背包物品列表"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        
        inventory_list = []
        for row in rows:
            item_id = row['item_id']
            quantity = row['quantity']
            item_info = config.item_data.get(item_id, {})
            inventory_list.append({
                "item_id": item_id,
                "name": item_info.get("name", "未知物品"),
                "quantity": quantity,
                "description": item_info.get("description", "无")
            })
        return inventory_list

def add_item_to_inventory(user_id: str, item_id: str, quantity: int = 1):
    """向用户背包添加物品"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id))
        row = cursor.fetchone()
        
        if row:
            new_quantity = row[0] + quantity
            cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ?", (new_quantity, user_id, item_id))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)", (user_id, item_id, quantity))
        
        conn.commit()