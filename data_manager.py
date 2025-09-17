# data_manager.py

import time
import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable, Awaitable
from dataclasses import fields

from astrbot.api import logger
from astrbot.api.star import StarTools

from .config_manager import config
from .models import Player, PlayerEffect, Item, ActiveWorldBoss, Boss

DATA_DIR = StarTools.get_data_dir("xiuxian")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / config.DATABASE_FILE

LATEST_DB_VERSION = 8

MIGRATION_TASKS: Dict[int, Callable[[aiosqlite.Connection], Awaitable[None]]] = {}

def migration(version: int):
    def decorator(func: Callable[[aiosqlite.Connection], Awaitable[None]]):
        MIGRATION_TASKS[version] = func
        return func
    return decorator

_db_connection: Optional[aiosqlite.Connection] = None

async def init_db_pool():
    global _db_connection
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(DB_PATH)
        _db_connection.row_factory = aiosqlite.Row
        logger.info(f"数据库连接已创建: {DB_PATH}")
        await migrate_database()

async def close_db_pool():
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
        logger.info("数据库连接已关闭。")

async def migrate_database():
    await _db_connection.execute("PRAGMA foreign_keys = ON")
    async with _db_connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_info'") as cursor:
        if await cursor.fetchone() is None:
            logger.info("未检测到数据库版本，将进行全新安装...")
            await _db_connection.execute("BEGIN")
            # 注意：全新安装直接创建 v8 结构
            await _create_all_tables_v8(_db_connection)
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
                is_v5_migration = (version == 5)
                try:
                    if is_v5_migration:
                        await _db_connection.execute("PRAGMA foreign_keys = OFF")
                    
                    await _db_connection.execute("BEGIN")
                    await MIGRATION_TASKS[version](_db_connection)
                    await _db_connection.execute("UPDATE db_info SET version = ?", (version,))
                    await _db_connection.commit()
                    
                    logger.info(f"v{current_version} -> v{version} 升级成功！")
                    current_version = version
                except Exception as e:
                    await _db_connection.rollback()
                    logger.error(f"数据库 v{current_version} -> v{version} 升级失败，已回滚: {e}", exc_info=True)
                    raise
                finally:
                    if is_v5_migration:
                        await _db_connection.execute("PRAGMA foreign_keys = ON")
        logger.info("数据库升级完成！")
    else:
        logger.info("数据库结构已是最新。")

async def _create_all_tables_v8(conn: aiosqlite.Connection):
    """用于全新安装时直接创建最新版（v8）的数据库表结构"""
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
            user_id TEXT PRIMARY KEY, level_index INTEGER NOT NULL, spiritual_root TEXT NOT NULL,
            experience INTEGER NOT NULL, gold INTEGER NOT NULL, last_check_in REAL NOT NULL,
            state TEXT NOT NULL, state_start_time REAL NOT NULL, sect_id INTEGER, sect_name TEXT,
            hp INTEGER NOT NULL, max_hp INTEGER NOT NULL, attack INTEGER NOT NULL, defense INTEGER NOT NULL,
            realm_id TEXT, realm_floor INTEGER NOT NULL DEFAULT 0, realm_data TEXT,
            FOREIGN KEY (sect_id) REFERENCES sects (id) ON DELETE SET NULL
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, item_id TEXT NOT NULL,
            quantity INTEGER NOT NULL, FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE,
            UNIQUE(user_id, item_id)
        )
    """)
    # 新的世界Boss表结构 (v8)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS active_world_bosses (
            boss_id TEXT PRIMARY KEY,
            current_hp INTEGER NOT NULL,
            max_hp INTEGER NOT NULL,
            spawned_at REAL NOT NULL,
            level_index INTEGER NOT NULL
        )
    """)
    # 新的伤害贡献表结构 (v8)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS world_boss_participants (
            boss_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            total_damage INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (boss_id, user_id),
            FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE
        )
    """)

@migration(2)
async def _upgrade_v1_to_v2(conn: aiosqlite.Connection):
    await conn.execute("PRAGMA foreign_keys = OFF")
    await conn.execute("ALTER TABLE inventory RENAME TO inventory_old")
    await conn.execute("""
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            item_id TEXT NOT NULL, quantity INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE,
            UNIQUE(user_id, item_id)
        )
    """)
    await conn.execute("INSERT INTO inventory (user_id, item_id, quantity) SELECT user_id, item_id, quantity FROM inventory_old")
    await conn.execute("DROP TABLE inventory_old")
    await conn.execute("PRAGMA foreign_keys = ON")

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
            FOREIGN KEY (sect_id) REFERENCES sects (id) ON DELETE SET NULL
        )
    """)
    level_name_to_index_map = {info['level_name']: i for i, info in enumerate(config.level_data)}
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

