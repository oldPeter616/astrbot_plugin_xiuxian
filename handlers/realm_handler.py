# handlers/realm_handler.py

from astrbot.api.event import AstrMessageEvent
from astrbot.api import AstrBotConfig
from ..data import DataBase
from ..core import RealmManager
from ..config_manager import ConfigManager
from ..models import Player

CMD_START_XIUXIAN = "我要修仙"
CMD_REALM_ADVANCE = "前进"

__all__ = ["RealmHandler"]

class RealmHandler:
    # 秘境相关指令处理器
    
    def __init__(self, db: DataBase, config: AstrBotConfig, config_manager: ConfigManager):
        self.db = db
        self.config = config
        self.config_manager = config_manager
        self.realm_manager = RealmManager(db, config, config_manager)

    async def _get_player_or_reply(self, event: AstrMessageEvent) -> Player | None:
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{CMD_START_XIUXIAN}」开启你的旅程。")
            return None
        return player

    async def handle_enter_realm(self, event: AstrMessageEvent):
        player = await self._get_player_or_reply(event)
        if not player:
            return

        success, msg, updated_player = await self.realm_manager.start_session(player, CMD_REALM_ADVANCE)
        if success and updated_player:
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
                item = self.config_manager.item_data.get(str(item_id))
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

        realm_instance = player.get_realm_instance()
        realm_name = f"{player.get_level(self.config_manager)}修士的试炼" if realm_instance else "未知的秘境"

        player.realm_id = None
        player.realm_floor = 0
        player.set_realm_instance(None)

        await self.db.update_player(player)

        yield event.plain_result(f"你已从【{realm_name}】中脱离，回到了大千世界。中途退出不会获得任何奖励。")