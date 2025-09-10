# data_manager.py
# 数据管理模块，负责所有数据库操作

import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable, Awaitable
from dataclasses import fields

from astrbot.api import logger
from astrbot.api.star import StarTools

from .config_manager import config
from .models import Player, PlayerEffect, Item

DATA_DIR = StarTools.get_data_dir("xiuxian")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / config.DATABASE_FILE

LATEST_DB_VERSION = 5

# --- 迁移任务注册表 ---
MIGRATION_TASKS: Dict[int, Callable[[aiosqlite.Connection], Awaitable[None]]] = {}

def migration(version: int):
    """注册数据库迁移任务的装饰器"""
    def decorator(func: Callable[[aiosqlite.Connection], Awaitable[None]]):
        MIGRATION_TASKS[version] = func
        return func
    return decorator

# --- 连接核心 ---
_db_connection: Optional[aiosqlite.Connection] = None

async def init_db_pool():
    """初始化数据库连接，并执行数据库迁移"""
    global _db_connection
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(DB_PATH)
        _db_connection.row_factory = aiosqlite.Row
        logger.info(f"数据库连接已创建: {DB_PATH}")
        await migrate_database()

async def close_db_pool():
    """关闭数据库连接"""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
        logger.info("数据库连接已关闭。")

async def migrate_database():
    """检查并执行数据库迁移"""
    await _db_connection.execute("PRAGMA foreign_keys = ON")

    async with _db_connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_info'") as cursor:
        if await cursor.fetchone() is None:
            logger.info("未检测到数据库版本，将进行全新安装...")
            await _create_all_tables_v5(_db_connection)
            await _db_connection.execute("INSERT INTO db_info (version) VALUES (?)", (LATEST_DB_VERSION,))
            await _db_connection.commit()
            logger.info(f"数据库已初始化到最新版本: v{LATEST_DB_VERSION}")
            return

    async with _db_connection.execute("SELECT version FROM db_info") as cursor:
        row = await cursor.fetchone()
        current_version = row[0] if row else 0
    
    logger.info(f"当前数据库版本: v{current_version}, 最新版本: v{LATEST_DB_VERSION}")

    if current_version < LATEST_DB_VERSION:
        logger.info("检测到数据库需要升级...")
        for version in sorted(MIGRATION_TASKS.keys()):
            if current_version < version:
                logger.info(f"正在执行数据库升级: v{current_version} -> v{version} ...")
                try:
                    async with _db_connection.transaction():
                        await MIGRATION_TASKS[version](_db_connection)
                        await _db_connection.execute("UPDATE db_info SET version = ?", (version,))
                    logger.info(f"v{current_version} -> v{version} 升级成功！")
                    current_version = version
                except Exception as e:
                    logger.error(f"数据库 v{current_version} -> v{version} 升级失败，已回滚: {e}", exc_info=True)
                    raise
        logger.info("数据库升级完成！")
    else:
        logger.info("数据库结构已是最新。")


