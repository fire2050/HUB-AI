"""话术基类 - 统一话术模板管理"""
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class DialogueTemplate:
    """对话话术模板"""
    template_code: str
    template_name: str
    template_text: str           # 支持变量用 {{变量名}} 格式
    variables: List[str] = None     # 变量列表

class BaseDialogueHandler:
    """对话处理基类"""
    
    def __init__(self, template_path: str = None):
        self.template_path = template_path
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, DialogueTemplate]:
        """加载话术模板"""
        templates = {}
        if not self.template_path or not os.path.exists(self.template_path):
            return templates
        
        with open(self.template_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for t in data.get('templates', []):
            template = DialogueTemplate(
                template_code=t['code'],
                template_name=t['name'],
                template_text=t['text'],
                variables=t.get('variables', [])
            )
            templates[template.template_code] = template
        
        return templates
    
    def render_template(self, template_code: str, **kwargs) -> str:
        """渲染话术模板"""
        template = self.templates.get(template_code)
        if not template:
            return f"[模板 {template_code} 不存在]"
        
        text = template.template_text
        for key, value in kwargs.items():
            text = text.replace("{{" + key + "}}", str(value))
        
        return text
    
    def get_welcome_message(self, product_name: str = "") -> str:
        """获取欢迎话术"""
        return self.render_template("welcome", product_name=product_name)
    
    def get_requirement_question(self, field_name: str, field_description: str = "") -> str:
        """获取字段追问话术"""
        return self.render_template("ask_requirement", 
                                   field_name=field_name, 
                                   field_description=field_description)
    
    def get_summary_message(self, data: Dict) -> str:
        """获取需求汇总话术"""
        return self.render_template("summary", **data)
    
    def get_no_product_detected(self) -> str:
        """未检测到产品时的引导话术"""
        return self.render_template("no_product_detected")
    
    def get_quotation_ready(self, **kwargs) -> str:
        """报价完成话术"""
        return self.render_template("quotation_ready", **kwargs)
