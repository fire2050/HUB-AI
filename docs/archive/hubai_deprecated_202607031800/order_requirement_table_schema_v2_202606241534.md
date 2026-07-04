# 订单原始需求单字段与数据库设计 v2.0

> 时间：2026-06-24  
> 所属方案：HubAI 报价工作流 v2.0  
> 当前落库：SQLite `/data/finance_wukong.db`  
> 初始化脚本：`finance-wukong-mvp/scripts/init_hubai_db.py`

---

## 一、定位

订单原始需求单是报价工作流的第一入口，等同于“订单 AI 表格”的主表。它不直接生成报价，而是先把客户的原始需求接住、归档、摘要、抽取和确认。

核心原则：

```text
客户原始输入先入表
AI 做整理、抽取、判断
人工只确认真实性和负责人
确认后再进入需求卡/缺口发现/报价工作流
```

---

## 二、最低必备字段

用户明确要求原始需求单至少包含以下字段，当前均已落库：

| 必备字段 | 数据库字段 | 当前状态 |
|---|---|---|
| 客户名称 | `customer_name` | 已有 |
| 联系人 | `customer_contact_name` | 已有 |
| 来源渠道 | `source_channel` | 已有 |
| 原始需求内容 | `raw_requirement` | 已有 |
| 附件 / 图片 / 文件链接 | `attachment_links` | 已新增 |
| 需求进入时间 | `entered_at` | 已新增 |
| 销售负责人 | `sales_owner_user_id` | 已新增 |
| 客户期望时间 | `customer_expected_time` | 已新增 |
| 当前是否紧急 | `is_urgent` | 已新增 |
| 是否已有历史项目 | `has_historical_project` | 已新增 |

---

## 三、AI 在本步骤做 4 件事

### 1. 整理原始内容摘要

| 内容 | 数据库字段 |
|---|---|
| AI 整理后的摘要 | `ai_summary` |
| 人工可编辑摘要 | `requirement_summary` |

示例：

```text
客户希望在月底前采购一批无影云教室产品，用于学校 AI 教室建设，预算约 20 万，需要确认型号、数量和交付周期。
```

### 2. 列出客户发来的材料清单

| 内容 | 数据库字段 |
|---|---|
| 附件/图片/文件链接原始列表 | `attachment_links` |
| AI 识别后的材料清单 | `ai_material_list` |

`attachment_links` 示例：

```json
[
  {"type": "image", "name": "客户现场照片.jpg", "url": "..."},
  {"type": "file", "name": "客户需求表.xlsx", "url": "..."},
  {"type": "link", "name": "历史项目链接", "url": "..."}
]
```

`ai_material_list` 示例：

```json
[
  {"type": "image", "summary": "现场机房照片"},
  {"type": "excel", "summary": "客户采购清单，包含数量和预算"}
]
```

### 3. 识别客户提到的产品、服务、数量、时间、预算、场景

| 内容 | 数据库字段 |
|---|---|
| 结构化识别结果 | `ai_extracted_entities` |
| 详细 AI 原始抽取结果 | `ai_extracted_json` |

`ai_extracted_entities` 示例：

```json
{
  "products": ["企业版-AI云教室-图形工作站旗舰型"],
  "services": ["部署", "培训"],
  "quantity": 20,
  "time": "月底前",
  "budget": "20万以内",
  "scenario": "学校 AI 云教室建设"
}
```

同时明细产品落到：

```text
order_requirement_item
```

### 4. 判断需求性质

AI 判断这条需求属于：

```text
repeated      重复需求
old_customer  老客户需求
change        变更需求
new           全新需求
unknown       未知
```

| 内容 | 数据库字段 |
|---|---|
| 需求性质 | `demand_nature` |
| 判断理由 | `demand_nature_reason` |
| 是否已有历史项目 | `has_historical_project` |
| 历史项目引用 | `historical_project_refs` |

判断逻辑：

| 类型 | 判定依据 |
|---|---|
| repeated | 同客户、同产品、同数量、短时间内已有相似需求 |
| old_customer | 客户在 `dim_customer` 或历史报价中存在 |
| change | 原始需求包含“变更、调整、增加、减少、改为”等关键词，或引用历史项目 |
| new | 未找到历史客户/项目/报价记录 |
| unknown | 信息不足，需人工确认 |

---

## 四、人工在本步骤只做 1 件事

人工只确认：

```text
这条需求是否真实有效，以及谁负责继续推进。
```

对应字段：

| 人工动作 | 数据库字段 |
|---|---|
| 是否已人工确认 | `human_validated` |
| 确认状态 | `validation_status` |
| 确认备注 | `validation_comment` |
| 确认人 | `validated_by` |
| 确认时间 | `validated_at` |
| 销售负责人 | `sales_owner_user_id` |
| 下一步推进负责人 | `next_owner_user_id` |

`validation_status` 枚举：

```text
pending    待确认
valid      真实有效
invalid    无效需求
duplicate  重复需求
```

人工确认后：

```text
valid      → 进入需求卡生成
invalid    → 归档，不进入后续流程
duplicate  → 关联历史需求/项目，不重复派单
```

---

## 五、数据库表设计

### 5.1 主表：`order_requirement`

当前已落库，共 64 个字段。

