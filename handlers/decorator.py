from functools import wraps
from astrbot.api.event import AstrMessageEvent
from .. import data_manager
from ..config_manager import config

def player_required(func):
    """装饰器：检查玩家是否存在，并将player对象附加到event上。"""
    @wraps(func)
    async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
        user_id = event.get_sender_id()
        player = await data_manager.get_player_by_id(user_id)

        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        
        # 将 manager 和 player 附加到 event 对象上，方便 handler 内部调用
        setattr(event, 'player', player)
        setattr(event, 'battle_manager', getattr(self, 'battle_manager', None))
        setattr(event, 'realm_manager', getattr(self, 'realm_manager', None))

        async for result in func(self, event, *args, **kwargs):
            yield result
            
    return wrapper