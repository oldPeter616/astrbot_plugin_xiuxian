# handlers/misc_handler.py
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase

CMD_START_XIUXIAN="我要修仙"
CMD_PLAYER_INFO="我的信息"
CMD_CHECK_IN="签到"
CMD_START_CULTIVATION="闭关"
CMD_END_CULTIVATION="出关"
CMD_BREAKTHROUGH="突破"
CMD_REROLL_SPIRIT_ROOT="重入仙途"
CMD_SHOP="商店"
CMD_BACKPACK="我的背包"
CMD_BUY="购买"
CMD_USE_ITEM="使用"
CMD_CREATE_SECT="创建宗门"
CMD_JOIN_SECT="加入宗门"
CMD_MY_SECT="我的宗门"
CMD_LEAVE_SECT="退出宗门"
CMD_SPAR="切磋"
CMD_BOSS_LIST="查看世界boss"
CMD_FIGHT_BOSS="讨伐boss"
CMD_ENTER_REALM="探索秘境"
CMD_REALM_ADVANCE="前进"
CMD_LEAVE_REALM="离开秘境"

__all__ = ["MiscHandler"]

class MiscHandler:
    # 杂项指令处理器
    
    def __init__(self, db: DataBase):
        self.db = db

    async def handle_help(self, event: AstrMessageEvent):
        help_text = (
            "--- 寻仙指令手册 ---\n"
            f"【{CMD_START_XIUXIAN}】: 开启修仙之旅。\n"
            f"【{CMD_PLAYER_INFO}】: 查看人物信息。\n"
            f"【{CMD_CHECK_IN}】: 每日签到。\n"
            "--- 修炼与成长 ---\n"
            f"【{CMD_START_CULTIVATION}】: 开始闭关。\n"
            f"【{CMD_END_CULTIVATION}】: 结束闭关。\n"
            f"【{CMD_BREAKTHROUGH}】: 尝试突破境界。\n"
            f"【{CMD_REROLL_SPIRIT_ROOT}】: 逆天改命，重置灵根。\n"
            "--- 坊市与物品 ---\n"
            f"【{CMD_SHOP}】: 查看坊市商品。\n"
            f"【{CMD_BACKPACK}】: 查看个人背包。\n"
            f"【{CMD_BUY} <名> [数]】: 购买物品。\n"
            f"【{CMD_USE_ITEM} <名> [数]】: 使用物品。\n"
            "--- 宗门社交 ---\n"
            f"【{CMD_CREATE_SECT} <名>】: 创建宗门。\n"
            f"【{CMD_JOIN_SECT} <名>】: 加入宗门。\n"
            f"【{CMD_MY_SECT}】: 查看宗门信息。\n"
            f"【{CMD_LEAVE_SECT}】: 退出宗门。\n"
            "--- PVE/PVP ---\n"
            f"【{CMD_SPAR} @某人】: 与玩家切磋。\n"
            f"【{CMD_BOSS_LIST}】: 查看当前世界Boss。\n"
            f"【{CMD_FIGHT_BOSS} <ID>】: 讨伐指定ID的Boss。\n"
            f"【{CMD_ENTER_REALM}】: 进入秘境。\n"
            f"【{CMD_REALM_ADVANCE}】: 在秘境中前进。\n"
            f"【{CMD_LEAVE_REALM}】: 离开秘境。\n"
            "--------------------"
        )
        yield event.plain_result(help_text)