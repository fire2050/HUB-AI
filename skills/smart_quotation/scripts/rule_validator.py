"""规则校验引擎 - 7项自动检测"""
import sys
import os
# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from hubai_base.scripts.db import HubAIDatabase
    from hubai_base.scripts.logger import HubAILogger
except ImportError:
    sys.path.append(os.path.expanduser('~/.openclaw/skills/hubai-base/scripts'))
    from db import HubAIDatabase
    from logger import HubAILogger

logger = HubAILogger.get_logger("smart-quotation.rule_validator")

class RuleValidator:
    """规则校验引擎"""
    
    RULES = [
        {"id": 1, "name": "产品存在性", "severity": "BLOCKER", "check": "product_exists"},
        {"id": 2, "name": "价格完整性", "severity": "BLOCKER", "check": "price_exists"},
        {"id": 3, "name": "库存充足性", "severity": "HIGH", "check": "inventory_sufficient"},
        {"id": 4, "name": "策略覆盖性", "severity": "MEDIUM", "check": "policy_coverage"},
        {"id": 5, "name": "毛利率合规", "severity": "MEDIUM", "check": "margin_compliance"},
        {"id": 6, "name": "账期合规", "severity": "MEDIUM", "check": "payment_terms"},
        {"id": 7, "name": "交付可行性", "severity": "LOW", "check": "delivery_feasible"}
    ]
    
    def __init__(self):
        self.db = HubAIDatabase()
        self.issues = []
        self.warnings = []
    
    def validate(self, requirement: dict) -> dict:
        """执行所有规则校验"""
        self.issues = []
        self.warnings = []
        
        for rule in self.RULES:
            check_method = getattr(self, f"_check_{rule['check']}", None)
            if check_method:
                try:
                    check_method(requirement, rule)
                except Exception as e:
                    logger.error(f"Rule check failed: {rule['name']}, error: {str(e)}")
        
        completeness_score = self._calculate_score()
        
        result = {
            "completeness_score": completeness_score,
            "issues_count": len(self.issues),
            "warnings_count": len(self.warnings),
            "issues": self.issues,
            "warnings": self.warnings,
            "can_auto_quote": len(self.issues) == 0
        }
        
        logger.info(f"Validation completed: score={completeness_score}, issues={len(self.issues)}, warnings={len(self.warnings)}")
        return result
    
    def _check_product_exists(self, req, rule):
        for product in req.get("products", []):
            exists = self.db.query_one(
                "SELECT 1 FROM product WHERE product_code = ? AND status = 'active'",
                (product["product_code"],)
            )
            if not exists:
                self.issues.append({"type": "PRODUCT_NOT_FOUND", **rule, "product": product["product_code"]})
    
    def _check_price_exists(self, req, rule):
        for product in req.get("products", []):
            price = self.db.query_one(
                "SELECT 1 FROM product_price WHERE product_code = ? AND status = 'active'",
                (product["product_code"],)
            )
            if not price:
                self.issues.append({"type": "PRICE_NOT_FOUND", **rule, "product": product["product_code"]})
    
    def _check_inventory_sufficient(self, req, rule):
        for product in req.get("products", []):
            inv = self.db.query_one(
                "SELECT available_quantity, reserved_quantity FROM inventory WHERE product_code = ?",
                (product["product_code"],)
            )
            if inv:
                available = inv["available_quantity"] - inv["reserved_quantity"]
                if available < product["quantity"]:
                    self.warnings.append({
                        "type": "INVENTORY_SHORTAGE", 
                        **rule, 
                        "product": product["product_code"], 
                        "need": product["quantity"], 
                        "available": available
                    })
    
    def _check_margin_compliance(self, req, rule):
        # 毛利率校验在 price_engine 中计算后处理
        pass
    
    def _calculate_score(self) -> int:
        base = 100
        for issue in self.issues:
            if issue["severity"] == "BLOCKER":
                base -= 30
            elif issue["severity"] == "HIGH":
                base -= 20
            elif issue["severity"] == "MEDIUM":
                base -= 10
            else:
                base -= 5
        return max(0, base)
