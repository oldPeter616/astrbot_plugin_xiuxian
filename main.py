# main.py

import aiosqlite
from astrbot.api import logger
from astrbot.api.star import Context, Star, register
from astrbot.api.event import AstrMessageEvent, filter

# --- 核心依赖 ---
from . import data_manager, xiuxian_logic, combat_manager, realm_manager
from .config_manager import config
from .models import Player

# --- 导入独立的 Handler 类 ---
from .handlers import (
    MiscHandler, PlayerHandler, ShopHandler, SectHandler, 
    CombatHandler, RealmHandler
)

@register(
    "astrbot_plugin_xiuxian", 
    "oldPeter616", 
    "基于astrbot框架的文字修仙游戏", 
    "v1.2.0", 
    "https://github.com/oldPeter616/astrbot_plugin_xiuxian"
)
class XiuXianPlugin(Star):
    
    def __init__(self, context: Context):
        super().__init__(context)
        # --- 核心管理器 ---
        self.battle_manager = combat_manager.BattleManager()
        self.realm_manager = realm_manager.RealmManager()

        # --- 实例化所有 Handler，将 self (插件实例) 传入 ---
        self.misc_handler = MiscHandler(self)
        self.player_handler = PlayerHandler(self)
        self.shop_handler = ShopHandler(self)
        self.sect_handler = SectHandler(self)
        self.combat_handler = CombatHandler(self)
        self.realm_handler = RealmHandler(self)

    async def initialize(self):
        await data_manager.init_db_pool()
        logger.info("修仙插件已加载 (最终版)。")

    async def terminate(self):
        await data_manager.close_db_pool()
        logger.info("修仙插件已卸载。")

    # --- 指令委托实现 ---

    # Misc Commands
    @filter.command(config.CMD_HELP, "显示帮助信息")
    async def handle_help(self, event: AstrMessageEvent):
        async for r in self.misc_handler.handle_help(event): yield r

    # Player Commands
    @filter.command(config.CMD_START_XIUXIAN, "开始你的修仙之路")
    async def handle_start_xiuxian(self, event: AstrMessageEvent):
        async for r in self.player_handler.handle_start_xiuxian(event): yield r

    @filter.command(config.CMD_PLAYER_INFO, "查看你的角色信息")
    async def handle_player_info(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.player_handler.handle_player_info(event, player): yield r

    @filter.command(config.CMD_CHECK_IN, "每日签到领取奖励")
    async def handle_check_in(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.player_handler.handle_check_in(event, player): yield r
        
    @filter.command(config.CMD_START_CULTIVATION, "开始闭关修炼")
    async def handle_start_cultivation(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.player_handler.handle_start_cultivation(event, player): yield r

    @filter.command(config.CMD_END_CULTIVATION, "结束闭关修炼")
    async def handle_end_cultivation(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.player_handler.handle_end_cultivation(event, player): yield r

    @filter.command(config.CMD_BREAKTHROUGH, "尝试突破当前境界")
    async def handle_breakthrough(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.player_handler.handle_breakthrough(event, player): yield r

    # Shop Commands
    @filter.command(config.CMD_SHOP, "查看坊市商品")
    async def handle_shop(self, event: AstrMessageEvent):
        async for r in self.shop_handler.handle_shop(event): yield r
        
    @filter.command(config.CMD_BACKPACK, "查看你的背包")
    async def handle_backpack(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.shop_handler.handle_backpack(event, player): yield r

    @filter.command(config.CMD_BUY, "购买物品")
    async def handle_buy(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.shop_handler.handle_buy(event, item_name, quantity, player): yield r
        
    @filter.command(config.CMD_USE_ITEM, "使用背包中的物品")
    async def handle_use(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.shop_handler.handle_use(event, item_name, quantity, player): yield r

    # Sect Commands
    @filter.command(config.CMD_CREATE_SECT, "创建你的宗门")
    async def handle_create_sect(self, event: AstrMessageEvent, sect_name: str):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.sect_handler.handle_create_sect(event, sect_name, player): yield r

    @filter.command(config.CMD_JOIN_SECT, "加入一个宗门")
    async def handle_join_sect(self, event: AstrMessageEvent, sect_name: str):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.sect_handler.handle_join_sect(event, sect_name, player): yield r

    @filter.command(config.CMD_LEAVE_SECT, "退出当前宗门")
    async def handle_leave_sect(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.sect_handler.handle_leave_sect(event, player): yield r
        
    @filter.command(config.CMD_MY_SECT, "查看我的宗门信息")
    async def handle_my_sect(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.sect_handler.handle_my_sect(event, player): yield r
        
    # Combat Commands
    @filter.command(config.CMD_SPAR, "与其他玩家切磋")
    async def handle_spar(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.combat_handler.handle_spar(event, player): yield r
        
    @filter.command(config.CMD_WORLD_BOSS, "挑战或查看当前的世界Boss")
    async def handle_world_boss(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.combat_handler.handle_world_boss(event, player): yield r

    @filter.command(config.CMD_ATTACK_BOSS, "攻击当前的世界Boss")
    async def handle_attack_boss(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.combat_handler.handle_attack_boss(event, player): yield r

    @filter.command(config.CMD_FIGHT_STATUS, "查看当前战斗状态")
    async def handle_fight_status(self, event: AstrMessageEvent):
        async for r in self.combat_handler.handle_fight_status(event): yield r
        
    # Realm Commands
    @filter.command(config.CMD_REALM_LIST, "查看所有可探索的秘境")
    async def handle_realm_list(self, event: AstrMessageEvent):
        async for r in self.realm_handler.handle_realm_list(event): yield r

    @filter.command(config.CMD_ENTER_REALM, "进入秘境开始探索")
    async def handle_enter_realm(self, event: AstrMessageEvent, realm_name: str):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.realm_handler.handle_enter_realm(event, realm_name, player): yield r

    @filter.command(config.CMD_REALM_ADVANCE, "在秘境中前进")
    async def handle_realm_advance(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.realm_handler.handle_realm_advance(event, player): yield r

    @filter.command(config.CMD_LEAVE_REALM, "离开当前秘境")
    async def handle_leave_realm(self, event: AstrMessageEvent):
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        async for r in self.realm_handler.handle_leave_realm(event, player): yield r