"""多轮会话管理器 - 管理报价对话的完整生命周期"""
import json
import time
from typing import Dict, Optional
from datetime import datetime, timedelta

class SessionManager:
    """会话管理器"""
    
    SESSION_TIMEOUT = 1800  # 30分钟超时
    
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
    
    def create_session(self, user_id: str, channel: str) -> str:
        """创建新会话"""
        session_id = f"{channel}_{user_id}_{int(time.time())}"
        self.sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "channel": channel,
            "product_code": None,
            "collected_data": {},
            "quotation_data": None,
            "status": "collecting",  # collecting | confirming | generating | completed
            "created_at": datetime.now(),
            "last_active": datetime.now()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """获取会话（自动清理过期会话）"""
        self._cleanup_expired()
        session = self.sessions.get(session_id)
        if session:
            session["last_active"] = datetime.now()
        return session
    
    def update_session(self, session_id: str, updates: dict):
        """更新会话数据"""
        session = self.sessions.get(session_id)
        if session:
            session.update(updates)
            session["last_active"] = datetime.now()
    
    def _cleanup_expired(self):
        """清理过期会话"""
        now = datetime.now()
        expired = [
            sid for sid, s in self.sessions.items()
            if now - s["last_active"] > timedelta(seconds=self.SESSION_TIMEOUT)
        ]
        for sid in expired:
            del self.sessions[sid]
    
    def get_active_sessions(self) -> list:
        """获取所有活跃会话"""
        self._cleanup_expired()
        return list(self.sessions.values())