@migration(6)
async def _upgrade_v5_to_v6(conn: aiosqlite.Connection):
    logger.info("开始执行 v5 -> v6 数据库迁移...")
    cursor = await conn.execute("PRAGMA table_info(players)")
    columns = [row['name'] for row in await cursor.fetchall()]
    if 'realm_data' not in columns:
        await conn.execute("ALTER TABLE players ADD COLUMN realm_data TEXT")
    logger.info("v5 -> v6 数据库迁移完成！")

@migration(7)
async def _upgrade_v6_to_v7(conn: aiosqlite.Connection):
    logger.info("开始执行 v6 -> v7 数据库迁移...")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS world_boss (
            id INTEGER PRIMARY KEY, boss_template_id TEXT NOT NULL, current_hp INTEGER NOT NULL,
            max_hp INTEGER NOT NULL, generated_at REAL NOT NULL
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS world_boss_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL UNIQUE, total_damage INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE
        )
    """)
    logger.info("v6 -> v7 数据库迁移完成！")

@migration(8)
async def _upgrade_v7_to_v8(conn: aiosqlite.Connection):
    logger.info("开始执行 v7 -> v8 数据库迁移...")
    await conn.execute("DROP TABLE IF EXISTS world_boss")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS active_world_bosses (
            boss_id TEXT PRIMARY KEY,
            current_hp INTEGER NOT NULL,
            max_hp INTEGER NOT NULL,
            spawned_at REAL NOT NULL,
            level_index INTEGER NOT NULL
        )
    """)
    await conn.execute("DROP TABLE IF EXISTS world_boss_participants")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS world_boss_participants (
            boss_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            total_damage INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (boss_id, user_id),
            FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE
        )
    """)
    logger.info("v7 -> v8 数据库迁移完成！")

async def get_active_bosses() -> List[ActiveWorldBoss]:
    async with _db_connection.execute("SELECT * FROM active_world_bosses") as cursor:
        rows = await cursor.fetchall()
        return [ActiveWorldBoss(**dict(row)) for row in rows]

async def create_active_boss(boss: ActiveWorldBoss):
    await _db_connection.execute(
        "INSERT INTO active_world_bosses (boss_id, current_hp, max_hp, spawned_at, level_index) VALUES (?, ?, ?, ?, ?)",
        (boss.boss_id, boss.current_hp, boss.max_hp, boss.spawned_at, boss.level_index)
    )
    await _db_connection.commit()

async def update_active_boss_hp(boss_id: str, new_hp: int):
    await _db_connection.execute(
        "UPDATE active_world_bosses SET current_hp = ? WHERE boss_id = ?",
        (new_hp, boss_id)
    )
    await _db_connection.commit()

async def delete_active_boss(boss_id: str):
    await _db_connection.execute("DELETE FROM active_world_bosses WHERE boss_id = ?", (boss_id,))
    await _db_connection.commit()

async def record_boss_damage(boss_id: str, user_id: str, user_name: str, damage: int):
    await _db_connection.execute("""
        INSERT INTO world_boss_participants (boss_id, user_id, user_name, total_damage) VALUES (?, ?, ?, ?)
        ON CONFLICT(boss_id, user_id) DO UPDATE SET total_damage = total_damage + excluded.total_damage;
    """, (boss_id, user_id, user_name, damage))
    await _db_connection.commit()

async def get_boss_participants(boss_id: str) -> List[Dict[str, Any]]:
    sql = "SELECT user_id, user_name, total_damage FROM world_boss_participants WHERE boss_id = ? ORDER BY total_damage DESC"
    async with _db_connection.execute(sql, (boss_id,)) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def clear_boss_data(boss_id: str):
    try:
        await _db_connection.execute("BEGIN")
        await _db_connection.execute("DELETE FROM active_world_bosses WHERE boss_id = ?", (boss_id,))
        await _db_connection.execute("DELETE FROM world_boss_participants WHERE boss_id = ?", (boss_id,))
        await _db_connection.commit()
        logger.info(f"Boss {boss_id} 的数据已清理。")
    except aiosqlite.Error as e:
        await _db_connection.rollback()
        logger.error(f"清理Boss {boss_id} 数据失败: {e}")

async def get_top_players(limit: int) -> List['Player']:
    async with _db_connection.execute(
        "SELECT * FROM players ORDER BY level_index DESC, experience DESC LIMIT ?", (limit,)
    ) as cursor:
        rows = await cursor.fetchall()
        return [Player(**dict(row)) for row in rows]

async def get_player_by_id(user_id: str) -> Optional['Player']:
    async with _db_connection.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        return Player(**dict(row)) if row else None

async def create_player(player: 'Player'):
    player_fields = [f.name for f in fields(Player)]
    columns = ", ".join(player_fields)
    placeholders = ", ".join([f":{f}" for f in player_fields])
    sql = f"INSERT INTO players ({columns}) VALUES ({placeholders})"
    await _db_connection.execute(sql, player.__dict__)
    await _db_connection.commit()

async def update_player(player: 'Player'):
    player_fields = [f.name for f in fields(Player) if f.name != 'user_id']
    set_clause = ", ".join([f"{f} = :{f}" for f in player_fields])
    sql = f"UPDATE players SET {set_clause} WHERE user_id = :user_id"
    await _db_connection.execute(sql, player.__dict__)
    await _db_connection.commit()

async def update_players_in_transaction(players: List['Player']):
    if not players:
        return
    player_fields = [f.name for f in fields(Player) if f.name != 'user_id']
    set_clause = ", ".join([f"{f} = :{f}" for f in player_fields])
    sql = f"UPDATE players SET {set_clause} WHERE user_id = :user_id"
    try:
        await _db_connection.execute("BEGIN")
        for player in players:
            await _db_connection.execute(sql, player.__dict__)
        await _db_connection.commit()
    except aiosqlite.Error as e:
        await _db_connection.rollback()
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

async def get_sect_members(sect_id: int) -> List['Player']:
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
        await _db_connection.execute("BEGIN")
        for item_id, quantity in items.items():
            await _db_connection.execute("""
                INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity;
            """, (user_id, item_id, quantity))
        await _db_connection.commit()
    except aiosqlite.Error as e:
        await _db_connection.rollback()
        logger.error(f"批量添加物品事务失败: {e}")
        raise

async def remove_item_from_inventory(user_id: str, item_id: str, quantity: int = 1) -> bool:
    try:
        await _db_connection.execute("BEGIN")
        cursor = await _db_connection.execute("""
            UPDATE inventory SET quantity = quantity - ? 
            WHERE user_id = ? AND item_id = ? AND quantity >= ?
        """, (quantity, user_id, item_id, quantity))
        
        if cursor.rowcount == 0:
            await _db_connection.rollback()
            return False

        await _db_connection.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0", (user_id, item_id))
        await _db_connection.commit()
        return True
    except aiosqlite.Error as e:
        await _db_connection.rollback()
        logger.error(f"移除物品事务失败: {e}")
        return False
        
async def transactional_buy_item(user_id: str, item_id: str, quantity: int, total_cost: int) -> Tuple[bool, str]:
    try:
        await _db_connection.execute("BEGIN")
        cursor = await _db_connection.execute(
            "UPDATE players SET gold = gold - ? WHERE user_id = ? AND gold >= ?",
            (total_cost, user_id, total_cost)
        )
        if cursor.rowcount == 0:
            await _db_connection.rollback()
            return False, "ERROR_INSUFFICIENT_FUNDS"
        
        await _db_connection.execute("""
            INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity;
        """, (user_id, item_id, quantity))
        
        await _db_connection.commit()
        return True, "SUCCESS"
    except aiosqlite.Error as e:
        await _db_connection.rollback()
        logger.error(f"购买物品事务失败: {e}")
        return False, "ERROR_DATABASE"

async def transactional_apply_item_effect(user_id: str, item_id: str, quantity: int, effect: 'PlayerEffect') -> bool:
    try:
        await _db_connection.execute("BEGIN")
        cursor = await _db_connection.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ? AND quantity >= ?",
            (quantity, user_id, item_id, quantity)
        )
        if cursor.rowcount == 0:
            await _db_connection.rollback()
            return False
            
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
        await _db_connection.commit()
        return True
    except aiosqlite.Error as e:
        await _db_connection.rollback()
        logger.error(f"使用物品事务失败: {e}")
        return False