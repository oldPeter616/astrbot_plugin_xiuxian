# handlers/shop_handler.py
from typing import Optional, Tuple
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..config_manager import ConfigManager
from ..models import Player, PlayerEffect, Item
from .utils import player_required, require_idle_state

CMD_BUY = "购买"
CMD_USE_ITEM = "使用"

__all__ = ["ShopHandler"]

def calculate_item_effect(item_info: Optional[Item], quantity: int) -> Tuple[Optional[PlayerEffect], str]:
    if not item_info or not (effect_config := item_info.effect):
        return None, f"【{item_info.name if item_info else '未知物品'}】似乎只是凡物，无法使用。"

    effect = PlayerEffect()
    messages = []

    effect_type = effect_config.get("type")
    value = effect_config.get("value", 0) * quantity

    if effect_type == "add_experience":
        effect.experience = value
        messages.append(f"修为增加了 {value} 点")
    elif effect_type == "add_gold":
        effect.gold = value
        messages.append(f"灵石增加了 {value} 点")
    elif effect_type == "add_hp":
        effect.hp = value
        messages.append(f"恢复了 {value} 点生命")
    else:
         return None, f"你研究了半天，也没能参透【{item_info.name}】的用法。"

    full_message = f"你使用了 {quantity} 个【{item_info.name}】，" + "，".join(messages) + "！"
    return effect, full_message

class ShopHandler:
    # 坊市相关指令处理器
    
    def __init__(self, db: DataBase, config_manager: ConfigManager):
        self.db = db
        self.config_manager = config_manager

    async def handle_shop(self, event: AstrMessageEvent):
        reply_msg = "--- 仙途坊市 ---\n"
        sorted_items = sorted(self.config_manager.item_data.values(), key=lambda item: item.price)

        if not sorted_items:
            reply_msg += "今日坊市暂无商品。\n"
        else:
            for info in sorted_items:
                if info.price > 0:
                    reply_msg += f"【{info.name}】售价：{info.price} 灵石\n"
        reply_msg += "------------------\n"
        reply_msg += f"使用「{CMD_BUY} <物品名> [数量]」进行购买。"
        yield event.plain_result(reply_msg)

    @player_required
    async def handle_backpack(self, player: Player, event: AstrMessageEvent):
        inventory = await self.db.get_inventory_by_user_id(player.user_id, self.config_manager)
        if not inventory:
            yield event.plain_result("道友的背包空空如也。")
            return

        reply_msg = f"--- {event.get_sender_name()} 的背包 ---\n"
        for item in inventory:
            reply_msg += f"【{item['name']}】x{item['quantity']} - {item['description']}\n"
        reply_msg += "--------------------------"
        yield event.plain_result(reply_msg)

    @player_required
    @require_idle_state
    async def handle_buy(self, player: Player, event: AstrMessageEvent, item_name: str, quantity: int):
        if not item_name or quantity <= 0:
            yield event.plain_result(f"指令格式错误。正确用法: `{CMD_BUY} <物品名> [数量]`。")
            return

        item_to_buy = self.config_manager.get_item_by_name(item_name)
        if not item_to_buy or item_to_buy[1].price <= 0:
            yield event.plain_result(f"道友，小店中并无「{item_name}」这件商品。")
            return

        item_id_to_add, target_item_info = item_to_buy
        total_cost = target_item_info.price * quantity

        success, reason = await self.db.transactional_buy_item(player.user_id, item_id_to_add, quantity, total_cost)

        if success:
            updated_player = await self.db.get_player_by_id(player.user_id)
            if updated_player:
                yield event.plain_result(f"购买成功！花费{total_cost}灵石，购得「{item_name}」x{quantity}。剩余灵石 {updated_player.gold}。")
            else:
                yield event.plain_result(f"购买成功！花费{total_cost}灵石，购得「{item_name}」x{quantity}。")
        else:
            if reason == "ERROR_INSUFFICIENT_FUNDS":
                yield event.plain_result(f"灵石不足！购买 {quantity}个「{item_name}」需{total_cost}灵石，你只有{player.gold}。")
            else:
                yield event.plain_result("购买失败，坊市交易繁忙，请稍后再试。")

    @player_required
    @require_idle_state
    async def handle_use(self, player: Player, event: AstrMessageEvent, item_name: str, quantity: int):
        if not item_name or quantity <= 0:
            yield event.plain_result(f"指令格式错误。正确用法: `{CMD_USE_ITEM} <物品名> [数量]`。")
            return

        item_to_use = self.config_manager.get_item_by_name(item_name)
        if not item_to_use:
            yield event.plain_result(f"背包中似乎没有名为「{item_name}」的物品。")
            return

        target_item_id, target_item_info = item_to_use

        effect, msg = calculate_item_effect(target_item_info, quantity)
        if not effect:
            yield event.plain_result(msg)
            return

        success = await self.db.transactional_apply_item_effect(player.user_id, target_item_id, quantity, effect)

        if success:
            yield event.plain_result(msg)
        else:
            yield event.plain_result(f"使用失败！你的「{item_name}」数量不足 {quantity} 个，或发生了未知错误。")
