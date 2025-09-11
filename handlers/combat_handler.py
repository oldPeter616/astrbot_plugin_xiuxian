from astrbot.api.event import AstrMessageEvent, filter
from .decorator import player_required
from .. import data_manager, xiuxian_logic
from ..config_manager import config
from ..models import Player
from ..combat_manager import BattleManager

class CombatHandler:
    def __init__(self, battle_manager: BattleManager):
        self.battle_manager = battle_manager

    @filter.command(config.CMD_SPAR, "与其他玩家切磋")
    @player_required
    async def handle_spar(self, event: AstrMessageEvent, player: Player):
        attacker = player
        if attacker.hp < attacker.max_hp:
            yield event.plain_result("你当前气血不满，无法与人切磋，请先恢复。")
            return
        mentioned_user_id = event.get_at_list()[0] if event.get_at_list() else None
        if not mentioned_user_id:
            yield event.plain_result(f"请指定切磋对象，例如：`{config.CMD_SPAR} @张三`")
            return
        if str(mentioned_user_id) == attacker.user_id:
            yield event.plain_result("道友，不可与自己为敌。")
            return
        defender = await data_manager.get_player_by_id(str(mentioned_user_id))
        if not defender:
            yield event.plain_result("对方尚未踏入仙途，无法应战。")
            return
        if defender.hp < defender.max_hp:
            yield event.plain_result("对方气血不满，此时挑战非君子所为。")
            return
        report = await xiuxian_logic.handle_pvp(attacker, defender)
        yield event.plain_result(report)

    @filter.command(config.CMD_WORLD_BOSS, "挑战或查看当前的世界Boss")
    @player_required
    async def handle_world_boss(self, event: AstrMessageEvent, player: Player):
        boss, status_msg = await self.battle_manager.ensure_boss_exists_and_get_status()
        if not boss:
            yield event.plain_result(status_msg)
            return
        yield event.plain_result(status_msg)
        yield event.plain_result(f"发送「{config.CMD_ATTACK_BOSS}」对它造成伤害！")

    @filter.command(config.CMD_ATTACK_BOSS, "攻击当前的世界Boss")
    @player_required
    async def handle_attack_boss(self, event: AstrMessageEvent, player: Player):
        result_msg = await self.battle_manager.player_attack(player)
        yield event.plain_result(result_msg)

    @filter.command(config.CMD_FIGHT_STATUS, "查看当前战斗状态")
    async def handle_fight_status(self, event: AstrMessageEvent):
        _, status_report = await self.battle_manager.ensure_boss_exists_and_get_status()
        yield event.plain_result(status_report)