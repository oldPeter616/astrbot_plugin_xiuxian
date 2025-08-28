# data_manager.py
# 数据管理模块，负责所有数据库操作

import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any

from astrbot.api import logger
from astrbot.api.star import StarTools

from .config_manager import config
from .models import Player

DATA_DIR = StarTools.get_data_dir("xiuxian")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / config.DATABASE_FILE

# --- 连接池核心 ---
_db_pool: Optional[aiosqlite.Connection] = None

async def init_db_pool():
    """初始化数据库连接池并在必要时创建表"""
    global _db_pool
    if _db_pool is None:
        # aiosqlite.connect in practice here creates a single connection
        # that we will reuse, acting like a pool of size 1.
        _db_pool = await aiosqlite.connect(DB_PATH)
        logger.info(f"数据库连接已创建: {DB_PATH}")
        await init_database() # 调用建表函数

async def close_db_pool():
    """关闭数据库连接"""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("数据库连接已关闭。")

async def init_database():
    """初始化数据库，如果表不存在则创建。"""
    async with _db_pool.execute("PRAGMA foreign_keys = ON"):
        pass
    
    await _db_pool.execute("""
        CREATE TABLE IF NOT EXISTS sects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            leader_id TEXT NOT NULL,
            level INTEGER NOT NULL DEFAULT 1,
            funds INTEGER NOT NULL DEFAULT 0
        )
    """)
    await _db_pool.execute("""
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
    await _db_pool.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES players (user_id),
            UNIQUE(user_id, item_id)
        )
    """)
    await _db_pool.commit()

async def get_player_by_id(user_id: str) -> Optional[Player]:
    """通过用户ID获取玩家数据"""
    _db_pool.row_factory = aiosqlite.Row
    async with _db_pool.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        return Player(**dict(row)) if row else None

async def create_player(player: Player):
    """创建新玩家"""
    await _db_pool.execute("""
        INSERT INTO players (user_id, level, spiritual_root, experience, gold, last_check_in, state, state_start_time, sect_id, sect_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        player.user_id, player.level, player.spiritual_root, player.experience,
        player.gold, player.last_check_in, player.state, player.state_start_time,
        player.sect_id, player.sect_name
    ))
    await _db_pool.commit()

async def update_player(player: Player):
    """更新玩家数据"""
    await _db_pool.execute("""
        UPDATE players
        SET level = ?, spiritual_root = ?, experience = ?, gold = ?, last_check_in = ?, 
            state = ?, state_start_time = ?, sect_id = ?, sect_name = ?
        WHERE user_id = ?
    """, (
        player.level, player.spiritual_root, player.experience, player.gold,
        player.last_check_in, player.state, player.state_start_time,
        player.sect_id, player.sect_name, player.user_id
    ))
    await _db_pool.commit()

async def create_sect(sect_name: str, leader_id: str) -> int:
    """创建新宗门并返回宗门ID"""
    async with _db_pool.execute("INSERT INTO sects (name, leader_id) VALUES (?, ?)", (sect_name, leader_id)) as cursor:
        await _db_pool.commit()
        return cursor.lastrowid

async def get_sect_by_name(sect_name: str) -> Optional[Dict[str, Any]]:
    """根据名称查找宗门"""
    _db_pool.row_factory = aiosqlite.Row
    async with _db_pool.execute("SELECT * FROM sects WHERE name = ?", (sect_name,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_sect_by_id(sect_id: int) -> Optional[Dict[str, Any]]:
    """根据ID查找宗门"""
    _db_pool.row_factory = aiosqlite.Row
    async with _db_pool.execute("SELECT * FROM sects WHERE id = ?", (sect_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_sect_members(sect_id: int) -> List[Player]:
    """获取宗门所有成员 (已优化)"""
    _db_pool.row_factory = aiosqlite.Row
    async with _db_pool.execute("SELECT * FROM players WHERE sect_id = ?", (sect_id,)) as cursor:
        rows = await cursor.fetchall()
        return [Player(**dict(row)) for row in rows]

async def update_player_sect(user_id: str, sect_id: Optional[int], sect_name: Optional[str]):
    """更新玩家的宗门信息"""
    await _db_pool.execute("UPDATE players SET sect_id = ?, sect_name = ? WHERE user_id = ?", (sect_id, sect_name, user_id))
    await _db_pool.commit()

async def get_inventory_by_user_id(user_id: str) -> List[Dict[str, Any]]:
    """获取指定用户的背包物品列表"""
    _db_pool.row_factory = aiosqlite.Row
    async with _db_pool.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ?", (user_id,)) as cursor:
        rows = await cursor.fetchall()
        inventory_list = []
        for row in rows:
            item_id, quantity = row['item_id'], row['quantity']
            item_info = config.item_data.get(str(item_id), {})
            inventory_list.append({
                "item_id": item_id, "name": item_info.get("name", "未知物品"),
                "quantity": quantity, "description": item_info.get("description", "无")
            })
        return inventory_list

async def add_item_to_inventory(user_id: str, item_id: str, quantity: int = 1):
    """向用户背包添加物品 (UPSERT)"""
    await _db_pool.execute("""
        INSERT INTO inventory (user_id, item_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, item_id) DO UPDATE SET
        quantity = quantity + excluded.quantity;
    """, (user_id, item_id, quantity))
    await _db_pool.commit()