# HubAI 多产品线架构优化方案

> 版本：v1.0
> 时间：2026-06-26
> 定位：底座支持多产品，每个产品独立 Skill，统一入口协调

---

## 一、架构设计原则

### 1.1 核心原则

| 原则 | 说明 |
|------|------|
| **底座统一** | `hubai-base` 提供通用能力：产品路由、需求表基类、话术基类、数据库、权限 |
| **产品独立** | 每个产品线独立为一个 Skill，包含专属需求表、话术、报价规则 |
| **配置驱动** | 需求表、话术全部 JSON 化，无需修改代码即可调整 |
| **自动路由** | 根据对话内容自动识别产品，路由到对应产品 Skill |
| **统一入口** | 用户对话始终由 `smart-quotation` 统一接收，内部再分发 |

### 1.2 架构层级

```
┌─────────────────────────────────────────────────────────────────────┐
│                     统一接入层 (OpenClaw Gateway)                    │
│         钉钉 / 飞书 / 企微 / WebChat / 其他 Agents                    │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ 用户对话
┌─────────────────────────────────────────────────────────────────────┐
│                     大模型调度层（理解与决策）                        │
│              意图识别 → 产品检测 → Skill 调度                        │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ Skill 调用
┌─────────────────────────────────────────────────────────────────────┐
│                  统一报价入口 (smart-quotation)                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  quotation_coordinator.py    # 报价协调器（总入口）         │   │
│  │  product_detector.py          # 产品检测器                 │   │
│  │  session_manager.py           # 多轮会话管理               │   │
│  │  cross_product.py             # 跨产品组合报价             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ 产品路由
┌──────────────────────┬──────────────────────┬──────────────────────┐
│ product-cloud-desktop│ product-wuying-pc   │ product-xxx         │
│  云桌面产品 Skill     │  无影云电脑 Skill   │  其他产品 Skill      │
├──────────────────────┼──────────────────────┼──────────────────────┤
│ requirement_handler  │ requirement_handler  │ requirement_handler │
│ dialogue_handler    │ dialogue_handler    │ dialogue_handler    │
│ price_engine        │ price_engine        │ price_engine        │
│ doc_generator       │ doc_generator       │ doc_generator       │
│ config/             │ config/             │ config/             │
│   requirement.json  │   requirement.json  │   requirement.json  │
│   dialogue.json    │   dialogue.json    │   dialogue.json    │
└──────────────────────┴──────────────────────┴──────────────────────┘
                              ↓ 底层依赖
┌─────────────────────────────────────────────────────────────────────┐
│                      底座能力包 (hubai-base)                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  product_router.py          # 产品路由引擎（新增）         │   │
│  │  requirement_base.py          # 需求表基类（新增）         │   │
│  │  dialogue_base.py            # 话术基类（新增）            │   │
│  │  db.py                       # 数据库连接池                │   │
│  │  logger.py                   # 日志审计                    │   │
│  │  auth.py                     # 权限校验                    │   │
│  │  config.py                   # 配置管理（增强）            │   │
│  │  errors.py                   # 错误处理                    │   │
│  │  mcp_client.py               # 外部系统连接                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、底座增强设计

### 2.1 新增/增强模块

#### 2.1.1 产品路由引擎（product_router.py）

```python
"""产品路由引擎 - 自动识别对话中的产品，路由到对应 Skill"""
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ProductInfo:
    """产品信息"""
    code: str              # 产品编码：cloud-desktop | wuying-pc
    name: str              # 产品名称
    skill_name: str          # 对应 Skill 名称
    keywords: List[str]      # 关键词列表
    category: str           # 产品分类
    priority: int = 100    # 优先级（数字越大越优先）

