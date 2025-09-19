# main.py
from astrbot.api import logger
from astrbot.api.star import Context, Star, register
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.core.config.astrbot_config import AstrBotConfig
from data.plugins.astrbot_plugin_xiuxian.data.migration import MigrationManager

# --- 核心依赖 ---
from .data.data_manager import DataBase
from .config_manager import config


# --- 导入独立的 Handler 类 ---
from .handlers import (
    MiscHandler,
    PlayerHandler,
    ShopHandler,
    SectHandler,
    CombatHandler,
    RealmHandler,
)


@register("astrbot_plugin_xiuxian", "oldPeter616", "...", "...")
class XiuXianPlugin(Star):
    xiuxian_dataBase_version = 8
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.conf = config  # astrbot_config, 备用

    async def initialize(self):
        # --- 数据库 ---
        self.db = DataBase()
        await self.db.init()

        # --- 数据迁移 ---
        self.migration_manager = MigrationManager(self.xiuxian_dataBase_version)
        await self.migration_manager.migrate(self.db._conn)

        # --- 实例化所有 Handler ---
        self.misc_handler = MiscHandler(self.db)
        self.player_handler = PlayerHandler(self.db)
        self.shop_handler = ShopHandler(self.db)
        self.sect_handler = SectHandler(self.db)
        self.combat_handler = CombatHandler(self.db)
        self.realm_handler = RealmHandler(self.db)

        logger.info("修仙插件已加载")

    async def terminate(self):
        await self.db.close()
        logger.info("修仙插件已优雅关闭")

    # Misc Commands
    @filter.command(config.CMD_HELP, "显示帮助信息")
    async def handle_help(self, event: AstrMessageEvent):
        async for r in self.misc_handler.handle_help(event):
            yield r

    # Player Commands
    @filter.command(config.CMD_START_XIUXIAN, "开始你的修仙之路")
    async def handle_start_xiuxian(self, event: AstrMessageEvent):
        async for r in self.player_handler.handle_start_xiuxian(event):
            yield r

    @filter.command(config.CMD_PLAYER_INFO, "查看你的角色信息")
    async def handle_player_info(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.player_handler.handle_player_info(event, player):
            yield r

    @filter.command(config.CMD_CHECK_IN, "每日签到领取奖励")
    async def handle_check_in(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.player_handler.handle_check_in(event, player):
            yield r

    @filter.command(config.CMD_START_CULTIVATION, "开始闭关修炼")
    async def handle_start_cultivation(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.player_handler.handle_start_cultivation(event, player):
            yield r

    @filter.command(config.CMD_END_CULTIVATION, "结束闭关修炼")
    async def handle_end_cultivation(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.player_handler.handle_end_cultivation(event, player):
            yield r

    @filter.command(config.CMD_BREAKTHROUGH, "尝试突破当前境界")
    async def handle_breakthrough(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.player_handler.handle_breakthrough(event, player):
            yield r

    # Shop Commands
    @filter.command(config.CMD_SHOP, "查看坊市商品")
    async def handle_shop(self, event: AstrMessageEvent):
        async for r in self.shop_handler.handle_shop(event):
            yield r

    @filter.command(config.CMD_BACKPACK, "查看你的背包")
    async def handle_backpack(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.shop_handler.handle_backpack(event, player):
            yield r

    @filter.command(config.CMD_BUY, "购买物品")
    async def handle_buy(
        self, event: AstrMessageEvent, item_name: str, quantity: int = 1
    ):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.shop_handler.handle_buy(event, item_name, quantity, player):
            yield r

    @filter.command(config.CMD_USE_ITEM, "使用背包中的物品")
    async def handle_use(
        self, event: AstrMessageEvent, item_name: str, quantity: int = 1
    ):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.shop_handler.handle_use(event, item_name, quantity, player):
            yield r

    # Sect Commands
    @filter.command(config.CMD_CREATE_SECT, "创建你的宗门")
    async def handle_create_sect(self, event: AstrMessageEvent, sect_name: str):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.sect_handler.handle_create_sect(event, sect_name, player):
            yield r

    @filter.command(config.CMD_JOIN_SECT, "加入一个宗门")
    async def handle_join_sect(self, event: AstrMessageEvent, sect_name: str):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.sect_handler.handle_join_sect(event, sect_name, player):
            yield r

    @filter.command(config.CMD_LEAVE_SECT, "退出当前宗门")
    async def handle_leave_sect(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.sect_handler.handle_leave_sect(event, player):
            yield r

    @filter.command(config.CMD_MY_SECT, "查看我的宗门信息")
    async def handle_my_sect(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.sect_handler.handle_my_sect(event, player):
            yield r

    # Combat Commands
    @filter.command(config.CMD_SPAR, "与其他玩家切磋")
    async def handle_spar(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.combat_handler.handle_spar(event, player):
            yield r

    @filter.command(config.CMD_BOSS_LIST, "查看当前所有世界Boss")
    async def handle_boss_list(self, event: AstrMessageEvent):
        async for r in self.combat_handler.handle_boss_list(event):
            yield r

    @filter.command(config.CMD_FIGHT_BOSS, "讨伐指定ID的世界Boss")
    async def handle_fight_boss(self, event: AstrMessageEvent, boss_id: str):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        player_name = event.get_sender_name()
        async for r in self.combat_handler.handle_fight_boss(
            event, player, boss_id, player_name
        ):
            yield r

    # Realm Commands
    @filter.command(config.CMD_ENTER_REALM, "根据当前境界，探索一个随机秘境")
    async def handle_enter_realm(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.realm_handler.handle_enter_realm(event, player):
            yield r

    @filter.command(config.CMD_REALM_ADVANCE, "在秘境中前进")
    async def handle_realm_advance(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.realm_handler.handle_realm_advance(event, player):
            yield r

    @filter.command(config.CMD_LEAVE_REALM, "离开当前秘境")
    async def handle_leave_realm(self, event: AstrMessageEvent):
        player = await self.db.get_player_by_id(event.get_sender_id())
        if not player:
            yield event.plain_result(
                f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。"
            )
            return
        async for r in self.realm_handler.handle_leave_realm(event, player):
            yield r
