# realm_manager.py
# 秘境探索管理器 (已重构为无状态)

import random
from typing import Tuple, Dict
from copy import deepcopy

from .models import Player, Monster
from .config_manager import config
from . import combat_manager

class RealmManager:

    def start_session(self, player: Player, realm_id: str) -> Tuple[bool, str, Player]:
        """
        开始一次秘境探索，直接修改并返回玩家对象。
        返回: (是否成功, 消息, 更新后的玩家对象)
        """
        p = deepcopy(player)
        realm_config = config.realm_data.get(realm_id)
        if not realm_config:
            return False, "不存在的秘境。", p

        if p.realm_id is not None:
             current_realm_name = config.realm_data.get(p.realm_id, {}).get("name", "未知的秘境")
             return False, f"你已身在【{current_realm_name}】之中，无法分心他顾。", p

        cost = realm_config['entry_cost']['gold']
        if p.gold < cost:
            return False, f"进入此秘境需要 {cost} 灵石，你的灵石不足。", p
        
        player_level_idx = config.level_map.get(p.level, {}).get("index", -1)
        req_level_idx = config.level_map.get(realm_config['level_requirement'], {}).get("index", 999)
        if player_level_idx < req_level_idx:
            return False, f"你的境界（{p.level}）未达到进入【{realm_config['name']}】所需的（{realm_config['level_requirement']}）！", p
        
        p.gold -= cost
        p.realm_id = realm_id
        p.realm_floor = 0
        
        msg = (f"你消耗了 {cost} 灵石，进入了【{realm_config['name']}】。\n"
               f"此地共有 {realm_config['total_floors']} 层，充满了未知的危险与机遇。\n"
               f"使用「{config.CMD_REALM_ADVANCE}」指令向前探索。")
        return True, msg, p

    async def advance_session(self, player: Player) -> Tuple[bool, str, Player, Dict]:
        """
        处理前进逻辑。
        返回: (是否成功, 消息, 更新后的玩家对象, 获得的物品字典)
        """
        if not player.realm_id:
            return False, "你不在任何秘境中。", player, {}

        p = deepcopy(player)
        realm_config = config.realm_data[p.realm_id]
        total_floors = realm_config['total_floors']
        
        p.realm_floor += 1
        
        is_boss_floor = p.realm_floor == total_floors
        gained_items = {}
        
        if is_boss_floor:
            event_log = [f"--- 第 {p.realm_floor}/{total_floors} 层 (最终挑战) ---"]
            boss_id = realm_config['boss_id']
            monster_config = config.monster_data.get(boss_id)
            enemy = Monster(id=boss_id, **monster_config, max_hp=monster_config['hp'])
            
            victory, combat_log, p_after_combat = await combat_manager.player_vs_monster(p, enemy)
            event_log.extend(combat_log)

            if victory:
                rewards = self._get_rewards(enemy.rewards)
                p_after_combat.gold += rewards['gold']
                p_after_combat.experience += rewards['experience']
                gained_items = rewards['items']
                event_log.append(f"\n成功击败最终头目！你通关了【{realm_config['name']}】！")
                reward_text = []
                if rewards['gold'] > 0: reward_text.append(f"灵石+{rewards['gold']}")
                if rewards['experience'] > 0: reward_text.append(f"修为+{rewards['experience']}")
                if reward_text: event_log.append(f"获得奖励：" + ", ".join(reward_text))
            else:
                event_log.append(f"\n挑战失败！你被传送出了秘境。")
            
            p_after_combat.realm_id = None
            p_after_combat.realm_floor = 0
            return victory, "\n".join(event_log), p_after_combat, gained_items

        event_log = [f"--- 第 {p.realm_floor}/{total_floors} 层 ---"]
        events_pool = config.realm_events.get(p.realm_id, {})
        event_types = list(events_pool.keys())
        event_weights = [sum(e.get('weight', 0) for e in events_pool.get(t, [])) for t in event_types]
        
        if not any(w > 0 for w in event_weights):
             return True, "\n".join(event_log) + "\n此地异常安静，你谨慎地探索着，未发生任何事。", p, {}

        chosen_event_type = random.choices(event_types, weights=event_weights, k=1)[0]
        
        if chosen_event_type == "monster" and events_pool.get('monster'):
            chosen_monster_event = random.choice(events_pool['monster'])
            monster_id = chosen_monster_event['id']
            monster_config = config.monster_data[monster_id]
            enemy = Monster(id=monster_id, **monster_config, max_hp=monster_config['hp'])
            
            victory, combat_log, p_after_combat = await combat_manager.player_vs_monster(p, enemy)
            event_log.extend(combat_log)
            p = p_after_combat

            if victory:
                rewards = self._get_rewards(enemy.rewards)
                p.gold += rewards['gold']
                p.experience += rewards['experience']
                gained_items = rewards['items']
            else:
                p.realm_id = None
                p.realm_floor = 0
            return victory, "\n".join(event_log), p, gained_items
        
        elif chosen_event_type == "treasure" and events_pool.get('treasure'):
            chosen_treasure_event = random.choice(events_pool['treasure'])
            rewards = self._get_rewards(chosen_treasure_event['rewards'])
            p.gold += rewards['gold']
            p.experience += rewards['experience']
            gained_items = rewards['items']
            event_log.append("你发现了一个宝箱，收获颇丰！")
            return True, "\n".join(event_log), p, gained_items
            
        return True, "\n".join(event_log) + "\n你谨慎地探索着，未发生任何事。", p, {}

    def _get_rewards(self, rewards_config: dict) -> dict:
        """根据配置计算本次获得的具体奖励"""
        gained = {"gold": 0, "experience": 0, "items": {}}
        gained["gold"] = rewards_config.get("gold", 0)
        gained["experience"] = rewards_config.get("experience", 0)
        for item_id, drop_rate in rewards_config.get("items", {}).items():
            if random.random() < drop_rate:
                gained["items"][item_id] = gained["items"].get(item_id, 0) + 1
        return gained