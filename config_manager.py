# config_manager.py

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

from astrbot.api import logger
from .models import Item

class Config:
    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        self._paths = {
            "config": base_dir / "config" / "config.json",
            "level": base_dir / "config" / "level_config.json",
            "item": base_dir / "config" / "items.json",
            "boss": base_dir / "config" / "bosses.json",
            "monster": base_dir / "config" / "monsters.json",
            "realm": base_dir / "config" / "realms.json",
            "tag": base_dir / "config" / "tags.json"
        }

        self.level_data: List[dict] = []
        self.item_data: Dict[str, Item] = {}
        self.boss_data: Dict[str, dict] = {}
        self.monster_data: Dict[str, dict] = {}
        self.realm_data: Dict[str, dict] = {}
        self.tag_data: Dict[str, dict] = {}

        self.level_map: Dict[str, dict] = {}
        self.item_name_to_id: Dict[str, str] = {}
        self.realm_name_to_id: Dict[str, str] = {}
        self.boss_name_to_id: Dict[str, str] = {}

        # --- 可配置属性 (带默认值) ---
        self.CMD_BOSS_LIST = "查看世界boss"
        self.CMD_FIGHT_BOSS = "讨伐boss"
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
        self.CMD_ENTER_REALM = "探索秘境"
        self.CMD_REALM_ADVANCE = "前进"
        self.CMD_LEAVE_REALM = "离开秘境"
        self.CMD_HELP = "修仙帮助"

        self.INITIAL_GOLD = 100
        self.CHECK_IN_REWARD_MIN = 50
        self.CHECK_IN_REWARD_MAX = 200
        self.BASE_EXP_PER_MINUTE = 10
        self.BREAKTHROUGH_FAIL_PUNISHMENT_RATIO = 0.1
        self.CREATE_SECT_COST = 5000
        self.WORLD_BOSS_TOP_PLAYERS_AVG = 3
        self.REALM_BASE_FLOORS = 3
        self.REALM_FLOORS_PER_LEVEL_DIVISOR = 2
        self.REALM_MONSTER_CHANCE = 0.7

        self.POSSIBLE_SPIRITUAL_ROOTS: List[str] = ["金", "木", "水", "火", "土"]

        self.DATABASE_FILE = "xiuxian_data.db"

        self._load_all()

    def _load_json_data(self, file_path: Path) -> Any:
        if not file_path.exists():
            logger.warning(f"配置文件 {file_path} 不存在，将使用默认值。")
            return {} if file_path.suffix == '.json' else []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"成功加载 {file_path.name} (共 {len(data)} 条数据)。")
                return data
        except Exception as e:
            logger.error(f"加载配置文件 {file_path} 失败: {e}")
            return {} if file_path.suffix == '.json' else []

    def _load_all(self):
        """加载所有配置文件并进行后处理"""
        if self._paths["config"].exists():
            try:
                with open(self._paths["config"], 'r', encoding='utf-8') as f:
                    main_cfg = json.load(f)

                for category_name, category_data in main_cfg.items():
                    if isinstance(category_data, dict):
                        for key, value in category_data.items():
                            if hasattr(self, key):
                                setattr(self, key, value)
                logger.info("成功加载主配置文件 config.json。")
            except Exception as e:
                logger.error(f"加载主配置文件 config.json 失败: {e}")

        self.level_data = self._load_json_data(self._paths["level"])
        raw_item_data = self._load_json_data(self._paths["item"])
        self.boss_data = self._load_json_data(self._paths["boss"])
        self.monster_data = self._load_json_data(self._paths["monster"])
        self.realm_data = self._load_json_data(self._paths["realm"])
        self.tag_data = self._load_json_data(self._paths["tag"])

        self.level_map = {info["level_name"]: {"index": i, **info}
                          for i, info in enumerate(self.level_data) if "level_name" in info}

        self.item_data = {}
        self.item_name_to_id = {}
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
        return (item_id, self.item_data[item_id]) if item_id and item_id in self.item_data else None

    def get_realm_by_name(self, name: str) -> Optional[Tuple[str, dict]]:
        realm_id = self.realm_name_to_id.get(name)
        return (realm_id, self.realm_data[realm_id]) if realm_id else None

    def get_boss_by_name(self, name: str) -> Optional[Tuple[str, dict]]:
        boss_id = self.boss_name_to_id.get(name)
        return (boss_id, self.boss_data[boss_id]) if boss_id else None

_current_dir = Path(__file__).parent
config = Config(_current_dir)