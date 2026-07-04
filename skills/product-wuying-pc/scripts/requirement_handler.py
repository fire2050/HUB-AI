"""无影云电脑需求处理器"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'hubai_base', 'scripts'))

from requirement_base import BaseRequirementHandler, RequirementTable

class WuyingPCRequirementHandler(BaseRequirementHandler):
    """无影云电脑需求处理器"""
    
    def __init__(self):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'requirement.json'
        )
        super().__init__(config_path)
    
    def _load_config(self) -> RequirementTable:
        """加载无影云电脑需求表配置"""
        return super()._load_config()
