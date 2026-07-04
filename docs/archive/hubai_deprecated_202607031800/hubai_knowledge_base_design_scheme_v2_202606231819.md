# HubAI 企业知识库与数字员工平台设计与部署建设方案（V2）

> **版本**：V2（优化版）
> **编制**：AI+比特虾
> **日期**：2026-06-23
> **目标读者**：企业技术负责人、业务部门负责人、AI 实施团队

---

## 一、方案概述

### 1.1 方案名称
**HubAI 企业级一体化知识与业务智能底座**

### 1.2 核心定位
面向企业多部门场景，构建以 **一体化知识与业务智能底座 + 可插拔数字员工生态 + 增强型 RAG + 安全合规体系** 为核心的企业级 AI 应用平台，统一承载知识库、业务数据、数字员工、权限审计、模型路由与工作流编排能力，支撑财务、商务、销售、技术四类部门助理的智能化运营。

### 1.3 建设目标

- **知识统一沉淀**：产品、方案、合同、报价、财务、技术等企业知识资产统一入库、统一检索、统一治理；
- **数据智能问答**：通过自然语言查询业务数据（销售、回款、预算、库存、订单等），回答附带数据来源；
- **部门助理自动化**：财务助理、商务助理、销售助理、技术助理各司其职，共用底座、统一调度；
- **权限与审计隔离**：RBAC + ABAC 组合权限，不同角色访问不同知识与数据，操作全程可审计、可溯源；
- **安全合规保障**：文档密级、敏感数据脱敏、水印溯源、操作日志、导出审计、越权拦截；
- **可持续扩展**：基础版采用开源技术构建，可平滑升级到完整企业版，支持本地/云端双模模型路由。

---

## 二、总体架构设计（优化版）

```text
┌──────────────────────────────────────────────┐
│                终端接入层                      │
│  Web控制台 / 钉钉 / 飞书 / 企微 / 移动端 / API  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│        数字员工与业务应用层                    │
│  财务助理 │ 商务助理 │ 销售助理 │ 技术助理        │
│  · 智能问数    · 库存查询    · 产品问答    · 方案生成   │
│  · 报表输出    · 订单跟踪    · 报价辅助    · 技术应答   │
│  · 异常预警    · 合同检查    · 客户跟进    · 售前支持   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│     HubAI 一体化知识与业务智能底座            │
│                                              │
│  · 内嵌 API 网关        · 智能路由与调度         │
│  · RAG 检索引擎         · 问数引擎              │
│  · 工具调用框架         · 工作流编排            │
│  · 权限控制（RBAC+ABAC） · 审计日志              │
│  · Prompt 管理          · 模型路由（本地/云端）   │
│  · 敏感数据脱敏         · 水印溯源              │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│     企业知识库、业务数据库与知识图谱层          │
│                                              │
│  共享知识库 │ 部门知识库 │ 结构化业务数据库      │
│  产品库    │ 合同库    │ 报价库    │ 财务库    │
│  技术方案库 │ 博文资产库 │ 知识图谱（GraphRAG）  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│       本地/云端双模模型与基础设施层            │
│                                              │
│  LLM 大模型（本地/云端）│ Embedding 模型        │
│  向量数据库              │ 关系数据库            │
│  对象存储                │ 日志与监控系统        │
│  容器化部署（Docker/K8s）│ CI/CD 流水线         │
└──────────────────────────────────────────────┘
```

---

## 三、增强型 RAG 与知识推理体系设计

### 3.1 三层 RAG 演进路线

| 层级 | 技术方案 | 适用阶段 | 核心能力 |
|------|---------|---------|---------|
| **基础版 RAG** | SQLite + FTS5 + 关键词检索 + 标签过滤 | 基础开源版（当前） | 文档检索、chunk 匹配、来源记录 |
| **增强版 RAG** | BM25 + 向量检索（Qdrant/Chroma）+ Rerank + 元数据过滤 | 增强开源版 | HyDE 查询改写、混合排序、权限前置过滤 |
| **企业版 RAG** | GraphRAG + Self-RAG + 多知识库统一检索 + 知识图谱 | 完整企业版 | 跨文档关系推理、答案自检、自动盲区分析 |

### 3.2 核心能力设计

#### （1）语义自适应分块
- 按 Markdown 标题层级分块；
- 表格整表保留不拆分；
- 代码块整段保留；
- FAQ 一问一答为一个 chunk；
- 重叠窗口 128 tokens，防止上下文断裂。

