from astrbot.api.event import AstrMessageEvent, filter
from .decorator import player_required
from .parser import parse_args
from .. import data_manager, xiuxian_logic
from ..config_manager import config
from ..models import Player
from astrbot.api import logger

class ShopHandlerMixin:
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
    async def handle_backpack(self, event: AstrMessageEvent, player: Player):
        inventory = await data_manager.get_inventory_by_user_id(player.user_id)
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
    @parse_args(str, int, optional=1)
    async def handle_buy(self, event: AstrMessageEvent, item_name: str, quantity: int, player: Player):        
        # 如果数量未提供，默认为1
        if quantity is None:
            quantity = 1
            
        if quantity <= 0:
            yield event.plain_result("购买数量必须是正整数。")
            return

        item_to_buy = config.get_item_by_name(item_name)
        if not item_to_buy:
            yield event.plain_result(f"道友，小店中并无「{item_name}」这件商品。")
            return

        item_id_to_add, target_item_info = item_to_buy
        total_cost = target_item_info['price'] * quantity

        success, reason = await data_manager.transactional_buy_item(player.user_id, item_id_to_add, quantity, total_cost)

        if success:
            new_gold = player.gold - total_cost
            yield event.plain_result(f"购买成功！花费{total_cost}灵石，购得「{item_name}」x{quantity}。剩余灵石 {new_gold}。")
        else:
            if reason == "ERROR_INSUFFICIENT_FUNDS":
                yield event.plain_result(f"灵石不足！购买 {quantity}个「{item_name}」需{total_cost}灵石，你只有{player.gold}。")
            else:
                yield event.plain_result("购买失败，坊市交易繁忙，请稍后再试。")

    @filter.command(config.CMD_USE_ITEM, "使用背包中的物品")
    @player_required
    @parse_args(str, int, optional=1)
    async def handle_use(self, event: AstrMessageEvent, item_name: str, quantity: int, player: Player):
        # 如果数量未提供，默认为1
        if quantity is None:
            quantity = 1

        if quantity <= 0:
            yield event.plain_result("使用数量必须是正整数。")
            return
            
        item_to_use = config.get_item_by_name(item_name)
        if not item_to_use:
            yield event.plain_result(f"背包中似乎没有名为「{item_name}」的物品。")
            return

        target_item_id, _ = item_to_use

        effect, msg = xiuxian_logic.calculate_item_effect(target_item_id, quantity)
        if not effect:
            yield event.plain_result(msg)
            return

        success = await data_manager.transactional_apply_item_effect(player.user_id, target_item_id, quantity, effect)

        if success:
            yield event.plain_result(msg)
        else:
            yield event.plain_result(f"使用失败！你的「{item_name}」数量不足 {quantity} 个，或发生了未知错误。")