"""价格计算引擎 - 100% 确定性，绝不让大模型计算"""
import sys
import os
# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from hubai_base.scripts.db import HubAIDatabase
    from hubai_base.scripts.logger import HubAILogger
    from hubai_base.scripts.errors import QuotationError, ERROR_CODES
except ImportError:
    sys.path.append(os.path.expanduser('~/.openclaw/skills/hubai-base/scripts'))
    from db import HubAIDatabase
    from logger import HubAILogger
    from errors import QuotationError, ERROR_CODES

logger = HubAILogger.get_logger("smart-quotation.price_engine")

def calculate_price(product_code: str, quantity: int, customer_level: str = "standard") -> dict:
    """计算单行报价，返回完整价格信息"""
    db = HubAIDatabase()
    
    # 1. 获取产品标准价
    price = db.query_one("""
        SELECT * FROM product_price 
        WHERE product_code = ? AND status = 'active'
        AND (valid_to IS NULL OR valid_to >= datetime('now'))
        ORDER BY valid_from DESC LIMIT 1
    """, (product_code,))
    
    if not price:
        logger.error(f"Product price not found: {product_code}")
        raise QuotationError(
            code=ERROR_CODES["PRODUCT_PRICE_NOT_FOUND"]["code"],
            message=ERROR_CODES["PRODUCT_PRICE_NOT_FOUND"]["message"],
            details={"product_code": product_code}
        )
    
    # 2. 匹配价格策略（确定性规则）
    policy = db.query_one("""
        SELECT * FROM quotation_policy 
        WHERE status = 'active' 
        AND (customer_level = ? OR customer_level IS NULL)
        AND (valid_to IS NULL OR valid_to >= datetime('now'))
        ORDER BY priority DESC LIMIT 1
    """, (customer_level,))
    
    # 报价系统强制不打折扣，始终按报价数据源原价计算
    discount_rate = 1.0
    discount_note = "按报价数据源原价报价，不做折扣"
    
    # 3. 计算原价（确定性计算）
    unit_price_final = price["unit_price"] * discount_rate
    line_amount = unit_price_final * quantity
    
    # 4. 毛利率计算
    margin_rate = 0
    if price.get("cost_price") and price["cost_price"] > 0:
        margin_rate = (unit_price_final - price["cost_price"]) / unit_price_final
    
    # 5. 库存校验
    inventory = db.query_one("""
        SELECT available_quantity, reserved_quantity 
        FROM inventory WHERE product_code = ?
    """, (product_code,))
    
    inventory_ok = True
    if inventory:
        available = inventory["available_quantity"] - inventory["reserved_quantity"]
        inventory_ok = available >= quantity
    
    # 6. 记录审计日志
    HubAILogger.audit_log(
        action="quotation.price_calculate",
        user_id="system",
        details={
            "product_code": product_code,
            "quantity": quantity,
            "unit_price": price["unit_price"],
            "discount_rate": discount_rate,
            "line_amount": line_amount,
            "margin_rate": margin_rate
        }
    )
    
    logger.info(f"Price calculated: {product_code} x{quantity} = {line_amount}")
    
    return {
        "success": True,
        "product_code": product_code,
        "unit_price_original": price["unit_price"],
        "discount_rate": discount_rate,
        "discount_note": discount_note,
        "unit_price_final": unit_price_final,
        "quantity": quantity,
        "line_amount": line_amount,
        "cost_price": price.get("cost_price"),
        "margin_rate": margin_rate,
        "inventory_ok": inventory_ok,
        "policy_applied": policy["policy_code"] if policy else None
    }

def generate_quotation_lines(products: list, customer_level: str = "standard") -> list:
    """生成多行报价明细"""
    lines = []
    for item in products:
        line = calculate_price(
            product_code=item["product_code"],
            quantity=item["quantity"],
            customer_level=customer_level
        )
        lines.append(line)
    return lines