#### （2）混合检索策略
- **第一级**：BM25 关键词检索（标题、正文、标签、元数据）；
- **第二级**：向量语义检索（标题向量 + 内容向量，多向量表示）；
- **第三级**：元数据过滤（部门、权限、密级、时间范围）；
- **第四级**：Rerank 精排（cross-encoder 重排序，取 Top-K）。

#### （3）HyDE 查询改写
- 用户问题 → 生成假设文档 → 向量化 → 检索 → 用真实文档回答；
- 特别适用于业务术语歧义、口语化提问。

#### （4）Self-RAG 答案自检
- 生成答案后，自我评估是否充分、是否有依据；
- 不足时自动补充检索或提示"信息不足，请提供更多上下文"。

#### （5）GraphRAG（企业版）
- 构建实体关系图谱：产品-参数-方案-客户-订单-合同；
- 支持跨文档关系推理，例如"客户 A 去年买了哪些产品，今年的预算还剩多少？"

#### （6）强制引用溯源
- 所有回答必须附带来源文档名称、chunk 编号、原始段落；
- 无来源回答必须明确标记【信息来源不足，仅供参考】；
- 来源可追溯率目标：≥ 95%。

---

## 四、知识库体系设计（优化版）

### 4.1 知识库四层结构

```text
原始资料层
  ↓ 自动/手动导入、OCR、格式转换
清洗加工层
  ↓ 去重、脱敏、分块、标注、权限标记
标准知识层
  ↓ 向量化、索引化、图谱化、评测集建设
智能应用层
  ↓ 问答、生成、分析、推荐、预警
```

### 4.2 知识库目录设计

```text
企业知识库/
├── 00-知识地图/
│   ├── 知识库总览.md
│   ├── 主题索引.md
│   ├── 场景索引.md
│   ├── FAQ索引.md
│   ├── 数字员工使用指南.md
│   └── 版本维护记录.md
│
├── 01-共享知识库/
│   ├── 公司介绍/
│   ├── 产品资料/
│   ├── 成功案例/
│   ├── 标准话术/
│   ├── 通用FAQ/
│   └── 政策法规/
│
├── 02-财务知识库/
│   ├── 财务制度/
│   ├── 预算规则/
│   ├── 报表模板/
│   ├── 指标口径/
│   └── 审计规范/
│
├── 03-商务知识库/
│   ├── 合同模板/
│   ├── 报价政策/
│   ├── 库存规则/
│   ├── 订单流程/
│   └── 供应商档案/
│
├── 04-销售知识库/
│   ├── 销售话术/
│   ├── 客户案例/
│   ├── 竞品资料/
│   ├── 商机流程/
│   └── 报价参考/
│
├── 05-技术知识库/
│   ├── 产品参数/
│   ├── 技术方案/
│   ├── 实施文档/
│   ├── 故障手册/
│   └── API文档/
│
├── 06-知识切片与索引/
│   ├── chunks/
│   ├── vectors/
│   ├── graph/
│   └── metadata/
│
└── 07-评测集/
    ├── 财务问答测试集.md
    ├── 商务问答测试集.md
    ├── 销售问答测试集.md
    ├── 技术问答测试集.md
    ├── 权限边界测试集.md
    └── 幻觉检测测试集.md
```

---

## 五、基础版四大模块设计（优化版）

### 5.1 财务报表数据模块

#### 定位
支撑财务助理进行 **智能问数、经营分析、报表输出、异常预警、预算执行监控**。

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

### 5.2 产品知识库模块

#### 定位
支撑技术助理输出方案、销售助理解答产品问题、商务助理匹配型号，实现产品资料的结构化管理与智能检索。

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

### 5.3 产品报价模块

#### 定位
支撑销售助理和商务助理进行 **报价生成、折扣策略匹配、库存联动检查、合同前置风险检查**。

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

### 5.4 博文数据库模块

#### 定位
沉淀悟空系列内容资产，支撑内容检索、文章复用、方案生成、知识运营与 AI 内容创作辅助。

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

## 六、四类数字员工设计（优化版）

### 6.1 统一调度与接入规范

所有数字员工共用底层底座，禁止各自独立建设知识库：

- **统一知识库**：共享知识库 + 部门知识库 + 业务数据库；
- **统一权限体系**：RBAC + ABAC 组合，权限上下文随请求传递；
- **统一审计日志**：所有问答、数据查询、文件导出全程记录；
- **统一工具调用框架**：每个数字员工只负责意图识别、任务拆解、工具选择、结果组织；
- **统一输入输出标准**：标准 JSON 输入、Markdown 输出、来源引用格式统一。

