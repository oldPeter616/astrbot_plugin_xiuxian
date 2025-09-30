# handlers/utils.py
# 通用工具函数和装饰器

from functools import wraps
from typing import Callable, Coroutine, AsyncGenerator

from astrbot.api.event import AstrMessageEvent
from ..models import Player

CMD_END_CULTIVATION = "出关"
CMD_LEAVE_REALM = "离开秘境"
CMD_CHECK_IN = "签到"
CMD_PLAYER_INFO = "我的信息"
CMD_MY_EQUIPMENT = "我的装备" 
CMD_BACKPACK = "我的背包"

# 其他指令
CMD_START_XIUXIAN = "我要修仙"


def player_required(func: Callable[..., Coroutine[any, any, AsyncGenerator[any, None]]]):
    """
    一个装饰器，用于需要玩家登录才能执行的指令。
    它会自动检查玩家是否存在、状态是否空闲（特定指令除外），否则将玩家对象作为参数注入。
    """
    @wraps(func)
    async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
        # self 是 Handler 类的实例 (e.g., PlayerHandler)
        player = await self.db.get_player_by_id(event.get_sender_id())
        
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{CMD_START_XIUXIAN}」开启你的旅程。")
            return

        # 状态检查
        if player.state != "空闲":
            # 允许特定指令在非空闲时执行
            allowed_commands = [
                CMD_END_CULTIVATION, 
                CMD_LEAVE_REALM,
                CMD_CHECK_IN,
                CMD_PLAYER_INFO,
                CMD_MY_EQUIPMENT,
                CMD_BACKPACK
            ]
            message_text = event.get_message_str().strip()
            
            is_allowed = False
            for cmd in allowed_commands:
                if message_text.startswith(cmd):
                    is_allowed = True
                    break
            
            if not is_allowed:
                yield event.plain_result(f"道友当前正在「{player.state}」中，无法分心他顾。")
                return

        # 将 player 对象作为第一个参数传递给原始函数
        async for result in func(self, player, event, *args, **kwargs):
            yield result
            
    return wrapper