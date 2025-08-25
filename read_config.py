import os
import toml
from dotenv import load_dotenv

def load_adapter_config():
    """读取适配器配置文件 adapter_config.toml。"""
    # 构建配置文件路径
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'adapter_config.toml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return toml.load(f)

def load_bot_config():
    """读取 bot 配置文件 bot_config.toml。"""
    # 构建配置文件路径
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'bot_config.toml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return toml.load(f)

def load_model_config():
    """读取模型配置文件 .env，并提取相关环境变量。"""
    # 构建配置文件路径
    config_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
    load_dotenv(config_path)
    
    model_config = {}
    # 动态加载所有以 _URL 和 _KEY 结尾的环境变量
    for key, value in os.environ.items():
        if key.endswith('_URL'):
            provider = key[:-4].lower()  # 移除 _URL 并转为小写
            model_config[provider] = {'url': value}
        elif key.endswith('_KEY'):
            provider = key[:-4].lower()
            if provider not in model_config:
                model_config[provider] = {}
            model_config[provider]['key'] = value
    
    return model_config

def _get_provider_config(env_config, provider):
    """根据提供商名称获取对应的配置，如果不存在则返回 None。"""
    provider_lower = provider.lower()
    return env_config.get(provider_lower)

def load_adaptive_model_config():
    """自适应读取模型配置，根据 bot_config.toml 中的模型设置自动匹配对应的 API 配置。"""
    from log import error  # 延迟导入以避免循环导入
    bot_config = load_bot_config()  # 加载 bot 配置
    env_config = load_model_config()  # 加载环境配置
    
    adaptive_config = {
        '回复模型_url': '',
        '回复模型_key': '',
        '回复模型_model': '',
        '判断模型_url': '',
        '判断模型_key': '',
        '判断模型_model': '',
        '图片模型_url': '',
        '图片模型_key': '',
        '图片模型_model': '',
        '图片模型_switch': False
    }
    
    # 配置回复模型
    replyer_1 = bot_config.get('model', {}).get('replyer_1', {})
    provider = replyer_1.get('provider', '')
    model_name = replyer_1.get('name', '')
    config = _get_provider_config(env_config, provider)
    if config:
        adaptive_config['回复模型_url'] = config.get('url', '')
        adaptive_config['回复模型_key'] = config.get('key', '')
        adaptive_config['回复模型_model'] = model_name
    else:
        error(f"回复模型提供商 '{provider}' 未在 .env 中找到配置。")
    
    # 配置判断模型
    utils_small = bot_config.get('model', {}).get('utils_small', {})
    provider = utils_small.get('provider', '')
    model_name = utils_small.get('name', '')
    config = _get_provider_config(env_config, provider)
    if config:
        adaptive_config['判断模型_url'] = config.get('url', '')
        adaptive_config['判断模型_key'] = config.get('key', '')
        adaptive_config['判断模型_model'] = model_name
    else:
        error(f"判断模型提供商 '{provider}' 未在 .env 中找到配置。")
    
    # 配置图片识别模型
    picture = bot_config.get('model', {}).get('picture', {})
    provider = picture.get('provider', '')
    model_name = picture.get('name', '')
    switch = picture.get('开关', False)
    config = _get_provider_config(env_config, provider)
    if config:
        adaptive_config['图片模型_url'] = config.get('url', '')
        adaptive_config['图片模型_key'] = config.get('key', '')
        adaptive_config['图片模型_model'] = model_name
        adaptive_config['图片模型_switch'] = switch
    else:
        error(f"图片模型提供商 '{provider}' 未在 .env 中找到配置。")
    
    return adaptive_config