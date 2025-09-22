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
CMD_CHANGE_NAME = "更改道号"

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

        sender_name = event.get_sender_name()
        new_player = self.cultivation_manager.generate_new_player_stats(user_id, sender_name)
        await self.db.create_player(new_player)
        reply_msg = (
            f"恭喜道友 {sender_name} 踏上仙途！\n"
            f"你的初始道号为【{new_player.name}】\n"
            f"初始灵根：【{new_player.spiritual_root}】\n"
            f"启动资金：【{new_player.gold}】灵石\n"
            f"发送「{CMD_PLAYER_INFO}」查看状态，「{CMD_CHECK_IN}」领取福利！"
        )
        yield event.plain_result(reply_msg)

    @player_required
    async def handle_player_info(self, player: Player, event: AstrMessageEvent):
        # 查找装备名称，如果id存在但找不到物品，则显示未知
        weapon_name = self.config_manager.item_data.get(player.weapon_id).name if player.weapon_id and self.config_manager.item_data.get(player.weapon_id) else "无"
        armor_name = self.config_manager.item_data.get(player.armor_id).name if player.armor_id and self.config_manager.item_data.get(player.armor_id) else "无"
        accessory_name = self.config_manager.item_data.get(player.accessory_id).name if player.accessory_id and self.config_manager.item_data.get(player.accessory_id) else "无"
        magic_tool_name = self.config_manager.item_data.get(player.magic_tool_id).name if player.magic_tool_id and self.config_manager.item_data.get(player.magic_tool_id) else "无"

        # 获取下一等级所需经验
        exp_to_next_level = "已达顶峰"
        if player.level_index < len(self.config_manager.level_data) - 1:
            next_level_info = self.config_manager.level_data[player.level_index + 1]
            exp_needed = next_level_info['exp_needed']
            exp_to_next_level = f"距离下次升级还需 {exp_needed - player.experience} 经验。"


        reply_msg = (
            f"【{player.name}的修行状态】\n"
            f"境界：{player.get_level(self.config_manager)}\n"
            f"灵根：{player.spiritual_root}\n"
            f"灵石：{player.gold} 枚\n\n"
            f"【属性面板】\n"
            f"生命：{player.hp}/{player.max_hp}\n"
            f"灵力：{player.mp}/{player.max_mp}\n"
            f"攻击：{player.attack}\n"
            f"防御：{player.defense}\n"
            f"速度：{player.speed}\n\n"
            f"【天赋面板】\n"
            f"根骨：{player.aptitude}\n"
            f"悟性：{player.insight}\n"
            f"气运：{player.luck}\n"
            f"神识：{player.divine_sense}\n"
            f"暴击率：{player.crit_rate:.1%}\n"
            f"暴击伤害：{player.crit_damage:.0%}\n\n"
            f"【装备信息】\n"
            f"武器: {weapon_name}\n"
            f"防具: {armor_name}\n"
            f"饰品: {accessory_name}\n"
            f"法宝: {magic_tool_name}\n\n"
            f"{exp_to_next_level}"
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
        if player.state != "空闲":
            yield event.plain_result(f"道友当前正在「{player.state}」中，无法尝试突破。")
            return
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
        
    @player_required
    async def handle_change_name(self, player: Player, event: AstrMessageEvent, new_name: str):
        if not new_name:
            yield event.plain_result("道号不可为空，请重新输入。")
            return
        
        cost = self.config["VALUES"].get("CHANGE_NAME_COST", 1000)
        
        if player.gold < cost:
            yield event.plain_result(f"更改道号需花费 {cost} 灵石，你的家底还不够。")
            return
            
        p_clone = player.clone()
        old_name = p_clone.name
        p_clone.gold -= cost
        p_clone.name = new_name
        
        await self.db.update_player(p_clone)
        
        yield event.plain_result(f"道号已成功从【{old_name}】更改为【{new_name}】，花费了 {cost} 灵石。")
