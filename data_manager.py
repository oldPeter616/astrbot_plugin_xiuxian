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

LATEST_DB_VERSION = 4

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
    async with _db_connection.execute("PRAGMA foreign_keys = ON"):
        pass

    async with _db_connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_info'") as cursor:
        if await cursor.fetchone() is None:
            logger.info("未检测到数据库版本，将进行全新安装...")
            await _create_all_tables_v4() # Bug 修复：调用正确的最新版本建表函数
            await _db_connection.execute("INSERT INTO db_info (version) VALUES (?)", (LATEST_DB_VERSION,))
            await _db_connection.commit()
            logger.info(f"数据库已初始化到最新版本: v{LATEST_DB_VERSION}")
            return

    current_version = 0
    async with _db_connection.execute("SELECT version FROM db_info") as cursor:
        row = await cursor.fetchone()
        if row:
            current_version = row[0]

    logger.info(f"当前数据库版本: v{current_version}, 最新版本: v{LATEST_DB_VERSION}")

    if current_version < LATEST_DB_VERSION:
        logger.info("检测到数据库需要升级...")
        if current_version < 2:
            await _upgrade_v1_to_v2()
            current_version = 2
        if current_version < 3:
            await _upgrade_v2_to_v3()
            current_version = 3
        if current_version < 4:
            await _upgrade_v3_to_v4()
        
        logger.info("数据库升级完成！")
    else:
        logger.info("数据库结构已是最新。")

async def _create_all_tables_v4():
    """创建版本4（最新）的所有表结构"""
    await _db_connection.execute("CREATE TABLE IF NOT EXISTS db_info (version INTEGER NOT NULL)")
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS sects (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
            leader_id TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 1,
            funds INTEGER NOT NULL DEFAULT 0
        )
    """)
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY, level TEXT NOT NULL, spiritual_root TEXT NOT NULL,
            experience INTEGER NOT NULL, gold INTEGER NOT NULL, last_check_in REAL NOT NULL,
            state TEXT NOT NULL, state_start_time REAL NOT NULL, sect_id INTEGER,
            sect_name TEXT, hp INTEGER NOT NULL, max_hp INTEGER NOT NULL,
            attack INTEGER NOT NULL, defense INTEGER NOT NULL,
            realm_id TEXT, realm_floor INTEGER NOT NULL DEFAULT 0, -- 新增字段
            FOREIGN KEY (sect_id) REFERENCES sects (id)
        )
    """)
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            item_id TEXT NOT NULL, quantity INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES players (user_id),
            UNIQUE(user_id, item_id)
        )
    """)
    await _db_connection.commit()

async def _upgrade_v1_to_v2():
    """从版本1升级到版本2的迁移逻辑"""
    logger.info("正在执行数据库升级: v1 -> v2 ...")
    try:
        await _db_connection.execute("ALTER TABLE inventory RENAME TO inventory_old")
        await _db_connection.execute("""
            CREATE TABLE inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
                item_id TEXT NOT NULL, quantity INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES players (user_id),
                UNIQUE(user_id, item_id)
            )
        """)
        await _db_connection.execute("INSERT INTO inventory (user_id, item_id, quantity) SELECT user_id, item_id, quantity FROM inventory_old")
        await _db_connection.execute("DROP TABLE inventory_old")
        await _db_connection.execute("UPDATE db_info SET version = 2")
        await _db_connection.commit()
        logger.info("v1 -> v2 升级成功！")
    except Exception as e:
        await _db_connection.rollback()
        logger.error(f"数据库 v1 -> v2 升级失败，已回滚: {e}")
        raise

async def _upgrade_v2_to_v3():
    """从版本2升级到版本3的迁移逻辑 (已重构)"""
    logger.info("正在执行数据库升级: v2 -> v3 ...")
    try:
        async with _db_connection.execute("PRAGMA table_info(players)") as cursor:
            columns = [row['name'] for row in await cursor.fetchall()]
        
        if 'hp' not in columns:
            await _db_connection.execute("ALTER TABLE players ADD COLUMN hp INTEGER NOT NULL DEFAULT 100")
        if 'max_hp' not in columns:
            await _db_connection.execute("ALTER TABLE players ADD COLUMN max_hp INTEGER NOT NULL DEFAULT 100")
        if 'attack' not in columns:
            await _db_connection.execute("ALTER TABLE players ADD COLUMN attack INTEGER NOT NULL DEFAULT 10")
        if 'defense' not in columns:
            await _db_connection.execute("ALTER TABLE players ADD COLUMN defense INTEGER NOT NULL DEFAULT 5")

        await _db_connection.execute("UPDATE db_info SET version = 3")
        await _db_connection.commit()
        logger.info("v2 -> v3 升级成功！")
    except Exception as e:
        await _db_connection.rollback()
        logger.error(f"数据库 v2 -> v3 升级失败，已回滚: {e}")
        raise

async def _upgrade_v3_to_v4():
    """从版本3升级到版本4的迁移逻辑"""
    logger.info("正在执行数据库升级: v3 -> v4 ...")
    try:
        async with _db_connection.execute("PRAGMA table_info(players)") as cursor:
            columns = [row['name'] for row in await cursor.fetchall()]
        
        if 'realm_id' not in columns:
            await _db_connection.execute("ALTER TABLE players ADD COLUMN realm_id TEXT")
        if 'realm_floor' not in columns:
            await _db_connection.execute("ALTER TABLE players ADD COLUMN realm_floor INTEGER NOT NULL DEFAULT 0")

        await _db_connection.execute("UPDATE db_info SET version = 4")
        await _db_connection.commit()
        logger.info("v3 -> v4 升级成功！")
    except Exception as e:
        await _db_connection.rollback()
        logger.error(f"数据库 v3 -> v4 升级失败，已回滚: {e}")
        raise

async def get_player_by_id(user_id: str) -> Optional[Player]:
    """通过用户ID获取玩家数据"""
    async with _db_connection.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        return Player(**dict(row)) if row else None

async def create_player(player: Player):
    """创建新玩家"""
    await _db_connection.execute("""
        INSERT INTO players (user_id, level, spiritual_root, experience, gold, 
                             last_check_in, state, state_start_time, sect_id, 
                             sect_name, hp, max_hp, attack, defense, realm_id, realm_floor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        player.user_id, player.level, player.spiritual_root, player.experience,
        player.gold, player.last_check_in, player.state, player.state_start_time,
        player.sect_id, player.sect_name, player.hp, player.max_hp,
        player.attack, player.defense, player.realm_id, player.realm_floor
    ))
    await _db_connection.commit()

