# combat_manager.py
# 核心战斗逻辑模块 (已重构)

import asyncio
import random
from copy import deepcopy
from typing import Dict, List, Optional, Tuple
from .models import Player, Boss, Monster
from . import data_manager
from .config_manager import config

class BattleSession:
    """封装一场世界Boss战斗的所有状态"""
    def __init__(self, boss: Boss):
        self.boss = boss
        self.participants: Dict[str, Player] = {}
        self.total_damage: Dict[str, int] = {}
        self.start_time = asyncio.get_running_loop().time()
        self.lock = asyncio.Lock()
        self.log: List[str] = [f"远古妖兽【{boss.name}】出现在了修仙界！"]
        self.player_attack_count = 0

class BattleManager:
    """管理全局的世界Boss战斗会话"""
    def __init__(self):
        self.current_battle: Optional[BattleSession] = None
        self.boss_cooldowns: Dict[str, float] = {}

    def is_boss_on_cooldown(self, boss_id: str) -> Tuple[bool, float]:
        """检查Boss是否在冷却中"""
        loop = asyncio.get_running_loop()
        current_time = loop.time()
        cooldown_end_time = self.boss_cooldowns.get(boss_id)
        if cooldown_end_time and current_time < cooldown_end_time:
            return True, cooldown_end_time - current_time
        return False, 0

    async def start_battle(self, boss_config: dict) -> Tuple[bool, str]:
        """开启一场新的Boss战"""
        if self.current_battle:
            return False, f"当前已有【{self.current_battle.boss.name}】正在被讨伐中！"

        boss_id = boss_config['id']
        is_cd, remaining_time = self.is_boss_on_cooldown(boss_id)
        if is_cd:
            return False, f"【{boss_config['name']}】元气大伤，正在调息，请在 {int(remaining_time // 60)} 分钟后再来。"

        boss = Boss(
            id=boss_id,
            name=boss_config['name'],
            hp=boss_config['hp'],
            max_hp=boss_config['hp'],
            attack=boss_config['attack'],
            defense=boss_config['defense'],
            cooldown_minutes=boss_config['cooldown_minutes'],
            rewards=boss_config['rewards']
        )
        self.current_battle = BattleSession(boss)
        return True, self.current_battle.log[0]

    async def add_participant(self, player: Player) -> Tuple[bool, str]:
        """玩家加入世界Boss战斗"""
        if not self.current_battle:
            return False, "当前没有正在进行的战斗。"
        async with self.current_battle.lock:
            if player.user_id in self.current_battle.participants:
                return False, "你已经在战场中了！"
            if player.hp <= 1:
                return False, "你已重伤，无法加入战斗！"
            
            self.current_battle.participants[player.user_id] = player
            self.current_battle.log.append(f"【{player.user_id[-4:]}】加入了战场！")
            return True, f"你已成功加入对【{self.current_battle.boss.name}】的讨伐！"

    async def player_attack(self, player: Player) -> Tuple[bool, str, bool, List[Player]]:
        """处理玩家攻击世界Boss, 返回 (是否成功, 消息, 战斗是否结束, 需更新的玩家)"""
        if not self.current_battle:
            return False, "当前没有战斗。", False, []
            
        async with self.current_battle.lock:
            if player.user_id not in self.current_battle.participants:
                return False, "你尚未加入战斗，无法攻击！", False, []

            p = self.current_battle.participants[player.user_id]
            if p.hp <= 0:
                return False, "你已经倒下了，无法行动！", False, []

            damage = max(1, p.attack - self.current_battle.boss.defense)
            self.current_battle.boss.hp -= damage
            log_msg = f"【{p.user_id[-4:]}】奋力一击，对Boss造成了 {damage} 点伤害！"
            self.current_battle.log.append(log_msg)
            
            self.current_battle.total_damage[p.user_id] = self.current_battle.total_damage.get(p.user_id, 0) + damage
            
            if self.current_battle.boss.hp <= 0:
                battle_over, final_msg, updated_players = await self._end_battle(victory=True)
                return True, final_msg, battle_over, updated_players

            self.current_battle.player_attack_count += 1
            changed_players = []
            if self.current_battle.player_attack_count % 3 == 0:
                self.current_battle.log.append(f"【{self.current_battle.boss.name}】被激怒了，发动了猛烈的反击！")
                changed_player = await self._boss_attack()
                if changed_player:
                    changed_players.append(changed_player)
            
            return True, log_msg, False, changed_players

    async def _boss_attack(self) -> Optional[Player]:
        """Boss攻击参战玩家, 返回被攻击的玩家对象"""
        if not self.current_battle: return None
        
        targets = [p for p in self.current_battle.participants.values() if p.hp > 0]
        if not targets: return None
        
        target_player = random.choice(targets)
        damage = max(1, self.current_battle.boss.attack - target_player.defense)
        target_player.hp -= damage
        
        log_msg = f"Boss对【{target_player.user_id[-4:]}】造成了 {damage} 点伤害。"
        if target_player.hp <= 0:
            target_player.hp = 0
            log_msg += f"【{target_player.user_id[-4:]}】重伤倒地！"
        self.current_battle.log.append(log_msg)
        return target_player

    async def _end_battle(self, victory: bool) -> Tuple[bool, str, List[Player]]:
        """结束世界Boss战斗并结算"""
        if not self.current_battle: return False, "", []

        final_log = ""
        updated_players = []
        
        if victory:
            boss = self.current_battle.boss
            final_log = f"恭喜各位道友！成功讨伐【{boss.name}】！\n---战利品分配---"
            
            total_damage_dealt = sum(self.current_battle.total_damage.values())
            if total_damage_dealt == 0: total_damage_dealt = 1

            for user_id, player in self.current_battle.participants.items():
                damage_contribution = self.current_battle.total_damage.get(user_id, 0) / total_damage_dealt
                
                gold_reward = int(boss.rewards['gold'] * damage_contribution)
                exp_reward = int(boss.rewards['experience'] * damage_contribution)
                
                player.gold += gold_reward
                player.experience += exp_reward
                reward_log = f"\n【{user_id[-4:]}】(贡献度 {damage_contribution:.1%}):"
                reward_log += f" 灵石+{gold_reward}, 修为+{exp_reward}"
                
                for item_id, drop_rate in boss.rewards['items'].items():
                    if random.random() < drop_rate:
                        await data_manager.add_item_to_inventory(user_id, item_id, 1)
                        item_name = config.item_data.get(item_id, {}).get("name", "未知物品")
                        reward_log += f", 获得了【{item_name}】!"
                
                final_log += reward_log
                updated_players.append(player)

            loop = asyncio.get_running_loop()
            self.boss_cooldowns[boss.id] = loop.time() + boss.cooldown_minutes * 60
        else:
            final_log = f"很遗憾，讨伐【{self.current_battle.boss.name}】失败了。"
            updated_players = list(self.current_battle.participants.values())
            
        self.current_battle = None
        return True, final_log, updated_players

    def get_status(self) -> str:
        """获取当前世界Boss战斗状态"""
        if not self.current_battle:
            return "当前风平浪静，没有世界Boss出现。"
        
        boss = self.current_battle.boss
        status = f"--- 【{boss.name}】讨伐战况 ---\n"
        status += f"❤️Boss剩余生命: {boss.hp}/{boss.max_hp}\n\n"
        status += "参战道友:\n"
        
        sorted_participants = sorted(
            self.current_battle.participants.values(),
            key=lambda p: self.current_battle.total_damage.get(p.user_id, 0),
            reverse=True
        )
        
        for player in sorted_participants:
            damage = self.current_battle.total_damage.get(player.user_id, 0)
            status += f" - 【{player.user_id[-4:]}】 ❤️{player.hp}/{player.max_hp} | ⚔️输出: {damage}\n"
        return status

