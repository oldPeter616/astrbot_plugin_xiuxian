# handlers/shop_handler.py

from astrbot.api.event import AstrMessageEvent, filter
from .decorator import player_required
from .. import data_manager, xiuxian_logic
from ..config_manager import config
from ..models import Player

class ShopHandler:
    @filter.command(config.CMD_SHOP, "查看坊市商品")
    async def handle_shop(self, event: AstrMessageEvent):
        reply_msg = "--- 仙途坊市 ---\n"
        if not config.item_data:
            reply_msg += "今日坊市暂无商品。\n"
        else:
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

        item_to_buy = config.get_item_by_name(item_name)
        if not item_to_buy:
            yield event.plain_result(f"道友，小店中并无「{item_name}」这件商品。")
            return

        item_id_to_add, target_item_info = item_to_buy
        total_cost = target_item_info['price'] * quantity
        
        # 预先检查余额，减少不必要的数据库事务
        current_player = await data_manager.get_player_by_id(player.user_id)
        if current_player.gold < total_cost:
            yield event.plain_result(f"灵石不足！购买 {quantity}个「{item_name}」需{total_cost}灵石，你只有{current_player.gold}。")
            return

        # 调用事务性操作
        success = await data_manager.transactional_buy_item(player.user_id, item_id_to_add, quantity, total_cost)

        if success:
            yield event.plain_result(f"购买成功！花费{total_cost}灵石，购得「{item_name}」x{quantity}。")
        else:
            yield event.plain_result("购买失败，可能是灵石不足或坊市交易繁忙，请稍后再试。")

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

        item_to_use = config.get_item_by_name(item_name)
        if not item_to_use:
            yield event.plain_result(f"背包中似乎没有名为「{item_name}」的物品。")
            return
        
        target_item_id, _ = item_to_use
        
        # 1. 先安全地从数据库移除物品
        removed = await data_manager.transactional_use_item(player.user_id, target_item_id, quantity)
        if not removed:
             yield event.plain_result(f"你的「{item_name}」数量不足 {quantity} 个！")
             return

        # 2. 物品移除成功后，在内存中应用效果
        #    重新获取最新的玩家数据，避免状态不一致
        current_player_state = await data_manager.get_player_by_id(player.user_id)
        eff_success, msg, updated_player = xiuxian_logic.handle_use_item(current_player_state, target_item_id, quantity)
        
        if eff_success:
            # 3. 将应用效果后的玩家状态存回数据库
            await data_manager.update_player(updated_player)
            yield event.plain_result(msg)
        else:
            # 如果应用效果失败，可以考虑将物品加回去，实现真正的回滚
            await data_manager.add_item_to_inventory(player.user_id, target_item_id, quantity)
            yield event.plain_result(f"你使用了【{item_name}】，但似乎什么也没发生...物品已返还。")