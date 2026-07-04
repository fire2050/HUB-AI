# HubAI 企业知识库与报价系统统一方案

> 版本：v1.3（Unified）
> 时间：2026-06-29
> 定位：HubAI 知识库基础版 + 报价系统 v3 + OpenClaw 统一入口 + 多产品线架构 四方案合并统一
> 原则：数据底座统一、工作流统一、入口统一、产品架构统一、后续迭代基于此方案

---

## 一、项目概述

### 1.1 统一背景

HubAI 项目包含三个相互依赖的子系统：

| 子系统 | 原方案 | 职责 | 统一后定位 |
|--------|--------|------|-----------|
| **HubAI 知识库基础版** | v1.0 (2026-06-23) | 数据底座：财务/产品/报价/博文四大模块 | **统一数据层** |
| **HubAI 报价系统** | v3.0 (2026-06-25) | 商务报价工作流：10步闭环流程 | **核心业务流** |
| **OpenClaw 统一入口** | v4.1 (2026-06-25) | 多渠道接入：IM/Web/Agent 统一入口 | **统一接入层** |
| **多产品线架构** | v1.0 (2026-06-26) | 底座统一 + 产品独立 Skill 体系 | **统一产品层** |

### 1.2 统一原则

1. **数据底座统一**：所有业务模块共用一套数据库、一套知识切片、一套权限模型
2. **工作流统一**：报价流程基于知识库数据，知识库沉淀报价结果
3. **入口统一**：所有渠道（Web/钉钉/飞书/企微/Agent）共用同一套 API
4. **协议统一**：OpenClaw 与其他 Agents 通过同一套 MCP 协议调用能力
5. **产品架构统一**：底座能力包（hubai-base）统一支撑，每个产品线独立 Skill，配置驱动扩展
6. **历史项目隔离**：历史项目仅用于参考，不参与定价规则
7. **客户需求表三必经**：任何渠道的客户需求报价必须先完成需求表三
8. **认知与执行分离**：报价知识库（认知层）提供业务上下文，报价 Skill（执行层）负责确定性计算与流程驱动
9. **渐进式迭代**：后续所有方案基于本统一方案演进，不推翻重来

### 1.3 统一架构（认知与执行分离）

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        统一接入层 (OpenClaw Gateway)                │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────────┐  │
│  │ WebChat  │   钉钉   │   飞书   │   企微   │  其他 Agents     │  │
│  │ (内置)   │ (已部署) │ (待配置) │ (Webhook)│ (MCP协议)        │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────────────┘  │
│                           ↓ 用户对话/指令                           │
├─────────────────────────────────────────────────────────────────────┤
│                     大模型调度层（理解与决策）                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  • 意图识别：判断用户是否需要报价                            │   │
│  │  • 信息提取：从对话中提取客户公司、产品、数量、预算等        │   │
│  │  • 上下文管理：维护多轮对话状态，决定下一步追问或执行        │   │
│  │  • Skill 调度：确定调用 smart-quotation Skill，不自行计算  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           ↓ 确定性计算/执行                         │
├─────────────────────────────────────────────────────────────────────┤
│                     报价 Agent Skill（执行层）                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  smart-quotation Skill                                       │   │
│  │  ├─ SKILL.md：任务边界、输入参数、输出格式、异常处理        │   │
│  │  ├─ scripts/：                                              │   │
│  │  │   ├─ price_engine.py    # 价格计算引擎（100%确定性）    │   │
│  │  │   ├─ rule_validator.py  # 规则校验引擎                  │   │
│  │  │   ├─ route_engine.py    # 分流派单引擎                  │   │
│  │  │   └─ doc_generator.py   # 报价单文档生成                │   │
│  │  ├─ templates/：报价单模板（Markdown/PDF）                 │   │
│  │  ├─ config/：折扣系数表、权限边界、审批规则                │   │
│  │  └─ logs/：完整执行日志（满足审计要求）                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           ↓ MCP 协议调用                            │
├─────────────────────────────────────────────────────────────────────┤
│                      MCP 协议适配层（薄接入层）                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  create_requirement()       # 创建需求表三                  │   │
│  │  generate_requirement_card() # 生成需求卡                    │   │
│  │  route_requirement()        # 需求分流                      │   │
│  │  get_historical_cases()     # 获取历史案例（仅供参考）       │   │
│  │  generate_quotation()       # 生成报价草稿（调用Skill）     │   │
│  │  validate_quotation()       # 规则校验                      │   │
│  │  approve_quotation()        # 审批操作                      │   │
│  │  generate_customer_output() # 生成客户版本                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                    核心业务流 (HubAI Quotation v3)                  │
│  需求表三 → 需求卡(完整性+缺口+追问) → 分流派单 → 历史参考 →        │
│  输出确认 → 方案初稿 → 报价草稿 → 规则校验 → 客户版本 → 回写知识库   │
├─────────────────────────────────────────────────────────────────────┤
│                        统一数据层（认知层）                           │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────────┐  │
│  │ 财务模块 │ 产品模块 │ 报价模块 │ 博文模块 │ 知识检索(FTS5)   │  │
│  │ fact_fin │ product  │quotation│ blog_    │ knowledge_chunk  │  │
│  │ dim_dept │ product_ │quotation│ article  │ + FTS5 虚拟表    │  │
│  │ dim_emp  │ spec/doc │_policy  │ blog_    │                  │  │
│  │ dim_cust │ product_ │product_ │ outline  │                  │  │
│  │ fact_    │ faq      │ price   │ blog_    │                  │  │
│  │ budget   │          │inventory│ resource │                  │  │
│  │ fact_    │          │quotation│          │                  │  │
│  │ receivable│         │_header/ │          │                  │  │
│  │ report_  │          │_line    │          │                  │  │
│  │ snapshot │          │         │          │                  │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────────────┘  │
│                           ↓ 归档沉淀                                │
├─────────────────────────────────────────────────────────────────────┤
│                        IMA 知识库 (云端归档)                         │
│  报价需求库 │ 历史报价库 │ 解决方案库 │ 过程档案 │ 悟空系列文章    │
└─────────────────────────────────────────────────────────────────────┘

