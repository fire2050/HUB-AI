# HubAI 报价工作流设计方案 v3.0

> 版本：v3.0  
> 时间：2026-06-25  
> 定位：基于 HubAI 企业知识库基础版（0.2.0）的商务助理报价工作流  
> 原则：不脱离当前方案，复用现有 product/price/inventory/quotation/policy/knowledge_chunk 表结构与 API 底座

---

## 一、总体架构

```text
┌─────────────────────────────────────────────────────────────┐
│                     HubAI 数字员工工作台                       │
│  财务助理 │ 商务助理 │ 销售助理 │ 技术助理 │ 上传 │ API       │
├─────────────────────────────────────────────────────────────┤
│  入口：Web 端 + Agent 端（skill/MVP：钉钉、企微等）           │
│    ↓                                                        │
│  客户需求表三（必需） → 需求卡（规则校验+缺口+追问）          │
│    ↓                                                        │
│  分流派单：标准型 / 方案型 / 非标型 / 高风险                   │
│    ↓                                                        │
│  历史案例参考（强制参考，不作为报价规则）                     │
│    ↓                                                        │
│  输出选择确认：方案 / 报价单 / 两者都要                         │
│    ↓                                                        │
│  内部方案初稿 → 报价草稿 → 规则校验 → 客户版本 → 回写结果     │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、工作流详细设计

### Step 1：多入口需求接入 + 客户需求表三（需求接收入口）

**目标**：以客户需求表三作为客户需求报价的必经入口，同时支持 Web 端和 Agent 端两类入口。Agent 端通过 skill 和 MVP 能力接入，覆盖钉钉、企微等对话入口；无论入口来自哪里，都必须先沉淀为客户需求表三，再进入需求卡、缺口发现和报价流程。



#### 1.1 报价入口边界

| 入口类型 | 范围 | 作用 | 落库要求 |
|---|---|---|---|
| Web 端 | HubAI 工作台、商务/销售助理页面 | 人工录入、粘贴客户原文、上传附件、查看流程状态 | 必须创建客户需求表三记录 |
| Agent 端 | Agents 通过 skill 和 MVP 接入 | 对话式收集需求、追问、提醒补充材料 | 必须调用同一套需求表三 API |
| 钉钉入口 | Agent 端子入口 | 群聊/单聊中收集客户需求、同步审批/提醒 | source_channel=`dingtalk` |
| 企微入口 | Agent 端子入口 | 企微会话中收集客户需求、同步客户材料 | source_channel=`wecom` |
| 其他入口 | 邮件、电话转录、导入文件 | 只作为需求来源，不直接报价 | 统一归档到客户需求表三 |

**强约束**：

1. 客户需求报价单必须先完成“客户需求表三”。
2. Web 端和 Agent 端只是入口不同，后续共用同一套需求卡、分流、历史参考、报价和审批流程。
3. Agent 端不得绕过需求表三直接生成正式客户报价。最多可输出“报价参考/待确认草稿”。
4. 入口字段统一使用 `source_channel`、`source_ref` 和 `created_by` 标识来源，避免多入口数据割裂。

#### 1.2 历史项目定位

历史项目、历史报价和相似案例在本流程中只作为参考，不作为报价规则。

| 类型 | 可做 | 不可做 |
|---|---|---|
| 历史项目 | 辅助理解客户背景、交付方式、相似产品组合 | 直接套用为当前报价规则 |
| 历史报价 | 展示参考价格、折扣、赢输单结果 | 替代当前产品价格表、报价政策、审批规则 |
| 相似案例 | 提醒风险、生成参考说明、辅助销售判断 | 自动决定最终报价底价或折扣上限 |

正式报价规则必须来自当前有效的产品价格、报价政策、库存、审批和人工确认结果。

**当前已有能力**：
- `/api/chat` 统一对话入口
- `route_assistant()` 识别报价意图
- `resolve_product_code()` 从文本提取产品编码
- `upsert_product_records()` 产品数据导入

**新增能力**：
- 新增 `order_requirement_table` 表（AI 表格化需求收集）

```sql
CREATE TABLE IF NOT EXISTS order_requirement_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT UNIQUE NOT NULL,              -- E-20260624-XXXXXX
    source_channel TEXT DEFAULT 'web',          -- web / dingtalk / phone / email
    customer_name TEXT,
    customer_company TEXT,
    customer_contact TEXT,                      -- 电话/微信/邮箱
    customer_level TEXT DEFAULT 'standard',     -- standard / vip / strategic / new
    requirement_type TEXT,                      -- standard / solution / custom / risky
    -- 需求主体
    product_codes TEXT,                         -- JSON 数组，支持多产品
    quantity TEXT,                              -- JSON 对象 {product_code: qty}
    required_delivery_date TEXT,
    budget_range TEXT,                          -- 预算区间
    -- 交付与条款
    delivery_mode TEXT DEFAULT 'standard',      -- standard / urgent / phased / onsite
    payment_terms TEXT DEFAULT 'prepay_30',     -- prepay_30 / prepay_50 / net_30 / net_60
    warranty_required TEXT,                     -- 延保要求
    training_required INTEGER DEFAULT 0,        -- 是否需要培训
    -- 特殊信息
    competitor_info TEXT,                       -- 竞品提及
    custom_requirements TEXT,                   -- 定制需求描述
    risk_flags TEXT,                            -- JSON 数组：低毛利/超短交期/信用风险/越权折扣
    -- AI 辅助字段
    ai_extracted_summary TEXT,                  -- AI 自动提取的摘要
    ai_confidence_score REAL DEFAULT 0.0,       -- AI 识别置信度
    ai_suggested_products TEXT,                 -- AI 推荐产品
    -- 状态
    status TEXT DEFAULT 'draft',                -- draft / submitted / processing / completed
    submitted_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**AI 表格收集方式**：

