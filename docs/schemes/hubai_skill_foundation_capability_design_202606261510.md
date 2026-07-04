# HubAI 支持 OpenClaw Skill 的底座能力架构设计

> 版本：v1.0
> 日期：2026-06-26
> 定位：HubAI 报价系统的 OpenClaw Skill 底座能力层设计
> 核心原则：大模型"调度"，Skill"执行"，底座"支撑"

---

## 一、总体架构

### 1.1 三层架构模型

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        Layer 1: 调度层（LLM）                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  OpenClaw Gateway + 大模型                                   │   │
│  │  • 意图识别：判断用户是否需要报价                            │   │
│  │  • 信息提取：从对话中提取客户公司、产品、数量、预算等        │   │
│  │  • 上下文管理：维护多轮对话状态，决定下一步追问或执行        │   │
│  │  • Skill 调度：确定调用 smart-quotation Skill，不自行计算  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ 调用 Skill（确定性执行）
┌──────────────────────────────────┼──────────────────────────────────┐
│                        Layer 2: 执行层（Skill）                      │
│  ┌───────────────────────────────┼─────────────────────────────┐   │
│  │  hubai-base（底座能力包）      │ 被所有业务 Skill 依赖       │   │
│  │  ├─ 数据库连接池              │ SQLite/PostgreSQL 统一封装  │   │
│  │  ├─ 配置管理                  │ 多环境配置加载与热更新        │   │
│  │  ├─ 日志审计                  │ 统一日志格式 + 审计追踪       │   │
│  │  ├─ 权限校验                  │ RBAC 角色权限控制             │   │
│  │  ├─ 错误处理                  │ 统一异常捕获与错误码          │   │
│  │  └─ 工具函数                  │ 数据转换、格式校验、日期处理  │   │
│  └───────────────────────────────┼─────────────────────────────┘   │
│                                  │                                  │
│  ┌───────────────────────────────┼─────────────────────────────┐   │
│  │  smart-quotation（业务 Skill）│ 报价核心执行能力            │   │
│  │  ├─ price_engine.py           │ 价格计算引擎（100%确定性）  │   │
│  │  ├─ rule_validator.py         │ 规则校验引擎（7项自动检测） │   │
│  │  ├─ route_engine.py           │ 分流派单引擎（4类需求路由） │   │
│  │  ├─ doc_generator.py          │ 文档生成引擎（Markdown/PDF）│   │
│  │  ├─ approval_engine.py        │ 审批流程引擎（状态机）      │   │
│  │  └─ requirement_card.py       │ 需求卡生成（完整性+缺口）   │   │
│  └───────────────────────────────┼─────────────────────────────┘   │
└──────────────────────────────────┼──────────────────────────────────┘
                                   │ 数据持久化
┌──────────────────────────────────┼──────────────────────────────────┐
│                        Layer 3: 数据层（存储）                       │
│  ├─ SQLite/PostgreSQL：结构化业务数据（报价单、客户、产品等）       │
│  ├─ FTS5：全文检索（知识切片）                                      │
│  ├─ IMA 知识库：云端归档（报价单、方案文档）                        │
│  └─ 文件系统：日志、模板、配置                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则

| 原则 | 说明 | 实现方式 |
|------|------|---------|
| **调度与执行分离** | 大模型只负责理解需求和调度 Skill，Skill 负责确定性计算 | 通过 SKILL.md 定义边界，脚本执行计算 |
| **认知与执行分离** | 知识库提供业务上下文，Skill 负责执行业务逻辑 | RAG 检索 + Python 脚本 |
| **底座与业务分离** | hubai-base 提供通用能力，smart-quotation 专注报价 | 依赖注入 + 模块化设计 |
| **100% 确定性** | 价格、折扣、毛利率等关键计算绝不依赖大模型 | Python 脚本 + 规则引擎 |
| **完整可审计** | 每次报价的执行步骤、调用参数、计算结果均有日志 | 审计日志 + 执行追踪 |

---

## 二、底座能力层（hubai-base）详细设计

### 2.1 能力模块清单

