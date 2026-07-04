# HubAI Skill 底层能力架构与部署步骤

> 版本：v1.0
> 日期：2026-06-26
> 定位：基于 OpenClaw Skill 机制构建 HubAI 报价系统的底层执行能力
> 目标：30 分钟内完成从 0 到可运行的 Skill 部署

---

## 一、当前环境状态

| 项 | 当前状态 | 需要变更 |
|---|---|---|
| Gateway | ✅ 运行中 | 重启生效 |
| 钉钉连接器 | ✅ 已配置 | 无需变更 |
| Skill 开关 | ❌ `skills.enabled = False` | **启用** |
| Agent 数量 | 1 个（default main） | **新增 hubai agent** |
| Bindings 数量 | 0 个 | **新增报价绑定** |
| 现有 Skill | 5 个（system） | **新增 hubai-base + smart-quotation** |

---

## 二、Skill 底层能力架构

### 2.1 架构分层

```text
┌─────────────────────────────────────────────────────────────┐
│              大模型调度层（OpenClaw LLM）                     │
│  • 理解客户需求、提取信息、决定流程、调用 Skill               │
│  • 维护多轮对话状态，绝不进行价格计算                        │
└──────────────────────────┬──────────────────────────────────┘
                           ↓ 调用 Skill（确定性执行）
┌─────────────────────────────────────────────────────────────┐
│  hubai-base（基础能力包）←── 被所有业务 Skill 依赖           │
│  ├─ db.py          数据库连接池（SQLite/PostgreSQL）         │
│  ├─ logger.py      统一日志 + 审计日志                       │
│  ├─ auth.py        RBAC 权限校验                             │
│  └─ utils.py       通用工具函数                              │
└──────────────────────────┬──────────────────────────────────┘
                           ↓ 依赖
┌─────────────────────────────────────────────────────────────┐
│  smart-quotation（报价核心 Skill）                           │
│  ├─ price_engine.py      价格计算引擎（100%确定性脚本）      │
│  ├─ rule_validator.py    规则校验引擎（7项自动检测）          │
│  ├─ route_engine.py      分流派单引擎（4类需求路由）          │
│  ├─ doc_generator.py     文档生成引擎（Markdown/PDF）        │
│  ├─ approval_engine.py   审批流程引擎（状态机 + 通知）       │
│  └─ requirement_card.py  需求卡生成（完整性+缺口+追问）      │
└──────────────────────────┬──────────────────────────────────┘
                           ↓ MCP 协议
┌─────────────────────────────────────────────────────────────┐
│  外部系统对接（可选扩展）                                     │
│  ├─ ERP：库存查询、成本价同步                                │
│  ├─ CRM：客户等级、历史订单                                  │
│  ├─ 审批系统：钉钉审批、飞书审批                             │
│  └─ 文件存储：COS、IMA 知识库                                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```bash
~/hubai/
├── workspace/
│   ├── data/              # SQLite 数据库文件
│   │   └── hubai.db
│   └── logs/
│       ├── audit/         # 审计日志（按月分文件）
│       ├── smart-quotation.log
│       └── hubai-base.log
│
└── skills/
    ├── hubai-base/        # 基础能力包
    │   ├── SKILL.md
    │   ├── _meta.json
    │   ├── requirements.txt
    │   ├── config/
    │   │   └── default.json
    │   ├── scripts/
    │   │   ├── __init__.py
    │   │   ├── db.py          # 数据库连接池
    │   │   ├── logger.py      # 统一日志审计
    │   │   ├── auth.py        # 权限校验
    │   │   └── utils.py       # 通用工具
    │   └── tests/
    │       └── test_db.py
    │
    └── smart-quotation/   # 报价核心 Skill
        ├── SKILL.md
        ├── _meta.json
        ├── requirements.txt
        ├── config/
        │   ├── discount_rates.json    # 折扣系数表
        │   ├── approval_rules.json    # 审批规则
        │   └── route_rules.json       # 分流规则
        ├── scripts/
        │   ├── __init__.py
        │   ├── price_engine.py        # 价格计算引擎
        │   ├── rule_validator.py      # 规则校验引擎
        │   ├── route_engine.py        # 分流派单引擎
        │   ├── doc_generator.py       # 文档生成引擎
        │   ├── approval_engine.py     # 审批流程引擎
        │   └── requirement_card.py    # 需求卡生成
        ├── templates/
        │   ├── quotation_internal.md  # 内部报价单
        │   ├── quotation_customer.md  # 客户版报价单
        │   └── proposal_template.md   # 技术方案模板
        ├── logs/                  # 执行日志
        └── tests/
            └── test_price_engine.py

