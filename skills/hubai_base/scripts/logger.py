"""HubAI 统一日志审计模块"""
import logging
import os
import json
from datetime import datetime

class HubAILogger:
    _loggers = {}
    
    @staticmethod
    def get_logger(name: str, log_dir: str = None) -> logging.Logger:
        if name in HubAILogger._loggers:
            return HubAILogger._loggers[name]
        
        if log_dir is None:
            log_dir = os.path.expanduser("~/hubai/workspace/logs")
        os.makedirs(log_dir, exist_ok=True)
        
        logger = logging.getLogger(f"hubai.{name}")
        logger.setLevel(logging.DEBUG)
        
        if logger.handlers:
            return logger
        
        log_file = os.path.join(log_dir, f"{name}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        HubAILogger._loggers[name] = logger
        return logger
    
    @staticmethod
    def audit_log(action: str, user_id: str, details: dict, log_dir: str = None):
        if log_dir is None:
            log_dir = os.path.expanduser("~/hubai/workspace/logs/audit")
        os.makedirs(log_dir, exist_ok=True)
        
        audit_file = os.path.join(log_dir, f"audit_{datetime.now().strftime('%Y%m')}.log")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user_id": user_id,
            "details": details
        }
        with open(audit_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
