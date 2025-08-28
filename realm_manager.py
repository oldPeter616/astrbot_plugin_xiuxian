# realm_manager.py

import random
import asyncio
from typing import Dict, Optional, Tuple, List
from copy import deepcopy

from .models import Player, Monster, RealmSession
from .config_manager import config
from . import combat_manager, data_manager

class RealmManager:
    def __init__(self):
        # 注意：会话仍存储在内存中。持久化是下一步优化的目标。
        self.sessions: Dict[str, RealmSession] = {}

    def get_session(self, user_id: str) -> Optional[RealmSession]:
        return self.sessions.get(user_id)

    def start_session(self, player: Player, realm_id: str) -> Tuple[bool, str]:
        if self.get_session(player.user_id):
            return False, "你已身在秘境之中，无法分心他顾。"
        
        realm_config = config.realm_data.get(realm_id)
        if not realm_config:
            return False, "不存在的秘境。"

        cost = realm_config['entry_cost']['gold']
        if player.gold < cost:
            return False, f"进入此秘境需要 {cost} 灵石，你的灵石不足。"
        
        player_level_idx = config.level_map.get(player.level, {}).get("index", -1)
        req_level_idx = config.level_map.get(realm_config['level_requirement'], {}).get("index", 999)
        if player_level_idx < req_level_idx:
            return False, f"你的境界（{player.level}）未达到进入【{realm_config['name']}】所需的（{realm_config['level_requirement']}）！"
        
        player.gold -= cost
        
        session = RealmSession(
            player_id=player.user_id,
            realm_id=realm_id,
            realm_name=realm_config['name'],
            total_floors=realm_config['total_floors']
        )
        self.sessions[player.user_id] = session
        
        msg = (f"你消耗了 {cost} 灵石，进入了【{session.realm_name}】。\n"
               f"此地共有 {session.total_floors} 层，充满了未知的危险与机遇。\n"
               f"使用「{config.CMD_REALM_ADVANCE}」指令向前探索。")
        return True, msg

    async def advance_session(self, player: Player) -> Tuple[bool, str, Player]:
        """处理前进逻辑，返回是否成功，消息，以及更新后的玩家对象"""
        session = self.get_session(player.user_id)
        if not session:
            return False, "你不在任何秘境中。", player

        session.current_floor += 1
        
        # 判断是否为最终头目战 (在最后一层触发)
        is_boss_floor = session.current_floor == session.total_floors
        
        if is_boss_floor:
            event_log = [f"--- 第 {session.current_floor}/{session.total_floors} 层 ---"]
            realm_config = config.realm_data.get(session.realm_id)
            boss_id = realm_config['boss_id']
            monster_config = config.monster_data.get(boss_id)
            enemy = Monster(id=boss_id, **monster_config, max_hp=monster_config['hp'])
            
            victory, combat_log, updated_player = await combat_manager.player_vs_monster(player, enemy)
            event_log.extend(combat_log)

            if victory:
                event_log.append(f"成功击败最终头目，你完成了【{session.realm_name}】的探索！")
                self._apply_rewards(session, enemy.rewards)
            else:
                event_log.append(f"挑战失败！你被传送出了秘境，一无所获。")

            # 无论胜败，都结束会话
            self.end_session(player.user_id)
            return victory, "\n".join(event_log), updated_player
        
        # --- 普通楼层事件 ---
        realm_config = config.realm_data[session.realm_id]
        events_pool = config.realm_events.get(session.realm_id, {})
        
        event_types = list(events_pool.keys())
        event_weights = [sum(e['weight'] for e in events_pool[t]) for t in event_types]
        chosen_event_type = random.choices(event_types, weights=event_weights, k=1)[0]
        
        event_log = [f"--- 第 {session.current_floor}/{session.total_floors} 层 ---"]
        
        if chosen_event_type == "monster" and events_pool.get('monster'):
            chosen_monster_event = random.choice(events_pool['monster'])
            monster_id = chosen_monster_event['id']
            monster_config = config.monster_data[monster_id]
            enemy = Monster(id=monster_id, **monster_config, max_hp=monster_config['hp'])
            
            victory, combat_log, updated_player = await combat_manager.player_vs_monster(player, enemy)
            event_log.extend(combat_log)

            if victory:
                self._apply_rewards(session, enemy.rewards)
                if session.current_floor == session.total_floors - 1:
                     event_log.append("\n前方气息强大，似乎就是此行的终点！再次「前进」以发起最终挑战！")
                else:
                    event_log.append("你继续向深处走去...")
                return True, "\n".join(event_log), updated_player
            else:
                event_log.append("探索失败！你被传送出了秘境，一无所获。")
                self.end_session(player.user_id)
                return False, "\n".join(event_log), updated_player
        
        elif chosen_event_type == "treasure" and events_pool.get('treasure'):
            chosen_treasure_event = random.choice(events_pool['treasure'])
            self._apply_rewards(session, chosen_treasure_event['rewards'])
            event_log.append("你发现了一个宝箱，获得了一些资源！")
            
            if session.current_floor == session.total_floors - 1:
                event_log.append("\n前方气息强大，似乎就是此行的终点！再次「前进」以发起最终挑战！")
            else:
                event_log.append("你继续向深处走去...")
            return True, "\n".join(event_log), player # 宝箱不改变玩家状态，直接返回
            
        return True, "\n".join(event_log) + "\n似乎什么都没有发生，你继续前进。", player

    def _apply_rewards(self, session: RealmSession, rewards: dict):
        """应用奖励到会话的gained_rewards中"""
        session.gained_rewards["gold"] += rewards.get("gold", 0)
        session.gained_rewards["experience"] += rewards.get("experience", 0)
        for item_id, drop_rate in rewards.get("items", {}).items():
            if random.random() < drop_rate:
                session.gained_rewards["items"][item_id] = session.gained_rewards["items"].get(item_id, 0) + 1

    def end_session(self, user_id: str) -> Optional[RealmSession]:
        return self.sessions.pop(user_id, None)