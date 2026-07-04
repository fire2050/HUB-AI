# HubAI 企业知识库设计与部署建设方案

## 一、方案概述

### 1.1 方案名称
**HubAI 企业知识库与数字员工平台**

### 1.2 核心定位
面向企业多部门场景，构建以**共享知识库 + 数字员工 + 业务数据问答 + AI 工作流**为核心的企业级 AI 应用底座，支撑财务、商务、销售、技术四类部门助理的智能化运营。

### 1.3 建设目标

- **知识统一沉淀**：产品、方案、合同、报价、财务、技术等企业知识资产统一入库；
- **数据智能问答**：通过自然语言查询业务数据（销售、回款、预算、库存、订单等）；
- **部门助理自动化**：财务助理、商务助理、销售助理、技术助理各司其职；
- **权限与审计隔离**：不同角色访问不同知识与数据，操作全程可审计；
- **可持续扩展**：基础版采用开源技术构建，可平滑升级到完整系统。

---

## 二、总体架构设计

```text
┌──────────────────────────────────────────────┐
│                 用户入口层                    │
│ Web控制台 / 钉钉 / 飞书 / 企微 / 移动端          │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│              数字员工应用层                   │
│ 财务助理 │ 商务助理 │ 销售助理 │ 技术助理        │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│              HubAI 能力中台层                 │
│ RAG检索 │ 问数引擎 │ 工具调用 │ 工作流编排        │
│ 权限控制 │ 审计日志 │ Prompt管理 │ API网关          │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│              企业知识库与数据底座               │
│ 共享知识库 │ 部门知识库 │ 结构化业务数据库        │
│ 产品库 │ 合同库 │ 报价库 │ 财务库 │ 技术方案库       │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│              模型与基础设施层                   │
│ LLM大模型 │ Embedding模型 │ 向量数据库 │ 关系数据库  │
│ 对象存储 │ 日志系统 │ 权限系统 │ 部署运维          │
└──────────────────────────────────────────────┘
```

---

## 三、知识库体系设计

### 3.1 知识库四层结构

```text
原始资料层
  ↓
清洗加工层
  ↓
标准知识层
  ↓
智能应用层
```

### 3.2 知识库目录设计

```text
企业知识库/
├── 00-知识地图/
│   ├── 知识库总览.md
│   ├── 主题索引.md
│   ├── 场景索引.md
│   ├── FAQ索引.md
│   └── 版本维护记录.md
│
├── 01-共享知识库/
│   ├── 公司介绍/
│   ├── 产品资料/
│   ├── 成功案例/
│   ├── 标准话术/
│   └── 通用FAQ/
│
├── 02-财务知识库/
│   ├── 财务制度/
│   ├── 预算规则/
│   ├── 报表模板/
│   └── 指标口径/
│
├── 03-商务知识库/
│   ├── 合同模板/
│   ├── 报价政策/
│   ├── 库存规则/
│   └── 订单流程/
│
├── 04-销售知识库/
│   ├── 销售话术/
│   ├── 客户案例/
│   ├── 竞品资料/
│   └── 商机流程/
│
├── 05-技术知识库/
│   ├── 产品参数/
│   ├── 技术方案/
│   ├── 实施文档/
│   └── 故障手册/
│
├── 06-知识切片/
│   ├── chunks.jsonl
│   └── metadata.jsonl
│
└── 07-评测集/
    ├── 财务问答测试集.md
    ├── 商务问答测试集.md
    ├── 销售问答测试集.md
    ├── 技术问答测试集.md
    └── 权限边界测试集.md
```

---

## 四、基础版四大模块设计

### 4.1 财务报表数据模块

#### 定位
支撑财务助理进行**智能问数、经营分析、报表输出、异常预警**。

#### 数据表设计

**（1）部门维表：`dim_department`**
```sql
CREATE TABLE dim_department (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_code TEXT UNIQUE NOT NULL,
    department_name TEXT NOT NULL,
    parent_department_code TEXT,
    manager_name TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（2）销售人员维表：`dim_employee`**
```sql
CREATE TABLE dim_employee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_code TEXT UNIQUE NOT NULL,
    employee_name TEXT NOT NULL,
    department_code TEXT,
    role TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（3）客户维表：`dim_customer`**
