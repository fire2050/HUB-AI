from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserContext:
    user_id: str
    name: str
    role: str
    department: str | None


DEMO_USERS = {
    "u_sales_zhang": UserContext("u_sales_zhang", "张三", "sales", "华东销售部"),
    "u_sales_li": UserContext("u_sales_li", "李四", "sales", "华南销售部"),
    "u_mgr_east": UserContext("u_mgr_east", "王经理", "manager", "华东销售部"),
    "u_finance_admin": UserContext("u_finance_admin", "财务管理员", "finance_admin", None),
}


def get_user(user_id: str) -> UserContext:
    return DEMO_USERS.get(user_id, DEMO_USERS["u_sales_zhang"])


def role_label(role: str) -> str:
    return {
        "sales": "销售个人",
        "manager": "部门经理",
        "finance_admin": "财务管理员",
    }.get(role, role)


def scope_filter(user: UserContext) -> tuple[str, tuple]:
    if user.role == "finance_admin":
        return "1=1", ()
    if user.role == "manager":
        return "department = ?", (user.department,)
    return "salesperson = ?", (user.name,)