架构核心原则：
• 大模型负责"调度"报价（理解需求、提取信息、决定流程、调用Skill）
• Skill 负责"执行"报价（确定性计算、规则校验、文档生成、审批流转）
• 知识库负责"认知"（提供业务上下文、历史案例、产品文档、FAQ）
• 绝不让大模型直接进行成本核算与折扣计算
```

---

## 二、统一数据层（知识库基础版）

### 2.1 数据库模块总览

| 模块 | 表数量 | 核心表 | 用途 |
|------|--------|--------|------|
| **财务模块** | 8 | fact_finance_monthly, dim_department, dim_employee, dim_customer, fact_budget, fact_receivable, report_snapshot, audit_log | 财务问数、报表、预警 |
| **产品模块** | 5 | product, product_category, product_spec, product_document, product_faq | 产品查询、文档、FAQ |
| **报价模块** | 7 | quotation_policy, product_price, inventory, quotation_header, quotation_line, order_requirement_table, quotation_requirement_card | 报价生成、库存、审批 |
| **博文模块** | 3 | blog_article, blog_outline, blog_resource | 悟空系列归档、检索 |
| **知识检索** | 2 | knowledge_chunk, knowledge_chunk_fts(虚拟表) | 统一全文检索 |

### 2.2 新增统一表（跨模块）

```sql
-- 客户需求表三（所有入口必经）
CREATE TABLE IF NOT EXISTS order_requirement_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT UNIQUE NOT NULL,              -- E-20260626-XXXXXX
    source_channel TEXT DEFAULT 'web',          -- web / dingtalk / wecom / feishu / agent
    source_ref TEXT,                            -- 原始消息ID/会话ID
    customer_name TEXT,
    customer_company TEXT,
    customer_contact TEXT,
    customer_level TEXT DEFAULT 'standard',     -- standard / vip / strategic / new
    requirement_type TEXT,                      -- standard / solution / custom / risky
    product_codes TEXT,                         -- JSON 数组
    quantity TEXT,                              -- JSON 对象
    required_delivery_date TEXT,
    budget_range TEXT,
    delivery_mode TEXT DEFAULT 'standard',
    payment_terms TEXT DEFAULT 'prepay_30',
    warranty_required TEXT,
    training_required INTEGER DEFAULT 0,
    competitor_info TEXT,
    custom_requirements TEXT,
    risk_flags TEXT,                            -- JSON 数组
    has_historical_project INTEGER DEFAULT 0,
    historical_project_refs TEXT,               -- JSON 数组
    ai_extracted_summary TEXT,
    ai_confidence_score REAL DEFAULT 0.0,
    ai_suggested_products TEXT,
    sales_owner_user_id TEXT,
    status TEXT DEFAULT 'draft',
    submitted_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 需求卡（规则校验+缺口+追问+分流）