| 模块 | 文件 | 职责 | 被谁调用 |
|------|------|------|---------|
| **数据库连接池** | `db.py` | SQLite/PostgreSQL 统一连接、事务管理、ORM 封装 | 所有 Skill |
| **配置管理** | `config.py` | 多环境配置加载、热更新、配置校验 | 所有 Skill |
| **日志审计** | `logger.py` | 统一日志格式、分级日志、审计日志、自动轮转 | 所有 Skill |
| **权限校验** | `auth.py` | RBAC 角色定义、权限检查、折扣权限、审批权限 | 报价 Skill |
| **错误处理** | `errors.py` | 统一错误码、异常捕获、错误分类、友好的错误消息 | 所有 Skill |
| **工具函数** | `utils.py` | 数据转换、格式校验、日期处理、字符串处理、文件操作 | 所有 Skill |
| **MCP 客户端** | `mcp_client.py` | 连接外部系统（ERP/CRM/审批系统）的 MCP 协议封装 | 业务 Skill |

### 2.2 数据库连接池（db.py）

```python
class HubAIDatabase:
    """
    HubAI 统一数据库连接池
    
    特性：
    - 单例模式：全局唯一实例
    - 上下文管理：自动事务提交/回滚
    - 连接复用：SQLite 单连接，PostgreSQL 连接池
    - SQL 注入防护：参数化查询
    """
    
    def __init__(self, db_path: str = None, db_type: str = "sqlite"):
        """
        Args:
            db_path: 数据库文件路径（SQLite）或连接字符串（PostgreSQL）
            db_type: 数据库类型 sqlite | postgresql
        """
    
    def execute(self, sql: str, params: tuple = ()) -> int:
        """执行 SQL，返回影响行数"""
    
    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        """查询单行，返回字典"""
    
    def query_all(self, sql: str, params: tuple = ()) -> List[Dict]:
        """查询多行，返回字典列表"""
    
    def insert(self, table: str, data: Dict) -> int:
        """插入数据，返回 rowid"""
    
    def insert_many(self, table: str, data_list: List[Dict]) -> int:
        """批量插入，返回影响行数"""
    
    def update(self, table: str, data: Dict, where: str, where_params: tuple) -> int:
        """更新数据，返回影响行数"""
    
    def transaction(self):
        """事务上下文管理器"""
```

### 2.3 配置管理（config.py）

```python
class HubAIConfig:
    """
    HubAI 统一配置管理
    
    特性：
    - 多环境支持：development | testing | production
    - 配置分层：default < environment < user_override
    - 热更新：运行时重新加载配置
    - 配置校验：必填项检查、类型检查、范围检查
    """
    
    def __init__(self, config_dir: str = None, env: str = None):
        """
        Args:
            config_dir: 配置文件目录，默认 ~/hubai/skills/hubai-base/config/
            env: 环境名称，默认从 ENV 环境变量读取
        """
    
    def get(self, key: str, default=None, type_hint=None):
        """获取配置项，支持点号路径"""
        # 示例：config.get("database.sqlite.path")
        # 示例：config.get("quotation.discount.max_rate", 0.9, float)
    
    def get_database_config(self, db_name: str = "default") -> Dict:
        """获取数据库配置"""
    
    def get_quotation_rules(self) -> Dict:
        """获取报价规则配置"""
    
    def get_approval_rules(self) -> Dict:
        """获取审批规则配置"""
    
    def reload(self):
        """热更新：重新加载配置文件"""
    
    def validate(self) -> List[str]:
        """校验配置完整性，返回错误列表"""
```

### 2.4 日志审计（logger.py）

```python
class HubAILogger:
    """
    HubAI 统一日志审计系统
    
    特性：
    - 分级日志：DEBUG | INFO | WARNING | ERROR | CRITICAL
    - 命名空间：按 Skill/模块隔离日志
    - 审计日志：独立审计通道，不可关闭
    - 自动轮转：按日期/大小自动轮转
    - 结构化：JSON 格式，便于日志分析
    """
    
    @staticmethod
    def get_logger(name: str, log_level: str = "INFO") -> logging.Logger:
        """获取命名日志实例"""
    
    @staticmethod
    def audit_log(action: str, user_id: str, details: Dict, 
                  result: str = "success", error_code: str = None):
        """
        审计日志：记录关键业务操作
        
        Args:
            action: 操作名称（quotation.create | quotation.approve | ...）
            user_id: 操作用户ID
            details: 操作详情（JSON 可序列化）
            result: 操作结果 success | failed
            error_code: 错误码（失败时必填）
        """
    
    @staticmethod
    def performance_log(operation: str, duration_ms: int, 
                       input_size: int = None, output_size: int = None):
        """性能日志：记录操作耗时"""
```

### 2.5 权限校验（auth.py）

