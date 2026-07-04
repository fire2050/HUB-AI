"""HubAI 配置管理模块"""
import json
import os
from typing import Dict, Any, Optional

class HubAIConfig:
    """HubAI 统一配置管理"""
    
    _instance = None
    _config = {}
    
    def __new__(cls, config_dir: str = None, env: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(config_dir, env)
        return cls._instance
    
    def _init(self, config_dir: str = None, env: str = None):
        if config_dir is None:
            config_dir = os.path.expanduser("~/hubai/skills/hubai-base/config")
        
        if env is None:
            env = os.environ.get("HUbai_ENV", "development")
        
        self.config_dir = config_dir
        self.env = env
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        # 1. 加载默认配置
        default_config = os.path.join(self.config_dir, "default.json")
        if os.path.exists(default_config):
            with open(default_config, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        
        # 2. 加载环境配置（覆盖默认）
        env_config = os.path.join(self.config_dir, f"{self.env}.json")
        if os.path.exists(env_config):
            with open(env_config, 'r', encoding='utf-8') as f:
                env_data = json.load(f)
                self._deep_update(self._config, env_data)
    
    def _deep_update(self, base: dict, update: dict):
        """深度更新字典"""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default=None, type_hint=None) -> Any:
        """获取配置项，支持点号路径"""
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        if type_hint and value is not None:
            try:
                value = type_hint(value)
            except (ValueError, TypeError):
                return default
        
        return value
    
    def get_database_config(self, db_name: str = "default") -> Dict:
        """获取数据库配置"""
        return self.get(f"database.{db_name}", {})
    
    def get_quotation_rules(self) -> Dict:
        """获取报价规则配置"""
        return self.get("quotation.rules", {})
    
    def get_approval_rules(self) -> Dict:
        """获取审批规则配置"""
        return self.get("approval.rules", {})
    
    def reload(self):
        """热更新：重新加载配置文件"""
        self._config = {}
        self._load_config()
    
    def validate(self) -> list:
        """校验配置完整性"""
        errors = []
        required_keys = [
            "database.default.type",
            "database.default.path",
            "quotation.max_discount_rate",
            "approval.auto_approve_threshold"
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                errors.append(f"Missing required config: {key}")
        
        return errors
