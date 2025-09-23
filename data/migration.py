# data/migration.py

import aiosqlite
from typing import Dict, Callable, Awaitable
from astrbot.api import logger
from ..config_manager import ConfigManager


LATEST_DB_VERSION = 10

MIGRATION_TASKS: Dict[int, Callable[[aiosqlite.Connection, ConfigManager], Awaitable[None]]] = {}

def migration(version: int):
    """注册数据库迁移任务的装饰器"""

    def decorator(func: Callable[[aiosqlite.Connection, ConfigManager], Awaitable[None]]):
        MIGRATION_TASKS[version] = func
        return func
    return decorator

async def _create_all_tables_v10(conn: aiosqlite.Connection):
    """
    一步到位创建最新版本(v10)的数据库表结构
    """
    await conn.execute("CREATE TABLE IF NOT EXISTS db_info (version INTEGER NOT NULL)")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS sects (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
            leader_id TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 1,
            funds INTEGER NOT NULL DEFAULT 0
        )
    """)
    # 关键修改：CREATE TABLE 语句包含了所有新字段
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY, name TEXT NOT NULL, level_index INTEGER NOT NULL, 
            spiritual_root TEXT NOT NULL, experience INTEGER NOT NULL, gold INTEGER NOT NULL, 
            state TEXT NOT NULL, state_start_time REAL NOT NULL, sect_id INTEGER, sect_name TEXT,
            hp INTEGER NOT NULL, max_hp INTEGER NOT NULL, attack INTEGER NOT NULL, defense INTEGER NOT NULL,
            mp INTEGER NOT NULL, max_mp INTEGER NOT NULL, speed INTEGER NOT NULL, aptitude INTEGER NOT NULL,
            insight INTEGER NOT NULL, luck INTEGER NOT NULL, divine_sense INTEGER NOT NULL,
            crit_rate REAL NOT NULL, crit_damage REAL NOT NULL,
            weapon_id TEXT, armor_id TEXT, accessory_id TEXT, magic_tool_id TEXT,
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
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS active_world_bosses (
            boss_id TEXT PRIMARY KEY,
            current_hp INTEGER NOT NULL,
            max_hp INTEGER NOT NULL,
            spawned_at REAL NOT NULL,
            level_index INTEGER NOT NULL
        )
    """)
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

class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self, conn: aiosqlite.Connection, config_manager: ConfigManager):
        self.conn = conn
        self.config_manager = config_manager

    async def migrate(self):
        await self.conn.execute("PRAGMA foreign_keys = ON")
        async with self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_info'") as cursor:
            if await cursor.fetchone() is None:
                logger.info("未检测到数据库版本，将进行全新安装...")
                await self.conn.execute("BEGIN")
                # 关键修改：确保全新安装时调用的是最新版本的建表函数
                await _create_all_tables_v10(self.conn)
                await self.conn.execute("INSERT INTO db_info (version) VALUES (?)", (LATEST_DB_VERSION,))
                await self.conn.commit()
                logger.info(f"数据库已初始化到最新版本: v{LATEST_DB_VERSION}")
                return

        async with self.conn.execute("SELECT version FROM db_info") as cursor:
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
                            await self.conn.execute("PRAGMA foreign_keys = OFF")

                        await self.conn.execute("BEGIN")
                        await MIGRATION_TASKS[version](self.conn, self.config_manager)
                        await self.conn.execute("UPDATE db_info SET version = ?", (version,))
                        await self.conn.commit()

                        logger.info(f"v{current_version} -> v{version} 升级成功！")
                        current_version = version
                    except Exception as e:
                        await self.conn.rollback()
                        logger.error(f"数据库 v{current_version} -> v{version} 升级失败，已回滚: {e}", exc_info=True)
                        raise
                    finally:
                        if is_v5_migration:
                            await self.conn.execute("PRAGMA foreign_keys = ON")
            logger.info("数据库升级完成！")
        else:
            logger.info("数据库结构已是最新。")


# --- 旧的迁移任务，已恢复函数体 ---

@migration(2)
async def _upgrade_v1_to_v2(conn: aiosqlite.Connection, config_manager: ConfigManager):
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
async def _upgrade_v2_to_v3(conn: aiosqlite.Connection, config_manager: ConfigManager):
    cursor = await conn.execute("PRAGMA table_info(players)")
    columns = [row['name'] for row in await cursor.fetchall()]
    if 'hp' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN hp INTEGER NOT NULL DEFAULT 100")
    if 'max_hp' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN max_hp INTEGER NOT NULL DEFAULT 100")
    if 'attack' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN attack INTEGER NOT NULL DEFAULT 10")
    if 'defense' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN defense INTEGER NOT NULL DEFAULT 5")

@migration(4)
async def _upgrade_v3_to_v4(conn: aiosqlite.Connection, config_manager: ConfigManager):
    cursor = await conn.execute("PRAGMA table_info(players)")
    columns = [row['name'] for row in await cursor.fetchall()]
    if 'realm_id' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN realm_id TEXT")
    if 'realm_floor' not in columns: await conn.execute("ALTER TABLE players ADD COLUMN realm_floor INTEGER NOT NULL DEFAULT 0")

