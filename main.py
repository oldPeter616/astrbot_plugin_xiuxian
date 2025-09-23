from pathlib import Path
from astrbot.api import logger, AstrBotConfig
from astrbot.api.star import Context, Star, register
from astrbot.api.event import AstrMessageEvent, filter
from .data import DataBase, MigrationManager
from .config_manager import ConfigManager
from .handlers import (
    MiscHandler, PlayerHandler, ShopHandler, SectHandler, CombatHandler, RealmHandler
)

CMD_HELP = "修仙帮助"
CMD_START_XIUXIAN = "我要修仙"
CMD_PLAYER_INFO = "我的信息"
CMD_CHECK_IN = "签到"
CMD_START_CULTIVATION = "闭关"
CMD_END_CULTIVATION = "出关"
CMD_BREAKTHROUGH = "突破"
CMD_REROLL_SPIRIT_ROOT = "重入仙途"
CMD_SHOP = "商店"
CMD_BACKPACK = "我的背包"
CMD_BUY = "购买"
CMD_USE_ITEM = "使用"
CMD_CREATE_SECT = "创建宗门"
CMD_JOIN_SECT = "加入宗门"
CMD_LEAVE_SECT = "退出宗门"
CMD_MY_SECT = "我的宗门"
CMD_SPAR = "切磋"
CMD_BOSS_LIST = "查看世界boss"
CMD_FIGHT_BOSS = "讨伐boss"
CMD_ENTER_REALM = "探索秘境"
CMD_REALM_ADVANCE = "前进"
CMD_LEAVE_REALM = "离开秘境"

