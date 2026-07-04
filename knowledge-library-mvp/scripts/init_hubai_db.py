from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.db import DB_PATH  # noqa: E402

DDL = """
PRAGMA foreign_keys = ON;

-- 4.1 财务维度表
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

-- 4.2 产品知识库
CREATE TABLE IF NOT EXISTS product_category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_code TEXT UNIQUE NOT NULL,
    category_name TEXT NOT NULL,
    parent_category_code TEXT,
    description TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    category_code TEXT,
    product_type TEXT,                         -- compute / storage / bandwidth / traffic_package / terminal / ai_assistant / disk / network / addon
    product_type_name TEXT,                    -- 计算规格 / 磁盘规格 / 带宽规格 / 流量包 / 终端外设 / AI助手等
    region_scope TEXT,                         -- domestic / international / enterprise / commercial / common
    source_sheet TEXT,                         -- Excel 来源 sheet
    source_row INTEGER,                        -- Excel 来源行号
    brand TEXT,
    model TEXT,
    unit TEXT DEFAULT '套',
    product_config_description TEXT,           -- Excel 产品配置描述 / 描述 / 参数
    short_description TEXT,
    status TEXT DEFAULT 'active',
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_product_code ON product(product_code);
CREATE INDEX IF NOT EXISTS idx_product_category ON product(category_code);
CREATE INDEX IF NOT EXISTS idx_product_type ON product(product_type);
CREATE INDEX IF NOT EXISTS idx_product_source_sheet ON product(source_sheet);
CREATE INDEX IF NOT EXISTS idx_product_region_scope ON product(region_scope);

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
CREATE INDEX IF NOT EXISTS idx_spec_product ON product_spec(product_code);

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
CREATE INDEX IF NOT EXISTS idx_doc_product ON product_document(product_code);
CREATE INDEX IF NOT EXISTS idx_doc_type ON product_document(doc_type);

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
CREATE INDEX IF NOT EXISTS idx_faq_product ON product_faq(product_code);

-- 4.3 报价模块
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
CREATE TABLE IF NOT EXISTS product_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL,
    unit_price REAL NOT NULL,
    currency TEXT DEFAULT 'CNY',
    price_type TEXT DEFAULT 'standard',       -- 1month / 1year / hourly / yearly / package / standard
    billing_period TEXT,                      -- 一个月 / 一年 / 小时 / 年 / 包
    source_sheet TEXT,                        -- Excel 来源 sheet
    source_column TEXT,                       -- Excel 来源价格列
    unit_label TEXT,                          -- 元/月/台、元/小时、元/个流量包等
    valid_from TEXT,
    valid_to TEXT,
    status TEXT DEFAULT 'active',
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_price_product ON product_price(product_code);
CREATE INDEX IF NOT EXISTS idx_price_type ON product_price(price_type);
CREATE INDEX IF NOT EXISTS idx_price_source_sheet ON product_price(source_sheet);

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
CREATE INDEX IF NOT EXISTS idx_inv_product ON inventory(product_code);

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
CREATE INDEX IF NOT EXISTS idx_qh_no ON quotation_header(quotation_no);
CREATE INDEX IF NOT EXISTS idx_ql_no ON quotation_line(quotation_no);

-- 4.3.1 订单需求表 / AI 表格入口
CREATE TABLE IF NOT EXISTS order_requirement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_no TEXT UNIQUE NOT NULL,          -- OR-20260624-XXXXXX
    source_channel TEXT DEFAULT 'web',            -- web / dingtalk / email / phone / import
    source_ref TEXT,                              -- 原始消息ID/上传文件路径/AI表格行ID
    attachment_links TEXT,                        -- JSON array: 附件/图片/文件链接
    entered_at TEXT DEFAULT CURRENT_TIMESTAMP,    -- 需求进入时间

    -- 客户信息
    customer_code TEXT,
    customer_name TEXT NOT NULL,
    customer_company TEXT,
    customer_contact_name TEXT,
    customer_contact_phone TEXT,
    customer_contact_email TEXT,
    customer_level TEXT DEFAULT 'standard',       -- standard / vip / strategic / new
    customer_credit_status TEXT DEFAULT 'unknown',-- good / normal / risky / unknown

    -- 需求摘要
    raw_requirement TEXT,                         -- 客户原始表达
    requirement_summary TEXT,                     -- AI/销售整理后的摘要
    business_goal TEXT,                           -- 客户目标：建设云教室/替换桌面/扩容等
    scenario_type TEXT,                           -- education / office / design / training / other
    requirement_type TEXT DEFAULT 'unknown',      -- standard / solution / custom / risky / unknown

    -- 交付与商务条款
    required_delivery_date TEXT,
    customer_expected_time TEXT,                  -- 客户期望时间（原始表达）
    is_urgent INTEGER DEFAULT 0,                  -- 当前是否紧急
    delivery_mode TEXT DEFAULT 'standard',        -- standard / urgent / phased / onsite
    delivery_address TEXT,
    payment_terms TEXT DEFAULT 'standard',        -- standard / prepay_30 / prepay_50 / net_30 / net_60 / custom
    warranty_required TEXT,
    training_required INTEGER DEFAULT 0,
    installation_required INTEGER DEFAULT 0,

    -- 预算、竞品与特殊要求
    budget_min REAL,
    budget_max REAL,
    budget_text TEXT,
    competitor_info TEXT,
    custom_requirements TEXT,
    special_terms TEXT,
    risk_flags TEXT,                              -- JSON array: low_margin/short_delivery/credit_risk/big_commitment/over_discount
    has_historical_project INTEGER DEFAULT 0,     -- 是否已有历史项目
    historical_project_refs TEXT,                 -- JSON array: 历史项目/报价/案例引用

    -- 输出选择
    output_proposal_required INTEGER DEFAULT 0,
    output_quotation_required INTEGER DEFAULT 1,
    output_confirmed INTEGER DEFAULT 0,

    -- AI 辅助字段
    ai_summary TEXT,                              -- AI 整理的原始内容摘要
    ai_material_list TEXT,                        -- JSON array: 客户发来的材料清单
    ai_extracted_json TEXT,                       -- AI 结构化抽取结果
    ai_extracted_entities TEXT,                   -- JSON: 产品/服务/数量/时间/预算/场景
    ai_confidence_score REAL DEFAULT 0,
    ai_suggested_route TEXT,
    ai_missing_fields TEXT,
    demand_nature TEXT DEFAULT 'unknown',         -- repeated/old_customer/change/new/unknown
    demand_nature_reason TEXT,

    -- 人工确认
    human_validated INTEGER DEFAULT 0,            -- 人工是否确认真实有效
    validation_status TEXT DEFAULT 'pending',     -- pending/valid/invalid/duplicate
    validation_comment TEXT,
    validated_by TEXT,
    validated_at TEXT,
    sales_owner_user_id TEXT,                     -- 销售负责人
    next_owner_user_id TEXT,                      -- 继续推进负责人

    -- 工作流状态
    status TEXT DEFAULT 'draft',                  -- draft/submitted/card_generated/routed/quoting/approved/output_sent/completed/cancelled
    priority TEXT DEFAULT 'normal',               -- low/normal/high/urgent
    owner_user_id TEXT,
    created_by TEXT,
    updated_by TEXT,
    ext_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_order_req_no ON order_requirement(requirement_no);
CREATE INDEX IF NOT EXISTS idx_order_req_status ON order_requirement(status);
CREATE INDEX IF NOT EXISTS idx_order_req_customer ON order_requirement(customer_code, customer_name);
CREATE INDEX IF NOT EXISTS idx_order_req_type ON order_requirement(requirement_type);
CREATE INDEX IF NOT EXISTS idx_order_req_owner ON order_requirement(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_order_req_sales_owner ON order_requirement(sales_owner_user_id);
CREATE INDEX IF NOT EXISTS idx_order_req_entered ON order_requirement(entered_at);
CREATE INDEX IF NOT EXISTS idx_order_req_validation ON order_requirement(validation_status);
CREATE INDEX IF NOT EXISTS idx_order_req_nature ON order_requirement(demand_nature);

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
CREATE INDEX IF NOT EXISTS idx_order_req_item_req ON order_requirement_item(requirement_no);
CREATE INDEX IF NOT EXISTS idx_order_req_item_product ON order_requirement_item(product_code);

-- 4.4 博文数据库
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
CREATE INDEX IF NOT EXISTS idx_blog_code ON blog_article(article_code);
CREATE INDEX IF NOT EXISTS idx_blog_series ON blog_article(series_no);
CREATE INDEX IF NOT EXISTS idx_blog_status ON blog_article(status);

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

-- 4.5 知识切片与全文检索
CREATE TABLE IF NOT EXISTS knowledge_chunk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
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
CREATE INDEX IF NOT EXISTS idx_chunk_source ON knowledge_chunk(source_type, source_id);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunk_fts USING fts5(
    chunk_text,
    title,
    source_type,
    source_id,
    content='knowledge_chunk',
    content_rowid='id'
);

-- 触发器：保持 FTS 同步
CREATE TRIGGER IF NOT EXISTS knowledge_chunk_ai AFTER INSERT ON knowledge_chunk BEGIN
  INSERT INTO knowledge_chunk_fts(rowid, chunk_text, title, source_type, source_id)
  VALUES (NEW.id, NEW.chunk_text, NEW.title, NEW.source_type, NEW.source_id);
END;
CREATE TRIGGER IF NOT EXISTS knowledge_chunk_ad AFTER DELETE ON knowledge_chunk BEGIN
  INSERT INTO knowledge_chunk_fts(knowledge_chunk_fts, rowid, chunk_text, title, source_type, source_id)
  VALUES ('delete', OLD.id, OLD.chunk_text, OLD.title, OLD.source_type, OLD.source_id);
END;
CREATE TRIGGER IF NOT EXISTS knowledge_chunk_au AFTER UPDATE ON knowledge_chunk BEGIN
  INSERT INTO knowledge_chunk_fts(knowledge_chunk_fts, rowid, chunk_text, title, source_type, source_id)
  VALUES ('delete', OLD.id, OLD.chunk_text, OLD.title, OLD.source_type, OLD.source_id);
  INSERT INTO knowledge_chunk_fts(rowid, chunk_text, title, source_type, source_id)
  VALUES (NEW.id, NEW.chunk_text, NEW.title, NEW.source_type, NEW.source_id);
END;
"""


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(DDL)

    # Non-destructive migration: add new columns to existing product / product_price tables
    migrator = conn.cursor()
    existing_product = {r[1] for r in migrator.execute("PRAGMA table_info(product)")}
    product_additions = {
        "product_type": "TEXT DEFAULT 'compute'",
        "product_type_name": "TEXT DEFAULT ''",
        "region_scope": "TEXT DEFAULT 'domestic'",
        "source_sheet": "TEXT DEFAULT ''",
        "source_row": "INTEGER DEFAULT 0",
        "product_config_description": "TEXT DEFAULT ''",
    }
    for col_name, col_def in product_additions.items():
        if col_name not in existing_product:
            try:
                migrator.execute(f"ALTER TABLE product ADD COLUMN {col_name} {col_def}")
                print(f"  product.{col_name} ADDED")
            except Exception as e:
                print(f"  product.{col_name} SKIP ({e})")

    existing_price = {r[1] for r in migrator.execute("PRAGMA table_info(product_price)")}
    price_additions = {
        "billing_period": "TEXT DEFAULT ''",
        "source_sheet": "TEXT DEFAULT ''",
        "source_column": "TEXT DEFAULT ''",
        "unit_label": "TEXT DEFAULT ''",
    }
    for col_name, col_def in price_additions.items():
        if col_name not in existing_price:
            try:
                migrator.execute(f"ALTER TABLE product_price ADD COLUMN {col_name} {col_def}")
                print(f"  product_price.{col_name} ADDED")
            except Exception as e:
                print(f"  product_price.{col_name} SKIP ({e})")

    # Non-destructive migration: project requirement quotation M1 schema
    def _add_columns(table, additions):
        existing = {r[1] for r in migrator.execute(f"PRAGMA table_info({table})")}
        for col_name, col_def in additions.items():
            if col_name not in existing:
                try:
                    migrator.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                    print(f"  {table}.{col_name} ADDED")
                except Exception as e:
                    print(f"  {table}.{col_name} SKIP ({e})")

    order_requirement_additions = {
        "project_name": "TEXT",
        "project_background": "TEXT",
        "product_line": "TEXT DEFAULT 'wuying-pc'",
        "deployment_scale": "TEXT",
        "usage_scenario": "TEXT",
        "duration_type": "TEXT",
        "performance_level": "TEXT",
        "sleep_policy": "TEXT",
        "device_type": "TEXT",
        "cloud_storage": "TEXT",
        "data_security": "TEXT",
    }
    _add_columns("order_requirement", order_requirement_additions)
    order_requirement_item_additions = {
        "duration_type": "TEXT",
        "performance_level": "TEXT",
        "sleep_policy": "TEXT",
        "device_type": "TEXT",
    }
    _add_columns("order_requirement_item", order_requirement_item_additions)
    card_additions = {
        "entry_id": "TEXT",
        "missing_fields": "TEXT",
        "gap_summary": "TEXT",
        "gap_count": "INTEGER DEFAULT 0",
        "clarification_list": "TEXT",
        "suggested_route": "TEXT",
        "output_types": "TEXT",
        "status": "TEXT DEFAULT 'draft'",
        "created_by": "TEXT",
    }
    _add_columns("quotation_requirement_card", card_additions)
    migrator.executescript("""
        CREATE INDEX IF NOT EXISTS idx_order_req_product_line ON order_requirement(product_line);
        CREATE INDEX IF NOT EXISTS idx_order_req_duration_type ON order_requirement(duration_type);
        CREATE INDEX IF NOT EXISTS idx_order_req_item_duration ON order_requirement_item(duration_type);
        CREATE INDEX IF NOT EXISTS idx_req_card_req ON quotation_requirement_card(requirement_no);
        CREATE INDEX IF NOT EXISTS idx_req_card_status ON quotation_requirement_card(status);
    """)
    conn.commit()

    conn.close()
    print(f"HubAI base database initialized: {DB_PATH}")


if __name__ == "__main__":
    main()
