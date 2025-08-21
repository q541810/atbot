import os
import toml
from dotenv import load_dotenv
from typing import Dict, Any, Optional

class ConfigManager:
    """配置管理器，用于读取和管理所有配置文件"""
    
    def __init__(self, config_dir: str = None):
        """初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为当前脚本所在目录
        """
        if config_dir is None:
            config_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.config_dir = config_dir
        self.env_file = os.path.join(config_dir, '.env')
        self.bot_config_file = os.path.join(config_dir, 'bot_config.toml')
        
        # 存储配置数据
        self.env_config = {}
        self.bot_config = {}
        self.reply_models = {}
        
        # 加载所有配置
        self._load_all_configs()
    
    def _load_all_configs(self):
        """加载所有配置文件"""
        self._load_env_config()
        self._load_bot_config()
        self._parse_reply_models()
    
    def _load_env_config(self):
        """加载.env文件配置"""
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
        else:
            print(f"警告: .env文件不存在: {self.env_file}")
    
    def _load_bot_config(self):
        """加载bot_config.toml文件配置"""
        if os.path.exists(self.bot_config_file):
            try:
                with open(self.bot_config_file, 'r', encoding='utf-8') as f:
                    self.bot_config = toml.load(f)
            except Exception as e:
                print(f"错误: 无法读取bot_config.toml文件: {e}")
                self.bot_config = {}
        else:
            print(f"警告: bot_config.toml文件不存在: {self.bot_config_file}")
    
    def _parse_reply_models(self):
        """解析回复模型配置，优先从bot_config.toml读取，其次从环境变量读取"""
        # 优先从bot_config.toml读取
        if 'reply_model' in self.bot_config:
            self.reply_models['reply_model'] = self.bot_config['reply_model']
        else:
            # 回退到从环境变量读取
            for key, value in os.environ.items():
                if key.startswith('REPLY_MODEL_'):
                    parts = key.split('_')
                    if len(parts) >= 3 and parts[2].isdigit(): # REPLY_MODEL_N_NAME, REPLY_MODEL_N_PROVIDER, etc.
                        model_index = parts[2]
                        model_key = '_'.join(parts[3:]).lower() # name, provider, pri_in, pri_out, temp
                        model_name = f"reply_model{model_index}"
                        
                        if model_name not in self.reply_models:
                            self.reply_models[model_name] = {}
                        
                        try:
                            if model_key in ['pri_in', 'pri_out']:
                                self.reply_models[model_name][model_key] = int(value)
                            elif model_key == 'temp':
                                self.reply_models[model_name][model_key] = float(value)
                            else:
                                self.reply_models[model_name][model_key] = value
                        except ValueError:
                            self.reply_models[model_name][model_key] = value

    def get_api_key(self, provider: str) -> str:
        """获取指定提供商的API密钥"""
        # 优先从bot_config.toml中获取
        if 'api_keys' in self.bot_config and provider.upper() in self.bot_config['api_keys']:
            return self.bot_config['api_keys'][provider.upper()]
        # 回退到从环境变量获取
        return os.getenv(f'{provider.upper()}_KEY', '')
    
    def get_base_url(self, provider: str) -> str:
        """获取指定提供商的基础URL"""
        # 优先从bot_config.toml中获取
        if 'base_urls' in self.bot_config and provider.upper() in self.bot_config['base_urls']:
            return self.bot_config['base_urls'][provider.upper()]
        # 回退到从环境变量获取
        return os.getenv(f'{provider.upper()}_BASE_URL', '')


    
    def get_bot_info(self) -> Dict[str, Any]:
        """获取机器人基本信息"""
        return self.bot_config.get('bot', {})
    
    def get_personality(self) -> Dict[str, Any]:
        """获取机器人人格配置"""
        return self.bot_config.get('personality', {})
    
    def get_context_memory_config(self):
        """获取上下文记忆配置"""
        return self.bot_config.get('context_memory', {
            'max_messages': 10,
            'max_message_length': 300,
            'enabled': True
        })
    
    def get_whitelist_config(self):
        """获取群聊白名单配置"""
        return self.bot_config.get('whitelist', {
            'group_ids': []
        })
    
    def get_reply_config(self):
        """获取智能回复配置"""
        bot_section = self.bot_config.get('bot', {})
        return {
            'reply_probability': bot_section.get('reply_probability', 20),
            'reply_messagelength': bot_section.get('reply_messagelength', 5),
            'reply_messagetime': bot_section.get('reply_messagetime', 4)
        }
    
    def get_estimate_model_config(self):
        """获取判断模型配置"""
        estimate_config = self.bot_config.get('estimate_model', {})
        if estimate_config:
            provider = estimate_config.get('provider', '')
            return {
                'name': estimate_config.get('name', ''),
                'provider': provider,
                'key': self.get_api_key(provider),
                'url': self.get_base_url(provider),
                'pri_in': estimate_config.get('pri_in', 0),
                'pri_out': estimate_config.get('pri_out', 0),
                'temp': estimate_config.get('temp', 0.2)
            }
        return {}
    

    
    def get_reply_model(self, model_name: str = 'reply_model') -> Dict[str, Any]:
        """获取回复模型配置"""
        model_config = self.reply_models.get(model_name, {})
        if model_config:
            provider = model_config.get('provider', '')
            return {
                'name': model_config.get('name', ''),
                'provider': provider,
                'key': self.get_api_key(provider),
                'url': self.get_base_url(provider),
                'pri_in': model_config.get('pri_in', 0), # 默认值
                'pri_out': model_config.get('pri_out', 0), # 默认值
                'temp': model_config.get('temp', 0.0) # 默认值
            }
        return {}
    
    def get_all_reply_models(self) -> Dict[str, Dict[str, Any]]:
        """获取所有回复模型配置"""
        result = {}
        for model_name in self.reply_models:
            result[model_name] = self.get_reply_model(model_name)
        return result
    
    def print_config_summary(self):
        """打印配置摘要"""
        print("=== 配置文件加载摘要 ===")
        
        # 机器人信息
        bot_info = self.get_bot_info()
        if bot_info:
            print(f"机器人昵称: {bot_info.get('nickname', '未设置')}")
            print(f"机器人QQ: {bot_info.get('qq', '未设置')}")
        
        # 人格信息
        personality = self.get_personality()
        if personality:
            print(f"人格核心: {personality.get('personality_core', '未设置')[:30]}...")
        
        # 模型配置
        models = self.get_all_reply_models()
        print(f"已配置的回复模型数量: {len(models)}")
        for model_name, config in models.items():
            print(f"  - {model_name}: {config.get('name', '未知')} ({config.get('provider', '未知')})")
            print(f"    Key: {'已配置' if config.get('key') else '未配置'}")
            print(f"    URL: {config.get('url', '未配置')}")
            print(f"    pri_in: {config.get('pri_in', '未配置')}")
            print(f"    pri_out: {config.get('pri_out', '未配置')}")
            print(f"    temp: {config.get('temp', '未配置')}")
        
        print("=== 配置加载完成 ===")


