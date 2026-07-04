# HubAI 企业知识库与数字员工平台设计与部署建设方案（V3）

> **版本**：V3.1（报价工作流 + 钉钉AI表格双入口整合版）
> **编制**：AI+比特虾
> **日期**：2026-06-25
> **目标读者**：企业技术负责人、业务部门负责人、AI 实施团队
> **变更说明**：V3.0 → V3.1，新增第六章"需求表三 + 钉钉AI表格双入口报价体系"，包含对话驱动和表格驱动两种报价方式、双向同步机制、需求表三字段标准化

---

## 一、方案概述

### 1.1 方案名称
**HubAI 企业级一体化知识与业务智能底座**

### 1.2 核心定位
面向企业多部门场景，构建以 **一体化知识与业务智能底座 + 可插拔数字员工生态 + 增强型 RAG + 统一报价工作流 + 安全合规体系** 为核心的企业级 AI 应用平台，统一承载知识库、业务数据、数字员工、报价流程、权限审计、模型路由与工作流编排能力，支撑财务、商务、销售、技术四类部门助理的智能化运营。

### 1.3 建设目标

- **知识统一沉淀**：产品、方案、合同、报价、财务、技术等企业知识资产统一入库、统一检索、统一治理；
- **数据智能问答**：通过自然语言查询业务数据（销售、回款、预算、库存、订单等），回答附带数据来源；
- **报价流程闭环**：客户需求表三 → 规则校验 → 缺口发现 → 分流派单 → 方案生成 → 报价审批 → 客户输出 → 知识库沉淀；
- **部门助理自动化**：财务助理、商务助理、销售助理、技术助理各司其职，共用底座、统一调度；
- **权限与审计隔离**：RBAC + ABAC 组合权限，不同角色访问不同知识与数据，操作全程可审计、可溯源；
- **安全合规保障**：文档密级、敏感数据脱敏、水印溯源、操作日志、导出审计、越权拦截；
- **可持续扩展**：基础版采用开源技术构建，可平滑升级到完整企业版，支持本地/云端双模模型路由。

---

## 二、总体架构设计（V3 整合版）

### 2.1 分层架构

