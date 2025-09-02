from functools import wraps
from astrbot.api.event import AstrMessageEvent
from .. import data_manager
from ..config_manager import config

def player_required(func):
    """
    装饰器：检查玩家是否存在，并将player和通过self注入的管理器附加到event上。
    被装饰的函数必须是一个异步生成器 (async def with yield)。
    """
    @wraps(func)
    async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
        user_id = event.get_sender_id()
        player = await data_manager.get_player_by_id(user_id)

        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        
        # 通过 self (Handler实例) 获取注入的管理器
        # 这是依赖注入模式的一部分，管理器在主插件类中被创建并传递给Handler的构造函数
        setattr(event, 'battle_manager', getattr(self, 'battle_manager', None))
        setattr(event, 'realm_manager', getattr(self, 'realm_manager', None))
        setattr(event, 'player', player)

        async for result in func(self, event, *args, **kwargs):
            yield result
            
    return wrapper