```python
class PermissionChecker:
    """
    HubAI RBAC 权限校验系统
    
    特性：
    - 角色定义：sales | sales_manager | sales_director | finance_director | admin
    - 权限粒度：功能权限 + 数据权限 + 折扣权限
    - 动态权限：基于客户级别、产品类型的动态权限计算
    """
    
    # 角色权限定义
    ROLES = {
        "sales": {
            "description": "标准销售",
            "max_discount": 0.9,           # 最多9折
            "can_approve": False,
            "can_create_quotation": True,
            "can_view_all_quotations": False,
            "can_modify_approved": False
        },
        "sales_manager": {
            "description": "销售经理",
            "max_discount": 0.8,           # 最多8折
            "can_approve": True,
            "approval_scope": ["standard", "solution"],
            "can_create_quotation": True,
            "can_view_team_quotations": True
        },
        "sales_director": {
            "description": "销售总监",
            "max_discount": 0.7,           # 最多7折
            "can_approve": True,
            "approval_scope": ["custom", "risky"],
            "can_view_all_quotations": True
        },
        "finance_director": {
            "description": "财务总监",
            "max_discount": 0.6,           # 最多6折
            "can_approve": True,
            "approval_scope": ["risky"],
            "can_view_financial_data": True
        },
        "admin": {
            "description": "系统管理员",
            "max_discount": 0.5,
            "can_approve": True,
            "can_manage_users": True,
            "can_manage_products": True
        }
    }
    
    @staticmethod
    def check_discount_permission(user_role: str, discount_rate: float) -> Dict:
        """
        检查折扣权限
        
        Returns:
            {
                "allowed": bool,              # 是否允许
                "max_discount": float,        # 该角色最大折扣
                "need_approval": bool,        # 是否需要审批
                "approver_role": str,         # 审批人角色
                "reason": str                 # 说明
            }
        """
    
    @staticmethod
    def check_approval_permission(approver_role: str, quotation_type: str) -> bool:
        """检查审批权限"""
    
    @staticmethod
    def get_user_permissions(user_role: str) -> Dict:
        """获取用户全部权限"""
```

### 2.6 错误处理（errors.py）

```python
class HubAIError(Exception):
    """HubAI 基础异常类"""
    
    def __init__(self, code: str, message: str, details: Dict = None, 
                 http_status: int = 500):
        self.code = code
        self.message = message
        self.details = details or {}
        self.http_status = http_status
        super().__init__(self.message)

class QuotationError(HubAIError):
    """报价相关异常"""
    pass

# 错误码定义
ERROR_CODES = {
    # 产品相关
    "PRODUCT_NOT_FOUND": {"code": "Q001", "message": "产品不存在", "status": 404},
    "PRODUCT_INACTIVE": {"code": "Q002", "message": "产品未上架", "status": 400},
    "PRODUCT_PRICE_NOT_FOUND": {"code": "Q003", "message": "产品无有效价格", "status": 404},
    
    # 库存相关
    "INVENTORY_SHORTAGE": {"code": "Q101", "message": "库存不足", "status": 400},
    "INVENTORY_LOCKED": {"code": "Q102", "message": "库存已被锁定", "status": 409},
    
    # 价格相关
    "DISCOUNT_EXCEEDED": {"code": "Q201", "message": "折扣超出权限", "status": 403},
    "MARGIN_TOO_LOW": {"code": "Q202", "message": "毛利率过低", "status": 400},
    "PRICE_EXPIRED": {"code": "Q203", "message": "价格已过期", "status": 400},
    
    # 权限相关
    "PERMISSION_DENIED": {"code": "A001", "message": "权限不足", "status": 403},
    "APPROVAL_REQUIRED": {"code": "A002", "message": "需要审批", "status": 403},
    
    # 系统相关
    "DATABASE_ERROR": {"code": "S001", "message": "数据库错误", "status": 500},
    "CONFIG_ERROR": {"code": "S002", "message": "配置错误", "status": 500},
    "MCP_CONNECTION_ERROR": {"code": "S003", "message": "外部系统连接失败", "status": 503}
}

def get_error_response(error_code: str, **kwargs) -> Dict:
    """获取标准错误响应"""
```

### 2.7 MCP 客户端（mcp_client.py）

```python
class HubAIMCPClient:
    """
    HubAI MCP（Model Context Protocol）客户端
    
    用于连接外部系统：
    - ERP 系统：库存查询、成本价同步
    - CRM 系统：客户等级、历史订单
    - 审批系统：钉钉审批、飞书审批
    - 文件存储：COS、本地文件、IMA
    
    特性：
    - 连接池管理
    - 超时重试
    - 健康检查
    - 熔断机制
    """
    
    def __init__(self, service_name: str, config: Dict):
        """
        Args:
            service_name: 服务名称 erp | crm | approval | storage
            config: 连接配置
        """
    
    def call(self, method: str, params: Dict, timeout: int = 30) -> Dict:
        """调用外部系统接口"""
    
    def health_check(self) -> bool:
        """健康检查"""
    
    def close(self):
        """关闭连接"""
```

