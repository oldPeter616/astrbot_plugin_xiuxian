from astrbot.api.event import AstrMessageEvent, filter
from .decorator import player_required
from .. import data_manager, xiuxian_logic
from ..config_manager import config
from ..models import Player

class ShopHandler:
    @filter.command(config.CMD_SHOP, "查看坊市商品")
    async def handle_shop(self, event: AstrMessageEvent):
        reply_msg = "--- 仙途坊市 ---\n"
        for item_id, info in config.item_data.items():
            reply_msg += f"【{info['name']}】售价：{info['price']} 灵石\n"
        reply_msg += "------------------\n"
        reply_msg += f"使用「{config.CMD_BUY} <物品名> [数量]」进行购买。"
        yield event.plain_result(reply_msg)

    @filter.command(config.CMD_BACKPACK, "查看你的背包")
    @player_required
    async def handle_backpack(self, event: AstrMessageEvent):
        inventory = await data_manager.get_inventory_by_user_id(event.player.user_id)
        if not inventory:
            yield event.plain_result("道友的背包空空如也。")
            return
        
        reply_msg = f"--- {event.get_sender_name()} 的背包 ---\n"
        for item in inventory:
            reply_msg += f"【{item['name']}】x{item['quantity']} - {item['description']}\n"
        reply_msg += "--------------------------"
        yield event.plain_result(reply_msg)

    @filter.command(config.CMD_BUY, "购买物品")
    @player_required
    async def handle_buy(self, event: AstrMessageEvent):
        player: Player = event.player
        parts = event.message_str.strip().split(maxsplit=2)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_BUY} <物品名> [数量]」。")
            return

        item_name = parts[1]
        quantity = 1
        if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) > 0:
            quantity = int(parts[2])
        
        success, msg, updated_player, item_id_to_add = xiuxian_logic.handle_buy_item(player, item_name, quantity)
        if success:
            await data_manager.update_player(updated_player)
            await data_manager.add_item_to_inventory(player.user_id, item_id_to_add, quantity)
        yield event.plain_result(msg)
        
    @filter.command(config.CMD_USE_ITEM, "使用背包中的物品")
    @player_required
    async def handle_use(self, event: AstrMessageEvent):
        player: Player = event.player
        parts = event.message_str.strip().split(maxsplit=2)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_USE_ITEM} <物品名> [数量]」。")
            return

        item_name = parts[1]
        quantity = 1
        if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) > 0:
            quantity = int(parts[2])

        item_id_to_use, _ = config.get_item_by_name(item_name)
        if not item_id_to_use:
            yield event.plain_result(f"背包中似乎没有名为「{item_name}」的物品。")
            return

        if not await data_manager.remove_item_from_inventory(player.user_id, item_id_to_use, quantity):
             yield event.plain_result(f"你的「{item_name}」数量不足 {quantity} 个！")
             return

        success, msg, updated_player = xiuxian_logic.handle_use_item(player, item_id_to_use, quantity)
        
        if success:
            await data_manager.update_player(updated_player)

        yield event.plain_result(msg)