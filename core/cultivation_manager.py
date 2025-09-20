
import time
from typing import Tuple

from data.plugins.astrbot_plugin_xiuxian.data.data_manager import DataBase
from ..config_manager import config
from ..models import Player


class CultivationManager:
    """闭关逻辑处理"""
    def __init__(self, db: DataBase):
        self.db = db
    def handle_start_cultivation(self, player: Player) -> Tuple[bool, str, Player]:
        """处理闭关逻辑"""
        if player.state != "空闲":
            return False, f"道友当前正在「{player.state}」中，无法分心闭关。", player

        player.state = "修炼中"
        player.state_start_time = time.time()

        msg = "道友已进入冥想状态，开始闭关修炼。使用「出关」可查看修炼成果。"
        return True, msg, player


    def handle_end_cultivation(self, player: Player) -> Tuple[bool, str, Player]:
        """处理出关逻辑"""
        if player.state != "修炼中":
            return False, "道友尚未开始闭关，何谈出关？", player

        now = time.time()
        duration_minutes = (now - player.state_start_time) / 60

        if duration_minutes < 1:
            player.state = "空闲"
            player.state_start_time = 0.0
            msg = "道友本次闭关不足一分钟，未能有所精进。下次要更有耐心才是。"
            return True, msg, player

        exp_gained = int(duration_minutes * config.BASE_EXP_PER_MINUTE)
        player.experience += exp_gained
        player.state = "空闲"
        player.state_start_time = 0.0

        msg = (
            f"道友本次闭关共持续 {int(duration_minutes)} 分钟，\n"
            f"修为增加了 {exp_gained} 点！\n"
            f"当前总修为：{player.experience}"
        )
        return True, msg, player
