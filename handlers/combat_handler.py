# handlers/combat_handler.py
from astrbot.api.event import AstrMessageEvent
from astrbot.api import AstrBotConfig
from astrbot.core.message.components import At
from ..data import DataBase
from ..core import BattleManager
from ..config_manager import ConfigManager
from ..models import Player
from .utils import player_required, require_idle_state

CMD_SPAR = "切磋"
CMD_FIGHT_BOSS = "讨伐boss"

__all__ = ["CombatHandler"]

class CombatHandler:
    # 战斗相关指令处理器
    
    def __init__(self, db: DataBase, config: AstrBotConfig, config_manager: ConfigManager):
        self.db = db
        self.config = config
        self.config_manager = config_manager
        self.battle_manager = BattleManager(db, config, config_manager)

    @player_required
    @require_idle_state
    async def handle_spar(self, attacker: Player, event: AstrMessageEvent):
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
                    if hasattr(comp, 'name'):
                        defender_name = comp.name
                    break

        if not mentioned_user_id:
            yield event.plain_result(f"请指定切磋对象，例如：`{CMD_SPAR} @张三`")
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

        _, _, report_lines = self.battle_manager.player_vs_player(attacker, defender, attacker_name, defender_name)
        yield event.plain_result("\n".join(report_lines))

    async def handle_boss_list(self, event: AstrMessageEvent):
        active_bosses_with_templates = await self.battle_manager.ensure_bosses_are_spawned()

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
                    report.append(f"    - {p_data['user_name']}: {p_data['total_damage']} 伤害")

        report.append(f"\n使用「{CMD_FIGHT_BOSS} <Boss ID>」发起挑战！")
        yield event.plain_result("\n".join(report))

    @player_required
    @require_idle_state
    async def handle_fight_boss(self, player: Player, event: AstrMessageEvent, boss_id: str):
        if not boss_id:
            yield event.plain_result(f"指令格式错误！请使用「{CMD_FIGHT_BOSS} <Boss ID>」。")
            return

        player_name = event.get_sender_name()
        result_msg = await self.battle_manager.player_fight_boss(player, boss_id, player_name)
        yield event.plain_result(result_msg)