| 字段 | 类型 | 收集方式 |
|---|---|---|
| 客户信息 | 文本 | 销售手动填写或从客户池下拉选择 |
| 产品需求 | 多选+数量 | 从产品库搜索选择，支持模糊匹配 |
| 交付时间 | 日期 | 日期选择器 |
| 预算 | 文本 | 文本输入，AI 自动识别数字区间 |
| 竞品 | 文本 | 文本输入 |
| 定制需求 | 长文本 | 文本框，AI 自动标红关键词 |
| 特殊条款 | 多选 | 勾选：账期/延保/培训/现场交付 |

**AI 辅助能力**：
1. **智能填单**：销售粘贴客户微信/邮件原文，AI 自动提取字段并回填
2. **产品推荐**：根据需求描述，从 `product` 表推荐最匹配产品
3. **风险标红**：识别"急单"、"账期长"、"定制"等关键词，自动标红并提示

**接口**：
```text
POST /api/quotations/order-entry
Body: { customer_name, customer_company, customer_contact, product_codes, quantity, ... }

POST /api/quotations/order-entry/ai-extract
Body: { raw_text }  -- 粘贴客户原文，AI 自动提取字段
```

**落地动作**：
销售在"订单 AI 表格"页面填写或粘贴客户信息：
```text
客户原文："我们需要 20 台无影云教室，预算 2 万以内，月底前要交货，竞品是华为云桌面"
→ AI 自动提取：
  产品：无影云教室（推荐匹配：企业版-AI云教室-图形工作站旗舰型）
  数量：20
  预算：2万以内
  交期：月底前（标红：超短交期）
  竞品：华为云桌面
  风险标红：⚠️ 超短交期
```

---

### Step 2：需求卡（规则校验 + 缺口发现 + 追问清单）

**目标**：把订单表格数据生成结构化需求卡，内置规则校验和缺口发现，自动生成追问清单。一次完成，不再分三步。

**当前已有能力**：
- `product` / `product_price` / `inventory` / `quotation_policy` 表
- `knowledge_search()` 知识检索

**新增能力**：
- `quotation_requirement_card` 表（关联订单表格）
- 内置规则引擎（无需 LLM）

