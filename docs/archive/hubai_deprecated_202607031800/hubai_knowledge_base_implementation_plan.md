# HubAI 知识库基础版详细实施方案

## 一、项目概述

### 1.1 项目背景
当前已具备 `finance-wukong-mvp`（FastAPI + SQLite 财务问数 MVP）和 `wukong_series_archive`（悟空系列内容资产库）。本方案在此基础上，扩展建设一个**可运行、可验证、可升级**的 HubAI 知识库基础版，覆盖财务报表数据、产品知识库、产品报价、博文数据库四大模块，支撑财务/商务/销售/技术四类数字员工。

### 1.2 基础版定位
- **不是**完整企业级平台，而是**业务知识与数据底座 MVP**；
- 本地可运行，单 Docker 容器或 Python 虚拟环境即可启动；
- 采用全开源技术栈，零授权成本；
- 数据库从 SQLite 起步，后续可平滑迁移 PostgreSQL；
- 所有表结构预留扩展字段，支持未来升级到完整系统。

### 1.3 核心目标
| 目标 | 说明 |
|------|------|
| 数据层扩展 | 从单一 `sales_monthly` 扩展到财务/产品/报价/博文四大模块 |
| 知识库化 | 将 Markdown 文档资产转化为可检索的知识切片 |
| 数字员工路由 | 实现四类助理的请求分发与独立处理 |
| 权限隔离 | 延续现有 RBAC 模型，扩展到新产品/报价/博文模块 |
| 可演示 | 提供 Web 页面 + API，可对外演示 |
| 可升级 | 所有设计预留 PostgreSQL / 向量库 / 企业 IM 集成接口 |

---

## 二、技术选型（全开源）

| 层级 | 技术组件 | 版本建议 | 说明 |
|------|---------|---------|------|
| 后端框架 | FastAPI | 0.115+ | 现有基础，异步高性能 |
| 数据库 | SQLite | 3.39+ | 本地零配置，后续迁移 PostgreSQL |
| 数据库迁移 | Alembic（预留） | - | 后续升级时引入 |
| 文档解析 | Python-markdown / Mistune | - | Markdown 转文本入库 |
| 全文检索 | SQLite FTS5 | 内置 | 基础版关键词检索 |
| 向量检索（预留） | Chroma / Qdrant | - | 后续替换 FTS5 |
| Embedding（预留） | BGE-M3 / BGE-Large-ZH | - | 后续知识切片向量化 |
| 本地模型（预留） | Ollama + Qwen2.5 | - | 后续接入本地 LLM |
| 前端演示 | Gradio / Streamlit | 4.x / 1.x | 快速构建对话界面 |
| 容器化 | Docker + Docker Compose | - | 一键启动 |
| 测试 | pytest + httpx | - | 现有测试框架延续 |

---

## 三、现有资产盘点

### 3.1 代码资产
```text
finance-wukong-mvp/
├── app/
│   ├── main.py          (73行)  FastAPI 入口，含健康检查、聊天、查询接口
│   ├── db.py            (32行)  SQLite 连接封装
│   ├── security.py      (39行)  用户/角色/权限过滤
│   ├── nlp.py           (77行)  中文意图识别（规则型）
│   └── service.py       (146行) 业务问答逻辑
├── scripts/
│   ├── init_db.py       (92行)  初始化 sales_monthly + audit_log
│   └── smoke_test.py    (30行)  冒烟测试
└── tests/
    └── test_api.py      (40行)  API 单元测试
```

### 3.2 数据资产
| 资产 | 状态 | 说明 |
|------|------|------|
| `sales_monthly` | ✅ 已有 | 36 行示例数据，覆盖 3 部门 × 6 个月 |
| `audit_log` | ✅ 已有 | 表结构存在，0 条记录 |
| 产品数据 | ❌ 缺失 | 无产品主数据、参数、文档 |
| 报价数据 | ❌ 缺失 | 无价格策略、库存、报价单 |
| 博文数据 | ❌ 缺失 | 无结构化博文库 |
| 知识切片 | ❌ 缺失 | 无文档切分和检索索引 |