---

## 三、底座能力与 OpenClaw 的集成

### 3.1 集成架构

```text
OpenClaw Gateway
    ├── 大模型（调度层）
    │   └── 理解需求 → 提取信息 → 调用 Skill
    │
    ├── Skill 加载器
    │   ├── 扫描 ~/.openclaw/skills/
    │   ├── 扫描 ~/hubai/skills/
    │   ├── 解析 SKILL.md
    │   ├── 解析 _meta.json
    │   └── 注册 Skill
    │
    └── Skill 执行器
        ├── 验证权限
        ├── 加载依赖（hubai-base）
        ├── 执行脚本（Python）
        ├── 捕获输出
        └── 返回结果

┌─────────────────────────────────────────────────────────────┐
│                    Skill 生命周期管理                        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐ │
│  │ 加载    │ → │ 初始化  │ → │ 执行    │ → │ 卸载    │ │
│  │         │    │         │    │         │    │         │ │
│  │ • 扫描  │    │ • 依赖  │    │ • 调用  │    │ • 清理  │ │
│  │ • 解析  │    │ • 配置  │    │ • 监控  │    │ • 日志  │ │
│  │ • 注册  │    │ • 连接  │    │ • 返回  │    │         │ │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 OpenClaw 配置

```json
{
  "skills": {
    "enabled": true,
    "autoLoad": true,
    "directories": [
      "~/.openclaw/skills",
      "~/hubai/skills"
    ],
    "security": {
      "sandboxMode": "workspace",
      "allowNetwork": ["ima.qq.com", "localhost"],
      "allowFsWrite": ["workspace", "tmp"],
      "allowExec": ["python3", "node"]
    },
    "execution": {
      "timeoutSeconds": 300,
      "maxMemoryMB": 512,
      "maxOutputLength": 10000
    }
  },
  "agents": {
    "list": [
      {
        "id": "hubai",
        "name": "HubAI 报价助手",
        "workspace": "~/hubai/workspace",
        "model": "ark-code-latest",
        "skills": ["hubai-base", "smart-quotation"],
        "systemPrompt": "你是 HubAI 报价助手..."
      }
    ]
  }
}
```

### 3.3 Skill 注册与发现机制

| 步骤 | 说明 | 文件 |
|------|------|------|
| **扫描** | OpenClaw 启动时扫描配置的 directories | - |
| **解析** | 读取 SKILL.md 和 _meta.json | SKILL.md, _meta.json |
| **验证** | 检查依赖是否满足、权限是否正确 | - |
| **注册** | 将 Skill 注册到 Skill 注册表 | - |
| **初始化** | 调用 Skill 的初始化脚本（如果有） | scripts/init.py |
| **加载** | 加载 Skill 的脚本到执行环境 | - |

---

## 四、底座能力的使用方式

### 4.1 在业务 Skill 中引用底座能力

```python
# smart-quotation/scripts/price_engine.py
import sys
import os

# 添加底座能力到 Python 路径
sys.path.append(os.path.expanduser('~/.openclaw/skills/hubai-base/scripts'))

# 导入底座能力
from db import HubAIDatabase
from logger import HubAILogger
from auth import PermissionChecker
from errors import HubAIError, QuotationError, ERROR_CODES
from config import HubAIConfig
from mcp_client import HubAIMCPClient

# 初始化
logger = HubAILogger.get_logger("smart-quotation.price_engine")
config = HubAIConfig()
db = HubAIDatabase()

