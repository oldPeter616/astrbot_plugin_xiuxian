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

# --- 数据库版本控制 ---
LATEST_DB_VERSION = 2 # 定义当前代码期望的最新数据库版本

# --- 连接池核心 ---
_db_pool: Optional[aiosqlite.Connection] = None

async def init_db_pool():
    """初始化数据库连接池，并执行数据库迁移"""
    global _db_pool
    if _db_pool is None:
        _db_pool = await aiosqlite.connect(DB_PATH)
        logger.info(f"数据库连接已创建: {DB_PATH}")
        await migrate_database() # 在初始化时执行迁移

async def close_db_pool():
    """关闭数据库连接"""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("数据库连接已关闭。")

# --- 数据库迁移核心功能 ---

async def migrate_database():
    """检查并执行数据库迁移"""
    async with _db_pool.execute("PRAGMA foreign_keys = ON"):
        pass

    # 检查版本表是否存在
    async with _db_pool.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_info'") as cursor:
        if await cursor.fetchone() is None:
            # 全新安装
            logger.info("未检测到数据库版本，将进行全新安装...")
            await _create_all_tables_v2()
            await _db_pool.execute("INSERT INTO db_info (version) VALUES (?)", (LATEST_DB_VERSION,))
            await _db_pool.commit()
            logger.info(f"数据库已初始化到最新版本: v{LATEST_DB_VERSION}")
            return

    # 获取当前版本
    current_version = 0
    async with _db_pool.execute("SELECT version FROM db_info") as cursor:
        row = await cursor.fetchone()
        if row:
            current_version = row[0]

    logger.info(f"当前数据库版本: v{current_version}, 最新版本: v{LATEST_DB_VERSION}")

    if current_version < LATEST_DB_VERSION:
        logger.info("检测到数据库需要升级...")
        if current_version < 2:
            await _upgrade_v1_to_v2()
        # --- 未来在这里添加更多的版本升级 ---
        # if current_version < 3:
        #     await _upgrade_v2_to_v3()
        
        logger.info("数据库升级完成！")
    else:
        logger.info("数据库结构已是最新。")

async def _create_all_tables_v2():
    """创建版本2（最新）的所有表结构"""
    await _db_pool.execute("""
        CREATE TABLE IF NOT EXISTS db_info (version INTEGER NOT NULL)
    """)
    await _db_pool.execute("""
        CREATE TABLE IF NOT EXISTS sects (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
            leader_id TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 1,
            funds INTEGER NOT NULL DEFAULT 0
        )
    """)
    await _db_pool.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY, level TEXT NOT NULL, spiritual_root TEXT NOT NULL,
            experience INTEGER NOT NULL, gold INTEGER NOT NULL, last_check_in REAL NOT NULL,
            state TEXT NOT NULL, state_start_time REAL NOT NULL, sect_id INTEGER,
            sect_name TEXT, FOREIGN KEY (sect_id) REFERENCES sects (id)
        )
    """)
    await _db_pool.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            item_id TEXT NOT NULL, quantity INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES players (user_id),
            UNIQUE(user_id, item_id)
        )
    """)
    await _db_pool.commit()

async def _upgrade_v1_to_v2():
    """从版本1升级到版本2的迁移逻辑"""
    logger.info("正在执行数据库升级: v1 -> v2 ...")
    try:
        # 1. 重命名旧的 inventory 表
        await _db_pool.execute("ALTER TABLE inventory RENAME TO inventory_old")

        # 2. 创建新的、带 UNIQUE 约束的 inventory 表
        await _db_pool.execute("""
            CREATE TABLE inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
                item_id TEXT NOT NULL, quantity INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES players (user_id),
                UNIQUE(user_id, item_id)
            )
        """)

        # 3. 将旧表数据迁移到新表
        await _db_pool.execute("""
            INSERT INTO inventory (user_id, item_id, quantity)
            SELECT user_id, item_id, quantity FROM inventory_old
        """)

        # 4. 删除旧表
        await _db_pool.execute("DROP TABLE inventory_old")
        
        # 5. 更新版本号
        await _db_pool.execute("UPDATE db_info SET version = 2")
        await _db_pool.commit()
        logger.info("v1 -> v2 升级成功！")
    except Exception as e:
        await _db_pool.rollback()
        logger.error(f"数据库 v1 -> v2 升级失败，已回滚: {e}")
        raise

# --- 以下是数据操作函数，保持不变 ---

async def get_player_by_id(user_id: str) -> Optional[Player]:
    _db_pool.row_factory = aiosqlite.Row
    async with _db_pool.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        return Player(**dict(row)) if row else None

async def create_player(player: Player):
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
    async with _db_pool.execute("INSERT INTO sects (name, leader_id) VALUES (?, ?)", (sect_name, leader_id)) as cursor:
        await _db_pool.commit()
        return cursor.lastrowid

async def get_sect_by_name(sect_name: str) -> Optional[Dict[str, Any]]:
    _db_pool.row_factory = aiosqlite.Row
    async with _db_pool.execute("SELECT * FROM sects WHERE name = ?", (sect_name,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_sect_by_id(sect_id: int) -> Optional[Dict[str, Any]]:
    _db_pool.row_factory = aiosqlite.Row
    async with _db_pool.execute("SELECT * FROM sects WHERE id = ?", (sect_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_sect_members(sect_id: int) -> List[Player]:
    _db_pool.row_factory = aiosqlite.Row
    async with _db_pool.execute("SELECT * FROM players WHERE sect_id = ?", (sect_id,)) as cursor:
        rows = await cursor.fetchall()
        return [Player(**dict(row)) for row in rows]

async def update_player_sect(user_id: str, sect_id: Optional[int], sect_name: Optional[str]):
    await _db_pool.execute("UPDATE players SET sect_id = ?, sect_name = ? WHERE user_id = ?", (sect_id, sect_name, user_id))
    await _db_pool.commit()

async def get_inventory_by_user_id(user_id: str) -> List[Dict[str, Any]]:
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
    await _db_pool.execute("""
        INSERT INTO inventory (user_id, item_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, item_id) DO UPDATE SET
        quantity = quantity + excluded.quantity;
    """, (user_id, item_id, quantity))
    await _db_pool.commit()