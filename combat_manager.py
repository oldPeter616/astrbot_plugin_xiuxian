# combat_manager.py
# 核心战斗逻辑模块

import asyncio
import random
from typing import Dict, List, Optional, Tuple

from astrbot.api import logger
from .models import Player, Boss, AttackResult
from . import data_manager
from .config_manager import config
from .generators import MonsterGenerator

class BattleManager:
    """管理全局的、持久化的世界Boss"""
    def __init__(self):
        self._boss_attack_lock = asyncio.Lock() # 用于确保攻击的原子性

    async def ensure_boss_exists_and_get_status(self) -> Tuple[Optional[Boss], str]:
        """
        确保世界Boss存在于数据库中，如果不存在则创建。
        返回 (Boss对象, 状态消息)
        """
        boss_status = await data_manager.get_world_boss()

        if not boss_status:
            logger.info("当前无世界Boss，开始生成新的Boss...")
            # 1. 获取顶尖玩家
            top_players = await data_manager.get_top_players(config.WORLD_BOSS_TOP_PLAYERS_AVG)
            if not top_players:
                # 如果服务器没有玩家，则按等级1生成
                avg_level_index = 1
            else:
                avg_level_index = int(sum(p.level_index for p in top_players) / len(top_players))

            # 2. 生成Boss实例
            boss_template_id = config.WORLD_BOSS_TEMPLATE_ID
            boss = MonsterGenerator.create_boss(boss_template_id, avg_level_index)
            if not boss:
                return None, "错误：世界Boss模板配置不正确，生成失败！"

            # 3. 存入数据库并清理旧数据
            await data_manager.clear_world_boss_data()
            boss_status = await data_manager.create_world_boss(boss)
            logger.info(f"已生成新的世界Boss: {boss.name} (HP: {boss.max_hp})")
            
            msg = f"沉睡的远古妖兽【{boss.name}】苏醒了！它的力量深不可测！\n"
            msg += f"❤️生命: {boss_status.current_hp}/{boss_status.max_hp}"
            return boss, msg
        else:
            # Boss已存在，直接获取信息
            boss_template = config.boss_data.get(boss_status.boss_template_id)
            boss_name = boss_template.get("name", "远古妖兽") if boss_template else "远古妖兽"
            
            msg = f"--- 当前世界Boss：【{boss_name}】 ---\n"
            msg += f"❤️剩余生命: {boss_status.current_hp}/{boss_status.max_hp}\n\n"
            msg += "--- 伤害贡献榜 ---\n"
            
            participants = await data_manager.get_all_boss_participants()
            if not participants:
                msg += "暂无道友对其造成伤害。"
            else:
                for p_data in participants[:5]: # 只显示前5名
                    msg += f" - 玩家 {p_data['user_id'][-4:]}: {p_data['total_damage']} 点伤害\n"
            
            return MonsterGenerator.create_boss(boss_status.boss_template_id, 1), msg # 返回一个临时的boss实例用于获取名字等信息

    async def player_attack(self, player: Player) -> str:
        """处理玩家对世界Boss的攻击"""
        async with self._boss_attack_lock:
            boss_status = await data_manager.get_world_boss()
            if not boss_status or boss_status.current_hp <= 0:
                return "来晚了一步，世界Boss已被击败！"
            
            # 获取Boss的防御力
            boss_template = config.boss_data.get(boss_status.boss_template_id)
            if not boss_template: return "Boss数据异常！" # 安全检查
            
            # 为了获取防御力，需要模拟生成一个boss对象
            top_players = await data_manager.get_top_players(config.WORLD_BOSS_TOP_PLAYERS_AVG)
            avg_level_index = int(sum(p.level_index for p in top_players) / len(top_players)) if top_players else 1
            boss_instance = MonsterGenerator.create_boss(boss_status.boss_template_id, avg_level_index)


            damage = max(1, player.attack - boss_instance.defense)
            
            success, new_hp = await data_manager.transactional_attack_world_boss(player, damage)
            
            if not success:
                return "攻击失败，Boss可能已被其他道友击败！"

            msg = f"你对Boss造成了 {damage} 点伤害！Boss剩余血量: {new_hp}/{boss_status.max_hp}"

            if new_hp <= 0:
                msg += "\n\n**惊天动地！在众位道友的合力之下，世界Boss倒下了！**\n--- 战利品结算 ---"
                await self._end_battle(boss_instance)

            return msg

    async def _end_battle(self, boss: Boss):
        """结算奖励并清理Boss"""
        participants = await data_manager.get_all_boss_participants()
        if not participants:
            await data_manager.clear_world_boss_data()
            return

        total_damage_dealt = sum(p['total_damage'] for p in participants) or 1
        
        updated_players = []
        for p_data in participants:
            player = await data_manager.get_player_by_id(p_data['user_id'])
            if not player: continue

            damage_contribution = p_data['total_damage'] / total_damage_dealt
            
            gold_reward = int(boss.rewards['gold'] * damage_contribution)
            exp_reward = int(boss.rewards['experience'] * damage_contribution)

            player.gold += gold_reward
            player.experience += exp_reward
            updated_players.append(player)
            
            logger.info(f"玩家 {player.user_id} 获得Boss奖励: {gold_reward} 灵石, {exp_reward} 修为")
        
        # 批量更新玩家数据
        await data_manager.update_players_in_transaction(updated_players)
        
        # 清理Boss数据，等待下一次生成
        await data_manager.clear_world_boss_data()
        logger.info("世界Boss已被击败，数据已清理。")

