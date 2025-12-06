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
    """
    敏感信息遮蔽函数，用于防止API密钥等敏感信息在日志中泄露。
    
    此函数通过正则表达式匹配常见的敏感信息格式，并将其替换为部分遮蔽的形式。
    只保留敏感信息的最后几个字符，其余部分用星号(*)替代。
    
    参数:
        msg (str): 需要进行敏感信息遮蔽的原始消息字符串
        
    返回:
        str: 遮蔽敏感信息后的安全消息字符串
        
    遮蔽规则:
        1. API密钥格式: "api_key=xxxxx" -> "api_key=***xxxx"
        2. 通用密钥格式: "key=xxxxx" -> "key=***xxxx"
        3. Bearer认证格式: "Authorization: Bearer xxxxx" -> "Authorization: Bearer ***xxxx"
        
    注意事项:
        - 如果密钥长度小于等于8，则完全遮蔽为"***"
        - 使用re.IGNORECASE标志，确保匹配不区分大小写
        - 保留原始消息中的其他内容不变
    """
    # 创建消息副本，避免修改原始字符串
    s = msg
    
    # 匹配并遮蔽API密钥格式: api_key=xxxxx
    # 正则表达式解释:
    # (api_key\s*=\s*) - 捕获组1: 匹配"api_key"后跟0或多个空白字符，再跟等号和0或多个空白字符
    # (\S+) - 捕获组2: 匹配一个或多个非空白字符(即密钥本身)
    # lambda函数处理: 如果密钥长度>8，保留最后4个字符；否则完全遮蔽
    s = re.sub(r"(api_key\s*=\s*)(\S+)", 
               lambda m: m.group(1) + ("***" + m.group(2)[-4:] if len(m.group(2)) > 8 else "***"), 
               s, 
               flags=re.IGNORECASE)
    
    # 匹配并遮蔽通用密钥格式: key=xxxxx
    # 同上，但匹配更通用的"key"参数
    s = re.sub(r"(key\s*=\s*)(\S+)", 
               lambda m: m.group(1) + ("***" + m.group(2)[-4:] if len(m.group(2)) > 8 else "***"), 
               s, 
               flags=re.IGNORECASE)
    
    # 匹配并遮蔽Bearer认证令牌格式: Authorization: Bearer xxxxx
    # 常见于HTTP请求头中的认证信息
    s = re.sub(r"(Authorization:\s*Bearer\s+)(\S+)", 
               lambda m: m.group(1) + ("***" + m.group(2)[-4:] if len(m.group(2)) > 8 else "***"), 
               s, 
               flags=re.IGNORECASE)
    
    # 返回遮蔽后的安全字符串
    return s


def error(msg: str):
    """
    打印错误级别的日志消息，使用红色突出显示。
    
    此函数用于记录系统中的错误信息，包括异常、失败的操作等。
    错误消息会被自动进行敏感信息遮蔽处理，确保不会泄露API密钥等敏感数据。
    
    参数:
        msg (str): 要记录的错误消息内容
        
    返回:
        None
        
    功能细节:
        1. 获取当前本地时间并格式化为"HH:MM"格式
        2. 对消息内容进行敏感信息遮蔽处理
        3. 使用ANSI转义序列将文本颜色设置为红色(\033[31m)
        4. 格式化输出: "[时间] [ERROR] 消息内容"
        5. 重置文本颜色(\033[0m)确保不影响后续终端输出
        
    使用示例:
        error("API请求失败: api_key=abcdef123456")
        # 输出: [14:30] [ERROR] API请求失败: api_key=***3456
    """
    # 获取当前本地时间并格式化为"时:分"格式
    current_time = time.strftime("%H:%M", time.localtime())
    
    # 使用ANSI红色转义序列打印错误消息，并对消息进行敏感信息遮蔽
    # \033[31m - 设置文本颜色为红色
    # \033[0m - 重置所有文本属性(包括颜色)
    print(f"\033[31m[{current_time}] [ERROR] {_mask(str(msg))}\033[0m")


def debug(msg: str):
    """
    打印调试级别的日志消息，使用紫色突出显示，支持频率限制。
    
    此函数用于开发和调试过程中的信息输出，具有以下特性:
    1. 可通过配置文件控制是否启用调试模式
    2. 支持最小输出间隔限制，避免日志刷屏
    3. 首次调用时自动加载配置并初始化调试设置
    4. 使用紫色突出显示，便于在终端中识别
    
    参数:
        msg (str): 要记录的调试消息内容
        
    返回:
        None
        
    功能细节:
        1. 配置加载:
           - 从bot_config.toml中读取"调试模式"和"调试间隔ms"设置
           - 延迟加载: 只在首次调用时读取配置，提高性能
           
        2. 频率限制:
           - 使用时间戳比较确保两次调试输出间隔不小于配置值
           - 默认间隔为200毫秒，防止日志刷屏
           
        3. 输出格式:
           - 使用ANSI紫色转义序列(\033[35m)
           - 格式: "[时间] [DEBUG] 消息内容"
           
        4. 全局变量:
           - _DEBUG_ENABLED: 调试模式开关(None表示未初始化)
           - _LAST_DEBUG_TIME: 上次调试输出的时间戳(毫秒)
           - _DEBUG_INTERVAL_MS: 调试输出的最小间隔(毫秒)
           
    使用示例:
        debug("处理消息: 用户发送了问候")
        # 如果启用调试模式且满足间隔要求，输出: [14:30] [DEBUG] 处理消息: 用户发送了问候
    """
    # 声明使用全局变量，以便修改这些变量的值
    global _DEBUG_ENABLED, _LAST_DEBUG_TIME, _DEBUG_INTERVAL_MS
    
    # 检查是否已初始化调试配置
    if _DEBUG_ENABLED is None:
        # 首次调用时加载配置
        bot_config = load_bot_config()
        
        # 从配置中读取调试模式开关，默认为False
        调试模式 = bot_config['bot'].get('调试模式', False)
        
        # 从配置中读取调试输出间隔，默认为200毫秒
        间隔 = bot_config['bot'].get('调试间隔ms', 200)
        
        # 尝试将间隔转换为整数，失败则使用默认值200
        try:
            _DEBUG_INTERVAL_MS = int(间隔)
        except Exception:
            _DEBUG_INTERVAL_MS = 200
            
        # 设置调试模式开关
        _DEBUG_ENABLED = bool(调试模式)
    
    # 如果调试模式未启用，直接返回不输出
    if not _DEBUG_ENABLED:
        return
    
    # 获取当前时间戳(毫秒)
    now_ms = time.time() * 1000
    
    # 检查距离上次调试输出的时间是否小于配置的最小间隔
    if now_ms - _LAST_DEBUG_TIME < _DEBUG_INTERVAL_MS:
        return  # 未达到间隔要求，不输出
    
    # 更新上次调试输出时间戳
    _LAST_DEBUG_TIME = now_ms
    
    # 获取当前本地时间并格式化为"时:分"格式
    current_time = time.strftime("%H:%M", time.localtime())
    
    # 使用ANSI紫色转义序列打印调试消息
    # \033[35m - 设置文本颜色为紫色
    # \033[0m - 重置所有文本属性(包括颜色)
    print(f"\033[35m[{current_time}] [DEBUG] {msg}\033[0m")

def warning(msg: str):
    """打印警告级别的日志，使用黄色突出显示。"""
    current_time = time.strftime("%H:%M", time.localtime())
    print(f"\033[33m[{current_time}] [WARNING] {msg}\033[0m")
