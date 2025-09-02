# config_manager.py
# 负责读取和解析配置文件

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

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

        # --- 数据容器 (显式声明) ---
        self.level_data: List[dict] = []
        self.item_data: Dict[str, dict] = {}
        self.boss_data: Dict[str, dict] = {}
        self.monster_data: Dict[str, dict] = {}
        self.realm_data: Dict[str, dict] = {}
        
        # --- 预处理数据容器 (显式声明) ---
        self.level_map: Dict[str, dict] = {}
        self.realm_events: Dict[str, Dict[str, list]] = {}
        self.item_name_to_id: Dict[str, str] = {}
        self.realm_name_to_id: Dict[str, str] = {}

        # --- 可配置属性 (显式声明并设置默认值) ---
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
        
        # 游戏规则
        self.POSSIBLE_SPIRITUAL_ROOTS: List[str] = ["金", "木", "水", "火", "土"]

        # 文件
        self.DATABASE_FILE = "xiuxian_data.db"

    def _load_json_data(self, file_path: Path, attribute_name: str, log_name: str) -> bool:
        """通用JSON数据文件加载器"""
        if not file_path.exists():
            logger.warning(f"{log_name}数据文件 {file_path} 不存在，跳过加载。")
            setattr(self, attribute_name, {}) # 确保属性存在
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                setattr(self, attribute_name, data)
                logger.info(f"成功加载 {len(data)} 条 {log_name} 数据。")
                return True
        except json.JSONDecodeError as e:
            logger.error(f"加载{log_name}数据文件 {file_path} 失败：JSON格式错误 - {e}")
        except Exception as e:
            logger.error(f"加载{log_name}数据文件 {file_path} 时发生未知错误: {e}")
        return False

    def load(self):
        """显式加载所有配置文件并进行后处理"""
        # 加载主配置文件
        if self._paths["config"].exists():
            try:
                with open(self._paths["config"], 'r', encoding='utf-8') as f:
                    main_cfg = json.load(f)
                
                # 安全地更新已声明的属性
                for category in ("COMMANDS", "VALUES", "FILES", "RULES"):
                    if category in main_cfg:
                        for key, value in main_cfg[category].items():
                            if hasattr(self, key):
                                setattr(self, key, value)
                            else:
                                logger.warning(f"主配置文件中的未知配置项 '{key}' 将被忽略。")
                logger.info("成功加载主配置文件 config.json。")
            except Exception as e:
                logger.error(f"加载主配置文件 config.json 失败: {e}")

        # 加载其他数据文件
        self._load_json_data(self._paths["level"], "level_data", "境界")
        self._load_json_data(self._paths["item"], "item_data", "物品")
        self._load_json_data(self._paths["boss"], "boss_data", "Boss")
        self._load_json_data(self._paths["monster"], "monster_data", "怪物")
        self._load_json_data(self._paths["realm"], "realm_data", "秘境")

        # 数据后处理
        self._post_process_data()

    def _post_process_data(self):
        """预处理所有数据，建立映射以优化性能"""
        # 境界数据
        for i, level_info in enumerate(self.level_data):
            if level_name := level_info.get("level_name"):
                self.level_map[level_name] = {"index": i, **level_info}
        # 物品数据
        for item_id, info in self.item_data.items():
            if name := info.get("name"):
                self.item_name_to_id[name] = item_id
        # 秘境数据
        for realm_id, realm_info in self.realm_data.items():
            if name := realm_info.get("name"):
                self.realm_name_to_id[name] = realm_id
            
            self.realm_events[realm_id] = {'monster': [], 'treasure': []}
            for event in realm_info.get("events", []):
                if event_type := event.get('type'):
                    if event_type in self.realm_events[realm_id]:
                        self.realm_events[realm_id][event_type].append(event)

    def get_item_by_name(self, name: str) -> Optional[Tuple[str, dict]]:
        item_id = self.item_name_to_id.get(name)
        return (item_id, self.item_data.get(item_id)) if item_id else None

    def get_realm_by_name(self, name: str) -> Optional[Tuple[str, dict]]:
        realm_id = self.realm_name_to_id.get(name)
        return (realm_id, self.realm_data.get(realm_id)) if realm_id else None

# 全局配置实例
_current_dir = Path(__file__).parent
config = Config(_current_dir)