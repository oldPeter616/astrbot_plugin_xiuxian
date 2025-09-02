from astrbot.api.event import AstrMessageEvent, filter
from .decorator import player_required
from .parser import parse_args
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

    @filter.command(config.CMD_START_BOSS_FIGHT, "开启一场世界Boss讨伐战")
    @player_required
    @parse_args(str)
    async def handle_start_boss_fight(self, event: AstrMessageEvent, boss_name: str, player: Player):
        if not boss_name:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_START_BOSS_FIGHT} <Boss名>」。")
            return

        target_boss_config = None
        for boss_id, info in config.boss_data.items():
            if info['name'] == boss_name:
                target_boss_config = {'id': boss_id, **info}
                break

        if not target_boss_config:
            yield event.plain_result(f"未找到名为【{boss_name}】的Boss。")
            return

        success, msg = await self.battle_manager.start_battle(target_boss_config)
        yield event.plain_result(msg)

        if success:
            _, join_msg = await self.battle_manager.add_participant(player)
            yield event.plain_result(join_msg)

    @filter.command(config.CMD_JOIN_FIGHT, "加入当前的Boss战")
    @player_required
    async def handle_join_fight(self, event: AstrMessageEvent, player: Player):
        success, msg = await self.battle_manager.add_participant(player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_ATTACK_BOSS, "攻击当前的世界Boss")
    @player_required
    async def handle_attack_boss(self, event: AstrMessageEvent, player: Player):
        result = await self.battle_manager.player_attack(player)
        yield event.plain_result(result.message)

        if result.updated_players:
            await data_manager.update_players_in_transaction(result.updated_players)

    @filter.command(config.CMD_FIGHT_STATUS, "查看当前战斗状态")
    async def handle_fight_status(self, event: AstrMessageEvent):
        status_report = self.battle_manager.get_status()
        yield event.plain_result(status_report)