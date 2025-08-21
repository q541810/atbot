import json
import threading
import time
from typing import Dict, Any
from openai import OpenAI
from read_config import bot, get_reply_model, config_manager
from context_manager import context_manager
from smart_reply import smart_reply_manager
from plugin_manager import PluginManager
from user_info_fetcher import UserInfoFetcher
from at_parser import AtParser
from user_cache import UserCache
import os
import toml
import random

class MessageHandler:
    def __init__(self, ws_client, async_executor, plugin_manager: PluginManager, user_fetcher: UserInfoFetcher, at_parser: AtParser, user_cache: UserCache, client: OpenAI, reply_model: Dict[str, Any]):
        self.ws_client = ws_client
        self.async_executor = async_executor
        self.plugin_manager = plugin_manager
        self.user_fetcher = user_fetcher
        self.at_parser = at_parser
        self.user_cache = user_cache
        self.client = client
        self.reply_model = reply_model

    def handle_message(self, msg_dict: Dict[str, Any]):
        if 'post_type' in msg_dict and msg_dict['post_type'] == 'message' and \
           'message_type' in msg_dict and msg_dict['message_type'] == 'group' and \
           'group_id' in msg_dict and 'message' in msg_dict:

            raw_message = msg_dict['message']
            message_parts = []
            reply_message_id = None

            for part in raw_message:
                if part.get('type') == 'text':
                    message_parts.append(part.get('data', {}).get('text', ''))
                elif part.get('type') == 'at':
                    qq_number = part.get('data', {}).get('qq', '')
                    if qq_number:
                        message_parts.append(f'@{qq_number}')
                elif part.get('type') == 'image':
                    file_data = part.get('data', {}).get('file', '')
                    if 'face' in file_data.lower() or file_data.startswith('[CQ:face'):
                        message_parts.append('[表情]')
                    else:
                        message_parts.append('[图片]')
                elif part.get('type') == 'face':
                    message_parts.append('[表情]')
                elif part.get('type') == 'reply':
                    reply_message_id = part.get('data', {}).get('id')
                    if reply_message_id:
                        try:
                            get_msg_request = {
                                'action': 'get_msg',
                                'params': {'message_id': reply_message_id}
                            }
                            self.ws_client.send_json(get_msg_request)
                            response = self.ws_client.recv()
                            response_data = json.loads(response)
                            if response_data.get('status') == 'ok' and 'data' in response_data:
                                quoted_msg = response_data['data']
                                quoted_content = ''
                                quoted_sender = quoted_msg.get('sender', {}).get('nickname', '未知用户')
                                if 'message' in quoted_msg:
                                    for msg_part in quoted_msg['message']:
                                        if msg_part.get('type') == 'text':
                                            quoted_content += msg_part.get('data', {}).get('text', '')
                                        elif msg_part.get('type') == 'at':
                                            qq_num = msg_part.get('data', {}).get('qq', '')
                                            if qq_num:
                                                quoted_content += f'@{qq_num}'
                                        elif msg_part.get('type') == 'image':
                                            file_data = msg_part.get('data', {}).get('file', '')
                                            if 'face' in file_data.lower() or file_data.startswith('[CQ:face'):
                                                quoted_content += '[表情]'
                                            else:
                                                quoted_content += '[图片]'
                                        elif msg_part.get('type') == 'face':
                                            quoted_content += '[表情]'
                                if quoted_content:
                                    quoted_content_with_names = self.at_parser.replace_at_with_names(quoted_content, self.user_fetcher)
                                    message_parts.append(f'[引用 {quoted_sender}: {quoted_content_with_names[:50]}{'...' if len(quoted_content_with_names) > 50 else ''}]')
                                else:
                                    message_parts.append(f'[引用 {quoted_sender} 的消息]')
                            else:
                                message_parts.append('[引用消息获取失败]')
                        except Exception as e:
                            print(f'获取引用消息失败: {e}')
                            message_parts.append('[引用消息]')

            message = ''.join(message_parts)
            name = msg_dict.get('sender', {}).get('nickname', '未知用户')

            if msg_dict['group_id'] in config_manager.get_whitelist_config().get('group_ids', []):
                global last_group_id
                last_group_id = msg_dict['group_id']

                should_reply_at = '@' in message and str(bot.qq) in message
                display_message = self.at_parser.replace_at_with_names(message, self.user_fetcher)
                print(f'收到群消息来自 {name}（群号：{msg_dict["group_id"]}）：{display_message}')

                self.async_executor.run(smart_reply_manager.record_message(str(msg_dict['group_id'])))

                # 将 send 回调传递给插件
                if self.plugin_manager.handle_message(display_message, group_id=msg_dict['group_id'], message_id=msg_dict.get('message_id'), reply_message_id=reply_message_id, user_id=msg_dict.get('user_id'), send=self.send_message, revoke=self.revoke_message):
                    context_manager.add_message(msg_dict['group_id'], name, display_message, is_bot=False)
                    return

                if not should_reply_at:
                    current_group_id = msg_dict['group_id']
                    current_message = display_message
                    current_name = name
                    cached_user_message = {'role': 'user', 'content': current_name + '发了消息:' + current_message}
                    context_added = threading.Event()

                    def smart_reply_check():
                        context_messages = context_manager.get_context_messages(current_group_id)
                        context_str = '\n'.join([f"{msg['role']}: {msg['content']}" for msg in context_messages[-5:]])
                        future = self.async_executor.run(smart_reply_manager.should_reply(str(current_group_id), current_message, context_str))
                        result = future.result()
                        if result:
                            messages = [
                                {'role': 'system', 'content': f'你叫{bot.nickname}。{bot.personality_core}{bot.personality_side}{bot.identity}。要求:尽量简短，但在你认为必要的时候（比如别人求助时）可以详细一点,不许无意义的换行,也不许有无意义的空格,只输出一句话。你在一个qq群里面，请分辨谁是谁'}
                            ]
                            context_msgs = context_manager.get_context_messages(current_group_id)
                            messages.extend(context_msgs)
                            messages.append(cached_user_message)
                            response = self.client.chat.completions.create(model=self.reply_model['name'], messages=messages, stream=False)
                            bot_reply = response.choices[0].message.content.strip()
                            self.send_message(bot_reply, current_group_id)
                            context_manager.add_message(current_group_id, current_name, current_message, is_bot=False)
                            context_manager.add_message(current_group_id, bot.nickname, bot_reply, is_bot=True)
                            context_added.set()
                            self.async_executor.run(smart_reply_manager.record_reply(str(current_group_id)))

                    thread = threading.Thread(target=smart_reply_check, daemon=True)
                    thread.start()

                    def check_and_add_context():
                        time.sleep(1)
                        if not context_added.is_set():
                            context_manager.add_message(current_group_id, current_name, current_message, is_bot=False)
                            context_added.set()

                    context_thread = threading.Thread(target=check_and_add_context, daemon=True)
                    context_thread.start()
                else:
                    messages = [
                        {'role': 'system', 'content': f'你叫{bot.nickname}。{bot.personality_core}{bot.personality_side}{bot.identity}。要求:尽量简短，但在你认为必要的时候（比如别人求助时）可以详细一点,不许无意义的换行,也不许有无意义的空格,只输出一句话。你在一个qq群里面，请分辨谁是谁'}
                    ]
                    context_messages = context_manager.get_context_messages(msg_dict['group_id'])
                    messages.extend(context_messages)
                    messages.append({'role': 'user', 'content': name + '发了消息:' + display_message})
                    response = self.client.chat.completions.create(model=self.reply_model['name'], messages=messages, stream=False)
                    bot_reply = response.choices[0].message.content.strip()
                    self.send_message(bot_reply, msg_dict['group_id'])
                    context_manager.add_message(msg_dict['group_id'], name, display_message, is_bot=False)
                    context_manager.add_message(msg_dict['group_id'], bot.nickname, bot_reply, is_bot=True)
                    self.async_executor.run(smart_reply_manager.record_reply(str(msg_dict['group_id'])))

    def send_message(self, text: str, group_id: int):
        is_filtered, filtered_text = self.check_blacklist(text)
        if is_filtered and not filtered_text:
            print(f'消息包含黑名单词语，已阻止发送: {text}')
            return
        final_text = filtered_text
        req = {
            'action': 'send_group_msg',
            'params': {'group_id': group_id, 'message': final_text},
            'echo': 'test'
        }
        self.ws_client.send_json(req)
        if is_filtered:
            print(f'向群{group_id}发送了过滤后的消息: {final_text} (原消息: {text})')
        else:
            print(f'向群{group_id}发送了: {final_text}')

    def revoke_message(self, group_id: int, message_id: int):
        req = {
            'action': 'delete_msg',
            'params': {'group_id': group_id, 'message_id': message_id},
            'echo': 'test'
        }
        try:
            self.ws_client.send_json(req)
            print('撤回了一条消息')
        except Exception:
            print('撤回失败：WebSocketClient 未初始化')

    def check_blacklist(self, text: str):
        # 实现黑名单检查逻辑，从demo.py复制
        try:
            cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot_config.toml')
            with open(cfg_path, 'r', encoding='utf-8') as f:
                config = toml.load(f)
            filterlist = config.get('filterlist', {})
            black_terms = filterlist.get('black_terms', [])
            blacklist_out = filterlist.get('blacklist_out', [])
            if not black_terms:
                return False, text
            contains_blacklist = any(term and term in text for term in black_terms)
            if contains_blacklist:
                if blacklist_out:
                    filtered_message = random.choice(blacklist_out)
                    return True, filtered_message
                else:
                    return True, ''
            else:
                return False, text
        except Exception as e:
            print(f'黑名单检查失败: {e}')
            return False, text