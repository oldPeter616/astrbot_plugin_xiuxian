# migration_manager.py

import aiosqlite
from typing import Callable, Awaitable, Dict
from astrbot.api import logger
from ..config_manager import config



class MigrationManager:
    """数据库迁移管理器，负责版本检测、初始化、升级"""

    def __init__(self, target_version: int):
        self.target_version = target_version
        self.migrations: Dict[
            int, Callable[[aiosqlite.Connection], Awaitable[None]]
        ] = {}
        self._register_migrations()

    def register(self, version: int):
        """装饰器注册迁移函数"""

        def decorator(func: Callable[[aiosqlite.Connection], Awaitable[None]]):
            self.migrations[version] = func
            return func

        return decorator

    async def migrate(self, conn: aiosqlite.Connection):
        await conn.execute("PRAGMA foreign_keys = ON")

        # 检查是否存在 db_info
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='db_info'"
        ) as cursor:
            if await cursor.fetchone() is None:
                logger.info("未检测到数据库版本，将进行全新安装...")
                await conn.execute("BEGIN")
                await self._create_all_tables_v8(conn)
                await conn.execute(
                    "INSERT INTO db_info (version) VALUES (?)", (self.target_version,)
                )
                await conn.commit()
                logger.info(f"数据库已初始化到最新版本: v{self.target_version}")
                return

        async with conn.execute("SELECT version FROM db_info") as cursor:
            row = await cursor.fetchone()
            current_version = row[0] if row else 0

        logger.info(
            f"当前数据库版本: v{current_version}, 最新版本: v{self.target_version}"
        )
        if current_version < self.target_version:
            logger.info("检测到数据库需要升级...")
            for version in sorted(self.migrations.keys()):
                if current_version < version:
                    logger.info(
                        f"正在执行数据库升级: v{current_version} -> v{version} ..."
                    )
                    is_v5_migration = version == 5
                    try:
                        if is_v5_migration:
                            await conn.execute("PRAGMA foreign_keys = OFF")

                        await conn.execute("BEGIN")
                        await self.migrations[version](conn)
                        await conn.execute("UPDATE db_info SET version = ?", (version,))
                        await conn.commit()
                        logger.info(f"v{current_version} -> v{version} 升级成功！")
                        current_version = version
                    except Exception as e:
                        await conn.rollback()
                        logger.error(
                            f"数据库 v{current_version} -> v{version} 升级失败，已回滚: {e}",
                            exc_info=True,
                        )
                        raise
                    finally:
                        if is_v5_migration:
                            await conn.execute("PRAGMA foreign_keys = ON")
            logger.info("数据库升级完成！")
        else:
            logger.info("数据库结构已是最新。")

    async def _create_all_tables_v8(self, conn: aiosqlite.Connection):
        """用于全新安装时直接创建最新版（v8）的数据库表结构"""
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS db_info (version INTEGER NOT NULL)"
        )
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


    def _register_migrations(self):
        """注册迁移"""
        @self.register(2)
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
            await conn.execute(
                "INSERT INTO inventory (user_id, item_id, quantity) SELECT user_id, item_id, quantity FROM inventory_old"
            )
            await conn.execute("DROP TABLE inventory_old")
            await conn.execute("PRAGMA foreign_keys = ON")


        @self.register(3)
        async def _upgrade_v2_to_v3(conn: aiosqlite.Connection):
            cursor = await conn.execute("PRAGMA table_info(players)")
            columns = [row["name"] for row in await cursor.fetchall()]
            if "hp" not in columns:
                await conn.execute(
                    "ALTER TABLE players ADD COLUMN hp INTEGER NOT NULL DEFAULT 100"
                )
            if "max_hp" not in columns:
                await conn.execute(
                    "ALTER TABLE players ADD COLUMN max_hp INTEGER NOT NULL DEFAULT 100"
                )
            if "attack" not in columns:
                await conn.execute(
                    "ALTER TABLE players ADD COLUMN attack INTEGER NOT NULL DEFAULT 10"
                )
            if "defense" not in columns:
                await conn.execute(
                    "ALTER TABLE players ADD COLUMN defense INTEGER NOT NULL DEFAULT 5"
                )


        @self.register(4)
        async def _upgrade_v3_to_v4(conn: aiosqlite.Connection):
            cursor = await conn.execute("PRAGMA table_info(players)")
            columns = [row["name"] for row in await cursor.fetchall()]
            if "realm_id" not in columns:
                await conn.execute("ALTER TABLE players ADD COLUMN realm_id TEXT")
            if "realm_floor" not in columns:
                await conn.execute(
                    "ALTER TABLE players ADD COLUMN realm_floor INTEGER NOT NULL DEFAULT 0"
                )


        @self.register(5)
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
            level_name_to_index_map = {
                info["level_name"]: i for i, info in enumerate(config.level_data)
            }
            async with conn.execute("SELECT * FROM players_old_v4") as cursor:
                async for row in cursor:
                    old_data = dict(row)
                    level_name = old_data.pop("level")
                    level_index = level_name_to_index_map.get(level_name, 0)
                    new_data = old_data
                    new_data["level_index"] = level_index
                    columns = ", ".join(new_data.keys())
                    placeholders = ", ".join([f":{k}" for k in new_data.keys()])
                    await conn.execute(
                        f"INSERT INTO players ({columns}) VALUES ({placeholders})", new_data
                    )
            await conn.execute("DROP TABLE players_old_v4")
            logger.info("v4 -> v5 数据库迁移完成！")


        @self.register(6)
        async def _upgrade_v5_to_v6(conn: aiosqlite.Connection):
            logger.info("开始执行 v5 -> v6 数据库迁移...")
            cursor = await conn.execute("PRAGMA table_info(players)")
            columns = [row["name"] for row in await cursor.fetchall()]
            if "realm_data" not in columns:
                await conn.execute("ALTER TABLE players ADD COLUMN realm_data TEXT")
            logger.info("v5 -> v6 数据库迁移完成！")


        @self.register(7)
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


        @self.register(8)
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