class ProductRouter:
    """产品路由引擎"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.expanduser("~/hubai/skills/hubai-base/config/products")
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
                        skill_name=config['skill_name'],
                        keywords=config.get('keywords', []),
                        category=config.get('category', 'default'),
                        priority=config.get('priority', 100)
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
```

#### 2.1.2 需求表基类（requirement_base.py）

```python
"""需求表基类 - 所有产品需求表的统一基类"""
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any
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
        pass
    
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
        field = next((f for f in self.requirement_table.fields 
                     if f.field_code == field_code), None)
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
        total = len([f for f in self.requirement_table.fields if f.required])
        if total == 0:
            return 100
        filled = sum(1 for f in self.requirement_table.fields 
                    if f.required and f.field_code in data)
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
```

#### 2.1.3 话术基类（dialogue_base.py）

```python
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
```

### 2.2 底座目录结构（增强后）

```
hubai-base/
├── SKILL.md                          # 更新：说明多产品支撑能力
├── _meta.json
├── config/
│   ├── default.json                  # 全局配置
│   └── products/                      # 产品注册配置目录（新增）
│       ├── cloud-desktop.json        # 云桌面配置
│       └── wuying-pc.json            # 无影云电脑配置
├── scripts/
│   ├── __init__.py                   # 更新：新增导出
│   ├── db.py
│   ├── logger.py
│   ├── auth.py
│   ├── errors.py
│   ├── config.py                     # 增强：支持多产品配置
│   ├── mcp_client.py
│   ├── product_router.py             # 新增：产品路由引擎
│   ├── requirement_base.py             # 新增：需求表基类
│   └── dialogue_base.py            # 新增：话术基类
└── templates/
    └── common/                        # 通用模板
```

---

## 三、产品线 Skill 设计

### 3.1 云桌面产品 Skill（product-cloud-desktop）

#### 3.1.1 目录结构

```
product-cloud-desktop/
├── SKILL.md                          # 产品技能说明
├── _meta.json
├── config/
│   ├── requirement.json              # 需求表配置
│   └── dialogue.json               # 话术模板配置
├── scripts/
│   ├── __init__.py
│   ├── requirement_handler.py       # 需求表处理（继承基类）
│   ├── dialogue_handler.py         # 对话处理（继承基类）
│   ├── price_engine.py             # 价格引擎（产品专属）
│   └── quotation_engine.py        # 报价引擎
└── templates/
    └── quotation/                     # 报价单模板
        ├── internal.md              # 内部版
        └── customer.md              # 客户版
```

#### 3.1.2 需求表配置（config/requirement.json）

```json
{
  "product_code": "cloud-desktop",
  "product_name": "云桌面",
  "version": "1.0.0",
  "categories": [
    "基础信息",
    "配置需求",
    "用户需求",
    "部署需求",
    "商务需求"
  ],
  "fields": [
    {
      "field_code": "customer_name",
      "field_name": "客户名称",
      "field_type": "text",
      "required": true,
      "priority": 1,
      "category": "基础信息",
      "description": "请提供客户公司全称"
    },
    {
      "field_code": "contact_person",
      "field_name": "联系人",
      "field_type": "text",
      "required": true,
      "priority": 1,
      "category": "基础信息",
      "description": "联系人姓名和电话"
    },
    {
      "field_code": "deployment_scale",
      "field_name": "部署规模",
      "field_type": "select",
      "required": true,
      "priority": 1,
      "category": "配置需求",
      "options": [
        "50点以下",
        "50-200点",
        "200-500点",
        "500-1000点",
        "1000点以上"
      ],
      "description": "预计部署规模，影响服务器配置选型"
    },
    {
      "field_code": "usage_scenario",
      "field_name": "使用场景",
      "field_type": "multiselect",
      "required": true,
      "priority": 1,
      "category": "配置需求",
      "options": [
        "办公桌面",
        "研发开发",
        "教学实训",
        "呼叫中心",
        "分支机构",
        "图形设计",
        "视频渲染",
        "其他场景"
      ],
      "description": "云桌面主要使用场景"
    },
    {
      "field_code": "performance_level",
      "field_name": "性能等级",
      "field_type": "select",
      "required": true,
      "priority": 2,
      "category": "配置需求",
      "options": [
        "基础型（2核4G）",
        "标准型（4核8G）",
        "增强型（8核16G）",
        "图形型（8核32G+GPU）",
        "高性能型（16核64G+GPU）"
      ],
      "description": "云桌面性能等级"
    },
    {
      "field_code": "os_preference",
      "field_name": "操作系统偏好",
      "field_type": "select",
      "required": false,
      "priority": 3,
      "category": "配置需求",
      "options": [
        "Windows 10",
        "Windows 11",
        "Windows Server",
        "Ubuntu Linux",
        "麒麟操作系统",
        "统信UOS",
        "其他"
      ],
      "description": "操作系统偏好"
    },
    {
      "field_code": "user_types",
      "field_name": "用户类型",
      "field_type": "multiselect",
      "required": true,
      "priority": 2,
      "category": "用户需求",
      "options": [
        "普通办公人员",
        "研发开发人员",
        "设计美工人员",
        "管理人员",
        "学生/学员",
        "临时访客",
        "其他特殊需求"
      ],
      "description": "使用云桌面使用者类型"
    },
    {
      "field_code": "deployment_method",
      "field_name": "部署方式",
      "field_type": "select",
      "required": false,
      "priority": 3,
      "category": "部署需求",
      "options": [
        "公有云SaaS",
        "私有云部署",
        "混合云部署",
        "暂不确定"
      ],
      "description": "部署方式"
    },
    {
      "field_code": "budget_range",
      "field_name": "预算范围",
      "field_type": "select",
      "required": false,
      "priority": 3,
      "category": "商务需求",
      "options": [
        "5万以下",
        "5-10万",
        "10-30万",
        "30-50万",
        "50-100万",
        "100万以上",
        "暂不确定"
      ],
      "description": "预算范围"
    },
    {
      "field_code": "timeline",
      "field_name": "期望交付时间",
      "field_type": "select",
      "required": false,
      "priority": 3,
      "category": "商务需求",
      "options": [
        "1周内",
        "1个月内",
        "1-3个月",
        "3-6个月",
        "6个月以上",
        "暂不确定"
      ],
      "description": "期望交付时间"
    },
    {
      "field_code": "special_requirements",
      "field_name": "特殊需求说明",
      "field_type": "text",
      "required": false,
      "priority": 4,
      "category": "商务需求",
      "description": "如有其他特殊需求请说明"
    }
  ]
}
```

#### 3.1.3 话术配置（config/dialogue.json）

```json
{
  "product_code": "cloud-desktop",
  "product_name": "云桌面",
  "templates": [
    {
      "code": "welcome",
      "name": "欢迎话术",
      "text": "您好！我是云桌面报价助手 🖥️\n\n我可以帮您快速获取云桌面解决方案的报价。为了给您提供准确的方案，我需要了解几个关键信息。\n\n请告诉我：\n1️⃣ 您的公司名称\n2️⃣ 预计部署多少点（用户数）？\n3️⃣ 主要使用场景是什么？\n\n您也可以直接发送需求，例如：\"XX公司需要100个云桌面，主要用于办公\""
    },
    {
      "code": "ask_requirement",
      "name": "字段追问",
      "text": "为了给您更精准的报价，还需要了解：{{field_name}}\n\n{{field_description}}",
      "variables": ["field_name", "field_description"]
    },
    {
      "code": "summary",
      "name": "需求汇总",
      "text": "📋 需求信息汇总\n\n{{summary_data}}\n\n确认以上信息无误后，我将为您生成报价方案。如需修改请直接告知。"
    },
    {
      "code": "no_product_detected",
      "name": "未检测到产品",
      "text": "您好！我可以为您提供以下产品的报价服务：\n\n🖥️ 云桌面\n💻 无影云电脑\n\n请告诉我您需要哪个产品的报价？或者描述您的需求，我来帮您判断。"
    },
    {
      "code": "quotation_ready",
      "name": "报价完成",
      "text": "✅ 报价方案已生成！\n\n{{quotation_summary}}\n\n如需调整或有其他需求，请随时告知。"
    }
  ]
}
```

### 3.2 无影云电脑产品 Skill（product-wuying-pc）

结构同上，需求表和话术配置根据产品特点调整：

- **产品编码**: `wuying-pc`
- **产品名称**: 无影云电脑
- **关键词**: 无影、云电脑、云端PC、远程电脑、WUYING
- **专属需求表字段**: 桌面规格、使用时长、并发需求、网络要求等
- **专属话术**: 欢迎话术、字段追问、需求汇总等

---

## 四、统一入口增强（smart-quotation）

### 4.1 新增模块

#### 4.1.1 报价协调器（quotation_coordinator.py）

```python
"""报价协调器 - 统一报价入口，负责产品检测、会话管理、Skill 调度"""
import sys
import os
sys.path.append(os.path.expanduser('~/.openclaw/skills/hubai-base/scripts'))

from product_router import ProductRouter
from requirement_base import BaseRequirementHandler
from dialogue_base import BaseDialogueHandler
from logger import HubAILogger

logger = HubAILogger.get_logger("smart-quotation.coordinator")

class QuotationCoordinator:
    """报价协调器 - 统一入口"""
    
    def __init__(self):
        self.router = ProductRouter()
        self.sessions = {}  # 会话管理：{session_id: session_data}
    
    def handle_message(self, session_id: str, user_message: str) -> dict:
        """处理用户消息（统一入口）"""
        logger.info(f"Handling message: session={session_id}, msg={user_message}")
        
        # 1. 获取或创建会话
        session = self._get_or_create_session(session_id)
        
        # 2. 检测产品（如果尚未确定）
        if not session.get('product_code'):
            products = self.router.detect_product(user_message)
            if products:
                session['product_code'] = products[0].code
                session['product_name'] = products[0].name
                session['skill_name'] = products[0].skill_name
                logger.info(f"Product detected: {products[0].code}")
            else:
                # 未检测到产品，返回引导话术
                return {
                    "action": "ask_product",
                    "message": "请问您需要哪个产品的报价？（云桌面 / 无影云电脑）"
                }
        
        # 3. 加载产品 Skill 处理需求
        product_code = session['product_code']
        skill_name = session['skill_name']
        
        # 4. 更新会话数据（提取字段）
        self._extract_fields(session, user_message)
        
        # 5. 检查需求完整性
        requirement_handler = self._load_requirement_handler(product_code)
        requirement_handler.collected_data = session.get('collected_data', {})
        
        missing_fields = requirement_handler.get_missing_fields()
        
        if missing_fields:
            # 需求不完整，追问下一个字段
            next_field = missing_fields[0]
            return {
                "action": "ask_requirement",
                "field": next_field.field_code,
                "field_name": next_field.field_name,
                "message": f"为了给您更精准的报价，还需要了解：{next_field.field_name}\n{next_field.description}"
            }
        
        # 6. 需求完整，生成报价
        return {
            "action": "generate_quotation",
            "product_code": product_code,
            "requirement_data": requirement_handler.to_dict(),
            "message": "需求信息已收集完整，正在生成报价方案..."
        }
    
    def _get_or_create_session(self, session_id: str) -> dict:
        """获取或创建会话"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'session_id': session_id,
                'product_code': None,
                'product_name': None,
                'skill_name': None,
                'collected_data': {},
                'created_at': datetime.now().isoformat()
            }
        return self.sessions[session_id]
    
    def _extract_fields(self, session: dict, user_message: str):
        """从用户消息中提取字段值（简化版，实际由大模型提取）"""
        # 这里将由大模型通过 NLP 提取字段
        # 示例：如果消息包含"XX公司"，提取 customer_name
        pass
    
    def _load_requirement_handler(self, product_code: str):
        """加载产品需求表处理器"""
        # 动态加载对应产品的 requirement_handler
        config_path = f"~/hubai/skills/product-{product_code}/config/requirement.json"
        # 返回对应产品的 RequirementHandler 实例
        pass

