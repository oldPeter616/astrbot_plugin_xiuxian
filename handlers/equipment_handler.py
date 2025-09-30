# handlers/equipment_handler.py
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..config_manager import ConfigManager
from ..models import Player
from .utils import player_required

# CMD_EQUIP 已被移除
CMD_UNEQUIP = "卸下"
CMD_MY_EQUIPMENT = "我的装备"

__all__ = ["EquipmentHandler"]

class EquipmentHandler:
    # 装备相关指令处理器
    
    def __init__(self, db: DataBase, config_manager: ConfigManager):
        self.db = db
        self.config_manager = config_manager

    # handle_equip 方法已合并到 handle_use

    @player_required
    async def handle_unequip(self, player: Player, event: AstrMessageEvent, subtype_name: str):
        if not subtype_name or subtype_name not in ["武器", "防具", "饰品"]:
            yield event.plain_result(f"指令格式错误。正确用法: `{CMD_UNEQUIP} <武器|防具|饰品>`。")
            return

        p_clone = player.clone()
        item_id_to_unequip = None
        
        if subtype_name == "武器":
            item_id_to_unequip = p_clone.equipped_weapon
            p_clone.equipped_weapon = None
        elif subtype_name == "防具":
            item_id_to_unequip = p_clone.equipped_armor
            p_clone.equipped_armor = None
        elif subtype_name == "饰品":
            item_id_to_unequip = p_clone.equipped_accessory
            p_clone.equipped_accessory = None

        if not item_id_to_unequip:
            yield event.plain_result(f"你的{subtype_name}栏位是空的。")
            return
            
        await self.db.add_items_to_inventory_in_transaction(player.user_id, {item_id_to_unequip: 1})
        await self.db.update_player(p_clone)
        
        item_info = self.config_manager.item_data.get(str(item_id_to_unequip))
        item_name = item_info.name if item_info else "未知装备"

        yield event.plain_result(f"已卸下【{item_name}】，并将其放入背包。")

    @player_required
    async def handle_my_equipment(self, player: Player, event: AstrMessageEvent):
        reply_lines = [f"--- {event.get_sender_name()} 的装备 ---"]
        
        def get_item_line(item_id: str, slot_name: str) -> str:
            if not item_id:
                return f"【{slot_name}】: (空)"
            item = self.config_manager.item_data.get(str(item_id))
            if not item:
                return f"【{slot_name}】: (ID:{item_id} 数据丢失)"
            
            effects_str = ", ".join([f"{k}+{v}" for k, v in item.equip_effects.items()]) if item.equip_effects else "无"
            return f"【{slot_name}】: {item.name} ({effects_str})"

        reply_lines.append(get_item_line(player.equipped_weapon, "武器"))
        reply_lines.append(get_item_line(player.equipped_armor, "防具"))
        reply_lines.append(get_item_line(player.equipped_accessory, "饰品"))
        
        reply_lines.append("--------------------------")
        yield event.plain_result("\n".join(reply_lines))