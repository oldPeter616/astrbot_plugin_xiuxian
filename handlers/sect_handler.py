# handlers/sect_handler.py
from astrbot.api.event import AstrMessageEvent
from .. import data_manager, xiuxian_logic
from ..config_manager import config
from ..models import Player

__all__ = ["SectHandler"]

class SectHandler:
    def __init__(self, plugin):
        self.plugin = plugin

    async def handle_create_sect(self, event: AstrMessageEvent, sect_name: str, player: Player):
        if not sect_name:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_CREATE_SECT} <宗门名称>」。")
            return
            
        success, msg, updated_player = await xiuxian_logic.handle_create_sect(player, sect_name)
        if success and updated_player:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    async def handle_join_sect(self, event: AstrMessageEvent, sect_name: str, player: Player):
        if not sect_name:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_JOIN_SECT} <宗门名称>」。")
            return

        success, msg, updated_player = await xiuxian_logic.handle_join_sect(player, sect_name)
        if success and updated_player:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    async def handle_leave_sect(self, event: AstrMessageEvent, player: Player):
        success, msg, updated_player = await xiuxian_logic.handle_leave_sect(player)
        if success and updated_player:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    async def handle_my_sect(self, event: AstrMessageEvent, player: Player):
        if not player.sect_id:
            yield event.plain_result("道友乃逍遥散人，尚未加入任何宗门。")
            return

        sect_info = await data_manager.get_sect_by_id(player.sect_id)
        if not sect_info:
            player.sect_id = None
            player.sect_name = None
            await data_manager.update_player(player)
            yield event.plain_result("错误：找不到你的宗门信息，可能已被解散。已将你设为散修。")
            return

        leader_player = await data_manager.get_player_by_id(sect_info['leader_id'])
        leader_info = "宗主: (信息丢失)"
        
        if leader_player and leader_player.sect_id == sect_info['id']:
            leader_info = f"宗主: {leader_player.user_id[-4:]}"

        members = await data_manager.get_sect_members(player.sect_id)
        member_list = [f"{m.level}-{m.user_id[-4:]}" for m in members]

        reply_msg = (
            f"--- {sect_info['name']} (Lv.{sect_info['level']}) ---\n"
            f"{leader_info}\n"
            f"宗门资金：{sect_info['funds']} 灵石\n"
            f"成员 ({len(members)}人):\n"
            f"{' | '.join(member_list)}\n"
            "--------------------------"
        )
        yield event.plain_result(reply_msg)