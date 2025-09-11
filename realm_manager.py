# realm_manager.py
# 秘境探索管理器

import asyncio
from typing import Tuple, Dict, Any

from .models import Player
from .config_manager import config
from . import combat_manager
from .generators import RealmGenerator, MonsterGenerator

class RealmManager:

    async def start_session(self, player: Player, realm_template_id: str) -> Tuple[bool, str, Player]:
        """
        开始一次秘境探索
        返回: (是否成功, 消息, 更新后的玩家对象)
        """
        p = player.clone()
        realm_template = config.realm_data.get(realm_template_id)
        if not realm_template:
            return False, "不存在的秘境。", p

        if p.realm_id is not None:
             current_realm_name = config.realm_data.get(p.realm_id, {}).get("name", "未知的秘境")
             return False, f"你已身在【{current_realm_name}】之中，无法分心他顾。", p

        cost = realm_template['entry_cost']['gold']
        if p.gold < cost:
            return False, f"进入此秘境需要 {cost} 靈石，你的靈石不足。", p

        player_level_idx = p.level_index
        req_level_idx = config.level_map.get(realm_template['level_requirement'], {}).get("index", 999)
        if player_level_idx < req_level_idx:
            return False, f"你的境界（{p.level}）未达到进入【{realm_template['name']}】所需的（{realm_template['level_requirement']}）！", p

        realm_instance = RealmGenerator.generate(realm_template_id)
        if not realm_instance:
             return False, "秘境生成失败，请联系管理员检查配置。", p

        p.gold -= cost
        p.realm_id = realm_template_id
        p.realm_floor = 0
        p.set_realm_instance(realm_instance)

        msg = (f"你消耗了 {cost} 靈石，进入了【{realm_template['name']}】。\n"
               f"此地共有 {realm_instance.total_floors} 层，充满了未知的危险与机遇。\n"
               f"使用「{config.CMD_REALM_ADVANCE}」指令向前探索。")
        return True, msg, p

    async def advance_session(self, player: Player) -> Tuple[bool, str, Player, Dict[str, int]]:
        """
        处理前进逻辑
        返回: (是否成功, 消息, 更新后的玩家对象, 获得的物品字典)
        """
        p = player.clone()
        realm_instance = p.get_realm_instance()

        if not p.realm_id or not realm_instance:
            return False, "你不在任何秘境中。", p, {}
            
        p.realm_floor += 1
        current_floor_index = p.realm_floor - 1

        if not (0 <= current_floor_index < len(realm_instance.floors)):
            p.realm_id = None
            p.realm_floor = 0
            p.set_realm_instance(None)
            return False, "秘境探索数据异常，已将你传送出来。", p, {}
        
        event = realm_instance.floors[current_floor_index]
        event_log = [f"--- 第 {p.realm_floor}/{realm_instance.total_floors} 层 ---"]

        # 传递玩家等级索引 player.level_index
        if event.type == "monster" or event.type == "boss":
            return await self._handle_monster_event(p, event_log, event, p.level_index)
        elif event.type == "treasure":
            return self._handle_treasure_event(p, event_log, event)
        else:
            event_log.append("此地异常安静，你谨慎地探索着，未发生任何事。")
            if p.realm_floor >= realm_instance.total_floors:
                realm_template = config.realm_data[p.realm_id]
                event_log.append(f"\n你成功探索完了【{realm_template['name']}】的所有区域！")
                p.realm_id = None
                p.realm_floor = 0
                p.set_realm_instance(None)
            return True, "\n".join(event_log), p, {}

    async def _handle_monster_event(self, p: Player, event_log: list, event, realm_level: int) -> Tuple[bool, str, Player, Dict[str, int]]:
        """处理遭遇怪物/Boss事件"""
        monster_template_id = event.data["id"]
        # 传入玩家等级索引
        enemy = MonsterGenerator.create_monster(monster_template_id, player_level_index)
        if not enemy:
            return False, "怪物生成失败！", p, {}
        
        loop = asyncio.get_running_loop()
        victory, combat_log, p_after_combat = await loop.run_in_executor(
            None, combat_manager.player_vs_monster, p, enemy
        )
        event_log.extend(combat_log)
        p = p_after_combat

        gained_items = {}
        if victory:
            rewards = enemy.rewards
            p.gold += rewards.get('gold', 0)
            p.experience += rewards.get('experience', 0)
            gained_items = rewards.get('items', {})
            
            # 胜利后检查是否探索完毕
            realm_instance = p.get_realm_instance()
            realm_template = config.realm_data[p.realm_id]
            if p.realm_floor >= realm_instance.total_floors:
                event_log.append(f"\n成功击败最终头目！你通关了【{realm_template['name']}】！")
                p.realm_id = None
                p.realm_floor = 0
                p.set_realm_instance(None)
        else:
            # 战斗失败，重置秘境状态
            p.realm_id = None
            p.realm_floor = 0
            p.set_realm_instance(None)
        
        return victory, "\n".join(event_log), p, gained_items

    def _handle_treasure_event(self, p: Player, event_log: list, event, realm_level: int) -> Tuple[bool, str, Player, Dict[str, int]]:
        """处理发现宝藏事件"""
        gold_gained = event.data.get("gold", 50) 
        p.gold += gold_gained
        event_log.append(f"你发现了一个宝箱，获得了 {gold_gained} 灵石！")

        realm_instance = p.get_realm_instance()
        realm_template = config.realm_data[p.realm_id]
        if p.realm_floor >= realm_instance.total_floors:
            event_log.append(f"\n你成功探索完了【{realm_template['name']}】的所有区域！")
            p.realm_id = None
            p.realm_floor = 0
            p.set_realm_instance(None)
        return True, "\n".join(event_log), p, {}