async def update_player(player: Player):
    """更新玩家数据"""
    await _db_connection.execute("""
        UPDATE players
        SET level = ?, spiritual_root = ?, experience = ?, gold = ?, last_check_in = ?, 
            state = ?, state_start_time = ?, sect_id = ?, sect_name = ?,
            hp = ?, max_hp = ?, attack = ?, defense = ?, 
            realm_id = ?, realm_floor = ?
        WHERE user_id = ?
    """, (
        player.level, player.spiritual_root, player.experience, player.gold,
        player.last_check_in, player.state, player.state_start_time,
        player.sect_id, player.sect_name, player.hp, player.max_hp,
        player.attack, player.defense, player.realm_id, player.realm_floor,
        player.user_id
    ))
    await _db_connection.commit()

async def create_sect(sect_name: str, leader_id: str) -> int:
    async with _db_connection.execute("INSERT INTO sects (name, leader_id) VALUES (?, ?)", (sect_name, leader_id)) as cursor:
        await _db_connection.commit()
        return cursor.lastrowid

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
            item_info = config.item_data.get(str(item_id), {})
            inventory_list.append({
                "item_id": item_id, "name": item_info.get("name", "未知物品"),
                "quantity": quantity, "description": item_info.get("description", "无")
            })
        return inventory_list

async def get_item_from_inventory(user_id: str, item_id: str) -> Optional[Dict[str, Any]]:
    async with _db_connection.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_item_to_inventory(user_id: str, item_id: str, quantity: int = 1):
    await _db_connection.execute("""
        INSERT INTO inventory (user_id, item_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, item_id) DO UPDATE SET
        quantity = quantity + excluded.quantity;
    """, (user_id, item_id, quantity))
    await _db_connection.commit()

async def remove_item_from_inventory(user_id: str, item_id: str, quantity: int = 1) -> bool:
    """从用户背包移除物品 (原子操作)"""
    async with _db_connection.cursor() as cursor:
        await cursor.execute("""
            UPDATE inventory SET quantity = quantity - ? 
            WHERE user_id = ? AND item_id = ? AND quantity >= ?
        """, (quantity, user_id, item_id, quantity))
        
        if cursor.rowcount > 0:
            await cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0", (user_id, item_id))
            await _db_connection.commit()
            return True
        else:
            await _db_connection.rollback()
            return False
        
async def transactional_buy_item(user_id: str, item_id: str, quantity: int, total_cost: int) -> bool:
    """事务性地处理购买物品：扣款并添加物品，保证数据一致性"""
    try:
        async with _db_connection.transaction():
            # 1. 扣款，并校验余额
            cursor = await _db_connection.execute(
                "UPDATE players SET gold = gold - ? WHERE user_id = ? AND gold >= ?",
                (total_cost, user_id, total_cost)
            )
            if cursor.rowcount == 0:
                # 如果没有行被更新，说明余额不足，事务会自动回滚
                return False

            # 2. 添加物品
            await _db_connection.execute("""
                INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity;
            """, (user_id, item_id, quantity))
        return True
    except aiosqlite.Error as e:
        logger.error(f"购买物品事务失败: {e}")
        return False

async def transactional_use_item(user_id: str, item_id: str, quantity: int) -> bool:
    """事务性地安全移除背包物品"""
    try:
        async with _db_connection.transaction():
            cursor = await _db_connection.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ? AND quantity >= ?",
                (quantity, user_id, item_id, quantity)
            )
            if cursor.rowcount == 0:
                # 数量不足，事务回滚
                return False
            
            await _db_connection.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0", (user_id, item_id))
        return True
    except aiosqlite.Error as e:
        logger.error(f"使用物品事务（移除阶段）失败: {e}")
        return False