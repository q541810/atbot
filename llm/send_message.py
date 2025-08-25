import asyncio
from openai import OpenAI
import websockets
import json
import sys
import os
import time
import random
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from log import info
from typing import Optional
from read_config import load_bot_config
from data.read_the_username import 替换消息中的at

# 全局变量用于频率限制和缓存验证
last_call_time = 0
message_cache = {}  # 用于缓存消息，防止重复发送



async def send_message_to_group(消息内容,群号,napcat_host,napcat_port):
    global last_call_time, message_cache
    
    bot_config = load_bot_config()
    bot_name = bot_config['bot']['bot的名字']
    bot_qq = bot_config['bot']['bot的qq号']
    
    if re.search(r"@\d{5,12}", 消息内容):
        消息内容 = await 替换消息中的at(消息内容, napcat_host, napcat_port, bot_qq=bot_qq, bot_name=bot_name, 群号=群号)
    
    # 生成消息唯一标识
    message_id = f"{群号}_{hash(消息内容)}_{int(time.time())}"
    
    # 检查是否重复消息
    if message_id in message_cache:
        info(f"检测到重复消息，跳过发送: {消息内容[:20]}...")
        return
    
    current_time = time.time()
    
    # 频率限制：每2秒只能调用一次
    if current_time - last_call_time < 2:
        # 随机延迟3-4秒
        delay = random.uniform(3, 4)
        info(f"频率限制触发，延迟{delay:.2f}秒后发送消息")
        await asyncio.sleep(delay)
    
    # 更新最后调用时间
    last_call_time = time.time()
    
    # 将消息加入缓存（保留最近50条消息记录）
    message_cache[message_id] = current_time
    if len(message_cache) > 50:
        # 清理旧的缓存记录
        oldest_key = min(message_cache.keys(), key=lambda k: message_cache[k])
        del message_cache[oldest_key]
    
    # 验证参数有效性
    if not isinstance(群号, int) or 群号 <= 0:
        info(f"无效的群号: {群号}，跳过发送")
        return
    
    if not 消息内容 or not isinstance(消息内容, str):
        info(f"无效的消息内容，跳过发送")
        return
    
    try:
        uri = (f"ws://{napcat_host}:{napcat_port}/")
        async with websockets.connect(uri) as ws:
        # 发送请求
            req = {
                "action": "send_group_msg",
                "params": {"group_id": 群号, "message": 消息内容},
                "echo": "chat"
            }
            await ws.send(json.dumps(req))
            info(f"成功发送消息到群{群号}: {消息内容[:30]}...")
    except Exception as e:
        info(f"发送消息失败: {e}")
        # 发送失败时从缓存中移除
        if message_id in message_cache:
            del message_cache[message_id]
"""
使用llm发送消息
"""
async def llm_send_message(消息历史,那个人的名字,单条完整消息,bot名字:str,提示词:str,群号:int,napcat_host:str,napcat_port:int,api_url:str,api_key:str,模型:str,是否发至群里:bool,最大token:int=300)->str:
    if "system" in 单条完整消息.lower() or "开发者模式" in 单条完整消息 and "x" not in 那个人的名字:
        info("检测到敏感关键词，跳过发送")
        return "111111111"#配合bot.py的防误报机制实现不返回报错的功能
    client = OpenAI(
            base_url=api_url,
            api_key=api_key,
            timeout=30.0
    )
    completion = client.chat.completions.create(
        model=模型,
        max_tokens=最大token,
        messages=[
            {"role": "system", "content": f"""你叫"{bot名字}"，你正在一个qq群里聊天，人设:{提示词}，不能换行!!!!!!!!，少用空格，回复尽量简短，只输出一句话"""},
            {"role": "user", "content": f"""消息历史:{消息历史},你要回复的消息：{单条完整消息}（他不一定在和你说话，请注意判断）"""}
    ]
    )
        # 获取返回内容并处理
    content = completion.choices[0].message.content
    if 是否发至群里:
        await send_message_to_group(content,群号,napcat_host,napcat_port)
    return content