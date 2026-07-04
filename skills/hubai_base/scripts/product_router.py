"""产品路由引擎 - 自动识别对话中的产品，路由到对应 Skill"""
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ProductInfo:
    """产品信息"""
    code: str              # 产品编码
    name: str              # 产品名称
    category: str           # 产品分类编码
    category_name: str      # 产品分类名称
    skill_name: str          # 对应 Skill 名称
    keywords: List[str]      # 关键词列表
    database_table: str      # 数据库表名
    pricing_model: str       # 定价模型
    priority: int = 100      # 优先级
    description: str = ""    # 产品描述
    version: str = "1.0.0"   # 版本

class ProductRouter:
    """产品路由引擎"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'products')
        self.config_dir = config_dir
        self.products = self._load_products()
    
    def _load_products(self) -> Dict[str, ProductInfo]:
        """加载所有产品配置"""
        products = {}
        if not os.path.exists(self.config_dir):
            return products
        
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.config_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    product = ProductInfo(
                        code=config['code'],
                        name=config['name'],
                        category=config['category'],
                        category_name=config.get('category_name', config['category']),
                        skill_name=config['skill_name'],
                        keywords=config.get('keywords', []),
                        database_table=config.get('database_table', f"product_{config['code'].replace('-', '_')}"),
                        pricing_model=config.get('pricing_model', 'default'),
                        priority=config.get('priority', 100),
                        description=config.get('description', ''),
                        version=config.get('version', '1.0.0')
                    )
                    products[product.code] = product
        return products
    
    def detect_product(self, dialogue_text: str) -> List[ProductInfo]:
        """从对话文本中识别产品，按匹配度排序"""
        matched = []
        text = dialogue_text.lower()
        
        for product in self.products.values():
            match_count = sum(1 for kw in product.keywords if kw.lower() in text)
            if match_count > 0:
                matched.append((product, match_count))
        
        matched.sort(key=lambda x: (-x[1], -x[0].priority))
        return [p[0] for p in matched]
    
    def get_skill_for_product(self, product_code: str) -> Optional[str]:
        """获取产品对应的 Skill 名称"""
        product = self.products.get(product_code)
        return product.skill_name if product else None
    
    def register_product(self, product_info: ProductInfo):
        """动态注册产品（支持热更新）"""
        self.products[product_info.code] = product_info
    
    def get_all_products(self) -> List[ProductInfo]:
        """获取所有已注册产品"""
        return list(self.products.values())
    
    def get_products_by_category(self, category: str) -> List[ProductInfo]:
        """按分类获取产品"""
        return [p for p in self.products.values() if p.category == category]
