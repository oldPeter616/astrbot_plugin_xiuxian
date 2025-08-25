# config_manager.py
# 负责读取和解析配置文件

import json
from pathlib import Path
from astrbot.api import logger

class Config:
    def __init__(self, config_file: Path, level_config_file: Path, item_config_file: Path):
        # 存放配置数据
        self.level_data = []
        self.item_data = {}

        # 设置默认值
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
        self.CMD_HELP = "修仙帮助"
        
        self.INITIAL_GOLD = 100
        self.CHECK_IN_REWARD_MIN = 50
        self.CHECK_IN_REWARD_MAX = 200
        self.BASE_EXP_PER_MINUTE = 10
        self.BREAKTHROUGH_FAIL_PUNISHMENT_RATIO = 0.1
        self.CREATE_SECT_COST = 5000
        
        self.DATABASE_FILE = "xiuxian_data.db"
        
        self._load_config(config_file)
        self._load_level_config(level_config_file)
        self._load_item_config(item_config_file)

    def _load_item_config(self, item_config_file: Path):
        if not item_config_file.exists():
            logger.error(f"物品配置文件 {item_config_file} 不存在！请创建它。")
            return
        
        try:
            with open(item_config_file, 'r', encoding='utf-8') as f:
                self.item_data = json.load(f)
            logger.info(f"成功加载 {len(self.item_data)} 条物品配置。")
        except Exception as e:
            logger.error(f"加载物品配置文件 {item_config_file} 失败: {e}")

    def _load_level_config(self, level_config_file: Path):
        if not level_config_file.exists():
            logger.error(f"境界配置文件 {level_config_file} 不存在！请创建它。")
            return
        
        try:
            with open(level_config_file, 'r', encoding='utf-8') as f:
                self.level_data = json.load(f)
            logger.info(f"成功加载 {len(self.level_data)} 条境界配置。")
        except Exception as e:
            logger.error(f"加载境界配置文件 {level_config_file} 失败: {e}")

    def _load_config(self, config_file: Path):
        if not config_file.exists():
            logger.warning(f"配置文件 {config_file} 不存在，将使用默认设置。")
            return

        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('=', 1)
                if len(parts) != 2:
                    continue
                
                key = parts[0].strip()
                value = parts[1].strip()
                
                try:
                    if '.' in value:
                        setattr(self, key, float(value))
                    else:
                        setattr(self, key, int(value))
                except ValueError:
                    setattr(self, key, value)

# 路径定义
_current_dir = Path(__file__).parent
CONFIG_PATH = _current_dir / "config.txt"
LEVEL_CONFIG_PATH = _current_dir / "level_config.json"
ITEM_CONFIG_PATH = _current_dir / "items.json"

# 实例化
config = Config(CONFIG_PATH, LEVEL_CONFIG_PATH, ITEM_CONFIG_PATH)