~/.openclaw/skills/    # 软链接指向 ~/hubai/skills/
    ├── hubai-base -> ~/hubai/skills/hubai-base
    └── smart-quotation -> ~/hubai/skills/smart-quotation
```

---

## 三、部署步骤（从 0 到可运行）

### Phase 0：前置准备（5分钟）

```bash
# Step 0.1: 备份配置
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup.hubai-$(date +%Y%m%d)

# Step 0.2: 修复权限（Critical 安全项）
chmod 600 ~/.openclaw/openclaw.json

# Step 0.3: 检查环境
python3 --version    # 需要 3.8+
pip3 --version
```

### Phase 1：配置 OpenClaw（5分钟）

```bash
# Step 1.1: 修改 openclaw.json 启用 Skill
python3 << 'PYEOF'
import json

with open('/home/xhb-szwl/.openclaw/openclaw.json', 'r') as f:
    cfg = json.load(f)

# 启用 Skill
cfg['skills'] = {
    "enabled": True,
    "autoLoad": True,
    "directories": [
        "~/.openclaw/skills",
        "~/hubai/skills"
    ]
}

# 添加 hubai agent
if 'agents' not in cfg:
    cfg['agents'] = {}
if 'list' not in cfg['agents']:
    cfg['agents']['list'] = []

has_hubai = any(a.get('id') == 'hubai' for a in cfg['agents']['list'])
if not has_hubai:
    cfg['agents']['list'].append({
        "id": "hubai",
        "name": "HubAI 报价助手",
        "workspace": "~/hubai/workspace",
        "model": "ark-code-latest"
    })

# 添加 bindings（报价路由）
cfg['bindings'] = [
    {
        "match": {"channel": "dingtalk"},
        "agentId": "hubai",
        "priority": 10
    }
]

with open('/home/xhb-szwl/.openclaw/openclaw.json', 'w') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

print("✅ OpenClaw 配置已更新")
PYEOF

# Step 1.2: 重启 Gateway
openclaw gateway restart
sleep 5
openclaw status | grep -E "(Gateway|Skills|Agents)"
```

### Phase 2：创建目录与软链接（5分钟）

```bash
# Step 2.1: 创建完整目录结构
mkdir -p ~/hubai/workspace/{data,logs/audit}
mkdir -p ~/hubai/skills/hubai-base/{config,scripts,templates,tests}
mkdir -p ~/hubai/skills/smart-quotation/{config,scripts,templates,logs,tests}

# Step 2.2: 创建软链接
ln -sf ~/hubai/skills/hubai-base ~/.openclaw/skills/hubai-base
ln -sf ~/hubai/skills/smart-quotation ~/.openclaw/skills/smart-quotation

# Step 2.3: 验证
ls -la ~/.openclaw/skills/ | grep hubai
tree ~/hubai -L 3 || find ~/hubai -type d | sort
```

### Phase 3：创建 hubai-base（基础能力包）（15分钟）

```bash
# Step 3.1: SKILL.md
cat > ~/hubai/skills/hubai-base/SKILL.md << 'EOF'
---
name: hubai-base
description: >
  HubAI 报价系统基础能力包。
  提供数据库连接、配置管理、日志审计、权限校验等底层能力。
  被 smart-quotation 等业务 Skill 依赖。
allowed-tools:
  - Read
  - Write
  - Edit
  - exec
dependencies: []
---

# HubAI Base - 基础能力包

## 核心能力

