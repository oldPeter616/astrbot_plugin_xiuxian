# config_manager.py
# 负责读取和解析 config.txt 文件

from pathlib import Path
# 修改点：导入 logger
from astrbot.api import logger

class Config:
    def __init__(self, config_file: Path):
        # 设置默认值
        self.CMD_START_XIUXIAN = "我要修仙"
        self.CMD_PLAYER_INFO = "我的信息"
        self.CMD_CHECK_IN = "签到"
        self.INITIAL_GOLD = 100
        self.CHECK_IN_REWARD_MIN = 50
        self.CHECK_IN_REWARD_MAX = 200
        self.DATABASE_FILE = "xiuxian_data.db"
        
        self._load_config(config_file)

    def _load_config(self, config_file: Path):
        if not config_file.exists():
            # 修改点：使用 logger 记录警告
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
                
                if value.isdigit():
                    setattr(self, key, int(value))
                else:
                    setattr(self, key, value)

CONFIG_PATH = Path(__file__).parent / "config.txt"
config = Config(CONFIG_PATH)