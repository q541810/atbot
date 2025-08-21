import sqlite3
import os
import threading
from typing import Optional, Dict

class UserCache:
    def __init__(self, db_path: str = "user_cache.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    nickname TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def update_user_info(self, user_id: int, nickname: str):
        """更新用户基本信息"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO users (user_id, nickname, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (user_id, nickname))
                conn.commit()
    
    def get_user_nickname(self, user_id: int) -> Optional[str]:
        """获取用户昵称"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT nickname FROM users WHERE user_id = ?
                """, (user_id,))
                result = cursor.fetchone()
                return result[0] if result else None
    
    def is_user_cached(self, user_id: int) -> bool:
        """检查用户信息是否已缓存"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM users WHERE user_id = ?
                """, (user_id,))
                return cursor.fetchone() is not None
    
    def clear_cache(self):
        """清空缓存"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users")
                conn.commit()