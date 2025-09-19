# main.py

import aiosqlite
from functools import wraps
from typing import Optional, Callable, Awaitable
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
    "v2.0.0", 
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
        logger.info("修仙插件已加载。")

    async def terminate(self):
        await data_manager.close_db_pool()
        logger.info("修仙插件已卸载。")

    async def _execute_with_player(self, event: AstrMessageEvent, handler_func: Callable, *args, **kwargs):
        """
        一个通用的异步生成器执行器。
        1. 检查玩家是否存在。
        2. 如果不存在，yield错误信息。
        3. 如果存在，则调用指定的handler_func并yield其结果。
        """
        player = await data_manager.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        
        async for r in handler_func(event, player, *args, **kwargs):
            yield r

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
        async for r in self._execute_with_player(event, self.player_handler.handle_player_info):
            yield r

    @filter.command(config.CMD_CHECK_IN, "每日签到领取奖励")
    async def handle_check_in(self, event: AstrMessageEvent):
        async for r in self._execute_with_player(event, self.player_handler.handle_check_in):
            yield r
        
    @filter.command(config.CMD_START_CULTIVATION, "开始闭关修炼")
    async def handle_start_cultivation(self, event: AstrMessageEvent):
        async for r in self._execute_with_player(event, self.player_handler.handle_start_cultivation):
            yield r

    @filter.command(config.CMD_END_CULTIVATION, "结束闭关修炼")
    async def handle_end_cultivation(self, event: AstrMessageEvent):
        async for r in self._execute_with_player(event, self.player_handler.handle_end_cultivation):
            yield r

    @filter.command(config.CMD_BREAKTHROUGH, "尝试突破当前境界")
    async def handle_breakthrough(self, event: AstrMessageEvent):
        async for r in self._execute_with_player(event, self.player_handler.handle_breakthrough):
            yield r

    # Shop Commands
    @filter.command(config.CMD_SHOP, "查看坊市商品")
    async def handle_shop(self, event: AstrMessageEvent):
        async for r in self.shop_handler.handle_shop(event): yield r
        
    @filter.command(config.CMD_BACKPACK, "查看你的背包")
    async def handle_backpack(self, event: AstrMessageEvent):
        async for r in self._execute_with_player(event, self.shop_handler.handle_backpack):
            yield r

    @filter.command(config.CMD_BUY, "购买物品")
    async def handle_buy(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        async for r in self._execute_with_player(event, self.shop_handler.handle_buy, item_name, quantity):
            yield r
        
    @filter.command(config.CMD_USE_ITEM, "使用背包中的物品")
    async def handle_use(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        async for r in self._execute_with_player(event, self.shop_handler.handle_use, item_name, quantity):
            yield r

    # Sect Commands
    @filter.command(config.CMD_CREATE_SECT, "创建你的宗门")
    async def handle_create_sect(self, event: AstrMessageEvent, sect_name: str):
        async for r in self._execute_with_player(event, self.sect_handler.handle_create_sect, sect_name):
            yield r

    @filter.command(config.CMD_JOIN_SECT, "加入一个宗门")
    async def handle_join_sect(self, event: AstrMessageEvent, sect_name: str):
        async for r in self._execute_with_player(event, self.sect_handler.handle_join_sect, sect_name):
            yield r

    @filter.command(config.CMD_LEAVE_SECT, "退出当前宗门")
    async def handle_leave_sect(self, event: AstrMessageEvent):
        async for r in self._execute_with_player(event, self.sect_handler.handle_leave_sect):
            yield r
        
    @filter.command(config.CMD_MY_SECT, "查看我的宗门信息")
    async def handle_my_sect(self, event: AstrMessageEvent):
        async for r in self._execute_with_player(event, self.sect_handler.handle_my_sect):
            yield r
        
    # Combat Commands
    @filter.command(config.CMD_SPAR, "与其他玩家切磋")
    async def handle_spar(self, event: AstrMessageEvent):
        async for r in self._execute_with_player(event, self.combat_handler.handle_spar):
            yield r
        
    @filter.command(config.CMD_BOSS_LIST, "查看当前所有世界Boss")
    async def handle_boss_list(self, event: AstrMessageEvent):
        async for r in self.combat_handler.handle_boss_list(event): yield r

    @filter.command(config.CMD_FIGHT_BOSS, "讨伐指定ID的世界Boss")
    async def handle_fight_boss(self, event: AstrMessageEvent, boss_id: str):
        player_name = event.get_sender_name()
        async for r in self._execute_with_player(event, self.combat_handler.handle_fight_boss, boss_id, player_name):
            yield r
        
    # Realm Commands
    @filter.command(config.CMD_ENTER_REALM, "根据当前境界，探索一个随机秘境")
    async def handle_enter_realm(self, event: AstrMessageEvent):
        async for r in self._execute_with_player(event, self.realm_handler.handle_enter_realm):
            yield r

    @filter.command(config.CMD_REALM_ADVANCE, "在秘境中前进")
    async def handle_realm_advance(self, event: AstrMessageEvent):
        async for r in self._execute_with_player(event, self.realm_handler.handle_realm_advance):
            yield r

    @filter.command(config.CMD_LEAVE_REALM, "离开当前秘境")
    async def handle_leave_realm(self, event: AstrMessageEvent):
        async for r in self._execute_with_player(event, self.realm_handler.handle_leave_realm):
            yield r