def player_vs_player(attacker: Player, defender: Player) -> Tuple[Optional[Player], Optional[Player], List[str]]:
    p1 = attacker.clone()
    p2 = defender.clone()
    combat_log = [f"⚔️【切磋开始】{p1.user_id[-4:]} vs {p2.user_id[-4:]}！"]
    turn = 1
    max_turns = 30
    while p1.hp > 0 and p2.hp > 0 and turn <= max_turns:
        combat_log.append(f"\n--- 第 {turn} 回合 ---")
        damage_to_p2 = max(1, p1.attack - p2.defense)
        p2.hp -= damage_to_p2
        combat_log.append(f"{p1.user_id[-4:]} 对 {p2.user_id[-4:]} 造成了 {damage_to_p2} 点伤害。")
        if p2.hp <= 0:
            combat_log.append(f"❤️{p2.user_id[-4:]} 剩余生命: 0/{p2.max_hp}")
            combat_log.append(f"\n🏆【切磋结束】{p1.user_id[-4:]} 获胜！")
            return attacker, defender, combat_log
        combat_log.append(f"❤️{p2.user_id[-4:]} 剩余生命: {p2.hp}/{p2.max_hp}")
        damage_to_p1 = max(1, p2.attack - p1.defense)
        p1.hp -= damage_to_p1
        combat_log.append(f"{p2.user_id[-4:]} 对 {p1.user_id[-4:]} 造成了 {damage_to_p1} 点伤害。")
        if p1.hp <= 0:
            combat_log.append(f"❤️{p1.user_id[-4:]} 剩余生命: 0/{p1.max_hp}")
            combat_log.append(f"\n🏆【切磋结束】{p2.user_id[-4:]} 获胜！")
            return defender, attacker, combat_log
        combat_log.append(f"❤️{p1.user_id[-4:]} 剩余生命: {p1.hp}/{p1.max_hp}")
        turn += 1
    if turn > max_turns:
        combat_log.append("\n【平局】双方大战三十回合，未分胜负！")
    return None, None, combat_log

def player_vs_monster(player: Player, monster) -> Tuple[bool, List[str], Player]:
    log = [f"你遭遇了【{monster.name}】！"]
    p = player.clone()
    monster_hp = monster.hp
    while p.hp > 0 and monster_hp > 0:
        damage_to_monster = max(1, p.attack - monster.defense)
        monster_hp -= damage_to_monster
        log.append(f"你对【{monster.name}】造成了 {damage_to_monster} 点伤害。")
        if monster_hp <= 0:
            log.append(f"你成功击败了【{monster.name}】！")
            return True, log, p
        damage_to_player = max(1, monster.attack - p.defense)
        p.hp -= damage_to_player
        log.append(f"【{monster.name}】对你造成了 {damage_to_player} 点伤害。")
    if p.hp <= 0:
        log.append("你不敌对手，重伤倒地...")
        p.hp = 1
        return False, log, p
    return False, log, p