# 创建全局配置管理器实例
config_manager = ConfigManager()

# 便捷访问函数
def get_bot_info():
    """获取机器人信息"""
    return config_manager.get_bot_info()

def get_personality():
    """获取人格配置"""
    return config_manager.get_personality()

def get_reply_model(model_name='reply_model'):
    """获取回复模型配置"""
    return config_manager.get_reply_model(model_name)

def get_whitelist_config():
    """获取群聊白名单配置"""
    return config_manager.get_whitelist_config()

def get_reply_config():
    """获取智能回复配置"""
    return config_manager.get_reply_config()

def get_estimate_model_config():
    """获取判断模型配置"""
    return config_manager.get_estimate_model_config()


# 创建一个简化的bot对象，方便在demo.py中使用
class Bot:
    def __init__(self):
        bot_info = get_bot_info()
        personality = get_personality()
        
        self.nickname = bot_info.get('nickname', '麦麦')
        self.qq = bot_info.get('qq', 385487834)
        self.personality_core = personality.get('personality_core', '')
        self.personality_side = personality.get('personality_side', '')
        self.identity = personality.get('identity', '')

# 创建全局bot实例
bot = Bot()

if __name__ == "__main__":
    # 测试配置读取
    config_manager.print_config_summary()
    
    print("\n=== 测试配置访问 ===")
    print(f"Bot昵称: {bot.nickname}")
    print(f"Bot QQ: {bot.qq}")
    
    reply_model = get_reply_model()
    print(f"默认回复模型: {reply_model}")