import re
import asyncio
from functools import wraps
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter, MessageEventResult
from astrbot.api.star import Context, Star, register

from . import data_manager, xiuxian_logic, combat_manager, realm_manager
from .config_manager import config
from .models import Player

def player_required(func):
    """装饰器：检查玩家是否存在，并将player对象附加到event上。"""
    @wraps(func)
    async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
        user_id = event.get_sender_id()
        player = await data_manager.get_player_by_id(user_id)

        if not player:
            yield event.plain_result(f"道友尚未踏入仙途，请发送「{config.CMD_START_XIUXIAN}」开启你的旅程。")
            return
        
        setattr(event, 'player', player)
        
        async for result in func(self, event, *args, **kwargs):
            yield result
            
    return wrapper

@register("xiuxian", "YourName", "一个文字修仙插件", "1.0.0")
class XiuXianPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.battle_manager = combat_manager.BattleManager()
        self.realm_manager = realm_manager.RealmManager()

    async def initialize(self):
        """插件初始化"""
        config.load()
        try:
            await data_manager.init_db_pool()
            logger.info("修仙插件：数据库连接池初始化成功。")
        except Exception as e:
            logger.error(f"修仙插件：数据库初始化失败，错误：{e}")

    @filter.command(config.CMD_START_XIUXIAN, "开始你的修仙之路")
    async def handle_start_xiuxian(self, event: AstrMessageEvent) -> MessageEventResult:
        user_id = event.get_sender_id()
        if await data_manager.get_player_by_id(user_id):
            yield event.plain_result("道友，你已踏入仙途，无需重复此举。")
            return

        new_player = xiuxian_logic.generate_new_player_stats(user_id)
        await data_manager.create_player(new_player)
        reply_msg = (
            f"恭喜道友 {event.get_sender_name()} 踏上仙途！\n"
            f"初始灵根：【{new_player.spiritual_root}】\n"
            f"启动资金：【{new_player.gold}】灵石\n"
            f"发送「{config.CMD_PLAYER_INFO}」查看状态，「{config.CMD_CHECK_IN}」领取福利！"
        )
        yield event.plain_result(reply_msg)

    @filter.command(config.CMD_PLAYER_INFO, "查看你的角色信息")
    @player_required
    async def handle_player_info(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
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

    @filter.command(config.CMD_CHECK_IN, "每日签到领取奖励")
    @player_required
    async def handle_check_in(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        success, msg, updated_player = xiuxian_logic.handle_check_in(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_START_CULTIVATION, "开始闭关修炼")
    @player_required
    async def handle_start_cultivation(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        success, msg, updated_player = xiuxian_logic.handle_start_cultivation(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_END_CULTIVATION, "结束闭关修炼")
    @player_required
    async def handle_end_cultivation(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        success, msg, updated_player = xiuxian_logic.handle_end_cultivation(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)
    
    @filter.command(config.CMD_BREAKTHROUGH, "尝试突破当前境界")
    @player_required
    async def handle_breakthrough(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        if player.state != "空闲":
            yield event.plain_result(f"道友当前正在「{player.state}」中，无法尝试突破。")
            return
        success, msg, updated_player = xiuxian_logic.handle_breakthrough(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_SHOP, "查看坊市商品")
    async def handle_shop(self, event: AstrMessageEvent) -> MessageEventResult:
        reply_msg = "--- 仙途坊市 ---\n"
        for item_id, info in config.item_data.items():
            reply_msg += f"【{info['name']}】售价：{info['price']} 灵石\n"
        reply_msg += "------------------\n"
        reply_msg += f"使用「{config.CMD_BUY} <物品名> [数量]」进行购买。"
        yield event.plain_result(reply_msg)

    @filter.command(config.CMD_BACKPACK, "查看你的背包")
    @player_required
    async def handle_backpack(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        inventory = await data_manager.get_inventory_by_user_id(player.user_id)
        if not inventory:
            yield event.plain_result("道友的背包空空如也。")
            return
        
        reply_msg = f"--- {event.get_sender_name()} 的背包 ---\n"
        for item in inventory:
            reply_msg += f"【{item['name']}】x{item['quantity']} - {item['description']}\n"
        reply_msg += "--------------------------"
        yield event.plain_result(reply_msg)

    @filter.command(config.CMD_BUY, "购买物品")
    @player_required
    async def handle_buy(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        parts = event.message_str.strip().split(maxsplit=2)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_BUY} <物品名> [数量]」。")
            return

        item_name = parts[1]
        quantity = 1
        if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) > 0:
            quantity = int(parts[2])
        
        success, msg, updated_player, item_id_to_add = xiuxian_logic.handle_buy_item(player, item_name, quantity)
        if success:
            await data_manager.update_player(updated_player)
            await data_manager.add_item_to_inventory(player.user_id, item_id_to_add, quantity)
        yield event.plain_result(msg)
        
    @filter.command(config.CMD_USE_ITEM, "使用背包中的物品")
    @player_required
    async def handle_use(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        parts = event.message_str.strip().split(maxsplit=2)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_USE_ITEM} <物品名> [数量]」。")
            return

        item_name = parts[1]
        quantity = 1
        if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) > 0:
            quantity = int(parts[2])

        target_item_id = None
        for item_id, info in config.item_data.items():
            if info['name'] == item_name:
                target_item_id = item_id
                break
        
        if not target_item_id:
            yield event.plain_result(f"背包中似乎没有名为「{item_name}」的物品。")
            return

        if not await data_manager.remove_item_from_inventory(player.user_id, target_item_id, quantity):
             yield event.plain_result(f"你的「{item_name}」数量不足 {quantity} 个！")
             return

        success, msg, updated_player = xiuxian_logic.handle_use_item(player, target_item_id, quantity)
        
        if success:
            await data_manager.update_player(updated_player)

        yield event.plain_result(msg)

    @filter.command(config.CMD_CREATE_SECT, "创建你的宗门")
    @player_required
    async def handle_create_sect(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_CREATE_SECT} <宗门名称>」。")
            return
        
        sect_name = parts[1]
        success, msg, updated_player = await xiuxian_logic.handle_create_sect(player, sect_name)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_JOIN_SECT, "加入一个宗门")
    @player_required
    async def handle_join_sect(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_JOIN_SECT} <宗门名称>」。")
            return
        
        sect_name = parts[1]
        success, msg, updated_player = await xiuxian_logic.handle_join_sect(player, sect_name)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_LEAVE_SECT, "退出当前宗门")
    @player_required
    async def handle_leave_sect(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        success, msg, updated_player = await xiuxian_logic.handle_leave_sect(player)
        if success:
            await data_manager.update_player(updated_player)
        yield event.plain_result(msg)
        
    @filter.command(config.CMD_MY_SECT, "查看我的宗门信息")
    @player_required
    async def handle_my_sect(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        if not player.sect_id:
            yield event.plain_result("道友乃逍遥散人，尚未加入任何宗门。")
            return
            
        sect_info = await data_manager.get_sect_by_id(player.sect_id)
        if not sect_info:
            # 数据自愈，移除玩家失效的宗门信息
            player.sect_id = None
            player.sect_name = None
            await data_manager.update_player(player)
            yield event.plain_result("错误：找不到你的宗门信息，可能已被解散。已将你设为散修。")
            return

        leader_info = f"宗主ID: {sect_info['leader_id']}"
        members = await data_manager.get_sect_members(player.sect_id)
        member_list = [f"{m.level}-{m.user_id[-4:]}" for m in members]

        reply_msg = (
            f"--- {sect_info['name']} (Lv.{sect_info['level']}) ---\n"
            f"{leader_info}\n"
            f"宗门资金：{sect_info['funds']} 灵石\n"
            f"成员 ({len(members)}人):\n"
            f"{' | '.join(member_list)}\n"
            "--------------------------"
        )
        yield event.plain_result(reply_msg)
    
    @filter.command(config.CMD_SPAR, "与其他玩家切磋")
    @player_required
    async def handle_spar(self, event: AstrMessageEvent) -> MessageEventResult:
        attacker: Player = event.player
        
        if attacker.hp < attacker.max_hp:
            yield event.plain_result("你当前气血不满，无法与人切磋，请先恢复。")
            return
        
        mentioned_user_id = None
        if event.at_list:
            mentioned_user_id = event.at_list[0]
        
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

        report, _ = await xiuxian_logic.handle_pvp(attacker, defender)
            
        yield event.plain_result(report)

    @filter.command(config.CMD_START_BOSS_FIGHT, "开启一场世界Boss讨伐战")
    @player_required
    async def handle_start_boss_fight(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_START_BOSS_FIGHT} <Boss名>」。")
            return
            
        boss_name = parts[1]
        target_boss_config = None
        for boss_id, info in config.boss_data.items():
            if info['name'] == boss_name:
                target_boss_config = info
                target_boss_config['id'] = boss_id
                break
        
        if not target_boss_config:
            yield event.plain_result(f"未找到名为【{boss_name}】的Boss。")
            return
            
        success, msg = await self.battle_manager.start_battle(target_boss_config)
        yield event.plain_result(msg)

        if success:
            _, join_msg = await self.battle_manager.add_participant(player)
            await asyncio.sleep(1)
            yield event.plain_result(join_msg)

    @filter.command(config.CMD_JOIN_FIGHT, "加入当前的Boss战")
    @player_required
    async def handle_join_fight(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        success, msg = await self.battle_manager.add_participant(player)
        yield event.plain_result(msg)

    @filter.command(config.CMD_ATTACK_BOSS, "攻击当前的世界Boss")
    @player_required
    async def handle_attack_boss(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        success, msg, battle_over, updated_players = await self.battle_manager.player_attack(player)
        
        yield event.plain_result(msg)
        
        if success:
            for p in updated_players:
                await data_manager.update_player(p)
    
    @filter.command(config.CMD_FIGHT_STATUS, "查看当前战斗状态")
    async def handle_fight_status(self, event: AstrMessageEvent) -> MessageEventResult:
        status_report = self.battle_manager.get_status()
        yield event.plain_result(status_report)

    @filter.command(config.CMD_REALM_LIST, "查看所有可探索的秘境")
    async def handle_realm_list(self, event: AstrMessageEvent) -> MessageEventResult:
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
    async def handle_enter_realm(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        if self.realm_manager.get_session(player.user_id):
            yield event.plain_result(f"你已在秘境【{self.realm_manager.get_session(player.user_id).realm_name}】中！")
            return
            
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result(f"指令格式错误！请使用「{config.CMD_ENTER_REALM} <秘境名>」。")
            return
        
        realm_name = parts[1]
        target_realm_id = None
        for realm_id, info in config.realm_data.items():
            if info['name'] == realm_name:
                target_realm_id = realm_id
                break
        
        if not target_realm_id:
            yield event.plain_result(f"未找到名为【{realm_name}】的秘境。")
            return
            
        success, msg = self.realm_manager.start_session(player, target_realm_id)
        
        if success:
            await data_manager.update_player(player)
            
        yield event.plain_result(msg)
        
    @filter.command(config.CMD_REALM_ADVANCE, "在秘境中前进")
    @player_required
    async def handle_realm_advance(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        session = self.realm_manager.get_session(player.user_id)
        if not session:
            yield event.plain_result("你不在任何秘境中，无法前进。")
            return
            
        success, msg, rewards = await self.realm_manager.advance_session(player)
        
        # 无论成功失败，都需要更新玩家状态（例如HP, 获得的奖励等）
        if rewards:
            player.gold += rewards.get("gold", 0)
            player.experience += rewards.get("experience", 0)
            for item_id, qty in rewards.get("items", {}).items():
                await data_manager.add_item_to_inventory(player.user_id, item_id, qty)

        await data_manager.update_player(player)
        
        yield event.plain_result(msg)

    @filter.command(config.CMD_LEAVE_REALM, "离开当前秘境")
    @player_required
    async def handle_leave_realm(self, event: AstrMessageEvent) -> MessageEventResult:
        player: Player = event.player
        session = self.realm_manager.end_session(player.user_id)
        
        if not session:
            yield event.plain_result("你不在任何秘境中。")
            return
            
        rewards = session.gained_rewards
        player.gold += rewards['gold']
        player.experience += rewards['experience']
        
        reward_log = f"你离开了【{session.realm_name}】，本次探索收获如下：\n"
        reward_log += f" - 灵石: {rewards['gold']}\n"
        reward_log += f" - 修为: {rewards['experience']}\n"
        
        if items := rewards.get('items'):
            reward_log += " - 物品:\n"
            for item_id, qty in items.items():
                await data_manager.add_item_to_inventory(player.user_id, item_id, qty)
                item_name = config.item_data.get(item_id, {}).get("name", "未知物品")
                reward_log += f"   - 【{item_name}】x{qty}\n"
        
        await data_manager.update_player(player)
        yield event.plain_result(reward_log)

    @filter.command(config.CMD_HELP, "显示帮助信息")
    async def handle_help(self, event: AstrMessageEvent) -> MessageEventResult:
        help_text = (
            "--- 寻仙指令手册 ---\n"
            f"【{config.CMD_START_XIUXIAN}】: 开启修仙之旅。\n"
            f"【{config.CMD_PLAYER_INFO}】: 查看人物信息。\n"
            f"【{config.CMD_CHECK_IN}】: 每日签到。\n"
            "--- 修炼与成长 ---\n"
            f"【{config.CMD_START_CULTIVATION}】: 开始闭关。\n"
            f"【{config.CMD_END_CULTIVATION}】: 结束闭关。\n"
            f"【{config.CMD_BREAKTHROUGH}】: 尝试突破境界。\n"
            "--- 坊市与物品 ---\n"
            f"【{config.CMD_SHOP}】: 查看坊市商品。\n"
            f"【{config.CMD_BACKPACK}】: 查看个人背包。\n"
            f"【{config.CMD_BUY} <物品名> [数量]】: 购买物品。\n"
            f"【{config.CMD_USE_ITEM} <物品名> [数量]】: 使用物品。\n"
            "--- 宗门社交 ---\n"
            f"【{config.CMD_CREATE_SECT} <名称>】: 创建宗门。\n"
            f"【{config.CMD_JOIN_SECT} <名称>】: 加入宗门。\n"
            f"【{config.CMD_MY_SECT}】: 查看宗门信息。\n"
            f"【{config.CMD_LEAVE_SECT}】: 退出宗门。\n"
            "--- PVE/PVP ---\n"
            f"【{config.CMD_SPAR} @某人】: 与其他玩家切磋。\n"
            f"【{config.CMD_START_BOSS_FIGHT} <名称>】: 开启世界Boss讨伐。\n"
            f"【{config.CMD_JOIN_FIGHT}】: 加入当前的世界Boss战。\n"
            f"【{config.CMD_ATTACK_BOSS}】: 攻击世界Boss。\n"
            f"【{config.CMD_FIGHT_STATUS}】: 查看世界Boss战况。\n"
            f"【{config.CMD_REALM_LIST}】: 查看可探索的秘境。\n"
            f"【{config.CMD_ENTER_REALM} <名称>】: 进入秘境探索。\n"
            f"【{config.CMD_REALM_ADVANCE}】: 在秘境中前进一层。\n"
            f"【{config.CMD_LEAVE_REALM}】: 离开秘境并结算奖励。\n"
            "--------------------"
        )
        yield event.plain_result(help_text)

    async def terminate(self):
        """插件卸载/停用时调用，关闭数据库连接池。"""
        await data_manager.close_db_pool()
        logger.info("修仙插件已卸载。")