```sql
CREATE TABLE IF NOT EXISTS quotation_requirement_card (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_no TEXT UNIQUE NOT NULL,               -- QC-20260624-XXXXXX
    entry_id TEXT NOT NULL,                     -- 关联 order_requirement_table
    
    -- 完整性检查字段
    completeness_score INTEGER DEFAULT 0,       -- 0-100 分
    missing_fields TEXT,                        -- JSON 数组：缺失字段列表
    
    -- 缺口发现结果
    gap_summary TEXT,                           -- JSON 对象
    gap_count INTEGER DEFAULT 0,                -- 缺口数量
    
    -- 追问清单（JSON 数组）
    clarification_list TEXT,                    -- JSON 数组
    
    -- 分流建议（自动计算）
    suggested_route TEXT,                       -- standard / solution / custom / risky
    route_reason TEXT,
    
    status TEXT DEFAULT 'draft',                -- draft / clarified / ready
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.1 规则校验（完整性检查）

**必输字段检查（基础版硬编码规则）**：

| 检查项 | 规则 | 权重 |
|---|---|---|
| 客户名称 | 不能为空 | 15 |
| 产品信息 | 至少选 1 个产品 | 20 |
| 数量 | 必须 > 0 | 15 |
| 预算 | 不能为空或"面议" | 10 |
| 交期 | 不能为空 | 15 |
| 联系方式 | 电话或邮箱至少一个 | 10 |
| 交付方式 | 不能为空 | 10 |
| 付款方式 | 不能为空 | 5 |

**完整性评分**：
```
score = Σ(通过项权重) / 总权重 * 100
score >= 80：完整，可直接进入分流
score 60-79：有缺失，需补充
score < 60：严重缺失，必须追问
```

#### 2.2 缺口发现（7 项自动检测）

| # | 缺口类型 | 检测逻辑 | 严重级别 |
|---|---|---|---|
| 1 | 产品不存在 | `product` 表中无匹配记录 | blocker |
| 2 | 价格缺失 | `product_price` 无 active 记录 | high |
| 3 | 库存不足 | `inventory.available < 需求数量` | high |
| 4 | 折扣政策缺失 | `quotation_policy` 无匹配客户级别+品类 | medium |
| 5 | 规格不完整 | `product_spec` 少于 3 条 | low |
| 6 | 竞品资料缺失 | `knowledge_chunk` 无竞品相关记录 | medium |
| 7 | 历史案例缺失 | `knowledge_chunk` 无同类产品历史报价 | low |

#### 2.3 追问清单自动生成

根据缺口和缺失字段，自动生成追问：

**追问模板（规则引擎）**：

```
IF 客户名称缺失 → "请补充客户公司名称和联系人"
IF 预算缺失 → "客户预算区间是多少？方便匹配最优方案"
IF 交期 < 7天 → "⚠️ 超短交期：需求 XX 天内交付，是否可接受分批发货？"
IF 库存不足 → "需求 XX 台，当前库存 YY 台，是否接受分批发货？"
IF 价格缺失 → "该产品暂无标准报价，是否可以先提供客户预算？"
IF 定制需求含"定制" → "定制需求已记录，是否需要技术团队介入评估？"
IF 竞品提及 → "客户提及竞品【XXX】，是否需要提供对比资料？"
IF 账期 > 30天 → "⚠️ 账期要求超过标准政策，需要商务审批"
```

**接口**：
```text
POST /api/quotations/requirement-card/generate
Body: { entry_id }
→ 返回：{ card_no, completeness_score, missing_fields, gap_summary, clarification_list, suggested_route }

