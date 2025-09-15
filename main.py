# main.py

import aiosqlite
from astrbot.api import logger
from astrbot.api.star import Context, Star
from astrbot.api.event import AstrMessageEvent, filter

# --- 核心依赖 ---
from . import data_manager, xiuxian_logic, combat_manager, realm_manager
from .config_manager import config

# --- 导入所有 Handler Mixins ---
from .handlers.misc_handler import MiscHandlerMixin
from .handlers.player_handler import PlayerHandlerMixin
from .handlers.shop_handler import ShopHandlerMixin
from .handlers.sect_handler import SectHandlerMixin
from .handlers.combat_handler import CombatHandlerMixin
from .handlers.realm_handler import RealmHandlerMixin

# --- 通过多重继承，将所有指令处理函数“混入”到主插件类中 ---
class XiuXianPlugin(
    Star,
    MiscHandlerMixin,
    PlayerHandlerMixin,
    ShopHandlerMixin,
    SectHandlerMixin,
    CombatHandlerMixin,
    RealmHandlerMixin
):
    
    def __init__(self, context: Context):
        super().__init__(context)
        # 实例化所有核心管理器，它们将被所有Mixin方法通过 self.xxx 共享
        self.battle_manager = combat_manager.BattleManager()
        self.realm_manager = realm_manager.RealmManager()

    async def initialize(self):
        """插件初始化"""
        try:
            # config 已在导入时自动加载
            await data_manager.init_db_pool()
            logger.info("修仙插件：数据库连接池初始化成功。")
            logger.info("修仙插件已加载，架构已更新为优雅的 Mixin 模式。")
        except Exception as e:
            logger.critical(f"修仙插件：初始化失败。错误：{e}", exc_info=True)

    async def terminate(self):
        """插件卸载/停用时调用"""
        await data_manager.close_db_pool()
        logger.info("修仙插件已卸载。")