from datetime import datetime
```

#### 4.1.2 会话管理器（session_manager.py）

```python
"""多轮会话管理器 - 管理报价对话的完整生命周期"""
import json
import time
from typing import Dict, Optional
from datetime import datetime, timedelta

class SessionManager:
    """会话管理器"""
    
    SESSION_TIMEOUT = 1800  # 30分钟超时
    
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
    
    def create_session(self, user_id: str, channel: str) -> str:
        """创建新会话"""
        session_id = f"{channel}_{user_id}_{int(time.time())}"
        self.sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "channel": channel,
            "product_code": None,
            "collected_data": {},
            "quotation_data": None,
            "status": "collecting",  # collecting | confirming | generating | completed
            "created_at": datetime.now(),
            "last_active": datetime.now()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """获取会话（自动清理过期会话）"""
        self._cleanup_expired()
        session = self.sessions.get(session_id)
        if session:
            session["last_active"] = datetime.now()
        return session
    
    def update_session(self, session_id: str, updates: dict):
        """更新会话数据"""
        session = self.sessions.get(session_id)
        if session:
            session.update(updates)
            session["last_active"] = datetime.now()
    
    def _cleanup_expired(self):
        """清理过期会话"""
        now = datetime.now()
        expired = [
            sid for sid, s in self.sessions.items()
            if now - s["last_active"] > timedelta(seconds=self.SESSION_TIMEOUT)
        ]
        for sid in expired:
            del self.sessions[sid]
