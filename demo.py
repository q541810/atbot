from pydoc import text
from requests import api
import websocket
import json
from openai import OpenAI, api_key
import random
import asyncio
import threading
import time
import signal
import sys

from read_config import bot, get_reply_model, config_manager, get_whitelist_config
import toml
from plugin_manager import initialize_plugin_manager
from context_manager import context_manager
from smart_reply import smart_reply_manager
from user_cache import UserCache
from user_info_fetcher import UserInfoFetcher
from at_parser import AtParser


llm_msg=()
#定义版本
version="beta_0.3.0"
#从配置文件读取群聊白名单
whitelist_config = get_whitelist_config()
white_list = whitelist_config.get('group_ids', [])

# 读取调试配置和WebSocket URL
try:
    with open('bot_config.toml', 'r', encoding='utf-8') as f:
        bot_config = toml.load(f)
    debug_enabled = bot_config.get('bot', {}).get('debug', False)
    websocket_url = bot_config.get('bot', {}).get('websocket_url', 'ws://localhost:8099/')
except Exception as e:
    print(f"读取配置文件失败: {e}")
    debug_enabled = False
    websocket_url = 'ws://localhost:8099/'

# 全局退出标志
exit_flag = False

def signal_handler(signum, frame):
    """信号处理函数，用于快速退出"""
    global exit_flag
    print("\n收到退出信号，程序将立即退出...")
    exit_flag = True
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)
def 撤回(group_id, message_id):
    ws = websocket.WebSocket()
    ws.connect(websocket_url)
    req = {
        "action": "delete_msg",
        "params": {"group_id": group_id, "message_id": message_id},
        "echo": "test"
    }
    ws.send(json.dumps(req))
    print("撤回了一条消息")

#定义发消息所用函数
def 发(text, group_id=None):
    if group_id is None:
        # 如果没有提供group_id，尝试使用全局变量中的最后一个group_id
        global last_group_id
        if 'last_group_id' in globals() and last_group_id is not None:
            group_id = last_group_id
        else:
            print("错误: 未提供群组ID且无法从上下文获取")
            return
            
    ws = websocket.WebSocket()
    ws.connect(websocket_url)
    req = {
        "action": "send_group_msg",
        "params": {"group_id": group_id, "message": text},
        "echo": "test"
    }
    ws.send(json.dumps(req))
    print(f"向群{group_id}发送了: {text}")
#开始运行

