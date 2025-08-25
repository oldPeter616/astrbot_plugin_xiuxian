# xiuxian_logic.py
# 核心游戏逻辑模块

import random
import time
from typing import Tuple, Dict, Any, Optional

from .config_manager import config
from .models import Player
from . import data_manager

# ... (Previous functions remain unchanged)
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
    """处理突破逻辑"""
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
    
    if random.random() < success_rate:
        player.level = next_level_info['level_name']
        player.experience -= exp_needed
        msg = (
            f"恭喜道友！天降祥瑞，突破成功！\n"
            f"当前境界已达：【{player.level}】\n"
            f"消耗修为 {exp_needed} 点，剩余 {player.experience} 点。"
        )
    else:
        punishment = int(exp_needed * config.BREAKTHROUGH_FAIL_PUNISHMENT_RATIO)
        player.experience -= punishment
        msg = (
            f"可惜！道友在突破过程中气息不稳，导致失败。\n"
            f"境界稳固在【{player.level}】，但修为空耗 {punishment} 点。\n"
            f"请重整旗鼓，再次尝试！"
        )
        
    return True, msg, player

def handle_buy_item(player: Player, item_name: str, quantity: int) -> Tuple[bool, str, Optional[Player], Optional[str]]:
    """处理购买物品逻辑"""
    target_item_id = None
    target_item_info = None
    for item_id, info in config.item_data.items():
        if info['name'] == item_name:
            target_item_id = item_id
            target_item_info = info
            break
            
    if not target_item_info:
        return False, f"道友，小店中并无「{item_name}」这件商品。", None, None

    total_cost = target_item_info['price'] * quantity
    if player.gold < total_cost:
        return False, f"道友的灵石不足！购买 {quantity} 个「{item_name}」需要 {total_cost} 灵石，而你只有 {player.gold}。 ", None, None

    player.gold -= total_cost
    msg = f"购买成功！道友花费 {total_cost} 灵石，购得「{item_name}」x{quantity}。"
    
    return True, msg, player, target_item_id

# --- 新增的宗门逻辑函数 ---
def handle_create_sect(player: Player, sect_name: str) -> Tuple[bool, str, Optional[Player]]:
    """处理创建宗门逻辑"""
    if player.sect_id is not None:
        return False, f"道友已是「{player.sect_name}」的成员，无法另立门户。", None
    
    if data_manager.get_sect_by_name(sect_name):
        return False, f"「{sect_name}」之名已响彻修仙界，请道友另择佳名。", None

    cost = config.CREATE_SECT_COST
    if player.gold < cost:
        return False, f"开宗立派非同小可，需消耗 {cost} 灵石，道友的家底还不够。", None

    player.gold -= cost
    sect_id = data_manager.create_sect(sect_name, player.user_id)
    player.sect_id = sect_id
    player.sect_name = sect_name
    
    msg = f"恭喜道友！「{sect_name}」今日正式成立，广纳门徒，共图大道！"
    return True, msg, player

def handle_join_sect(player: Player, sect_name: str) -> Tuple[bool, str, Optional[Player]]:
    """处理加入宗门逻辑"""
    if player.sect_id is not None:
        return False, f"道友已是「{player.sect_name}」的成员，不可三心二意。", None
        
    sect = data_manager.get_sect_by_name(sect_name)
    if not sect:
        return False, f"寻遍天下，也未曾听闻「{sect_name}」之名，请道友核实。", None
        
    player.sect_id = sect['id']
    player.sect_name = sect['name']
    
    msg = f"道友已成功拜入「{sect_name}」，从此同门齐心，共觅仙缘！"
    return True, msg, player

def handle_leave_sect(player: Player) -> Tuple[bool, str, Optional[Player]]:
    """处理退出宗门逻辑"""
    if player.sect_id is None:
        return False, "道友本是逍遥散人，何谈退出宗门？", None
    
    sect = data_manager.get_sect_by_id(player.sect_id)
    if sect and sect['leader_id'] == player.user_id:
        return False, "道友身为一宗之主，身系宗门兴衰，不可轻易脱离！请先传位于他人。", None
        
    sect_name = player.sect_name
    player.sect_id = None
    player.sect_name = None
    
    msg = f"道不同不相为谋。道友已脱离「{sect_name}」，从此山高水长，江湖再见。"
    return True, msg, player