### 3.3 内容资产
```text
wukong_series_archive/
├── 01-已发布/          (7篇已发布文章 + 封面素材)
├── 02-大纲规划/        (7份大纲/规划文档)
├── 02-规划与大纲/      (4篇后续选题规划)
└── 03-资源库/          (28份资源文件)
```

---

## 四、数据库设计实施

### 4.1 实施原则
1. **SQLite 兼容**：所有 SQL 使用 SQLite 语法，避免 PostgreSQL 特有函数；
2. **预留字段**：关键表增加 `ext_json` 字段，用于未来扩展；
3. **统一审计**：所有业务表增加 `created_at` / `updated_at`；
4. **外键约束**：SQLite 外键默认关闭，建表脚本需显式启用；
5. **索引策略**：按查询维度建立组合索引，避免全表扫描。

### 4.2 财务模块表实施

#### Phase 1：扩展现有财务表（优先级：P0）

**（1）新建 `dim_department`**
```sql
CREATE TABLE IF NOT EXISTS dim_department (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_code TEXT UNIQUE NOT NULL,
    department_name TEXT NOT NULL,
    parent_department_code TEXT,
    manager_name TEXT,
    status TEXT DEFAULT 'active',
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_dept_code ON dim_department(department_code);
```

**（2）新建 `dim_employee`**
```sql
CREATE TABLE IF NOT EXISTS dim_employee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_code TEXT UNIQUE NOT NULL,
    employee_name TEXT NOT NULL,
    department_code TEXT,
    role TEXT,
    status TEXT DEFAULT 'active',
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_emp_code ON dim_employee(employee_code);
CREATE INDEX IF NOT EXISTS idx_dim_emp_dept ON dim_employee(department_code);
```

**（3）新建 `dim_customer`**
```sql
CREATE TABLE IF NOT EXISTS dim_customer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_code TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    industry TEXT,
    region TEXT,
    customer_level TEXT,
    owner_employee_code TEXT,
    status TEXT DEFAULT 'active',
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_cust_code ON dim_customer(customer_code);
CREATE INDEX IF NOT EXISTS idx_dim_cust_owner ON dim_customer(owner_employee_code);
```

**（4）升级 `sales_monthly` → `fact_finance_monthly`**
```sql
-- 保留原表作为备份
ALTER TABLE sales_monthly RENAME TO sales_monthly_backup;

-- 新建标准事实表
CREATE TABLE fact_finance_monthly (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    department_code TEXT NOT NULL,
    employee_code TEXT,
    customer_code TEXT,
    sales_amount REAL DEFAULT 0,
    collection_amount REAL DEFAULT 0,
    receivable_amount REAL DEFAULT 0,
    cost_amount REAL DEFAULT 0,
    gross_profit REAL DEFAULT 0,
    expense_amount REAL DEFAULT 0,
    target_amount REAL DEFAULT 0,
    budget_amount REAL DEFAULT 0,
    budget_used_amount REAL DEFAULT 0,
    ext_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fact_fin_period ON fact_finance_monthly(year, quarter, month);
CREATE INDEX idx_fact_fin_dept ON fact_finance_monthly(department_code);
CREATE INDEX idx_fact_fin_emp ON fact_finance_monthly(employee_code);

-- 迁移旧数据
INSERT INTO fact_finance_monthly
(year, quarter, month, department_code, employee_code, sales_amount, collection_amount, gross_profit, target_amount, budget_rate, budget_used_amount)
SELECT year, quarter, month, department, salesperson, sales_amount, collection_amount, profit, target_amount, budget_rate, 0
FROM sales_monthly_backup;
```

**（5）新建 `fact_budget`**
```sql
CREATE TABLE IF NOT EXISTS fact_budget (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER,
    department_code TEXT NOT NULL,
    budget_type TEXT NOT NULL,
    budget_amount REAL NOT NULL,
    used_amount REAL DEFAULT 0,
    warning_threshold REAL DEFAULT 90,
    ext_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_budget_period ON fact_budget(year, month, department_code);
```

