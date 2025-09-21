# data/data_manager.py

import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import fields

from astrbot.api import logger
from astrbot.api.star import StarTools

from ..config_manager import ConfigManager
from ..models import Player, PlayerEffect, ActiveWorldBoss

class DataBase:
    """数据库管理器，封装所有数据库操作"""
    
    def __init__(self, db_file_name: str):
        data_dir = StarTools.get_data_dir("xiuxian")
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = data_dir / db_file_name
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        if self.conn is None:
            self.conn = await aiosqlite.connect(self.db_path)
            self.conn.row_factory = aiosqlite.Row
            logger.info(f"数据库连接已创建: {self.db_path}")

    async def close(self):
        if self.conn:
            await self.conn.close()
            self.conn = None
            logger.info("数据库连接已关闭。")

    async def get_active_bosses(self) -> List[ActiveWorldBoss]:
        async with self.conn.execute("SELECT * FROM active_world_bosses") as cursor:
            rows = await cursor.fetchall()
            return [ActiveWorldBoss(**dict(row)) for row in rows]

    async def create_active_boss(self, boss: ActiveWorldBoss):
        await self.conn.execute(
            "INSERT INTO active_world_bosses (boss_id, current_hp, max_hp, spawned_at, level_index) VALUES (?, ?, ?, ?, ?)",
            (boss.boss_id, boss.current_hp, boss.max_hp, boss.spawned_at, boss.level_index)
        )
        await self.conn.commit()

    async def update_active_boss_hp(self, boss_id: str, new_hp: int):
        await self.conn.execute(
            "UPDATE active_world_bosses SET current_hp = ? WHERE boss_id = ?",
            (new_hp, boss_id)
        )
        await self.conn.commit()

    async def delete_active_boss(self, boss_id: str):
        await self.conn.execute("DELETE FROM active_world_bosses WHERE boss_id = ?", (boss_id,))
        await self.conn.commit()

    async def record_boss_damage(self, boss_id: str, user_id: str, user_name: str, damage: int):
        await self.conn.execute("""
            INSERT INTO world_boss_participants (boss_id, user_id, user_name, total_damage) VALUES (?, ?, ?, ?)
            ON CONFLICT(boss_id, user_id) DO UPDATE SET total_damage = total_damage + excluded.total_damage;
        """, (boss_id, user_id, user_name, damage))
        await self.conn.commit()

    async def get_boss_participants(self, boss_id: str) -> List[Dict[str, Any]]:
        sql = "SELECT user_id, user_name, total_damage FROM world_boss_participants WHERE boss_id = ? ORDER BY total_damage DESC"
        async with self.conn.execute(sql, (boss_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def clear_boss_data(self, boss_id: str):
        try:
            await self.conn.execute("BEGIN")
            await self.conn.execute("DELETE FROM active_world_bosses WHERE boss_id = ?", (boss_id,))
            await self.conn.execute("DELETE FROM world_boss_participants WHERE boss_id = ?", (boss_id,))
            await self.conn.commit()
            logger.info(f"Boss {boss_id} 的数据已清理。")
        except aiosqlite.Error as e:
            await self.conn.rollback()
            logger.error(f"清理Boss {boss_id} 数据失败: {e}")

    async def get_top_players(self, limit: int) -> List[Player]:
        async with self.conn.execute(
            "SELECT * FROM players ORDER BY level_index DESC, experience DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [Player(**dict(row)) for row in rows]

    async def get_player_by_id(self, user_id: str) -> Optional[Player]:
        async with self.conn.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return Player(**dict(row)) if row else None

    async def create_player(self, player: Player):
        player_fields = [f.name for f in fields(Player)]
        columns = ", ".join(player_fields)
        placeholders = ", ".join([f":{f}" for f in player_fields])
        sql = f"INSERT INTO players ({columns}) VALUES ({placeholders})"
        await self.conn.execute(sql, player.__dict__)
        await self.conn.commit()

    async def update_player(self, player: Player):
        player_fields = [f.name for f in fields(Player) if f.name != 'user_id']
        set_clause = ", ".join([f"{f} = :{f}" for f in player_fields])
        sql = f"UPDATE players SET {set_clause} WHERE user_id = :user_id"
        await self.conn.execute(sql, player.__dict__)
        await self.conn.commit()

    async def update_players_in_transaction(self, players: List[Player]):
        if not players:
            return
        player_fields = [f.name for f in fields(Player) if f.name != 'user_id']
        set_clause = ", ".join([f"{f} = :{f}" for f in player_fields])
        sql = f"UPDATE players SET {set_clause} WHERE user_id = :user_id"
        try:
            await self.conn.execute("BEGIN")
            for player in players:
                await self.conn.execute(sql, player.__dict__)
            await self.conn.commit()
        except aiosqlite.Error as e:
            await self.conn.rollback()
            logger.error(f"批量更新玩家事务失败: {e}")
            raise

    async def create_sect(self, sect_name: str, leader_id: str) -> int:
        async with self.conn.execute("INSERT INTO sects (name, leader_id) VALUES (?, ?)", (sect_name, leader_id)) as cursor:
            await self.conn.commit()
            return cursor.lastrowid

    async def delete_sect(self, sect_id: int):
        await self.conn.execute("DELETE FROM sects WHERE id = ?", (sect_id,))
        await self.conn.commit()

    async def get_sect_by_name(self, sect_name: str) -> Optional[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM sects WHERE name = ?", (sect_name,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_sect_by_id(self, sect_id: int) -> Optional[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM sects WHERE id = ?", (sect_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_sect_members(self, sect_id: int) -> List[Player]:
        async with self.conn.execute("SELECT * FROM players WHERE sect_id = ?", (sect_id,)) as cursor:
            rows = await cursor.fetchall()
            return [Player(**dict(row)) for row in rows]

    async def update_player_sect(self, user_id: str, sect_id: Optional[int], sect_name: Optional[str]):
        await self.conn.execute("UPDATE players SET sect_id = ?, sect_name = ? WHERE user_id = ?", (sect_id, sect_name, user_id))
        await self.conn.commit()

    async def get_inventory_by_user_id(self, user_id: str, config_manager: ConfigManager) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            inventory_list = []
            for row in rows:
                item_id, quantity = row['item_id'], row['quantity']
                item_info = config_manager.item_data.get(str(item_id))
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

    async def get_item_from_inventory(self, user_id: str, item_id: str) -> Optional[Dict[str, Any]]:
        async with self.conn.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_items_to_inventory_in_transaction(self, user_id: str, items: Dict[str, int]):
        try:
            await self.conn.execute("BEGIN")
            for item_id, quantity in items.items():
                await self.conn.execute("""
                    INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity;
                """, (user_id, item_id, quantity))
            await self.conn.commit()
        except aiosqlite.Error as e:
            await self.conn.rollback()
            logger.error(f"批量添加物品事务失败: {e}")
            raise

    async def remove_item_from_inventory(self, user_id: str, item_id: str, quantity: int = 1) -> bool:
        try:
            await self.conn.execute("BEGIN")
            cursor = await self.conn.execute("""
                UPDATE inventory SET quantity = quantity - ?
                WHERE user_id = ? AND item_id = ? AND quantity >= ?
            """, (quantity, user_id, item_id, quantity))

            if cursor.rowcount == 0:
                await self.conn.rollback()
                return False

            await self.conn.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0", (user_id, item_id))
            await self.conn.commit()
            return True
        except aiosqlite.Error as e:
            await self.conn.rollback()
            logger.error(f"移除物品事务失败: {e}")
            return False

    async def transactional_buy_item(self, user_id: str, item_id: str, quantity: int, total_cost: int) -> Tuple[bool, str]:
        try:
            await self.conn.execute("BEGIN")
            cursor = await self.conn.execute(
                "UPDATE players SET gold = gold - ? WHERE user_id = ? AND gold >= ?",
                (total_cost, user_id, total_cost)
            )
            if cursor.rowcount == 0:
                await self.conn.rollback()
                return False, "ERROR_INSUFFICIENT_FUNDS"

            await self.conn.execute("""
                INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity;
            """, (user_id, item_id, quantity))

            await self.conn.commit()
            return True, "SUCCESS"
        except aiosqlite.Error as e:
            await self.conn.rollback()
            logger.error(f"购买物品事务失败: {e}")
            return False, "ERROR_DATABASE"

    async def transactional_apply_item_effect(self, user_id: str, item_id: str, quantity: int, effect: PlayerEffect) -> bool:
        try:
            await self.conn.execute("BEGIN")
            cursor = await self.conn.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ? AND quantity >= ?",
                (quantity, user_id, item_id, quantity)
            )
            if cursor.rowcount == 0:
                await self.conn.rollback()
                return False

            await self.conn.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0", (user_id, item_id))

            await self.conn.execute(
                """
                UPDATE players
                SET experience = experience + ?,
                    gold = gold + ?,
                    hp = MIN(max_hp, hp + ?)
                WHERE user_id = ?
                """,
                (effect.experience, effect.gold, effect.hp, user_id)
            )
            await self.conn.commit()
            return True
        except aiosqlite.Error as e:
            await self.conn.rollback()
            logger.error(f"使用物品事务失败: {e}")
            return False