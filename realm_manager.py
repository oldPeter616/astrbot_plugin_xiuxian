# realm_manager.py
# 秘境探索管理器

import random
from typing import Dict, Optional, Tuple
from .models import Player, Monster, RealmSession
from .config_manager import config
from . import combat_manager

class RealmManager:
    def __init__(self):
        self.sessions: Dict[str, RealmSession] = {}

    def get_session(self, user_id: str) -> Optional[RealmSession]:
        return self.sessions.get(user_id)

    def start_session(self, player: Player, realm_id: str) -> Tuple[bool, str]:
        if self.get_session(player.user_id):
            return False, "你已身在秘境之中，无法分心他顾。"
        
        realm_config = config.realm_data.get(realm_id)
        if not realm_config:
            return False, "不存在的秘境。"

        # 检查进入条件
        if player.gold < realm_config['entry_cost']['gold']:
            return False, f"进入此秘境需要 {realm_config['entry_cost']['gold']} 灵石，你的灵石不足。"
        
        player.gold -= realm_config['entry_cost']['gold']
        
        session = RealmSession(
            player_id=player.user_id,
            realm_id=realm_id,
            realm_name=realm_config['name'],
            total_floors=realm_config['total_floors']
        )
        self.sessions[player.user_id] = session
        
        msg = (f"你消耗了 {realm_config['entry_cost']['gold']} 灵石，进入了【{session.realm_name}】。\n"
               f"此地共有 {session.total_floors} 层，充满了未知的危险与机遇。\n"
               f"使用「{config.CMD_REALM_ADVANCE}」指令向前探索。")
        return True, msg

    def advance_session(self, player: Player) -> Tuple[bool, str, Dict]:
        """处理前进逻辑，返回是否成功，消息，以及奖励字典"""
        session = self.get_session(player.user_id)
        if not session:
            return False, "你不在任何秘境中。", {}

        session.current_floor += 1
        
        if session.current_floor > session.total_floors:
            # 挑战最终Boss
            realm_config = config.realm_data.get(session.realm_id)
            boss_id = realm_config['boss_id']
            monster_config = config.monster_data.get(boss_id)
            enemy = Monster(id=boss_id, name=monster_config['name'], hp=monster_config['hp'],
                            max_hp=monster_config['hp'], attack=monster_config['attack'],
                            defense=monster_config['defense'], rewards=monster_config['rewards'])
            
            victory, log = combat_manager.player_vs_monster(player, enemy)
            
            if victory:
                log.append(f"成功击败最终头目，你完成了【{session.realm_name}】的探索！")
                final_rewards = self._apply_rewards(session, enemy.rewards)
                self.end_session(player.user_id)
                return True, "\n".join(log), final_rewards
            else:
                player.hp = 1 # 挑战失败，重伤
                log.append(f"挑战失败！你被传送出了秘境，一无所获。")
                self.end_session(player.user_id)
                return False, "\n".join(log), {}
        
        # 触发随机事件
        realm_config = config.realm_data[session.realm_id]
        events = realm_config['events']
        event_types = [e['type'] for e in events]
        event_weights = [e['weight'] for e in events]
        chosen_event_type = random.choices(event_types, weights=event_weights, k=1)[0]
        
        event_log = [f"--- 第 {session.current_floor}/{session.total_floors} 层 ---"]
        
        if chosen_event_type == "monster":
            monster_id = random.choice([e['id'] for e in events if e['type'] == 'monster'])
            monster_config = config.monster_data[monster_id]
            enemy = Monster(id=monster_id, **monster_config, max_hp=monster_config['hp'])
            
            victory, combat_log = combat_manager.player_vs_monster(player, enemy)
            event_log.extend(combat_log)

            if victory:
                self._apply_rewards(session, enemy.rewards)
                event_log.append("你继续向深处走去...")
                return True, "\n".join(event_log), {}
            else:
                player.hp = 1
                event_log.append("探索失败！你被传送出了秘境，一无所获。")
                self.end_session(player.user_id)
                return False, "\n".join(event_log), {}
        
        elif chosen_event_type == "treasure":
            treasure_config = [e for e in events if e['type'] == 'treasure'][0]
            self._apply_rewards(session, treasure_config['rewards'])
            event_log.append("你发现了一个宝箱，获得了一些资源！")
            event_log.append("你继续向深处走去...")
            return True, "\n".join(event_log), {}
            
        return False, "发生未知错误。", {}

    def _apply_rewards(self, session: RealmSession, rewards: dict) -> Dict:
        """应用奖励到会话中，并返回本次获得的奖励"""
        gained = {"gold": 0, "experience": 0, "items": {}}
        
        g = rewards.get("gold", 0)
        session.gained_rewards["gold"] += g
        gained["gold"] = g

        e = rewards.get("experience", 0)
        session.gained_rewards["experience"] += e
        gained["experience"] = e

        for item_id, drop_rate in rewards.get("items", {}).items():
            if random.random() < drop_rate:
                session.gained_rewards["items"][item_id] = session.gained_rewards["items"].get(item_id, 0) + 1
                gained["items"][item_id] = gained["items"].get(item_id, 0) + 1
        
        return gained

    def end_session(self, user_id: str) -> Optional[RealmSession]:
        return self.sessions.pop(user_id, None)