# core/cultivation_manager.py
import random
import time 
from typing import Tuple, Dict

from astrbot.api import AstrBotConfig, logger
from ..config_manager import ConfigManager
from ..models import Player

class CultivationManager:
    def __init__(self, config: AstrBotConfig, config_manager: ConfigManager):
        self.config = config
        self.config_manager = config_manager
        
        # 灵根名称到配置项键的映射
        self.root_to_config_key = {
            "金": "WUXING_ROOT_SPEED",
            "木": "WUXING_ROOT_SPEED",
            "水": "WUXING_ROOT_SPEED",
            "火": "WUXING_ROOT_SPEED",
            "土": "WUXING_ROOT_SPEED",
            "异": "VARIANT_ROOT_SPEED",
            "天": "HEAVENLY_ROOT_SPEED",
            "融合": "FUSION_ROOT_SPEED",
            "混沌": "CHAOS_ROOT_SPEED"
        }

    def _calculate_base_stats(self, level_index: int) -> Dict[str, any]:
        # 更新这里，加入新属性的基础值计算
        base_hp = 100 + level_index * 50
        base_mp = 50 + level_index * 20 # 灵力成长
        base_attack = 10 + level_index * 8
        base_defense = 5 + level_index * 4
        base_speed = 5 + level_index * 1  # 速度成长
        return {
            "hp": base_hp, "max_hp": base_hp,
            "mp": base_mp, "max_mp": base_mp,
            "attack": base_attack, "defense": base_defense,
            "speed": base_speed
        }

    def _get_random_spiritual_root(self) -> str:
        # 从配置的灵根类型中随机选择一个
        possible_roots = list(self.root_to_config_key.keys())
        return random.choice(possible_roots)

    def generate_new_player_stats(self, user_id: str, name: str) -> Player:
        root = self._get_random_spiritual_root()
        initial_stats = self._calculate_base_stats(0)
            
        # 返回一个带有所有新属性初始值的 Player 对象
        return Player(
            user_id=user_id,
            name=name,
            spiritual_root=f"{root}灵根",
            gold=self.config["VALUES"]["INITIAL_GOLD"],
            # 新增天赋属性的随机初始值，让开局更多样化
            aptitude=random.randint(5, 15),
            insight=random.randint(5, 15),
            luck=random.randint(1, 10),
            divine_sense=random.randint(15, 25),
            **initial_stats
        )

    def handle_check_in(self, player: Player) -> Tuple[bool, str, Player]:
        now = time.time()
        if now - player.last_check_in < 22 * 60 * 60:
            return False, "道友，今日已经签到过了，请明日再来。", player

        reward = random.randint(self.config["VALUES"]["CHECK_IN_REWARD_MIN"], self.config["VALUES"]["CHECK_IN_REWARD_MAX"])
        p_clone = player.clone()
        p_clone.gold += reward
        p_clone.last_check_in = now

        msg = f"签到成功！获得灵石 x{reward}。道友当前的家底为 {p_clone.gold} 灵石。"
        return True, msg, p_clone

    def handle_start_cultivation(self, player: Player) -> Tuple[bool, str, Player]:
        if player.state != "空闲":
            return False, f"道友当前正在「{player.state}」中，无法分心闭关。", player

        p_clone = player.clone()
        p_clone.state = "修炼中"
        p_clone.state_start_time = time.time()

        msg = "道友已进入冥想状态，开始闭关修炼。使用「出关」可查看修炼成果。"
        return True, msg, p_clone

    def handle_end_cultivation(self, player: Player) -> Tuple[bool, str, Player]:
        if player.state != "修炼中":
            return False, "道友尚未开始闭关，何谈出关？", player

        now = time.time()
        duration_minutes = (now - player.state_start_time) / 60

        p_clone = player.clone()
        p_clone.state = "空闲"
        p_clone.state_start_time = 0.0

        if duration_minutes < 1:
            msg = "道友本次闭关不足一分钟，未能有所精进。下次要更有耐心才是。"
            return True, msg, p_clone

        player_root_name = p_clone.spiritual_root.replace("灵根", "")
        config_key = self.root_to_config_key.get(player_root_name, "WUXING_ROOT_SPEED")
        speed_multiplier = self.config["SPIRIT_ROOT_SPEEDS"].get(config_key, 1.0)
        
        base_exp_per_min = self.config["VALUES"]["BASE_EXP_PER_MINUTE"]
        exp_gained = int(duration_minutes * base_exp_per_min * speed_multiplier)
        p_clone.experience += exp_gained

        # 计算回血
        hp_recovery_ratio = self.config["VALUES"].get("CULTIVATION_HP_RECOVERY_RATIO", 0.0)
        hp_recovered = int(exp_gained * hp_recovery_ratio)
        hp_before = p_clone.hp
        p_clone.hp = min(p_clone.max_hp, p_clone.hp + hp_recovered)
        hp_actually_recovered = p_clone.hp - hp_before

        speed_info = f"（灵根加成: {speed_multiplier:.2f}倍）"
        msg_parts = [
            f"道友本次闭关共持续 {int(duration_minutes)} 分钟,",
            f"修为增加了 {exp_gained} 点！{speed_info}",
        ]
        if hp_actually_recovered > 0:
            msg_parts.append(f"闭关吐纳间，气血恢复了 {hp_actually_recovered} 点。")
        
        msg_parts.append(f"当前总修为：{p_clone.experience}")
        if p_clone.level_index < len(self.config_manager.level_data) - 1:
            next_level_info = self.config_manager.level_data[p_clone.level_index + 1]
            exp_needed = next_level_info['exp_needed']
            if p_clone.experience >= exp_needed:
                msg_parts.append("\n检测到道友修为已然圆满，可使用「突破」指令尝试冲击下一境界！")
        
        msg = "\n".join(msg_parts)
        return True, msg, p_clone

    def handle_breakthrough(self, player: Player) -> Tuple[bool, str, Player]:
        current_level_index = player.level_index
        p_clone = player.clone()

        if current_level_index >= len(self.config_manager.level_data) - 1:
            return False, "道友已臻化境，达到当前世界的顶峰，无法再进行突破！", p_clone

        next_level_info = self.config_manager.level_data[current_level_index + 1]
        exp_needed = next_level_info['exp_needed']
        success_rate = next_level_info['success_rate']

        if p_clone.experience < exp_needed:
            msg = (f"突破失败！\n目标境界：{next_level_info['level_name']}\n"
                   f"所需修为：{exp_needed} (当前拥有 {p_clone.experience})")
            return False, msg, p_clone

        if random.random() < success_rate:
            p_clone.level_index = current_level_index + 1
            p_clone.experience -= exp_needed

            new_stats = self._calculate_base_stats(p_clone.level_index)
            p_clone.hp = new_stats['hp']
            p_clone.max_hp = new_stats['max_hp']
            p_clone.mp = new_stats['mp']
            p_clone.max_mp = new_stats['max_mp']
            p_clone.attack = new_stats['attack']
            p_clone.defense = new_stats['defense']
            p_clone.speed = new_stats['speed']


            msg = (f"恭喜道友！天降祥瑞，突破成功！\n"
                   f"当前境界已达：【{p_clone.get_level(self.config_manager)}】\n"
                   f"生命提升至{p_clone.max_hp}，灵力提升至{p_clone.max_mp}，攻防速全面增长！\n" # 更新提示信息
                   f"剩余修为: {p_clone.experience}")
        else:
            punishment = int(exp_needed * self.config["VALUES"]["BREAKTHROUGH_FAIL_PUNISHMENT_RATIO"])
            p_clone.experience -= punishment
            msg = (f"可惜！道友在突破过程中气息不稳，导致失败。\n"
                   f"境界稳固在【{p_clone.get_level(self.config_manager)}】，但修为空耗 {punishment} 点。\n"
                   f"剩余修为: {p_clone.experience}")

        return True, msg, p_clone
    
    def handle_reroll_spirit_root(self, player: Player) -> Tuple[bool, str, Player]:
        cost = self.config["VALUES"].get("REROLL_SPIRIT_ROOT_COST", 10000)
        
        if player.gold < cost:
            return False, f"重入仙途乃逆天之举，需消耗 {cost} 灵石，道友的家底还不够。", player

        p_clone = player.clone()
        p_clone.gold -= cost
        
        old_root = p_clone.spiritual_root
        new_root_name = self._get_random_spiritual_root()
        p_clone.spiritual_root = f"{new_root_name}灵根"

        msg = (f"道友耗费 {cost} 灵石逆天改命，原有的「{old_root}」已化为全新的「{p_clone.spiritual_root}」！\n"
               f"祝道友仙途坦荡，大道可期！")
        return True, msg, p_clone