@register(
    "astrbot_plugin_xiuxian",
    "oldPeter616",
    "基 于 astrbot框 架 的 文 字 修 仙 游 戏 ",
    "v2.0.2",
    "https://github.com/oldPeter616/astrbot_plugin_xiuxian"
)
class XiuXianPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        _current_dir = Path(__file__).parent
        self.config_manager = ConfigManager(_current_dir)
        
        files_config = self.config.get("FILES", {})
        db_file = files_config.get("DATABASE_FILE", "xiuxian_data.db")
        self.db = DataBase(db_file)

        self.misc_handler = MiscHandler(self.db)
        self.player_handler = PlayerHandler(self.db, self.config, self.config_manager)
        self.shop_handler = ShopHandler(self.db, self.config_manager)
        self.sect_handler = SectHandler(self.db, self.config, self.config_manager)
        self.combat_handler = CombatHandler(self.db, self.config, self.config_manager)
        self.realm_handler = RealmHandler(self.db, self.config, self.config_manager)

        access_control_config = self.config.get("ACCESS_CONTROL", {})
        self.whitelist_groups = [str(g) for g in access_control_config.get("WHITELIST_GROUPS", [])]
        
        logger.info("【修仙插件】XiuXianPlugin __init__ 方法成功执行完毕。")

    def _check_access(self, event: AstrMessageEvent) -> bool:
        if not self.whitelist_groups:
            return True
        
        group_id = event.get_group_id()
        if not group_id:
            return False
            
        if str(group_id) in self.whitelist_groups:
            return True
        
        return False

    async def initialize(self):
        await self.db.connect()
        migration_manager = MigrationManager(self.db.conn, self.config_manager)
        await migration_manager.migrate()
        logger.info("修 仙 插 件 已 加 载 。 ")

    async def terminate(self):
        await self.db.close()
        logger.info("修 仙 插 件 已 卸 载 。 ")

    
    @filter.command(CMD_HELP, "显 示 帮 助 信 息 ")
    async def handle_help(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.misc_handler.handle_help(event): yield r
        
    @filter.command(CMD_START_XIUXIAN, "开 始 你 的 修 仙 之 路 ")
    async def handle_start_xiuxian(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.player_handler.handle_start_xiuxian(event): yield r
        
    @filter.command(CMD_PLAYER_INFO, "查 看 你 的 角 色 信 息 ")
    async def handle_player_info(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.player_handler.handle_player_info(event): yield r
        
    @filter.command(CMD_CHECK_IN, "每 日 签 到 领 取 奖 励 ")
    async def handle_check_in(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.player_handler.handle_check_in(event): yield r
        
    @filter.command(CMD_START_CULTIVATION, "开 始 闭 关 修 炼 ")
    async def handle_start_cultivation(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.player_handler.handle_start_cultivation(event): yield r
        
    @filter.command(CMD_END_CULTIVATION, "结 束 闭 关 修 炼 ")
    async def handle_end_cultivation(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.player_handler.handle_end_cultivation(event): yield r
        
    @filter.command(CMD_BREAKTHROUGH, "尝 试 突 破 当 前 境 界 ")
    async def handle_breakthrough(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.player_handler.handle_breakthrough(event): yield r
        
    @filter.command(CMD_REROLL_SPIRIT_ROOT, "花 费 灵 石 ， 重 置 灵 根 ")
    async def handle_reroll_spirit_root(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.player_handler.handle_reroll_spirit_root(event): yield r
        
    @filter.command(CMD_SHOP, "查 看 坊 市 商 品 ")
    async def handle_shop(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.shop_handler.handle_shop(event): yield r
        
    @filter.command(CMD_BACKPACK, "查 看 你 的 背 包 ")
    async def handle_backpack(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.shop_handler.handle_backpack(event): yield r
        
    @filter.command(CMD_BUY, "购 买 物 品 ")
    async def handle_buy(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        if not self._check_access(event): return
        async for r in self.shop_handler.handle_buy(event, item_name, quantity): yield r
        
    @filter.command(CMD_USE_ITEM, "使 用 背 包 中 的 物 品 ")
    async def handle_use(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        if not self._check_access(event): return
        async for r in self.shop_handler.handle_use(event, item_name, quantity): yield r
        
    @filter.command(CMD_CREATE_SECT, "创 建 你 的 宗 门 ")
    async def handle_create_sect(self, event: AstrMessageEvent, sect_name: str):
        if not self._check_access(event): return
        async for r in self.sect_handler.handle_create_sect(event, sect_name): yield r
        
    @filter.command(CMD_JOIN_SECT, "加 入 一 个 宗 门 ")
    async def handle_join_sect(self, event: AstrMessageEvent, sect_name: str):
        if not self._check_access(event): return
        async for r in self.sect_handler.handle_join_sect(event, sect_name): yield r
        
    @filter.command(CMD_LEAVE_SECT, "退 出 当 前 宗 门 ")
    async def handle_leave_sect(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.sect_handler.handle_leave_sect(event): yield r
        
    @filter.command(CMD_MY_SECT, "查 看 我 的 宗 门 信 息 ")
    async def handle_my_sect(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.sect_handler.handle_my_sect(event): yield r
        
    @filter.command(CMD_SPAR, "与 其 他 玩 家 切 磋 ")
    async def handle_spar(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.combat_handler.handle_spar(event): yield r
        
    @filter.command(CMD_BOSS_LIST, "查 看 当 前 所 有 世 界 Boss")
    async def handle_boss_list(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.combat_handler.handle_boss_list(event): yield r
        
    @filter.command(CMD_FIGHT_BOSS, "讨 伐 指 定 ID的 世 界 Boss")
    async def handle_fight_boss(self, event: AstrMessageEvent, boss_id: str):
        if not self._check_access(event): return
        async for r in self.combat_handler.handle_fight_boss(event, boss_id): yield r
        
    @filter.command(CMD_ENTER_REALM, "根 据 当 前 境 界 ， 探 索 一 个 随 机 秘 境 ")
    async def handle_enter_realm(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.realm_handler.handle_enter_realm(event): yield r
        
    @filter.command(CMD_REALM_ADVANCE, "在 秘 境 中 前 进 ")
    async def handle_realm_advance(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.realm_handler.handle_realm_advance(event): yield r
        
    @filter.command(CMD_LEAVE_REALM, "离 开 当 前 秘 境 ")
    async def handle_leave_realm(self, event: AstrMessageEvent):
        if not self._check_access(event): return
        async for r in self.realm_handler.handle_leave_realm(event): yield r
