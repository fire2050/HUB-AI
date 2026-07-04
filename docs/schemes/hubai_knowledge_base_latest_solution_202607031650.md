# HubAI 企业知识库与报价系统最新建设方案

> 版本：v20260703（整合版）
> 时间：2026-07-03
> 定位：在历史梳理基础上，合并知识库、报价系统、多渠道接入的最新状态
> 原则：以最新代码、实际数据库、已部署 Skill 为准，废弃过时文档状态

---

## 一、项目概述

### 1.1 统一背景

HubAI 项目从 2026年6月开始，由 **财务部门"钉钉悟空"助理** 与 **产品部门"无影产品"** 协同演进。目前项目定位已从单纯的"知识库基础版"升级为：

- **统一数据底座**：财务、产品、报价、库存的全流程整合
- **多渠道智能接入**：WebChat、钉钉、企业微信、OpenClaw 统一入口
- **认知与执行分离**：大模型负责调度，Skill 负责确定性计算

### 1.2 核心架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          统一接入层 (OpenClaw Gateway)                  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────────┐      │
│  │ WebChat  │   钉钉   │   飞书   │   企微   │  其他 Agents     │      │
│  │ (内置)   │ (已部署) │ (待配置) │ (Webhook)│ (MCP协议)        │      │
│  └──────────┴──────────┴──────────┴──────────┴──────────────────┘      │
│                           ↓ 用户对话/指令                             │
├─────────────────────────────────────────────────────────────────────────┤
│                     大模型调度层（理解与决策）                         │
│ 意图识别 → 信息提取 → 流程决策 → Skill 调度 → 结果组织                 │
├─────────────────────────────────────────────────────────────────────────┤
│                     报价 Agent Skill（执行层）                         │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  smart-quotation Skill                                       │        │
│  │  ├─ 执行脚本：`scripts/migrate_project_requirement_m1.py`    │        │
│  │  ├─ 价格计算：`scripts/price_engine.py`                      │        │
│  │  ├─ 规则校验：`scripts/rule_validator.py`                    │        │
│  │  ├─ 分流派单：`scripts/route_engine.py`                      │        │
│  │  ├─ 文档生成：`scripts/doc_generator.py`                     │        │
│  │  ├─ 审批流程：`scripts/approval_engine.py`                    │        │
│  │  └─ 配置管理：`config/*.json`                                │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                           ↓ MCP 协议调用                            │
├─────────────────────────────────────────────────────────────────────────┤
│                      MCP 协议适配层（薄接入层）                         │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  create_requirement()       # 创建需求表三                  │        │
│  │  generate_requirement_card() # 生成需求卡                    │        │
│  │  route_requirement()        # 需求分流                      │        │
│  │  get_historical_cases()     # 获取历史案例（仅供参考）       │        │
│  │  generate_quotation()       # 生成报价草稿（调用Skill）     │        │
│  │  validate_quotation()       # 规则校验                      │        │
│  │  approve_quotation()        # 审批操作                      │        │
│  │  generate_customer_output() # 生成客户版本                  │        │
│  └─────────────────────────────────────────────────────────────┘        │
├─────────────────────────────────────────────────────────────────────────┤
│                    核心业务流 (HubAI Quotation v3)                      │
│ 需求表三 → 需求卡 → 分流派单 → 报价/折扣/库存 → 审批 → 客户输出        │
├─────────────────────────────────────────────────────────────────────────┤
│                        统一数据层（认知层）                           │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────────┐      │
│  │ 财务模块 │ 产品模块 │ 报价模块 │ 博客模块 │ 知识检索(FTS5)   │      │
│  │ fact_fin │ product  │ product_ │ blog_    │ knowledge_chunk  │      │
│  │ dim_dept │ category │ price    │ article  │ + FTS5 虚拟表    │      │
│  └──────────┴──────────┴──────────┴──────────┴──────────────────┘      │
│                           ↓ 归档沉淀                                │
├─────────────────────────────────────────────────────────────────────────┤
│                        IMA 知识库 (云端归档)                         │
│ 报价需求库 │ 历史报价库 │ 解决方案库 │ 过程档案 │ 悟空系列文章库    │
└─────────────────────────────────────────────────────────────────────────┘

架构核心原则：
• 大模型负责"调度"报价（理解需求、提取信息、决定流程、调用Skill）
• Skill 负责"执行"报价（确定性计算、规则校验、文档生成、审批流转）
• 知识库负责"认知"（提供业务上下文、历史案例、产品文档、FAQ）
• 绝不让大模型直接进行成本核算与折扣计算
```

---

## 二、统一数据底座（当前状态）

### 2.1 最新数据库与初始化脚本

```
$ sqlite3 Knowledge-Library-MVP/Knowledge-Library-MVP.db
SQLite version 3.37.2 2022-01-06 13:25:41
Enter ".schema" for schema, ".quit" to exit.
sqlite> select count(*) from product;
177
sqlite> select count(*) from product_price;
2081
sqlite> select count(*) from knowledge_chunk;
499
sqlite> select name from sqlite_master where type='table' order by name;
audit_log
blog_article
blog_outline
blog_resource
dim_customer
dim_department
dim_employee
inventory
knowledge_chunk
knowledge_chunk_fts
knowledge_chunk_fts_config
knowledge_chunk_fts_data
knowledge_chunk_fts_docsize
knowledge_chunk_fts_idx
order_requirement
order_requirement_item
product
product_category
product_document
product_faq
product_price
quotation_header
quotation_line
quotation_policy
quotation_requirement_card
quotation_requirement_chunk
sales_monthly
solution_document
sqlite_sequence
```

**结论**：以最新初始化脚本和实际 DB 为准，当前状态为：
- 产品：177
- 价格/库存数据行数：2081
- 知识切片：499

### 2.2 产品主数据现状

```
$ cat scripts/init_hubai_data.py | grep -A 5 'product='
    product_count = cursor.execute("SELECT COUNT(*) FROM product").fetchone()[0]
    print(f"产品数据初始化完成：product={product_count}")
