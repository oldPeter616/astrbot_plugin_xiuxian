from astrbot.api import logger
from astrbot.api.star import Context, Star, register

from . import data_manager, combat_manager, realm_manager
from .config_manager import config
from .handlers import (
    PlayerHandler, ShopHandler, SectHandler, 
    CombatHandler, RealmHandler, MiscHandler
)

@register(
    name="xiuxian", 
    author="oldPeter616", 
    desc="一个文字修仙插件", 
    version="1.2.0-refactored"
)
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
        config.load()
        try:
            await data_manager.init_db_pool()
            logger.info("修仙插件：数据库连接池初始化成功。")
        except Exception as e:
            logger.error(f"修仙插件：数据库初始化失败，错误：{e}")
        logger.info("修仙插件已加载，所有指令已通过装饰器自动注册。")

    async def terminate(self):
        """插件卸载/停用时调用，关闭数据库连接池"""
        await data_manager.close_db_pool()
        logger.info("修仙插件已卸载。")