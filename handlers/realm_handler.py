from astrbot.api.event import AstrMessageEvent, filter
from .decorator import player_required
from .. import data_manager
from ..config_manager import config
from ..models import Player

class RealmHandler:
    @filter.command(config.CMD_REALM_LIST, "查看所有可探索的秘境")
    async def handle_realm_list(self, event: AstrMessageEvent):
        reply_msg = "--- 秘境列表 ---\n"
        for realm_id, info in config.realm_data.items():
            cost = info['entry_cost']['gold']
            reply_msg += (f"【{info['name']}】\n"
                          f"  准入境界: {info['level_requirement']}\n"
                          f"  进入消耗: {cost} 灵石\n")
        reply_msg += f"\n使用「{config.CMD_ENTER_REALM} <秘境名>」进入探索。"
        yield event.plain_result(reply_msg)

    @filter.command(config.CMD_ENTER_REALM, "进入秘境开始探索")
    @player_required
    async def handle_enter_realm(self, event: AstrMessageEvent):
        player: Player = event.player
        realm_manager = event.realm_manager
        
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_ENTER_REALM} <秘境名>」。")
            return
        
        realm_name = parts[1]
        target_realm_id = None
        for r_id, info in config.realm_data.items():
            if info['name'] == realm_name:
                target_realm_id = r_id
                break
        
        if not target_realm_id:
            yield event.plain_result(f"未找到名为【{realm_name}】的秘境。")
            return
            
        success, msg = realm_manager.start_session(player, target_realm_id)
        if success:
            await data_manager.update_player(player)
        yield event.plain_result(msg)
        
    @filter.command(config.CMD_REALM_ADVANCE, "在秘境中前进")
    @player_required
    async def handle_realm_advance(self, event: AstrMessageEvent):
        player: Player = event.player
        realm_manager = event.realm_manager
            
        success, msg, updated_player = await realm_manager.advance_session(player)
        
        # 战斗或事件结束后，无论成功失败，都同步一次最新状态到数据库
        await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_LEAVE_REALM, "离开当前秘境")
    @player_required
    async def handle_leave_realm(self, event: AstrMessageEvent):
        player: Player = event.player
        realm_manager = event.realm_manager
        session = realm_manager.end_session(player.user_id)
        
        if not session:
            yield event.plain_result("你不在任何秘境中。")
            return
            
        rewards = session.gained_rewards
        player.gold += rewards.get('gold', 0)
        player.experience += rewards.get('experience', 0)
        
        reward_log = f"你离开了【{session.realm_name}】，本次探索收获如下：\n"
        reward_log += f" - 灵石: {rewards.get('gold', 0)}\n"
        reward_log += f" - 修为: {rewards.get('experience', 0)}\n"
        
        if items := rewards.get('items'):
            reward_log += " - 物品:\n"
            for item_id, qty in items.items():
                await data_manager.add_item_to_inventory(player.user_id, item_id, qty)
                item_name = config.item_data.get(item_id, {}).get("name", "未知物品")
                reward_log += f"   - 【{item_name}】x{qty}\n"
        
        await data_manager.update_player(player)
        yield event.plain_result(reward_log)