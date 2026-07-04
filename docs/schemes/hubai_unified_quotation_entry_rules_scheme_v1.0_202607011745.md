# HubAI 统一报价入口与规则设置方案

> 版本：v1.0
> 时间：2026-07-01
> 定位：基于历史方案（v1.3 统一方案、v3 报价工作流、v3 执行计划、v4 系统规划、项目需求报价建议）和当前代码实现，给出可执行的统一入口与规则配置。
> 原则：数据底座统一、工作流统一、入口统一、历史项目隔离、客户需求表三必经。

---

## 一、历史方案一致性结论

所有历史方案在以下规则上完全一致（见 `hubai_unified_solution_v1.3_202606291723.md` L26-L32、`hubai_quotation_workflow_design_v3_202606250952.md` L35-L68、`hubai_quotation_execution_plan_v3_202606250952.md` L15-L19、`hubai_openclaw_quotation_system_plan_v4_202606251244.md` L69-L75）：

1. **客户需求表三必经**：客户/项目/方案/P0/正式报价必须先完成 `order_requirement`，任何渠道不得绕过。
2. **历史项目仅参考**：历史报价/合同/案例只用于风险提示和辅助判断，不参与定价、折扣、审批规则。
3. **入口统一**：Web/钉钉/飞书/企微/Agent 共用同一套 API，用 `source_channel` + `source_ref` 标识来源。
4. **单品与项目分离**：单品快速查价保留为内部参考；项目需求报价必须走表三→需求卡→分流→校验→审批→客户版。
5. **认知与执行分离**：LLM 负责理解/抽取/追问/调度；Skill/规则引擎负责确定性计算和流程驱动。

---

## 二、统一报价入口分类规则

### 2.1 三类入口（全产品通用）

由 `classify_quotation_entry(message, payload)` 统一判定，当前已在以下位置实现：
- `smart_quotation/scripts/quotation_flow.py`
- `Knowledge-Library-MVP/app/quotation_flow.py`

| 入口类型 | 判定条件 | 处理规则 |
|---|---|---|
| `single_item` | 明确产品编码/配置名称 + 查价/库存/多少钱信号；或泛化报价但附带了较完整产品描述（≥8字） | 直接走单品快速查价，输出内部参考报价，**不进入正式客户报价流程** |
| `requirement_p0` | 命中客户/项目/方案/正式报价/P0/公司/学校/医院/集团/预算/交付/部署/招标/合同/联系人/批量采购等信号；或 payload 含 `customer_name`/`customer_company`/`raw_requirement`/`attachment_links` 等 | 必须先创建/补齐**客户需求表三**，再进入需求卡、分流、规则校验、人工确认、客户版输出 |
| `unclear` | 仅命中泛化"报价/提供报价"，无产品配置信号也无客户项目信号 | **先追问用户确认入口类型**，不得默认单品或项目 |

### 2.2 关键判定优先级

1. **保守原则**：只要有客户/项目/方案/正式输出信号，即使同时包含"价格/报价"，也按 `requirement_p0` 处理。
2. **项目数量联动**：`\d+(人/用户/点/台/套/终端/席) + (项目/客户/部署/交付/公司/学校/医院/集团/预算)` 直接判定为 `requirement_p0`。
3. **泛化报价兜底**："报价/提供报价"单独出现时，必须追问；若同时有较长产品描述（≥8字），可视为 `single_item`。

### 2.3 各渠道映射

| 渠道 | `source_channel` | 入口行为 |
|---|---|---|
| Web 工作台 | `web` | 前端分"单品价格查询"和"客户需求表三"两个模式，单品直接报价，项目必须先保存表三 |
| 钉钉 | `dingtalk` | 消息 → `classify_quotation_entry` → 单品直接查价 / 项目进入表三流程并追问 P0 字段 |
| 飞书 | `feishu` | 同钉钉逻辑，待配置 |
| 企微 | `wecom` | 同钉钉逻辑，Webhook 接入 |
| Agent/其他 | `agent` | 通过 MCP 调用同一套 API，不得单独写表 |
| 邮件/电话/导入 | `email`/`phone`/`import` | 只作为需求来源，统一归档到表三 |

