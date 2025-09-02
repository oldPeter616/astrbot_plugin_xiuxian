# handlers/parser.py
# 通用指令参数解析器

from functools import wraps
from typing import Callable, Any, Tuple
from astrbot.api.event import AstrMessageEvent

def parse_args(*types: Callable[[str], Any], sep: str = ' '):
    """
    一个装饰器，用于解析指令字符串的参数，并进行类型转换。

    Args:
        *types: 一系列用于转换参数的类型或函数 (例如 str, int, float)。
        sep (str): 参数之间的分隔符，默为空格。
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
            # 移除指令本身
            parts = event.message_str.strip().split(sep, 1)
            if len(parts) > 1:
                arg_str = parts[1]
            else:
                arg_str = ""
            
            raw_args = [arg.strip() for arg in arg_str.split(sep) if arg.strip()]
            
            parsed_args = []
            error_msg = None

            # 预期参数数量
            expected_arg_count = len(types)

            for i, type_func in enumerate(types):
                if i < len(raw_args):
                    try:
                        # 尝试转换类型
                        parsed_args.append(type_func(raw_args[i]))
                    except (ValueError, TypeError):
                        error_msg = f"参数「{raw_args[i]}」格式错误，应为 {type_func.__name__} 类型。"
                        break
                else:
                    # 如果参数是可选的 (通过默认值判断)，则不报错
                    # 注意：此简单解析器不支持函数默认值检查，需要handler自行处理可选参数
                    pass
            
            if error_msg:
                yield event.plain_result(error_msg)
                return

            # 将解析后的参数传递给原函数
            # 注意：这里我们假设解析出的参数直接追加到 *args 后面
            # 更好的方式可能是将它们放入 kwargs
            # 为简单起见，我们直接传递
            new_args = tuple(parsed_args)
            
            async for result in func(self, event, *new_args, *args, **kwargs):
                yield result

        return wrapper
    return decorator