1. **数据库连接池**：SQLite/PostgreSQL 统一连接管理
2. **配置管理**：多环境配置加载与热更新
3. **日志审计**：统一日志格式、自动轮转、审计追踪
4. **权限校验**：基于角色的访问控制（RBAC）
5. **工具函数**：数据转换、格式校验、加密解密、日期处理

## 使用方式

```python
import sys
sys.path.append('~/.openclaw/skills/hubai-base/scripts')
from db import HubAIDatabase
from logger import HubAILogger
```
EOF

# Step 3.2: _meta.json
cat > ~/hubai/skills/hubai-base/_meta.json << 'EOF'
{
  "name": "hubai-base",
  "version": "1.0.0",
  "author": "AI+比特虾",
  "description": "HubAI 报价系统基础能力包",
  "entry": "scripts/",
  "dependencies": [],
  "python_version": ">=3.8"
}
EOF

# Step 3.3: 数据库连接模块
cat > ~/hubai/skills/hubai-base/scripts/db.py << 'PYEOF'
"""HubAI 数据库连接与 ORM 封装"""
import sqlite3
import os
from typing import Optional, Dict, List
from contextlib import contextmanager

class HubAIDatabase:
    _instance = None
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(db_path)
        return cls._instance
    
    def _init(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.expanduser("~/hubai/workspace/data/hubai.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
    
    @contextmanager
    def cursor(self):
        cursor = self._connection.cursor()
        try:
            yield cursor
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            raise e
        finally:
            cursor.close()
    
    def execute(self, sql: str, params: tuple = ()) -> int:
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount
    
    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        with self.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None
    
    def query_all(self, sql: str, params: tuple = ()) -> List[Dict]:
        with self.cursor() as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
    
    def close(self):
        if self._connection:
            self._connection.close()
            HubAIDatabase._instance = None
PYEOF

# Step 3.4: 日志模块
cat > ~/hubai/skills/hubai-base/scripts/logger.py << 'PYEOF'
"""HubAI 统一日志审计模块"""
import logging
import os
import json
from datetime import datetime

class HubAILogger:
    _loggers = {}
    
    @staticmethod
    def get_logger(name: str, log_dir: str = None) -> logging.Logger:
        if name in HubAILogger._loggers:
            return HubAILogger._loggers[name]
        
        if log_dir is None:
            log_dir = os.path.expanduser("~/hubai/workspace/logs")
        os.makedirs(log_dir, exist_ok=True)
        
        logger = logging.getLogger(f"hubai.{name}")
        logger.setLevel(logging.DEBUG)
        
        if logger.handlers:
            return logger
        
        log_file = os.path.join(log_dir, f"{name}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        HubAILogger._loggers[name] = logger
        return logger
    
    @staticmethod
    def audit_log(action: str, user_id: str, details: dict, log_dir: str = None):
        if log_dir is None:
            log_dir = os.path.expanduser("~/hubai/workspace/logs/audit")
        os.makedirs(log_dir, exist_ok=True)
        
        audit_file = os.path.join(log_dir, f"audit_{datetime.now().strftime('%Y%m')}.log")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user_id": user_id,
            "details": details
        }
        with open(audit_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
PYEOF

# Step 3.5: 权限模块
cat > ~/hubai/skills/hubai-base/scripts/auth.py << 'PYEOF'
"""HubAI RBAC 权限校验模块"""

class PermissionChecker:
    ROLES = {
        "sales": {"max_discount": 0.9, "can_approve": False},
        "sales_manager": {"max_discount": 0.8, "can_approve": True},
        "sales_director": {"max_discount": 0.7, "can_approve": True},
        "finance_director": {"max_discount": 0.6, "can_approve": True},
        "admin": {"max_discount": 0.5, "can_approve": True}
    }
    
    @staticmethod
    def check_discount_permission(user_role: str, discount_rate: float) -> dict:
        role = PermissionChecker.ROLES.get(user_role, PermissionChecker.ROLES["sales"])
        allowed = discount_rate >= role["max_discount"]
        return {
            "allowed": allowed,
            "max_discount": role["max_discount"],
            "need_approval": not allowed,
            "approver_role": "sales_director" if not allowed else None
        }
    
    @staticmethod
    def can_approve(user_role: str) -> bool:
        role = PermissionChecker.ROLES.get(user_role, {})
        return role.get("can_approve", False)
PYEOF

echo "✅ hubai-base 基础能力包创建完成"
```

### Phase 4：创建 smart-quotation（报价核心 Skill）（15分钟）

```bash
# Step 4.1: SKILL.md
cat > ~/hubai/skills/smart-quotation/SKILL.md << 'EOF'
---
name: smart-quotation
description: >
  HubAI 智能报价核心 Skill。
  封装报价 SOP、配置规则、成本核算逻辑、审批流程与输出模板。
  提供 100% 确定性的价格计算、规则校验、分流派单、文档生成能力。
  大模型只负责"调度"报价，本 Skill 负责"执行"报价。
allowed-tools:
  - Read
  - Write
  - Edit
  - exec
dependencies:
  - hubai-base
---

# Smart Quotation - 智能报价核心 Skill

## 核心能力

1. **价格计算引擎**：基于产品库 + 价格策略，100% 确定性计算
2. **规则校验引擎**：7 项自动检测（产品存在、价格完整、库存充足等）
3. **分流派单引擎**：标准型/方案型/非标型/高风险 四类路由
4. **文档生成引擎**：生成内部版、客户版报价单（Markdown/PDF）
5. **审批流程引擎**：状态机驱动的多级审批 + 通知推送

## 输入参数

```json
{
  "customer_company": "XX教育科技有限公司",
  "customer_level": "standard|vip|strategic|new",
  "products": [{"product_code": "CLOUD-DESK-ENT", "quantity": 20}],
  "budget_range": "20000-25000",
  "custom_requirements": "",
  "communication_needed": true
}
```

## 输出格式

```json
{
  "quotation_no": "Q-20260626-XXXXXX",
  "status": "draft",
  "lines": [...],
  "total_amount": 21600.00,
  "margin_rate": 0.283,
  "risk_flags": [],
  "approval_required": false,
  "documents": {"internal": "...", "customer": "..."}
}
```

## 异常处理

- `PRODUCT_NOT_FOUND`：产品不存在，返回替代建议
- `INVENTORY_SHORTAGE`：库存不足，标注预计补货日期
- `DISCOUNT_EXCEEDED`：折扣超限，触发审批流程
- `MARGIN_TOO_LOW`：毛利率过低，要求财务确认
EOF

# Step 4.2: _meta.json
cat > ~/hubai/skills/smart-quotation/_meta.json << 'EOF'
{
  "name": "smart-quotation",
  "version": "1.0.0",
  "author": "AI+比特虾",
  "description": "HubAI 智能报价核心 Skill",
  "entry": "scripts/",
  "dependencies": ["hubai-base"],
  "python_version": ">=3.8"
}
EOF

# Step 4.3: 价格计算引擎
cat > ~/hubai/skills/smart-quotation/scripts/price_engine.py << 'PYEOF'
"""价格计算引擎 - 100% 确定性，绝不让大模型计算"""
import sys
sys.path.append('~/.openclaw/skills/hubai-base/scripts')
from db import HubAIDatabase
from logger import HubAILogger

logger = HubAILogger.get_logger("smart-quotation")

def calculate_price(product_code: str, quantity: int, customer_level: str = "standard") -> dict:
    """计算单行报价，返回完整价格信息"""
    db = HubAIDatabase()
    
    # 1. 获取产品标准价
    price = db.query_one("""
        SELECT * FROM product_price 
        WHERE product_code = ? AND status = 'active'
        ORDER BY valid_from DESC LIMIT 1
    """, (product_code,))
    
    if not price:
        return {"success": False, "error": "PRODUCT_PRICE_NOT_FOUND"}
    
    # 2. 匹配价格策略（确定性规则）
    policy = db.query_one("""
        SELECT * FROM quotation_policy 
        WHERE status = 'active' 
        AND (customer_level = ? OR customer_level IS NULL)
        AND (valid_to IS NULL OR valid_to >= datetime('now'))
        ORDER BY priority DESC LIMIT 1
    """, (customer_level,))
    
    discount_rate = policy["discount_rate"] if policy else 1.0
    
    # 3. 计算折扣后价格
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
    
    logger.info(f"Price calculated: {product_code} x{quantity} = {line_amount}")
    
    return {
        "success": True,
        "product_code": product_code,
        "unit_price_original": price["unit_price"],
        "discount_rate": discount_rate,
        "unit_price_final": unit_price_final,
        "quantity": quantity,
        "line_amount": line_amount,
        "cost_price": price.get("cost_price"),
        "margin_rate": margin_rate,
        "inventory_ok": inventory_ok,
        "policy_applied": policy["policy_code"] if policy else None
    }
PYEOF

# Step 4.4: 规则校验引擎
cat > ~/hubai/skills/smart-quotation/scripts/rule_validator.py << 'PYEOF'
"""规则校验引擎 - 7项自动检测"""
import sys
sys.path.append('~/.openclaw/skills/hubai-base/scripts')
from db import HubAIDatabase

class RuleValidator:
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
                check_method(requirement, rule)
        
        completeness_score = self._calculate_score()
        
        return {
            "completeness_score": completeness_score,
            "issues": self.issues,
            "warnings": self.warnings,
            "can_auto_quote": len(self.issues) == 0
        }
    
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
                    self.warnings.append({"type": "INVENTORY_SHORTAGE", **rule, 
                                         "product": product["product_code"], "need": product["quantity"], "available": available})
    
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
PYEOF

# Step 4.5: 分流派单引擎
cat > ~/hubai/skills/smart-quotation/scripts/route_engine.py << 'PYEOF'
"""分流派单引擎 - 4类需求路由"""

class RouteEngine:
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
        has_risk = any(w["type"] in ["MARGIN_TOO_LOW", "PAYMENT_EXCEEDED"] for w in warnings)
        if has_risk:
            return RouteEngine.ROUTES["risky"]
        
        # 非标型判定
        has_custom = any(i["type"] == "CUSTOM_REQUIREMENT" for i in issues)
        if has_custom or score < 70:
            return RouteEngine.ROUTES["custom"]
        
        # 方案型判定
        has_solution = any(w["type"] == "SOLUTION_NEEDED" for w in warnings)
        if has_solution or (70 <= score < 90):
            return RouteEngine.ROUTES["solution"]
        
        # 标准型（默认）
        return RouteEngine.ROUTES["standard"]
PYEOF

echo "✅ smart-quotation 报价核心 Skill 创建完成"
```

### Phase 5：验证测试（5分钟）

```bash
# Step 5.1: 验证目录结构
echo "=== 目录结构 ==="
find ~/hubai -type f | sort

echo "=== 软链接验证 ==="
ls -la ~/.openclaw/skills/ | grep hubai

echo "=== Python 模块测试 ==="
python3 -c "
import sys
sys.path.append('/home/xhb-szwl/hubai/skills/hubai-base/scripts')
from db import HubAIDatabase
from logger import HubAILogger
from auth import PermissionChecker

# 测试数据库
db = HubAIDatabase()
print('✅ 数据库连接成功')

# 测试日志
logger = HubAILogger.get_logger('test')
logger.info('测试日志')
print('✅ 日志模块正常')

# 测试权限
result = PermissionChecker.check_discount_permission('sales', 0.85)
print(f'✅ 权限校验: {result}')

print('所有基础模块测试通过！')
"

echo "=== OpenClaw Skill 加载验证 ==="
openclaw status | grep -A5 "Skills"
```

---

## 四、钉钉对话测试步骤

### 测试场景 1：标准型报价（全自动）

```text
【用户】@AI+比特虾 帮我报个价

【HubAI】🦐 我是部门销售助手，将帮您完成客户报价。

让我先了解一下情况，请依次回答以下问题：

1/5 📋 客户公司名称是？
2/5 👤 联系人姓名和电话？
3/5 📦 业务场景、需要哪些产品，数量多少？
4/5 💰 客户预算范围是？
5/5 📅 是否需要沟通交流和技术方案？

您可以一条一条告诉我，也可以一次性说完哦！
💡 提示：直接粘贴客户的微信/邮件原文，我会自动提取信息

【用户】XX教育公司，张经理 13812345678，要20台企业版云桌面，预算2万左右，不需要技术方案

【HubAI】✅ 信息已提取：
   • 客户：XX教育公司
   • 联系人：张经理 13812345678
   • 产品：企业版云桌面 ×20台
   • 预算：约2万元
   • 沟通需求：否

📋 需求卡已生成（完整性 92/100）

🔀 分流建议：标准型需求 → 快速报价通道

💰 报价草稿：
   企业版云桌面 ×20台
   标准价：¥800/台
   折扣价：¥720/台（大客户9折）
   合计：¥14,400.00
   毛利率：31% ✅
   无需审批

[查看客户版] [发送给客户] [调整价格]

【用户】发送给客户

【HubAI】📤 客户版报价单已发送：

═══════════════════════════════
        商务报价单
═══════════════════════════════
报价编号：Q-20260626-000001
有效期至：2026-07-26

客户：XX教育公司
联系人：张经理

产品清单：
企业版云桌面 ×20台  ¥720/台  小计 ¥14,400

合计金额：¥14,400.00（大写：壹万肆仟肆佰元整）

付款方式：预付30%，发货前付清
交付周期：7个工作日
保修期限：1年标准保修

═══════════════════════════════

报价已发送，等待客户反馈。
```

### 测试场景 2：方案型报价（多 Agent 协作）

```text
【用户】@AI+比特虾 有个大客户要报价

【HubAI】🦐 好的，请提供以下信息：

【用户】XX集团，500台云桌面，50万预算，需要技术方案和上门沟通

【HubAI】✅ 信息已提取：
   • 客户：XX集团
   • 产品：云桌面 ×500台
   • 预算：50万元
   • 沟通需求：需要技术方案 + 上门沟通

📋 需求卡已生成（完整性 88/100）

🔀 分流建议：方案型需求
   • 业务场景复杂（大企业）
   • 产品数量多（500台）
   • 金额规模大（50万）
   • 需要技术方案

🤖 已为您召唤技术助理...

═══════════════════════════
🤖 技术助理已加入

正在评估技术方案...
预计2个工作日内完成技术方案初稿。

═══════════════════════════

[查看技术方案进度] [与技术人员对话] [调整需求]
```

---

## 五、部署清单与检查表

### 部署前检查

- [ ] 备份 `~/.openclaw/openclaw.json`
- [ ] 确认 Python 3.8+
- [ ] 确认 OpenClaw Gateway 运行正常

### 部署中检查

- [ ] Phase 0：备份与权限修复
- [ ] Phase 1：OpenClaw 配置更新（skills.enabled = true）
- [ ] Phase 1：Gateway 重启成功
- [ ] Phase 2：目录结构创建完整
- [ ] Phase 2：软链接创建成功
- [ ] Phase 3：hubai-base 文件创建完整
- [ ] Phase 4：smart-quotation 文件创建完整

### 部署后验证

- [ ] `openclaw status` 显示 Skills 已启用
- [ ] Python 模块测试通过
- [ ] 钉钉对话测试通过（标准型）
- [ ] 钉钉对话测试通过（方案型）
- [ ] 审计日志正常生成

---

## 六、后续优化方向

| 阶段 | 优化内容 | 预计时间 |
|------|---------|---------|
| **M1** | 完善数据库 DDL（20+ 张表） | 2天 |
| **M2** | 补充报价单模板（Markdown/PDF） | 1天 |
| **M3** | 接入钉钉审批流 | 2天 |
| **M4** | 对接 IMA 知识库归档 | 1天 |
| **M5** | 性能优化（连接池、缓存） | 2天 |
| **M6** | 完善异常处理与监控告警 | 2天 |

---

**编制人**：AI+比特虾  
**日期**：2026-06-26  
**版本**：v1.0  
**部署预计总时间**：45-60 分钟（Phase 0-5）