```

#### 4.1.3 跨产品组合报价（cross_product.py）

```python
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
        total_amount = sum(item["quotation"]["total_amount"] for item in self.items)
        
        return {
            "quotation_type": "combined",
            "items": self.items,
            "total_amount": total_amount,
            "discount_suggestion": self._calculate_bundle_discount(),
            "summary": f"组合报价共计 {len(self.items)} 个产品，总计 ¥{total_amount:,.2f}"
        }
    
    def _calculate_bundle_discount(self) -> float:
        """计算组合折扣"""
        if len(self.items) >= 3:
            return 0.95  # 95折
        elif len(self.items) >= 2:
            return 0.98  # 98折
        return 1.0
```

### 4.2 统一入口目录结构

```
smart-quotation/
├── SKILL.md                          # 更新：说明统一入口职责
├── _meta.json
├── scripts/
│   ├── __init__.py
│   ├── quotation_coordinator.py     # 新增：报价协调器（总入口）
│   ├── session_manager.py            # 新增：会话管理器
│   ├── cross_product.py               # 新增：跨产品组合报价
│   ├── product_detector.py            # 新增：产品检测（基于底座）
│   ├── price_engine.py               # 保留：通用价格计算
│   ├── rule_validator.py             # 保留：规则校验
│   ├── route_engine.py               # 保留：分流派单
│   ├── doc_generator.py              # 保留：文档生成
│   ├── approval_engine.py             # 保留：审批流程
│   └── requirement_card.py           # 更新：适配多产品
├── templates/
│   ├── quotation/
│   │   ├── internal.md
│   │   └── customer.md
│   └── combined/                      # 新增：组合报价模板
│       └── combined.md
└── config/
    └── routing_rules.json              # 新增：路由规则配置
