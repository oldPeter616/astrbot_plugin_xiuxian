# handlers/realm_handler.py

from astrbot.api.event import AstrMessageEvent
from .. import data_manager
from ..config_manager import config
from ..models import Player

__all__ = ["RealmHandler"]

class RealmHandler:
    def __init__(self, plugin):
        self.plugin = plugin

    async def handle_enter_realm(self, event: AstrMessageEvent, player: Player):
        success, msg, updated_player = await self.plugin.realm_manager.start_session(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    async def handle_realm_advance(self, event: AstrMessageEvent, player: Player):
        if not player.realm_id:
            yield event.plain_result("你不在任何秘境中，无法前进。")
            return
        
        success, msg, updated_player, gained_items = await self.plugin.realm_manager.advance_session(player)

        await data_manager.update_player(updated_player)
        
        if gained_items:
            await data_manager.add_items_to_inventory_in_transaction(updated_player.user_id, gained_items)
            item_log = []
            for item_id, qty in gained_items.items():
                item = config.item_data.get(str(item_id))
                item_name = item.name if item else "未知物品"
                item_log.append(f"【{item_name}】x{qty}")
            if item_log:
                msg += "\n获得物品：" + ", ".join(item_log)

        yield event.plain_result(msg)

    async def handle_leave_realm(self, event: AstrMessageEvent, player: Player):
        if not player.realm_id:
            yield event.plain_result("你不在任何秘境中。")
            return

        # 动态获取秘境名称
        realm_instance = player.get_realm_instance()
        realm_name = f"{player.level}修士的试炼" if realm_instance else "未知的秘境"

        player.realm_id = None
        player.realm_floor = 0
        player.set_realm_instance(None) 
        
        await data_manager.update_player(player)

        yield event.plain_result(f"你已从【{realm_name}】中脱离，回到了大千世界。中途退出不会获得任何奖励。")