```sql
CREATE TABLE dim_customer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_code TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    industry TEXT,
    region TEXT,
    customer_level TEXT,
    owner_employee_code TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（4）财务月度事实表：`fact_finance_monthly`**
```sql
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
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（5）预算表：`fact_budget`**
```sql
CREATE TABLE fact_budget (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER,
    department_code TEXT NOT NULL,
    budget_type TEXT NOT NULL,
    budget_amount REAL NOT NULL,
    used_amount REAL DEFAULT 0,
    warning_threshold REAL DEFAULT 90,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（6）回款表：`fact_receivable`**
```sql
CREATE TABLE fact_receivable (
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
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（7）报表快照表：`report_snapshot`**
```sql
CREATE TABLE report_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type TEXT NOT NULL,
    report_period TEXT NOT NULL,
    title TEXT NOT NULL,
    markdown_content TEXT NOT NULL,
    data_json TEXT,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### 核心 API
```text
GET  /api/finance/summary
GET  /api/finance/sales
GET  /api/finance/collections
GET  /api/finance/budget
GET  /api/finance/alerts
POST /api/finance/report/generate
GET  /api/finance/reports
GET  /api/finance/reports/{id}
```

---

### 4.2 产品知识库模块

#### 定位
支撑技术助理输出方案、销售助理解答产品问题、商务助理匹配型号。

#### 数据表设计

**（1）产品分类表：`product_category`**
```sql
CREATE TABLE product_category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_code TEXT UNIQUE NOT NULL,
    category_name TEXT NOT NULL,
    parent_category_code TEXT,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（2）产品主表：`product`**
```sql
CREATE TABLE product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    category_code TEXT,
    brand TEXT,
    model TEXT,
    unit TEXT DEFAULT '套',
    short_description TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（3）产品参数表：`product_spec`**
```sql
CREATE TABLE product_spec (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL,
    spec_name TEXT NOT NULL,
    spec_value TEXT NOT NULL,
    spec_unit TEXT,
    spec_group TEXT,
    sort_order INTEGER DEFAULT 0
);
```

**（4）产品文档表：`product_document`**
```sql
CREATE TABLE product_document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT,
    title TEXT NOT NULL,
    doc_type TEXT,
    file_path TEXT,
    source TEXT,
    version TEXT,
    permission_level TEXT DEFAULT 'internal',
    markdown_content TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（5）产品知识切片表：`knowledge_chunk`**
```sql
CREATE TABLE knowledge_chunk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    title TEXT,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER,
    tags TEXT,
    department_scope TEXT,
    permission_level TEXT DEFAULT 'internal',
    embedding_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（6）产品 FAQ 表：`product_faq`**
```sql
CREATE TABLE product_faq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    tags TEXT,
    source TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### 核心 API
```text
GET  /api/products
GET  /api/products/{product_code}
GET  /api/products/{product_code}/specs
GET  /api/products/{product_code}/documents
POST /api/products/import
POST /api/products/search
POST /api/products/ask
```

---

### 4.3 产品报价模块

#### 定位
支撑销售助理和商务助理进行**报价生成、折扣策略、库存联动、合同前置检查**。

#### 数据表设计

**（1）报价策略表：`quotation_policy`**
```sql
CREATE TABLE quotation_policy (
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
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（2）产品报价表：`product_price`**
```sql
CREATE TABLE product_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL,
    unit_price REAL NOT NULL,
    currency TEXT DEFAULT 'CNY',
    price_type TEXT DEFAULT 'standard',
    valid_from TEXT,
    valid_to TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（3）库存表：`inventory`**
```sql
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL,
    warehouse_code TEXT,
    quantity INTEGER DEFAULT 0,
    reserved_quantity INTEGER DEFAULT 0,
    available_quantity INTEGER GENERATED ALWAYS AS (quantity - reserved_quantity),
    safety_stock INTEGER DEFAULT 10,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（4）报价单表：`quotation_header`**
```sql
CREATE TABLE quotation_header (
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
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（5）报价明细表：`quotation_line`**
```sql
CREATE TABLE quotation_line (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_no TEXT NOT NULL,
    product_code TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    discount_rate REAL DEFAULT 1.0,
    line_amount REAL GENERATED ALWAYS AS (quantity * unit_price * discount_rate),
    delivery_date TEXT
);
```

#### 核心 API
```text
GET  /api/quotations/check-stock
POST /api/quotations/generate
POST /api/quotations/create
GET  /api/quotations/{quotation_no}
POST /api/quotations/{quotation_no}/export
GET  /api/quotations/policies
```

---

### 4.4 博文数据库模块

#### 定位
沉淀悟空系列内容资产，支撑内容检索、文章复用、方案生成和知识运营。

#### 数据表设计

**（1）文章主表：`blog_article`**
```sql
CREATE TABLE blog_article (
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
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（2）大纲规划表：`blog_outline`**
```sql
CREATE TABLE blog_outline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outline_code TEXT UNIQUE NOT NULL,
    series_no TEXT,
    title TEXT NOT NULL,
    outline_markdown TEXT,
    planned_publish_date TEXT,
    status TEXT DEFAULT 'planned',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（3）资源库文件表：`blog_resource`**
```sql
CREATE TABLE blog_resource (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    resource_type TEXT,
    file_path TEXT,
    related_article_code TEXT,
    tags TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（4）博文知识切片表：`blog_knowledge_chunk`**
```sql
CREATE TABLE blog_knowledge_chunk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_code TEXT NOT NULL,
    chunk_type TEXT,
    title TEXT,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER,
    tags TEXT,
    embedding_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### 核心 API
```text
GET  /api/blogs/articles
GET  /api/blogs/articles/{article_code}
POST /api/blogs/search
POST /api/blogs/import
GET  /api/blogs/outlines
GET  /api/blogs/resources
GET  /api/blogs/{article_code}/chunks
POST /api/blogs/ask
```

---

## 五、四类数字员工设计

### 5.1 财务助理

| 维度 | 内容 |
|------|------|
| **定位** | 企业经营数据分析员 |
| **核心能力** | 智能问数、财务报表查询、销售数据分析、预算执行分析、异常预警、报表输出 |
| **数据来源** | 销售订单表、回款表、预算表、费用表、利润表、客户合同表 |
| **典型问题** | "上个月华东区销售额多少？" "Q2 回款完成率怎么样？" "生成一份本周经营简报" |
| **输出形式** | Markdown 报表、Excel 报表、图表摘要、管理层简报、异常预警清单 |
| **权限要求** | 销售个人看本人、部门经理看本部门、财务管理员看全局、管理层看汇总 |

---

### 5.2 商务助理

| 维度 | 内容 |
|------|------|
| **定位** | 订单、库存、合同、报价的流程处理员 |
| **核心能力** | 库存查询、销售订单查询、采购订单查询、合同模板匹配、合同差异比对、风险条款提示、报价单生成、发货条件检查 |
| **数据来源** | 库存表、订单表、采购表、合同模板库、报价政策库、供应商档案、客户档案 |
| **典型问题** | "这个型号还有多少库存？" "客户A的订单到哪一步了？" "帮我检查这份合同有没有风险条款" |
| **输出形式** | 库存查询结果、订单状态表、合同风险摘要、报价单、发货建议、商务待办清单 |

---

### 5.3 销售助理

| 维度 | 内容 |
|------|------|
| **定位** | 客户响应、商机推进和报价辅助工具 |
| **核心能力** | 产品资料查询、客户问题应答、销售话术生成、成功案例匹配、初步报价建议、商机推进建议、客户拜访纪要生成 |
| **数据来源** | 产品知识库、报价政策库、客户档案、销售案例库、竞品资料库、商机记录、CRM数据 |
| **典型问题** | "客户问这款产品和竞品有什么区别，怎么回答？" "帮我生成一份客户拜访纪要" "根据客户需求推荐合适的产品组合" |
| **输出形式** | 客户答复话术、产品推荐表、初步报价建议、客户跟进计划、销售机会分析、成功案例匹配结果 |

---

### 5.4 技术助理

| 维度 | 内容 |
|------|------|
| **定位** | 售前、交付和技术团队的方案生成与知识问答助手 |
| **核心能力** | 产品参数问答、技术方案生成、方案模板调用、实施计划生成、故障排查建议、API 文档问答、技术选型对比、售前方案支持 |
| **数据来源** | 产品手册、技术白皮书、实施方案、项目案例、故障手册、API文档、招投标方案、技术规范 |
| **典型问题** | "帮我生成一份医院数据中台建设方案" "这个产品支持哪些接口？" "根据这份招标参数整理技术应答" |
| **输出形式** | 技术方案、产品参数说明、技术应答表、实施计划、故障排查步骤、售前 PPT 大纲、项目交付清单 |

---

## 六、系统版本规划

### 6.1 基础开源版本

**定位**：基于当前环境快速搭建可运行的知识库与数字员工原型。

**技术栈**：
- 后端：FastAPI
- 数据库：SQLite（后续可迁移到 PostgreSQL）
- 前端：Gradio / Streamlit
- 文档解析：Markdown / Python-markdown
- 检索：SQLite FTS5（后续可升级为 Chroma / Qdrant）
- 模型：本地 Qwen / DeepSeek / 云端 API

**已有基础**：
- `finance-wukong-mvp`：FastAPI + SQLite + 意图识别 + 权限过滤 + 报表输出
- `wukong_series_archive`：完整的悟空系列内容资产

---

### 6.2 整体完整版本

**定位**：企业级长期建设，多部门、多角色、多数据源、多模型、多知识库、多数字员工的统一 AI 能力平台。

**推荐技术栈**：

| 模块 | 推荐技术 |
|------|---------|
| 前端 | React / Vue / Next.js |
| 后端 | FastAPI / Spring Boot / NestJS |
| 数据库 | PostgreSQL / MySQL |
| 向量库 | Milvus / Qdrant / Weaviate |
| 对象存储 | MinIO / S3 |
| 文档解析 | Unstructured / Apache Tika / Docling |
| Embedding | bge-m3 / bge-large-zh / text-embedding-v3 |
| 本地模型 | Qwen / DeepSeek / Yi / GLM |
| 模型服务 | vLLM / Ollama / Xinference |
| RAG 框架 | LangChain / LlamaIndex / Dify / RagFlow |
| 工作流 | Dify Workflow / Flowise / LangGraph |
| 权限认证 | Keycloak / Casdoor / LDAP |
| 日志监控 | OpenTelemetry / Prometheus / Grafana |
| 容器部署 | Docker / Kubernetes |
| CI/CD | GitLab CI / GitHub Actions |

---

## 七、基础版推荐目录结构

```text
hubai-basic/
├── app/
│   ├── main.py
│   ├── db.py
│   ├── security.py
│   ├── nlp.py
│   │
│   ├── modules/
│   │   ├── finance/
│   │   │   ├── service.py
│   │   │   ├── schemas.py
│   │   │   └── queries.py
│   │   │
│   │   ├── product/
│   │   │   ├── service.py
│   │   │   ├── importer.py
│   │   │   └── retrieval.py
│   │   │
│   │   ├── quotation/
│   │   │   ├── service.py
│   │   │   ├── pricing.py
│   │   │   └── rules.py
│   │   │
│   │   ├── blog/
│   │   │   ├── service.py
│   │   │   ├── importer.py
│   │   │   └── retrieval.py
│   │   │
│   │   └── knowledge/
│   │       ├── chunker.py
│   │       ├── indexer.py
│   │       └── search.py
│   │
│   ├── templates/
│   └── static/
│
├── data/
│   ├── imports/
│   │   ├── finance/
│   │   ├── products/
│   │   ├── quotations/
│   │   └── blogs/
│   │
│   ├── knowledge/
│   │   ├── product_docs/
│   │   ├── blog_docs/
│   │   └── chunks/
│   │
│   └── exports/
│
├── scripts/
│   ├── init_db.py
│   ├── import_products.py
│   ├── import_blog_archive.py
│   ├── import_finance_reports.py
│   └── build_knowledge_index.py
│
├── tests/
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 八、知识库运营机制

| 机制 | 说明 |
|------|------|
| **数据清洗是前提** | 垃圾进，垃圾出。入库前务必清理过期草稿、重复文件、乱码内容 |
| **权限管控是底线** | 严禁将薪资、核心技术源码等高敏感数据直接接入全员可见知识库，利用钉钉权限组进行精细化隔离 |
| **持续运营是关键** | 指定专人定期审查"未命中"问题，补充新知识切片，保持知识库新鲜度 |
| **定期更新索引** | 政策法规和业务文档动态变化，新文件加入后运行 re-index |
| **评测集建设** | 准备 20+ 财务问答、20+ 产品问答、10+ 权限边界测试、10+ 幻觉测试 |

---

## 九、实施建议

1. **阶段一**：修复当前记忆/语义索引，建立知识库知识地图
2. **阶段二**：将当前 `sales_monthly` 扩展为完整财务数据模型
3. **阶段三**：建设产品知识库和产品报价模块原型
4. **阶段四**：将悟空系列博文结构化入库
5. **阶段五**：打通四类数字员工路由
6. **阶段六**：接入真实业务系统（ERP、CRM、进销存）

---

**编制人**：AI+比特虾
**日期**：2026-06-23