async def _create_all_tables_v5(conn: aiosqlite.Connection):
    """创建版本5（最新）的所有表结构"""
    await conn.execute("CREATE TABLE IF NOT EXISTS db_info (version INTEGER NOT NULL)")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS sects (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
            leader_id TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 1,
            funds INTEGER NOT NULL DEFAULT 0
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY,
            level_index INTEGER NOT NULL,
            spiritual_root TEXT NOT NULL,
            experience INTEGER NOT NULL,
            gold INTEGER NOT NULL,
            last_check_in REAL NOT NULL,
            state TEXT NOT NULL,
            state_start_time REAL NOT NULL,
            sect_id INTEGER,
            sect_name TEXT,
            hp INTEGER NOT NULL,
            max_hp INTEGER NOT NULL,
            attack INTEGER NOT NULL,
            defense INTEGER NOT NULL,
            realm_id TEXT,
            realm_floor INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (sect_id) REFERENCES sects (id)
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            item_id TEXT NOT NULL, quantity INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES players (user_id),
            UNIQUE(user_id, item_id)
        )
    """)

@migration(2)
async def _upgrade_v1_to_v2(conn: aiosqlite.Connection):
    await conn.execute("ALTER TABLE inventory RENAME TO inventory_old")
    await conn.execute("""
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            item_id TEXT NOT NULL, quantity INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES players (user_id),
            UNIQUE(user_id, item_id)
        )
    """)
    await conn.execute("INSERT INTO inventory (user_id, item_id, quantity) SELECT user_id, item_id, quantity FROM inventory_old")
    await conn.execute("DROP TABLE inventory_old")

@migration(3)
async def _upgrade_v2_to_v3(conn: aiosqlite.Connection):
    cursor = await conn.execute("PRAGMA table_info(players)")
    columns = [row['name'] for row in await cursor.fetchall()]
    if 'hp' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN hp INTEGER NOT NULL DEFAULT 100")
    if 'max_hp' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN max_hp INTEGER NOT NULL DEFAULT 100")
    if 'attack' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN attack INTEGER NOT NULL DEFAULT 10")
    if 'defense' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN defense INTEGER NOT NULL DEFAULT 5")

@migration(4)
async def _upgrade_v3_to_v4(conn: aiosqlite.Connection):
    cursor = await conn.execute("PRAGMA table_info(players)")
    columns = [row['name'] for row in await cursor.fetchall()]
    if 'realm_id' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN realm_id TEXT")
    if 'realm_floor' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN realm_floor INTEGER NOT NULL DEFAULT 0")

@migration(5)
async def _upgrade_v4_to_v5(conn: aiosqlite.Connection):
    """升级数据库 v4 -> v5: 将 level(TEXT) 迁移到 level_index(INTEGER)"""
    logger.info("开始执行 v4 -> v5 数据库迁移...")
    
    await conn.execute("ALTER TABLE players RENAME TO players_old_v4")
    
    await conn.execute("""
        CREATE TABLE players (
            user_id TEXT PRIMARY KEY, level_index INTEGER NOT NULL, spiritual_root TEXT NOT NULL,
            experience INTEGER NOT NULL, gold INTEGER NOT NULL, last_check_in REAL NOT NULL,
            state TEXT NOT NULL, state_start_time REAL NOT NULL, sect_id INTEGER,
            sect_name TEXT, hp INTEGER NOT NULL, max_hp INTEGER NOT NULL,
            attack INTEGER NOT NULL, defense INTEGER NOT NULL,
            realm_id TEXT, realm_floor INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (sect_id) REFERENCES sects (id)
        )
    """)
    
    level_name_to_index_map = {info['level_name']: info['index'] for info in config.level_data}
    
    async with conn.execute("SELECT * FROM players_old_v4") as cursor:
        async for row in cursor:
            old_data = dict(row)
            level_name = old_data.pop('level')
            level_index = level_name_to_index_map.get(level_name, 0)
            
            new_data = old_data
            new_data['level_index'] = level_index
            
            columns = ", ".join(new_data.keys())
            placeholders = ", ".join([f":{k}" for k in new_data.keys()])
            await conn.execute(f"INSERT INTO players ({columns}) VALUES ({placeholders})", new_data)
            
    await conn.execute("DROP TABLE players_old_v4")
    logger.info("v4 -> v5 数据库迁移完成！")


async def get_player_by_id(user_id: str) -> Optional[Player]:
    async with _db_connection.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        return Player(**dict(row)) if row else None

async def create_player(player: Player):
    player_fields = [f.name for f in fields(Player)]
    columns = ", ".join(player_fields)
    placeholders = ", ".join([f":{f}" for f in player_fields])
    sql = f"INSERT INTO players ({columns}) VALUES ({placeholders})"
    
    await _db_connection.execute(sql, player.__dict__)
    await _db_connection.commit()

async def update_player(player: Player):
    player_fields = [f.name for f in fields(Player) if f.name != 'user_id']
    set_clause = ", ".join([f"{f} = :{f}" for f in player_fields])
    sql = f"UPDATE players SET {set_clause} WHERE user_id = :user_id"

    await _db_connection.execute(sql, player.__dict__)
    await _db_connection.commit()


async def update_players_in_transaction(players: List[Player]):
    if not players:
        return
        
    player_fields = [f.name for f in fields(Player) if f.name != 'user_id']
    set_clause = ", ".join([f"{f} = :{f}" for f in player_fields])
    sql = f"UPDATE players SET {set_clause} WHERE user_id = :user_id"
    
    try:
        async with _db_connection.transaction():
            for player in players:
                await _db_connection.execute(sql, player.__dict__)
    except aiosqlite.Error as e:
        logger.error(f"批量更新玩家事务失败: {e}")
        raise

async def create_sect(sect_name: str, leader_id: str) -> int:
    async with _db_connection.execute("INSERT INTO sects (name, leader_id) VALUES (?, ?)", (sect_name, leader_id)) as cursor:
        await _db_connection.commit()
        return cursor.lastrowid

async def delete_sect(sect_id: int):
    await _db_connection.execute("DELETE FROM sects WHERE id = ?", (sect_id,))
    await _db_connection.commit()

async def get_sect_by_name(sect_name: str) -> Optional[Dict[str, Any]]:
    async with _db_connection.execute("SELECT * FROM sects WHERE name = ?", (sect_name,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_sect_by_id(sect_id: int) -> Optional[Dict[str, Any]]:
    async with _db_connection.execute("SELECT * FROM sects WHERE id = ?", (sect_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_sect_members(sect_id: int) -> List[Player]:
    async with _db_connection.execute("SELECT * FROM players WHERE sect_id = ?", (sect_id,)) as cursor:
        rows = await cursor.fetchall()
        return [Player(**dict(row)) for row in rows]

async def update_player_sect(user_id: str, sect_id: Optional[int], sect_name: Optional[str]):
    await _db_connection.execute("UPDATE players SET sect_id = ?, sect_name = ? WHERE user_id = ?", (sect_id, sect_name, user_id))
    await _db_connection.commit()

async def get_inventory_by_user_id(user_id: str) -> List[Dict[str, Any]]:
    async with _db_connection.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ?", (user_id,)) as cursor:
        rows = await cursor.fetchall()
        inventory_list = []
        for row in rows:
            item_id, quantity = row['item_id'], row['quantity']
            item_info = config.item_data.get(str(item_id))
            if item_info:
                 inventory_list.append({
                    "item_id": item_id, "name": item_info.name,
                    "quantity": quantity, "description": item_info.description,
                    "rank": item_info.rank, "type": item_info.type
                })
            else:
                inventory_list.append({
                    "item_id": item_id, "name": f"未知物品(ID:{item_id})",
                    "quantity": quantity, "description": "此物品信息已丢失",
                    "rank": "未知", "type": "未知"
                })
        return inventory_list

async def get_item_from_inventory(user_id: str, item_id: str) -> Optional[Dict[str, Any]]:
    async with _db_connection.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_items_to_inventory_in_transaction(user_id: str, items: Dict[str, int]):
    try:
        async with _db_connection.transaction():
            for item_id, quantity in items.items():
                await _db_connection.execute("""
                    INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity;
                """, (user_id, item_id, quantity))
    except aiosqlite.Error as e:
        logger.error(f"批量添加物品事务失败: {e}")
        raise

async def remove_item_from_inventory(user_id: str, item_id: str, quantity: int = 1) -> bool:
    try:
        async with _db_connection.transaction():
            cursor = await _db_connection.execute("""
                UPDATE inventory SET quantity = quantity - ? 
                WHERE user_id = ? AND item_id = ? AND quantity >= ?
            """, (quantity, user_id, item_id, quantity))
            
            if cursor.rowcount == 0:
                return False

            await _db_connection.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0", (user_id, item_id))
        return True
    except aiosqlite.Error as e:
        logger.error(f"移除物品事务失败: {e}")
        return False
        
async def transactional_buy_item(user_id: str, item_id: str, quantity: int, total_cost: int) -> Tuple[bool, str]:
    try:
        async with _db_connection.transaction():
            cursor = await _db_connection.execute(
                "UPDATE players SET gold = gold - ? WHERE user_id = ? AND gold >= ?",
                (total_cost, user_id, total_cost)
            )
            if cursor.rowcount == 0:
                return False, "ERROR_INSUFFICIENT_FUNDS"
            await _db_connection.execute("""
                INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity;
            """, (user_id, item_id, quantity))
        return True, "SUCCESS"
    except aiosqlite.Error as e:
        logger.error(f"购买物品事务失败: {e}")
        return False, "ERROR_DATABASE"

async def transactional_apply_item_effect(user_id: str, item_id: str, quantity: int, effect: PlayerEffect) -> bool:
    try:
        async with _db_connection.transaction():
            cursor = await _db_connection.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ? AND quantity >= ?",
                (quantity, user_id, item_id, quantity)
            )
            if cursor.rowcount == 0: return False
            await _db_connection.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0", (user_id, item_id))
            await _db_connection.execute(
                """
                UPDATE players 
                SET experience = experience + ?,
                    gold = gold + ?,
                    hp = MIN(max_hp, hp + ?)
                WHERE user_id = ?
                """,
                (effect.experience, effect.gold, effect.hp, user_id)
            )
        return True
    except aiosqlite.Error as e:
        logger.error(f"使用物品事务失败: {e}")
        return False