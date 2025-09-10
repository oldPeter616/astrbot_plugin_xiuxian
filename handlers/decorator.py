# handlers/decorator.py

from functools import wraps
from astrbot.api.event import AstrMessageEvent
from .. import data_manager
from ..config_manager import config
from ..models import Player

def player_required(func):
    """
    装饰器：检查玩家是否存在，并将Player实例作为关键字参数 'player' 注入。

    功能:
        1. 从事件中获取用户ID，并查询数据库以获取对应的玩家对象。
        2. 如果玩家不存在，则中断执行，并向用户发送引导创建角色的消息。
        3. 如果玩家存在，则通过关键字参数 `player` 将玩家对象传递给被装饰的函数。

    对被装饰函数的要求:
        - 函数签名中必须包含一个名为 `player` 的参数，以接收注入的 `Player` 对象。
        - 推荐的签名格式: `async def your_handler(self, event: AstrMessageEvent, *, player: Player, **kwargs):`
          (使用 `*` 来强制 `player` 成为关键字参数，增加代码可读性)
    """
    @wraps(func)
    async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
        user_id = event.get_sender_id()
        player = await data_manager.get_player_by_id(user_id)

        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return

        # 将 player 作为关键字参数传递
        kwargs['player'] = player

        async for result in func(self, event, *args, **kwargs):
            yield result

    return wrapper