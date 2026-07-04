"""HubAI RBAC 权限校验模块"""

class PermissionChecker:
    ROLES = {
        "sales": {"max_discount": 0.9, "can_approve": False},
        "sales_manager": {"max_discount": 0.8, "can_approve": True},
        "sales_director": {"max_discount": 0.7, "can_approve": True},
        "finance_director": {"max_discount": 0.6, "can_approve": True},
        "admin": {"max_discount": 0.5, "can_approve": True}
    }
    
    @staticmethod
    def check_discount_permission(user_role: str, discount_rate: float) -> dict:
        role = PermissionChecker.ROLES.get(user_role, PermissionChecker.ROLES["sales"])
        allowed = discount_rate >= role["max_discount"]
        return {
            "allowed": allowed,
            "max_discount": role["max_discount"],
            "need_approval": not allowed,
            "approver_role": "sales_director" if not allowed else None
        }
    
    @staticmethod
    def can_approve(user_role: str) -> bool:
        role = PermissionChecker.ROLES.get(user_role, {})
        return role.get("can_approve", False)
