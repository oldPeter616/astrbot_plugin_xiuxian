# handlers/realm_handler.py
from astrbot.api.event import AstrMessageEvent
from .. import data_manager
from ..config_manager import config
from ..models import Player

__all__ = ["RealmHandler"]

class RealmHandler:
    def __init__(self, plugin):
        self.plugin = plugin

    async def handle_realm_list(self, event: AstrMessageEvent):
        reply_msg = "--- 秘境列表 ---\n"
        for realm_id, info in config.realm_data.items():
            cost = info['entry_cost']['gold']
            reply_msg += (f"【{info['name']}】\n"
                          f"  准入境界: {info['level_requirement']}\n"
                          f"  进入消耗: {cost} 灵石\n")
        reply_msg += f"\n使用「{config.CMD_ENTER_REALM} <秘境名>」进入探索。"
        yield event.plain_result(reply_msg)

    async def handle_enter_realm(self, event: AstrMessageEvent, realm_name: str, player: Player):
        if not realm_name:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_ENTER_REALM} <秘境名>」。")
            return

        realm_found = config.get_realm_by_name(realm_name)

        if not realm_found:
            yield event.plain_result(f"未找到名为【{realm_name}】的秘境。")
            return

        target_realm_id, _ = realm_found
        success, msg, updated_player = await self.plugin.realm_manager.start_session(player, target_realm_id)

        if success:
            await data_manager.update_player(updated_player)

        yield event.plain_result(msg)

    async def handle_realm_advance(self, event: AstrMessageEvent, player: Player):
        if not player.realm_id:
            yield event.plain_result("你不在任何秘境中，无法前进。")
            return

        success, msg, updated_player, gained_items = await self.plugin.realm_manager.advance_session(player)

        if gained_items:
            await data_manager.add_items_to_inventory_in_transaction(player.user_id, gained_items)

            item_log = []
            for item_id, qty in gained_items.items():
                item = config.item_data.get(str(item_id))
                item_name = item.name if item else "未知物品"
                item_log.append(f"【{item_name}】x{qty}")
            if item_log:
                msg += "\n获得物品：" + ", ".join(item_log)

        await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    async def handle_leave_realm(self, event: AstrMessageEvent, player: Player):
        if not player.realm_id:
            yield event.plain_result("你不在任何秘境中。")
            return

        realm_name = config.realm_data.get(player.realm_id, {}).get("name", "未知的秘境")

        player.realm_id = None
        player.realm_floor = 0
        player.set_realm_instance(None) 
        
        await data_manager.update_player(player)

        yield event.plain_result(f"你已从【{realm_name}】中脱离，回到了大千世界。中途退出不会获得任何奖励。")