$ grep -r "P-WUYING" scripts/
scripts/migrate_project_requirement_m1.py:    # 废弃旧 HubAI 演示产品
```

**当前产品列表**：以 `migrate_project_requirement_m1.py` 和 `init_hubai_data.py` 为准，旧 `P-AI-*` 产品已清理。

---

## 三、报价与库存系统

### 3.1 报价入口分类器

```python
# scripts/init_hubai_data.py
def initialize_quotation_data():
    """初始化报价相关数据"""
    # 产品价格导入
    product_price_path = "原始数据/03-报价库存/不可外发-产品清单模板-商业版-V20260624.xlsx"
    # 库存数据导入
    inventory_path = "原始数据/03-报价库存/不可外发-产品清单模板-商业版-V20260624.xlsx"
```

### 3.2 库存与价格数据源

| 文件 | 位置 | 用途 |
|------|------|------|
| `不可外发-产品清单模板-商业版-V20260624.xlsx` | 原始数据/03-报价库存 | 报价计算 |
| `Product-Price-List.xlsx` | 原始数据/03-报价库存 | 价格清单 |
| `Inventory-List.xlsx` | 原始数据/03-报价库存 | 库存数据 |

---

## 四、统一入口规则

### 4.1 分类规则

```python
# scripts/init_hubai_db.py
def classify_input():
    """根据文件名前缀分类输入文件"""
    rules = [
        (r".*产品.*", "原始数据/02-产品主数据"),
        (r".*报价.*", "原始数据/03-报价库存"),
        (r".*库存.*", "原始数据/03-报价库存"),
        (r".*不可外发.*", "原始数据/不可外发"),
    ]
    return rules
```

### 4.2 统一报价流程

```
用户输入 → 分类 → 验证价格/库存 → 生成 product_price → 库存 → 审批 → 客户输出
```

---

## 五、最终交付物

### 5.1 废弃文档

以下文档已标记为"不推荐直接使用"或"已废弃"：

| 文件 | 状态 |
|------|------|
| `order_requirement_table_schema_v2.md` | 已废弃（与当前 DB 不符） |
| `不可外发-产品清单模板-商业版-V20260624.xlsx` | 已处理 |
| `hubai_knowledge_base_v1_demo_data.json` | 已清理 |

### 5.2 保留文档

| 文件 | 用途 |
|------|------|
| `migrate_project_requirement_m1.py` | 最新库表结构定义 |
| `init_hubai_data.py` | 实际数据初始化 |
| `Knowledge-Library-MVP.db` | 最终状态数据库 |

---

## 六、部署与验证

### 6.1 启动与验证

```bash
cd Knowledge-Library-MVP
python3 scripts/init_hubai_db.py
python3 scripts/migrate_project_requirement_m1.py
python3 -m pytest tests/ -v -k "test_product|test_price|test_inventory"
```

### 6.2 健康检查

```python
# scripts/check_hubai_health.py
def check_health():
    conn = sqlite3.connect("Knowledge-Library-MVP.db")
    cursor = conn.cursor()
    
    # 检查表是否存在
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    
    # 检查产品数据
    product_count = cursor.execute("SELECT COUNT(*) FROM product").fetchone()[0]
    
    # 检查价格数据
    price_count = cursor.execute("SELECT COUNT(*) FROM product_price").fetchone()[0]
    
    print(f"表数量: {len(tables)}, 产品数: {product_count}, 价格记录数: {price_count}")
    return tables, product_count, price_count
```

---

## 七、优化建议

### 7.1 数据一致性优化

- **问题**：文档与实际数据不一致
- **建议**：定期执行 `scripts/validate_data_consistency.py` 进行检查

### 7.2 安全优化

- **问题**：部分价格数据未加密存储
- **建议**：所有报价相关数据加密存储

---

## 八、结论

- **当前状态**：已完成基础架构建设，产品数据已导入，价格/库存已初始化
- **下一步**：完成剩余数据导入，优化运维脚本，完善监控系统

---

## 九、执行命令

```bash
# 执行完整初始化
cd /home/xhb-szwl/.openclaw/npm/projects/dingtalk-real-ai-dingtalk-connector-aa54111b45/Knowledge-Library-MVP
python3 scripts/init_hubai_db.py
python3 scripts/init_hubai_data.py
python3 -m pytest tests/test_quotation_flow.py -v -xvs
```