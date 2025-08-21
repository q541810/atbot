from pydoc import text
from requests import api
import websocket
import json
from openai import OpenAI, api_key
import random
import asyncio
import threading
import queue
import time
import signal
import sys
import os

from read_config import bot, get_reply_model, config_manager, get_whitelist_config
import toml
from plugin_manager import initialize_plugin_manager
from context_manager import context_manager
from smart_reply import smart_reply_manager
from user_cache import UserCache
from user_info_fetcher import UserInfoFetcher
from at_parser import AtParser
from message_handler import MessageHandler

# 新增: WebSocketClient 单例与异步执行器
class WebSocketClient:
    def __init__(self, url: str):
        self.url = url
        self.ws: websocket.WebSocket | None = None
        self._lock = threading.Lock()
        self._send_q: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()
        self._sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self._sender_started = False
        self._connected_logged = False

    def connect(self):
        with self._lock:
            if self.ws is not None:
                return
            ws = websocket.WebSocket()
            ws.connect(self.url)
            ws.settimeout(1.0)  # 接收超时，避免阻塞
            self.ws = ws
            if not self._connected_logged:
                print("WebSocket连接已建立")
                self._connected_logged = True
            if not self._sender_started:
                self._sender_thread.start()
                self._sender_started = True

    def _reconnect(self):
        with self._lock:
            try:
                if self.ws is not None:
                    try:
                        self.ws.close()
                    except:
                        pass
                    self.ws = None
            finally:
                pass
        # 尝试重连（带退避）
        delay = 1
        while True:
            try:
                self.connect()
                return
            except Exception as e:
                print(f"重连失败，{delay}s后重试: {e}")
                time.sleep(delay)
                delay = min(delay * 2, 10)

    def _sender_loop(self):
        while not self._stop_event.is_set():
            try:
                data = self._send_q.get(timeout=0.5)
            except queue.Empty:
                continue
            if data is None:
                continue
            try:
                if self.ws is None:
                    self.connect()
                self.ws.send(data)
            except Exception as e:
                print(f"发送失败，尝试重连并重试: {e}")
                self._reconnect()
                try:
                    if self.ws is not None:
                        self.ws.send(data)
                except Exception as e2:
                    print(f"重试发送仍失败，丢弃本次消息: {e2}")

    def send(self, data: str):
        self._send_q.put(data)

    def send_json(self, obj: dict):
        try:
            self.send(json.dumps(obj, ensure_ascii=False))
        except Exception as e:
            print(f"序列化发送数据失败: {e}")

    def recv(self) -> str:
        # 确保已连接
        if self.ws is None:
            self.connect()
        try:
            return self.ws.recv()
        except Exception:
            # 出现异常则重连并向上抛出供上层处理重连逻辑
            self._reconnect()
            raise

    def close(self):
        with self._lock:
            try:
                if self.ws is not None:
                    self.ws.close()
                    self.ws = None
                    print("WebSocket连接已关闭")
                    # 允许下次真正“首次连接”时再次打印一次已建立日志
                    self._connected_logged = False
            except:
                pass
        # 停止发送线程
        try:
            self._stop_event.set()
            try:
                self._send_q.put_nowait(None)
            except:
                pass
            if self._sender_started and self._sender_thread.is_alive():
                self._sender_thread.join(timeout=1.0)
        except:
            pass

class AsyncLoopExecutor:
    def __init__(self):
        self.loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._started.set()
        self.loop.run_forever()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._started.wait(timeout=2)

    def run(self, coro):
        if not self.loop:
            self.start()
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)


llm_msg=()
#定义版本
version="beta_0.3.0"
#从配置文件读取群聊白名单
whitelist_config = get_whitelist_config()
white_list = whitelist_config.get('group_ids', [])

# 读取调试配置和WebSocket URL
def resolve_config_path(filename: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, filename),
        os.path.join(os.path.dirname(base_dir), filename),
        os.path.join(os.getcwd(), filename),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None

try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = resolve_config_path('bot_config.toml')
    if cfg_path:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            bot_config = toml.load(f)
        debug_enabled = bot_config.get('bot', {}).get('debug', False)
        websocket_url = bot_config.get('bot', {}).get('websocket_url', 'ws://localhost:8099/')
    else:
        raise FileNotFoundError('bot_config.toml not found in expected locations')
except Exception as e:
    print(f"读取配置文件失败: {e}")
    debug_enabled = False
    websocket_url = 'ws://localhost:8099/'

# 全局退出标志
exit_flag = False
ws_client = None  # WebSocketClient 实例将于 __main__ 中初始化
async_executor = None  # AsyncLoopExecutor 实例将于 __main__ 中初始化

def signal_handler(signum, frame):
    """信号处理函数，用于快速退出"""
    global exit_flag, ws_client, async_executor
    print("\n收到退出信号，程序将立即退出...")
    exit_flag = True
    try:
        if ws_client:
            ws_client.close()
    except:
        pass
    try:
        if async_executor:
            async_executor.stop()
    except:
        pass
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)

def 撤回(group_id, message_id):
    req = {
        "action": "delete_msg",
        "params": {"group_id": group_id, "message_id": message_id},
        "echo": "test"
    }
    if ws_client is not None:
        ws_client.send_json(req)
        print("撤回了一条消息")
    else:
        print("撤回失败：WebSocketClient 未初始化")

