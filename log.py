import time
from read_config import load_bot_config


def info(msg: str):
    """打印信息级别的日志。"""
    current_time = time.strftime("%H:%M", time.localtime())
    print(f"[{current_time}] [INFO] {msg}")

def error(msg: str):
    """打印错误级别的日志，使用红色突出显示。"""
    current_time = time.strftime("%H:%M", time.localtime())
    print(f"\033[31m[{current_time}] [ERROR] {msg}\033[0m")

def debug(msg: str):
    """打印调试级别的日志，仅在调试模式启用时输出，使用紫色突出显示。"""
    # 加载bot配置
    bot_config = load_bot_config()
    调试模式 = bot_config['bot']['调试模式']
    调试模式 = bool(调试模式)
    if 调试模式:
        current_time = time.strftime("%H:%M", time.localtime())
        print(f"\033[35m[{current_time}] [DEBUG] {msg}\033[0m")

def warning(msg: str):
    """打印警告级别的日志，使用黄色突出显示。"""
    current_time = time.strftime("%H:%M", time.localtime())
    print(f"\033[33m[{current_time}] [WARNING] {msg}\033[0m")
