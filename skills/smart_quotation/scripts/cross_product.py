"""跨产品组合报价 - 支持同时购买多个产品的组合报价"""
from typing import List, Dict

class CrossProductQuotation:
    """跨产品组合报价"""
    
    def __init__(self):
        self.items = []
    
    def add_product(self, product_code: str, requirement_data: dict, 
                   quotation_result: dict):
        """添加产品报价项"""
        self.items.append({
            "product_code": product_code,
            "requirement": requirement_data,
            "quotation": quotation_result
        })
    
    def generate_combined_quotation(self) -> dict:
        """生成组合报价"""
        total_amount = sum(
            item["quotation"].get("total_amount", 0) 
            for item in self.items
        )
        
        discount_rate = self._calculate_bundle_discount()
        final_amount = total_amount * discount_rate
        
        return {
            "quotation_type": "combined",
            "items_count": len(self.items),
            "items": self.items,
            "original_amount": total_amount,
            "discount_rate": discount_rate,
            "final_amount": final_amount,
            "summary": f"组合报价共计 {len(self.items)} 个产品，原价 ¥{total_amount:,.2f}，折扣后 ¥{final_amount:,.2f}"
        }
    
    def _calculate_bundle_discount(self) -> float:
        """计算组合折扣"""
        if len(self.items) >= 3:
            return 0.95  # 95折
        elif len(self.items) >= 2:
            return 0.98  # 98折
        return 1.0
    
    def clear(self):
        """清空报价项"""
        self.items = []
