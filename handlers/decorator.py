from functools import wraps
from astrbot.api.event import AstrMessageEvent
from .. import data_manager
from ..config_manager import config
from ..models import Player

def player_required(func):
    """
    装饰器：检查玩家是否存在，并将Player实例作为关键字参数 'player' 传递给被装饰的函数。
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