from astrbot.api.event import AstrMessageEvent, filter
from .decorator import player_required
from .. import data_manager
from ..config_manager import config
from ..models import Player
from ..realm_manager import RealmManager

class RealmHandler:
    def __init__(self, realm_manager: RealmManager):
        self.realm_manager = realm_manager

    @filter.command(config.CMD_REALM_LIST, "查看所有可探索的秘境")
    async def handle_realm_list(self, event: AstrMessageEvent):
        reply_msg = "--- 秘境列表 ---\n"
        for realm_id, info in config.realm_data.items():
            cost = info['entry_cost']['gold']
            reply_msg += (f"【{info['name']}】\n"
                          f"  准入境界: {info['level_requirement']}\n"
                          f"  进入消耗: {cost} 灵石\n")
        reply_msg += f"\n使用「{config.CMD_ENTER_REALM} <秘境名>」进入探索。"
        yield event.plain_result(reply_msg)

    @filter.command(config.CMD_ENTER_REALM, "进入秘境开始探索")
    @player_required
    async def handle_enter_realm(self, event: AstrMessageEvent, player: Player):
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_ENTER_REALM} <秘境名>」。")
            return

        realm_name = parts[1]
        realm_found = config.get_realm_by_name(realm_name)

        if not realm_found:
            yield event.plain_result(f"未找到名为【{realm_name}】的秘境。")
            return

        target_realm_id, _ = realm_found
        success, msg, updated_player = self.realm_manager.start_session(player, target_realm_id)

        if success:
            await data_manager.update_player(updated_player)

        yield event.plain_result(msg)

    @filter.command(config.CMD_REALM_ADVANCE, "在秘境中前进")
    @player_required
    async def handle_realm_advance(self, event: AstrMessageEvent, player: Player):
        if not player.realm_id:
            yield event.plain_result("你不在任何秘境中，无法前进。")
            return

        success, msg, updated_player, gained_items = await self.realm_manager.advance_session(player)

        if gained_items:
            await data_manager.add_items_to_inventory_in_transaction(player.user_id, gained_items)

            item_log = []
            for item_id, qty in gained_items.items():
                item_name = config.item_data.get(str(item_id), {}).get("name", "未知物品")
                item_log.append(f"【{item_name}】x{qty}")
            if item_log:
                msg += "\n获得物品：" + ", ".join(item_log)

        await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_LEAVE_REALM, "离开当前秘境")
    @player_required
    async def handle_leave_realm(self, event: AstrMessageEvent, player: Player):
        if not player.realm_id:
            yield event.plain_result("你不在任何秘境中。")
            return

        realm_name = config.realm_data.get(player.realm_id, {}).get("name", "未知的秘境")

        player.realm_id = None
        player.realm_floor = 0
        await data_manager.update_player(player)

        yield event.plain_result(f"你已从【{realm_name}】中脱离，回到了大千世界。中途退出不会获得任何奖励。")