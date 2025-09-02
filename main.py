# main.py

import aiosqlite
from astrbot.api import logger
from astrbot.api.star import Context, Star

from . import data_manager, combat_manager, realm_manager
from .config_manager import config
from .handlers import (
    PlayerHandler, ShopHandler, SectHandler,
    CombatHandler, RealmHandler, MiscHandler
)

# 移除 @register
class XiuXianPlugin(Star,
                   PlayerHandler,
                   ShopHandler,
                   SectHandler,
                   CombatHandler,
                   RealmHandler,
                   MiscHandler):

    def __init__(self, context: Context):
        super().__init__(context)
        # 实例化有状态的管理器
        self.battle_manager = combat_manager.BattleManager()
        self.realm_manager = realm_manager.RealmManager()

    async def initialize(self):
        """插件初始化，加载配置并连接数据库"""
        try:
            config.load()
            await data_manager.init_db_pool()
            logger.info("修仙插件：数据库连接池初始化成功。")
            logger.info("修仙插件已加载，所有指令已通过装饰器自动注册。")
        except aiosqlite.Error as e:
            logger.error(f"修仙插件：数据库操作失败，请检查数据库文件权限或完整性。错误：{e}")
        except FileNotFoundError as e:
            logger.error(f"修仙插件：缺少必要的配置文件，请检查插件目录结构。错误：{e}")
        except Exception as e:
            logger.critical(f"修仙插件：发生未知严重错误导致初始化失败。错误：{e}", exc_info=True)


    async def terminate(self):
        """插件卸载/停用时调用，关闭数据库连接池"""
        await data_manager.close_db_pool()
        logger.info("修仙插件已卸载。")