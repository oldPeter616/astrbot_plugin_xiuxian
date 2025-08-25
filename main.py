import re
from functools import wraps
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter, MessageEventResult
from astrbot.api.star import Context, Star, register

from . import data_manager, xiuxian_logic
from .config_manager import config
from .models import Player

# --- 装饰器定义 (已重构) ---
def player_required(func):
    """
    装饰器：检查玩家是否存在。
    如果存在，则将 player 对象附加到 event 对象上 (event.player)。
    """
    @wraps(func)
    async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
        user_id = event.get_sender_id()
        player = await data_manager.get_player_by_id(user_id)

        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        
        # 将 player 对象附加到 event 上下文中
        setattr(event, 'player', player)
        
        # 使用原始参数调用被装饰的函数
        async for result in func(self, event, *args, **kwargs):
            yield result
            
    return wrapper

@register("xiuxian", "YourName", "一个文字修仙插件", "1.0.0")
class XiuXianPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        await data_manager.init_database()
        logger.info("修仙插件：数据库初始化成功。")

    @filter.command(config.CMD_START_XIUXIAN, "开始你的修仙之路")
    async def handle_start_xiuxian(self, event: AstrMessageEvent) -> MessageEventResult:
        user_id = event.get_sender_id()
        if await data_manager.get_player_by_id(user_id):
            yield event.plain_result("道友，你已踏入仙途，无需重复此举。")
            return

        new_player = xiuxian_logic.generate_new_player_stats(user_id)
        await data_manager.create_player(new_player)
        reply_msg = (
            f"恭喜道友 {event.get_sender_name()} 踏上仙途！\n"
            f"初始灵根：【{new_player.spiritual_root}】\n"
            f"启动资金：【{new_player.gold}】灵石\n"
            f"发送「{config.CMD_PLAYER_INFO}」查看状态，「{config.CMD_CHECK_IN}」领取福利！"
        )
        yield event.plain_result(reply_msg)

    @filter.command(config.CMD_PLAYER_INFO, "查看你的角色信息")
    @player_required
    async def handle_player_info(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player # 从 event 中获取 player 对象
        sect_info = f"宗门：{player.sect_name if player.sect_name else '逍遥散人'}"
        reply_msg = (
            f"--- 道友 {event.get_sender_name()} 的信息 ---\n"
            f"境界：{player.level}\n"
            f"灵根：{player.spiritual_root}\n"
            f"修为：{player.experience}\n"
            f"灵石：{player.gold}\n"
            f"{sect_info}\n"
            f"状态：{player.state}\n"
            f"--------------------------"
        )
        yield event.plain_result(reply_msg)

    @filter.command(config.CMD_CHECK_IN, "每日签到领取奖励")
    @player_required
    async def handle_check_in(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        success, msg, updated_player = xiuxian_logic.handle_check_in(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_START_CULTIVATION, "开始闭关修炼")
    @player_required
    async def handle_start_cultivation(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        success, msg, updated_player = xiuxian_logic.handle_start_cultivation(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_END_CULTIVATION, "结束闭关修炼")
    @player_required
    async def handle_end_cultivation(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        success, msg, updated_player = xiuxian_logic.handle_end_cultivation(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)
    
    @filter.command(config.CMD_BREAKTHROUGH, "尝试突破当前境界")
    @player_required
    async def handle_breakthrough(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        if player.state != "空闲":
            yield event.plain_result(f"道友当前正在「{player.state}」中，无法尝试突破。")
            return
        success, msg, updated_player = xiuxian_logic.handle_breakthrough(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_SHOP, "查看坊市商品")
    async def handle_shop(self, event: AstrMessageEvent) -> MessageEventResult:
        reply_msg = "--- 仙途坊市 ---\n"
        for item_id, info in config.item_data.items():
            reply_msg += f"【{info['name']}】售价：{info['price']} 灵石\n"
        reply_msg += "------------------\n"
        reply_msg += f"使用「{config.CMD_BUY} <物品名> [数量]」进行购买。"
        yield event.plain_result(reply_msg)

    @filter.command(config.CMD_BACKPACK, "查看你的背包")
    @player_required
    async def handle_backpack(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
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
    async def handle_buy(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        text = event.message_str.strip()
        parts = text.split()
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_BUY} <物品名> [数量]」。")
            return

        item_name = parts[1]
        quantity = 1
        if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) > 0:
            quantity = int(parts[2])
        
        success, msg, updated_player, item_id_to_add = xiuxian_logic.handle_buy_item(player, item_name, quantity)
        if success:
            await data_manager.update_player(updated_player)
            await data_manager.add_item_to_inventory(player.user_id, item_id_to_add, quantity)
        yield event.plain_result(msg)
        
    @filter.command(config.CMD_CREATE_SECT, "创建你的宗门")
    @player_required
    async def handle_create_sect(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        text = event.message_str.strip()
        parts = text.split()
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
    async def handle_join_sect(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        text = event.message_str.strip()
        parts = text.split()
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
    async def handle_leave_sect(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        success, msg, updated_player = await xiuxian_logic.handle_leave_sect(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)
        
    @filter.command(config.CMD_MY_SECT, "查看我的宗门信息")
    @player_required
    async def handle_my_sect(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        if not player.sect_id:
            yield event.plain_result("道友乃逍遥散人，尚未加入任何宗门。")
            return
            
        sect_info = await data_manager.get_sect_by_id(player.sect_id)
        if not sect_info:
            yield event.plain_result("错误：找不到你的宗门信息，可能已被解散。")
            await data_manager.update_player_sect(player.user_id, None, None)
            return

        leader_info = f"宗主ID: {sect_info['leader_id']}"
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
        
    @filter.command(config.CMD_HELP, "显示帮助信息")
    async def handle_help(self, event: AstrMessageEvent) -> MessageEventResult:
        help_text = (
            "--- 寻仙指令手册 ---\n"
            f"【{config.CMD_START_XIUXIAN}】: 开启修仙之旅。\n"
            f"【{config.CMD_PLAYER_INFO}】: 查看人物信息。\n"
            f"【{config.CMD_CHECK_IN}】: 每日签到。\n"
            "--- 修炼与成长 ---\n"
            f"【{config.CMD_START_CULTIVATION}】: 开始闭关。\n"
            f"【{config.CMD_END_CULTIVATION}】: 结束闭关。\n"
            f"【{config.CMD_BREAKTHROUGH}】: 尝试突破境界。\n"
            "--- 坊市与物品 ---\n"
            f"【{config.CMD_SHOP}】: 查看坊市商品。\n"
            f"【{config.CMD_BACKPACK}】: 查看个人背包。\n"
            f"【{config.CMD_BUY} <物品名> [数量]】: 购买物品。\n"
            "--- 宗门社交 ---\n"
            f"【{config.CMD_CREATE_SECT} <名称>】: 创建宗门。\n"
            f"【{config.CMD_JOIN_SECT} <名称>】: 加入宗门。\n"
            f"【{config.CMD_MY_SECT}】: 查看宗门信息。\n"
            f"【{config.CMD_LEAVE_SECT}】: 退出宗门。\n"
            "--------------------"
        )
        yield event.plain_result(help_text)

    async def terminate(self):
        logger.info("修仙插件已卸载。")