POST /api/quotations/requirement-card/clarify
Body: { card_no, answers }  -- 销售回填追问答案
```

**落地动作**：
销售提交订单表格后，系统自动：
1. 跑完整性检查 → 显示评分（如 65/100）
2. 列出缺口 → "⚠️ 库存不足：需求 20，可用 12"
3. 生成追问清单 → 销售逐条确认或追问客户
4. 所有追问解决后，状态变为 `clarified`，进入分流

---

### Step 3：分流派单（四类需求路由）

**目标**：根据需求卡的分析结果，自动判断需求类型，分流到不同处理路径。

**分流规则（基础版硬编码）**：

#### 3.1 标准型需求（Standard）

**判定条件**（满足全部）：
- `completeness_score >= 80`
- 产品在 `product` 表中存在
- `product_price` 有 active 记录
- `inventory.available >= 需求数量`
- `quotation_policy` 有匹配政策
- 无定制需求
- 无竞品提及
- 账期 <= 标准政策
- 交期 >= 标准周期

**处理路径**：
```
订单表格 → 需求卡（自动通过）→ 历史案例参考 → 报价草稿 → 规则校验 → 客户版本
```
**处理人**：销售助理（自动生成）
**预计时间**：5 分钟

#### 3.2 方案型需求（Solution）

**判定条件**（满足任一）：
- 客户目标明确，但产品选型不确定
- 需要多个产品组合方案
- 有"方案"、"整体"、"规划"等关键词
- 需求涉及跨部门协作

**处理路径**：
```
订单表格 → 需求卡 → 分流到技术助理 → 内部方案初稿 → 销售确认 → 历史案例 → 报价草稿
```
**处理人**：技术助理（方案）+ 销售助理（报价）
**预计时间**：1-2 天

#### 3.3 非标型需求（Custom）

**判定条件**（满足任一）：
- `custom_requirements` 不为空
- 有"定制"、"特殊"、"个性化"等关键词
- 交付方式 = `onsite` 或 `phased`
- 需要培训或延保
- 产品不在标准库中

**处理路径**：
```
订单表格 → 需求卡 → 标记非标 → 内部评审（技术+商务+财务）→ 评审通过后 → 历史案例 → 方案+报价
```
**处理人**：技术助理 + 商务助理 + 财务助理（联合评审）
**预计时间**：3-5 天

#### 3.4 高风险需求（Risky）

**判定条件**（满足任一）：
- `risk_flags` 包含任一风险项
- 账期 > 标准政策
- 交期 < 标准周期 50%
- 折扣请求突破 `quotation_policy` 上限
- 客户级别 = `new` 且金额 > 阈值
- 毛利率 < 15%（估算）

**处理路径**：
```
订单表格 → 需求卡 → 标记高风险 → 升级审批（负责人/老板）→ 审批通过后 → 历史案例 → 方案+报价
```
**处理人**：销售总监 / 商务负责人 / 老板
**预计时间**：待定（取决于审批速度）

#### 3.5 分流决策矩阵

```
┌─────────────────────────────────────────────────────────────┐
│                    分流决策树                                │
│                                                              │
│  是否有 risk_flags？                                         │
│    ├── 是 → 高风险型 → 升级审批                              │
│    └── 否 → 是否有 custom_requirements？                     │
│           ├── 是 → 非标型 → 内部评审                          │
│           └── 否 → 产品是否明确？                            │
│                  ├── 否 → 方案型 → 技术确认                   │
│                  └── 是 → 标准型 → 快速报价                   │
└─────────────────────────────────────────────────────────────┘
```

**接口**：
```text
POST /api/quotations/route
Body: { card_no }
→ 返回：{ route_type, route_reason, assigned_assistants, estimated_time }
```

---

### Step 4：历史案例参考（强制参考，不作为报价规则）

**目标**：输出任何方案或报价之前，必须检索并展示历史类似案例，辅助销售理解背景和风险；但历史项目仅作为报价参考，不作为报价规则。

**当前已有能力**：
- `quotation_header` / `quotation_line` 历史报价记录
- `knowledge_chunk_fts` 全文检索

**新增能力**：
- 历史案例自动匹配算法

**匹配逻辑**：

| 维度 | 权重 | 匹配方式 |
|---|---|---|
| 产品相同 | 40% | `product_code` 完全匹配 |
| 数量相近 | 20% | 数量差异 <= 30% |
| 客户级别相同 | 15% | `customer_level` 匹配 |
| 交付方式相同 | 10% | `delivery_mode` 匹配 |
| 时间相近 | 10% | 6 个月内 |
| 行业相同 | 5% | `customer_company` 行业匹配 |

**输出格式**：
```
📚 历史相似案例（Top 3）

案例 1（相似度 92%）
  客户：XX 教育公司（VIP）
  产品：企业版-AI云教室-图形工作站旗舰型 Pro-16核
  数量：18 台
  单价：14.40 元（折扣 0.90）
  交付：标准
  时间：2026-05-15
  结果：赢单

案例 2（相似度 78%）
  ...