async def player_vs_player(attacker: Player, defender: Player) -> Tuple[Optional[Player], Optional[Player], List[str]]:
    """处理玩家切磋的逻辑 (使用副本)"""
    p1 = deepcopy(attacker)
    p2 = deepcopy(defender)
    
    combat_log = [f"⚔️【切磋开始】{p1.user_id[-4:]} vs {p2.user_id[-4:]}！"]
    turn = 1
    max_turns = 30
    
    while p1.hp > 0 and p2.hp > 0 and turn <= max_turns:
        combat_log.append(f"\n--- 第 {turn} 回合 ---")
        damage_to_p2 = max(1, p1.attack - p2.defense)
        p2.hp -= damage_to_p2
        combat_log.append(f"{p1.user_id[-4:]} 对 {p2.user_id[-4:]} 造成了 {damage_to_p2} 点伤害。")
        combat_log.append(f"❤️{p2.user_id[-4:]} 剩余生命: {p2.hp}/{p2.max_hp}")
        
        if p2.hp <= 0:
            combat_log.append(f"\n🏆【切磋结束】{p1.user_id[-4:]} 获胜！")
            return attacker, defender, combat_log

        await asyncio.sleep(0)

        damage_to_p1 = max(1, p2.attack - p1.defense)
        p1.hp -= damage_to_p1
        combat_log.append(f"{p2.user_id[-4:]} 对 {p1.user_id[-4:]} 造成了 {damage_to_p1} 点伤害。")
        combat_log.append(f"❤️{p1.user_id[-4:]} 剩余生命: {p1.hp}/{p1.max_hp}")

        if p1.hp <= 0:
            combat_log.append(f"\n🏆【切磋结束】{p2.user_id[-4:]} 获胜！")
            return defender, attacker, combat_log
            
        turn += 1
        await asyncio.sleep(0)

    if turn > max_turns:
        combat_log.append("\n【平局】双方大战三十回合，未分胜负！")
    
    return None, None, combat_log

async def player_vs_monster(player: Player, monster: Monster) -> Tuple[bool, List[str], Player]:
    """
    处理玩家 vs 普通怪物的战斗。
    返回: (是否胜利, 战斗日志, 战斗后的玩家状态副本)
    """
    log = [f"你遭遇了【{monster.name}】！"]
    p = deepcopy(player) # 使用玩家对象的副本进行战斗
    monster_hp = monster.hp

    while p.hp > 0 and monster_hp > 0:
        damage_to_monster = max(1, p.attack - monster.defense)
        monster_hp -= damage_to_monster
        log.append(f"你对【{monster.name}】造成了 {damage_to_monster} 点伤害。")

        if monster_hp <= 0:
            log.append(f"你成功击败了【{monster.name}】！")
            return True, log, p

        await asyncio.sleep(0)

        damage_to_player = max(1, monster.attack - p.defense)
        p.hp -= damage_to_player
        log.append(f"【{monster.name}】对你造成了 {damage_to_player} 点伤害。")

    if p.hp <= 0:
        log.append("你不敌对手，重伤倒地...")
        p.hp = 1 # 战斗失败后保留1点生命
        return False, log, p
    
    # 理论上不会到达这里，但在循环外返回以防万一
    return False, log, p