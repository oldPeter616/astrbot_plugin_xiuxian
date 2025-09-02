# main.py

import aiosqlite
from typing import Dict, Any, List, Tuple, Callable, Awaitable
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

        # 3. 显式指令注册表
        self.command_map: Dict[str, XiuXianPlugin.HandlerMethod] = {}
        self._register_handlers()

    def _register_handlers(self):
        """
        遍历所有handler实例，将其标记为指令的方法注册到 command_map 中。
        这种方法比动态 setattr 更清晰，易于追踪。
        """
        logger.info("开始注册修仙插件指令...")
        for handler_name, handler_instance in self.handlers.items():
            for attr_name in dir(handler_instance):
                if attr_name.startswith("handle_"):
                    method = getattr(handler_instance, attr_name)
                    # 检查方法是否被 astrbot 的 filter.command 装饰器标记
                    if callable(method) and hasattr(method, "filters"):
                        # 从filter中获取指令名
                        for f in method.filters:
                            # 这是一个简化的获取方式，实际可能需要更复杂的解析，出bug再修
                            # 假设第一个 filter 是 command filter
                            if hasattr(f, "cmds"):
                                for cmd in f.cmds:
                                    if cmd in self.command_map:
                                        logger.warning(f"指令 '{cmd}' 重复注册，将被覆盖。")
                                    self.command_map[cmd] = method
                                    setattr(self, attr_name, method) # 兼容旧版 astrbot 发现机制
                                    logger.info(f"指令 '{cmd}' 已注册到方法 {handler_name}.{attr_name}")

    async def initialize(self):
        """插件初始化，加载配置并连接数据库"""
        try:
            config.load()
            await data_manager.init_db_pool()
            logger.info("修仙插件：数据库连接池初始化成功。")
            logger.info("修仙插件已加载。")
        except aiosqlite.Error as e:
            logger.error(f"修仙插件：数据库操作失败。错误：{e}", exc_info=True)
        except FileNotFoundError as e:
            logger.error(f"修仙插件：缺少必要的配置文件。错误：{e}", exc_info=True)
        except Exception as e:
            logger.critical(f"修仙插件：初始化失败。错误：{e}", exc_info=True)

    async def terminate(self):
        """插件卸载/停用时调用，关闭数据库连接池"""
        await data_manager.close_db_pool()
        logger.info("修仙插件已卸载。")