```

**接口**：
```text
POST /api/quotations/historical-cases
Body: { card_no }
→ 返回：{ cases: [{ similarity, quotation_no, customer, products, prices, result }] }
```

**强制校验**：
- 如无历史案例匹配度 > 50%，系统提示："⚠️ 未找到足够相似的历史案例，建议谨慎定价"
- 历史案例只参与风险提示和参考说明，不参与自动定价规则计算
- 报价草稿不得依据历史最低价自动下调；折扣、底价和审批必须以当前 `product_price`、`quotation_policy`、库存与审批规则为准

---

### Step 5：输出选择确认

**目标**：在生成内部方案或报价草稿之前，先确认客户需要输出什么：方案、报价单、还是两者都要。

**当前已有能力**：
- `quotation_header` / `quotation_line` 报价表
- `product_document` 产品文档

**新增能力**：
- 输出类型选择确认机制

**选择逻辑**：

| 需求类型 | 默认输出 | 可选 |
|---|---|---|
| 标准型 | 报价单 | — |
| 方案型 | 方案 + 报价单 | 可只选方案 |
| 非标型 | 方案 + 报价单 | 不可拆分 |
| 高风险 | 方案 + 报价单 | 不可拆分 |

**确认流程**：
```
销售在页面选择：
☑️ 输出技术/商务方案
☑️ 输出正式报价单
[确认输出]
```

**方案与报价单的区别**：

| | 方案 | 报价单 |
|---|---|---|
| 内容 | 技术架构、交付计划、实施步骤、风险评估 | 产品清单、数量、单价、折扣、合计 |
| 受众 | 客户技术/采购团队 | 客户采购/财务 |
| 格式 | Markdown / PPT（后续） | Markdown / PDF |
| 审批 | 技术/商务审批 | 商务/财务审批 |
| 有效期 | 长期 | 30 天 |

**接口**：
```text
POST /api/quotations/output-type/confirm
Body: { card_no, output_types: ['proposal', 'quotation'] }
```

---

### Step 6：内部方案初稿（可选，仅当输出包含方案时）

**目标**：基于需求卡和历史案例，生成内部技术/商务方案。

**当前已有能力**：
- `product_document` / `product_spec` / `product_faq`
- `knowledge_chunk` 知识检索

**新增能力**：
- `quotation_proposal` 表

```sql
CREATE TABLE IF NOT EXISTS quotation_proposal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_no TEXT UNIQUE NOT NULL,           -- QP-20260624-XXXXXX
    card_no TEXT NOT NULL,
    
    proposal_type TEXT,                         -- technical / commercial / combined
    
    -- 方案内容
    overview TEXT,                              -- 项目概述
    product_solution TEXT,                      -- 产品解决方案
    architecture TEXT,                          -- 技术架构
    delivery_plan TEXT,                         -- 交付计划
    training_plan TEXT,                         -- 培训计划
    risk_assessment TEXT,                       -- 风险评估
    
    -- 商务信息
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
```

**生成逻辑**：
1. 从 `product_document` 拉取部署手册 → 技术架构
2. 从 `product_spec` 拉取参数 → 产品选型说明
3. 从历史案例 → 定价参考
4. 从 `quotation_policy` → 折扣策略

---

### Step 7：报价草稿

**目标**：基于方案（如有）和当前价格/库存/政策，生成正式报价草稿。

**当前已有能力**：
- `generate_quotation()` 已有报价生成逻辑
- `quotation_header` / `quotation_line` 表

**新增能力**：
- 关联需求卡和方案号
- 多产品支持
- 历史案例价格参考

```sql
-- 扩展现有表
ALTER TABLE quotation_header ADD COLUMN card_no TEXT;
ALTER TABLE quotation_header ADD COLUMN proposal_no TEXT;
ALTER TABLE quotation_header ADD COLUMN historical_case_refs TEXT;  -- JSON 数组
ALTER TABLE quotation_header ADD COLUMN version INTEGER DEFAULT 1;
```

**生成规则**：
1. 从 `product_price` 取最新 active 价格
2. 从 `quotation_policy` 匹配最优折扣（客户级别 + 数量 + 品类）
3. 从 `inventory` 校验库存
4. 历史案例只写入 `historical_case_refs` 作为参考说明，不参与规则决策
5. 生成 `quotation_header` + `quotation_line`

**接口**：
```text
POST /api/quotations/generate
Body: {
    customer_code,
    items: [{ product_code, qty }],
    card_no,
    proposal_no,
    historical_case_refs,
    created_by
}
```

---

### Step 8：规则校验和审批

**目标**：校验报价是否符合公司政策，根据需求类型触发不同审批流。

**当前已有能力**：
- `quotation_policy` 折扣规则
- `UserContext` 权限

**审批规则**：

| 需求类型 | 审批流程 | 审批人 |
|---|---|---|
| 标准型 | 自动通过（无人工审批） | — |
| 方案型 | 技术确认 + 商务确认 | 技术助理 + 商务助理 |
| 非标型 | 技术评审 + 商务评审 + 财务评审 | 三方联合 |
| 高风险 | 负责人审批 + 老板审批（如需） | 销售总监 / 老板 |

**校验规则**：

| 规则 | 标准型 | 方案型 | 非标型 | 高风险 |
|---|---|---|---|---|
| 价格底线 | 自动 | 自动 | 人工 | 人工 |
| 折扣上限 | 自动 | 自动 | 人工 | 人工 |
| 库存校验 | 自动 | 自动 | 人工 | 人工 |
| 利润校验 | 自动 | 自动 | 人工 | 人工 |
| 交付周期 | 自动 | 技术确认 | 技术评审 | 负责人审批 |

**接口**：
```text
POST /api/quotations/validate
Body: { quotation_no }