#### 智能路由机制

| 问题类型 | 路由目标 | 典型特征 |
|---------|---------|---------|
| 销售额、回款、预算、费用、利润 | 财务助理 | 涉及金额、时间、部门、人员 |
| 库存、订单、合同、采购、供应商 | 商务助理 | 涉及物料、数量、流程、文档 |
| 产品推荐、报价、客户跟进、话术 | 销售助理 | 涉及客户、需求、方案、价格 |
| 技术参数、方案生成、实施、故障 | 技术助理 | 涉及产品、架构、配置、排错 |
| 跨域复杂问题 | 主调度 Agent 分解协同 | 多模块关联 |

---

### 6.2 财务助理

| 维度 | 内容 |
|------|------|
| **定位** | 企业经营数据分析员 |
| **核心能力** | 智能问数、财务报表查询、销售数据分析、预算执行分析、异常预警、报表输出 |
| **数据来源** | 销售订单表、回款表、预算表、费用表、利润表、客户合同表 |
| **典型问题** | "上个月华东区销售额多少？" "Q2 回款完成率怎么样？" "生成一份本周经营简报" |
| **输出形式** | Markdown 报表、Excel 报表、图表摘要、管理层简报、异常预警清单 |
| **权限要求** | 销售个人看本人、部门经理看本部门、财务管理员看全局、管理层看汇总 |
| **模型策略** | 优先本地模型，涉密数据不外流 |

---

### 6.3 商务助理

| 维度 | 内容 |
|------|------|
| **定位** | 订单、库存、合同、报价的流程处理员 |
| **核心能力** | 库存查询、销售订单查询、采购订单查询、合同模板匹配、合同差异比对、风险条款提示、报价单生成、发货条件检查 |
| **数据来源** | 库存表、订单表、采购表、合同模板库、报价政策库、供应商档案、客户档案 |
| **典型问题** | "这个型号还有多少库存？" "客户A的订单到哪一步了？" "帮我检查这份合同有没有风险条款" |
| **输出形式** | 库存查询结果、订单状态表、合同风险摘要、报价单、发货建议、商务待办清单 |
| **权限要求** | 看本人负责订单/合同，部门经理看本部门，商务主管看全局 |
| **模型策略** | 本地模型优先，合同风险分析不外流 |

---

### 6.4 销售助理

| 维度 | 内容 |
|------|------|
| **定位** | 客户响应、商机推进和报价辅助工具 |
| **核心能力** | 产品资料查询、客户问题应答、销售话术生成、成功案例匹配、初步报价建议、商机推进建议、客户拜访纪要生成 |
| **数据来源** | 产品知识库、报价政策库、客户档案、销售案例库、竞品资料库、商机记录、CRM数据 |
| **典型问题** | "客户问这款产品和竞品有什么区别，怎么回答？" "帮我生成一份客户拜访纪要" "根据客户需求推荐合适的产品组合" |
| **输出形式** | 客户答复话术、产品推荐表、初步报价建议、客户跟进计划、销售机会分析、成功案例匹配结果 |
| **权限要求** | 看本人客户和商机，经理看团队，销售总监看全局 |
| **模型策略** | 本地/云端均可，报价底价分析走本地 |

---

### 6.5 技术助理

| 维度 | 内容 |
|------|------|
| **定位** | 售前、交付和技术团队的方案生成与知识问答助手 |
| **核心能力** | 产品参数问答、技术方案生成、方案模板调用、实施计划生成、故障排查建议、API 文档问答、技术选型对比、售前方案支持 |
| **数据来源** | 产品手册、技术白皮书、实施方案、项目案例、故障手册、API文档、招投标方案、技术规范 |
| **典型问题** | "帮我生成一份医院数据中台建设方案" "这个产品支持哪些接口？" "根据这份招标参数整理技术应答" |
| **输出形式** | 技术方案、产品参数说明、技术应答表、实施计划、故障排查步骤、售前 PPT 大纲、项目交付清单 |
| **权限要求** | 公开产品资料全员可见，技术方案按项目/角色授权 |
| **模型策略** | 本地模型优先，方案生成可调云端增强 |

---

## 七、权限、安全与审计体系设计（新增）

### 7.1 权限模型：RBAC + ABAC 组合

