# handlers/sect_handler.py

from astrbot.api.event import AstrMessageEvent, filter
from .decorator import player_required
from .. import data_manager, xiuxian_logic
from ..config_manager import config
from ..models import Player

class SectHandler:
    @filter.command(config.CMD_CREATE_SECT, "创建你的宗门")
    @player_required
    async def handle_create_sect(self, event: AstrMessageEvent):
        player: Player = event.player
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_CREATE_SECT} <宗门名称>」。")
            return
        
        sect_name = parts[1]
        success, msg, updated_player = await xiuxian_logic.handle_create_sect(player, sect_name)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_JOIN_SECT, "加入一个宗门")
    @player_required
    async def handle_join_sect(self, event: AstrMessageEvent):
        player: Player = event.player
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_JOIN_SECT} <宗门名称>」。")
            return
        
        sect_name = parts[1]
        success, msg, updated_player = await xiuxian_logic.handle_join_sect(player, sect_name)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_LEAVE_SECT, "退出当前宗门")
    @player_required
    async def handle_leave_sect(self, event: AstrMessageEvent):
        player: Player = event.player
        success, msg, updated_player = await xiuxian_logic.handle_leave_sect(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)
        
    @filter.command(config.CMD_MY_SECT, "查看我的宗门信息")
    @player_required
    async def handle_my_sect(self, event: AstrMessageEvent):
        player: Player = event.player
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

        # 健壮性增强：检查宗主是否存在
        leader_player = await data_manager.get_player_by_id(sect_info['leader_id'])
        leader_info = f"宗主: {leader_player.user_id[-4:]}" if leader_player else "宗主: (信息丢失)"

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