POST /api/quotations/approve
Body: { quotation_no, approval_type, approver_user_id, approval_status, approval_comment }
```

---

### Step 9：客户版本输出

**目标**：把审批通过的方案/报价单，转换为对外客户版本。

**当前已有能力**：
- Markdown 输出
- `quotation_header` / `quotation_line` 数据

**新增能力**：
- `quotation_customer_output` 表
- 客户版模板（脱敏、美化）

```sql
CREATE TABLE IF NOT EXISTS quotation_customer_output (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    output_no TEXT UNIQUE NOT NULL,             -- CO-20260624-XXXXXX
    quotation_no TEXT,
    proposal_no TEXT,
    output_type TEXT,                           -- proposal / quotation / combined
    
    customer_markdown TEXT,                     -- 客户可见版本
    valid_until TEXT,
    terms_and_conditions TEXT,
    contact_info TEXT,
    
    sent_at TEXT,
    opened_at TEXT,                             -- 客户查看时间（如有）
    
    status TEXT DEFAULT 'draft',
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**客户版 Markdown 模板**：
```markdown
# 商务报价单

**报价单号**：{quotation_no}  
**有效期至**：{valid_until}  

## 产品清单

| 产品名称 | 数量 | 单价 | 折扣 | 小计 |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

**合计**：{final_amount} 元

## 交付信息
- **交付周期**：{delivery_date}
- **付款方式**：{payment_terms}
- **质保**：{warranty}

## 联系方式
{contact_info}
```

**接口**：
```text
POST /api/quotations/customer-output/generate
Body: { quotation_no, proposal_no, output_type, terms_and_conditions, contact_info }
```

---

### Step 10：回写结果

**目标**：把最终报价结果回写到知识库，形成闭环。

**当前已有能力**：
- `knowledge_chunk` 知识切片
- `product_faq` 产品 FAQ
- 原始数据上传中心

**回写内容**：
1. **历史报价切片**：写入 `knowledge_chunk`（`source_type='historical_quotation'`）
2. **产品 FAQ 更新**：把客户常见问题写入 `product_faq`
3. **政策优化建议**：如果多次突破 `quotation_policy`，写入 `ext_json`
4. **原始数据归档**：客户询价文件归档到 `原始数据/03-报价库存`
5. **订单表格状态更新**：`order_requirement_table.status = 'completed'`

**接口**：
```text
POST /api/quotations/feedback
Body: { quotation_no, result: 'won'/'lost', final_price, competitor_final_price, lessons_learned }
```

---

## 三、数据流全景图

```text
订单 AI 表格 (order_requirement_table)
    ↓
需求卡生成 (quotation_requirement_card)
    ├── 完整性检查 (completeness_score)
    ├── 缺口发现 (7 项检测)
    └── 追问清单 (clarification_list)
    ↓
分流派单 (4 类路由)
    ├── 标准型 → 快速报价
    ├── 方案型 → 技术确认 → 方案+报价
    ├── 非标型 → 三方评审 → 方案+报价
    └── 高风险 → 升级审批 → 方案+报价
    ↓
历史案例参考（强制参考，不作为报价规则）
    ↓
输出选择确认（方案/报价单/两者）
    ↓
内部方案 (quotation_proposal) [可选]
    ↓
报价草稿 (quotation_header + quotation_line)
    ↓
规则校验 + 审批 (quotation_approval)
    ↓
客户版本 (quotation_customer_output)
    ↓
回写结果 (knowledge_chunk + product_faq + 归档)
```

---

## 四、页面交互设计

在商务助理页面新增"报价工作流"标签页：

```text
┌─────────────────────────────────────────────────────────────┐
│ 商务助理                                                    │
│ [智能问数] [库存查询] [报价辅助] [合同检查] [报价工作流]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ① 订单 AI 表格                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 客户信息 | 产品需求 | 交付条款 | 特殊要求            │   │
│  │ [粘贴客户原文] → [AI 自动提取]                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ② 需求卡                                                  │
│  完整性：85/100 ✅                                          │
│  缺口：⚠️ 库存不足（20 > 12）                               │
│  追问：❓ 是否接受分批发货？ [是] [否] [已追问客户]         │
│                                                             │
│  ③ 分流结果：标准型 → 销售助理自动处理                      │
│                                                             │
│  ④ 历史案例                                                │
│  📚 相似度 92%：XX 教育 18 台，单价 14.40，赢单            │
│                                                             │
│  ⑤ 输出确认                                                │
│  ☑️ 方案  ☑️ 报价单  [确认生成]                             │
│                                                             │
│  ⑥ 报价草稿                                                │
│  💰 原价 16.00 × 20 = 320.00                               │
│     折扣 0.90                                              │
│     应付 288.00                                            │
│  [提交审批]                                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、与当前方案的衔接点

| 当前已有 | 工作流复用 |
|---|---|
| `product` / `product_price` / `inventory` | 缺口检测、报价生成 |
| `quotation_policy` | 缺口检测、折扣匹配、规则校验 |
| `quotation_header` / `quotation_line` | 报价草稿、历史案例 |
| `knowledge_chunk` + FTS5 | 历史案例检索、结果回写 |
| `product_faq` | 追问模板、结果回写 |
| 原始数据上传中心 | 客户询价文件归档 |
| `/api/chat` 统一路由 | 订单表格 AI 辅助填单 |
| 四类数字员工 | 分流派单 |

---

## 六、实施优先级

| 阶段 | 内容 | 工作量 | 优先级 |
|---|---|---|---|
| Phase 1 | Step 1：订单 AI 表格 + Step 2：需求卡（完整性+缺口+追问） | 2 天 | P0 |
| Phase 2 | Step 3：分流派单（4 类路由） | 1 天 | P0 |
| Phase 3 | Step 4：历史案例参考（强制参考，不作为报价规则） | 1 天 | P1 |
| Phase 4 | Step 5：输出选择确认 + Step 6：方案初稿 | 1 天 | P1 |
| Phase 5 | Step 7-8：报价草稿 + 规则校验/审批 | 1 天 | P2 |
| Phase 6 | Step 9：客户版本 + Step 10：回写结果 | 1 天 | P2 |

**总计约 7 天，分 6 个阶段迭代。**

---

## 七、风险与约束

1. **不脱离当前方案**：所有新增表使用 SQLite，不引入 PostgreSQL/Qdrant
2. **客户需求表三必经**：客户需求报价单必须先形成需求表三记录；Web/Agent/钉钉/企微入口不得绕过
3. **不引入 LLM 作为规则源**：完整性检查、缺口检测、追问生成、分流判断优先使用规则引擎；LLM 只做摘要、抽取、话术和辅助建议
4. **保持 RBAC**：所有接口复用 `UserContext` 权限校验
5. **向后兼容**：现有 `/api/quotations/generate` 接口保留，新增字段为可选；单品价格查询仍可直接出参考报价
6. **历史案例强制参考但不做规则**：如无足够相似案例，系统必须提示风险；历史项目不得替代当前价格、政策和审批规则


---

## 八、v3.0 执行计划

### 8.1 执行目标

围绕“Web 端 + Agent 端统一入口、客户需求表三必经、历史项目只做参考”三条新约束，把现有 v2.0 报价工作流升级为可执行 MVP。

### 8.2 里程碑计划

| 阶段 | 周期 | 目标 | 主要交付物 | 验收标准 |
|---|---:|---|---|---|
| M1：入口统一 | 0.5 天 | 明确 Web/Agent/钉钉/企微入口边界 | 入口字段、source_channel 枚举、API 入参约束 | 所有入口都能落到客户需求表三 |
| M2：客户需求表三增强 | 1 天 | 将需求表三设为客户需求报价必经步骤 | 表字段补齐、前端文案、保存接口校验 | 未保存需求表三不能进入客户需求正式报价 |
| M3：Agent 接入 MVP | 1 天 | Agent 通过 skill/MVP 调用同一需求表 API | Agent 采集流程、钉钉/企微 source_channel 预留 | Agent 端提交的数据和 Web 端一致落库 |
| M4：需求卡和分流 | 1-2 天 | 生成需求卡、缺口、追问、四类分流 | 规则引擎、需求卡接口、分流结果 | 标准/方案/非标/高风险可被正确识别 |
| M5：历史参考重构 | 0.5-1 天 | 历史项目只做参考，不参与报价规则 | historical_case_refs、参考提示、页面展示 | 页面展示“参考”标识；规则计算不读取历史价作为约束 |
| M6：报价/审批闭环 | 1-2 天 | 报价草稿、规则校验、审批、客户版输出 | 报价接口扩展、审批字段、客户版模板 | 能从需求表三走到客户版输出 |
| M7：回写和验收 | 0.5 天 | 回写知识库和流程状态 | knowledge_chunk 回写、状态流转、测试报告 | 报价完成后可检索历史记录，但仍为参考 |

### 8.3 开发任务清单

#### A. 数据库与数据模型

1. 保留并增强 `order_requirement`，作为“客户需求表三”主表。
2. 增加或确认以下字段：`source_channel`、`source_ref`、`attachment_links`、`entered_at`、`sales_owner_user_id`、`customer_expected_time`、`is_urgent`、`has_historical_project`、`historical_project_refs`。
3. 将 `source_channel` 枚举扩展为：`web`、`agent`、`dingtalk`、`wecom`、`email`、`phone`、`import`。
4. 新增需求卡表 `quotation_requirement_card`，存储完整性评分、缺口、追问、分流建议。
5. 报价头表扩展：`requirement_no/card_no/proposal_no/historical_case_refs/version`。

#### B. Web 端

1. 销售助理/商务助理页面保留“单品价格查询”。
2. “客户需求报价单”模式改名为“客户需求表三”。
3. 页面文案明确：客户需求报价必须先保存客户需求表三。
4. 保存成功后展示：需求编号、待人工确认、下一步负责人、可生成需求卡。
5. 如果用户尝试客户需求报价但没有 `requirement_no`，前端阻断并提示补全需求表三。

#### C. Agent 端（skill + MVP）

1. 定义 Agent 提交流程：收集客户名称、联系人、来源、原始需求、附件、期望时间、负责人、是否紧急、是否历史项目。
2. Agent 调用同一接口 `POST /api/order-requirements`，不得单独写另一套表。
3. 钉钉入口映射 `source_channel=dingtalk`；企微入口映射 `source_channel=wecom`；普通 Agent 映射 `source_channel=agent`。
4. Agent 只可生成“待确认报价参考/草稿”，正式客户报价必须经过需求表三和审批状态。

#### D. 历史项目参考逻辑

1. 历史项目字段只用于检索参考案例、展示客户背景、提示相似风险。
2. 报价规则来源限定为：产品价格、报价政策、库存、客户等级、审批结果、人工确认。
3. 删除或禁用“历史最低折扣约束”类自动规则。
4. 页面展示历史案例时加标签：“仅供参考，不作为报价规则”。

#### E. 测试验收

1. Web 端提交一条需求表三，确认落库字段完整。
2. 模拟 Agent/钉钉/企微入口提交，确认均落到同一表。
3. 未提交需求表三时，客户需求报价按钮必须阻断。
4. 含历史项目的需求能展示历史参考，但报价金额仍按当前价格/政策生成。
5. 标准型需求可快速报价；方案型、非标、高风险能进入相应待处理状态。

### 8.4 优先级建议

P0：客户需求表三必经、入口字段统一、历史项目不作为规则。

P1：Agent 端提交 MVP、需求卡生成、分流派单。

P2：客户版输出、审批细化、结果回写和知识切片。