```

---

## 五、完整多产品架构图

```
用户对话
    ↓
┌─────────────────────────────────────────────────────────────┐
│                    smart-quotation（统一入口）                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  1. quotation_coordinator.py                          │  │
│  │     - 接收所有报价请求                                │  │
│  │     - 检测/确认产品类型                               │  │
│  │     - 管理多轮会话                                    │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  2. product_detector.py → hubai-base/product_router   │  │
│  │     - 关键词匹配识别产品                              │  │
│  │     - 置信度评估                                      │  │
│  │     - 模糊匹配引导                                    │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  3. session_manager.py                                │  │
│  │     - 创建/维护/超时清理会话                          │  │
│  │     - 字段收集状态追踪                                │  │
│  │     - 上下文管理                                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
    ↓ 路由到对应产品 Skill
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│ product-cloud-desktop│    │ product-wuying-pc   │    │ product-xxx         │
│     云桌面 Skill      │    │   无影云电脑 Skill   │    │    其他产品 Skill      │
├──────────────────────┤    ├──────────────────────┤    ├──────────────────────┤
│ requirement_handler  │    │ requirement_handler  │    │ requirement_handler │
│  → 加载需求表配置     │    │  → 加载需求表配置     │    │  → 加载需求表配置     │
│  → 字段验证           │    │  → 字段验证           │    │  → 字段验证           │
├──────────────────────┤    ├──────────────────────┤    ├──────────────────────┤
│ dialogue_handler    │    │ dialogue_handler    │    │ dialogue_handler    │
│  → 加载话术模板       │    │  → 加载话术模板       │    │  → 加载话术模板       │
│  → 模板渲染           │    │  → 模板渲染           │    │  → 模板渲染           │
├──────────────────────┤    ├──────────────────────┤    ├──────────────────────┤
│ price_engine        │    │ price_engine        │    │ price_engine        │
│  → 产品专属价格表     │    │  → 产品专属价格表     │    │  → 产品专属价格表     │
│  → 专属折扣规则       │    │  → 专属折扣规则       │    │  → 专属折扣规则       │
├──────────────────────┤    ├──────────────────────┤    ├──────────────────────┤
│ quotation_engine    │    │ quotation_engine    │    │ quotation_engine    │
│  → 生成产品报价       │    │  → 生成产品报价       │    │  → 生成产品报价       │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  可选：cross_product.py（跨产品组合报价）                    │
│  - 合并多个产品报价                                         │
│  - 计算组合折扣                                             │
│  - 生成组合报价单                                           │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  通用流程（保留）                                           │
│  rule_validator → route_engine → approval_engine           │
│  → doc_generator（生成内部/客户版报价单）                    │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│                      hubai-base（底座支撑）                   │
│  db.py | logger.py | auth.py | config.py | errors.py        │
│  product_router.py | requirement_base.py | dialogue_base.py │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、实施计划

