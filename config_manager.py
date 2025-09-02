# config_manager.py
# 负责读取和解析配置文件

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from astrbot.api import logger

class Config:
    def __init__(self, base_dir: Path):
        # --- 文件路径定义 ---
        self._base_dir = base_dir
        self._paths = {
            "config": base_dir / "config.json",
            "level": base_dir / "level_config.json",
            "item": base_dir / "items.json",
            "boss": base_dir / "bosses.json",
            "monster": base_dir / "monsters.json",
            "realm": base_dir / "realms.json"
        }

        # --- 配置数据容器 ---
        self.level_data: list = []
        self.item_data: dict = {}
        self.boss_data: dict = {}
        self.monster_data: dict = {}
        self.realm_data: dict = {}
        self.level_map: dict = {}
        self.realm_events: Dict[str, Dict[str, list]] = {}

        # --- 用于性能优化的名称到ID映射 ---
        self.item_name_to_id: Dict[str, str] = {}
        self.realm_name_to_id: Dict[str, str] = {}

        self._set_defaults()

    def _set_defaults(self):
        """设置所有配置的默认值"""
        # 指令
        self.CMD_START_XIUXIAN = "我要修仙"
        self.CMD_PLAYER_INFO = "我的信息"
        self.CMD_CHECK_IN = "签到"
        self.CMD_START_CULTIVATION = "闭关"
        self.CMD_END_CULTIVATION = "出关"
        self.CMD_BREAKTHROUGH = "突破"
        self.CMD_SHOP = "商店"
        self.CMD_BUY = "购买"
        self.CMD_BACKPACK = "我的背包"
        self.CMD_CREATE_SECT = "创建宗门"
        self.CMD_JOIN_SECT = "加入宗门"
        self.CMD_MY_SECT = "我的宗门"
        self.CMD_LEAVE_SECT = "退出宗门"
        self.CMD_USE_ITEM = "使用"
        self.CMD_SPAR = "切磋"
        self.CMD_START_BOSS_FIGHT = "讨伐"
        self.CMD_JOIN_FIGHT = "加入战斗"
        self.CMD_ATTACK_BOSS = "攻击"
        self.CMD_FIGHT_STATUS = "战斗状态"
        self.CMD_REALM_LIST = "秘境列表"
        self.CMD_ENTER_REALM = "探索秘境"
        self.CMD_REALM_ADVANCE = "前进"
        self.CMD_LEAVE_REALM = "离开秘境"
        self.CMD_HELP = "修仙帮助"
        
        # 数值
        self.INITIAL_GOLD = 100
        self.CHECK_IN_REWARD_MIN = 50
        self.CHECK_IN_REWARD_MAX = 200
        self.BASE_EXP_PER_MINUTE = 10
        self.BREAKTHROUGH_FAIL_PUNISHMENT_RATIO = 0.1
        self.CREATE_SECT_COST = 5000
        
        # 文件
        self.DATABASE_FILE = "xiuxian_data.db"

    def _load_json_config(self, file_path: Path, attribute_name: str, log_name: str) -> bool:
        """通用JSON配置文件加载器"""
        if not file_path.exists():
            logger.warning(f"{log_name}配置文件 {file_path} 不存在，跳过加载。")
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                setattr(self, attribute_name, data)
                logger.info(f"成功加载 {len(data)} 条 {log_name} 配置。")
                return True
        except json.JSONDecodeError as e:
            logger.error(f"加载{log_name}配置文件 {file_path} 失败：JSON格式错误 - {e}")
        except Exception as e:
            logger.error(f"加载{log_name}配置文件 {file_path} 时发生未知错误: {e}")
        return False

    def load(self):
        """显式加载所有配置文件并进行后处理"""
        if self._load_json_config(self._paths["config"], "main_config", "主"):
            main_cfg = getattr(self, "main_config")
            # 将 COMMANDS, VALUES, FILES 类别下的所有键值对设置为 config 对象的属性
            for category in ("COMMANDS", "VALUES", "FILES"):
                if category in main_cfg:
                    for key, value in main_cfg[category].items():
                        setattr(self, key, value)

        # 加载其他数据文件
        self._load_json_config(self._paths["level"], "level_data", "境界")
        self._load_json_config(self._paths["item"], "item_data", "物品")
        self._load_json_config(self._paths["boss"], "boss_data", "Boss")
        self._load_json_config(self._paths["monster"], "monster_data", "怪物")
        self._load_json_config(self._paths["realm"], "realm_data", "秘境")

        # --- 数据后处理，建立映射以优化性能 ---
        self._post_process_level_data()
        self._post_process_realm_data()
        self._post_process_item_data()

    def _post_process_level_data(self):
        """预处理境界数据"""
        for i, level_info in enumerate(self.level_data):
            if level_name := level_info.get("level_name"):
                self.level_map[level_name] = {"index": i, **level_info}

    def _post_process_item_data(self):
        """预处理物品数据，建立名称到ID的映射"""
        for item_id, info in self.item_data.items():
            if name := info.get("name"):
                self.item_name_to_id[name] = item_id
    
    def _post_process_realm_data(self):
        """预处理秘境数据，建立事件池和名称映射"""
        for realm_id, realm_info in self.realm_data.items():
            if name := realm_info.get("name"):
                self.realm_name_to_id[name] = realm_id
            
            self.realm_events[realm_id] = {'monster': [], 'treasure': []}
            for event in realm_info.get("events", []):
                if event_type := event.get('type'):
                    if event_type in self.realm_events[realm_id]:
                        self.realm_events[realm_id][event_type].append(event)

    def get_item_by_name(self, name: str) -> Optional[Tuple[str, dict]]:
        """根据名称高效查找物品"""
        item_id = self.item_name_to_id.get(name)
        if item_id:
            return item_id, self.item_data.get(item_id)
        return None

    def get_realm_by_name(self, name: str) -> Optional[Tuple[str, dict]]:
        """根据名称高效查找秘境"""
        realm_id = self.realm_name_to_id.get(name)
        if realm_id:
            return realm_id, self.realm_data.get(realm_id)
        return None

# 全局配置实例
_current_dir = Path(__file__).parent
config = Config(_current_dir)