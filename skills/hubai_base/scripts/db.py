"""HubAI 数据库连接与 ORM 封装"""
import sqlite3
import os
from typing import Optional, Dict, List
from contextlib import contextmanager

class HubAIDatabase:
    _instance = None
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(db_path)
        return cls._instance
    
    def _init(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.expanduser("~/hubai/workspace/data/hubai.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
    
    @contextmanager
    def cursor(self):
        cursor = self._connection.cursor()
        try:
            yield cursor
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            raise e
        finally:
            cursor.close()
    
    def execute(self, sql: str, params: tuple = ()) -> int:
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount
    
    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        with self.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None
    
    def query_all(self, sql: str, params: tuple = ()) -> List[Dict]:
        with self.cursor() as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
    
    def close(self):
        if self._connection:
            self._connection.close()
            HubAIDatabase._instance = None
