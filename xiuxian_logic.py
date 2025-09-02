# xiuxian_logic.py
# 核心游戏逻辑模块

import random
import asyncio
from typing import Tuple, Dict, Any, Optional

from .config_manager import config
from .models import Player, PlayerEffect
from . import data_manager
from . import combat_manager

def _calculate_base_stats(level_index: int) -> Dict[str, int]:
    """根据境界等级计算基础战斗属性"""
    base_hp = 100 + level_index * 50
    base_attack = 10 + level_index * 8
    base_defense = 5 + level_index * 4
    return {"hp": base_hp, "max_hp": base_hp, "attack": base_attack, "defense": base_defense}

def generate_new_player_stats(user_id: str) -> Player:
    """为新玩家生成初始属性"""
    root = random.choice(config.POSSIBLE_SPIRITUAL_ROOTS)
    initial_stats = _calculate_base_stats(0)
    return Player(
        user_id=user_id,
        spiritual_root=f"{root}灵根",
        gold=config.INITIAL_GOLD,
        **initial_stats
    )

def handle_check_in(player: Player) -> Tuple[bool, str, Player]:
    """处理签到逻辑"""
    now = asyncio.get_running_loop().time()
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
    player.state_start_time = asyncio.get_running_loop().time()
    
    msg = "道友已进入冥想状态，开始闭关修炼。使用「出关」可查看修炼成果。"
    return True, msg, player

def handle_end_cultivation(player: Player) -> Tuple[bool, str, Player]:
    """处理出关逻辑"""
    if player.state != "修炼中":
        return False, "道友尚未开始闭关，何谈出关？", player
    
    now = asyncio.get_running_loop().time()
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
    current_level_info = config.level_map.get(player.level)
    
    if current_level_info is None:
        return False, "发生未知错误：无法找到道友当前的境界信息。", player

    current_level_index = current_level_info['index']
    
    if current_level_index >= len(config.level_data) - 1:
        return False, "道友已臻化境，达到当前世界的顶峰，无法再进行突破！", player
        
    next_level_info = config.level_data[current_level_index + 1]
    exp_needed = next_level_info['exp_needed']
    success_rate = next_level_info['success_rate']

    if player.experience < exp_needed:
        msg = (f"突破失败！\n目标境界：{next_level_info['level_name']}\n"
               f"所需修为：{exp_needed} (当前拥有 {player.experience})")
        return False, msg, player
    
    if random.random() < success_rate:
        player.level = next_level_info['level_name']
        player.experience = 0 # 突破后修为清零
        
        new_stats = _calculate_base_stats(current_level_index + 1)
        player.hp = new_stats['hp']
        player.max_hp = new_stats['max_hp']
        player.attack = new_stats['attack']
        player.defense = new_stats['defense']
        
        msg = (f"恭喜道友！天降祥瑞，突破成功！\n"
               f"当前境界已达：【{player.level}】\n"
               f"生命值提升至 {player.max_hp}，攻击提升至 {player.attack}，防御提升至 {player.defense}！")
    else:
        punishment = int(exp_needed * config.BREAKTHROUGH_FAIL_PUNISHMENT_RATIO)
        player.experience -= punishment
        msg = (f"可惜！道友在突破过程中气息不稳，导致失败。\n"
               f"境界稳固在【{player.level}】，但修为空耗 {punishment} 点。")
        
    return True, msg, player
    
def calculate_item_effect(item_id: str, quantity: int) -> Tuple[Optional[PlayerEffect], str]:
    """计算物品效果，返回效果对象和描述文本"""
    item_info = config.item_data.get(item_id)
    if not item_info or not (effect_config := item_info.get("effect")):
        return None, f"【{item_info.get('name', '未知物品')}】似乎只是凡物，无法使用。"

    effect = PlayerEffect()
    messages = []

    effect_type = effect_config.get("type")
    value = effect_config.get("value", 0) * quantity
    
    if effect_type == "add_experience":
        effect.experience = value
        messages.append(f"修为增加了 {value} 点")
    elif effect_type == "add_gold":
        effect.gold = value
        messages.append(f"灵石增加了 {value} 点")
    elif effect_type == "add_hp":
        effect.hp = value
        messages.append(f"恢复了 {value} 点生命")
    else:
         return None, f"你研究了半天，也没能参透【{item_info['name']}】的用法。"

    full_message = f"你使用了 {quantity} 个【{item_info['name']}】，" + "，".join(messages) + "！"
    return effect, full_message

async def handle_create_sect(player: Player, sect_name: str) -> Tuple[bool, str, Optional[Player]]:
    """处理创建宗门逻辑"""
    if player.sect_id is not None:
        return False, f"道友已是「{player.sect_name}」的成员，无法另立门户。", None
    
    if await data_manager.get_sect_by_name(sect_name):
        return False, f"「{sect_name}」之名已响彻修仙界，请道友另择佳名。", None

    cost = config.CREATE_SECT_COST
    if player.gold < cost:
        return False, f"开宗立派非同小可，需消耗 {cost} 灵石，道友的家底还不够。", None

    player.gold -= cost
    sect_id = await data_manager.create_sect(sect_name, player.user_id)
    player.sect_id = sect_id
    player.sect_name = sect_name
    
    msg = f"恭喜道友！「{sect_name}」今日正式成立，广纳门徒，共图大道！"
    return True, msg, player

async def handle_join_sect(player: Player, sect_name: str) -> Tuple[bool, str, Optional[Player]]:
    """处理加入宗门逻辑"""
    if player.sect_id is not None:
        return False, f"道友已是「{player.sect_name}」的成员，不可三心二意。", None
        
    sect = await data_manager.get_sect_by_name(sect_name)
    if not sect:
        return False, f"寻遍天下，也未曾听闻「{sect_name}」之名，请道友核实。", None
        
    player.sect_id = sect['id']
    player.sect_name = sect['name']
    
    msg = f"道友已成功拜入「{sect_name}」，从此同门齐心，共觅仙缘！"
    return True, msg, player

async def handle_leave_sect(player: Player) -> Tuple[bool, str, Optional[Player]]:
    """处理退出宗门逻辑"""
    if player.sect_id is None:
        return False, "道友本是逍遥散人，何谈退出宗门？", None
    
    sect = await data_manager.get_sect_by_id(player.sect_id)
    if sect and sect['leader_id'] == player.user_id:
        # 宗门不可无主，需要先传位或解散
        members = await data_manager.get_sect_members(player.sect_id)
        if len(members) > 1:
            return False, "道友身为一宗之主，身系宗门兴衰，不可轻易脱离！请先传位于他人或解散宗门。", None
        else:
            # 如果宗门只剩自己，则直接解散
            await data_manager.delete_sect(player.sect_id)

    sect_name = player.sect_name
    player.sect_id = None
    player.sect_name = None
    
    msg = f"道不同不相为谋。道友已脱离「{sect_name}」，从此山高水长，江湖再见。"
    return True, msg, player

def handle_pvp(attacker: Player, defender: Player) -> str:
    """处理PVP逻辑，并返回战报"""
    # 直接调用同步函数，不再需要await
    _, _, combat_log = combat_manager.player_vs_player(attacker, defender)
    report = "\n".join(combat_log)
    return report