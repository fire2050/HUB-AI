"""需求表基类 - 所有产品需求表的统一基类"""
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class RequirementField:
    """需求字段定义"""
    field_code: str              # 字段编码
    field_name: str              # 字段名称
    field_type: str             # 类型：text | number | select | multiselect | boolean | date
    required: bool = False       # 必填
    options: List[str] = None    # 选项（select/multiselect）
    default: Any = None           # 默认值
    description: str = ""         # 字段说明
    validation: str = ""          # 验证规则
    priority: int = 1            # 优先级（1-5，1最高）
    category: str = ""            # 字段分组

@dataclass
class RequirementTable:
    """需求表定义"""
    product_code: str
    product_name: str
    version: str
    fields: List[RequirementField]
    categories: List[str] = None    # 字段分组

class BaseRequirementHandler(ABC):
    """需求表处理基类"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.requirement_table = self._load_config()
        self.collected_data = {}
    
    @abstractmethod
    def _load_config(self) -> RequirementTable:
        """加载需求表配置"""
        if not self.config_path or not os.path.exists(self.config_path):
            return RequirementTable(
                product_code="default",
                product_name="默认产品",
                version="1.0.0",
                fields=[]
            )
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        fields = []
        for f_config in config.get('fields', []):
            field = RequirementField(
                field_code=f_config['field_code'],
                field_name=f_config['field_name'],
                field_type=f_config['field_type'],
                required=f_config.get('required', False),
                options=f_config.get('options'),
                default=f_config.get('default'),
                description=f_config.get('description', ''),
                validation=f_config.get('validation', ''),
                priority=f_config.get('priority', 3),
                category=f_config.get('category', '')
            )
            fields.append(field)
        
        return RequirementTable(
            product_code=config.get('product_code', 'default'),
            product_name=config.get('product_name', '默认产品'),
            version=config.get('version', '1.0.0'),
            fields=fields,
            categories=config.get('categories')
        )
    
    def get_missing_fields(self, collected_data: Dict = None) -> List[RequirementField]:
        """获取缺失的必填字段，按优先级排序"""
        data = collected_data or self.collected_data
        missing = []
        
        for field in self.requirement_table.fields:
            if field.required and field.field_code not in data:
                missing.append(field)
        
        missing.sort(key=lambda x: x.priority)
        return missing
    
    def validate_field(self, field_code: str, value: Any) -> tuple[bool, str]:
        """验证字段值"""
        field = self.get_field_by_code(field_code)
        if not field:
            return False, f"字段 {field_code} 不存在"
        
        if field.required and value is None:
            return False, f"字段 {field.field_name} 是必填项"
        
        return True, "验证通过"
    
    def get_field_by_code(self, field_code: str) -> Optional[RequirementField]:
        """根据编码获取字段定义"""
        return next((f for f in self.requirement_table.fields 
                    if f.field_code == field_code), None)
    
    def get_completeness_score(self, collected_data: Dict = None) -> int:
        """计算需求完整性评分（0-100）"""
        data = collected_data or self.collected_data
        required_fields = [f for f in self.requirement_table.fields if f.required]
        total = len(required_fields)
        if total == 0:
            return 100
        filled = sum(1 for f in required_fields if f.field_code in data)
        return int(filled / total * 100)
    
    def to_dict(self) -> Dict:
        """导出为字典"""
        return {
            "product_code": self.requirement_table.product_code,
            "product_name": self.requirement_table.product_name,
            "collected_data": self.collected_data,
            "missing_fields": [f.field_code for f in self.get_missing_fields()],
            "completeness_score": self.get_completeness_score()
        }