if __name__ == "__main__":
    print("正在初始化...")
    print("版本："+version)
    
    # 初始化插件管理器
    print("\n正在加载插件...")
    plugin_manager = initialize_plugin_manager(current_version=version)
    print(f"已加载 {len(plugin_manager.plugins)} 个插件\n")
    ws = websocket.WebSocket()
    ws.connect(websocket_url)

    # 获取回复模型配置
    reply_model = get_reply_model()
    # 初始化OpenAI客户端
    client = OpenAI(
        api_key=config_manager.get_api_key(reply_model['provider']),
        base_url=config_manager.get_base_url(reply_model['provider'])
    )
    print("reply_model:",reply_model['name'], "provider:",reply_model['provider'])
    
    # 获取智能回复配置摘要
    smart_config = smart_reply_manager.get_config_summary()
    print(f"智能回复配置: {smart_config}\n")
    
    # 初始化用户缓存和@解析器
    user_cache = UserCache()
    at_parser = AtParser()
    user_fetcher = None  # 将在WebSocket连接建立后初始化
    
    # WebSocket连接函数
    def connect_websocket():
        ws = websocket.WebSocket()
        ws.connect(websocket_url)
        # 设置接收超时，避免长时间阻塞
        ws.settimeout(1.0)  # 1秒超时
        print("WebSocket连接已建立")
        return ws
    
    # 主循环，包含重连机制
    while not exit_flag:
        try:
            if exit_flag:
                break
            ws = connect_websocket()
            
            # 初始化用户信息获取器
            user_fetcher = UserInfoFetcher(ws, user_cache)

            while not exit_flag:
                try:
                    if exit_flag:
                        break
                    msg = ws.recv()
                    # 解析消息
                    msg_dict = json.loads(msg)
                    
                    # 检查是否为API响应
                    if "echo" in msg_dict:
                        user_fetcher.handle_api_response(msg_dict)
                        continue
                    
                    # 检查是否为群消息
                    if "post_type" in msg_dict and msg_dict["post_type"] == "message" and \
                       "message_type" in msg_dict and msg_dict["message_type"] == "group" and \
                       "group_id" in msg_dict and "message" in msg_dict:
                        
                        # 提取消息内容和引用信息（无论是否在白名单中都需要解析）
                        raw_message = msg_dict["message"]
                        message_parts = []
                        reply_message_id = None
                        
                        for part in raw_message:
                            # 添加调试信息
                            if debug_enabled:
                                print(f"调试: 消息段类型={part.get('type')}, 数据={part.get('data', {})}")
                            
                            if part.get("type") == "text":
                                message_parts.append(part.get("data", {}).get("text", ""))
                            elif part.get("type") == "at":
                                qq_number = part.get("data", {}).get("qq", "")
                                if qq_number:
                                    message_parts.append(f"@{qq_number}")
                            elif part.get("type") == "image":
                                # 检查是否是表情包（通过文件名或其他特征）
                                file_data = part.get("data", {}).get("file", "")
                                if "face" in file_data.lower() or file_data.startswith("[CQ:face"):
                                    message_parts.append("[表情]")
                                else:
                                    message_parts.append("[图片]")
                            elif part.get("type") == "face":
                                message_parts.append("[表情]")
                            elif part.get("type") == "reply":
                                # 提取被引用的消息ID
                                reply_message_id = part.get("data", {}).get("id")
                                # 获取被引用的消息内容
                                if reply_message_id:
                                    try:
                                        # 构建获取消息的请求
                                        get_msg_request = {
                                            "action": "get_msg",
                                            "params": {
                                                "message_id": reply_message_id
                                            }
                                        }
                                        # 发送请求获取消息内容
                                        ws.send(json.dumps(get_msg_request))
                                        # 接收响应
                                        response = ws.recv()
                                        response_data = json.loads(response)
                                        
                                        if response_data.get("status") == "ok" and "data" in response_data:
                                            quoted_msg = response_data["data"]
                                            quoted_content = ""
                                            quoted_sender = quoted_msg.get("sender", {}).get("nickname", "未知用户")
                                            
                                            # 解析被引用消息的内容
                                            if "message" in quoted_msg:
                                                for msg_part in quoted_msg["message"]:
                                                    # 添加调试信息
                                                    if debug_enabled:
                                                        print(f"调试: 引用消息段类型={msg_part.get('type')}, 数据={msg_part.get('data', {})}")
                                                    
                                                    if msg_part.get("type") == "text":
                                                        quoted_content += msg_part.get("data", {}).get("text", "")
                                                    elif msg_part.get("type") == "at":
                                                        qq_num = msg_part.get("data", {}).get("qq", "")
                                                        if qq_num:
                                                            quoted_content += f"@{qq_num}"
                                                    elif msg_part.get("type") == "image":
                                                        # 检查是否是表情包（通过文件名或其他特征）
                                                        file_data = msg_part.get("data", {}).get("file", "")
                                                        if "face" in file_data.lower() or file_data.startswith("[CQ:face"):
                                                            quoted_content += "[表情]"
                                                        else:
                                                            quoted_content += "[图片]"
                                                    elif msg_part.get("type") == "face":
                                                        quoted_content += "[表情]"
                                            
                                            # 对引用消息内容进行@替换
                                            if quoted_content:
                                                quoted_content_with_names = at_parser.replace_at_with_names(quoted_content, user_fetcher)
                                                message_parts.append(f"[引用 {quoted_sender}: {quoted_content_with_names[:50]}{'...' if len(quoted_content_with_names) > 50 else ''}]")
                                            else:
                                                message_parts.append(f"[引用 {quoted_sender} 的消息]")
                                        else:
                                            message_parts.append("[引用消息获取失败]")
                                    except Exception as e:
                                        print(f"获取引用消息失败: {e}")
                                        message_parts.append("[引用消息]")
                        
                        message = "".join(message_parts)
                        # 提取昵称，如果不存在则默认为"未知用户"
                        name = msg_dict.get("sender", {}).get("nickname", "未知用户")
                        
                        # 检查是否为白名单中的群
                        if msg_dict["group_id"] in white_list:
                            # 保存最后一个群组ID，用于插件发送消息
                            global last_group_id
                            last_group_id = msg_dict["group_id"]
                            
                            # 先检查是否@了bot（使用原始消息，避免@替换后的误判）
                            should_reply_at = "@" in message and str(bot.qq) in message
                            
                            # 替换消息中的@QQ号为昵称
                            display_message = at_parser.replace_at_with_names(message, user_fetcher)
                            
                            # 打印消息内容
                            print(f"收到群消息来自 {name}：{display_message}")
                            
                            # 记录消息到上下文历史
                            context_manager.add_message(msg_dict["group_id"], name, display_message, is_bot=False)

                            
                            # 记录收到的消息（用于智能回复统计）
                            try:
                                def record_message_sync():
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    loop.run_until_complete(
                                        smart_reply_manager.record_message(str(msg_dict["group_id"]))
                                    )
                                    loop.close()
                                
                                # 在单独线程中执行异步任务
                                thread = threading.Thread(target=record_message_sync, daemon=True)
                                thread.start()
                            except Exception as e:
                                print(f"记录消息状态失败: {e}")
                        
                            # 检查插件是否处理了消息
                            if plugin_manager.handle_message(display_message, group_id=msg_dict["group_id"], message_id=msg_dict.get("message_id"), reply_message_id=reply_message_id, user_id=msg_dict.get("user_id")):
                                # 如果插件处理了消息，则不需要AI回复
                                continue
                         
                            if not should_reply_at:
                                # 智能回复判断逻辑
                                try:
                                    # 保存当前消息信息到局部变量，避免线程间变量冲突
                                    current_group_id = msg_dict["group_id"]
                                    current_message = display_message
                                    current_name = name
                                    
                                    def smart_reply_check():
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        try:
                                            # 获取上下文消息并转换为字符串
                                            context_messages = context_manager.get_context_messages(current_group_id)
                                            context_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context_messages[-5:]])  # 取最近5条消息
                                            
                                            result = loop.run_until_complete(
                                                smart_reply_manager.should_reply(
                                                    str(current_group_id), 
                                                    current_message, 
                                                    context_str
                                                )
                                            )
                                            
                                            # 如果判断需要回复，则发送回复
                                            if result:
                                                # 构建消息列表，包含系统提示和上下文历史
                                                messages = [
                                                    {"role": "system", "content": f"你叫{bot.nickname}。{bot.personality_core}{bot.personality_side}{bot.identity}""。要求:尽量简短，但在你认为必要的时候（比如别人求助时）可以详细一点,不许无意义的换行,也不许有无意义的空格,只输出一句话。你在一个qq群里面，请分辨谁是谁"}
                                                ]
                                                
                                                # 添加上下文历史
                                                context_messages = context_manager.get_context_messages(current_group_id)
                                                messages.extend(context_messages)
                                                
                                                # 添加当前消息
                                                messages.append({"role": "user", "content": current_name+"发了消息:"+current_message})
                                                response = client.chat.completions.create(
                                                    model=reply_model['name'],
                                                    messages=messages,
                                                    stream=False
                                                )

                                                bot_reply = response.choices[0].message.content.strip()
                                                发(bot_reply, current_group_id)
                                                
                                                # 记录机器人回复到上下文
                                                context_manager.add_message(current_group_id, bot.nickname, bot_reply, is_bot=True)
                                                
                                                # 记录回复状态
                                                try:
                                                    def record_reply_sync():
                                                        inner_loop = asyncio.new_event_loop()
                                                        asyncio.set_event_loop(inner_loop)
                                                        inner_loop.run_until_complete(
                                                            smart_reply_manager.record_reply(str(current_group_id))
                                                        )
                                                        inner_loop.close()
                                                    
                                                    reply_thread = threading.Thread(target=record_reply_sync, daemon=True)
                                                    reply_thread.start()
                                                except Exception as e:
                                                    print(f"记录回复状态失败: {e}")
                                                
                                                # 智能回复完成，不需要重复打印消息
                                                
                                        finally:
                                            loop.close()
                                    
                                    # 在后台线程中执行智能回复判断，不阻塞主循环
                                    thread = threading.Thread(target=smart_reply_check, daemon=True)
                                    thread.start()
                                except Exception as e:
                                    print(f"智能回复判断失败: {e}")
                            elif should_reply_at:
                                # 处理@回复（智能回复在独立线程中处理）
                                messages = [
                                    {"role": "system", "content": f"你叫{bot.nickname}。{bot.personality_core}{bot.personality_side}{bot.identity}""。要求:尽量简短，但在你认为必要的时候（比如别人求助时）可以详细一点,不许无意义的换行,也不许有无意义的空格,只输出一句话。你在一个qq群里面，请分辨谁是谁"}
                                ]
                                
                                # 添加上下文历史
                                context_messages = context_manager.get_context_messages(msg_dict["group_id"])
                                messages.extend(context_messages)
                                
                                # 添加当前消息到对话历史
                                messages.append({"role": "user", "content": name+"发了消息:"+display_message})
                                response = client.chat.completions.create(
                                    model=reply_model['name'],
                                    messages=messages,
                                    stream=False
                                )

                                bot_reply = response.choices[0].message.content.strip()
                                发(bot_reply, msg_dict["group_id"])
                                
                                # 记录机器人回复到上下文
                                context_manager.add_message(msg_dict["group_id"], bot.nickname, bot_reply, is_bot=True)
                                
                                # 记录回复状态
                                try:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    loop.run_until_complete(
                                        smart_reply_manager.record_reply(str(msg_dict["group_id"]))
                                    )
                                    loop.close()
                                except Exception as e:
                                    print(f"记录回复状态失败: {e}")
                            
                            # @回复完成

                except websocket.WebSocketTimeoutException:
                    # 超时异常，继续循环等待下一条消息
                    continue
                except (websocket.WebSocketConnectionClosedException, ConnectionError, TimeoutError) as e:
                    print(f"WebSocket连接异常: {e}")
                    print("正在尝试重新连接...")
                    try:
                        ws.close()
                    except:
                        pass
                    break  # 跳出内层循环，重新连接
                    
        except KeyboardInterrupt:
            print("\n用户手动中断，程序将退出")
            try:
                # 立即关闭WebSocket连接
                ws.close()
                print("WebSocket连接已关闭")
            except:
                pass
            # 设置退出标志，让所有daemon线程知道程序正在退出
            import sys
            sys.exit(0)
        except Exception as e:
            print(f"发生未预期的错误: {e}")
            print("正在尝试重新连接...")
            try:
                ws.close()
            except:
                pass
            time.sleep(5)  # 等待5秒后重连