| 维度 | 说明 |
|------|------|
| **RBAC（角色权限）** | 管理员、财务、销售、商务、技术人员、部门经理、普通员工 |
| **ABAC（属性权限）** | 部门、岗位、区域、客户归属、文档密级、数据范围、时间窗口 |

### 7.2 四大模块权限控制重点

| 模块 | 权限控制重点 |
|------|-------------|
| **财务报表数据** | 部门、销售人员、客户、金额字段、汇总级别 |
| **产品知识库** | 公开资料、内部参数、技术文档、竞品资料 |
| **产品报价** | 标准价、底价、折扣策略、客户等级 |
| **博文数据库** | 草稿、已发布、内部策划、素材文件 |

### 7.3 敏感数据脱敏清单

- 手机号、身份证、银行账号；
- 合同金额（对外展示可脱敏为区间）；
- 产品底价、毛利率；
- 客户联系人信息；
- 内部成本、员工薪酬。

### 7.4 审计日志要求

记录以下维度：

- 谁问了什么问题（时间、用户、问题内容）；
- 调用了哪个数字员工和知识库；
- 访问了哪些数据表和文档；
- 返回了哪些来源引用；
- 是否触发越权拦截；
- 是否导出了文件或报表；
- 问答结果是否被用户标记为"不准确"。

### 7.5 安全合规机制

| 机制 | 说明 |
|------|------|
| **文档密级** | 公开 / 内部 / 机密 / 绝密 |
| **ABAC 前置检索** | 检索前过滤用户无权访问的文档和数据 |
| **动态脱敏** | 根据用户角色实时脱敏敏感字段 |
| **水印溯源** | 导出文件自动附加用户 ID、时间戳水印 |
| **越权拦截** | 无权限访问时直接拦截，记录审计日志 |
| **敏感问答拦截** | 涉及薪资、核心源码、未公开战略时提示"无权限" |

---

## 八、系统版本规划（优化版）

### 8.1 基础开源版本

**定位**：基于当前环境快速搭建可运行的知识库与数字员工原型。

**技术栈**：
- 后端：FastAPI
- 数据库：SQLite（后续可迁移到 PostgreSQL）
- 前端：Gradio / Streamlit
- 文档解析：Markdown / Python-markdown
- 检索：SQLite FTS5（后续可升级为 Qdrant / Chroma）
- 模型：本地 Qwen / DeepSeek / 云端 API

**已有基础**：
- `finance-wukong-mvp`：FastAPI + SQLite + 意图识别 + 权限过滤 + 报表输出
- `wukong_series_archive`：完整的悟空系列内容资产

### 8.2 整体完整版本

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

### 8.3 本地/云端双模模型路由（新增）

| 场景 | 模型策略 | 理由 |
|------|---------|------|
| 财务数据问答 | 优先本地模型 | 金额、预算、回款涉密 |
| 报价底价、合同风险 | 本地模型或私有云 | 底价、条款敏感 |
| 产品公开资料问答 | 本地/云端均可 | 公开信息 |
| 博文生成、营销内容 | 可调用云端模型 | 创意类任务，云端模型更强 |
| 通用办公问答 | 云端模型优先，降低成本 | 非敏感、高频 |

---

## 九、基础版推荐目录结构（优化版）

```text
hubai-basic/
├── app/
│   ├── main.py
│   ├── db.py
│   ├── security.py
│   ├── nlp.py
│   ├── router.py
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
│   │   ├── knowledge/
│   │   │   ├── chunker.py
│   │   │   ├── indexer.py
│   │   │   └── search.py
│   │   │
│   │   └── agent/
│   │       ├── router.py
│   │       ├── finance_agent.py
│   │       ├── business_agent.py
│   │       ├── sales_agent.py
│   │       └── tech_agent.py
│   │
│   ├── templates/
│   └── static/
│
├── data/
│   ├── db/
│   ├── docs/
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
│   ├── vector/
│   ├── graph/
│   ├── exports/
│   ├── backup/
│   ├── log/
│   ├── ocr/
│   └── temp/
│
├── scripts/
│   ├── init_db.py
│   ├── import_products.py
│   ├── import_blog_archive.py
│   ├── import_finance_reports.py
│   ├── build_knowledge_index.py
│   └── backup.py
│
├── tests/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── README.md
└── requirements.txt
```

---

## 十、自动化运维与知识运营机制（新增）

### 10.1 每日任务

