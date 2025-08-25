import re
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

    # ... (All previous handlers remain unchanged)
    @filter.command(config.CMD_START_XIUXIAN, "开始你的修仙之路")
    async def handle_start_xiuxian(self, event: AstrMessageEvent):
        """处理开始修仙的指令"""
        user_id = event.sender.id
        player = data_manager.get_player_by_id(user_id)

        if player:
            await event.reply("道友，你已踏入仙途，无需重复此举。使用「我的信息」查看修行成果吧。")
            return

        new_player = xiuxian_logic.generate_new_player_stats(user_id)
        data_manager.create_player(new_player)

        reply_msg = (
            f"恭喜道友 {event.sender.name} 踏上仙途！\n"
            f"你的初始灵根为：【{new_player.spiritual_root}】\n"
            f"门派赠予你启动资金：【{new_player.gold}】灵石\n"
            "发送「我的信息」来查看你的状态，发送「签到」领取每日福利吧！"
        )
        await event.reply(reply_msg)
        
    @filter.command(config.CMD_PLAYER_INFO, "查看你的角色信息")
    async def handle_player_info(self, event: AstrMessageEvent):
        """处理查看角色信息的指令"""
        user_id = event.sender.id
        player = data_manager.get_player_by_id(user_id)

        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        
        sect_info = f"宗门：{player.sect_name if player.sect_name else '逍遥散人'}"

        reply_msg = (
            f"--- 道友 {event.sender.name} 的信息 ---\n"
            f"境界：{player.level}\n"
            f"灵根：{player.spiritual_root}\n"
            f"修为：{player.experience}\n"
            f"灵石：{player.gold}\n"
            f"{sect_info}\n"
            f"状态：{player.state}\n"
            f"--------------------------"
        )
        await event.reply(reply_msg)

    @filter.command(config.CMD_CHECK_IN, "每日签到领取奖励")
    async def handle_check_in(self, event: AstrMessageEvent):
        """处理签到指令"""
        user_id = event.sender.id
        player = data_manager.get_player_by_id(user_id)

        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return

        success, msg, updated_player = xiuxian_logic.handle_check_in(player)
        
        if success:
            data_manager.update_player(updated_player)

        await event.reply(msg)

    @filter.command(config.CMD_START_CULTIVATION, "开始闭关修炼")
    async def handle_start_cultivation(self, event: AstrMessageEvent):
        """处理闭关指令"""
        user_id = event.sender.id
        player = data_manager.get_player_by_id(user_id)

        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return

        success, msg, updated_player = xiuxian_logic.handle_start_cultivation(player)

        if success:
            data_manager.update_player(updated_player)
        
        await event.reply(msg)

    @filter.command(config.CMD_END_CULTIVATION, "结束闭关修炼")
    async def handle_end_cultivation(self, event: AstrMessageEvent):
        """处理出关指令"""
        user_id = event.sender.id
        player = data_manager.get_player_by_id(user_id)

        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
            
        success, msg, updated_player = xiuxian_logic.handle_end_cultivation(player)

        if success:
            data_manager.update_player(updated_player)
            
        await event.reply(msg)
    
    @filter.command(config.CMD_BREAKTHROUGH, "尝试突破当前境界")
    async def handle_breakthrough(self, event: AstrMessageEvent):
        """处理突破指令"""
        user_id = event.sender.id
        player = data_manager.get_player_by_id(user_id)

        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        
        if player.state != "空闲":
            await event.reply(f"道友当前正在「{player.state}」中，心有旁骛，无法尝试突破。")
            return
            
        success, msg, updated_player = xiuxian_logic.handle_breakthrough(player)

        if success:
            data_manager.update_player(updated_player)
            
        await event.reply(msg)

    @filter.command(config.CMD_SHOP, "查看坊市商品")
    async def handle_shop(self, event: AstrMessageEvent):
        """处理商店指令"""
        reply_msg = "--- 仙途坊市 ---\n"
        for item_id, info in config.item_data.items():
            reply_msg += f"【{info['name']}】\n"
            reply_msg += f"  类型：{info['type']}\n"
            reply_msg += f"  售价：{info['price']} 灵石\n"
            reply_msg += f"  描述：{info['description']}\n"
        reply_msg += "------------------\n"
        reply_msg += f"使用「{config.CMD_BUY} <物品名> [数量]」进行购买。"
        await event.reply(reply_msg)

    @filter.command(config.CMD_BACKPACK, "查看你的背包")
    async def handle_backpack(self, event: AstrMessageEvent):
        """处理背包指令"""
        user_id = event.sender.id
        if not data_manager.get_player_by_id(user_id):
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
            
        inventory = data_manager.get_inventory_by_user_id(user_id)
        if not inventory:
            await event.reply("道友的背包空空如也，快去坊市逛逛吧！")
            return
        
        reply_msg = f"--- 道友 {event.sender.name} 的背包 ---\n"
        for item in inventory:
            reply_msg += f"【{item['name']}】x{item['quantity']}\n"
            reply_msg += f"  描述：{item['description']}\n"
        reply_msg += "--------------------------"
        await event.reply(reply_msg)

    @filter.command(config.CMD_BUY, "购买物品")
    async def handle_buy(self, event: AstrMessageEvent):
        """处理购买指令"""
        user_id = event.sender.id
        player = data_manager.get_player_by_id(user_id)
        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return

        text = event.get_plaintext().strip()
        parts = text.split()
        if len(parts) < 2:
            await event.reply(f"指令格式错误！请使用「{config.CMD_BUY} <物品名> [数量]」，数量可选，默认为1。")
            return

        item_name = parts[1]
        quantity = 1
        if len(parts) > 2 and parts[2].isdigit():
            quantity = int(parts[2])
            if quantity <= 0:
                await event.reply("购买数量必须是正整数！")
                return
        
        success, msg, updated_player, item_id_to_add = xiuxian_logic.handle_buy_item(player, item_name, quantity)

        if success:
            data_manager.update_player(updated_player)
            data_manager.add_item_to_inventory(user_id, item_id_to_add, quantity)

        await event.reply(msg)
        
    @filter.command(config.CMD_CREATE_SECT, "创建你的宗门")
    async def handle_create_sect(self, event: AstrMessageEvent):
        user_id = event.sender.id
        player = data_manager.get_player_by_id(user_id)
        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return

        text = event.get_plaintext().strip()
        parts = text.split()
        if len(parts) < 2:
            await event.reply(f"指令格式错误！请使用「{config.CMD_CREATE_SECT} <宗门名称>」。")
            return
        
        sect_name = parts[1]
        success, msg, updated_player = xiuxian_logic.handle_create_sect(player, sect_name)
        if success:
            data_manager.update_player(updated_player)
        
        await event.reply(msg)

    @filter.command(config.CMD_JOIN_SECT, "加入一个宗门")
    async def handle_join_sect(self, event: AstrMessageEvent):
        user_id = event.sender.id
        player = data_manager.get_player_by_id(user_id)
        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return

        text = event.get_plaintext().strip()
        parts = text.split()
        if len(parts) < 2:
            await event.reply(f"指令格式错误！请使用「{config.CMD_JOIN_SECT} <宗门名称>」。")
            return
        
        sect_name = parts[1]
        success, msg, updated_player = xiuxian_logic.handle_join_sect(player, sect_name)
        if success:
            data_manager.update_player(updated_player)
        
        await event.reply(msg)

    @filter.command(config.CMD_LEAVE_SECT, "退出当前宗门")
    async def handle_leave_sect(self, event: AstrMessageEvent):
        user_id = event.sender.id
        player = data_manager.get_player_by_id(user_id)
        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
            
        success, msg, updated_player = xiuxian_logic.handle_leave_sect(player)
        if success:
            data_manager.update_player(updated_player)
        
        await event.reply(msg)
        
    @filter.command(config.CMD_MY_SECT, "查看我的宗门信息")
    async def handle_my_sect(self, event: AstrMessageEvent):
        user_id = event.sender.id
        player = data_manager.get_player_by_id(user_id)
        if not player:
            await event.reply(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return

        if not player.sect_id:
            await event.reply("道友乃逍遥散人，尚未加入任何宗门。")
            return
            
        sect_info = data_manager.get_sect_by_id(player.sect_id)
        if not sect_info:
            await event.reply("错误：找不到你的宗门信息，可能已被解散。")
            # Clear player's outdated sect info
            data_manager.update_player_sect(user_id, None, None)
            return

        leader = data_manager.get_player_by_id(sect_info['leader_id'])
        leader_name = event.sender.name if leader.user_id == user_id else "未知" # This part needs a better way to get names
        members = data_manager.get_sect_members(player.sect_id)
        
        reply_msg = (
            f"--- {sect_info['name']} (Lv.{sect_info['level']}) ---\n"
            f"宗主：{leader_name}\n"
            f"资金：{sect_info['funds']} 灵石\n"
            f"成员 ({len(members)}人):\n"
        )
        reply_msg += ", ".join([f"ID:{m.user_id[-4:]}" for m in members])
        reply_msg += "\n--------------------------"

        await event.reply(reply_msg)
        
    @filter.command(config.CMD_HELP, "显示帮助信息")
    async def handle_help(self, event: AstrMessageEvent):
        """处理帮助指令"""
        help_text = (
            "--- 寻仙指令手册 ---\n"
            f"【{config.CMD_START_XIUXIAN}】: 开启你的修仙之旅。\n"
            f"【{config.CMD_PLAYER_INFO}】: 查看你的人物信息。\n"
            f"【{config.CMD_CHECK_IN}】: 每日签到，领取灵石。\n"
            "--- 修炼与成长 ---\n"
            f"【{config.CMD_START_CULTIVATION}】: 进入闭关，持续获取修为。\n"
            f"【{config.CMD_END_CULTIVATION}】: 结束闭关，结算修为。\n"
            f"【{config.CMD_BREAKTHROUGH}】: 消耗修为，尝试突破当前境界。\n"
            "--- 坊市与物品 ---\n"
            f"【{config.CMD_SHOP}】: 查看坊市中出售的商品。\n"
            f"【{config.CMD_BACKPACK}】: 查看你背包中的物品。\n"
            f"【{config.CMD_BUY} <物品名> [数量]】: 购买指定物品。\n"
            "--- 宗门社交 ---\n"
            f"【{config.CMD_CREATE_SECT} <名称>】: 创建属于你的宗门。\n"
            f"【{config.CMD_JOIN_SECT} <名称>】: 加入一个已存在的宗门。\n"
            f"【{config.CMD_MY_SECT}】: 查看你所在宗门的详细信息。\n"
            f"【{config.CMD_LEAVE_SECT}】: 脱离当前所在的宗门。\n"
            "--------------------"
        )
        await event.reply(help_text)

    async def terminate(self):
        """插件卸载/停用时调用，可用于资源清理。"""
        logger.info("修仙插件已卸载。")