from collections import deque
from typing import Dict, List, Optional
from read_config import config_manager

class ContextManager:
    """上下文记忆管理器，用于管理群聊的对话历史"""
    
    def __init__(self):
        """初始化上下文管理器"""
        # 获取配置
        self.config = config_manager.bot_config.get('context_memory', {})
        self.enabled = self.config.get('enabled', True)
        self.max_messages = self.config.get('max_messages', 10)
        self.max_message_length = self.config.get('max_message_length', 300)
        
        # 存储每个群聊的对话历史 {group_id: deque}
        self.group_histories: Dict[int, deque] = {}
    
    def add_message(self, group_id: int, user_name: str, message: str, is_bot: bool = False):
        """添加消息到对话历史
        
        Args:
            group_id: 群组ID
            user_name: 用户昵称
            message: 消息内容
            is_bot: 是否为机器人消息
        """
        if not self.enabled:
            return
        
        # 截断过长的消息
        if len(message) > self.max_message_length:
            message = message[:self.max_message_length] + "..."
        
        # 如果群组不存在，创建新的历史记录
        if group_id not in self.group_histories:
            self.group_histories[group_id] = deque(maxlen=self.max_messages)
        
        # 添加消息到历史记录
        role = "assistant" if is_bot else "user"
        content = f"{user_name}: {message}" if not is_bot else message
        
        self.group_histories[group_id].append({
            "role": role,
            "content": content
        })
    
    def get_context_messages(self, group_id: int) -> List[Dict[str, str]]:
        """获取指定群组的上下文消息列表
        
        Args:
            group_id: 群组ID
            
        Returns:
            消息列表，格式为 [{"role": "user/assistant", "content": "消息内容"}, ...]
        """
        if not self.enabled or group_id not in self.group_histories:
            return []
        
        return list(self.group_histories[group_id])
    
    def clear_group_history(self, group_id: int):
        """清空指定群组的对话历史
        
        Args:
            group_id: 群组ID
        """
        if group_id in self.group_histories:
            self.group_histories[group_id].clear()
    
    def get_group_message_count(self, group_id: int) -> int:
        """获取指定群组的消息数量
        
        Args:
            group_id: 群组ID
            
        Returns:
            消息数量
        """
        if group_id not in self.group_histories:
            return 0
        return len(self.group_histories[group_id])
    
    def is_enabled(self) -> bool:
        """检查上下文记忆功能是否启用
        
        Returns:
            是否启用
        """
        return self.enabled

# 创建全局上下文管理器实例
context_manager = ContextManager()