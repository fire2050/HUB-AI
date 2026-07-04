"""HubAI 基础能力包"""

from .scripts.db import HubAIDatabase
from .scripts.logger import HubAILogger
from .scripts.auth import PermissionChecker
from .scripts.errors import (
    HubAIError,
    DatabaseError,
    QuotationError,
    AuthError,
    get_error_response
)
from .scripts.config import HubAIConfig
from .scripts.mcp_client import HubAIMCPClient

__version__ = "1.0.0"
__all__ = [
    'HubAIDatabase',
    'HubAILogger',
    'PermissionChecker',
    'HubAIError', 'DatabaseError', 'QuotationError', 'AuthError',
    'get_error_response',
    'HubAIConfig',
    'HubAIMCPClient'
]
