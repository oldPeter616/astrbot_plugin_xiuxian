# handlers/utils.py
# 通用工具函数和装饰器

from functools import wraps
from typing import Callable, Coroutine, AsyncGenerator

from astrbot.api.event import AstrMessageEvent
from ..models import Player

CMD_START_XIUXIAN = "我要修仙"

def player_required(func: Callable[..., Coroutine[any, any, AsyncGenerator[any, None]]]):
    """
    一个装饰器，用于需要玩家登录才能执行的指令。
    它会自动检查玩家是否存在，如果不存在则发送提示，否则将玩家对象作为参数注入。
    """
    @wraps(func)
    async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
        # self 是 Handler 类的实例 (e.g., PlayerHandler)
        player = await self.db.get_player_by_id(event.get_sender_id())
        
        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{CMD_START_XIUXIAN}」开启你的旅程。")
            return

        # 将 player 对象作为第一个参数传递给原始函数
        async for result in func(self, player, event, *args, **kwargs):
            yield result
            
    return wrapper

def require_idle_state(func: Callable[..., Coroutine[any, any, AsyncGenerator[any, None]]]):
    """
    一个装饰器，用于限制玩家必须在“空闲”状态下才能执行的指令。
    它必须用在 @player_required 之后。
    """
    @wraps(func)
    async def wrapper(self, player: Player, event: AstrMessageEvent, *args, **kwargs):
        if player.state != "空闲":
            yield event.plain_result(f"道友当前正在「{player.state}」中，无法分心他顾。")
            return
        
        # 玩家状态正确，继续执行原指令
        async for result in func(self, player, event, *args, **kwargs):
            yield result

    return wrapper
