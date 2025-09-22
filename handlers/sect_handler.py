# handlers/sect_handler.py
from astrbot.api.event import AstrMessageEvent
from astrbot.api import AstrBotConfig
from ..data import DataBase
from ..core import SectManager
from ..config_manager import ConfigManager
from ..models import Player
from .utils import player_required

CMD_CREATE_SECT = "创建宗门"
CMD_JOIN_SECT = "加入宗门"

__all__ = ["SectHandler"]

class SectHandler:
    # 宗门相关指令处理器
    
    def __init__(self, db: DataBase, config: AstrBotConfig, config_manager: ConfigManager):
        self.db = db
        self.config = config
        self.config_manager = config_manager
        self.sect_manager = SectManager(db, config)

    @player_required
    async def handle_create_sect(self, player: Player, event: AstrMessageEvent, sect_name: str):
        if not sect_name:
            yield event.plain_result(f"指令格式错误！请使用「{CMD_CREATE_SECT} <宗门名称>」。")
            return

        success, msg, updated_player = await self.sect_manager.handle_create_sect(player, sect_name)
        if success and updated_player:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)

    @player_required
    async def handle_join_sect(self, player: Player, event: AstrMessageEvent, sect_name: str):
        if not sect_name:
            yield event.plain_result(f"指令格式错误！请使用「{CMD_JOIN_SECT} <宗门名称>」。")
            return

        success, msg, updated_player = await self.sect_manager.handle_join_sect(player, sect_name)
        if success and updated_player:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)

    @player_required
    async def handle_leave_sect(self, player: Player, event: AstrMessageEvent):
        success, msg, updated_player = await self.sect_manager.handle_leave_sect(player)
        if success and updated_player:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)

    @player_required
    async def handle_my_sect(self, player: Player, event: AstrMessageEvent):
        if not player.sect_id:
            yield event.plain_result("道友乃逍遥散人，尚未加入任何宗门。")
            return

        sect_info = await self.db.get_sect_by_id(player.sect_id)
        if not sect_info:
            player.sect_id = None
            player.sect_name = None
            await self.db.update_player(player)
            yield event.plain_result("错误：找不到你的宗门信息，可能已被解散。已将你设为散修。")
            return

        leader_player = await self.db.get_player_by_id(sect_info['leader_id'])
        leader_info = "宗主: (信息丢失)"

        if leader_player and leader_player.sect_id == sect_info['id']:
            leader_info = f"宗主: {leader_player.user_id[-4:]}"

        members = await self.db.get_sect_members(player.sect_id)
        member_list = [f"{m.get_level(self.config_manager)}-{m.user_id[-4:]}" for m in members]

        reply_msg = (
            f"--- {sect_info['name']} (Lv.{sect_info['level']}) ---\n"
            f"{leader_info}\n"
            f"宗门资金：{sect_info['funds']} 灵石\n"
            f"成员 ({len(members)}人):\n"
            f"{' | '.join(member_list)}\n"
            "--------------------------"
        )
        yield event.plain_result(reply_msg)