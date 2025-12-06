import asyncio
import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from log import debug, info, warning
from openai import AsyncOpenAI
from pydantic.types import T

async def llm_if(message: str, bot_name: str, bot_qq: int, url: str, key: str, model: str, message_content: str, bot_Prompt: str, 消息记录: str = ""):
    """使用 LLM 判断机器人对消息的兴趣度（0-10），并根据特定条件调整。"""
    提起名字 = False
    if "@" in message and str(bot_name) in message:
        info("被@,兴趣度改为10")
        return int(10)
    else:
        if bot_name in message:
            提起名字 = True
        # 调用 LLM
        client = AsyncOpenAI(
            base_url=url,
            api_key=key,
        )
        completion = await client.chat.completions.create(
            model=model,
            temperature=0.5,
            max_tokens=2,
            messages=[
                {"role": "system", "content": f"你叫{bot_name}，消息记录:{消息记录}本条消息{message}根据消息内容和上下文，评估你的回复兴趣度(0-10)。\n评分标准：\n- 0-3: 无需回复(纯表情、私人对话等)\n- 4-6: 可选回复(一般闲聊)\n- 7-8: 应该回复(直接提问、提及你)\n- 9-10: 必须回复(紧急情况、多次@你)\n只输出一个数字，不要其他内容。"}
            ]
        )
        # 获取返回内容并处理
        content = completion.choices[0].message.content
        debug(f"判断模型返回内容: {content}")
        # 移除所有非数字字符
        num_str = ''.join(c for c in content if c.isdigit() or c == '.')
        # 如果是空字符串，返回error:0
        if not num_str:
            return "error:0"
        # 若为浮点数则向上取整
        try:
            if "@" in message_content and str(bot_name) in message_content:
                message_content_len = int(len(message_content) - 10)
            else:
                message_content_len = len(message_content)
            num_str = int(float(num_str) + 0.4)
            if 提起名字:
                info("提起名字,兴趣度+5")
                num_str += 5
            if int(num_str) >= 10:
                num_str = 10
            if message_content_len <= 5 and 提起名字 != True:
                num_str -= (6 - message_content_len)
            return int(num_str)
        except ValueError:
            return "error:1"
    return 0



