# config_manager.py
# 负责读取和解析配置文件

import json
from pathlib import Path
from astrbot.api import logger

class Config:
    def __init__(self, config_file: Path, level_config_file: Path, item_config_file: Path, boss_config_file: Path, monster_config_file: Path, realm_config_file: Path):
        # 存放配置数据
        self.level_data = []
        self.item_data = {}
        self.boss_data = {}
        self.monster_data = {}
        self.realm_data = {}
        self.level_map = {}
        # 预处理后的秘境事件
        self.realm_events: Dict[str, Dict[str, list]] = {}

        # 保存路径以供加载时使用
        self._paths = {
            "config": config_file, "level": level_config_file, "item": item_config_file,
            "boss": boss_config_file, "monster": monster_config_file, "realm": realm_config_file
        }

        # --- 配置白名单 ---
        self.ALLOWED_KEYS = {
            'CMD_START_XIUXIAN', 'CMD_PLAYER_INFO', 'CMD_CHECK_IN', 'CMD_START_CULTIVATION',
            'CMD_END_CULTIVATION', 'CMD_BREAKTHROUGH', 'CMD_SHOP', 'CMD_BUY', 'CMD_BACKPACK',
            'CMD_CREATE_SECT', 'CMD_JOIN_SECT', 'CMD_MY_SECT', 'CMD_LEAVE_SECT', 'CMD_USE_ITEM',
            'CMD_SPAR', 'CMD_START_BOSS_FIGHT', 'CMD_JOIN_FIGHT', 'CMD_ATTACK_BOSS',
            'CMD_FIGHT_STATUS', 'CMD_REALM_LIST', 'CMD_ENTER_REALM', 'CMD_REALM_ADVANCE',
            'CMD_LEAVE_REALM', 'CMD_HELP',
            'INITIAL_GOLD', 'CHECK_IN_REWARD_MIN', 'CHECK_IN_REWARD_MAX', 'BASE_EXP_PER_MINUTE',
            'BREAKTHROUGH_FAIL_PUNISHMENT_RATIO', 'CREATE_SECT_COST', 'DATABASE_FILE'
        }

        # 设置默认值
        self._set_defaults()

    def _set_defaults(self):
        """设置所有配置的默认值"""
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
        self.INITIAL_GOLD = 100
        self.CHECK_IN_REWARD_MIN = 50
        self.CHECK_IN_REWARD_MAX = 200
        self.BASE_EXP_PER_MINUTE = 10
        self.BREAKTHROUGH_FAIL_PUNISHMENT_RATIO = 0.1
        self.CREATE_SECT_COST = 5000
        self.DATABASE_FILE = "xiuxian_data.db"
    
    def load(self):
        """显式加载所有配置文件"""
        self._load_config(self._paths["config"])
        self._load_level_config(self._paths["level"])
        self._load_item_config(self._paths["item"])
        self._load_boss_config(self._paths["boss"])
        self._load_monster_config(self._paths["monster"])
        self._load_realm_config(self._paths["realm"])

    def _load_config(self, config_file: Path):
        logger.info("建议：为了更好的扩展性和健壮性，未来可考虑将 config.txt 迁移至 JSON 或 TOML 格式。")
        if not config_file.exists():
            logger.warning(f"配置文件 {config_file} 不存在，将使用默认设置。")
            return

        with open(config_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('=', 1)
                if len(parts) != 2:
                    continue
                
                key = parts[0].strip()
                value_str = parts[1].strip()

                if key not in self.ALLOWED_KEYS:
                    logger.warning(f"配置文件 {config_file.name} 第 {line_num} 行发现未知配置项 '{key}'，已忽略。")
                    continue

                final_value = None
                try:
                    final_value = int(value_str)
                except ValueError:
                    try:
                        final_value = float(value_str)
                    except ValueError:
                        final_value = value_str
                
                setattr(self, key, final_value)

    def _load_level_config(self, level_config_file: Path):
        if not level_config_file.exists(): return
        try:
            with open(level_config_file, 'r', encoding='utf-8') as f:
                self.level_data = json.load(f)
            
            for i, level_info in enumerate(self.level_data):
                if level_name := level_info.get("level_name"):
                    self.level_map[level_name] = {"index": i, **level_info}
            
            logger.info(f"成功加载并预处理 {len(self.level_data)} 条境界配置。")
        except json.JSONDecodeError as e:
            logger.error(f"加载境界配置文件 {level_config_file} 失败：JSON格式错误 - {e}")
        except Exception as e:
            logger.error(f"加载境界配置文件 {level_config_file} 时发生未知错误: {e}")

    def _load_item_config(self, item_config_file: Path):
        if not item_config_file.exists(): return
        try:
            with open(item_config_file, 'r', encoding='utf-8') as f:
                self.item_data = json.load(f)
            logger.info(f"成功加载 {len(self.item_data)} 条物品配置。")
        except json.JSONDecodeError as e:
            logger.error(f"加载物品配置文件 {item_config_file} 失败：JSON格式错误 - {e}")
        except Exception as e:
            logger.error(f"加载物品配置文件 {item_config_file} 时发生未知错误: {e}")

    def _load_boss_config(self, boss_config_file: Path):
        if not boss_config_file.exists(): return
        try:
            with open(boss_config_file, 'r', encoding='utf-8') as f:
                self.boss_data = json.load(f)
            logger.info(f"成功加载 {len(self.boss_data)} 条Boss配置。")
        except json.JSONDecodeError as e:
            logger.error(f"加载Boss配置文件 {boss_config_file} 失败：JSON格式错误 - {e}")
        except Exception as e:
            logger.error(f"加载Boss配置文件 {boss_config_file} 时发生未知错误: {e}")
    
    def _load_monster_config(self, monster_config_file: Path):
        if not monster_config_file.exists(): return
        try:
            with open(monster_config_file, 'r', encoding='utf-8') as f:
                self.monster_data = json.load(f)
            logger.info(f"成功加载 {len(self.monster_data)} 条怪物配置。")
        except json.JSONDecodeError as e:
            logger.error(f"加载怪物配置文件 {monster_config_file} 失败：JSON格式错误 - {e}")
        except Exception as e:
            logger.error(f"加载怪物配置文件 {monster_config_file} 时发生未知错误: {e}")

    def _load_realm_config(self, realm_config_file: Path):
        if not realm_config_file.exists(): return
        try:
            with open(realm_config_file, 'r', encoding='utf-8') as f:
                self.realm_data = json.load(f)

            # 预处理秘境事件
            for realm_id, realm_info in self.realm_data.items():
                self.realm_events[realm_id] = {'monster': [], 'treasure': []}
                for event in realm_info.get("events", []):
                    if event['type'] in self.realm_events[realm_id]:
                        self.realm_events[realm_id][event['type']].append(event)
            
            logger.info(f"成功加载并预处理 {len(self.realm_data)} 条秘境配置。")
        except json.JSONDecodeError as e:
            logger.error(f"加载秘境配置文件 {realm_config_file} 失败：JSON格式错误 - {e}")
        except Exception as e:
            logger.error(f"加载秘境配置文件 {realm_config_file} 时发生未知错误: {e}")

# 路径定义
_current_dir = Path(__file__).parent
CONFIG_PATH = _current_dir / "config.txt"
LEVEL_CONFIG_PATH = _current_dir / "level_config.json"
ITEM_CONFIG_PATH = _current_dir / "items.json"
BOSS_CONFIG_PATH = _current_dir / "bosses.json"
MONSTER_CONFIG_PATH = _current_dir / "monsters.json"
REALM_CONFIG_PATH = _current_dir / "realms.json"

# 实例化时传入所有路径
config = Config(CONFIG_PATH, LEVEL_CONFIG_PATH, ITEM_CONFIG_PATH, BOSS_CONFIG_PATH, MONSTER_CONFIG_PATH, REALM_CONFIG_PATH)