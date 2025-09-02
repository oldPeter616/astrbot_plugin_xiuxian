from functools import wraps
from astrbot.api.event import AstrMessageEvent
from .. import data_manager
from ..config_manager import config
from ..main import shared_context

def managers_required(func):
    """
    装饰器：从共享上下文中获取管理器实例并注入到event对象中。
    """
    @wraps(func)
    async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
        # 从共享上下文中获取管理器并注入 event
        setattr(event, 'battle_manager', shared_context.get('battle_manager'))
        setattr(event, 'realm_manager', shared_context.get('realm_manager'))
        
        # 检查是否注入成功
        if not event.battle_manager or not event.realm_manager:
            yield event.plain_result("错误：插件核心管理器未初始化，请联系管理员。")
            return

        async for result in func(self, event, *args, **kwargs):
            yield result
            
    return wrapper

def player_required(func):
    """
    装饰器：检查玩家是否存在，并将player和管理器对象附加到event上。
    
    被此装饰器包裹的函数必须是一个异步生成器 (async def with yield)，
    否则会在运行时抛出 TypeError。
    """
    @wraps(func)
    async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
        user_id = event.get_sender_id()
        player = await data_manager.get_player_by_id(user_id)

        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        
        # 从共享上下文中获取管理器并注入 event
        setattr(event, 'battle_manager', shared_context.get('battle_manager'))
        setattr(event, 'realm_manager', shared_context.get('realm_manager'))

        # 检查是否注入成功
        if not event.battle_manager or not event.realm_manager:
            yield event.plain_result("错误：插件核心管理器未初始化，请联系管理员。")
            return

        # 将 player 附加到 event 对象上
        setattr(event, 'player', player)

        async for result in func(self, event, *args, **kwargs):
            yield result
            
    return wrapper