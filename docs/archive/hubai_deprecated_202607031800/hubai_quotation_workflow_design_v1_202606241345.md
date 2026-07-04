# HubAI 报价工作流设计方案（基础版）

> 版本：v1.0  
> 时间：2026-06-24  
> 定位：基于 HubAI 企业知识库基础版（0.2.0）的商务助理报价工作流  
> 原则：不脱离当前方案，复用现有 product/price/inventory/quotation/policy/knowledge_chunk 表结构与 API 底座

---

## 一、总体架构

```text
┌─────────────────────────────────────────────────────────────┐
│                     HubAI 数字员工工作台                       │
│  财务助理 │ 商务助理 │ 销售助理 │ 技术助理 │ 上传 │ API       │
├─────────────────────────────────────────────────────────────┤
│  原始需求 → 需求卡 → 缺口发现 → 追问确认 → 分流派单          │
│  → 历史案例 → 内部方案 → 报价草稿 → 规则校验 → 客户版本      │
│  → 变更跟踪 → 回写结果                                       │
├─────────────────────────────────────────────────────────────┤
│  数据底座：product / product_price / inventory /              │
│           quotation_policy / quotation_header / quotation_line│
│           knowledge_chunk / product_faq / product_spec        │
│           原始数据/03-报价库存（上传路径）                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、十二步工作流详细设计

### Step 1：接住原始需求

**目标**：把客户/销售输入的原始询价信息，沉淀到系统，生成一条原始需求记录。

**输入渠道**：
- 销售助理 Web 页面输入框
- 钉钉 webhook 接收消息
- `/api/chat` 统一对话入口（关键词："报价"、"询价"、"多少钱"）

**当前已有能力**：
- `route_assistant()` 已识别报价意图，路由到 `assistant=quotation`
- `resolve_product_code()` 已支持从文本提取产品编码/名称

**需补充**：
- 新增 `quotation_request` 表（原始需求池）

```sql
CREATE TABLE IF NOT EXISTS quotation_request (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_no TEXT UNIQUE NOT NULL,        -- QR-20260624-XXXXXX
    source TEXT DEFAULT 'webchat',          -- webchat / dingtalk / api
    customer_name TEXT,
    customer_contact TEXT,
    raw_text TEXT NOT NULL,                 -- 原始需求文本
    matched_product_code TEXT,              -- 初步识别产品
    matched_product_name TEXT,
    status TEXT DEFAULT 'pending',          -- pending / clarified / routed
    created_by TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**接口**：
```text
POST /api/quotations/request
Body: { raw_text, customer_name, customer_contact, source, user_id }
```

**落地动作**：
销售在 Web 页面输入："客户要 20 台企业版-AI云教室-图形工作站旗舰型 Pro-16核32G内存8G显存，报个价"  
→ 系统写入 `quotation_request`，状态 `pending`，分配 `request_no`

---

### Step 2：生成需求卡

**目标**：把原始需求结构化，生成标准化需求卡片，供后续缺口分析使用。

**当前已有能力**：
- `product` 表有产品主数据
- `product_spec` 有规格参数
- `knowledge_chunk` 有产品文档切片

**需补充**：
- `quotation_requirement_card` 表

```sql
CREATE TABLE IF NOT EXISTS quotation_requirement_card (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_no TEXT UNIQUE NOT NULL,           -- QC-20260624-XXXXXX
    request_no TEXT NOT NULL,
    product_code TEXT,
    quantity INTEGER DEFAULT 1,
    required_delivery_date TEXT,
    customer_level TEXT DEFAULT 'standard', -- standard / vip / strategic
    special_requirements TEXT,              -- 定制需求、交付方式、账期
    price_expectation TEXT,                 -- 客户预算区间（文本）
    competitor_mentioned TEXT,              -- 竞品提及
    status TEXT DEFAULT 'draft',
    created_by TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**接口**：
```text
POST /api/quotations/requirement-card
Body: { request_no, product_code, quantity, required_delivery_date, customer_level, special_requirements, price_expectation, competitor_mentioned, user_id }
```

**落地动作**：
销售点击"生成需求卡"，系统从 `quotation_request` 拉取原始文本，自动填充：
- `product_code` = `resolve_product_code(raw_text)`
- `quantity` = 从文本提取数字（正则）
- 其余字段销售补充

---

### Step 3：发现缺口

**目标**：对比需求卡与当前产品/价格/库存/政策数据，自动发现信息缺口。

**当前已有能力**：
- `product` / `product_price` / `inventory` / `quotation_policy` 表
- `knowledge_search()` 知识检索

**缺口检测规则（硬编码在当前基础版，后续可接入 Qwen 语义判断）**：

| 检查项 | 数据来源 | 缺口判定 |
|---|---|---|
| 产品是否存在 | `product` 表 | `product_code` 找不到 |
| 价格是否存在 | `product_price` 表 | 无 active 价格记录 |
| 库存是否满足 | `inventory` 表 | `available_quantity < quantity` |
| 折扣政策是否覆盖 | `quotation_policy` 表 | 无匹配 `customer_level + product_category_code + min_quantity` 的政策 |
| 产品规格是否完整 | `product_spec` 表 | 少于 3 条规格记录 |
| FAQ 是否覆盖 | `product_faq` 表 | 无 FAQ 记录 |
| 竞品资料缺失 | `knowledge_chunk` 表 | 无 `source_type='competitor'` 记录 |

**需补充**：
- `quotation_gap` 表

```sql
CREATE TABLE IF NOT EXISTS quotation_gap (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_no TEXT NOT NULL,
    gap_type TEXT NOT NULL,                 -- missing_product / missing_price / insufficient_stock / missing_policy / missing_spec / missing_faq / missing_competitor_info
    gap_desc TEXT NOT NULL,
    severity TEXT DEFAULT 'medium',         -- low / medium / high / blocker
    suggested_action TEXT,
    status TEXT DEFAULT 'open',             -- open / resolved / waived
    resolved_by TEXT,
    resolved_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**接口**：
```text
POST /api/quotations/gap-analysis
Body: { card_no }
```

**落地动作**：
销售提交需求卡后，系统自动扫描上述 7 项，生成缺口列表。  
例如："库存不足（缺口：需求 20 台，可用 12 台）" → `severity=high` → 建议 action="联系商务补货或拆分交付"

---

### Step 4：生成追问和内部确认事项

**目标**：基于缺口，自动生成需要追问客户或内部确认的事项清单。

**当前已有能力**：
- `quotation_gap` 表已记录缺口
- `product_faq` 有产品 FAQ

**需补充**：
- `quotation_clarification` 表

```sql
CREATE TABLE IF NOT EXISTS quotation_clarification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_no TEXT NOT NULL,
    question_type TEXT NOT NULL,            -- customer_question / internal_confirm
    question TEXT NOT NULL,
    suggested_answer TEXT,
    responsible_role TEXT,                  -- sales / commerce / tech / finance
    status TEXT DEFAULT 'pending',
    answer TEXT,
    answered_by TEXT,
    answered_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**追问模板（基础版规则）**：

| 缺口类型 | 追问客户 | 内部确认 |
|---|---|---|
| 库存不足 | "需求 20 台，当前可用 12 台，是否可以分批发货？" | 商务：确认补货周期 |
| 无价格 | "该产品暂无标准报价，是否可以先提供预算区间？" | 商务：确认价格策略 |
| 无折扣政策 | — | 商务：确认客户级别与折扣权限 |
| 定制需求 | "是否需要现场部署、培训、延保？" | 技术：确认交付方案 |
| 竞品提及 | "您提到的竞品是哪一家？方便我们针对性对比。" | 销售：调取竞品资料 |

**接口**：
```text
POST /api/quotations/clarifications/generate
Body: { card_no }
```

**落地动作**：
销售在页面看到追问清单，逐条标记状态。客户回答后回写 `answer` 字段。

---

### Step 5：分流派单

**目标**：根据需求类型和缺口，把报价任务分流到合适的处理人或数字员工。

**当前已有能力**：
- 四类数字员工：财务/商务/销售/技术
- `UserContext` 有 role 和 department

**分流规则**：

| 需求特征 | 主处理人 | 协同 | 数字员工 |
|---|---|---|---|
| 标准产品、有价格、有库存 | 销售助理 | — | 销售助理自动生成报价草稿 |
| 库存不足或价格缺失 | 商务助理 | 销售 | 商务助理确认补货/价格策略 |
| 有定制需求（部署、培训） | 技术助理 | 商务 | 技术助理生成交付方案 |
| 大客户、折扣超权限 | 财务助理 | 商务+销售 | 财务助理校验预算与利润 |
| 涉及竞品对比 | 销售助理 | 技术 | 统一知识检索竞品资料 |

**需补充**：
- `quotation_task` 表

```sql
CREATE TABLE IF NOT EXISTS quotation_task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_no TEXT UNIQUE NOT NULL,           -- QT-20260624-XXXXXX
    card_no TEXT NOT NULL,
    task_type TEXT NOT NULL,                -- sales_quote / commerce_review / tech_solution / finance_approval
    assigned_to TEXT,                       -- user_id 或 assistant 类型
    assigned_role TEXT,                     -- sales / commerce / tech / finance
    status TEXT DEFAULT 'pending',          -- pending / in_progress / completed / rejected
    due_date TEXT,
    result_json TEXT,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**接口**：
```text
POST /api/quotations/tasks/dispatch
Body: { card_no }
```

**落地动作**：
系统根据缺口自动创建 task 记录。销售在页面看到任务看板：
```text
[销售助理] 生成报价草稿      → 待处理
[商务助理] 确认库存与价格    → 待处理
[技术助理] 确认交付方案      → 已跳过（无定制需求）
```

---

### Step 6：调历史案例

**目标**：检索历史相似报价单，为新报价提供参考。

**当前已有能力**：
- `quotation_header` / `quotation_line` 已有历史报价记录
- `knowledge_chunk_fts` 全文检索

**需补充**：
- 新增 `source_type='historical_quotation'` 的知识切片
- 每次生成报价单后，自动把关键信息切片入库

```sql
-- 已有能力，只需在生成报价单后补充写入
INSERT INTO knowledge_chunk (source_type, source_id, title, chunk_text, tags)
VALUES (
    'historical_quotation',
    quotation_no,
    title,
    chunk_text,  -- 包含客户、产品、数量、折扣、金额
    '历史报价,商务助理'
);
```

**检索逻辑**：
```text
POST /api/knowledge/search
Body: {
    query: "{product_name} {customer_level} 报价",
    filters: { source_type: "historical_quotation" }
}
```

**落地动作**：
销售助理生成报价草稿前，自动检索历史相似报价，页面展示：
```text
📚 历史参考
- 2026-05-15：XX 客户采购 15 台，折扣 0.92，单价 14.72
- 2026-04-20：YY 客户采购 10 台，折扣 0.95，单价 15.20
```

---

### Step 7：生成内部方案初稿

**目标**：基于需求卡、缺口补齐结果、历史案例，生成内部技术/商务方案。

**当前已有能力**：
- `quotation_task` 记录任务
- `product_spec` / `product_faq` / `product_document` 产品资料
- `knowledge_chunk` 知识检索

**需补充**：
- `quotation_internal_proposal` 表

```sql
CREATE TABLE IF NOT EXISTS quotation_internal_proposal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_no TEXT UNIQUE NOT NULL,       -- QP-20260624-XXXXXX
    card_no TEXT NOT NULL,
    proposal_type TEXT,                     -- technical / commercial / combined
    proposal_markdown TEXT,                 -- 方案正文
    included_products TEXT,                 -- JSON 数组
    delivery_plan TEXT,                     -- 交付计划
    risk_assessment TEXT,                   -- 风险评估
    estimated_cost REAL,                    -- 预估成本
    estimated_profit REAL,                  -- 预估利润
    status TEXT DEFAULT 'draft',
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**生成逻辑（基础版）**：
1. 从 `product_document` 拉取部署手册 → 生成交付计划
2. 从 `product_spec` 拉取参数 → 生成技术规格说明
3. 从 `quotation_policy` 拉取折扣 → 生成商务策略建议
4. 从 `knowledge_chunk` 检索竞品 → 生成竞争策略

**接口**：
```text
POST /api/quotations/proposal/generate
Body: { card_no }
```

**落地动作**：
技术助理/商务助理页面展示方案初稿，支持编辑。

---

### Step 8：生成报价草稿

**目标**：基于内部方案，生成正式报价草稿。

**当前已有能力**：
- `generate_quotation()` 已有报价生成逻辑
- `quotation_header` / `quotation_line` 表

**需补充**：
- 报价草稿与需求卡关联
- 支持多产品、多折扣策略

```sql
-- 已有表，只需扩展关联
ALTER TABLE quotation_header ADD COLUMN card_no TEXT;
ALTER TABLE quotation_header ADD COLUMN proposal_no TEXT;
ALTER TABLE quotation_header ADD COLUMN version INTEGER DEFAULT 1;
```

**接口**：
```text
POST /api/quotations/generate
Body: {
    customer_code,
    items: [{ product_code, qty }],
    card_no,           -- 关联需求卡
    proposal_no,       -- 关联内部方案
    created_by
}
```

**落地动作**：
销售助理点击"生成报价草稿"，系统：
1. 从 `product_price` 取最新 active 价格
2. 从 `quotation_policy` 匹配最优折扣
3. 从 `inventory` 校验库存
4. 生成 `quotation_header` + `quotation_line`
5. 返回 Markdown 格式的报价单

---

### Step 9：规则校验和审批

**目标**：校验报价是否符合公司政策，触发审批流。

**当前已有能力**：
- `quotation_policy` 有折扣规则
- `UserContext` 有 role

**校验规则**：

| 规则 | 校验内容 | 不通过处理 |
|---|---|---|
| 价格底线 | `unit_price >= product_price * 0.7` | 标记需财务审批 |
| 折扣上限 | `discount_rate >= 0.7` | 标记需商务审批 |
| 库存校验 | `available_quantity >= quantity` | 标记需商务确认 |
| 利润校验 | `final_amount >= estimated_cost * 1.15` | 标记需财务审批 |
| 客户级别匹配 | `customer_level` 与 `quotation_policy` 匹配 | 标记需销售总监审批 |

**需补充**：
- `quotation_approval` 表

```sql
CREATE TABLE IF NOT EXISTS quotation_approval (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_no TEXT NOT NULL,
    approval_type TEXT NOT NULL,            -- price / discount / stock / profit / customer_level
    rule_code TEXT,
    check_result TEXT,                      -- pass / warning / block
    approver_role TEXT,                     -- sales_manager / commerce_manager / finance_manager
    approver_user_id TEXT,
    approval_status TEXT DEFAULT 'pending', -- pending / approved / rejected
    approval_comment TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**接口**：
```text
POST /api/quotations/validate
Body: { quotation_no }

POST /api/quotations/approve
Body: { quotation_no, approval_type, approver_user_id, approval_status, approval_comment }
```

**落地动作**：
系统生成报价草稿后自动跑校验，页面显示：
```text
✅ 价格底线 通过
✅ 折扣上限 通过
⚠️ 库存校验 警告（可用 12 < 需求 20）
✅ 利润校验 通过
```

---

### Step 10：输出客户版本

**目标**：把内部审批通过的报价单，转换为对外客户版本。

**当前已有能力**：
- `quotation_header` / `quotation_line` 有完整数据
- Markdown 输出

**需补充**：
- `quotation_customer_version` 表
- 客户版模板（脱敏、美化）

```sql
CREATE TABLE IF NOT EXISTS quotation_customer_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_no TEXT NOT NULL,
    version_no TEXT NOT NULL,               -- V1 / V2 / ...
    customer_markdown TEXT,                 -- 客户可见版本
    valid_until TEXT,
    terms_and_conditions TEXT,              -- 条款
    contact_info TEXT,
    status TEXT DEFAULT 'active',
    sent_at TEXT,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**客户版 Markdown 模板**：
```markdown
# 商务报价单

**报价单号**：{quotation_no}  
**有效期至**：{valid_until}  

| 产品名称 | 数量 | 单价 | 折扣 | 小计 |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

**合计**：{final_amount} 元

**交付周期**：{delivery_date}
**付款方式**：预付 30%，验收后 70%
**联系人**：{contact_info}
```

**接口**：
```text
POST /api/quotations/customer-version/generate
Body: { quotation_no, version_no, terms_and_conditions, contact_info }
```

**落地动作**：
审批通过后，销售助理点击"生成客户版"，系统生成脱敏 Markdown，可导出 PDF 或发送钉钉。

---

### Step 11：跟踪变更

**目标**：记录报价单的所有变更历史，支持版本对比。

**当前已有能力**：
- `quotation_header` 有基础字段

**需补充**：
- `quotation_change_log` 表

```sql
CREATE TABLE IF NOT EXISTS quotation_change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_no TEXT NOT NULL,
    version_from INTEGER,
    version_to INTEGER,
    change_type TEXT,                       -- price_change / quantity_change / discount_change / product_change / terms_change
    change_desc TEXT,
    changed_by TEXT,
    changed_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**触发点**：
- 每次修改 `quotation_line` 的 `unit_price` / `quantity` / `discount_rate`
- 每次修改 `quotation_header` 的 `valid_until` / `terms`

**接口**：
```text
GET /api/quotations/{quotation_no}/changelog
```

**落地动作**：
销售页面展示变更历史：
```text
V1 → V2：单价从 16.00 调整为 15.20（折扣从 0.90 调整为 0.95）
修改人：张三，2026-06-24 14:30
```

---

### Step 12：回写结果

**目标**：把最终报价结果回写到知识库，形成闭环，供后续检索。

**当前已有能力**：
- `knowledge_chunk` 知识切片
- `blog_article` 博文库

**回写内容**：
1. **历史报价切片**：把 `quotation_header` + `quotation_line` 关键信息写入 `knowledge_chunk`
   - `source_type = 'historical_quotation'`
   - `chunk_text` = 客户、产品、数量、折扣、金额、交付周期

2. **产品 FAQ 更新**：把客户常见问题写入 `product_faq`
   - 例如："20 台是否有额外折扣？" → 回答

3. **政策优化建议**：如果多次报价突破现有 `quotation_policy`，生成政策优化建议，写入 `quotation_policy` 的 `ext_json`

4. **原始数据归档**：把客户提供的询价原始文件（Excel/PDF）归档到 `原始数据/03-报价库存`

**接口**：
```text
POST /api/quotations/feedback
Body: { quotation_no, customer_feedback, competitor_final_price, won_or_lost }
```

**落地动作**：
报价结束后，销售选择"赢单/输单"，系统自动：
- 更新 `quotation_header.status` = `won` / `lost`
- 写入 `knowledge_chunk`
- 更新 `product_faq`（如有新增 FAQ）
- 归档原始文件

---

## 三、数据流全景图

```text
原始需求 (quotation_request)
    ↓
需求卡 (quotation_requirement_card)
    ↓
缺口分析 (quotation_gap)
    ↓
追问确认 (quotation_clarification)
    ↓
分流派单 (quotation_task)
    ↓
历史案例 (knowledge_chunk FTS 检索)
    ↓
内部方案 (quotation_internal_proposal)
    ↓
报价草稿 (quotation_header + quotation_line)
    ↓
规则校验 (quotation_approval)
    ↓
客户版本 (quotation_customer_version)
    ↓
变更跟踪 (quotation_change_log)
    ↓
回写结果 (knowledge_chunk + product_faq + 原始数据归档)
```

---

## 四、页面交互设计

在现有商务助理页面增加"报价工作流"标签：

```text
┌─────────────────────────────────────────────────────────────┐
│ 商务助理                                                    │
│ [智能问数] [库存查询] [报价辅助] [合同检查] [报价工作流]      │
├─────────────────────────────────────────────────────────────┤
│ 报价工作流：                                                │
│ ① 原始需求池  →  ② 需求卡  →  ③ 缺口分析                   │
│ ④ 追问清单  →  ⑤ 任务看板  →  ⑥ 历史参考                   │
│ ⑦ 内部方案  →  ⑧ 报价草稿  →  ⑨ 规则校验                   │
│ ⑩ 客户版本  →  ⑪ 变更跟踪  →  ⑫ 结果回写                   │
├─────────────────────────────────────────────────────────────┤
│ 当前步骤：③ 缺口分析                                        │
│ ⚠️ 库存不足：需求 20 台，可用 12 台                           │
│ ⚠️ 无竞品资料：客户提及 XX 品牌                               │
│ [标记已解决] [生成追问] [分流派单]                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、与当前方案的衔接点

| 当前已有 | 工作流复用 |
|---|---|
| `product` / `product_price` / `inventory` | Step 3 缺口检测、Step 8 报价生成 |
| `quotation_policy` | Step 3 折扣政策缺口、Step 8 折扣匹配、Step 9 规则校验 |
| `quotation_header` / `quotation_line` | Step 8 报价草稿、Step 11 变更跟踪 |
| `knowledge_chunk` + FTS5 | Step 6 历史案例检索、Step 12 回写结果 |
| `product_faq` | Step 12 FAQ 更新 |
| 原始数据上传中心 | Step 1 接收客户询价文件、Step 12 归档 |
| `/api/chat` 统一路由 | Step 1 自然语言识别报价意图 |
| 四类数字员工 | Step 5 分流派单 |

---

## 六、实施优先级

| 阶段 | 步骤 | 工作量 | 优先级 |
|---|---|---|---|
| Phase 1 | Step 1-2（原始需求 + 需求卡） | 1 天 | P0 |
| Phase 1 | Step 8（报价草稿，基于现有能力扩展） | 0.5 天 | P0 |
| Phase 2 | Step 3-4（缺口 + 追问） | 1 天 | P1 |
| Phase 2 | Step 9（规则校验） | 1 天 | P1 |
| Phase 3 | Step 5（分流派单） | 0.5 天 | P2 |
| Phase 3 | Step 6（历史案例） | 0.5 天 | P2 |
| Phase 4 | Step 7（内部方案） | 1 天 | P3 |
| Phase 4 | Step 10（客户版本） | 0.5 天 | P3 |
| Phase 5 | Step 11-12（变更 + 回写） | 1 天 | P4 |

**总计**：约 7 天，可分 5 个阶段迭代上线。

---

## 七、风险与约束

1. **不脱离当前方案**：所有新增表使用 SQLite，不引入 PostgreSQL/Qdrant
2. **不引入 LLM**：Step 3 缺口检测、Step 4 追问生成使用规则，不依赖本地 Qwen
3. **保持 RBAC**：所有接口复用 `UserContext` 权限校验
4. **向后兼容**：现有 `/api/quotations/generate` 接口保留，新增字段为可选
