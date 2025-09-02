# main.py

import aiosqlite
from astrbot.api import logger
from astrbot.api.star import Context, Star

from . import combat_manager, realm_manager, data_manager
from .config_manager import config
from .handlers import (
    PlayerHandler, ShopHandler, SectHandler,
    CombatHandler, RealmHandler, MiscHandler
)

class XiuXianPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 1. 实例化核心管理器
        self.battle_manager = combat_manager.BattleManager()
        self.realm_manager = realm_manager.RealmManager()

        # 2. 依赖注入：创建所有Handler的实例，并将依赖项（管理器）通过构造函数传入
        self.handlers = {
            "player": PlayerHandler(),
            "shop": ShopHandler(),
            "sect": SectHandler(),
            "combat": CombatHandler(self.battle_manager),
            "realm": RealmHandler(self.realm_manager),
            "misc": MiscHandler(),
        }

        # 3. 动态挂载方法以兼容AstrBot框架的指令发现机制
        # 这种方式保持了Handler类的独立性，同时满足了框架的要求。
        self._register_handlers()

    def _register_handlers(self):
        """
        遍历所有handler实例，将其公开的指令方法挂载到主插件类上。
        方法名必须以 "handle_" 开头。
        """
        for handler_instance in self.handlers.values():
            for attr_name in dir(handler_instance):
                if attr_name.startswith("handle_"):
                    method = getattr(handler_instance, attr_name)
                    if callable(method) and hasattr(method, "__is_command__"):
                        setattr(self, attr_name, method)

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

# 为了让 `filter.command` 能在方法定义时就工作
def command_handler(original_func):
    """一个简单的装饰器，用于标记一个方法是指令处理器。"""
    setattr(original_func, "__is_command__", True)
    return original_func

# 更新 filter.command 的行为，让它能配合我们的新模式
original_command = filter.command
def new_command(*args, **kwargs):
    def decorator(func):
        # 先应用原始的 command 装饰器
        decorated_func = original_command(*args, **kwargs)(func)
        # 再应用我们的标记
        return command_handler(decorated_func)
    return decorator

# 全局替换
filter.command = new_command