```sql
CREATE TABLE IF NOT EXISTS order_requirement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_no TEXT UNIQUE NOT NULL,
    source_channel TEXT DEFAULT 'web',
    source_ref TEXT,
    attachment_links TEXT,
    entered_at TEXT DEFAULT CURRENT_TIMESTAMP,

    customer_code TEXT,
    customer_name TEXT NOT NULL,
    customer_company TEXT,
    customer_contact_name TEXT,
    customer_contact_phone TEXT,
    customer_contact_email TEXT,
    customer_level TEXT DEFAULT 'standard',
    customer_credit_status TEXT DEFAULT 'unknown',

    raw_requirement TEXT,
    requirement_summary TEXT,
    business_goal TEXT,
    scenario_type TEXT,
    requirement_type TEXT DEFAULT 'unknown',

    required_delivery_date TEXT,
    customer_expected_time TEXT,
    is_urgent INTEGER DEFAULT 0,
    delivery_mode TEXT DEFAULT 'standard',
    delivery_address TEXT,
    payment_terms TEXT DEFAULT 'standard',
    warranty_required TEXT,
    training_required INTEGER DEFAULT 0,
    installation_required INTEGER DEFAULT 0,

    budget_min REAL,
    budget_max REAL,
    budget_text TEXT,
    competitor_info TEXT,
    custom_requirements TEXT,
    special_terms TEXT,
    risk_flags TEXT,
    has_historical_project INTEGER DEFAULT 0,
    historical_project_refs TEXT,

    output_proposal_required INTEGER DEFAULT 0,
    output_quotation_required INTEGER DEFAULT 1,
    output_confirmed INTEGER DEFAULT 0,

    ai_summary TEXT,
    ai_material_list TEXT,
    ai_extracted_json TEXT,
    ai_extracted_entities TEXT,
    ai_confidence_score REAL DEFAULT 0,
    ai_suggested_route TEXT,
    ai_missing_fields TEXT,
    demand_nature TEXT DEFAULT 'unknown',
    demand_nature_reason TEXT,

    human_validated INTEGER DEFAULT 0,
    validation_status TEXT DEFAULT 'pending',
    validation_comment TEXT,
    validated_by TEXT,
    validated_at TEXT,
    sales_owner_user_id TEXT,
    next_owner_user_id TEXT,

    status TEXT DEFAULT 'draft',
    priority TEXT DEFAULT 'normal',
    owner_user_id TEXT,
    created_by TEXT,
    updated_by TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 明细表：`order_requirement_item`

用于承接 AI 从需求中识别出的产品/服务明细。

```sql
CREATE TABLE IF NOT EXISTS order_requirement_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_no TEXT NOT NULL,
    line_no INTEGER DEFAULT 1,
    product_code TEXT,
    product_name TEXT,
    product_category_code TEXT,
    quantity INTEGER DEFAULT 1,
    unit TEXT DEFAULT '套',
    expected_unit_price REAL,
    expected_amount REAL,
    matched_confidence REAL DEFAULT 0,
    item_notes TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## 六、AI 表格字段建议

### 6.1 销售/人工填写区

| 字段 | 控件 | 必填 |
|---|---|---|
| 客户名称 | 文本/客户选择 | 是 |
| 联系人 | 文本 | 是 |
| 来源渠道 | 下拉 | 是 |
| 原始需求内容 | 多行文本 | 是 |
| 附件/图片/文件链接 | 上传/链接列表 | 否 |
| 需求进入时间 | 自动时间 | 自动 |
| 销售负责人 | 人员选择 | 是 |
| 客户期望时间 | 文本/日期 | 是 |
| 当前是否紧急 | 开关 | 是 |
| 是否已有历史项目 | 开关 | 是 |

### 6.2 AI 自动生成区

| 字段 | 控件 | 是否可编辑 |
|---|---|---|
| 原始内容摘要 | 多行文本 | 可编辑 |
| 材料清单 | 列表 | 可编辑 |
| 识别产品/服务/数量/时间/预算/场景 | JSON/结构化列表 | 可编辑 |
| 需求性质 | 单选：重复/老客户/变更/全新/未知 | 可编辑 |
| 判断理由 | 多行文本 | 可编辑 |

### 6.3 人工确认区

| 字段 | 控件 | 必填 |
|---|---|---|
| 是否真实有效 | 单选：有效/无效/重复 | 是 |
| 负责人 | 人员选择 | 是 |
| 确认备注 | 多行文本 | 否 |

---

## 七、当前落地状态

已完成：

- 初始化脚本 `scripts/init_hubai_db.py` 已更新
- 运行数据库已非破坏性迁移，不影响无影产品数据
- 新增字段已验证：`attachment_links`, `entered_at`, `customer_expected_time`, `is_urgent`, `has_historical_project`, `historical_project_refs`, `ai_summary`, `ai_material_list`, `ai_extracted_entities`, `demand_nature`, `human_validated`, `validation_status`, `sales_owner_user_id`, `next_owner_user_id` 等均已存在
- 当前产品数据仍保留：`product=178`

下一步：

- 实现订单原始需求单 Web 子页面
- 实现 `POST /api/order-requirements` 创建接口
- 实现 AI 规则抽取：摘要、材料清单、实体识别、需求性质判断
- 实现人工确认：有效/无效/重复 + 指定负责人
