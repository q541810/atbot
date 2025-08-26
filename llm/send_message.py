import asyncio
import errno
from nt import error
from openai import OpenAI
import websockets
import json
import sys
import os
import time
import random
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from log import debug, info,warning,error
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
            info(f"成功发送消息到群{群号}: {消息内容}")
    except Exception as e:
        info(f"发送消息失败: {e}")
"""
使用llm发送消息
"""
async def llm_send_message(消息历史,那个人的名字,单条完整消息,bot名字:str,提示词:str,群号:int,napcat_host:str,napcat_port:int,api_url:str,api_key:str,模型:str,是否发至群里:bool,最大token:int,替换词:str,被替换词:str)->str:
    if os.path.exists("data/Message_frequency_cache.txt"):
        with open("data/Message_frequency_cache.txt", "r", encoding="utf-8") as f:
            # 读取最后一行的时间戳
            lines = f.readlines()
            if lines:
                last_time = float(lines[-1].strip())
                # 判断时间差是否在3秒内
                if time.time() - last_time < 3:
                    info("消息发送频率过快，忽略")
                    return 0
    else:
        os.makedirs("data/Message_frequency_cache.txt", exist_ok=True)
        warning("消息频率缓存文件不存在，已创建")
    # 清空文件内容
    with open("data/Message_frequency_cache.txt", "w", encoding="utf-8") as f:
        f.write("")
    
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
    if content.startswith('\n'):
        content = content[2:]
        debug("已删除第一个换行符")
    if content.endswith('\n'):
        content = content[:-2]
        debug("已删除最后一个换行符")
    if content is None or content == "" or content ==" ":
        warning("llm返回为空")
        return "111111111"#配合bot.py的防误报机制实现不返回报错的功能
    # 检查替换词列表中是否有词出现在content中
    if isinstance(替换词, (list, tuple)):
        for word in 替换词:
            if word in content:
                if 被替换词 == "" or 被替换词 == " ":
                    raise ValueError("被替换词列表中存在空字符串或为空")
                else:
                    content = random.choice(被替换词)
    # 写入当前时间戳到频率缓存文件
    with open("data/Message_frequency_cache.txt", "a", encoding="utf-8") as f:
        f.write(f"{time.time()}\n")
    if 是否发至群里:
        await send_message_to_group(content,群号,napcat_host,napcat_port)
    return content