### Phase 1：底座增强（1 天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 创建产品路由引擎 | `product_router.py` | 产品注册、检测、路由 |
| 创建需求表基类 | `requirement_base.py` | 字段定义、验证、评分 |
| 创建话术基类 | `dialogue_base.py` | 模板加载、渲染、追问 |
| 更新配置管理 | `config.py` | 支持多产品配置加载 |
| 更新包导出 | `__init__.py` | 新增模块导出 |
| 创建产品配置目录 | `config/products/` | 产品注册配置 |

### Phase 2：统一入口增强（0.5 天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 创建报价协调器 | `quotation_coordinator.py` | 统一入口、Skill 调度 |
| 创建会话管理器 | `session_manager.py` | 多轮会话生命周期 |
| 创建跨产品报价 | `cross_product.py` | 组合报价、折扣 |
| 更新需求卡 | `requirement_card.py` | 适配多产品需求表 |
| 更新 SKILL.md | `SKILL.md` | 说明统一入口职责 |

### Phase 3：产品 Skill 创建（每产品 0.5 天）

以云桌面为例：

| 任务 | 文件 | 说明 |
|------|------|------|
| 创建 Skill 目录 | `product-cloud-desktop/` | 完整目录结构 |
| 编写需求表配置 | `config/requirement.json` | 11 个字段定义 |
| 编写话术配置 | `config/dialogue.json` | 5 套话术模板 |
| 创建需求处理器 | `requirement_handler.py` | 继承基类 |
| 创建对话处理器 | `dialogue_handler.py` | 继承基类 |
| 创建价格引擎 | `price_engine.py` | 云桌面专属价格 |
| 创建报价引擎 | `quotation_engine.py` | 整合报价逻辑 |
| 创建报价模板 | `templates/quotation/` | 内部版/客户版 |

### Phase 4：集成测试（0.5 天）

| 测试项 | 说明 |
|--------|------|
| 产品检测 | 关键词匹配、多产品识别 |
| 需求收集 | 多轮对话、字段追问 |
| 报价生成 | 单产品报价、跨产品组合 |
| 话术渲染 | 模板变量替换、动态内容 |
| 会话管理 | 超时清理、状态恢复 |

---

## 七、新增/修改文件清单

### 底座增强（hubai-base）

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `scripts/product_router.py` | 产品路由引擎 |
| 新增 | `scripts/requirement_base.py` | 需求表基类 |
| 新增 | `scripts/dialogue_base.py` | 话术基类 |
| 新增 | `config/products/cloud-desktop.json` | 云桌面注册配置 |
| 新增 | `config/products/wuying-pc.json` | 无影云电脑注册配置 |
| 修改 | `scripts/config.py` | 增强多产品配置加载 |
| 修改 | `scripts/__init__.py` | 新增模块导出 |
| 修改 | `SKILL.md` | 更新多产品支撑说明 |

