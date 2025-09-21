# main.py

from astrbot.api import logger
from astrbot.api.star import Context, Star, register
from astrbot.api.event import AstrMessageEvent, filter

# --- 核心依赖 ---
from .config_manager import config
from .data import DataBase, MigrationManager

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
        # --- 核心数据管理器 ---
        self.db = DataBase()

        # --- 实例化所有 Handler，将 db 实例传入 ---
        self.misc_handler = MiscHandler(self.db)
        self.player_handler = PlayerHandler(self.db)
        self.shop_handler = ShopHandler(self.db)
        self.sect_handler = SectHandler(self.db)
        self.combat_handler = CombatHandler(self.db)
        self.realm_handler = RealmHandler(self.db)

    async def initialize(self):
        # 初始化数据库连接
        await self.db.connect()
        # 执行数据库迁移
        migration_manager = MigrationManager(self.db.conn)
        await migration_manager.migrate()
        logger.info("修仙插件已加载。")

    async def terminate(self):
        await self.db.close()
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
        async for r in self.player_handler.handle_player_info(event): yield r

    @filter.command(config.CMD_CHECK_IN, "每日签到领取奖励")
    async def handle_check_in(self, event: AstrMessageEvent):
        async for r in self.player_handler.handle_check_in(event): yield r

    @filter.command(config.CMD_START_CULTIVATION, "开始闭关修炼")
    async def handle_start_cultivation(self, event: AstrMessageEvent):
        async for r in self.player_handler.handle_start_cultivation(event): yield r

    @filter.command(config.CMD_END_CULTIVATION, "结束闭关修炼")
    async def handle_end_cultivation(self, event: AstrMessageEvent):
        async for r in self.player_handler.handle_end_cultivation(event): yield r

    @filter.command(config.CMD_BREAKTHROUGH, "尝试突破当前境界")
    async def handle_breakthrough(self, event: AstrMessageEvent):
        async for r in self.player_handler.handle_breakthrough(event): yield r

    # Shop Commands
    @filter.command(config.CMD_SHOP, "查看坊市商品")
    async def handle_shop(self, event: AstrMessageEvent):
        async for r in self.shop_handler.handle_shop(event): yield r

    @filter.command(config.CMD_BACKPACK, "查看你的背包")
    async def handle_backpack(self, event: AstrMessageEvent):
        async for r in self.shop_handler.handle_backpack(event): yield r

    @filter.command(config.CMD_BUY, "购买物品")
    async def handle_buy(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        async for r in self.shop_handler.handle_buy(event, item_name, quantity): yield r

    @filter.command(config.CMD_USE_ITEM, "使用背包中的物品")
    async def handle_use(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        async for r in self.shop_handler.handle_use(event, item_name, quantity): yield r

    # Sect Commands
    @filter.command(config.CMD_CREATE_SECT, "创建你的宗门")
    async def handle_create_sect(self, event: AstrMessageEvent, sect_name: str):
        async for r in self.sect_handler.handle_create_sect(event, sect_name): yield r

    @filter.command(config.CMD_JOIN_SECT, "加入一个宗门")
    async def handle_join_sect(self, event: AstrMessageEvent, sect_name: str):
        async for r in self.sect_handler.handle_join_sect(event, sect_name): yield r

    @filter.command(config.CMD_LEAVE_SECT, "退出当前宗门")
    async def handle_leave_sect(self, event: AstrMessageEvent):
        async for r in self.sect_handler.handle_leave_sect(event): yield r

    @filter.command(config.CMD_MY_SECT, "查看我的宗门信息")
    async def handle_my_sect(self, event: AstrMessageEvent):
        async for r in self.sect_handler.handle_my_sect(event): yield r

    # Combat Commands
    @filter.command(config.CMD_SPAR, "与其他玩家切磋")
    async def handle_spar(self, event: AstrMessageEvent):
        async for r in self.combat_handler.handle_spar(event): yield r

    @filter.command(config.CMD_BOSS_LIST, "查看当前所有世界Boss")
    async def handle_boss_list(self, event: AstrMessageEvent):
        async for r in self.combat_handler.handle_boss_list(event): yield r

    @filter.command(config.CMD_FIGHT_BOSS, "讨伐指定ID的世界Boss")
    async def handle_fight_boss(self, event: AstrMessageEvent, boss_id: str):
        async for r in self.combat_handler.handle_fight_boss(event, boss_id): yield r

    # Realm Commands
    @filter.command(config.CMD_ENTER_REALM, "根据当前境界，探索一个随机秘境")
    async def handle_enter_realm(self, event: AstrMessageEvent):
        async for r in self.realm_handler.handle_enter_realm(event): yield r

    @filter.command(config.CMD_REALM_ADVANCE, "在秘境中前进")
    async def handle_realm_advance(self, event: AstrMessageEvent):
        async for r in self.realm_handler.handle_realm_advance(event): yield r

    @filter.command(config.CMD_LEAVE_REALM, "离开当前秘境")
    async def handle_leave_realm(self, event: AstrMessageEvent):
        async for r in self.realm_handler.handle_leave_realm(event): yield r