# handlers/realm_handler.py

from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..core import RealmManager
from ..config_manager import config
from ..models import Player

__all__ = ["RealmHandler"]

class RealmHandler:
    def __init__(self, db: DataBase):
        self.db = db
        self.realm_manager = RealmManager(db)

    async def _get_player_or_reply(self, event: AstrMessageEvent) -> Player | None:
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return None
        return player

    async def handle_enter_realm(self, event: AstrMessageEvent):
        player = await self._get_player_or_reply(event)
        if not player:
            return

        success, msg, updated_player = await self.realm_manager.start_session(player)
        if success:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)

    async def handle_realm_advance(self, event: AstrMessageEvent):
        player = await self._get_player_or_reply(event)
        if not player:
            return

        if not player.realm_id:
            yield event.plain_result("你不在任何秘境中，无法前进。")
            return

        success, msg, updated_player, gained_items = await self.realm_manager.advance_session(player)

        await self.db.update_player(updated_player)

        if gained_items:
            await self.db.add_items_to_inventory_in_transaction(updated_player.user_id, gained_items)
            item_log = []
            for item_id, qty in gained_items.items():
                item = config.item_data.get(str(item_id))
                item_name = item.name if item else "未知物品"
                item_log.append(f"【{item_name}】x{qty}")
            if item_log:
                msg += "\n获得物品：" + ", ".join(item_log)

        yield event.plain_result(msg)

    async def handle_leave_realm(self, event: AstrMessageEvent):
        player = await self._get_player_or_reply(event)
        if not player:
            return

        if not player.realm_id:
            yield event.plain_result("你不在任何秘境中。")
            return

        # 动态获取秘境名称
        realm_instance = player.get_realm_instance()
        realm_name = f"{player.level}修士的试炼" if realm_instance else "未知的秘境"

        player.realm_id = None
        player.realm_floor = 0
        player.set_realm_instance(None)

        await self.db.update_player(player)

        yield event.plain_result(f"你已从【{realm_name}】中脱离，回到了大千世界。中途退出不会获得任何奖励。")