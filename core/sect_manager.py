# core/sect_manager.py

from typing import Tuple, Optional

from astrbot.api import AstrBotConfig
from ..models import Player
from ..data import DataBase

class SectManager:
    def __init__(self, db: DataBase, config: AstrBotConfig):
        self.db = db
        self.config = config

    async def handle_create_sect(self, player: Player, sect_name: str) -> Tuple[bool, str, Optional[Player]]:
        if player.sect_id is not None:
            return False, f"道友已是「{player.sect_name}」的成员，无法另立门户。", None

        if await self.db.get_sect_by_name(sect_name):
            return False, f"「{sect_name}」之名已响彻修仙界，请道友另择佳名。", None

        cost = self.config["VALUES"]["CREATE_SECT_COST"]
        if player.gold < cost:
            return False, f"开宗立派非同小可，需消耗 {cost} 灵石，道友的家底还不够。", None

        p_clone = player.clone()
        p_clone.gold -= cost
        sect_id = await self.db.create_sect(sect_name, p_clone.user_id)
        p_clone.sect_id = sect_id
        p_clone.sect_name = sect_name

        msg = f"恭喜道友！「{sect_name}」今日正式成立，广纳门徒，共图大道！"
        return True, msg, p_clone

    async def handle_join_sect(self, player: Player, sect_name: str) -> Tuple[bool, str, Optional[Player]]:
        if player.sect_id is not None:
            return False, f"道友已是「{player.sect_name}」的成员，不可三心二意。", None

        sect = await self.db.get_sect_by_name(sect_name)
        if not sect:
            return False, f"寻遍天下，也未曾听闻「{sect_name}」之名，请道友核实。", None

        p_clone = player.clone()
        p_clone.sect_id = sect['id']
        p_clone.sect_name = sect['name']

        msg = f"道友已成功拜入「{sect_name}」，从此同门齐心，共觅仙缘！"
        return True, msg, p_clone

    async def handle_leave_sect(self, player: Player) -> Tuple[bool, str, Optional[Player]]:
        if player.sect_id is None:
            return False, "道友本是逍遥散人，何谈退出宗门？", None

        sect = await self.db.get_sect_by_id(player.sect_id)
        if sect and sect['leader_id'] == player.user_id:
            members = await self.db.get_sect_members(player.sect_id)
            if len(members) > 1:
                return False, "道友身为一宗之主，身系宗门兴衰，不可轻易脱离！请先传位于他人或解散宗门。", None
            else:
                await self.db.delete_sect(player.sect_id)

        p_clone = player.clone()
        sect_name = p_clone.sect_name
        p_clone.sect_id = None
        p_clone.sect_name = None

        msg = f"道不同不相为谋。道友已脱离「{sect_name}」，从此山高水长，江湖再见。"
        return True, msg, p_clone