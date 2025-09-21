# handlers/misc_handler.py
from astrbot.api.event import AstrMessageEvent
from ..config_manager import config
from ..data import DataBase

__all__ = ["MiscHandler"]

class MiscHandler:
    def __init__(self, db: DataBase):
        self.db = db

    async def handle_help(self, event: AstrMessageEvent):
        help_text = (
            "--- 寻仙指令手册 ---\n"
            f"【{config.CMD_START_XIUXIAN}】: 开启修仙之旅。\n"
            f"【{config.CMD_PLAYER_INFO}】: 查看人物信息。\n"
            f"【{config.CMD_CHECK_IN}】: 每日签到。\n"
            "--- 修炼与成长 ---\n"
            f"【{config.CMD_START_CULTIVATION}】: 开始闭关。\n"
            f"【{config.CMD_END_CULTIVATION}】: 结束闭关。\n"
            f"【{config.CMD_BREAKTHROUGH}】: 尝试突破境界。\n"
            "--- 坊市与物品 ---\n"
            f"【{config.CMD_SHOP}】: 查看坊市商品。\n"
            f"【{config.CMD_BACKPACK}】: 查看个人背包。\n"
            f"【{config.CMD_BUY} <名> [数]】: 购买物品。\n"
            f"【{config.CMD_USE_ITEM} <名> [数]】: 使用物品。\n"
            "--- 宗门社交 ---\n"
            f"【{config.CMD_CREATE_SECT} <名>】: 创建宗门。\n"
            f"【{config.CMD_JOIN_SECT} <名>】: 加入宗门。\n"
            f"【{config.CMD_MY_SECT}】: 查看宗门信息。\n"
            f"【{config.CMD_LEAVE_SECT}】: 退出宗门。\n"
            "--- PVE/PVP ---\n"
            f"【{config.CMD_SPAR} @某人】: 与玩家切磋。\n"
            f"【{config.CMD_BOSS_LIST}】: 查看当前世界Boss。\n"
            f"【{config.CMD_FIGHT_BOSS} <ID>】: 讨伐指定ID的Boss。\n"
            f"【{config.CMD_ENTER_REALM}】: 进入秘境。\n"
            f"【{config.CMD_REALM_ADVANCE}】: 在秘境中前进。\n"
            f"【{config.CMD_LEAVE_REALM}】: 离开秘境。\n"
            "--------------------"
        )
        yield event.plain_result(help_text)