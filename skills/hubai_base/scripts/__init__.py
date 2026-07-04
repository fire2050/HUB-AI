from .db import HubAIDatabase
from .logger import HubAILogger
from .auth import PermissionChecker
from .errors import HubAIError, QuotationError, DatabaseError, AuthError, ERROR_CODES, get_error_response
from .config import HubAIConfig
from .mcp_client import HubAIMCPClient
from .product_router import ProductRouter, ProductInfo
from .requirement_base import BaseRequirementHandler, RequirementField, RequirementTable
from .dialogue_base import BaseDialogueHandler, DialogueTemplate

__all__ = [
    'HubAIDatabase', 
    'HubAILogger', 
    'PermissionChecker',
    'HubAIError',
    'QuotationError',
    'DatabaseError',
    'AuthError',
    'ERROR_CODES',
    'get_error_response',
    'HubAIConfig',
    'HubAIMCPClient',
    'ProductRouter',
    'ProductInfo',
    'BaseRequirementHandler',
    'RequirementField',
    'RequirementTable',
    'BaseDialogueHandler',
    'DialogueTemplate'
]
__version__ = '1.1.0'  # 多产品架构增强版