```text
┌─────────────────────────────────────────────────────────────────────┐
│                           IM 层 (企业应用入口)                        │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────────┐  │
│  │ WebChat  │   钉钉   │   飞书   │   企微   │  OA / 其他系统   │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                         接入层 (三类入口统一)                        │
│  ┌────────────────────┬────────────────────┬─────────────────────┐ │
│  │  OpenClaw Gateway  │  其他 Agents 智能体  │   Web 管理后台      │ │
│  │  ├─ 通道插件        │  ├─ sessions_spawn   │  ├─ 报价工作台      │ │
│  │  ├─ bindings 路由   │  ├─ bindings 绑定     │  ├─ 需求表单        │ │
│  │  └─ Hook 入口       │  └─ 结果回流          │  └─ 审批看板        │ │
│  └────────────────────┴────────────────────┴─────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                      MCP 协议适配层（薄接入层）                       │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │  MCP Server：封装 HubAI 报价 API，暴露标准协议接口         │    │
│  │  ├─ create_requirement()       # 创建需求表三              │    │
│  │  ├─ generate_requirement_card() # 生成需求卡                │    │
│  │  ├─ route_requirement()        # 需求分流                  │    │
│  │  ├─ get_historical_cases()     # 获取历史案例              │    │
│  │  ├─ generate_quotation()       # 生成报价草稿              │    │
│  │  ├─ validate_quotation()       # 规则校验                  │    │
│  │  ├─ approve_quotation()        # 审批操作                  │    │
│  │  └─ generate_customer_output() # 生成客户版本              │    │
│  └───────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────┤
│        数字员工与业务应用层                                          │
│  ┌──────────┬──────────┬──────────┬──────────┐                     │
│  │ 财务助理  │ 商务助理  │ 销售助理  │ 技术助理  │                     │
│  │ ·智能问数 │ ·库存查询 │ ·产品问答 │ ·方案生成 │                     │
│  │ ·报表输出 │ ·订单跟踪 │ ·报价辅助 │ ·技术应答 │                     │
│  │ ·异常预警 │ ·合同检查 │ ·客户跟进 │ ·售前支持 │                     │
│  └──────────┴──────────┴──────────┴──────────┘                     │
├─────────────────────────────────────────────────────────────────────┤
│     HubAI 一体化知识与业务智能底座                                  │
│                                                                      │
│  · 内嵌 API 网关        · 智能路由与调度         · 报价工作流引擎    │
│  · RAG 检索引擎         · 问数引擎              · 规则校验引擎      │
│  · 工具调用框架         · 工作流编排            · 审批流引擎        │
│  · 权限控制（RBAC+ABAC） · 审计日志              · 缺口发现引擎      │
│  · Prompt 管理          · 模型路由（本地/云端）   · 分流派单引擎      │
│  · 敏感数据脱敏         · 水印溯源              · 历史参考引擎      │
└─────────────────────────────────────────────────────────────────────┤
│     企业知识库、业务数据库与知识图谱层                                │
│                                                                      │
│  共享知识库 │ 部门知识库 │ 结构化业务数据库      │ 报价历史库        │
│  产品库    │ 合同库    │ 报价库    │ 财务库    │ 需求表三库        │
│  技术方案库 │ 博文资产库 │ 知识图谱（GraphRAG）  │ 历史项目库        │
└─────────────────────────────────────────────────────────────────────┤
│       本地/云端双模模型与基础设施层                                  │
│                                                                      │
│  LLM 大模型（本地/云端）│ Embedding 模型        │ 报价规则引擎      │
│  向量数据库              │ 关系数据库            │ 库存/客户/价格库  │
│  对象存储                │ 日志与监控系统        │ 审批配置库        │
│  容器化部署（Docker/K8s）│ CI/CD 流水线         │ 渠道白名单配置    │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心架构原则

1. **入口统一**：所有 IM 渠道和接入方式最终落地同一套 `order_requirement` 需求表三与报价流程
2. **渠道无差别**：WebChat、钉钉、飞书、企微、OA 仅为交互入口，不承载业务规则
3. **接入方式无差别**：OpenClaw、其他 Agents、Web 后台三类接入方式共用同一套业务 API
4. **协议统一**：无论 OpenClaw 还是其他 Agents，都通过同一套 MCP 协议调用报价能力
5. **规则引擎外置**：报价政策、折扣、审批规则集中配置，不硬编码在渠道插件或接入层
6. **历史项目隔离**：历史项目仅用于相似性检索与参考，不直接参与定价计算
7. **会话隔离**：不同渠道、不同客户、不同 Agent 的会话按 OpenClaw session key 隔离

### 2.3 报价工作流在整体架构中的定位

报价工作流是 HubAI 底座中**独立的业务引擎模块**，与 RAG 检索引擎、问数引擎、工具调用框架处于同一层级，但专门负责：

- **需求接入**：统一处理来自所有 IM 渠道和接入方式的报价需求
- **规则校验**：完整性检查、缺口发现、追问生成
- **分流派单**：标准型/方案型/非标型/高风险四类需求自动分流
- **报价生成**：基于产品价格政策生成报价草稿
- **审批闭环**：按规则自动路由审批人，审批结果同步回所有渠道
- **知识沉淀**：报价完成后自动归档到知识库，作为历史参考

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
│   └── 报价参考/          ← 历史项目仅作参考，不作为报价规则
│
├── 05-技术知识库/
│   ├── 产品参数/
│   ├── 技术方案/
│   ├── 实施文档/
│   ├── 故障手册/
│   └── API文档/
│
├── 06-报价知识库/          ← 新增：报价工作流沉淀
│   ├── 需求表三库/
│   ├── 历史报价库/
│   ├── 解决方案库/
│   └── 过程档案/
│
├── 07-知识切片与索引/
│   ├── chunks/
│   ├── vectors/
│   ├── graph/
│   └── metadata/
│
└── 08-评测集/
    ├── 财务问答测试集.md
    ├── 商务问答测试集.md
    ├── 销售问答测试集.md
    ├── 技术问答测试集.md
    ├── 报价流程测试集.md      ← 新增
    ├── 权限边界测试集.md
    └── 幻觉检测测试集.md
```

---

## 五、五大业务模块设计（V3 整合版）

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

### 5.3 产品报价模块（V3 升级：整合报价工作流引擎）

#### 定位
支撑销售助理和商务助理进行 **客户需求接入、规则校验、缺口发现、需求分流、报价生成、折扣策略匹配、库存联动检查、合同前置风险检查、审批闭环、客户输出、知识沉淀**。

#### 核心原则
- **客户需求表三必经**：所有渠道（Web、钉钉、飞书、企微、Agent）必须先完成需求表三，再进入正式报价流程
- **历史项目仅作参考**：历史报价、历史合同、类似案例只用于相似性检索与风险提示，不作为报价规则
- **规则外置**：报价政策、折扣、审批规则集中配置，不硬编码在渠道插件或接入层
- **协议统一**：无论 OpenClaw 还是其他 Agents，都通过 MCP 协议调用报价能力

#### 数据表设计

**（1）客户需求表三：`order_requirement`**
```sql
CREATE TABLE order_requirement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_no TEXT UNIQUE NOT NULL,
    source_channel TEXT DEFAULT 'web',
    source_ref TEXT,
    attachment_links TEXT,
    entered_at TEXT DEFAULT CURRENT_TIMESTAMP,
    customer_name TEXT NOT NULL,
    customer_contact_name TEXT,
    raw_requirement TEXT NOT NULL,
    customer_expected_time TEXT,
    is_urgent INTEGER DEFAULT 0,
    has_historical_project INTEGER DEFAULT 0,
    historical_project_refs TEXT,
    sales_owner_user_id TEXT,
    output_proposal_required INTEGER DEFAULT 0,
    output_quotation_required INTEGER DEFAULT 1,
    human_validated INTEGER DEFAULT 0,
    validation_status TEXT DEFAULT 'pending',
    status TEXT DEFAULT 'draft',
    created_by TEXT,
    updated_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（2）需求明细表：`order_requirement_item`**
```sql
CREATE TABLE order_requirement_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_no TEXT NOT NULL,
    product_code TEXT,
    product_name TEXT,
    quantity INTEGER,
    unit TEXT,
    custom_spec TEXT,
    expected_delivery TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（3）需求卡表：`quotation_requirement_card`**
