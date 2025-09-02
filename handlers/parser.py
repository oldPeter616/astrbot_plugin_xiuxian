# handlers/parser.py
# 新增：通用指令参数解析器

from functools import wraps
from typing import Callable, Any, List, Optional
from astrbot.api.event import AstrMessageEvent

def parse_args(*types: Callable[[str], Any], sep: str = ' ', optional: int = 0):
    """
    一个装饰器，用于解析指令字符串的参数，并进行类型转换。

    Args:
        *types: 一系列用于转换参数的类型或函数 (例如 str, int, float)。
        sep (str): 参数之间的分隔符，默认为空格。
        optional (int): 最后几个参数是可选的。
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
            parts = event.message_str.strip().split(sep, 1)
            arg_str = parts[1] if len(parts) > 1 else ""
            raw_args: List[str] = [arg.strip() for arg in arg_str.split(sep) if arg.strip()]
            
            min_expected_args = len(types) - optional
            if len(raw_args) < min_expected_args:
                yield event.plain_result(f"指令格式错误，至少需要 {min_expected_args} 个参数，但只提供了 {len(raw_args)} 个。")
                return

            parsed_args: List[Any] = []
            
            for i, type_func in enumerate(types):
                if i < len(raw_args):
                    try:
                        parsed_args.append(type_func(raw_args[i]))
                    except (ValueError, TypeError):
                        yield event.plain_result(f"参数「{raw_args[i]}」格式错误，应为 {type_func.__name__} 类型。")
                        return
                else:
                    # 补充None给未提供的可选参数
                    parsed_args.append(None)
            
            # 将解析后的参数作为新的 *args 传递
            async for result in func(self, event, *parsed_args, *args, **kwargs):
                yield result

        return wrapper
    return decorator