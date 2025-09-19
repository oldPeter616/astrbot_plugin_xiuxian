# handlers/player_handler.py'
import random
import time
from typing import Tuple, Dict
from astrbot.api.event import AstrMessageEvent
from data.plugins.astrbot_plugin_xiuxian.data.data_manager import DataBase
from ..core.cultivation_manager import CultivationManager
from ..config_manager import config
from ..models import Player

__all__ = ["PlayerHandler"]


# xiuxian_logic.py
# 核心游戏逻辑模块

def _calculate_base_stats(level_index: int) -> Dict[str, int]:
    """根据境界等级计算基础战斗属性"""
    base_hp = 100 + level_index * 50
    base_attack = 10 + level_index * 8
    base_defense = 5 + level_index * 4
    return {
        "hp": base_hp,
        "max_hp": base_hp,
        "attack": base_attack,
        "defense": base_defense,
    }


def generate_new_player_stats(user_id: str) -> Player:
    """为新玩家生成初始属性"""
    root = random.choice(config.POSSIBLE_SPIRITUAL_ROOTS)
    initial_stats = _calculate_base_stats(0)
    return Player(
        user_id=user_id,
        spiritual_root=f"{root}灵根",
        gold=config.INITIAL_GOLD,
        **initial_stats, # type: ignore
    )


def handle_check_in(player: Player) -> Tuple[bool, str, Player]:
    """处理签到逻辑"""
    now = time.time()
    if now - player.last_check_in < 22 * 60 * 60:
        return False, "道友，今日已经签到过了，请明日再来。", player

    reward = random.randint(config.CHECK_IN_REWARD_MIN, config.CHECK_IN_REWARD_MAX)
    player.gold += reward
    player.last_check_in = now

    msg = f"签到成功！获得灵石 x{reward}。道友当前的家底为 {player.gold} 灵石。"
    return True, msg, player


def handle_breakthrough(player: Player) -> Tuple[bool, str, Player]:
    """处理突破逻辑"""
    current_level_index = player.level_index

    if current_level_index >= len(config.level_data) - 1:
        return False, "道友已臻化境，达到当前世界的顶峰，无法再进行突破！", player

    next_level_info = config.level_data[current_level_index + 1]
    exp_needed = next_level_info["exp_needed"]
    success_rate = next_level_info["success_rate"]

    if player.experience < exp_needed:
        msg = (
            f"突破失败！\n目标境界：{next_level_info['level_name']}\n"
            f"所需修为：{exp_needed} (当前拥有 {player.experience})"
        )
        return False, msg, player

    if random.random() < success_rate:
        player.level_index = current_level_index + 1
        player.experience = 0

        new_stats = _calculate_base_stats(player.level_index)
        player.hp = new_stats["hp"]
        player.max_hp = new_stats["max_hp"]
        player.attack = new_stats["attack"]
        player.defense = new_stats["defense"]

        msg = (
            f"恭喜道友！天降祥瑞，突破成功！\n"
            f"当前境界已达：【{player.level}】\n"
            f"生命值提升至 {player.max_hp}，攻击提升至 {player.attack}，防御提升至 {player.defense}！"
        )
    else:
        punishment = int(exp_needed * config.BREAKTHROUGH_FAIL_PUNISHMENT_RATIO)
        player.experience -= punishment
        msg = (
            f"可惜！道友在突破过程中气息不稳，导致失败。\n"
            f"境界稳固在【{player.level}】，但修为空耗 {punishment} 点。"
        )

    return True, msg, player


class PlayerHandler:
    def __init__(self, db: DataBase):
        self.db = db
        self.cultivation_manager = CultivationManager(db)

    async def handle_start_xiuxian(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if await self.db.get_player_by_id(user_id):
            yield event.plain_result("道友，你已踏入仙途，无需重复此举。")
            return

        new_player = generate_new_player_stats(user_id)
        await self.db.create_player(new_player)
        reply_msg = (
            f"恭喜道友 {event.get_sender_name()} 踏上仙途！\n"
            f"初始灵根：【{new_player.spiritual_root}】\n"
            f"启动资金：【{new_player.gold}】灵石\n"
            f"发送「{config.CMD_PLAYER_INFO}」查看状态，「{config.CMD_CHECK_IN}」领取福利！"
        )
        yield event.plain_result(reply_msg)

    async def handle_player_info(self, event: AstrMessageEvent, player: Player):
        sect_info = f"宗门：{player.sect_name if player.sect_name else '逍遥散人'}"
        reply_msg = (
            f"--- 道友 {event.get_sender_name()} 的信息 ---\n"
            f"境界：{player.level}\n"
            f"灵根：{player.spiritual_root}\n"
            f"修为：{player.experience}\n"
            f"灵石：{player.gold}\n"
            f"{sect_info}\n"
            f"状态：{player.state}\n"
            "--- 战斗属性 ---\n"
            f"❤️生命: {player.hp}/{player.max_hp}\n"
            f"⚔️攻击: {player.attack}\n"
            f"🛡️防御: {player.defense}\n"
            f"--------------------------"
        )
        yield event.plain_result(reply_msg)

    async def handle_check_in(self, event: AstrMessageEvent, player: Player):
        success, msg, updated_player = handle_check_in(player)
        if success:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)

    async def handle_start_cultivation(self, event: AstrMessageEvent, player: Player):
        success, msg, updated_player = (
            self.cultivation_manager.handle_start_cultivation(player)
        )
        if success:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)

    async def handle_end_cultivation(self, event: AstrMessageEvent, player: Player):
        success, msg, updated_player = self.cultivation_manager.handle_end_cultivation(
            player
        )
        if success:
            await self.db.update_player(updated_player)
        yield event.plain_result(msg)

    async def handle_breakthrough(self, event: AstrMessageEvent, player: Player):
        if player.state != "空闲":
            yield event.plain_result(
                f"道友当前正在「{player.state}」中，无法尝试突破。"
            )
            return
        success, msg, updated_player = handle_breakthrough(player)
        await self.db.update_player(updated_player)
        yield event.plain_result(msg)