- [ ] 服务健康检查（API、数据库、模型服务）
- [ ] 磁盘空间检查（data/ 目录、日志、备份）
- [ ] 异常日志检查（错误率、超时、越权拦截）
- [ ] 新增文件扫描（imports/ 目录自动识别待处理文件）

### 10.2 每周任务

- [ ] 知识索引增量重建（新增/修改文档重新分块、索引）
- [ ] 无答案问题统计（汇总"我不知道"类提问，分析知识盲区）
- [ ] 高频问题分析（Top 20 高频问题，检查是否已有标准答案）
- [ ] 重复文档清理（知识库去重、过期草稿清理）

### 10.3 每月任务

- [ ] 权限复核（检查离职人员权限、角色变更）
- [ ] 备份恢复演练（验证 backup/ 目录可恢复）
- [ ] 问答质量评测（运行评测集，统计命中率、准确率）
- [ ] 业务模块数据质量检查（空值、异常值、口径一致性）

### 10.4 季度任务

- [ ] 知识库结构优化（目录调整、分类优化、标签体系迭代）
- [ ] 数字员工 Prompt 评审（幻觉率、准确性、话术质量）
- [ ] RAG 参数优化（chunk 大小、重叠窗口、检索 Top-K、Rerank 阈值）
- [ ] 业务系统接口复盘（ERP/CRM/进销存对接进展评估）

---

## 十一、量化验收标准（新增）

| 验收类型 | 验收指标 | 目标值 |
|---------|---------|--------|
| **功能验收** | 四大模块 API 可用 | 100% |
| | 四类数字员工可完成基础问答 | 100% |
| **数据验收** | 财务、产品、报价、博文数据可导入、查询、检索 | 100% |
| **检索验收** | 高频业务问题命中率 | ≥ 80% |
| | 核心高频问题准确率（运营优化后） | ≥ 90% |
| **权限验收** | 越权访问拦截率 | 100% |
| **溯源验收** | 知识问答来源可追溯率 | ≥ 95% |
| **性能验收** | 基础版单用户问答响应 | 3-8 秒 |
| | 结构化数据查询响应 | ≤ 2 秒 |
| **运维验收** | 备份脚本可运行 | 100% |
| | 日志记录完整 | 100% |
| | 索引重建脚本可运行 | 100% |

---

## 十二、实施建议（优化版）

| 阶段 | 任务 | 预估周期 | 交付物 |
|------|------|---------|--------|
| **阶段一** | 修复当前记忆/语义索引，建立知识库知识地图，完善审计日志 | 1-2 周 | 知识地图、审计模块原型 |
| **阶段二** | 将当前 `sales_monthly` 扩展为完整财务数据模型，完成财务助理问数优化 | 2-3 周 | 财务数据模块、报表 API |
| **阶段三** | 建设产品知识库和产品报价模块原型，完成数据导入和基础检索 | 3-4 周 | 产品/报价模块、检索 API |
| **阶段四** | 将悟空系列博文结构化入库，完成内容检索和问答 | 2-3 周 | 博文数据库、内容问答 |
| **阶段五** | 打通四类数字员工统一路由，完成权限体系和安全合规建设 | 4-6 周 | 数字员工平台、权限/审计体系 |
| **阶段六** | 接入真实业务系统（ERP、CRM、进销存），升级增强型 RAG | 2-3 个月 | 企业级完整平台 |

> **说明**：上述周期为建议估算，实际进度受团队规模、数据质量、业务复杂度影响。建议以 MVP 快速验证为核心，逐步迭代。

---

## 十三、附录

### 13.1 术语表

| 术语 | 说明 |
|------|------|
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| GraphRAG | 基于知识图谱的 RAG |
| Self-RAG | 答案自我评估与补充检索 |
| HyDE | Hypothetical Document Embedding，假设文档嵌入 |
| RBAC | Role-Based Access Control，基于角色的访问控制 |
| ABAC | Attribute-Based Access Control，基于属性的访问控制 |
| FTS5 | SQLite Full-Text Search version 5 |
| Chunk | 知识切片，文档分块后的基本检索单元 |
| Rerank | 重排序，对初检索结果进行二次精排 |

### 13.2 参考文档

- 《企业智能知识库系统设计与实施方案 V2.2》（2025.01.15）
- `finance-wukong-mvp` 项目文档
- `wukong_series_archive` 项目文档

---

**编制人**：AI+比特虾 🦐
**版本**：V2（优化版）
**日期**：2026-06-23