---

## 三、客户需求表三字段配置（统一版）

### 3.1 最低必备字段（已落库）

来源：`order_requirement_table_schema_v2_202606241534.md` L25-L40

| 字段 | 数据库字段 | 必填 |
|---|---|---|
| 客户名称 | `customer_name` / `customer_name_full` | 是 |
| 联系人 | `customer_contact_name` | 是 |
| 联系方式 | `customer_contact_phone` / `customer_contact_email` | 是（电话/邮箱至少一种） |
| 来源渠道 | `source_channel` | 是 |
| 原始需求内容 | `raw_requirement` | 是 |
| 附件/图片/文件链接 | `attachment_links` | 否 |
| 需求进入时间 | `entered_at` | 自动 |
| 销售负责人 | `sales_owner_user_id` | 否 |
| 客户期望时间 | `customer_expected_time` | 否 |
| 是否紧急 | `is_urgent` | 否（默认0） |
| 是否已有历史项目 | `has_historical_project` | 否（默认0） |
| 输出类型 | `output_proposal_required` / `output_quotation_required` | 否 |

### 3.2 项目报价扩展字段（M1 已新增）

| 类别 | 字段 | 说明 |
|---|---|---|
| 项目信息 | `project_name`, `project_background` | 项目名称与背景 |
| 产品/配置 | `product_line`, `deployment_scale`, `usage_scenario`, `duration_type`, `performance_level`, `sleep_policy`, `device_type`, `cloud_storage`, `data_security` | 支持无影云电脑多规格 |
| 商务条款 | `payment_terms`, `required_delivery_date`, `delivery_mode`, `delivery_address` | 付款/交付 |
| 预算与竞品 | `budget_min`, `budget_max`, `budget_text`, `competitor_info` | 仅用于风险提示 |
| AI 辅助 | `ai_summary`, `ai_extracted_json`, `ai_missing_fields`, `ai_confidence_score`, `ai_suggested_route` | AI 摘要与缺口 |
| 流程状态 | `demand_nature`, `validation_status`, `human_validated`, `status`, `priority` | 分流与确认 |

### 3.3 无影云电脑项目 P0 必问字段

钉钉/对话场景每次追问 **3-5 个字段**，避免消息过长：

1. 客户公司 + 联系人/联系方式
2. 使用场景（办公/设计/教育/研发等）
3. 需求数量（人/台/点位）
4. 云电脑配置 + **时长类型**（120小时/200小时/不限时长1小时休眠/不限时长/教育办公）
5. 合同周期 / 期望交付时间

---

## 四、历史项目规则（统一版）

### 4.1 可做 vs 不可做

| 可做 | 不可做 |
|---|---|
| 检索并展示 Top 3 相似案例 | 直接套用为当前报价规则 |
| 辅助理解客户背景、交付方式、相似产品组合 | 替代当前产品价格表、报价政策、审批规则 |
| 风险提示（历史逾期、投诉点、变更记录） | 自动决定最终报价底价或折扣上限 |
| 写入 `historical_project_refs` 字段 | 参与定价计算或规则引擎条件 |

### 4.2 展示文案

所有含历史参考的输出必须标注：
> **历史项目仅供参考，不作为报价规则。正式报价以当前产品价格、政策、库存和审批结果为准。**

---

## 五、单品查询展示硬规则（无影云电脑）

### 5.1 对话输出限制

- **只展示**：月价 + 一年价
- **禁止展示**：2年、3年、4年、5年、6年价格（即使数据库有，也不得输出）
- **表格格式**：

| 序号 | 价格场景 | 时长类型 | 产品/配置 | 月价 | 一年价 | 计价单位 | 价格策略 |
|---:|---|---|---|---:|---:|---|---|

- **追问时长类型时**：只输出两列（序号 / 时长类型），不得包含内部代码列。

### 5.2 适用位置

