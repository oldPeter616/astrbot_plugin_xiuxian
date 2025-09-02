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

class XiuXianPlugin(Star):
    # 继承关系简化，不再需要继承所有Handler
    def __init__(self, context: Context):
        super().__init__(context)
        # 1. 实例化管理器
        self.battle_manager = combat_manager.BattleManager()
        self.realm_manager = realm_manager.RealmManager()

        # 2. 依赖注入：创建Handler实例并传入依赖
        self.player_handler = PlayerHandler()
        self.shop_handler = ShopHandler()
        self.sect_handler = SectHandler()
        self.combat_handler = CombatHandler(self.battle_manager)
        self.realm_handler = RealmHandler(self.realm_manager)
        self.misc_handler = MiscHandler()

    async def initialize(self):
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
        await data_manager.close_db_pool()
        logger.info("修仙插件已卸载。")

    # 3. 将所有handler的方法绑定到主类上
    # 这是astrtbot框架的要求，通过这种方式注册指令
    handle_start_xiuxian = PlayerHandler.handle_start_xiuxian
    handle_player_info = PlayerHandler.handle_player_info
    handle_check_in = PlayerHandler.handle_check_in
    handle_start_cultivation = PlayerHandler.handle_start_cultivation
    handle_end_cultivation = PlayerHandler.handle_end_cultivation
    handle_breakthrough = PlayerHandler.handle_breakthrough
    
    handle_shop = ShopHandler.handle_shop
    handle_backpack = ShopHandler.handle_backpack
    handle_buy = ShopHandler.handle_buy
    handle_use = ShopHandler.handle_use
    
    handle_create_sect = SectHandler.handle_create_sect
    handle_join_sect = SectHandler.handle_join_sect
    handle_leave_sect = SectHandler.handle_leave_sect
    handle_my_sect = SectHandler.handle_my_sect
    
    handle_spar = CombatHandler.handle_spar
    handle_start_boss_fight = CombatHandler.handle_start_boss_fight
    handle_join_fight = CombatHandler.handle_join_fight
    handle_attack_boss = CombatHandler.handle_attack_boss
    handle_fight_status = CombatHandler.handle_fight_status
    
    handle_realm_list = RealmHandler.handle_realm_list
    handle_enter_realm = RealmHandler.handle_enter_realm
    handle_realm_advance = RealmHandler.handle_realm_advance
    handle_leave_realm = RealmHandler.handle_leave_realm
    
    handle_help = MiscHandler.handle_help