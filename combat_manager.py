# combat_manager.py
# 核心战斗逻辑模块

import asyncio
import random
import time
from typing import Dict, List, Optional, Tuple

from astrbot.api import logger
from .models import Player, Boss, ActiveWorldBoss
from . import data_manager
from .config_manager import config
from .generators import MonsterGenerator

class BattleManager:
    """管理全局的世界Boss刷新与战斗"""

    async def ensure_bosses_are_spawned(self) -> List[Tuple[ActiveWorldBoss, Boss]]:
        """
        检查所有Boss模板，如果冷却完毕且当前未激活，则生成新的Boss实例。
        返回当前所有活跃的 (Boss实例, Boss模板) 列表。
        """
        active_boss_instances = await data_manager.get_active_bosses()
        active_boss_map = {b.boss_id: b for b in active_boss_instances}
        
        all_boss_templates = config.boss_data

        for boss_id, template in all_boss_templates.items():
            if boss_id not in active_boss_map:
                # 这个Boss当前不活跃，检查是否需要刷新
                # 在一个更复杂的系统中，这里会检查冷却时间戳
                # 为简化，我们总是刷新不存在的Boss
                logger.info(f"世界Boss {template['name']} (ID: {boss_id}) 当前未激活，开始生成...")
                
                top_players = await data_manager.get_top_players(config.WORLD_BOSS_TOP_PLAYERS_AVG)
                avg_level_index = int(sum(p.level_index for p in top_players) / len(top_players)) if top_players else 1

                # 使用 MonsterGenerator 创建一个临时的、带属性的Boss对象，用于获取血量等信息
                boss_with_stats = MonsterGenerator.create_boss(boss_id, avg_level_index)
                if not boss_with_stats:
                    logger.error(f"无法为Boss ID {boss_id} 生成属性，请检查配置。")
                    continue

                new_boss_instance = ActiveWorldBoss(
                    boss_id=boss_id,
                    current_hp=boss_with_stats.max_hp,
                    max_hp=boss_with_stats.max_hp,
                    spawned_at=time.time(),
                    level_index=avg_level_index
                )
                await data_manager.create_active_boss(new_boss_instance)
                active_boss_map[boss_id] = new_boss_instance
        
        # 准备返回值
        result = []
        for boss_id, active_instance in active_boss_map.items():
            # 为每个活跃的Boss，都生成一个带属性的临时对象用于战斗和展示
            boss_template = MonsterGenerator.create_boss(boss_id, active_instance.level_index)
            if boss_template:
                result.append((active_instance, boss_template))
        return result

    async def player_fight_boss(self, player: Player, boss_id: str, player_name: str) -> str:
        """处理玩家对世界Boss的自动战斗流程"""
        active_boss_instance = next((b for b in await data_manager.get_active_bosses() if b.boss_id == boss_id), None)
        
        if not active_boss_instance or active_boss_instance.current_hp <= 0:
            return f"来晚了一步，ID为【{boss_id}】的Boss已被击败或已消失！"
            
        # 生成带属性的Boss对象用于战斗
        boss = MonsterGenerator.create_boss(boss_id, active_boss_instance.level_index)
        if not boss:
            return "错误：无法加载Boss战斗数据！"

        # --- 自动战斗循环 ---
        p_clone = player.clone()
        boss_hp = active_boss_instance.current_hp
        combat_log = [f"⚔️ 你向【{boss.name}】发起了悍不畏死的冲锋！"]
        total_damage_dealt = 0
        turn = 1
        max_turns = 50 # 设定最大回合数防止无限循环

        while p_clone.hp > 0 and boss_hp > 0 and turn <= max_turns:
            combat_log.append(f"\n--- 第 {turn} 回合 ---")
            
            # 玩家攻击
            damage_to_boss = max(1, p_clone.attack - boss.defense)
            boss_hp -= damage_to_boss
            total_damage_dealt += damage_to_boss
            combat_log.append(f"你对【{boss.name}】造成了 {damage_to_boss} 点伤害。")
            
            if boss_hp <= 0:
                combat_log.append(f"❤️【{boss.name}】剩余生命: 0/{active_boss_instance.max_hp}")
                break
            combat_log.append(f"❤️【{boss.name}】剩余生命: {boss_hp}/{active_boss_instance.max_hp}")

            # Boss攻击
            damage_to_player = max(1, boss.attack - p_clone.defense)
            p_clone.hp -= damage_to_player
            combat_log.append(f"【{boss.name}】对你造成了 {damage_to_player} 点伤害。")
            combat_log.append(f"❤️你剩余生命: {p_clone.hp}/{p_clone.max_hp}")

            turn += 1

        # --- 战斗结算 ---
        final_report = ["\n".join(combat_log)]

        # 更新Boss血量并记录伤害
        await data_manager.update_active_boss_hp(boss_id, boss_hp)
        if total_damage_dealt > 0:
            await data_manager.record_boss_damage(boss_id, player.user_id, player_name, total_damage_dealt)
            final_report.append(f"\n你本次共对Boss造成 {total_damage_dealt} 点伤害！")

        if p_clone.hp <= 0:
            final_report.append("你不敌妖兽，力竭倒下...但你的贡献已被记录！")
        
        if boss_hp <= 0:
            final_report.append(f"\n**惊天动地！【{boss.name}】在众位道友的合力之下倒下了！**")
            final_report.append(await self._end_battle(boss, active_boss_instance))

        return "\n".join(final_report)

    async def _end_battle(self, boss_template: Boss, boss_instance: ActiveWorldBoss) -> str:
        """结算奖励并清理Boss"""
        participants = await data_manager.get_boss_participants(boss_instance.boss_id)
        if not participants:
            await data_manager.clear_boss_data(boss_instance.boss_id)
            return "但似乎无人对此Boss造成伤害，奖励无人获得。"

        total_damage_dealt = sum(p['total_damage'] for p in participants) or 1
        
        # 准备奖励结算报告
        reward_report = ["\n--- 战利品结算 ---"]
        updated_players = []

        for p_data in participants:
            # 注意：这里我们只根据记录的user_id和user_name发奖，而不直接获取Player对象
            # 这是一个简化的异步模型，避免在循环中多次查询数据库
            damage_contribution = p_data['total_damage'] / total_damage_dealt
            
            gold_reward = int(boss_template.rewards['gold'] * damage_contribution)
            exp_reward = int(boss_template.rewards['experience'] * damage_contribution)
            
            # 找到对应的玩家并更新
            player = await data_manager.get_player_by_id(p_data['user_id'])
            if player:
                player.gold += gold_reward
                player.experience += exp_reward
                updated_players.append(player)
                reward_report.append(f"道友 {p_data['user_name']} 获得灵石 {gold_reward}，修为 {exp_reward}！")
        
        # 批量更新玩家数据
        if updated_players:
            await data_manager.update_players_in_transaction(updated_players)
        
        # 清理Boss数据
        await data_manager.clear_boss_data(boss_instance.boss_id)
        logger.info(f"世界Boss {boss_instance.boss_id} 已被击败，数据已清理。")
        
        return "\n".join(reward_report)

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