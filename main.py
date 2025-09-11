# main.py

import aiosqlite
from typing import Dict, Any, Callable, Awaitable
from astrbot.api import logger
from astrbot.api.star import Context, Star
from astrbot.api.event import AstrMessageEvent

from . import combat_manager, realm_manager, data_manager
from .config_manager import config
from .handlers import (
    PlayerHandler, ShopHandler, SectHandler,
    CombatHandler, RealmHandler, MiscHandler
)

class XiuXianPlugin(Star):
    # 类型定义
    HandlerMethod = Callable[[Any, AstrMessageEvent], Awaitable[None]]
    
    def __init__(self, context: Context):
        super().__init__(context)
        # 1. 实例化核心管理器
        self.battle_manager = combat_manager.BattleManager()
        self.realm_manager = realm_manager.RealmManager()

        # 2. 依赖注入：创建所有Handler的实例
        self.handlers: Dict[str, Any] = {
            "player": PlayerHandler(),
            "shop": ShopHandler(),
            "sect": SectHandler(),
            "combat": CombatHandler(self.battle_manager),
            "realm": RealmHandler(self.realm_manager),
            "misc": MiscHandler(),
        }

        # AstrBot V11的指令发现机制已足够完善，不再需要手动注册和分发
        # 直接在Handler的方法上使用 @filter.command 即可

    async def initialize(self):
        """插件初始化，加载配置并连接数据库"""
        try:
            config.load()
            await data_manager.init_db_pool()
            logger.info("修仙插件：数据库连接池初始化成功。")
            
            # 自动挂载所有handlers中的指令方法
            self._mount_handlers()

            logger.info("修仙插件已加载。")
        except aiosqlite.Error as e:
            logger.error(f"修仙插件：数据库操作失败。错误：{e}", exc_info=True)
        except FileNotFoundError as e:
            logger.error(f"修仙插件：缺少必要的配置文件。错误：{e}", exc_info=True)
        except Exception as e:
            logger.critical(f"修仙插件：初始化失败。错误：{e}", exc_info=True)

    def _mount_handlers(self):
        """
        遍历所有handler实例，将其公开的指令方法挂载到主插件类上。
        这是为了兼容 AstrBot V11 的指令发现机制，同时保持 Handler 类的独立性。
        """
        for handler_instance in self.handlers.values():
            for attr_name in dir(handler_instance):
                if attr_name.startswith("handle_"):
                    method = getattr(handler_instance, attr_name)
                    if callable(method) and hasattr(method, "filters"):
                        # 直接将方法挂载到 self 上，AstrBot会自动发现
                        setattr(self, attr_name, method)

    async def terminate(self):
        """插件卸载/停用时调用，关闭数据库连接池"""
        await data_manager.close_db_pool()
        logger.info("修仙插件已卸载。")