# xiuxian_logic.py
# 核心游戏逻辑模块

import random
import time
from typing import Tuple, Dict, Any

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
    """处理签到逻辑"""
    now = time.time()
    if now - player.last_check_in < 22 * 60 * 60:
        return False, "道友，今日已经签到过了，请明日再来。", player

    reward = random.randint(config.CHECK_IN_REWARD_MIN, config.CHECK_IN_REWARD_MAX)
    player.gold += reward
    player.last_check_in = now
    
    msg = f"签到成功！获得灵石 x{reward}。道友当前的家底为 {player.gold} 灵石。"
    return True, msg, player

def handle_start_cultivation(player: Player) -> Tuple[bool, str, Player]:
    """处理闭关逻辑"""
    if player.state != "空闲":
        return False, f"道友当前正在「{player.state}」中，无法分心闭关。", player
    
    player.state = "修炼中"
    player.state_start_time = time.time()
    
    msg = "道友已进入冥想状态，开始闭关修炼。使用「出关」可查看修炼成果。"
    return True, msg, player

def handle_end_cultivation(player: Player) -> Tuple[bool, str, Player]:
    """处理出关逻辑"""
    if player.state != "修炼中":
        return False, "道友尚未开始闭关，何谈出关？", player
    
    now = time.time()
    duration_minutes = (now - player.state_start_time) / 60
    
    if duration_minutes < 1:
        player.state = "空闲"
        player.state_start_time = 0.0
        msg = "道友本次闭关不足一分钟，未能有所精进。下次要更有耐心才是。"
        return True, msg, player

    exp_gained = int(duration_minutes * config.BASE_EXP_PER_MINUTE)
    player.experience += exp_gained
    player.state = "空闲"
    player.state_start_time = 0.0
    
    msg = (
        f"道友本次闭关共持续 {int(duration_minutes)} 分钟，\n"
        f"修为增加了 {exp_gained} 点！\n"
        f"当前总修为：{player.experience}"
    )
    return True, msg, player

def handle_breakthrough(player: Player) -> Tuple[bool, str, Player]:
    """
    处理突破逻辑
    """
    current_level_info = None
    current_level_index = -1
    for i, level in enumerate(config.level_data):
        if level['level_name'] == player.level:
            current_level_info = level
            current_level_index = i
            break
    
    if current_level_info is None:
        return False, "发生未知错误：无法找到道友当前的境界信息。", player

    if current_level_index == len(config.level_data) - 1:
        return False, "道友已臻化境，达到当前世界的顶峰，无法再进行突破！", player
        
    next_level_info = config.level_data[current_level_index + 1]
    exp_needed = next_level_info['exp_needed']
    success_rate = next_level_info['success_rate']

    if player.experience < exp_needed:
        msg = (
            f"突破失败！\n"
            f"目标境界：{next_level_info['level_name']}\n"
            f"所需修为：{exp_needed} (道友当前拥有 {player.experience})\n"
            f"修为不足，请继续潜心修炼。"
        )
        return False, msg, player
    
    # 进行突破判定
    if random.random() < success_rate:
        # 突破成功
        player.level = next_level_info['level_name']
        player.experience -= exp_needed
        msg = (
            f"恭喜道友！天降祥瑞，突破成功！\n"
            f"当前境界已达：【{player.level}】\n"
            f"消耗修为 {exp_needed} 点，剩余 {player.experience} 点。"
        )
    else:
        # 突破失败
        punishment = int(exp_needed * config.BREAKTHROUGH_FAIL_PUNISHMENT_RATIO)
        player.experience -= punishment
        msg = (
            f"可惜！道友在突破过程中气息不稳，导致失败。\n"
            f"境界稳固在【{player.level}】，但修为空耗 {punishment} 点。\n"
            f"请重整旗鼓，再次尝试！"
        )
        
    return True, msg, player