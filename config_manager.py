# config_manager.py
# 负责读取和解析配置文件

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

from astrbot.api import logger
from .models import Item

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
            "realm": base_dir / "realms.json",
            "tag": base_dir / "tags.json"
        }

        # --- 数据容器 ---
        self.level_data: List[dict] = []
        self.item_data: Dict[str, Item] = {}
        self.boss_data: Dict[str, dict] = {}
        self.monster_data: Dict[str, dict] = {}
        self.realm_data: Dict[str, dict] = {}
        self.tag_data: Dict[str, dict] = {}

        # --- 预处理数据映射 ---
        self.level_map: Dict[str, dict] = {}
        self.item_name_to_id: Dict[str, str] = {}
        self.realm_name_to_id: Dict[str, str] = {}
        self.boss_name_to_id: Dict[str, str] = {}

        # --- 可配置属性 (带默认值) ---
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
        self.CMD_WORLD_BOSS = "讨伐世界boss"  # 新增此处的默认声明
        self.CMD_ATTACK_BOSS = "攻击"
        self.CMD_FIGHT_STATUS = "战斗状态"
        self.CMD_REALM_LIST = "秘境列表"
        self.CMD_ENTER_REALM = "探索秘境"
        self.CMD_REALM_ADVANCE = "前进"
        self.CMD_LEAVE_REALM = "离开秘境"
        self.CMD_HELP = "修仙帮助"
        self.CMD_JOIN_FIGHT = "加入战斗" # 为兼容旧配置保留

        # 数值
        self.INITIAL_GOLD = 100
        self.CHECK_IN_REWARD_MIN = 50
        self.CHECK_IN_REWARD_MAX = 200
        self.BASE_EXP_PER_MINUTE = 10
        self.BREAKTHROUGH_FAIL_PUNISHMENT_RATIO = 0.1
        self.CREATE_SECT_COST = 5000
        self.WORLD_BOSS_TEMPLATE_ID = "1"
        self.WORLD_BOSS_TOP_PLAYERS_AVG = 5

        # 游戏规则
        self.POSSIBLE_SPIRITUAL_ROOTS: List[str] = ["金", "木", "水", "火", "土"]

        # 文件
        self.DATABASE_FILE = "xiuxian_data.db"

    def _load_json_data(self, file_path: Path, attribute_name: str, log_name: str) -> bool:
        if not file_path.exists():
            logger.warning(f"{log_name}数据文件 {file_path} 不存在，将使用默认值。")
            setattr(self, attribute_name, {} if 'data' in attribute_name else [])
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                setattr(self, attribute_name, data)
                logger.info(f"成功加载 {len(data)} 条 {log_name} 数据。")
                return True
        except Exception as e:
            logger.error(f"加载 {log_name} 数据文件 {file_path} 失败: {e}")
        return False

    def load(self):
        """加载所有配置文件并进行后处理"""
        if self._paths["config"].exists():
            try:
                with open(self._paths["config"], 'r', encoding='utf-8') as f:
                    main_cfg = json.load(f)

                # 遍历所有分类，安全地更新属性
                for category_name, category_data in main_cfg.items():
                    if isinstance(category_data, dict):
                        for key, value in category_data.items():
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
        self._load_json_data(self._paths["tag"], "tag_data", "标签")

        self._post_process_data()

    def _post_process_data(self):
        """预处理所有数据，建立名称到ID的映射以优化性能"""
        self.level_map = {info["level_name"]: {"index": i, **info}
                          for i, info in enumerate(self.level_data) if "level_name" in info}

        raw_item_data = self.item_data
        self.item_data = {}
        for item_id, info in raw_item_data.items():
            try:
                self.item_data[item_id] = Item(id=item_id, **info)
                if "name" in info:
                    self.item_name_to_id[info["name"]] = item_id
            except TypeError as e:
                logger.error(f"加载物品 {item_id} 失败，配置项不匹配: {e}")

        self.realm_name_to_id = {info["name"]: realm_id
                                 for realm_id, info in self.realm_data.items() if "name" in info}
        self.boss_name_to_id = {info["name"]: boss_id
                                for boss_id, info in self.boss_data.items() if "name" in info}

    def get_item_by_name(self, name: str) -> Optional[Tuple[str, Item]]:
        item_id = self.item_name_to_id.get(name)
        return (item_id, self.item_data[item_id]) if item_id else None

    def get_realm_by_name(self, name: str) -> Optional[Tuple[str, dict]]:
        realm_id = self.realm_name_to_id.get(name)
        return (realm_id, self.realm_data[realm_id]) if realm_id else None

    def get_boss_by_name(self, name: str) -> Optional[Tuple[str, dict]]:
        boss_id = self.boss_name_to_id.get(name)
        return (boss_id, self.boss_data[boss_id]) if boss_id else None

_current_dir = Path(__file__).parent
config = Config(_current_dir)