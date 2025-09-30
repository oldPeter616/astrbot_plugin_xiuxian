# handlers/player_handler.py
from astrbot.api.event import AstrMessageEvent
from astrbot.api import AstrBotConfig
from ..data import DataBase
from ..core import CultivationManager
from ..models import Player
from ..config_manager import ConfigManager
from .utils import player_required

CMD_START_XIUXIAN = "我要修仙"
CMD_PLAYER_INFO = "我的信息"
CMD_CHECK_IN = "签到"

__all__ = ["PlayerHandler"]

class PlayerHandler:
    # 玩家相关指令处理器
    
    def __init__(self, db: DataBase, config: AstrBotConfig, config_manager: ConfigManager):
        self.db = db
        self.config = config
        self.config_manager = config_manager
        self.cultivation_manager = CultivationManager(config, config_manager)

    async def handle_start_xiuxian(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if await self.db.get_player_by_id(user_id):
            yield event.plain_result("道友，你已踏入仙途，无需重复此举。")
            return

        new_player = self.cultivation_manager.generate_new_player_stats(user_id)
        await self.db.create_player(new_player)
        reply_msg = (
            f"恭喜道友 {event.get_sender_name()} 踏上仙途！\n"
            f"初始灵根：【{new_player.spiritual_root}】\n"
            f"启动资金：【{new_player.gold}】灵石\n"
            f"发送「{CMD_PLAYER_INFO}」查看状态，「{CMD_CHECK_IN}」领取福利！"
        )
        yield event.plain_result(reply_msg)

    @player_required
    async def handle_player_info(self, player: Player, event: AstrMessageEvent):
        sect_info = f"宗门：{player.sect_name if player.sect_name else '逍遥散人'}"
        combat_stats = player.get_combat_stats(self.config_manager)

        # 构建装备显示部分
        equipped_items_lines = []
        slot_map = {"武器": player.equipped_weapon, "防具": player.equipped_armor, "饰品": player.equipped_accessory}
        for slot, item_id in slot_map.items():
            item_name = "(无)"
            if item_id:
                item_data = self.config_manager.item_data.get(str(item_id))
                if item_data:
                    item_name = f"「{item_data.name}」"
            equipped_items_lines.append(f"  {slot}: {item_name}")

        equipped_info = "\n".join(equipped_items_lines)

        reply_msg = (
            f"--- 道友 {event.get_sender_name()} 的信息 ---\n"
            f"境界：{player.get_level(self.config_manager)}\n"
            f"灵根：{player.spiritual_root}\n"
            f"修为：{player.experience}\n"
            f"灵石：{player.gold}\n"
            f"{sect_info}\n"
            f"状态：{player.state}\n"
            "--- 战斗属性 (含装备加成) ---\n"
            f"❤️生命: {combat_stats['hp']}/{combat_stats['max_hp']}\n"
            f"⚔️攻击: {combat_stats['attack']}\n"
            f"🛡️防御: {combat_stats['defense']}\n"
            "--- 穿戴装备 ---\n"
            f"{equipped_info}\n"
            f"--------------------------"
        )
        yield event.plain_result(reply_msg)

    @player_required
    async def handle_check_in(self, player: Player, event: AstrMessageEvent):
        success, msg, updated_player = self.cultivation_manager.handle_check_in(player)
        if success and updated_player:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)

    @player_required
    async def handle_start_cultivation(self, player: Player, event: AstrMessageEvent):
        success, msg, updated_player = self.cultivation_manager.handle_start_cultivation(player)
        if success and updated_player:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)

    @player_required
    async def handle_end_cultivation(self, player: Player, event: AstrMessageEvent):
        success, msg, updated_player = self.cultivation_manager.handle_end_cultivation(player)
        if success and updated_player:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)

    @player_required
    async def handle_breakthrough(self, player: Player, event: AstrMessageEvent):
        # 内部已经包含了状态检查，但为了统一，装饰器的检查是第一道防线
        success, msg, updated_player = self.cultivation_manager.handle_breakthrough(player)
        if success and updated_player:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)
        
    @player_required
    async def handle_reroll_spirit_root(self, player: Player, event: AstrMessageEvent):
        success, msg, updated_player = self.cultivation_manager.handle_reroll_spirit_root(player)
        if success and updated_player:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)