import json
import websocket
import threading
import time
from typing import Optional, Dict, Any
from user_cache import UserCache

class UserInfoFetcher:
    def __init__(self, ws: websocket.WebSocket, user_cache: UserCache):
        self.ws = ws
        self.user_cache = user_cache
        self.pending_requests = {}
        self.request_id_counter = 1000
        self.lock = threading.Lock()
    
    def _generate_request_id(self) -> str:
        """生成请求ID"""
        with self.lock:
            self.request_id_counter += 1
            return f"user_info_{self.request_id_counter}"
    
    def _send_api_request(self, action: str, params: Dict[str, Any]) -> Optional[str]:
        """发送API请求"""
        try:
            request_id = self._generate_request_id()
            request_data = {
                "action": action,
                "params": params,
                "echo": request_id
            }
            
            self.ws.send(json.dumps(request_data))
            return request_id
        except Exception as e:
            print(f"发送API请求失败: {e}")
            return None
    
    def fetch_user_info(self, user_id: int) -> bool:
        """获取用户信息"""
        # 检查是否已缓存
        if self.user_cache.is_user_cached(user_id):
            return True
        
        try:
            # 获取用户基本信息
            user_request_id = self._send_api_request("get_stranger_info", {
                "user_id": user_id
            })
            
            if user_request_id:
                self.pending_requests[user_request_id] = {
                    "type": "user_info",
                    "user_id": user_id
                }
            
            return True
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            return False
    
    def handle_api_response(self, response_data: Dict[str, Any]):
        """处理API响应"""
        echo = response_data.get("echo")
        if not echo or echo not in self.pending_requests:
            return
        
        request_info = self.pending_requests.pop(echo)
        
        if response_data.get("status") != "ok":
            print(f"API请求失败: {response_data.get('msg', '未知错误')}")
            return
        
        data = response_data.get("data", {})
        
        try:
            if request_info["type"] == "user_info":
                nickname = data.get("nickname", "")
                if nickname:
                    self.user_cache.update_user_info(request_info["user_id"], nickname)
                    print(f"缓存用户信息: {request_info['user_id']} -> {nickname}")
        
        except Exception as e:
            print(f"处理用户信息响应失败: {e}")
    
    def get_user_display_name(self, user_id: int) -> str:
        """获取用户显示名称"""
        # 先尝试从缓存获取
        cached_name = self.user_cache.get_user_nickname(user_id)
        if cached_name:
            return cached_name
        
        # 如果没有缓存，异步获取用户信息
        self.fetch_user_info(user_id)
        
        # 返回QQ号作为临时显示
        return str(user_id)