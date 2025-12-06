import time
import re
from read_config import load_bot_config


_DEBUG_ENABLED = None
_LAST_DEBUG_TIME = 0.0
_DEBUG_INTERVAL_MS = 200


def info(msg: str):
    """打印信息级别的日志。"""
    current_time = time.strftime("%H:%M", time.localtime())
    print(f"[{current_time}] [INFO] {msg}")

def _mask(msg: str):
    s = msg
    s = re.sub(r"(api_key\s*=\s*)(\S+)", lambda m: m.group(1) + ("***" + m.group(2)[-4:] if len(m.group(2)) > 8 else "***"), s, flags=re.IGNORECASE)
    s = re.sub(r"(key\s*=\s*)(\S+)", lambda m: m.group(1) + ("***" + m.group(2)[-4:] if len(m.group(2)) > 8 else "***"), s, flags=re.IGNORECASE)
    s = re.sub(r"(Authorization:\s*Bearer\s+)(\S+)", lambda m: m.group(1) + ("***" + m.group(2)[-4:] if len(m.group(2)) > 8 else "***"), s, flags=re.IGNORECASE)
    return s


def error(msg: str):
    current_time = time.strftime("%H:%M", time.localtime())
    print(f"\033[31m[{current_time}] [ERROR] {_mask(str(msg))}\033[0m")

def debug(msg: str):
    global _DEBUG_ENABLED, _LAST_DEBUG_TIME, _DEBUG_INTERVAL_MS
    if _DEBUG_ENABLED is None:
        bot_config = load_bot_config()
        调试模式 = bot_config['bot'].get('调试模式', False)
        间隔 = bot_config['bot'].get('调试间隔ms', 200)
        try:
            _DEBUG_INTERVAL_MS = int(间隔)
        except Exception:
            _DEBUG_INTERVAL_MS = 200
        _DEBUG_ENABLED = bool(调试模式)
    if not _DEBUG_ENABLED:
        return
    now_ms = time.time() * 1000
    if now_ms - _LAST_DEBUG_TIME < _DEBUG_INTERVAL_MS:
        return
    _LAST_DEBUG_TIME = now_ms
    current_time = time.strftime("%H:%M", time.localtime())
    print(f"\033[35m[{current_time}] [DEBUG] {msg}\033[0m")

def warning(msg: str):
    """打印警告级别的日志，使用黄色突出显示。"""
    current_time = time.strftime("%H:%M", time.localtime())
    print(f"\033[33m[{current_time}] [WARNING] {msg}\033[0m")
