import asyncio
import random
import json
import time
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
from read_config import get_reply_config, get_estimate_model_config, get_bot_info
from reply_tracker import reply_tracker

class SmartReplyManager:
    """智能回复管理器"""
    
    def __init__(self):
        self.reply_config = get_reply_config()
        self.estimate_config = get_estimate_model_config()
        self.client: Optional[AsyncOpenAI] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化AI客户端"""
        if not self.estimate_config:
            print("警告: 未找到estimate_model配置，LLM判断功能将不可用")
            return
        
        try:
            self.client = AsyncOpenAI(
                api_key=self.estimate_config.get('key'),
                base_url=self.estimate_config.get('url')
            )
            print(f"已初始化判断模型: {self.estimate_config.get('name')}")
        except Exception as e:
            print(f"初始化判断模型失败: {e}")
            self.client = None
    
    async def should_reply_probability(self) -> bool:
        """基于概率判断是否应该回复"""
        if not self.reply_config:
            return False
        
        probability_percent = self.reply_config.get('reply_probability', 0.0)
        probability = probability_percent / 100.0  # 将百分比转换为小数
        result = random.random() < probability
        return result
    
    async def should_reply_conditions(self, group_id: str) -> bool:
        """基于条件判断是否应该回复"""
        if not self.reply_config:
            return False
        
        min_messages = self.reply_config.get('reply_messagelength', 3)
        min_time_minutes = self.reply_config.get('reply_messagetime', 5)
        min_time_gap = min_time_minutes * 60  # 将分钟转换为秒
        
        result = await reply_tracker.should_consider_reply(
            group_id, min_messages, min_time_gap
        )
        
        state = await reply_tracker.get_state(group_id)
        time_since_init = time.time() - state.last_reply_time
        has_replied_before = time_since_init > 60
        
        if has_replied_before:
            None
        else:
            None
        
        return result
    
    async def should_reply_llm_judge(self, message: str, context: str = "") -> bool:
        """使用LLM判断是否应该回复"""
        if not self.client or not self.estimate_config:
            print("LLM判断不可用，跳过")
            return False
        
        try:
            bot_info = get_bot_info()
            bot_name = bot_info.get('nickname', '麦麦')
            prompt = f"""你是一个聊天机器人的回复判断助手,这个机器人叫"{bot_name}"。请判断在以下情况下是否应该回复用户的消息。
上下文信息：{context if context else "无"}
用户消息：{message}
判断标准：
1. 如果消息直接提到机器人或询问问题，应该回复
2. 虽然消息是日常闲聊且适合参与，但尽量不要回复，除非你认为特别恰当
3. 如果消息是纯表情、无意义内容或私人对话，不应回复

请只回答 "是" 或 "否"，不要解释原因或者输出其他任何东西。"""
            
            response = await self.client.chat.completions.create(
                model=self.estimate_config.get('name', 'gpt-3.5-turbo'),
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.estimate_config.get('temp', 0.3),
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip()
            should_reply = "是" in result or "yes" in result.lower()
            
            print(f"LLM判断结果: {result} -> {'应该回复' if should_reply else '不应回复'}")
            return should_reply
            
        except Exception as e:
            print(f"LLM判断失败: {e}")
            return False
    
    async def should_reply(self, group_id: str, message: str, context: str = "") -> bool:
        """综合判断是否应该回复
        
        Args:
            group_id: 群组ID
            message: 消息内容
            context: 上下文信息
        
        Returns:
            是否应该回复
        """
        # 检查消息是否包含bot名字
        from read_config import bot
        contains_bot_name = bot.nickname in message
        
        if contains_bot_name:
            print(f"消息包含bot名字 '{bot.nickname}'，跳过概率检查，直接进行LLM判断")
        else:
            # 1. 首先检查概率
            if not await self.should_reply_probability():
                return False
        
        # 2. 检查回复条件（消息数量和时间间隔）
        if not await self.should_reply_conditions(group_id):
            print(f"回复条件未满足，不回复")
            return False
        
        # 3. 使用LLM进行最终判断
        should_reply = await self.should_reply_llm_judge(message, context)
        print(f"=== 智能回复判断结束: {'回复' if should_reply else '不回复'} ===\n")
        return should_reply
    
    async def record_message(self, group_id: str):
        """记录收到的消息"""
        await reply_tracker.record_message(group_id)
    
    async def record_reply(self, group_id: str):
        """记录发送的回复"""
        await reply_tracker.record_reply(group_id)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            "reply_config": self.reply_config,
            "estimate_config": {
                "model_name": self.estimate_config.get('name') if self.estimate_config else None,
                "provider": self.estimate_config.get('provider') if self.estimate_config else None,
                "available": self.client is not None
            }
        }

# 全局实例
smart_reply_manager = SmartReplyManager()