def check_blacklist(text):
    """检查消息是否包含黑名单词语，如果包含则返回过滤后的消息
    
    Args:
        text: 要检查的消息文本
        
    Returns:
        tuple: (是否包含黑名单词语, 过滤后的消息)
    """
    try:
        # 读取黑名单配置
        cfg_path = resolve_config_path('bot_config.toml')
        if not cfg_path:
            return False, text
        with open(cfg_path, 'r', encoding='utf-8') as f:
            config = toml.load(f)
        
        filterlist = config.get('filterlist', {})
        black_terms = filterlist.get('black_terms', [])
        blacklist_out = filterlist.get('blacklist_out', [])
        
        # 如果黑名单为空，直接返回原消息
        if not black_terms:
            return False, text
            
        # 检查是否包含黑名单词语
        contains_blacklist = False
        for term in black_terms:
            if term and term in text:
                contains_blacklist = True
                break
                
        if contains_blacklist:
            # 如果包含黑名单词语且有过滤输出配置
            if blacklist_out:
                # 随机选择一个过滤输出
                filtered_message = random.choice(blacklist_out)
                return True, filtered_message
            else:
                # 如果没有配置过滤输出，返回空字符串（不发送消息）
                return True, ""
        else:
            return False, text
            
    except Exception as e:
        print(f"黑名单检查失败: {e}")
        return False, text

#定义发消息所用函数
def 发(text, group_id=None):
    if group_id is None:
        print("错误: 未提供群组ID，已取消发送以避免串群")
        return
    
    # 检查黑名单
    is_filtered, filtered_text = check_blacklist(text)
    
    # 如果消息被过滤且过滤后的消息为空，则不发送
    if is_filtered and not filtered_text:
        print(f"消息包含黑名单词语，已阻止发送: {text}")
        return
    
    # 使用过滤后的消息
    final_text = filtered_text
    
    req = {
        "action": "send_group_msg",
        "params": {"group_id": group_id, "message": final_text},
        "echo": "test"
    }
    if ws_client is not None:
        ws_client.send_json(req)
        if is_filtered:
            print(f"向群{group_id}发送了过滤后的消息: {final_text} (原消息: {text})")
        else:
            print(f"向群{group_id}发送了: {final_text}")
    else:
        print("发送失败：WebSocketClient 未初始化")

#开始运行

if __name__ == "__main__":
    print("正在初始化...")
    print("版本："+version)
    
    # 初始化插件管理器
    print("\n正在加载插件...")
    plugin_manager = initialize_plugin_manager(current_version=version)
    print(f"已加载 {len(plugin_manager.plugins)} 个插件\n")

    # 初始化 WebSocketClient 与 异步执行器
    ws_client = WebSocketClient(websocket_url)
    # 删除重复的首次 connect 调用，统一在 connect_websocket() 中管理连接
    async_executor = AsyncLoopExecutor()
    async_executor.start()

    # 获取回复模型配置
    reply_model = get_reply_model()
    # 初始化OpenAI客户端
    client = OpenAI(
        api_key=config_manager.get_api_key(reply_model['provider']),
        base_url=config_manager.get_base_url(reply_model['provider'])
    )
    print("reply_model:",reply_model['name'], "provider:",reply_model['provider'])
    
    smart_config = smart_reply_manager.get_config_summary()
    print(f"智能回复配置: {smart_config}\n")
    
    user_cache = UserCache()
    at_parser = AtParser()
    user_fetcher = None
    
    message_handler = MessageHandler(ws_client, async_executor, plugin_manager, user_fetcher, at_parser, user_cache, client, reply_model)
    
    def connect_websocket():
        ws_client.connect()
        return ws_client
    
    while not exit_flag:
        try:
            if exit_flag:
                break
            ws = connect_websocket()
            user_fetcher = UserInfoFetcher(ws_client, user_cache)
            message_handler.user_fetcher = user_fetcher  # 更新user_fetcher
            
            while not exit_flag:
                try:
                    if exit_flag:
                        break
                    msg = ws_client.recv()
                    msg_dict = json.loads(msg)
                    
                    if "echo" in msg_dict:
                        user_fetcher.handle_api_response(msg_dict)
                        continue
                    
                    message_handler.handle_message(msg_dict)
                except websocket.WebSocketTimeoutException:
                    continue
                except (websocket.WebSocketConnectionClosedException, ConnectionError, TimeoutError) as e:
                    print(f"WebSocket连接异常: {e}")
                    print("正在尝试重新连接...")
                    try:
                        ws_client.close()
                    except:
                        pass
                    break
        except KeyboardInterrupt:
            print("\n用户手动中断，程序将退出")
            try:
                ws_client.close()
                print("WebSocket连接已关闭")
            except:
                pass
            try:
                if async_executor:
                    async_executor.stop()
            except:
                pass
            sys.exit(0)
        except Exception as e:
            print(f"发生未预期的错误: {e}")
            print("正在尝试重新连接...")
            try:
                ws_client.close()
            except:
                pass
            time.sleep(5)  # 等待5秒后重连