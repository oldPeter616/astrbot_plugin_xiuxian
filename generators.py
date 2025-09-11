# generators.py
# 动态内容生成器模块

import random
from typing import Dict, Any, List, Optional

from astrbot.api import logger
from .config_manager import config
from .models import Monster, Boss, RealmInstance, FloorEvent, Player

class MonsterGenerator:
    """基于标签系统的怪物和Boss生成器"""

    @staticmethod
    def _generate_rewards(base_loot: List, level: int) -> Dict[str, int]:
        """根据掉落表生成具体奖励"""
        gained_items = {}
        for entry in base_loot:
            if random.random() < entry.get("chance", 0):
                quantity_range = entry.get("quantity", [1, 1])
                min_qty = quantity_range[0]
                max_qty = quantity_range[1] if len(quantity_range) > 1 else min_qty
                
                item_id = str(entry["item_id"])
                amount = random.randint(min_qty, max_qty)
                gained_items[item_id] = gained_items.get(item_id, 0) + amount
        return gained_items

    @classmethod
    def create_monster(cls, template_id: str, player_level_index: int) -> Optional[Monster]:
        """根据模板ID和玩家等级创建怪物实例"""
        template = config.monster_data.get(template_id)
        if not template:
            logger.warning(f"尝试创建怪物失败：找不到模板ID {template_id}")
            return None

        # 1. 计算基础属性 (与玩家等级挂钩)
        base_hp = 15 * player_level_index + 60
        base_attack = 2 * player_level_index + 8
        base_defense = 1 * player_level_index + 4
        base_gold = 3 * player_level_index + 10
        base_exp = 5 * player_level_index + 20

        # 2. 初始化最终属性和名称
        final_name = template["name"]
        final_hp = base_hp
        final_attack = base_attack
        final_defense = base_defense
        final_gold = base_gold
        final_exp = base_exp
        combined_loot_table = []

        # 3. 应用标签效果
        for tag_name in template.get("tags", []):
            tag_effect = config.tag_data.get(tag_name)
            if not tag_effect:
                continue
            
            # 修改名称
            if "name_prefix" in tag_effect:
                final_name = f"【{tag_effect['name_prefix']}】{final_name}"
            
            # 应用属性乘数
            final_hp *= tag_effect.get("hp_multiplier", 1.0)
            final_attack *= tag_effect.get("attack_multiplier", 1.0)
            final_defense *= tag_effect.get("defense_multiplier", 1.0)
            final_gold *= tag_effect.get("gold_multiplier", 1.0)
            final_exp *= tag_effect.get("exp_multiplier", 1.0)

            # 合并掉落表
            if "add_to_loot" in tag_effect:
                combined_loot_table.extend(tag_effect["add_to_loot"])
        
        # 4. 生成最终实例
        final_hp = int(final_hp)
        instance = Monster(
            id=template_id,
            name=final_name,
            hp=final_hp,
            max_hp=final_hp,
            attack=int(final_attack),
            defense=int(final_defense),
            rewards={
                "gold": int(final_gold),
                "experience": int(final_exp),
                "items": cls._generate_rewards(combined_loot_table, player_level_index)
            }
        )
        return instance

    @classmethod
    def create_boss(cls, template_id: str, player_level_index: int) -> Optional[Boss]:
        """根据模板ID和玩家等级创建Boss实例"""
        template = config.boss_data.get(template_id)
        if not template:
            logger.warning(f"尝试创建Boss失败：找不到模板ID {template_id}")
            return None

        # Boss的基础属性更高
        base_hp = 100 * player_level_index + 500
        base_attack = 10 * player_level_index + 40
        base_defense = 5 * player_level_index + 20
        base_gold = 50 * player_level_index + 1000
        base_exp = 100 * player_level_index + 2000

        final_name = template["name"]
        final_hp = base_hp
        final_attack = base_attack
        final_defense = base_defense
        final_gold = base_gold
        final_exp = base_exp
        combined_loot_table = []

        for tag_name in template.get("tags", []):
            tag_effect = config.tag_data.get(tag_name, {})
            if "name_prefix" in tag_effect:
                final_name = f"【{tag_effect['name_prefix']}】{final_name}"
            final_hp *= tag_effect.get("hp_multiplier", 1.0)
            final_attack *= tag_effect.get("attack_multiplier", 1.0)
            final_defense *= tag_effect.get("defense_multiplier", 1.0)
            final_gold *= tag_effect.get("gold_multiplier", 1.0)
            final_exp *= tag_effect.get("exp_multiplier", 1.0)
            if "add_to_loot" in tag_effect:
                combined_loot_table.extend(tag_effect["add_to_loot"])
        
        final_hp = int(final_hp)
        instance = Boss(
            id=template_id,
            name=final_name,
            hp=final_hp,
            max_hp=final_hp,
            attack=int(final_attack),
            defense=int(final_defense),
            cooldown_minutes=template["cooldown_minutes"],
            rewards={
                "gold": int(final_gold),
                "experience": int(final_exp),
                "items": cls._generate_rewards(combined_loot_table, player_level_index)
            }
        )
        return instance

class RealmGenerator:
    """秘境实例生成器"""

    @staticmethod
    def generate(realm_template_id: str) -> Optional[RealmInstance]:
        """根据秘境模板生成一个完整的秘境探索实例"""
        template = config.realm_data.get(realm_template_id)
        if not template:
            logger.warning(f"尝试生成秘境失败：找不到模板ID {realm_template_id}")
            return None

        floor_range = template.get("floor_range", [3, 3])
        total_floors = random.randint(floor_range[0], floor_range[1])
        
        floor_events: List[FloorEvent] = []
        event_pool = template.get("event_pool", [])
        weights = [event.get("weight", 0) for event in event_pool]
        
        if not event_pool or sum(weights) <= 0:
            return RealmInstance(id=realm_template_id, total_floors=total_floors, floors=[])

        for _ in range(total_floors - 1):
            chosen_event_template = random.choices(event_pool, weights=weights, k=1)[0]
            event_type = chosen_event_template["type"]
            
            if event_type == "monster":
                monster_pool = template.get("monster_pool", [])
                if monster_pool:
                    monster_id = random.choice(monster_pool)
                    floor_events.append(FloorEvent(type="monster", data={"id": monster_id}))
                else:
                    floor_events.append(FloorEvent(type="empty", data={}))
            elif event_type == "treasure":
                 floor_events.append(FloorEvent(type="treasure", data=chosen_event_template.get("rewards", {})))
            else:
                floor_events.append(FloorEvent(type="empty", data={}))

        floor_events.append(FloorEvent(type="boss", data={"id": template["boss_id"]}))

        return RealmInstance(
            id=realm_template_id,
            total_floors=total_floors,
            floors=floor_events
        )