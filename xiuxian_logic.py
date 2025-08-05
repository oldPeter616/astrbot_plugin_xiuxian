# xiuxian_logic.py
# 核心游戏逻辑模块

import random
import time
from typing import Tuple

# 修改点：从 config_manager 导入配置实例
from .config_manager import config
from .models import Player

POSSIBLE_SPIRITUAL_ROOTS = ["金", "木", "水", "火", "土", "天", "异"]

def generate_new_player_stats(user_id: str) -> Player:
    """为新玩家生成初始属性"""
    root = random.choice(POSSIBLE_SPIRITUAL_ROOTS)
    return Player(
        user_id=user_id,
        spiritual_root=f"{root}灵根",
        gold=config.INITIAL_GOLD
    )

def handle_check_in(player: Player) -> Tuple[bool, str, Player]:
    """
    处理签到逻辑
    :return: (是否成功, 提示消息, 更新后的Player对象)
    """
    now = time.time()
    # 检查距离上次签到是否超过22小时（给予一些容错）
    if now - player.last_check_in < 22 * 60 * 60:
        return False, "道友，今日已经签到过了，请明日再来。", player

    reward = random.randint(config.CHECK_IN_REWARD_MIN, config.CHECK_IN_REWARD_MAX)
    player.gold += reward
    player.last_check_in = now
    
    msg = f"签到成功！获得灵石 x{reward}。道友当前的家底为 {player.gold} 灵石。"
    return True, msg, player