CREATE TABLE IF NOT EXISTS quotation_requirement_card (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_no TEXT UNIQUE NOT NULL,               -- QC-20260626-XXXXXX
    entry_id TEXT NOT NULL,
    completeness_score INTEGER DEFAULT 0,       -- 0-100
    missing_fields TEXT,                        -- JSON 数组
    gap_summary TEXT,                           -- JSON 对象
    gap_count INTEGER DEFAULT 0,
    clarification_list TEXT,                    -- JSON 数组
    suggested_route TEXT,                       -- standard / solution / custom / risky
    route_reason TEXT,
    output_types TEXT,                          -- JSON 数组: proposal / quotation
    status TEXT DEFAULT 'draft',
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 方案初稿（技术/商务方案）
CREATE TABLE IF NOT EXISTS quotation_proposal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_no TEXT UNIQUE NOT NULL,           -- QP-20260626-XXXXXX
    card_no TEXT NOT NULL,
    proposal_type TEXT,                         -- technical / commercial / combined
    overview TEXT,
    product_solution TEXT,
    architecture TEXT,
    delivery_plan TEXT,
    training_plan TEXT,
    risk_assessment TEXT,
    estimated_cost REAL,
    estimated_profit REAL,
    suggested_price REAL,
    suggested_discount REAL,
    status TEXT DEFAULT 'draft',
    approved_by TEXT,
    approved_at TEXT,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 客户版本输出（脱敏对外版）
CREATE TABLE IF NOT EXISTS quotation_customer_output (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    output_no TEXT UNIQUE NOT NULL,             -- CO-20260626-XXXXXX
    quotation_no TEXT,
    proposal_no TEXT,
    output_type TEXT,                           -- proposal / quotation / combined
    customer_markdown TEXT,
    valid_until TEXT,
    terms_and_conditions TEXT,
    contact_info TEXT,
    sent_at TEXT,
    opened_at TEXT,
    status TEXT DEFAULT 'draft',
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 报价审批记录
CREATE TABLE IF NOT EXISTS quotation_approval (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_no TEXT NOT NULL,
    approval_type TEXT,                         -- technical / commercial / financial / director / boss
    approver_user_id TEXT,
    approver_role TEXT,
    approval_status TEXT,                       -- pending / approved / rejected
    approval_comment TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 知识切片（通用）
CREATE TABLE IF NOT EXISTS knowledge_chunk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,        -- product_doc / blog_article / faq / historical_quotation / policy
    source_id TEXT NOT NULL,
    title TEXT,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER,
    tags TEXT,
    department_scope TEXT,
    permission_level TEXT DEFAULT 'internal',
    embedding_id TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- FTS5 全文检索虚拟表
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunk_fts USING fts5(
    chunk_text, title, source_type, source_id,
    content='knowledge_chunk', content_rowid='id'
);
```

### 2.3 技术选型（全开源）

| 层级 | 技术组件 | 说明 |
|------|---------|------|
| 后端框架 | FastAPI 0.115+ | 异步高性能，现有基础 |
| 数据库 | SQLite 3.39+ | 本地零配置，预留 PostgreSQL 迁移接口 |
| 全文检索 | SQLite FTS5 | 基础版关键词检索，预留 Chroma/Qdrant 向量库接口 |
| 文档解析 | Python-markdown | Markdown 转文本入库 |
| 前端演示 | Gradio 4.x | 多标签页快速搭建 |
| 容器化 | Docker + Docker Compose | 一键启动 |
| 测试 | pytest + httpx | 现有框架延续 |

---

## 三、核心业务流（报价系统 v3 统一版）

### 3.1 10步标准工作流

```
Step 1: 多入口需求接入 → 客户需求表三（所有入口必经）
    ↓
Step 2: 需求卡生成 → 完整性检查 + 缺口发现 + 追问清单
    ↓
Step 3: 分流派单 → 标准型 / 方案型 / 非标型 / 高风险
    ↓
Step 4: 历史案例参考 → 强制参考，不作为报价规则
    ↓
Step 5: 输出选择确认 → 方案 / 报价单 / 两者都要
    ↓
Step 6: 内部方案初稿（可选，仅当输出包含方案时）
    ↓
Step 7: 报价草稿生成
    ↓
Step 8: 规则校验 + 审批
    ↓
Step 9: 客户版本输出
    ↓
Step 10: 回写结果 → 知识库沉淀
```

### 3.2 分流规则

| 需求类型 | 判定条件 | 处理路径 | 审批要求 | 预计时间 |
|---------|---------|---------|---------|---------|
| **标准型** | 完整性≥80、产品在库、有价格、库存充足、无定制、无风险 | 快速报价 | 无需审批 | 5 分钟 |
| **方案型** | 产品选型不确定、多产品组合、需技术方案 | 技术确认 → 方案+报价 | 技术+商务确认 | 1-2 天 |
| **非标型** | 有定制需求、现场交付、需培训延保 | 三方评审 → 方案+报价 | 技术+商务+财务评审 | 3-5 天 |
| **高风险** | 账期超长、毛利过低、新客户大额、越权折扣 | 升级审批 → 方案+报价 | 销售总监/老板审批 | 待定 |

### 3.3 关键约束（统一版）

1. **客户需求表三必经**：任何渠道的客户需求报价必须先完成 `order_requirement_table`
2. **历史项目仅参考**：历史项目参与风险提示和参考说明，不参与定价规则计算
3. **价格来源优先级**：product_price → quotation_policy → 人工确认
4. **折扣下限锁定**：低于 policy 下限自动触发审批
5. **库存预留校验**：inventory.available < 需求数量时标记缺口
6. **规则引擎优先**：完整性检查、缺口检测、分流判断优先使用规则引擎，LLM 只做摘要/抽取/话术

---

## 四、统一接入层（OpenClaw 多渠道）

### 4.1 渠道接入矩阵

| 渠道 | 状态 | 接入方式 | 入口字段 |
|------|------|---------|---------|
| **WebChat** | ✅ 已可用 | OpenClaw 内置 | `source_channel=webchat` |
| **钉钉** | ✅ 已部署 | dingtalk-openclaw-bridge | `source_channel=dingtalk` |
| **飞书** | ⚠️ 待配置 | OpenClaw 内置 Feishu 通道 | `source_channel=feishu` |
| **企微** | ⚠️ 待接入 | Webhook → /hooks/agent | `source_channel=wecom` |
| **其他 Agents** | ⚠️ 待接入 | MCP 协议适配层 | `source_channel=agent` |
| **Web 管理后台** | ⚠️ 待开发 | 前端页面 + 统一 API | `source_channel=web` |

### 4.2 OpenClaw 配置（统一版）

```json5
{
  channels: {
    "dingtalk-connector": {
      enabled: true,
      dmPolicy: "pairing",
      groupPolicy: "allowlist",
      requireMention: true,
      accounts: {
        __default__: {
          name: "AI+比特虾",
          clientId: "dingpubghlrsejvqgffp",
          groupAllowFrom: ["报价群ID1", "报价群ID2"]
        }
      }
    },
    feishu: {
      enabled: true,
      dmPolicy: "pairing",
      groupPolicy: "allowlist",
      requireMention: true
    }
  },
  hooks: {
    enabled: true,
    token: "hubai-webhook-secret-2026",
    path: "/hooks",
    allowedAgentIds: ["main", "commerce", "tech", "finance"],
    allowRequestSessionKey: false
  },
  agents: {
    list: [
      { id: "main", name: "主助理", workspace: "~/.openclaw/workspace" },
      { id: "commerce", name: "商务助理", workspace: "~/.openclaw/workspace-commerce" },
      { id: "tech", name: "技术助理", workspace: "~/.openclaw/workspace-tech" },
      { id: "finance", name: "财务助理", workspace: "~/.openclaw/workspace-finance" }
    ]
  },
  bindings: [
    { match: { channel: "dingtalk" }, agentId: "main" },
    { match: { channel: "feishu" }, agentId: "main" },
    { match: { channel: "webchat" }, agentId: "main" }
  ]
}
```

### 4.3 Webhook 端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/hooks/wake` | POST | 唤醒主会话，推送系统事件 |
| `/hooks/agent` | POST | 运行隔离 Agent 任务 |
| `/hooks/quotation` | POST | 报价系统专用 Hook |

### 4.4 多 Agent 协同

| Agent | 职责 | 触发条件 | 工作空间 |
|-------|------|---------|---------|
| **main** | 主助理，统一入口 | 所有渠道默认路由 | `workspace` |
| **commerce** | 商务助理 | 报价需求、客户沟通 | `workspace-commerce` |
| **tech** | 技术助理 | 方案型/非标型需求技术评估 | `workspace-tech` |
| **finance** | 财务助理 | 高风险审批、财务校验 | `workspace-finance` |

---

## 五、统一 API 设计

### 5.1 核心 API 清单

| API | 方法 | 说明 |
|-----|------|------|
| `/api/order-requirements` | POST | 创建客户需求表三 |
| `/api/order-requirements/{id}/ai-extract` | POST | AI 自动提取客户原文 |
| `/api/quotations/requirement-card/generate` | POST | 生成需求卡 |
| `/api/quotations/requirement-card/{id}/clarify` | POST | 回填追问答案 |
| `/api/quotations/route` | POST | 需求分流 |
| `/api/quotations/historical-cases` | POST | 历史案例参考（仅供参考） |
| `/api/quotations/output-type/confirm` | POST | 输出类型确认 |
| `/api/quotations/proposal/generate` | POST | 生成方案初稿 |
| `/api/quotations/generate` | POST | 生成报价草稿 |
| `/api/quotations/validate` | POST | 规则校验 |
| `/api/quotations/approve` | POST | 审批操作 |
| `/api/quotations/customer-output/generate` | POST | 生成客户版本 |
| `/api/quotations/feedback` | POST | 结果回写 |
| `/api/knowledge/search` | POST | 统一知识检索 |
| `/api/knowledge/ask` | POST | 知识问答 |

### 5.2 数字员工 API

| API | 方法 | 说明 |
|-----|------|------|
| `/api/assistants/finance/query` | POST | 财务助理查询 |
| `/api/assistants/product/query` | POST | 产品助理查询 |
| `/api/assistants/quotation/query` | POST | 报价助理查询 |
| `/api/assistants/blog/query` | POST | 博文助理查询 |

---

## 六、前端演示设计

### 6.1 Gradio 多标签页界面

```
HubAI 统一工作台 /
├── 财务助理
│   └── 聊天窗口 + 快捷问题 + 报表下载
├── 产品助理
│   └── 聊天窗口 + 产品搜索 + 文档查看
├── 报价助理
│   └── 聊天窗口 + 报价工作流 + 审批看板
├── 博文助理
│   └── 聊天窗口 + 文章检索 + 内容预览
└── 管理后台
    ├── 数据导入
    ├── 知识切片
    ├── 用户权限
    └── 报价工作台
```

### 6.2 报价工作流页面

```
┌─────────────────────────────────────────────────────────────┐
│ 报价工作流                                                   │
├─────────────────────────────────────────────────────────────┤
│ ① 订单 AI 表格                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 客户信息 | 产品需求 | 交付条款 | 特殊要求            │   │
│  │ [粘贴客户原文] → [AI 自动提取]                      │   │
│  └─────────────────────────────────────────────────────┘   │
│ ② 需求卡：完整性 85/100 ✅                                  │
│ ③ 分流结果：标准型 → 快速报价                               │
│ ④ 历史案例（仅供参考）                                       │
│ ⑤ 输出确认：☑️ 方案 ☑️ 报价单                               │
│ ⑥ 报价草稿：💰 应付 288.00                                  │
│ ⑦ [提交审批] / [直接输出客户版]                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 七、实施里程碑（统一排期）

### 7.1 总体排期（6 周）

| 阶段 | 周期 | 目标 | 交付物 |
|------|------|------|--------|
| **M1：数据底座** | Week 1 | 20+ 张表 DDL + 初始化脚本 + 数据导入 | 可运行的知识库基础版 |
| **M2：核心 API** | Week 2 | 后端模块化拆分 + 15+ API 实现 | FastAPI 服务 + 测试用例 |
| **M3：报价 MVP** | Week 3 | 10步工作流：需求表三 → 客户版本 | 报价全流程可跑通 |
| **M4：前端演示** | Week 4 | Gradio 多标签页 + 报价工作流页面 | 可对外演示的界面 |
| **M5：渠道接入** | Week 5 | 钉钉深化 + 飞书配置 + 企微 Webhook | 3 渠道可发起报价 |
| **M6：多 Agent** | Week 6 | 商务/技术/财务 Agent 协同 + 知识沉淀 | 完整闭环 + 上线 |

### 7.2 详细任务分解

#### Week 1：数据底座
- [ ] Day 1：财务模块表（8张）+ 维度数据初始化
- [ ] Day 2：产品模块表（5张）+ 示例产品数据
- [ ] Day 3：报价模块表（7张）+ 报价策略初始化
- [ ] Day 4：博文模块表（3张）+ 悟空系列导入
- [ ] Day 5：知识切片表（2张）+ FTS5 索引构建 + 冒烟测试

#### Week 2：核心 API
- [ ] Day 1：后端模块化拆分（5个模块）
- [ ] Day 2：数字员工路由 + 意图识别扩展
- [ ] Day 3：需求表三 API + 需求卡 API
- [ ] Day 4：报价生成 API + 规则校验 API
- [ ] Day 5：知识检索 API + 单元测试

#### Week 3：报价 MVP
- [ ] Day 1：Step 1-2：需求接入 + 需求卡生成
- [ ] Day 2：Step 3-4：分流派单 + 历史参考
- [ ] Day 3：Step 5-6：输出确认 + 方案初稿
- [ ] Day 4：Step 7-8：报价草稿 + 审批流
- [ ] Day 5：Step 9-10：客户版本 + 回写知识库

#### Week 4：前端演示
- [ ] Day 1-2：Gradio 框架 + 4 个助理标签页
- [ ] Day 3-4：报价工作流页面（10步可视化）
- [ ] Day 5：管理后台页面 + 端到端联调

#### Week 5：渠道接入
- [ ] Day 1-2：钉钉深化（审批回调、附件上传）
- [ ] Day 3：飞书通道配置测试
- [ ] Day 4：企微 Webhook 接入
- [ ] Day 5：三渠道联调测试

#### Week 6：多 Agent 协同
- [ ] Day 1-2：Agent 工作空间创建 + bindings 配置
- [ ] Day 3：sessions_spawn 子任务编排
- [ ] Day 4：知识库沉淀自动化 + IMA 归档
- [ ] Day 5：灰度发布 + 运维手册 + 正式上线

---

## 八、风险控制

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| SQLite 并发不足 | 多用户查询卡顿 | 基础版限定单用户演示；M6 后评估 PostgreSQL |
| FTS5 中文分词差 | 检索不准确 | 先用关键词匹配；M6 后接入 Jieba/Chroma |
| 渠道 API 变更 | 消息中断 | 保留 Webhook 降级方案；定期监控 |
| 规则引擎误判 | 报价错误 | 报价草稿强制人工确认；规则灰度发布 |
| 多 Agent 并发混乱 | 会话错乱 | Session key 按渠道+客户+需求ID隔离 |

---

## 九、文档索引

| 文档 | 说明 | 状态 |
|------|------|------|
| `hubai_unified_solution_v1_202606261030.md` | **本统一方案（主文档）** | ✅ 当前 |
| `hubai_knowledge_base_implementation_plan.md` | 知识库基础版详细实施方案 | ⛓️ 已合并 |
| `hubai_knowledge_base_design_scheme_v3.1_202606251723.md` | 知识库设计方案 v3.1 | ⛓️ 已合并 |
| `hubai_quotation_workflow_design_v3_202606250952.md` | 报价工作流 v3 设计 | ⛓️ 已合并 |
| `hubai_quotation_execution_plan_v3_202606250952.md` | 报价工作流 v3 执行计划 | ⛓️ 已合并 |
| `hubai_openclaw_quotation_system_plan_v4_202606251244.md` | OpenClaw 统一入口 v4.1 | ⛓️ 已合并 |

---

---

## 十、报价 Agent Skill 架构设计（新增）

> 核心原则：**不要让大模型去"算"报价，而是让大模型去"调度"报价。**
> 报价模块升级为 Agent Skill，辅以知识库提供业务上下文。

### 10.1 架构定位对比

| 对比维度 | 作为知识库功能模块（静态认知） | 作为 Agent Skill（动态执行） |
|---------|---------------------------|------------------------|
| **核心定位** | 提供报价相关的背景知识、产品手册、历史报价单、竞品对比等事实信息。 | 封装报价SOP、配置规则、成本核算逻辑、审批流程与输出模板。 |
| **解决的问题** | "怎么查"、"是什么"（例如：某型号设备的历史价格是多少？）。 | "怎么做"、"执行它"（例如：根据客户需求自动核算成本并生成合规报价单）。 |
| **交互方式** | 用户提问，系统检索并生成文本回答或展示文档片段。 | 用户下达指令，Agent 自动调用脚本/API，跨系统拉取数据并生成结构化文件。 |
| **业务价值** | 缩短销售查阅资料的时间，提供信息参考。 | 将数天的报价周期压缩至几小时，规范折扣权限，杜绝人工漏算与配置冲突。 |
| **架构特点** | 依赖向量检索（RAG），适合非结构化文档和FAQ。 | 依赖确定性脚本（如Python/SQL）、规则引擎和MCP工具连接，保证计算绝对准确。 |

### 10.2 方案优缺点分析

**作为知识库功能模块：**
- **优点**：开发成本低，部署快；适合处理非标准化的历史案例、客户证言和复杂的竞品优劣势分析。
- **缺点**：大模型存在"幻觉"风险，绝不能让大模型直接进行复杂的成本核算与折扣计算；无法与ERP/CRM等内部系统产生双向数据联动；只能"看"不能"做"。

**作为 Agent Skill：**
- **优点**：
  - **高确定性与合规性**：将报价规则、配件兼容性校验、参数冲突检测固化为代码脚本，确保每次输出结果一致且符合企业利润底线。
  - **跨系统自动化**：通过调用API，自动查询客户历史订单、当前库存，并根据规则动态计算折扣，最终生成标准格式的报价文档。
  - **可复用与可审计**：一次封装，所有Agent均可调用；且每次报价的执行步骤、调用参数均有完整日志，满足企业审计要求。
- **缺点**：开发门槛较高，需要梳理严密的业务SOP并编写相应的执行脚本；如果业务规则频繁变动，维护Skill的成本相对较高。

### 10.3 认知与执行分离的混合架构

在实际的企业级架构中，这两者并非互斥关系。最优解是将"报价知识库"作为底层支撑，将"报价生成Skill"作为上层执行单元，构建"认知+执行"的闭环。

#### 架构分层设计

| 层级 | 职责 | 组件 |
|------|------|------|
| **认知层（知识库）** | 提供业务上下文 | 产品手册、历史报价单、竞品参数、议价策略、FAQ |
| **调度层（大模型）** | 理解需求、提取信息、决定流程、调用Skill | OpenClaw Gateway、多轮对话管理、意图识别 |
| **执行层（Skill）** | 确定性计算、规则校验、文档生成、审批流转 | smart-quotation Skill（Python脚本 + 规则引擎 + MCP工具） |
| **数据层（数据库）** | 持久化存储 | SQLite/PostgreSQL、FTS5、IMA知识库 |

#### Skill 内部模块化封装

一个标准的报价 Skill 应包含以下组件，避免将其做成臃肿的"屎山知识库"：

| 组件 | 说明 | 示例 |
|------|------|------|
| **SKILL.md** | 任务说明书：明确报价的适用场景、输入参数、输出格式及异常处理 | 输入参数：客户等级、产品型号、数量；异常：库存不足时标注备货周期 |
| **scripts/** | 规则与脚本：封装成本核算逻辑、折扣系数表、配件兼容性校验代码 | price_engine.py、rule_validator.py、route_engine.py、doc_generator.py |
| **templates/** | 报价单模板：内置标准的报价单模板 | Markdown模板、PDF模板、客户版模板 |
| **config/** | 权限与规则：设定严格的权限边界 | 折扣上限、审批规则、库存阈值 |
| **logs/** | 审计日志：完整执行日志 | 每次报价的执行步骤、调用参数、计算结果 |

#### 渐进式披露与工具协同

在Agent执行报价时，采用"渐进式披露"机制：

1. **元数据加载**：Agent先加载 smart-quotation Skill的元数据（仅几十个Token）
2. **意图确认**：确认需要执行报价后，再加载完整的执行指令和脚本
3. **MCP连接**：Skill通过MCP协议安全地连接ERP查库存、连接CRM查客户等级
4. **端到端自动化**：实现从需求输入到报价单输出的全自动化流转

### 10.4 报价 Skill 定义示例

```text
Skill: smart-quotation
Location: ~/.openclaw/skills/smart-quotation/
Version: 1.0.0

## 适用场景
- 客户需要产品报价
- 客户需要技术方案+报价组合
- 客户需要快速价格参考（内部查询，不进入正式报价流程）

## 输入参数
{
  "customer_company": "string",        // 客户公司名称
  "customer_level": "standard|vip|strategic|new",
  "products": [
    {
      "product_code": "string",
      "quantity": "integer"
    }
  ],
  "budget_range": "string",            // 可选
  "custom_requirements": "string",     // 可选
  "communication_needed": "boolean"    // 是否需要沟通交流和技术方案
}

## 输出格式
{
  "quotation_no": "string",
  "status": "draft|approved|rejected",
  "lines": [
    {
      "product_name": "string",
      "quantity": "integer",
      "unit_price": "number",
      "discount_rate": "number",
      "line_amount": "number"
    }
  ],
  "total_amount": "number",
  "margin_rate": "number",
  "risk_flags": ["string"],
  "approval_required": "boolean",
  "approval_chain": ["string"],
  "documents": {
    "internal": "markdown_url",        // 内部审批版
    "customer": "markdown_url"         // 客户版（脱敏）
  }
}

## 异常处理
- 产品不存在：返回错误码 PRODUCT_NOT_FOUND，提示用户确认产品型号
- 库存不足：返回警告 INVENTORY_SHORTAGE，标注预计补货日期
- 折扣超限：返回错误码 DISCOUNT_EXCEEDED，触发审批流程
- 毛利率过低：返回警告 MARGIN_TOO_LOW，要求财务确认

## 权限边界
- 标准销售：可发起标准型报价（折扣≤9折）
- 销售经理：可审批方案型报价（折扣≤8折）
- 销售总监：可审批非标型报价（折扣≤7折）
- 财务总监：可审批高风险报价（折扣<7折或账期>30天）
```

### 10.5 执行流程（大模型调度 vs Skill执行）

```text
【大模型调度层】
用户："帮我报个价，XX教育公司要20台云桌面"

大模型动作：
1. 意图识别 → 确认是报价需求
2. 信息提取 → customer_company="XX教育", products=[{code:"cloud-desktop", qty:20}]
3. 检查完整性 → 缺少客户等级、预算、联系方式
4. 对话追问 → "请问联系人姓名和电话？客户预算范围？"

用户："张经理 138****1234，预算2万左右"

大模型动作：
5. 信息补全 → 所有P0字段已收集
6. 调用 Skill → sessions_spawn(agent="smart-quotation", params={...})

【Skill执行层】
Skill动作：
1. 加载配置 → 读取折扣系数表、审批规则
2. 查询数据库 → 获取产品价格、库存、客户等级
3. 计算价格 → Python脚本执行，100%确定性
4. 规则校验 → 毛利率、库存、折扣上限
5. 生成文档 → Markdown/PDF报价单
6. 返回结果 → 包含quotation_no、lines、total_amount、risk_flags

【大模型调度层】
大模型动作：
7. 接收结果 → 解析Skill返回的JSON
8. 生成回复 → "报价草稿已生成：
   企业版云桌面 ×20台，折扣价¥720/台，合计¥14,400
   毛利率28%，无需审批
   [查看客户版] [提交审批] [调整价格]"
```

### 10.6 技术实现要点

| 要点 | 说明 |
|------|------|
| **绝不让大模型计算** | 所有价格计算、折扣应用、毛利率核算均由Python脚本执行 |
| **规则引擎优先** | 完整性检查、缺口检测、分流判断优先使用规则引擎，LLM只做摘要/抽取/话术 |
| **MCP协议连接** | Skill通过MCP协议连接ERP（库存）、CRM（客户等级）、财务系统（成本价） |
| **渐进式披露** | Agent先加载Skill元数据确认意图，再加载完整执行脚本 |
| **完整审计日志** | 每次报价的执行步骤、调用参数、计算结果均记录到logs/目录 |
| **权限边界** | SKILL.md中明确定义不同角色的折扣权限和审批阈值 |

---

### 11. 多产品线架构（2026-06-26 新增）

#### 11.1 背景与演进

原有报价系统仅支持单一产品报价。实际业务中，HubAI 需要支持多个产品线（云桌面、无影云电脑等），且未来还会扩展更多产品。为避免每个产品重复开发，设计了"底座统一、产品独立"的多产品架构。

> **状态更新（2026-06-26）**：多产品线架构已**配置完成并部署验证通过**，全部 14 个 Python 模块创建完毕，底座增强模块与产品 Skill 均通过导入测试。

#### 11.2 架构层级

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        底座能力包 (hubai-base v1.1.0)                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  product_router.py          # 产品路由引擎（新增）          │   │
│  │  requirement_base.py          # 需求表基类（新增）          │   │
│  │  dialogue_base.py            # 话术基类（新增）             │   │
│  │  db.py | logger.py | auth.py | config.py | errors.py       │   │
│  │  mcp_client.py               # 外部系统连接                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                  统一报价入口 (smart-quotation v1.1.0)                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  quotation_coordinator.py    # 报价协调器（总入口）         │   │
│  │  product_detector.py          # 产品检测器                 │   │
│  │  session_manager.py           # 多轮会话管理               │   │
│  │  cross_product.py             # 跨产品组合报价             │   │
│  │  price_engine | rule_validator | route_engine | doc_generator│   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┬─────────────────────┬──────────────────┐  │
│  │ product-cloud-desktop│ product-wuying-pc  │ product-xxx      │  │
│  │   云桌面 Skill       │  无影云电脑 Skill   │   其他产品 Skill  │  │
│  ├─────────────────────┼─────────────────────┼──────────────────┤  │
│  │ config/requirement  │ config/requirement  │ config/requirement│  │
│  │ config/dialogue    │ config/dialogue    │ config/dialogue  │  │
│  │ requirement_handler │ requirement_handler │ requirement_handler│  │
│  │ dialogue_handler    │ dialogue_handler    │ dialogue_handler │  │
│  │ price_engine        │ price_engine        │ price_engine     │  │
│  │ quotation_engine    │ quotation_engine    │ quotation_engine │  │
│  └─────────────────────┴─────────────────────┴──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

#### 11.3 核心设计原则

| 原则 | 说明 |
|------|------|
| **底座统一** | hubai-base 提供通用能力：产品路由、需求表基类、话术基类 |
| **产品独立** | 每个产品线独立为一个 Skill，包含专属需求表、话术、报价规则 |
| **配置驱动** | 需求表、话术全部 JSON 化，新增产品只需添加配置 |
| **自动路由** | 根据对话内容自动识别产品，路由到对应产品 Skill |
| **统一入口** | 用户对话始终由 smart-quotation 统一接收，内部再分发 |

#### 11.4 已部署产品

| 产品 | 编码 | 字段数 | 性能等级 | 规模折扣 |
|------|------|--------|----------|----------|
| **云桌面** | cloud-desktop | 8 | 5 档 | 5 档 |
| **无影云电脑** | wuying-pc | 10 | 4 档 | 5 档 |

#### 11.5 部署完成清单（2026-06-26 ✅）

| 模块 | 文件 | 状态 |
|------|------|------|
| **底座增强 v1.1.0** | `hubai-base/scripts/product_router.py` | ✅ 已部署 |
| | `hubai-base/scripts/requirement_base.py` | ✅ 已部署 |
| | `hubai-base/scripts/dialogue_base.py` | ✅ 已部署 |
| | `hubai-base/config/products/cloud-desktop.json` | ✅ 已部署 |
| | `hubai-base/config/products/wuying-pc.json` | ✅ 已部署 |
| **统一入口增强 v1.1.0** | `smart-quotation/scripts/quotation_coordinator.py` | ✅ 已部署 |
| | `smart-quotation/scripts/session_manager.py` | ✅ 已部署 |
| | `smart-quotation/scripts/cross_product.py` | ✅ 已部署 |
| **云桌面 Skill v1.0.0** | `product-cloud-desktop/` 全套（8 模块） | ✅ 已部署 |
| **无影云电脑 Skill v1.0.0** | `product-wuying-pc/` 全套（8 模块） | ✅ 已部署 |
| **软链接注册** | `~/.openclaw/skills/` 下全部 Skill 链接 | ✅ 已创建 |
| **功能验证** | 产品路由、需求表、话术、价格计算 | ✅ 全部通过 |

#### 11.6 扩展方式

新增产品线只需 3 步：
1. **注册产品** - 在 `hubai-base/config/products/` 添加产品 JSON 配置
2. **创建配置** - 创建 `config/requirement.json` 和 `config/dialogue.json`
3. **继承基类** - 实现 `RequirementHandler` 和 `DialogueHandler`（约 20 行代码）

---

**编制人**：AI+比特虾 🦐  
**日期**：2026-06-29  
**版本**：v1.3 - Unified（已整合多产品线架构，底座与产品 Skill 全部部署验证通过）  
**部署状态**：✅ 底座增强 v1.1.0 | ✅ 统一入口 v1.1.0 | ✅ 云桌面 Skill v1.0.0 | ✅ 无影云电脑 Skill v1.0.0  
**后续迭代**：所有 HubAI 方案基于此统一方案演进
