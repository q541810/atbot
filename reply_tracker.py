import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass
from threading import Lock

@dataclass
class GroupReplyState:
    """群组回复状态"""
    last_reply_time: float = None
    message_count: int = 0
    last_message_time: float = 0.0
    
    def __post_init__(self):
        if self.last_reply_time is None:
            self.last_reply_time = time.time()

class AsyncReplyTracker:
    """异步回复状态跟踪器"""
    
    def __init__(self):
        self._group_states: Dict[str, GroupReplyState] = {}
        self._lock = Lock()
    
    async def record_message(self, group_id: str) -> None:
        """记录收到的消息"""
        current_time = time.time()
        
        with self._lock:
            if group_id not in self._group_states:
                self._group_states[group_id] = GroupReplyState()
            
            state = self._group_states[group_id]
            state.message_count += 1
            state.last_message_time = current_time
    
    async def record_reply(self, group_id: str) -> None:
        """记录发送的回复"""
        current_time = time.time()
        
        with self._lock:
            if group_id not in self._group_states:
                self._group_states[group_id] = GroupReplyState()
            
            state = self._group_states[group_id]
            state.last_reply_time = current_time
            state.message_count = 0  # 重置消息计数
    
    async def get_state(self, group_id: str) -> GroupReplyState:
        """获取群组状态"""
        with self._lock:
            if group_id not in self._group_states:
                self._group_states[group_id] = GroupReplyState()
            return self._group_states[group_id]
    
    async def should_consider_reply(self, group_id: str, min_messages: int = 3, min_time_gap: float = 300.0) -> bool:
        """判断是否应该考虑回复
        
        Args:
            group_id: 群组ID
            min_messages: 最少消息数量（仅在已回复过的情况下生效）
            min_time_gap: 最小时间间隔（秒，已废弃，不再使用）
        
        Returns:
            是否应该考虑回复
        """
        state = await self.get_state(group_id)
        current_time = time.time()
        
        # 检查是否曾经回复过（通过判断last_reply_time是否为初始化时间）
        # 如果last_reply_time和当前时间差距很小（小于1分钟），说明是刚初始化的，从未回复过
        time_since_init = current_time - state.last_reply_time
        has_replied_before = time_since_init > 60  # 如果超过1分钟，认为已经回复过
        
        if not has_replied_before:
            # 首次回复，不需要检查条件，直接允许
            return True
        
        # 已经回复过，只检查消息数量，不再检查时间间隔
        # 检查消息数量
        if state.message_count < min_messages:
            return False
        
        return True
    
    async def reset_group_state(self, group_id: str) -> None:
        """重置群组状态"""
        with self._lock:
            if group_id in self._group_states:
                del self._group_states[group_id]
    
    async def get_all_states(self) -> Dict[str, GroupReplyState]:
        """获取所有群组状态（用于调试）"""
        with self._lock:
            return self._group_states.copy()

# 全局实例
reply_tracker = AsyncReplyTracker()