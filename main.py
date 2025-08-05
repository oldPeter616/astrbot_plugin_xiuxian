from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from . import data_manager, xiuxian_logic
from .config_manager import config


@register("xiuxian", "YourName", "一个文字修仙插件", "1.0.0")
class XiuXianPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """插件初始化，在插件被加载时自动调用。"""
        try:
            data_manager.init_database()
            logger.info("修仙插件：数据库初始化成功。")
        except Exception as e:
            logger.error(f"修仙插件：数据库初始化失败，错误：{e}")

    @filter.command(config.CMD_START_XIUXIAN, "开始你的修仙之路")
    async def handle_start_xiuxian(self, event: AstrMessageEvent):
        """处理开始修仙的指令"""
        # --- 修改点 ---
        # 调用 event.get_user_id() 修正为直接访问属性 event.user_id
        user_id = event.user_id
        player = data_manager.get_player_by_id(user_id)

        if player:
            await event.reply("道友，你已踏入仙途，无需重复此举。使用「我的信息」查看修行成果吧。")
            return

        new_player = xiuxian_logic.generate_new_player_stats(user_id)
        data_manager.create_player(new_player)

        # --- 修改点 ---
        # 调用 event.get_sender_name() 修正为直接访问属性 event.sender_name
        reply_msg = (
            f"恭喜道友 {event.sender_name} 踏上仙途！\n"
            f"你的初始灵根为：【{new_player.spiritual_root}】\n"
            f"门派赠予你启动资金：【{new_player.gold}】灵石\n"
            "发送「我的信息」来查看你的状态，发送「签到」领取每日福利吧！"
        )
        await event.reply(reply_msg)

    @filter.command(config.CMD_PLAYER_INFO, "查看你的角色信息")
    async def handle_player_info(self, event: AstrMessageEvent):
        """处理查看角色信息的指令"""
        # --- 修改点 ---
        user_id = event.user_id
        player = data_manager.get_player_by_id(user_id)

        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return

        # --- 修改点 ---
        reply_msg = (
            f"--- 道友 {event.sender_name} 的信息 ---\n"
            f"境界：{player.level}\n"
            f"灵根：{player.spiritual_root}\n"
            f"修为：{player.experience}\n"
            f"灵石：{player.gold}\n"
            f"--------------------------"
        )
        await event.reply(reply_msg)

    @filter.command(config.CMD_CHECK_IN, "每日签到领取奖励")
    async def handle_check_in(self, event: AstrMessageEvent):
        """处理签到指令"""
        # --- 修改点 ---
        user_id = event.user_id
        player = data_manager.get_player_by_id(user_id)

        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return

        success, msg, updated_player = xiuxian_logic.handle_check_in(player)
        
        if success:
            data_manager.update_player(updated_player)

        await event.reply(msg)

    async def terminate(self):
        """插件卸载/停用时调用，可用于资源清理。"""
        logger.info("修仙插件已卸载。")