def calculate_price(product_code: str, quantity: int, customer_level: str):
    """计算价格（100% 确定性）"""
    
    # 1. 查询产品价格
    price = db.query_one("""
        SELECT * FROM product_price 
        WHERE product_code = ? AND status = 'active'
    """, (product_code,))
    
    if not price:
        # 使用底座能力的错误处理
        raise QuotationError(
            code=ERROR_CODES["PRODUCT_PRICE_NOT_FOUND"]["code"],
            message=ERROR_CODES["PRODUCT_PRICE_NOT_FOUND"]["message"],
            details={"product_code": product_code}
        )
    
    # 2. 匹配价格策略
    policy = db.query_one("""
        SELECT * FROM quotation_policy 
        WHERE status = 'active' AND customer_level = ?
        ORDER BY priority DESC LIMIT 1
    """, (customer_level,))
    
    discount_rate = policy["discount_rate"] if policy else 1.0
    
    # 3. 计算价格（确定性计算，不依赖大模型）
    unit_price_final = price["unit_price"] * discount_rate
    line_amount = unit_price_final * quantity
    
    # 4. 记录审计日志
    HubAILogger.audit_log(
        action="quotation.price_calculate",
        user_id="system",
        details={
            "product_code": product_code,
            "quantity": quantity,
            "unit_price": price["unit_price"],
            "discount_rate": discount_rate,
            "line_amount": line_amount
        }
    )
    
    return {
        "unit_price_original": price["unit_price"],
        "discount_rate": discount_rate,
        "unit_price_final": unit_price_final,
        "line_amount": line_amount
    }
```

### 4.2 大模型调用 Skill 的方式

```python
# 在 OpenClaw 的 Agent 中调用 Skill
# 大模型负责理解需求并提取参数，然后调用 Skill

# 示例对话：
# 用户：帮我报个价，XX教育公司要20台云桌面
# 
# 大模型提取参数：
#   customer_company = "XX教育公司"
#   products = [{"product_code": "CLOUD-DESK-ENT", "quantity": 20}]
#   customer_level = "standard"
#
# 大模型调用 Skill：
result = sessions_spawn(
    agent_id="hubai",
    skill="smart-quotation",
    task="generate_quotation",
    params={
        "customer_company": "XX教育公司",
        "products": [{"product_code": "CLOUD-DESK-ENT", "quantity": 20}],
        "customer_level": "standard"
    }
)
#
# Skill 返回结果：
# {
#   "quotation_no": "Q-20260626-000001",
#   "total_amount": 14400.00,
#   "lines": [...],
#   "margin_rate": 0.31,
#   "approval_required": false
# }
#
# 大模型将结果转化为自然语言回复：
# "报价草稿已生成：企业版云桌面 ×20台，折扣价¥720/台，合计¥14,400，
#  毛利率31%，无需审批。[查看客户版] [发送给客户]"
```

---

## 五、底座能力的扩展规划

### 5.1 未来扩展模块

| 模块 | 说明 | 优先级 |
|------|------|--------|
| **缓存层** | Redis/Memcached 缓存热点数据 | P1 |
| **消息队列** | 异步任务处理（报价审批通知） | P1 |
| **监控告警** | 性能监控、错误告警、业务指标 | P2 |
| **版本管理** | Skill 版本控制、灰度发布 | P2 |
| **多租户** | 企业级多租户隔离 | P3 |
| **分布式** | 分布式部署、负载均衡 | P3 |

### 5.2 与其他系统的集成

| 系统 | 集成方式 | 用途 |
|------|---------|------|
| **钉钉** | OpenClaw 内置通道 | 消息收发、审批通知 |
| **飞书** | OpenClaw 内置通道 | 消息收发、审批通知 |
| **企微** | Webhook | 消息收发 |
| **ERP** | MCP 协议 | 库存查询、成本价同步 |
| **CRM** | MCP 协议 | 客户等级、历史订单 |
| **IMA** | REST API | 知识库归档、文档存储 |

---

## 六、部署检查清单

### 6.1 底座能力部署检查

- [ ] hubai-base SKILL.md 正确
- [ ] hubai-base _meta.json 正确
- [ ] db.py 数据库连接正常
- [ ] logger.py 日志输出正常
- [ ] auth.py 权限校验正常
- [ ] errors.py 错误码定义完整
- [ ] config.py 配置加载正常
- [ ] mcp_client.py 连接测试通过

### 6.2 业务 Skill 部署检查

- [ ] smart-quotation SKILL.md 正确
- [ ] smart-quotation _meta.json 正确
- [ ] price_engine.py 计算准确性验证
- [ ] rule_validator.py 规则检测验证
- [ ] route_engine.py 分流逻辑验证
- [ ] doc_generator.py 文档生成验证
- [ ] approval_engine.py 审批流程验证

### 6.3 集成测试

- [ ] 大模型调用 Skill 正常
- [ ] Skill 调用底座能力正常
- [ ] 数据库读写正常
- [ ] 审计日志记录正常
- [ ] 钉钉对话测试通过

---

**编制人**：AI+比特虾  
**日期**：2026-06-26  
**版本**：v1.0