**（6）新建 `fact_receivable`**
```sql
CREATE TABLE IF NOT EXISTS fact_receivable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receivable_no TEXT UNIQUE NOT NULL,
    customer_code TEXT NOT NULL,
    contract_no TEXT,
    order_no TEXT,
    amount REAL NOT NULL,
    received_amount REAL DEFAULT 0,
    due_date TEXT,
    received_date TEXT,
    status TEXT DEFAULT 'pending',
    owner_employee_code TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recv_customer ON fact_receivable(customer_code);
CREATE INDEX idx_recv_due ON fact_receivable(due_date);
CREATE INDEX idx_recv_owner ON fact_receivable(owner_employee_code);
```

**（7）新建 `report_snapshot`**
```sql
CREATE TABLE IF NOT EXISTS report_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type TEXT NOT NULL,
    report_period TEXT NOT NULL,
    title TEXT NOT NULL,
    markdown_content TEXT NOT NULL,
    data_json TEXT,
    created_by TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_report_type_period ON report_snapshot(report_type, report_period);
```

---

### 4.3 产品知识库模块表实施

#### Phase 2：产品知识库（优先级：P1）

**（1）`product_category`**
```sql
CREATE TABLE IF NOT EXISTS product_category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_code TEXT UNIQUE NOT NULL,
    category_name TEXT NOT NULL,
    parent_category_code TEXT,
    description TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（2）`product`**
```sql
CREATE TABLE IF NOT EXISTS product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    category_code TEXT,
    brand TEXT,
    model TEXT,
    unit TEXT DEFAULT '套',
    short_description TEXT,
    status TEXT DEFAULT 'active',
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_product_code ON product(product_code);
CREATE INDEX idx_product_category ON product(category_code);
```

**（3）`product_spec`**
```sql
CREATE TABLE IF NOT EXISTS product_spec (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL,
    spec_name TEXT NOT NULL,
    spec_value TEXT NOT NULL,
    spec_unit TEXT,
    spec_group TEXT,
    sort_order INTEGER DEFAULT 0,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_spec_product ON product_spec(product_code);
```

**（4）`product_document`**
```sql
CREATE TABLE IF NOT EXISTS product_document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT,
    title TEXT NOT NULL,
    doc_type TEXT,
    file_path TEXT,
    source TEXT,
    version TEXT,
    permission_level TEXT DEFAULT 'internal',
    markdown_content TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_doc_product ON product_document(product_code);
CREATE INDEX idx_doc_type ON product_document(doc_type);
```

**（5）`product_faq`**
```sql
CREATE TABLE IF NOT EXISTS product_faq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    tags TEXT,
    source TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_faq_product ON product_faq(product_code);
```

---

### 4.4 产品报价模块表实施

#### Phase 3：产品报价（优先级：P1）

**（1）`quotation_policy`**
```sql
CREATE TABLE IF NOT EXISTS quotation_policy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_code TEXT UNIQUE NOT NULL,
    policy_name TEXT NOT NULL,
    customer_level TEXT,
    product_category_code TEXT,
    discount_rate REAL DEFAULT 1.0,
    min_quantity INTEGER DEFAULT 1,
    min_amount REAL DEFAULT 0,
    valid_from TEXT,
    valid_to TEXT,
    status TEXT DEFAULT 'active',
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（2）`product_price`**
```sql
CREATE TABLE IF NOT EXISTS product_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL,
    unit_price REAL NOT NULL,
    currency TEXT DEFAULT 'CNY',
    price_type TEXT DEFAULT 'standard',
    valid_from TEXT,
    valid_to TEXT,
    status TEXT DEFAULT 'active',
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_price_product ON product_price(product_code);
```

**（3）`inventory`**
```sql
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL,
    warehouse_code TEXT,
    quantity INTEGER DEFAULT 0,
    reserved_quantity INTEGER DEFAULT 0,
    safety_stock INTEGER DEFAULT 10,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    ext_json TEXT
);

CREATE INDEX idx_inv_product ON inventory(product_code);
```

**（4）`quotation_header` / `quotation_line`**
```sql
CREATE TABLE IF NOT EXISTS quotation_header (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_no TEXT UNIQUE NOT NULL,
    customer_code TEXT NOT NULL,
    quotation_date TEXT,
    valid_until TEXT,
    total_amount REAL DEFAULT 0,
    discount_amount REAL DEFAULT 0,
    final_amount REAL DEFAULT 0,
    status TEXT DEFAULT 'draft',
    created_by TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quotation_line (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_no TEXT NOT NULL,
    product_code TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    discount_rate REAL DEFAULT 1.0,
    line_amount REAL,
    delivery_date TEXT,
    ext_json TEXT
);

CREATE INDEX idx_qh_no ON quotation_header(quotation_no);
CREATE INDEX idx_ql_no ON quotation_line(quotation_no);
```

---

### 4.5 博文数据库模块表实施

#### Phase 4：博文数据库（优先级：P2）

**（1）`blog_article`**
```sql
CREATE TABLE IF NOT EXISTS blog_article (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    series_no TEXT,
    subtitle TEXT,
    author TEXT,
    publish_date TEXT,
    status TEXT DEFAULT 'draft',
    content_markdown TEXT,
    content_summary TEXT,
    keywords TEXT,
    tags TEXT,
    category TEXT,
    source_file TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_blog_code ON blog_article(article_code);
CREATE INDEX idx_blog_series ON blog_article(series_no);
CREATE INDEX idx_blog_status ON blog_article(status);
```

**（2）`blog_outline`**
```sql
CREATE TABLE IF NOT EXISTS blog_outline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outline_code TEXT UNIQUE NOT NULL,
    series_no TEXT,
    title TEXT NOT NULL,
    outline_markdown TEXT,
    planned_publish_date TEXT,
    status TEXT DEFAULT 'planned',
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（3）`blog_resource`**
```sql
CREATE TABLE IF NOT EXISTS blog_resource (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    resource_type TEXT,
    file_path TEXT,
    related_article_code TEXT,
    tags TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

### 4.6 知识切片与检索表

#### Phase 4：知识检索（优先级：P2）

**（1）`knowledge_chunk`（通用切片表）**
```sql
CREATE TABLE IF NOT EXISTS knowledge_chunk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,        -- product_doc / blog_article / faq / policy
    source_id TEXT NOT NULL,          -- product_code / article_code 等
    title TEXT,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER,
    tags TEXT,
    department_scope TEXT,
    permission_level TEXT DEFAULT 'internal',
    embedding_id TEXT,                -- 预留，后续向量库使用
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- FTS5 虚拟表（全文检索）
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunk_fts USING fts5(
    chunk_text,
    title,
    source_type,
    source_id,
    content='knowledge_chunk',
    content_rowid='id'
);

CREATE INDEX idx_chunk_source ON knowledge_chunk(source_type, source_id);
```

---

## 五、后端服务扩展实施

### 5.1 模块结构重组

将现有 `app/service.py` 拆分为模块化结构：

```text
app/
├── main.py              # FastAPI 入口，注册路由
├── db.py                # 数据库连接（扩展连接池预留）
├── security.py          # 用户/角色/权限（扩展新角色）
├── nlp.py               # 意图识别（扩展新意图）
│
├── modules/
│   ├── __init__.py
│   ├── finance/
│   │   ├── service.py     # 财务问数/报表/预警
│   │   ├── schemas.py     # Pydantic 模型
│   │   └── queries.py     # SQL 查询封装
│   │
│   ├── product/
│   │   ├── service.py     # 产品查询/文档/FAQ
│   │   ├── importer.py    # 产品数据导入
│   │   └── retrieval.py   # 产品知识检索
│   │
│   ├── quotation/
│   │   ├── service.py     # 报价生成/库存检查
│   │   ├── pricing.py     # 价格计算引擎
│   │   └── rules.py       # 报价策略规则
│   │
│   ├── blog/
│   │   ├── service.py     # 博文查询/检索
│   │   ├── importer.py    # 博文归档导入
│   │   └── retrieval.py   # 博文知识检索
│   │
│   └── knowledge/
│       ├── chunker.py     # 文档切片
│       ├── indexer.py     # 索引构建（FTS5）
│       └── search.py      # 统一检索接口
│
├── templates/             # Web 页面模板
└── static/                # CSS/JS
```

### 5.2 数字员工路由设计

在 `main.py` 中增加数字员工路由层：

```python
from fastapi import APIRouter
from app.modules.finance.service import FinanceService
from app.modules.product.service import ProductService
from app.modules.quotation.service import QuotationService
from app.modules.blog.service import BlogService

router = APIRouter(prefix="/api/assistants")

@router.post("/finance/query")
def finance_query(payload: QueryPayload):
    return FinanceService.answer(payload)

@router.post("/product/query")
def product_query(payload: QueryPayload):
    return ProductService.answer(payload)

@router.post("/quotation/query")
def quotation_query(payload: QueryPayload):
    return QuotationService.answer(payload)

@router.post("/blog/query")
def blog_query(payload: QueryPayload):
    return BlogService.answer(payload)
```

### 5.3 意图识别扩展

在 `nlp.py` 中增加新意图：

```python
INTENT_MAP = {
    # 财务意图
    "finance_metric": ["销售额", "回款", "利润", "预算", "成本"],
    "finance_report": ["报表", "简报", "周报", "月报"],
    "finance_alert": ["预警", "异常", "超标"],

    # 产品意图
    "product_info": ["产品", "参数", "型号", "规格"],
    "product_doc": ["文档", "手册", "白皮书"],
    "product_faq": ["FAQ", "常见问题"],

    # 报价意图
    "quotation_generate": ["报价", "价格", "多少钱"],
    "stock_check": ["库存", "现货", "有没有货"],
    "discount_query": ["折扣", "优惠", "最低价"],

    # 博文意图
    "blog_search": ["文章", "博文", "悟空系列"],
    "blog_ask": ["怎么写", "方案", "内容生成"],
}
```

---

## 六、数据初始化实施

### 6.1 初始化脚本规划

```text
scripts/
├── init_db.py                 # 主入口：调用所有子初始化
├── init_dimensions.py         # 维度表初始化（部门/员工/客户）
├── init_finance_data.py       # 财务事实表数据生成
├── init_products.py           # 产品主数据 + 参数 + FAQ 导入
├── init_inventory.py          # 库存初始数据
├── init_quotation_policies.py # 报价策略初始化
├── init_blog_archive.py       # 悟空系列博文归档导入
├── build_fts_index.py         # FTS5 全文索引构建
└── smoke_test.py              # 全链路冒烟测试
```

### 6.2 财务数据初始化

**维度数据**：
```python
departments = [
    {"code": "DEPT_EAST", "name": "华东销售部", "manager": "王经理"},
    {"code": "DEPT_SOUTH", "name": "华南销售部", "manager": "李经理"},
    {"code": "DEPT_NORTH", "name": "华北销售部", "manager": "张经理"},
    {"code": "DEPT_RD", "name": "研发部", "manager": "赵总监"},
    {"code": "DEPT_MARKET", "name": "市场部", "manager": "陈总监"},
]

employees = [
    {"code": "EMP001", "name": "张三", "dept": "DEPT_EAST", "role": "sales"},
    {"code": "EMP002", "name": "李四", "dept": "DEPT_SOUTH", "role": "sales"},
    {"code": "EMP003", "name": "王经理", "dept": "DEPT_EAST", "role": "manager"},
    {"code": "EMP099", "name": "财务管理员", "dept": None, "role": "finance_admin"},
]
```

**财务事实数据**：迁移现有 `sales_monthly` 36 行数据，并补充预算/回款表。

### 6.3 产品数据初始化（示例）

```python
products = [
    {
        "code": "P-AI-GW-001",
        "name": "HubAI 智能网关",
        "category": "CAT_AI_HARDWARE",
        "brand": "HubAI",
        "model": "GW-Pro-2026",
        "specs": [
            {"name": "并发会话数", "value": "500", "unit": "路", "group": "性能"},
            {"name": "支持协议", "value": "HTTP/HTTPS/MQTT", "group": "接口"},
            {"name": "部署方式", "value": "本地化/私有云/混合云", "group": "部署"},
        ],
        "faqs": [
            {"question": "支持哪些部署方式？", "answer": "支持本地化部署、私有云部署和混合云部署三种模式。"},
        ]
    },
]
```

### 6.4 悟空系列博文导入

编写 `init_blog_archive.py`，扫描 `wukong_series_archive/` 目录：

```python
def import_blog_archive():
    base_path = Path("wukong_series_archive")
    for md_file in base_path.rglob("*.md"):
        article_code = generate_code(md_file)
        title = extract_title(md_file)
        content = md_file.read_text(encoding='utf-8')
        summary = generate_summary(content, max_length=500)
        keywords = extract_keywords(content)

        insert_blog_article(
            article_code=article_code,
            title=title,
            source_file=str(md_file),
            content_markdown=content,
            content_summary=summary,
            keywords=keywords,
            status="published" if "01-已发布" in str(md_file) else "draft"
        )
```

### 6.5 知识切片构建

编写 `build_fts_index.py`：

```python
def chunk_and_index():
    # 1. 产品文档切片
    for doc in fetch_all("SELECT * FROM product_document"):
        chunks = semantic_chunk(doc["markdown_content"], chunk_size=800)
        for idx, chunk in enumerate(chunks):
            chunk_id = insert_chunk("product_doc", doc["product_code"], doc["title"], chunk, idx)
            insert_fts(chunk_id, chunk, doc["title"], "product_doc", doc["product_code"])

    # 2. 博文切片
    for article in fetch_all("SELECT * FROM blog_article"):
        chunks = semantic_chunk(article["content_markdown"], chunk_size=1000)
        for idx, chunk in enumerate(chunks):
            chunk_id = insert_chunk("blog_article", article["article_code"], article["title"], chunk, idx)
            insert_fts(chunk_id, chunk, article["title"], "blog_article", article["article_code"])

    # 3. FAQ 直接入库
    for faq in fetch_all("SELECT * FROM product_faq"):
        chunk_id = insert_chunk("faq", faq["product_code"], faq["question"], faq["answer"], 0)
        insert_fts(chunk_id, faq["answer"], faq["question"], "faq", faq["product_code"])
```

---

## 七、API 设计实施

### 7.1 财务助理 API

```text
GET  /api/finance/summary?period=2026-06&scope=dept
GET  /api/finance/sales?period=2026-Q2&department=DEPT_EAST
GET  /api/finance/collections?period=2026-06
GET  /api/finance/budget?period=2026-06
GET  /api/finance/alerts?period=2026-06
POST /api/finance/report/generate
     Body: {"period":"2026-06","report_type":"monthly","scope":"all"}
GET  /api/finance/reports
GET  /api/finance/reports/{report_id}
```

### 7.2 产品助理 API

```text
GET  /api/products
GET  /api/products/{product_code}
GET  /api/products/{product_code}/specs
GET  /api/products/{product_code}/documents
GET  /api/products/{product_code}/faqs
POST /api/products/search
     Body: {"query":"智能网关 并发","filters":{"category":"CAT_AI_HARDWARE"}}
POST /api/products/ask
     Body: {"question":"HubAI网关支持哪些部署方式？","product_code":"P-AI-GW-001"}
```

### 7.3 报价助理 API

```text
GET  /api/quotations/check-stock?product_code=P-AI-GW-001
POST /api/quotations/generate
     Body: {"customer_code":"C001","items":[{"product_code":"P-AI-GW-001","qty":2}]}
POST /api/quotations/create
GET  /api/quotations/{quotation_no}
POST /api/quotations/{quotation_no}/export
GET  /api/quotations/policies
```

### 7.4 博文助理 API

```text
GET  /api/blogs/articles
GET  /api/blogs/articles/{article_code}
POST /api/blogs/search
     Body: {"query":"RAG 知识库","filters":{"status":"published"}}
POST /api/blogs/ask
     Body: {"question":"悟空系列中哪篇讲RAG？"}
GET  /api/blogs/outlines
GET  /api/blogs/resources
```

### 7.5 统一知识检索 API

```text
POST /api/knowledge/search
     Body: {"query":"预算执行率","filters":{"source_type":"blog_article","permission_level":"internal"}}

POST /api/knowledge/ask
     Body: {"question":"怎么构建企业知识库？","user_id":"u_sales_zhang"}
```

---

## 八、前端演示实施

### 8.1 方案选择

基础版采用 **Gradio** 快速构建对话界面，原因：
- 5 分钟可搭建多标签页界面；
- 支持 Markdown 渲染；
- 支持文件上传；
- 支持多用户会话；
- 与 FastAPI 后端配合简单。

### 8.2 界面规划

```text
HubAI 基础版演示 /
├── 财务助理
│   └── 聊天窗口 + 快捷问题 + 报表下载
├── 产品助理
│   └── 聊天窗口 + 产品搜索 + 文档查看
├── 报价助理
│   └── 聊天窗口 + 报价单生成 + 库存查询
├── 博文助理
│   └── 聊天窗口 + 文章检索 + 内容预览
└── 管理后台
    ├── 数据导入
    ├── 知识切片
    └── 用户权限
```

### 8.3 Gradio 核心代码框架

```python
import gradio as gr
import requests

API_BASE = "http://localhost:8000/api"

def finance_chat(message, user_id):
    resp = requests.post(f"{API_BASE}/assistants/finance/query",
                        json={"message": message, "user_id": user_id})
    return resp.json().get("markdown", "服务异常")

def product_chat(message, user_id):
    resp = requests.post(f"{API_BASE}/assistants/product/query",
                        json={"message": message, "user_id": user_id})
    return resp.json().get("markdown", "服务异常")

# 构建多标签页界面
with gr.Blocks(title="HubAI 企业知识库基础版") as demo:
    gr.Markdown("# HubAI 企业知识库基础版")
    with gr.Tab("财务助理"):
        gr.ChatInterface(fn=finance_chat)
    with gr.Tab("产品助理"):
        gr.ChatInterface(fn=product_chat)
    # ... 其他标签页

demo.launch(server_name="0.0.0.0", server_port=7860)
```

---

## 九、测试验证方案

### 9.1 单元测试

```text
tests/
├── test_finance_api.py      # 财务 API 测试
├── test_product_api.py      # 产品 API 测试
├── test_quotation_api.py    # 报价 API 测试
├── test_blog_api.py         # 博文 API 测试
├── test_knowledge_search.py # 知识检索测试
├── test_security.py         # 权限边界测试
└── test_integration.py      # 端到端集成测试
```

### 9.2 测试用例示例

**财务权限测试**：
```python
def test_sales_cannot_see_other_department():
    resp = client.post("/api/finance/sales",
                      json={"user_id": "EMP001", "period": "2026-06"})
    assert "华东销售部" in resp.json()["data"][0]["department"]
    assert "华南销售部" not in str(resp.json())
```

**知识检索测试**：
```python
def test_knowledge_search_returns_source():
    resp = client.post("/api/knowledge/search",
                      json={"query": "RAG 知识库"})
    assert resp.json()["code"] == 0
    assert len(resp.json()["data"]["results"]) > 0
    assert "source_type" in resp.json()["data"]["results"][0]
```

### 9.3 冒烟测试

延续现有 `scripts/smoke_test.py`，扩展为全链路验证：

```python
SMOKE_CASES = [
    ("finance", "u_finance_admin", "本月销售额", "finance_metric"),
    ("product", "u_sales_zhang", "HubAI网关参数", "product_info"),
    ("quotation", "u_sales_zhang", "P-AI-GW-001库存", "stock_check"),
    ("blog", "u_sales_zhang", "悟空系列RAG", "blog_search"),
    ("knowledge", "u_sales_zhang", "怎么建知识库", "knowledge_ask"),
]
```

---

## 十、部署实施

### 10.1 本地开发部署

```bash
# 1. 克隆/进入项目目录
cd finance-wukong-mvp

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
pip install gradio  # 新增前端依赖

# 4. 初始化数据库
python scripts/init_db.py
python scripts/init_dimensions.py
python scripts/init_finance_data.py
python scripts/init_products.py
python scripts/init_inventory.py
python scripts/init_quotation_policies.py
python scripts/init_blog_archive.py
python scripts/build_fts_index.py

# 5. 运行测试
pytest tests/ -v
python scripts/smoke_test.py

# 6. 启动服务
# 终端1：启动 FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端2：启动 Gradio 前端
python frontend/app.py
```

### 10.2 Docker 部署

更新 `docker-compose.yml`：

```yaml
services:
  hubai-backend:
    build: .
    container_name: hubai-basic-backend
    ports:
      - "8000:8000"
    volumes:
      - hubai_data:/data
      - ./wukong_series_archive:/app/wukong_series_archive:ro
    environment:
      - HUBAI_DB_PATH=/data/hubai_basic.db
      - HUBAI_ARCHIVE_PATH=/app/wukong_series_archive
    command: >
      sh -c "python scripts/init_db.py &&
             python scripts/init_all.py &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"

  hubai-frontend:
    build: ./frontend
    container_name: hubai-basic-frontend
    ports:
      - "7860:7860"
    environment:
      - API_BASE=http://hubai-backend:8000/api
    depends_on:
      - hubai-backend

volumes:
  hubai_data:
```

### 10.3 升级路径

| 阶段 | 当前状态 | 升级动作 | 目标状态 |
|------|---------|---------|---------|
| 基础版 v0.1 | SQLite + FTS5 | 完成四大模块 + Gradio | 可演示 MVP |
| 基础版 v0.2 | SQLite + FTS5 | 引入 Alembic 迁移 + 数据导入工具 | 可维护 |
| 进阶版 v1.0 | SQLite | 迁移 PostgreSQL + Chroma | 生产级数据库 |
| 进阶版 v1.1 | 本地单实例 | Docker Swarm / K8s 部署 | 高可用 |
| 完整版 v2.0 | 本地模型 | 接入 Ollama / vLLM | 本地 LLM |
| 完整版 v2.1 | Web 界面 | 接入钉钉 / 飞书 / 企微 | 企业 IM 集成 |

---

## 十一、实施排期建议

| 阶段 | 任务 | 预计工时 | 产出物 |
|------|------|---------|--------|
| **Phase 1** | 数据库扩展：财务/维度表 | 0.5 天 | 新表结构 + 初始化脚本 |
| **Phase 2** | 产品知识库表 + 初始化 | 0.5 天 | 产品数据 + FAQ |
| **Phase 3** | 报价模块表 + 初始化 | 0.5 天 | 报价策略 + 库存数据 |
| **Phase 4** | 博文数据库 + 归档导入 | 0.5 天 | 结构化博文库 |
| **Phase 5** | 知识切片 + FTS5 索引 | 0.5 天 | 可检索知识库 |
| **Phase 6** | 后端模块拆分 + API 扩展 | 1 天 | 模块化服务 + 新 API |
| **Phase 7** | 数字员工路由 + 意图扩展 | 0.5 天 | 四类助理分发 |
| **Phase 8** | Gradio 前端搭建 | 0.5 天 | 多标签页演示界面 |
| **Phase 9** | 测试 + 冒烟 + 文档 | 0.5 天 | 测试用例 + 部署文档 |
| **总计** | | **4.5 天** | **可运行基础版** |

---

## 十二、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| SQLite 并发性能不足 | 多用户同时查询卡顿 | 基础版限定单用户演示；后续迁移 PostgreSQL |
| FTS5 中文分词效果差 | 检索不准确 | 基础版先用关键词匹配；后续接入 Jieba / Chroma |
| 知识切片质量差 | RAG 回答质量低 | 人工审核关键切片；后续优化 chunk_size 和 overlap |
| 数据初始化工作量大 | 实施延期 | 先导入示例数据；真实数据后续批量导入 |
| 权限模型过于简单 | 安全合规风险 | 基础版演示级；生产环境接入 OAuth / LDAP |

---

**编制人**：AI+比特虾  
**日期**：2026-06-23  
**版本**：v1.0 - 基础版详细实施方案
