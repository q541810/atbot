import asyncio
import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from log import debug, info, warning
from openai import OpenAI
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
        client = OpenAI(
            base_url=url,
            api_key=key,
        )
        completion = client.chat.completions.create(
            model=model,
            temperature=0.5,
            max_tokens=2,
            messages=[
                {"role": "system", "content": f"你叫{bot_name}，消息记录:{消息记录}请输出你对{message}的感兴趣的程度且只输出这段数字(0~10),不能带有其他的任何的东西!不能换行！只能输出一个数字！。你的人设：{bot_Prompt}，认为和你没太大关系就可以填2，为6就代表你认为大概可以回复（你拿不准），为8就代表你觉得没啥问题，为10就代表你认为必须。回复判断标准：如果消息直接提到机器人或询问问题，应该回复。 如果消息是日常闲聊且适合参与，并且你认为他会感兴趣，可以回复。 如果消息是纯表情、无意义内容或私人对话，不应回复（你可以按你自己的判断输出0~10的任意一个数字）"}
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



