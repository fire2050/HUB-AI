"""分流派单引擎 - 4类需求路由"""
import sys
import os
# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from hubai_base.scripts.logger import HubAILogger
except ImportError:
    sys.path.append(os.path.expanduser('~/.openclaw/skills/hubai-base/scripts'))
    from logger import HubAILogger

logger = HubAILogger.get_logger("smart-quotation.route_engine")

class RouteEngine:
    """分流派单引擎"""
    
    ROUTES = {
        "standard": {
            "name": "标准型",
            "description": "产品在库、价格政策匹配、库存充足、无定制",
            "auto_approve": True,
            "estimated_time": "5分钟",
            "agents": ["commerce"]
        },
        "solution": {
            "name": "方案型",
            "description": "多产品组合、需技术方案说明",
            "auto_approve": False,
            "estimated_time": "1-2天",
            "agents": ["tech", "commerce"]
        },
        "custom": {
            "name": "非标型",
            "description": "含定制需求、服务交付内容",
            "auto_approve": False,
            "estimated_time": "3-5天",
            "agents": ["tech", "commerce", "finance"]
        },
        "risky": {
            "name": "高风险",
            "description": "账期超长、毛利过低、新客户大额",
            "auto_approve": False,
            "estimated_time": "待定",
            "agents": ["sales_director", "finance_director"]
        }
    }
    
    @staticmethod
    def route(requirement_card: dict) -> dict:
        """根据需求卡判定需求类型并路由"""
        score = requirement_card.get("completeness_score", 0)
        issues = requirement_card.get("issues", [])
        warnings = requirement_card.get("warnings", [])
        
        # 高风险判定（优先检查）
        has_risk = any(w.get("type") in ["MARGIN_TOO_LOW", "PAYMENT_EXCEEDED"] for w in warnings)
        if has_risk:
            logger.info("Route decision: risky")
            return {**RouteEngine.ROUTES["risky"], "route_type": "risky"}
        
        # 非标型判定
        has_custom = any(i.get("type") == "CUSTOM_REQUIREMENT" for i in issues)
        if has_custom or score < 70:
            logger.info("Route decision: custom")
            return {**RouteEngine.ROUTES["custom"], "route_type": "custom"}
        
        # 方案型判定
        has_solution = any(w.get("type") == "SOLUTION_NEEDED" for w in warnings)
        if has_solution or (70 <= score < 90):
            logger.info("Route decision: solution")
            return {**RouteEngine.ROUTES["solution"], "route_type": "solution"}
        
        # 标准型（默认）
        logger.info("Route decision: standard")
        return {**RouteEngine.ROUTES["standard"], "route_type": "standard"}
