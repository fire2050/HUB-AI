"""审批流程引擎"""
import sys
import os
# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from hubai_base.scripts.logger import HubAILogger
    from hubai_base.scripts.auth import PermissionChecker
except ImportError:
    sys.path.append(os.path.expanduser('~/.openclaw/skills/hubai-base/scripts'))
    from logger import HubAILogger
    from auth import PermissionChecker

logger = HubAILogger.get_logger("smart-quotation.approval_engine")

class ApprovalEngine:
    """审批流程引擎"""
    
    APPROVAL_CHAINS = {
        "standard": {
            "auto_approve": True,
            "steps": []
        },
        "solution": {
            "auto_approve": False,
            "steps": [
                {"step": 1, "role": "tech_lead", "name": "技术方案确认"},
                {"step": 2, "role": "sales_manager", "name": "商务条款确认"}
            ]
        },
        "custom": {
            "auto_approve": False,
            "steps": [
                {"step": 1, "role": "tech_lead", "name": "技术可行性评审"},
                {"step": 2, "role": "sales_manager", "name": "商务条款评审"},
                {"step": 3, "role": "finance_manager", "name": "财务合规评审"}
            ]
        },
        "risky": {
            "auto_approve": False,
            "steps": [
                {"step": 1, "role": "sales_director", "name": "销售总监审批"},
                {"step": 2, "role": "finance_director", "name": "财务总监审批"},
                {"step": 3, "role": "ceo", "name": "总经理终审"}
            ]
        }
    }
    
    @staticmethod
    def check_approval(quotation_data: dict, route_type: str) -> dict:
        """检查是否需要审批"""
        chain = ApprovalEngine.APPROVAL_CHAINS.get(route_type, ApprovalEngine.APPROVAL_CHAINS["standard"])
        
        if chain["auto_approve"]:
            return {
                "approval_required": False,
                "auto_approved": True,
                "steps": []
            }
        
        # 检查折扣权限
        user_role = quotation_data.get("user_role", "sales")
        max_discount = quotation_data.get("max_discount_rate", 1.0)
        
        permission = PermissionChecker.check_discount_permission(user_role, max_discount)
        
        result = {
            "approval_required": True,
            "auto_approved": False,
            "steps": chain["steps"],
            "permission_check": permission
        }
        
        logger.info(f"Approval check: route={route_type}, required={result['approval_required']}")
        return result
    
    @staticmethod
    def create_approval_record(quotation_no: str, step: int, approver_role: str) -> dict:
        """创建审批记录"""
        return {
            "quotation_no": quotation_no,
            "step": step,
            "approver_role": approver_role,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }

from datetime import datetime
