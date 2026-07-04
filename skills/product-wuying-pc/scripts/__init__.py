# 兼容直接脚本导入的方式（避免 relative import 错误）
import sys
import os

# 确保当前目录在路径中
sys.path.insert(0, os.path.dirname(__file__))
# 确保 hubai_base 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'hubai_base', 'scripts'))

try:
    from requirement_handler import WuyingPCRequirementHandler
    from dialogue_handler import WuyingPCDialogueHandler
    from price_engine import WuyingPCPriceEngine
except ImportError:
    # 包模式导入（作为 package 导入时）
    from .requirement_handler import WuyingPCRequirementHandler
    from .dialogue_handler import WuyingPCDialogueHandler
    from .price_engine import WuyingPCPriceEngine

__all__ = [
    'WuyingPCRequirementHandler',
    'WuyingPCDialogueHandler',
    'WuyingPCPriceEngine'
]
__version__ = '1.0.0'