```sql
CREATE TABLE quotation_requirement_card (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_no TEXT UNIQUE NOT NULL,
    requirement_no TEXT NOT NULL,
    completeness_score INTEGER DEFAULT 0,
    gap_list TEXT,
    follow_up_questions TEXT,
    route_type TEXT DEFAULT 'unknown',
    route_reason TEXT,
    assigned_agent_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（4）报价策略表：`quotation_policy`**
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

**（5）产品报价表：`product_price`**
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

**（6）库存表：`inventory`**
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

**（7）报价单头表：`quotation_header`**
```sql
CREATE TABLE quotation_header (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_no TEXT UNIQUE NOT NULL,
    requirement_no TEXT,
    card_no TEXT,
    proposal_no TEXT,
    customer_code TEXT NOT NULL,
    quotation_date TEXT,
    valid_until TEXT,
    total_amount REAL DEFAULT 0,
    discount_amount REAL DEFAULT 0,
    final_amount REAL DEFAULT 0,
    historical_case_refs TEXT,
    version TEXT DEFAULT 'draft',
    status TEXT DEFAULT 'draft',
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（8）报价明细表：`quotation_line`**
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

#### 核心 API（V3 扩展：完整报价工作流）
```text
# 需求接入层
POST /api/order-requirements              # 创建客户需求表三
GET  /api/order-requirements/{req_no}     # 查询需求表三
PUT  /api/order-requirements/{req_no}     # 更新需求表三

# 规则校验与缺口发现
POST /api/quotations/requirement-card/generate  # 生成需求卡（完整性+缺口+追问）
GET  /api/quotations/requirement-card/{card_no} # 查询需求卡

# 需求分流
POST /api/quotations/route                # 需求分流（标准/方案/非标/高风险）
GET  /api/quotations/route/{req_no}       # 查询分流结果

# 历史案例参考
POST /api/quotations/historical-cases     # 检索历史案例（仅参考，不作为规则）

# 报价生成
POST /api/quotations/generate             # 生成报价草稿
GET  /api/quotations/{quotation_no}       # 查询报价单
POST /api/quotations/validate             # 规则校验（折扣下限、库存、账期）

# 审批流
POST /api/quotations/approve              # 审批操作（通过/驳回/批注）
GET  /api/quotations/pending-approvals    # 待审批列表

# 客户输出
POST /api/quotations/customer-output/generate  # 生成客户版本（Markdown/PDF）
GET  /api/quotations/customer-output/{quotation_no} # 下载客户版本

# 回写与沉淀
POST /api/quotations/feedback             # 结果回写（状态、审批意见）
POST /api/quotations/archive              # 归档到知识库

# 基础查询
GET  /api/quotations/check-stock          # 库存检查
GET  /api/quotations/policies             # 报价政策查询
```

#### MCP 协议适配方法
```text
MCP Server 暴露以下标准方法：
├─ create_requirement(params)       → POST /api/order-requirements
├─ generate_requirement_card(req_no) → POST /api/quotations/requirement-card/generate
├─ route_requirement(req_no)        → POST /api/quotations/route
├─ get_historical_cases(req_no)     → POST /api/quotations/historical-cases
├─ generate_quotation(req_no)       → POST /api/quotations/generate
├─ validate_quotation(quotation_no)  → POST /api/quotations/validate
├─ approve_quotation(quotation_no, action, comment) → POST /api/quotations/approve
└─ generate_customer_output(quotation_no, format)   → POST /api/quotations/customer-output/generate
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

### 5.5 报价知识库模块（V3 新增）

#### 定位
存储报价工作流沉淀的知识资产，包括需求表三、历史报价、解决方案、过程档案，供后续检索参考。

#### 数据表设计

**（1）需求表三知识切片：`quotation_requirement_chunk`**
```sql
CREATE TABLE quotation_requirement_chunk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_no TEXT NOT NULL,
    chunk_type TEXT,          -- 'summary', 'product', 'custom', 'risk'
    chunk_text TEXT NOT NULL,
    tags TEXT,
    embedding_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（2）报价历史切片：`quotation_history_chunk`**
```sql
CREATE TABLE quotation_history_chunk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_no TEXT NOT NULL,
    chunk_type TEXT,          -- 'header', 'line', 'approval', 'feedback'
    chunk_text TEXT NOT NULL,
    tags TEXT,
    embedding_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**（3）解决方案库：`solution_document`**
```sql
CREATE TABLE solution_document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    solution_no TEXT UNIQUE NOT NULL,
    requirement_no TEXT,
    title TEXT NOT NULL,
    content_markdown TEXT,
    industry TEXT,
    product_combo TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### 核心 API
```text
POST /api/quotations/knowledge/search       # 检索报价相关知识
POST /api/quotations/knowledge/archive      # 归档报价记录到知识库
GET  /api/quotations/knowledge/solutions    # 查询解决方案库
POST /api/quotations/knowledge/similar      # 查找相似历史报价
```

---



---

## 六、需求表三 + 钉钉AI表格双入口报价体系（新增）

### 6.1 整体架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                              钉钉端                                  │
│  ┌─────────────────┐                      ┌─────────────────┐   │
│  │   方式一：对话    │                      │   方式二：表格    │   │
│  │   @机器人报价     │◄────────────────────►│   直接填写提交   │   │
│  └─────────────────┘                      └─────────────────┘   │
└──────────────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        OpenClaw 接入层                               │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ 1. 报价意图识别（触发词：报价/做报价/帮我报价）               │  │
│  │ 2. 信息完整性校验（7个必填字段）                               │  │
│  │ 3. 智能追问引导（缺什么问什么，不重复）                        │  │
│  │ 4. 钉钉AI表格数据监听回调                                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        HubAI 业务层                                  │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ 1. 需求表三录入数据库（order_requirement）                     │  │
│  │ 2. 创建钉钉AI表格记录（双向同步）                               │  │
│  │ 3. 需求规格匹配产品库（无影产品29种）                          │  │
│  │ 4. 报价评估与生成（按数量×单价×周期×折扣）                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 方式一：对话驱动报价流程（@机器人）

#### 完整工作流

```
用户 @AI+比特虾 说"帮我做个报价"
        │
        ▼
    机器人应答："好的，我来帮您收集报价信息。请告诉我：
        1. 客户全称是什么？
        2. 联系人是谁，电话多少？
        3. 客户使用场景是什么（办公/研发/教育等）？
        4. 需要什么规格的产品？
        5. 需要多少数量？
        6. 报月价还是年价？"
        │
        ▼
┌─────────────────────────────────┐
│ 用户分多次回答，或一次性说完      │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│ 信息完整性校验                   │
│ ✅ 7个必填字段是否齐全？        │
└─────────────────────────────────┘
        │
        ├──────────── 不齐全 ─────────────┐
        │                                  │
        ▼                                  ▼
  智能追问补全                      ✅ 信息完整
  "还需要告诉我：使用场景和数量"       │
                                       ▼
                          ┌─────────────────────────────┐
                          │ 1. 写入 order_requirement 表 │
                          │ 2. 生成需求编号 REQ-XXXXXX  │
                          │ 3. 创建钉钉AI表格记录       │
                          │ 4. 返回表格链接给用户        │
                          └─────────────────────────────┘
                                       │
                                       ▼
                          报价评估与自动生成
                                       │
                                       ▼
                          返回报价草稿（钉钉卡片/表格）
```

#### 对话采集字段映射

| 采集顺序 | 用户话术示例 | 对应数据库字段 |
|---|---|---|
| 1 | "客户是北京XX科技有限公司" | `customer_name_full` |
| 2 | "联系人是张三，电话138XXXX" | `contact_person` + `contact_phone` |
| 3 | "办公场景，100人用" | `usage_scenario` |
| 4 | "要4核8G的规格，配SSD" | `spec_requirement` |
| 5 | "需要100台" | `required_quantity` |
| 6 | "报年价" | `quotation_cycle` |

#### 追问策略

- **智能补全**：用户说的话包含多个字段时，一次性识别所有字段
- **缺啥问啥**：只问缺失的字段，不重复问已有信息
- **追问示例**：
  ```
  我已收集到：
  ✅ 客户：北京XX科技
  ✅ 联系人：张三 138XXXX
  ❌ 还缺少：使用场景、数量
  请告诉我客户的使用场景和需要的数量？
  ```

### 6.3 方式二：钉钉AI表格直接提交

#### 完整工作流

```
用户打开钉钉AI表格（报价需求表三）
        │
        ▼
    填写7个必填字段 + 其他可选字段
        │
        ▼
    提交表格 / 新增一行
        │
        ▼
    钉钉表格回调通知 OpenClaw
        │
        ▼
    写入 HubAI order_requirement 表
        │
        ▼
    触发报价评估（自动匹配产品+计算价格）
        │
        ▼
    报价结果回填到AI表格 / 推送消息给用户
```

#### 钉钉AI表格字段设计（16列）

| 列名 | 字段类型 | 必填 | 对应数据库字段 | 说明 |
|---|---|---|---|---|
| **需求编号** | 自动生成 | - | `requirement_no` | 系统自动生成 REQ-YYYYMMDD-XXX |
| **客户全称** | 文本 | ✅ 是 | `customer_name_full` | 客户公司完整名称 |
| **联系人** | 文本 | ✅ 是 | `contact_person` | 客户对接人姓名 |
| **联系电话** | 文本 | ✅ 是 | `contact_phone` | 手机号 |
| **使用场景** | 下拉 | ✅ 是 | `usage_scenario` | 选项：办公/研发/教育/设计/其他 |
| **需求规格** | 长文本 | ✅ 是 | `spec_requirement` | 产品规格详细描述 |
| **需求数量** | 数字 | ✅ 是 | `required_quantity` | 台数/点数 |
| **报价周期** | 下拉 | ✅ 是 | `quotation_cycle` | 选项：月/年 |
| **合同周期** | 数字 | - | `contract_duration_months` | 月数 |
| **售前支持** | 复选 | - | `need_pre_sales_support` | 是/否 |
| **配套方案** | 复选 | - | `need_solution_package` | 是/否 |
| **交付服务** | 复选 | - | `need_delivery_service` | 是/否 |
| **售后服务** | 复选 | - | `need_after_sales_service` | 是/否 |
| **状态** | 下拉 | - | `status` | 待评估/报价中/已报价/已确认/已关闭 |
| **提交时间** | 自动时间 | - | `created_at` | 自动生成 |
| **提交人** | 人员选择 | - | `created_by` | 自动获取 |
| **需求来源渠道** | 下拉 | - | `source_channel` | 对话/表格 |
| **关联报价单** | 关联 | - | `quotation_no` | 关联报价结果 |

#### 表格权限设置

| 角色 | 权限 |
|---|---|
| 销售团队 | 可新增、编辑自己的需求 |
| 销售主管 | 可查看所有需求、修改状态 |
| 财务/技术 | 可查看需求详情 |
| AI+比特虾机器人 | 可新增行、修改状态、回填报价 |

### 6.4 双向同步机制

#### 6.4.1 对话 → 表格（方式一）

对话收集完成后，自动在表格中新增一行：

```
触发条件：7个必填字段全部收集完成
执行操作：
  1. 生成需求编号 REQ-XXXXXX
  2. 调用钉钉AI表格API新增一行
  3. 回填所有字段值
  4. 在对话中返回表格链接：
     "✅ 需求已登记！编号：REQ-20260625-001
      查看表格：[链接]"
```

#### 6.4.2 表格 → 数据库（方式二）

```
触发条件：表格新增行 / 修改行
执行操作：
  1. 钉钉表格回调通知 OpenClaw
  2. 校验7个必填字段完整性
  3. 写入 order_requirement 表
  4. 如果字段完整，触发报价评估
  5. @提交人，告知已收到，正在评估报价
```

#### 6.4.3 状态同步矩阵

表格中的"状态"列与数据库双向同步：

| 表格状态 | 数据库 status | 说明 |
|---|---|---|
| 待评估 | `pending` | 刚提交，待校验完整 |
| 报价中 | `quoting` | 正在评估报价 |
| 已报价 | `quoted` | 报价已生成 |
| 已确认 | `confirmed` | 客户已确认 |
| 已关闭 | `closed` | 需求关闭 |

### 6.5 需求表三核心必填字段（7个，NOT NULL约束）

| 字段名 | 说明 | 约束 |
|---|---|---|
| `requirement_no` | 需求编号（系统自动生成） | UNIQUE NOT NULL |
| `customer_name_full` | 客户名称（全称） | NOT NULL |
| `contact_person` | 联系人 | NOT NULL |
| `contact_phone` | 联系电话 | NOT NULL |
| `usage_scenario` | 使用场景（办公、研发、教育等） | NOT NULL |
| `spec_requirement` | 需求规格描述 | NOT NULL |
| `required_quantity` | 需求数量 | NOT NULL |
| `quotation_cycle` | 报价周期（月/年） | NOT NULL |

### 6.6 实现步骤规划

| 阶段 | 周期 | 目标 |
|---|---|---|
| **阶段一：钉钉AI表格创建** | 1天 | 创建表格、配置字段/下拉/权限、配置回调webhook |
| **阶段二：对话采集能力** | 2天 | 意图识别、7字段提取、完整性校验、智能追问 |
| **阶段三：双向同步** | 1天 | 对话写入表格、表格回调写入数据库、状态同步 |
| **阶段四：报价评估引擎** | 2天 | 规格匹配产品库、自动计算价格、生成报价单 |

### 6.7 关键技术点

| 技术点 | 方案 |
|---|---|
| 钉钉表格API | 钉钉开放平台 - 多维表格接口 |
| 回调通知 | 钉钉表格webhook → OpenClaw `/hooks/quotation-table` |
| NLU字段提取 | 利用大模型从自然语言中提取7个字段 |
| 对话状态管理 | 每个用户/群独立会话，记录已收集字段 |
| 数据一致性 | 需求编号唯一，双向同步时防止重复写入 |

### 6.8 验收标准

| 验收项 | 标准 |
|---|---|
| ✅ 方式一流程 | @机器人说"报价" → 机器人引导7个字段 → 收集完成自动写入表格 |
| ✅ 方式二流程 | 在表格新增一行填写7个字段 → 自动写入数据库 → 自动触发报价 |
| ✅ 字段完整性校验 | 缺少必填字段时，方式一自动追问，方式二标记"待补充" |
| ✅ 双向同步 | 对话收集的在表格可见，表格提交的在数据库可查 |
| ✅ 状态同步 | 表格状态变更自动同步到数据库，数据库状态变更自动更新表格 |


## 七、四类数字员工设计（V3 整合版）

### 6.1 统一调度与接入规范

所有数字员工共用底层底座，禁止各自独立建设知识库：

- **统一知识库**：共享知识库 + 部门知识库 + 业务数据库 + 报价知识库；
- **统一权限体系**：RBAC + ABAC 组合，权限上下文随请求传递；
- **统一审计日志**：所有问答、数据查询、报价操作、文件导出全程记录；
- **统一工具调用框架**：每个数字员工只负责意图识别、任务拆解、工具选择、结果组织；
- **统一输入输出标准**：标准 JSON 输入、Markdown 输出、来源引用格式统一；
- **统一报价入口**：所有数字员工通过 MCP 协议调用报价能力，不直接访问报价数据库。

#### 智能路由机制

| 问题类型 | 路由目标 | 典型特征 |
|---------|---------|---------|
| 销售额、回款、预算、费用、利润 | 财务助理 | 涉及金额、时间、部门、人员 |
| 库存、订单、合同、采购、供应商 | 商务助理 | 涉及物料、数量、流程、文档 |
| 产品推荐、报价、客户跟进、话术 | 销售助理 | 涉及客户、需求、方案、价格 |
| 技术参数、方案生成、实施、故障 | 技术助理 | 涉及产品、架构、配置、排错 |
| 报价流程、需求表三、审批状态 | 报价工作流引擎 | 涉及报价单、审批、客户输出 |
| 跨域复杂问题 | 主调度 Agent 分解协同 | 多模块关联 |

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

### 6.3 商务助理

| 维度 | 内容 |
|------|------|
| **定位** | 订单、库存、合同、报价的流程处理员 |
| **核心能力** | 库存查询、销售订单查询、采购订单查询、合同模板匹配、合同差异比对、风险条款提示、**报价单生成（通过 MCP 调用报价引擎）**、发货条件检查 |
| **数据来源** | 库存表、订单表、采购表、合同模板库、报价政策库、供应商档案、客户档案、**需求表三库、历史报价库** |
| **典型问题** | "这个型号还有多少库存？" "客户A的订单到哪一步了？" "帮我检查这份合同有没有风险条款" "**给这个客户生成一份报价单**" |
| **输出形式** | 库存查询结果、订单状态表、合同风险摘要、**报价草稿（通过 MCP 获取）**、发货建议、商务待办清单 |
| **权限要求** | 看本人负责订单/合同/报价，部门经理看本部门，商务主管看全局 |
| **模型策略** | 本地模型优先，合同风险分析不外流 |

### 6.4 销售助理

| 维度 | 内容 |
|------|------|
| **定位** | 客户响应、商机推进和报价辅助工具 |
| **核心能力** | 产品资料查询、客户问题应答、销售话术生成、成功案例匹配、**初步报价建议（通过 MCP 调用报价引擎）**、商机推进建议、客户拜访纪要生成 |
| **数据来源** | 产品知识库、报价政策库、客户档案、销售案例库、竞品资料库、商机记录、CRM数据、**需求表三库、历史报价库** |
| **典型问题** | "客户问这款产品和竞品有什么区别，怎么回答？" "帮我生成一份客户拜访纪要" "根据客户需求推荐合适的产品组合" "**这个客户之前报过价吗？**" |
| **输出形式** | 客户答复话术、产品推荐表、**初步报价建议（通过 MCP 获取，标注仅供参考）**、客户跟进计划、销售机会分析、成功案例匹配结果 |
| **权限要求** | 看本人客户和商机/报价，经理看团队，销售总监看全局 |
| **模型策略** | 本地/云端均可，报价底价分析走本地 |

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

## 七、报价工作流引擎设计（V3 新增章节）

### 7.1 报价工作流核心流程

```text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   需求接入    │ →  │   规则校验    │ →  │   缺口发现    │ →  │   人工确认    │
│  (所有渠道)   │    │ (完整性评分)  │    │ (追问清单)   │    │ (负责人指定)  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                    ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   知识沉淀    │ ←  │   客户输出    │ ←  │   审批闭环    │ ←  │   报价生成    │
│ (归档知识库)  │    │ (Markdown/PDF)│    │ (通过/驳回)  │    │ (规则校验)   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                    ↑
                                                           ┌──────────────┐
                                                           │   历史参考    │
                                                           │ (仅参考不决策)│
                                                           └──────────────┘
```

### 7.2 需求分流规则

| 需求类型 | 判定条件 | 负责 Agent | 审批要求 | 预计时间 |
|---|---|---|---|---|
| **标准型** | 产品在库、价格政策匹配、库存充足、账期合规 | 商务助理（自动） | 无需人工审批 | 5 分钟 |
| **方案型** | 多产品组合、需技术方案说明 | 商务 + 技术助理 | 技术方案确认 | 1-2 天 |
| **非标型** | 含定制需求、服务交付内容 | 商务 + 技术 + 财务 | 三方评审 | 3-5 天 |
| **高风险** | 账期超长、毛利过低、新客户大额 | 商务总监 + 财务 | 负责人/老板审批 | 待定 |

### 7.3 历史项目参考规则

- **检索范围**：历史报价单、历史合同、已交付项目知识库
- **匹配维度**：产品相同(40%) + 数量相近(20%) + 客户级别(15%) + 交付方式(10%) + 时间(10%) + 行业(5%)
- **输出内容**：Top 3 相似项目 + 风险提示
- **关键约束**：页面和输出文案必须标注 **"仅作参考，不作为报价规则"**
- **技术实现**：IMA 知识库检索 + 关键词匹配（暂不引入向量计算）

### 7.4 报价规则引擎

**价格来源优先级**：
1. `product_price` 最新 active 价格
2. `quotation_policy` 最优折扣（客户级别 × 数量 × 品类）
3. `inventory` 库存校验
4. 历史案例只写入 `historical_case_refs`，不参与定价

**约束检查**：
- 折扣下限锁定（低于下限自动触发审批）
- 库存预留校验
- 账期与付款方式合规校验

---

## 八、权限、安全与审计体系设计（V3 升级）

### 8.1 权限模型：RBAC + ABAC 组合

| 维度 | 说明 |
|------|------|
| **RBAC（角色权限）** | 管理员、财务、销售、商务、技术人员、部门经理、普通员工、**审批人** |
| **ABAC（属性权限）** | 部门、岗位、区域、客户归属、文档密级、数据范围、时间窗口、**报价金额区间** |

### 8.2 五大模块权限控制重点

| 模块 | 权限控制重点 |
|------|-------------|
| **财务报表数据** | 部门、销售人员、客户、金额字段、汇总级别 |
| **产品知识库** | 公开资料、内部参数、技术文档、竞品资料 |
| **产品报价** | 标准价、底价、折扣策略、客户等级、**需求表三归属、审批权限** |
| **报价工作流** | **渠道白名单、需求表三编辑权限、报价审批权限、客户输出生成权限** |
| **博文数据库** | 草稿、已发布、内部策划、素材文件 |

### 8.3 敏感数据脱敏清单

- 手机号、身份证、银行账号；
- 合同金额（对外展示可脱敏为区间）；
- 产品底价、毛利率；
- 客户联系人信息；
- 内部成本、员工薪酬；
- **历史项目折扣信息（对外展示仅显示参考区间）**。

### 8.4 审计日志要求

记录以下维度：

- 谁问了什么问题（时间、用户、问题内容）；
- 调用了哪个数字员工和知识库；
- 访问了哪些数据表和文档；
- **创建了哪些需求表三、生成了哪些报价单、走了哪些审批流程**；
- 返回了哪些来源引用；
- 是否触发越权拦截；
- 是否导出了文件或报表；
- 问答结果是否被用户标记为"不准确"；
- **报价审批意见和变更记录**。

### 8.5 安全合规机制

- **文档密级**：公开 / 内部 / 机密 / 绝密四级，自动拦截越权访问；
- **水印溯源**：所有导出文件附带用户 ID、时间戳隐形水印；
- **导出审计**：记录谁导出了什么、导出了多少、用途声明；
- **越权拦截**：ABAC 规则实时校验，越权请求直接拦截并记录；
- **报价安全**：底价、折扣策略、审批记录属于机密级，仅审批人和管理员可见；
- **渠道安全**：`allowFrom` 白名单限制可发起报价的用户，防止外部越权。

---

## 九、部署架构（V3 整合版）

### 9.1 单服务器部署架构（MVP）

```text
                    公网 HTTPS (Nginx)
                           ↓
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
OpenClaw Gateway       Web 管理后台           Hook 服务
(端口 18789)          (端口 80/443)         /hooks/wake
├─ 通道插件            ├─ 报价工作台         /hooks/agent
│  ├─ dingtalk         ├─ 需求表单           /hooks/quotation
│  ├─ feishu           ├─ 审批看板           └─ OA 回调
│  ├─ wecom-webhook    ├─ 统计报表
│  └─ webchat          └─ 系统配置
├─ Session 存储        接入层：Web
│  └─ 本地 SQLite
└─ 工作区文件           接入层：OpenClaw
                           ↓
            HubAI Quotation Service (端口 8000)
    ┌────────────────────┼────────────────────┐
    │                    │                    │
  业务 API           业务数据库            文件存储
  ├─ /api/order-     └─ hubai_quotation.db  └─ 原始数据/报价库存
     requirements    ├─ product
  ├─ /api/quotations   ├─ price
  └─ /api/knowledge    ├─ inventory
                       └─ customer
                           ↓
                    IMA Knowledge Base API
                    └─ 云端知识库读写（仅用于方案文章存储）

* 其他 Agents 智能体通过 MCP 协议调用 HubAI 报价系统 API
```

### 9.2 部署清单

| 组件 | 部署方式 | 资源要求 | 备注 |
|---|---|---|---|
| OpenClaw Gateway | 二进制 / systemd | 2C4G | 开机自启、日志轮转 |
| HubAI 报价服务 | Docker Compose | 2C4G | 容器化部署，含 MCP Server |
| Nginx 反向代理 | 宿主机安装 | 1C1G | HTTPS + IP 白名单 |
| SQLite 数据库 | 本地文件 | - | 定期备份到异地 |
| IMA 知识库 | 调用云端 API | - | 仅用于方案文章存储 |

### 9.3 网络与安全

| 层面 | 措施 |
|---|---|
| **通道回调** | HTTPS + IP 白名单（钉钉/飞书/企微服务器网段） |
| **Hook 接口** | `Authorization: Bearer <token>` 鉴权，query-string token 拒绝 |
| **文件权限** | 工作区与数据库文件 `0600` 权限 |
| **备份策略** | 每日自动备份 SQLite + 工作区文件到异地 |
| **渠道白名单** | `allowFrom` 限制可发起报价的用户范围 |
| **会话隔离** | Session key 按 `agent:<agentId>:<channel>:<peer>` 隔离 |
| **MCP 安全** | MCP Server 仅暴露必要方法，敏感操作需审批权限校验 |

---

## 十、实施里程碑与排期（V3 整合版）

### 10.1 总体排期（6 周）

| 阶段 | 周期 | 目标 | 交付物 |
|---|---|---|---|
| **M1：基础设施搭建** | Week 1 | OpenClaw 生产部署 + 三通道打通 + HubAI 集成 | 部署文档、通道连通性报告、API 联调报告 |
| **M2：底座核心建设** | Week 2 | 知识库体系、四大基础模块、RAG 检索引擎 | MVP 底座版本、测试用例报告 |
| **M3：报价工作流 MVP** | Week 3 | WebChat 端走完「需求表三 → 规则校验 → 报价生成 → 归档」全流程 | 报价 MVP 版本、流程测试报告 |
| **M4：IM 渠道接入** | Week 4 | 钉钉、飞书、企微（Webhook）接入，支持 IM 端发起报价 | 渠道接入文档、端到端测试报告 |
| **M5：多 Agent 协同 + MCP 适配** | Week 5 | 分流规则、子 Agent 协同、MCP Server 封装、知识库沉淀 | 协同测试报告、MCP 文档 |
| **M6：集成测试 + 上线** | Week 6 | 全链路集成测试、灰度发布、正式上线 | 上线报告、运维手册、验收用例 |

### 10.2 关键里程碑验收标准

| 里程碑 | 验收标准 |
|---|---|
| **M1 完成** | OpenClaw Gateway 正常运行、钉钉/飞书/企微至少一个通道可收发消息、HubAI API 可正常调用 |
| **M2 完成** | 产品知识库可检索、财务报表可查询、报价政策可配置、博文可导入检索 |
| **M3 完成** | WebChat 端可完成一条标准型报价全流程、需求表三落库正确、报价草稿金额计算正确 |
| **M4 完成** | 钉钉/飞书/企微至少两个渠道可完成完整报价流程、source_channel 记录正确 |
| **M5 完成** | 商务/技术/财务 Agent 可按分流规则自动介入、MCP Server 方法可用、子 Agent 结果可回流 |
| **M6 完成** | 全量渠道开放、监控告警配置完成、用户培训完成、运维手册交付 |

---

## 十一、附录

### 11.1 关键配置参考

```json5
// OpenClaw Gateway 配置片段
{
  channels: {
    dingtalk: {
      enabled: true,
      dmPolicy: "pairing",
      groupPolicy: "allowlist",
      groupAllowFrom: ["群ID1", "群ID2"],
      requireMention: true,
    },
    feishu: {
      enabled: true,
      dmPolicy: "pairing",
      groupPolicy: "allowlist",
      groupAllowFrom: ["oc_xxx"],
      requireMention: true,
    },
  },
  hooks: {
    enabled: true,
    token: "quotation-system-hook-token",
    path: "/hooks",
    allowedAgentIds: ["main", "commerce", "tech", "finance"],
  },
  agents: {
    list: [
      { id: "main", name: "主助理", workspace: "~/.openclaw/workspace" },
      { id: "commerce", name: "商务助理", workspace: "~/.openclaw/workspace-commerce" },
      { id: "tech", name: "技术助理", workspace: "~/.openclaw/workspace-tech" },
      { id: "finance", name: "财务助理", workspace: "~/.openclaw/workspace-finance" },
    ],
  },
  bindings: [
    { match: { channel: "dingtalk" }, agentId: "main" },
    { match: { channel: "feishu" }, agentId: "main" },
    { match: { channel: "webchat" }, agentId: "main" },
  ],
}
```

### 11.2 关键 API 清单

| API | 方法 | 说明 |
|---|---|---|
| `/api/order-requirements` | POST | 创建客户需求表三 |
| `/api/quotations/requirement-card/generate` | POST | 生成需求卡（完整性+缺口+追问） |
| `/api/quotations/route` | POST | 需求分流 |
| `/api/quotations/historical-cases` | POST | 历史案例参考（仅参考，不作为规则） |
| `/api/quotations/generate` | POST | 生成报价草稿 |
| `/api/quotations/validate` | POST | 规则校验 |
| `/api/quotations/approve` | POST | 审批操作 |
| `/api/quotations/customer-output/generate` | POST | 生成客户版本 |
| `/api/quotations/feedback` | POST | 结果回写 |
| `/api/finance/summary` | GET | 财务汇总 |
| `/api/products/search` | POST | 产品检索 |
| `/api/blogs/ask` | POST | 博文问答 |

### 11.3 相关文档索引

| 文档 | 说明 |
|---|---|
| `hubai_openclaw_quotation_system_plan_v4_202606251244.md` | OpenClaw 统一入口报价系统规划与部署方案 |
| `hubai_quotation_workflow_design_v3_202606250952.md` | HubAI 报价工作流设计方案 v3 |
| `hubai_quotation_execution_plan_v3_202606250952.md` | HubAI 报价工作流 v3 执行计划 |
| `hubai_knowledge_base_design_scheme_v2_202606231819.md` | HubAI 知识库设计方案 v2（本方案前置版本） |
| `order_requirement_table_schema_v2_202606241534.md` | 订单需求表字段设计 |
