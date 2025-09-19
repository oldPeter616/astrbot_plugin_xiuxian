# handlers/combat_handler.py

from astrbot.api.event import AstrMessageEvent
from astrbot.core.message.components import At
from data.plugins.astrbot_plugin_xiuxian.data.data_manager import DataBase
from ..core.combat_manager import BattleManager, player_vs_player
from ..config_manager import config
from ..models import Player

__all__ = ["CombatHandler"]


class CombatHandler:
    def __init__(self, db: DataBase):
        self.db = db
        self.combat_manager = BattleManager(self.db)

    async def handle_spar(self, event: AstrMessageEvent, player: Player):
        attacker = player
        if attacker.hp < attacker.max_hp:
            yield event.plain_result("你当前气血不满，无法与人切磋，请先恢复。")
            return

        message_obj = event.message_obj
        mentioned_user_id = None
        defender_name = None

        if hasattr(message_obj, "message"):
            for comp in message_obj.message:
                if isinstance(comp, At):
                    mentioned_user_id = comp.qq
                    if hasattr(comp, "name"):
                        defender_name = comp.name
                    break

        if not mentioned_user_id:
            yield event.plain_result(f"请指定切磋对象，例如：`{config.CMD_SPAR} @张三`")
            return

        if str(mentioned_user_id) == attacker.user_id:
            yield event.plain_result("道友，不可与自己为敌。")
            return

        defender = await self.db.get_player_by_id(str(mentioned_user_id))
        if not defender:
            yield event.plain_result("对方尚未踏入仙途，无法应战。")
            return

        if defender.hp < defender.max_hp:
            yield event.plain_result("对方气血不满，此时挑战非君子所为。")
            return

        attacker_name = event.get_sender_name()

        _, _, combat_log = player_vs_player(
            attacker, defender, attacker_name, defender_name
        )
        report = "\n".join(combat_log)
        yield event.plain_result(report)

    async def handle_boss_list(self, event: AstrMessageEvent):
        """处理查看世界Boss列表的指令"""
        active_bosses_with_templates = (
            await self.plugin.battle_manager.ensure_bosses_are_spawned()
        )

        if not active_bosses_with_templates:
            yield event.plain_result("天地间一片祥和，暂无妖兽作乱。")
            return

        report = ["--- 当前可讨伐的世界Boss ---"]
        for instance, template in active_bosses_with_templates:
            report.append(
                f"【{template.name}】 (ID: {instance.boss_id})\n"
                f"  ❤️剩余生命: {instance.current_hp}/{instance.max_hp}"
            )
            participants = await self.db.get_boss_participants(instance.boss_id)
            if participants:
                report.append("  - 伤害贡献榜 -")
                for p_data in participants[:3]:
                    report.append(
                        f"    - {p_data['user_name']}: {p_data['total_damage']} 伤害"
                    )

        report.append(f"\n使用「{config.CMD_FIGHT_BOSS} <Boss ID>」发起挑战！")
        yield event.plain_result("\n".join(report))

    async def handle_fight_boss(
        self, event: AstrMessageEvent, player: Player, boss_id: str, player_name: str
    ):
        """处理讨伐世界Boss的指令"""
        if not boss_id:
            yield event.plain_result(
                f"指令格式错误！请使用「{config.CMD_FIGHT_BOSS} <Boss ID>」。"
            )
            return

        result_msg = await self.plugin.battle_manager.player_fight_boss(
            player, boss_id, player_name
        )
        yield event.plain_result(result_msg)
