import os
import toml
from dotenv import load_dotenv
from pathlib import Path
from config.errors import ConfigError, ConfigErrorBundle


class ConfigLoader:
    def __init__(self):
        self.base = Path(__file__).parent / 'config'
        self._adapter = None
        self._bot = None
        self._env = None
        self._adaptive = None

    def load_all(self, collect_errors=True):
        errors = []
        try:
            self.get_adapter()
        except Exception as e:
            errors.append(e)
        bot_ok = True
        try:
            self.get_bot()
        except Exception as e:
            bot_ok = False
            errors.append(e)
        env_ok = True
        try:
            self.get_env()
        except Exception as e:
            env_ok = False
            errors.append(e)
        if bot_ok and env_ok:
            try:
                self.get_adaptive_models()
            except Exception as e:
                errors.append(e)
        if errors and collect_errors:
            raise ConfigErrorBundle(errors)
        if errors:
            raise errors[0]
        return {
            'adapter': self._adapter,
            'bot': self._bot,
            'env': self._env,
            'adaptive': self._adaptive,
        }

    def _read_toml(self, filename):
        path = self.base / filename
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = toml.load(f)
        except FileNotFoundError:
            raise ConfigError(str(path), hint='确保文件存在', example=None)
        except toml.TomlDecodeError as e:
            raise ConfigError(str(path), hint='修复 TOML 语法错误', example=None, actual=str(e))
        return data

    def get_adapter(self):
        if self._adapter is not None:
            return self._adapter
        data = self._read_toml('adapter_config.toml')
        self._validate_adapter(data)
        self._adapter = data
        return self._adapter

    def get_bot(self):
        if self._bot is not None:
            return self._bot
        data = self._read_toml('bot_config.toml')
        self._validate_bot(data)
        self._bot = data
        return self._bot

    def get_env(self):
        if self._env is not None:
            return self._env
        env_path = self.base / '.env'
        load_dotenv(env_path)
        out = {}
        for k, v in os.environ.items():
            if k.endswith('_URL'):
                provider = k[:-4].lower()
                out.setdefault(provider, {})
                out[provider]['url'] = v
            elif k.endswith('_KEY'):
                provider = k[:-4].lower()
                out.setdefault(provider, {})
                out[provider]['key'] = v
        self._env = out
        return self._env

    def _provider_env(self, provider):
        if not provider:
            return None
        return self.get_env().get(provider.lower())

    def get_adaptive_models(self):
        if self._adaptive is not None:
            return self._adaptive
        bot = self.get_bot()
        envs = self.get_env()
        cfg = {
            '回复模型_url': '',
            '回复模型_key': '',
            '回复模型_model': '',
            '判断模型_url': '',
            '判断模型_key': '',
            '判断模型_model': '',
            '图片模型_url': '',
            '图片模型_key': '',
            '图片模型_model': '',
            '图片模型_switch': False,
        }
        errors = []
        replyer = bot.get('model', {}).get('replyer_1', {})
        r_provider = replyer.get('provider', '')
        r_name = replyer.get('name', '')
        r_env = self._provider_env(r_provider)
        if r_env:
            cfg['回复模型_url'] = r_env.get('url', '')
            cfg['回复模型_key'] = r_env.get('key', '')
            cfg['回复模型_model'] = r_name
            if not cfg['回复模型_url'] or not cfg['回复模型_key']:
                errors.append(ConfigError(str(self.base / '.env'), section=r_provider, hint='补全 provider 的 URL/KEY', example=None))
        else:
            errors.append(ConfigError(str(self.base / '.env'), section=r_provider, hint='在 .env 添加 PROVIDER_URL/KEY', example=None))

        utils_small = bot.get('model', {}).get('utils_small', {})
        u_provider = utils_small.get('provider', '')
        u_name = utils_small.get('name', '')
        u_env = self._provider_env(u_provider)
        if u_env:
            cfg['判断模型_url'] = u_env.get('url', '')
            cfg['判断模型_key'] = u_env.get('key', '')
            cfg['判断模型_model'] = u_name
            if not cfg['判断模型_url'] or not cfg['判断模型_key']:
                errors.append(ConfigError(str(self.base / '.env'), section=u_provider, hint='补全 provider 的 URL/KEY', example=None))
        else:
            errors.append(ConfigError(str(self.base / '.env'), section=u_provider, hint='在 .env 添加 PROVIDER_URL/KEY', example=None))

        picture = bot.get('model', {}).get('picture', {})
        p_provider = picture.get('provider', '')
        p_name = picture.get('name', '')
        p_switch = bool(picture.get('开关', False))
        p_env = self._provider_env(p_provider)
        if p_env:
            cfg['图片模型_url'] = p_env.get('url', '')
            cfg['图片模型_key'] = p_env.get('key', '')
            cfg['图片模型_model'] = p_name
            cfg['图片模型_switch'] = p_switch
            if p_switch and (not cfg['图片模型_url'] or not cfg['图片模型_key']):
                errors.append(ConfigError(str(self.base / '.env'), section=p_provider, hint='开启图片模型时必须设置 URL/KEY', example=None))
        else:
            if p_switch:
                errors.append(ConfigError(str(self.base / '.env'), section=p_provider, hint='开启图片模型需在 .env 配置 provider', example=None))
            cfg['图片模型_switch'] = p_switch

        if errors:
            raise ConfigErrorBundle(errors)
        self._adaptive = cfg
        return self._adaptive

    def _validate_adapter(self, data):
        if 'napcat_server' not in data:
            raise ConfigError(str(self.base / 'adapter_config.toml'), section='napcat_server', hint='添加 napcat_server 段', example='[napcat_server]\nhost = "127.0.0.1"\nport = 8080')
        ns = data['napcat_server']
        if 'host' not in ns or not isinstance(ns['host'], str):
            raise ConfigError(str(self.base / 'adapter_config.toml'), section='napcat_server', key='host', expected='str', actual=type(ns.get('host')).__name__ if 'host' in ns else None, hint='设置主机地址', example='host = "127.0.0.1"')
        if 'port' not in ns or not isinstance(ns['port'], int):
            raise ConfigError(str(self.base / 'adapter_config.toml'), section='napcat_server', key='port', expected='int', actual=type(ns.get('port')).__name__ if 'port' in ns else None, hint='设置整数端口', example='port = 8080')
        chat = data.get('chat', {})
        gl = chat.get('group_list', [])
        if not isinstance(gl, list):
            raise ConfigError(str(self.base / 'adapter_config.toml'), section='chat', key='group_list', expected='list', actual=type(gl).__name__, hint='设置群白名单列表', example='group_list = [123456789, 987654321]')

    def _validate_bot(self, data):
        bot = data.get('bot', {})
        if 'bot的名字' not in bot or not isinstance(bot.get('bot的名字'), str):
            raise ConfigError(str(self.base / 'bot_config.toml'), section='bot', key='bot的名字', expected='str', actual=type(bot.get('bot的名字')).__name__ if 'bot的名字' in bot else None, hint='设置机器人名字', example='bot的名字 = "atbot"')
        if 'bot的qq号' not in bot:
            raise ConfigError(str(self.base / 'bot_config.toml'), section='bot', key='bot的qq号', expected='int', actual=type(bot.get('bot的qq号')).__name__ if 'bot的qq号' in bot else None, hint='设置机器人QQ号', example='bot的qq号 = 123456789')
        if '回复兴趣' not in bot or not isinstance(bot.get('回复兴趣'), int) or not (0 <= bot.get('回复兴趣') <= 10):
            raise ConfigError(str(self.base / 'bot_config.toml'), section='bot', key='回复兴趣', expected='int(0-10)', actual=bot.get('回复兴趣'), hint='设置 0-10 整数', example='回复兴趣 = 7')
        if '消息记录长度' not in bot or not isinstance(bot.get('消息记录长度'), int):
            raise ConfigError(str(self.base / 'bot_config.toml'), section='bot', key='消息记录长度', expected='int', actual=type(bot.get('消息记录长度')).__name__ if '消息记录长度' in bot else None, hint='设置历史长度', example='消息记录长度 = 100')
        personality = data.get('personality', {})
        for k in ['personality_core', 'personality_side', 'identity']:
            v = personality.get(k)
            if not isinstance(v, str):
                raise ConfigError(str(self.base / 'bot_config.toml'), section='personality', key=k, expected='str', actual=type(v).__name__ if v is not None else None, hint='设置文本', example=f'{k} = "..."')
        model = data.get('model', {})
        r = model.get('replyer_1', {})
        if not isinstance(r.get('provider'), str) or not isinstance(r.get('name'), str) or not isinstance(r.get('maxtoken'), int):
            raise ConfigError(str(self.base / 'bot_config.toml'), section='model.replyer_1', hint='设置 provider/name/maxtoken', example='[model.replyer_1]\nprovider = "SILICONFLOW"\nname = "qwen2.5"\nmaxtoken = 64')
        u = model.get('utils_small', {})
        if not isinstance(u.get('provider'), str) or not isinstance(u.get('name'), str):
            raise ConfigError(str(self.base / 'bot_config.toml'), section='model.utils_small', hint='设置 provider/name', example='[model.utils_small]\nprovider = "SILICONFLOW"\nname = "qwen2.5"')
        p = model.get('picture', {})
        if not isinstance(p.get('provider'), str) or not isinstance(p.get('name'), str) or not isinstance(p.get('开关', False), bool):
            raise ConfigError(str(self.base / 'bot_config.toml'), section='model.picture', hint='设置 provider/name/开关', example='[model.picture]\nprovider = "SILICONFLOW"\nname = "qwen2.5"\n开关 = false')


_loader = ConfigLoader()


def load_adapter_config():
    return _loader.get_adapter()


def load_bot_config():
    return _loader.get_bot()


def load_model_config():
    return _loader.get_env()


def load_adaptive_model_config():
    return _loader.get_adaptive_models()
