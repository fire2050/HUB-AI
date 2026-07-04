"""HubAI 统一错误处理模块"""

class HubAIError(Exception):
    """HubAI 基础异常类"""
    
    def __init__(self, code: str, message: str, details: dict = None, 
                 http_status: int = 500):
        self.code = code
        self.message = message
        self.details = details or {}
        self.http_status = http_status
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "http_status": self.http_status
        }

class QuotationError(HubAIError):
    """报价相关异常"""
    pass

class DatabaseError(HubAIError):
    """数据库相关异常"""
    pass

class AuthError(HubAIError):
    """权限相关异常"""
    pass

# 错误码定义
ERROR_CODES = {
    # 产品相关
    "PRODUCT_NOT_FOUND": {"code": "Q001", "message": "产品不存在", "status": 404},
    "PRODUCT_INACTIVE": {"code": "Q002", "message": "产品未上架", "status": 400},
    "PRODUCT_PRICE_NOT_FOUND": {"code": "Q003", "message": "产品无有效价格", "status": 404},
    
    # 库存相关
    "INVENTORY_SHORTAGE": {"code": "Q101", "message": "库存不足", "status": 400},
    "INVENTORY_LOCKED": {"code": "Q102", "message": "库存已被锁定", "status": 409},
    
    # 价格相关
    "DISCOUNT_EXCEEDED": {"code": "Q201", "message": "折扣超出权限", "status": 403},
    "MARGIN_TOO_LOW": {"code": "Q202", "message": "毛利率过低", "status": 400},
    "PRICE_EXPIRED": {"code": "Q203", "message": "价格已过期", "status": 400},
    
    # 权限相关
    "PERMISSION_DENIED": {"code": "A001", "message": "权限不足", "status": 403},
    "APPROVAL_REQUIRED": {"code": "A002", "message": "需要审批", "status": 403},
    
    # 系统相关
    "DATABASE_ERROR": {"code": "S001", "message": "数据库错误", "status": 500},
    "CONFIG_ERROR": {"code": "S002", "message": "配置错误", "status": 500},
    "MCP_CONNECTION_ERROR": {"code": "S003", "message": "外部系统连接失败", "status": 503}
}

def get_error_response(error_code: str, **kwargs) -> dict:
    """获取标准错误响应"""
    error_info = ERROR_CODES.get(error_code, {
        "code": "U001", 
        "message": "未知错误", 
        "status": 500
    })
    
    response = {
        "success": False,
        "error_code": error_info["code"],
        "error_message": error_info["message"],
        "http_status": error_info["status"]
    }
    
    if kwargs:
        response["details"] = kwargs
    
    return response