### 统一入口增强（smart-quotation）

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `scripts/quotation_coordinator.py` | 报价协调器 |
| 新增 | `scripts/session_manager.py` | 会话管理器 |
| 新增 | `scripts/cross_product.py` | 跨产品组合报价 |
| 新增 | `scripts/product_detector.py` | 产品检测器 |
| 新增 | `templates/combined/combined.md` | 组合报价模板 |
| 修改 | `scripts/requirement_card.py` | 适配多产品 |
| 修改 | `SKILL.md` | 更新统一入口职责 |

### 产品 Skill（product-cloud-desktop）

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `SKILL.md` | 产品技能说明 |
| 新增 | `_meta.json` | 元数据 |
| 新增 | `config/requirement.json` | 需求表配置（11 字段） |
| 新增 | `config/dialogue.json` | 话术模板配置 |
| 新增 | `scripts/requirement_handler.py` | 需求处理器 |
| 新增 | `scripts/dialogue_handler.py` | 对话处理器 |
| 新增 | `scripts/price_engine.py` | 价格引擎 |
| 新增 | `scripts/quotation_engine.py` | 报价引擎 |
| 新增 | `templates/quotation/internal.md` | 内部报价模板 |
| 新增 | `templates/quotation/customer.md` | 客户报价模板 |

---

## 八、配置示例

### 8.1 云桌面需求表配置（精简版）

```json
{
  "product_code": "cloud-desktop",
  "product_name": "云桌面",
  "version": "1.0.0",
  "categories": ["基础信息", "配置需求", "用户需求", "部署需求", "商务需求"],
  "fields": [
    {"field_code": "customer_name", "field_name": "客户名称", "field_type": "text", "required": true, "priority": 1, "category": "基础信息"},
    {"field_code": "deployment_scale", "field_name": "部署规模", "field_type": "select", "required": true, "priority": 1, "category": "配置需求", "options": ["50点以下", "50-200点", "200-500点", "500-1000点", "1000点以上"]},
    {"field_code": "usage_scenario", "field_name": "使用场景", "field_type": "multiselect", "required": true, "priority": 1, "category": "配置需求", "options": ["办公桌面", "研发开发", "教学实训", "呼叫中心", "图形设计"]},
    {"field_code": "performance_level", "field_name": "性能等级", "field_type": "select", "required": true, "priority": 2, "category": "配置需求", "options": ["基础型（2核4G）", "标准型（4核8G）", "增强型（8核16G）", "图形型（8核32G+GPU）"]},
    {"field_code": "user_types", "field_name": "用户类型", "field_type": "multiselect", "required": true, "priority": 2, "category": "用户需求", "options": ["普通办公人员", "研发开发人员", "设计美工人员", "管理人员", "学生/学员"]},
    {"field_code": "budget_range", "field_name": "预算范围", "field_type": "select", "required": false, "priority": 3, "category": "商务需求", "options": ["5万以下", "5-10万", "10-30万", "30-50万", "50-100万", "100万以上", "暂不确定"]}
  ]
}
```

### 8.2 产品注册配置

```json
{
  "code": "cloud-desktop",
  "name": "云桌面",
  "skill_name": "product-cloud-desktop",
  "category": "computing",
  "priority": 100,
  "keywords": ["云桌面", "cloud desktop", "企业云桌面", "桌面云", "vdi", "VDI"]
}
```

---

## 九、优势总结

| 优势 | 说明 |
|------|------|
| **底座统一** | 产品路由、需求表、话术全部基类化，避免重复代码 |
| **产品独立** | 每个产品 Skill 独立维护，互不影响 |
| **配置驱动** | 新增产品只需添加配置，无需修改代码 |
| **易扩展** | 新增产品线只需：①注册产品 ②创建配置 ③实现少量代码 |
| **用户体验** | 自动识别产品，减少用户选择步骤 |
| **组合报价** | 支持跨产品组合，自动计算折扣 |
| **话术统一** | 基类提供标准话术，产品可覆盖定制 |

---

**方案确认后，将更新到 `hubai_unified_solution_v1` 整体方案中。**