@migration(5)
async def _upgrade_v4_to_v5(conn: aiosqlite.Connection, config_manager: ConfigManager):
    logger.info("开始执行 v4 -> v5 数据库迁移...")
    async with conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players'") as cursor:
        if await cursor.fetchone() is None:
            logger.warning("在 v4->v5 迁移中未找到 'players' 表，将跳过此迁移步骤。")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id TEXT PRIMARY KEY, level_index INTEGER NOT NULL, spiritual_root TEXT NOT NULL,
                    experience INTEGER NOT NULL, gold INTEGER NOT NULL, last_check_in REAL NOT NULL,
                    state TEXT NOT NULL, state_start_time REAL NOT NULL, sect_id INTEGER,
                    sect_name TEXT, hp INTEGER NOT NULL, max_hp INTEGER NOT NULL,
                    attack INTEGER NOT NULL, defense INTEGER NOT NULL,
                    realm_id TEXT, realm_floor INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (sect_id) REFERENCES sects (id) ON DELETE SET NULL
                )
            """)
            return

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
    level_name_to_index_map = {info['level_name']: i for i, info in enumerate(config_manager.level_data)}
    async with conn.execute("SELECT * FROM players_old_v4") as cursor:
        async for row in cursor:
            old_data = dict(row)
            level_name = old_data.pop('level', None)
            level_index = level_name_to_index_map.get(level_name, 0)
            
            new_data = {
                'user_id': old_data.get('user_id'),
                'level_index': level_index,
                'spiritual_root': old_data.get('spiritual_root', '未知'),
                'experience': old_data.get('experience', 0),
                'gold': old_data.get('gold', 0),
                'last_check_in': old_data.get('last_check_in', 0.0),
                'state': old_data.get('state', '空闲'),
                'state_start_time': old_data.get('state_start_time', 0.0),
                'sect_id': old_data.get('sect_id'),
                'sect_name': old_data.get('sect_name'),
                'hp': old_data.get('hp', 100),
                'max_hp': old_data.get('max_hp', 100),
                'attack': old_data.get('attack', 10),
                'defense': old_data.get('defense', 5),
                'realm_id': old_data.get('realm_id'),
                'realm_floor': old_data.get('realm_floor', 0)
            }

            columns = ", ".join(new_data.keys())
            placeholders = ", ".join([f":{k}" for k in new_data.keys()])
            await conn.execute(f"INSERT INTO players ({columns}) VALUES ({placeholders})", new_data)
    
    await conn.execute("DROP TABLE players_old_v4")
    logger.info("v4 -> v5 数据库迁移完成！")

@migration(6)
async def _upgrade_v5_to_v6(conn: aiosqlite.Connection, config_manager: ConfigManager):
    logger.info("开始执行 v5 -> v6 数据库迁移...")
    cursor = await conn.execute("PRAGMA table_info(players)")
    columns = [row['name'] for row in await cursor.fetchall()]
    if 'realm_data' not in columns:
        await conn.execute("ALTER TABLE players ADD COLUMN realm_data TEXT")
    logger.info("v5 -> v6 数据库迁移完成！")

@migration(7)
async def _upgrade_v6_to_v7(conn: aiosqlite.Connection, config_manager: ConfigManager):
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
async def _upgrade_v7_to_v8(conn: aiosqlite.Connection, config_manager: ConfigManager):
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


# --- 新增的迁移任务 ---

@migration(9)
async def _upgrade_v8_to_v9(conn: aiosqlite.Connection, config_manager: ConfigManager):
    """
    为已有数据库的用户添加新属性列
    """
    logger.info("开始执行 v8 -> v9 数据库迁移...")
    cursor = await conn.execute("PRAGMA table_info(players)")
    columns = [row['name'] for row in await cursor.fetchall()]
    
    columns_to_add = {
        'mp': "INTEGER NOT NULL DEFAULT 50",
        'max_mp': "INTEGER NOT NULL DEFAULT 50",
        'speed': "INTEGER NOT NULL DEFAULT 5",
        'aptitude': "INTEGER NOT NULL DEFAULT 10",
        'insight': "INTEGER NOT NULL DEFAULT 10",
        'luck': "INTEGER NOT NULL DEFAULT 5",
        'divine_sense': "INTEGER NOT NULL DEFAULT 20",
        'crit_rate': "REAL NOT NULL DEFAULT 0.05",
        'crit_damage': "REAL NOT NULL DEFAULT 1.5",
        'weapon_id': "TEXT",
        'armor_id': "TEXT",
        'accessory_id': "TEXT",
        'magic_tool_id': "TEXT"
    }

    for col, definition in columns_to_add.items():
        if col not in columns:
            await conn.execute(f"ALTER TABLE players ADD COLUMN {col} {definition}")
            logger.info(f"成功为 'players' 表添加新列: {col}")
            
    logger.info("v8 -> v9 数据库迁移完成！")
@migration(10)
async def _upgrade_v9_to_v10(conn: aiosqlite.Connection, config_manager: ConfigManager):
    logger.info("开始执行 v9 -> v10 数据库迁移...")
    cursor = await conn.execute("PRAGMA table_info(players)")
    columns = [row['name'] for row in await cursor.fetchall()]
    if 'name' not in columns:
        await conn.execute("ALTER TABLE players ADD COLUMN name TEXT NOT NULL DEFAULT '无名氏'")
        logger.info("成功为 'players' 表添加新列: name")
    logger.info("v9 -> v10 数据库迁移完成！")