- `product-wuying-pc/scripts/price_engine.py`
- `dingtalk-channel-rules/SKILL.md`
- `dingtalk-connector/dist/message-handler-0NLKAqHU.mjs`

---

## 六、数据安全与价格来源优先级

来源：`hubai_quotation_guardrails_v1.0_202606291823.md`

```
P0: 数据库 product_price 表（实时权威）
P1: 产品 Skill 配置文件 config/price.json（静态降级）
P2: 报价策略表 quotation_policy（策略驱动）
P3: ❌ 绝对禁止：大模型估算、经验值、假设值
```

**无数据不报价**：产品不存在/价格缺失/价格过期 → 拒绝报价并提示补充。

---

## 七、钉钉渠道特殊配置

### 7.1 当前实际链路

钉钉消息 → `dingtalk-connector` → `message-handler-0NLKAqHU.mjs` → 前置无影拦截器 → 主 Agent → 回复

### 7.2 前置拦截器规则（需同步统一分类器）

当前前置拦截器直接按关键词匹配无影产品并调用单品引擎，**未复用 `classify_quotation_entry`**。

**建议修复**：
1. 前置拦截器先检查是否含客户/项目/方案/公司/预算/交付/部署/招标/合同等 `requirement_p0` 信号。
2. 若命中，**不进入单品价格引擎**，直接交给主 Agent 走项目需求报价流程。
3. 仅当明确为 `single_item` 时才调用无影单品引擎。

### 7.3 钉钉项目报价话术模板

```
已识别为项目需求报价，需要先进入客户需求表三。

当前已记录：
- 客户：{customer_name}
- 产品线：{product_line}

还需要补齐以下信息（每次回复可补充多项）：
1. 联系人 / 联系方式
2. 使用场景（办公/设计/教育/研发等）
3. 需求数量（人/台/点位）
4. 云电脑配置 + 时长类型
5. 合同周期 / 期望交付时间
6. 预算范围（可选，用于风险提示）
7. 输出类型（仅报价单 / 方案+报价单）
```

---

## 八、核心实现文件清单

| 文件 | 职责 |
|---|---|
| `smart_quotation/scripts/quotation_flow.py` | Skill 层统一入口分类器 |
| `Knowledge-Library-MVP/app/quotation_flow.py` | Web API 层统一入口分类器（与 Skill 层逻辑一致） |
| `product-wuying-pc/scripts/price_engine.py` | 无影云电脑单品/方案价格引擎 |
| `product-wuying-pc/config/requirement.json` | 无影项目需求字段定义（v1.3.0） |
| `smart_quotation/SKILL.md` | 报价核心 Skill 规则文档 |
| `product-wuying-pc/SKILL.md` | 无影产品 Skill 规则文档 |
| `dingtalk-channel-rules/SKILL.md` | 钉钉会话输出硬规则 |
| `dingtalk-connector/dist/message-handler-0NLKAqHU.mjs` | 钉钉实际前置拦截与规则注入 |
| `Knowledge-Library-MVP/app/main.py` | Web API：客户需求表三创建、报价生成 |
| `Knowledge-Library-MVP/scripts/init_hubai_db.py` | 数据库初始化与迁移（含项目需求 M1 字段） |

---

## 九、下一步必须修复的不一致点

1. **钉钉前置拦截器未复用统一分类器**：`message-handler-0NLKAqHU.mjs` 中无影单品拦截器可能将"客户公司 + 明确配置 + 报价"误判为单品查价，绕过客户需求表三。
2. **建议**：在前置拦截器中增加 `requirement_p0` 信号预检，或让拦截器直接调用 `classify_quotation_entry` 判定后再决定是否走单品引擎。

---

*本方案基于 `hubai_unified_solution_v1.3_202606291723.md`、`hubai_quotation_workflow_design_v3_202606250952.md`、`hubai_quotation_execution_plan_v3_202606250952.md`、`hubai_openclaw_quotation_system_plan_v4_202606251244.md`、`hubai_project_requirement_quotation_next_steps_202607011710.md`、`hubai_quotation_guardrails_v1.0_202606291823.md` 归纳统一。*
