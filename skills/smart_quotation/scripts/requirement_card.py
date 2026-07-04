"""需求卡生成引擎"""
import sys
import os
# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from hubai_base.scripts.db import HubAIDatabase
    from hubai_base.scripts.logger import HubAILogger
    from smart_quotation.scripts.rule_validator import RuleValidator
except ImportError:
    sys.path.append(os.path.expanduser('~/.openclaw/skills/hubai-base/scripts'))
    from db import HubAIDatabase
    from logger import HubAILogger
    from rule_validator import RuleValidator

logger = HubAILogger.get_logger("smart-quotation.requirement_card")

def generate_requirement_card(requirement: dict) -> dict:
    """生成需求卡"""
    validator = RuleValidator()
    validation_result = validator.validate(requirement)
    
    # 计算缺失字段
    missing_fields = []
    if not requirement.get("customer_company"):
        missing_fields.append("customer_company")
    if not requirement.get("products"):
        missing_fields.append("products")
    
    card = {
        "card_no": f"QC-{datetime.now().strftime('%Y%m%d')}-{os.urandom(4).hex()}",
        "requirement": requirement,
        "completeness_score": validation_result["completeness_score"],
        "missing_fields": missing_fields,
        "issues": validation_result["issues"],
        "warnings": validation_result["warnings"],
        "can_auto_quote": validation_result["can_auto_quote"],
        "created_at": datetime.now().isoformat()
    }
    
    logger.info(f"Requirement card generated: {card['card_no']}, score={card['completeness_score']}")
    return card

from datetime import datetime
