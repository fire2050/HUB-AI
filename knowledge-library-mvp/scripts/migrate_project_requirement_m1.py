from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DBS = [PROJECT_ROOT / "finance_wukong.db", PROJECT_ROOT / "hubai_quotes.db"]

ORDER_REQUIREMENT_COLUMNS = {
    "source_ref": "TEXT",
    "attachment_links": "TEXT",
    "entered_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
    "customer_code": "TEXT",
    "customer_name": "TEXT",
    "customer_company": "TEXT",
    "customer_contact_name": "TEXT",
    "customer_contact_phone": "TEXT",
    "customer_contact_email": "TEXT",
    "customer_level": "TEXT DEFAULT 'standard'",
    "customer_credit_status": "TEXT DEFAULT 'unknown'",
    "raw_requirement": "TEXT",
    "requirement_summary": "TEXT",
    "business_goal": "TEXT",
    "scenario_type": "TEXT",
    "requirement_type": "TEXT DEFAULT 'unknown'",
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
    "required_delivery_date": "TEXT",
    "customer_expected_time": "TEXT",
    "is_urgent": "INTEGER DEFAULT 0",
    "delivery_mode": "TEXT DEFAULT 'standard'",
    "delivery_address": "TEXT",
    "payment_terms": "TEXT DEFAULT 'standard'",
    "warranty_required": "TEXT",
    "training_required": "INTEGER DEFAULT 0",
    "installation_required": "INTEGER DEFAULT 0",
    "budget_min": "REAL",
    "budget_max": "REAL",
    "budget_text": "TEXT",
    "competitor_info": "TEXT",
    "custom_requirements": "TEXT",
    "special_terms": "TEXT",
    "risk_flags": "TEXT",
    "has_historical_project": "INTEGER DEFAULT 0",
    "historical_project_refs": "TEXT",
    "output_proposal_required": "INTEGER DEFAULT 0",
    "output_quotation_required": "INTEGER DEFAULT 1",
    "output_confirmed": "INTEGER DEFAULT 0",
    "ai_summary": "TEXT",
    "ai_material_list": "TEXT",
    "ai_extracted_json": "TEXT",
    "ai_extracted_entities": "TEXT",
    "ai_confidence_score": "REAL DEFAULT 0",
    "ai_suggested_route": "TEXT",
    "ai_missing_fields": "TEXT",
    "demand_nature": "TEXT DEFAULT 'unknown'",
    "demand_nature_reason": "TEXT",
    "human_validated": "INTEGER DEFAULT 0",
    "validation_status": "TEXT DEFAULT 'pending'",
    "validation_comment": "TEXT",
    "validated_by": "TEXT",
    "validated_at": "TEXT",
    "sales_owner_user_id": "TEXT",
    "next_owner_user_id": "TEXT",
    "status": "TEXT DEFAULT 'draft'",
    "priority": "TEXT DEFAULT 'normal'",
    "owner_user_id": "TEXT",
    "created_by": "TEXT",
    "updated_by": "TEXT",
    "ext_json": "TEXT",
    "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
}

ORDER_REQUIREMENT_ITEM_COLUMNS = {
    "line_no": "INTEGER DEFAULT 1",
    "product_code": "TEXT",
    "product_name": "TEXT",
    "product_category_code": "TEXT",
    "quantity": "INTEGER DEFAULT 1",
    "unit": "TEXT DEFAULT '套'",
    "duration_type": "TEXT",
    "performance_level": "TEXT",
    "sleep_policy": "TEXT",
    "device_type": "TEXT",
    "expected_unit_price": "REAL",
    "expected_amount": "REAL",
    "matched_confidence": "REAL DEFAULT 0",
    "item_notes": "TEXT",
    "ext_json": "TEXT",
    "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
}

CARD_COLUMNS = {
    "requirement_no": "TEXT",
    "entry_id": "TEXT",
    "completeness_score": "INTEGER DEFAULT 0",
    "missing_fields": "TEXT",
    "gap_summary": "TEXT",
    "gap_count": "INTEGER DEFAULT 0",
    "clarification_list": "TEXT",
    "suggested_route": "TEXT",
    "route_reason": "TEXT",
    "output_types": "TEXT",
    "status": "TEXT DEFAULT 'draft'",
    "created_by": "TEXT",
    "ext_json": "TEXT",
    "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
}


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS order_requirement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requirement_no TEXT UNIQUE NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS order_requirement_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requirement_no TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS quotation_requirement_card (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_no TEXT UNIQUE NOT NULL
        )
        """
    )


def add_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> list[str]:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    added: list[str] = []
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
            added.append(f"{table}.{name}")
    return added


def create_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_order_req_no ON order_requirement(requirement_no);
        CREATE INDEX IF NOT EXISTS idx_order_req_status ON order_requirement(status);
        CREATE INDEX IF NOT EXISTS idx_order_req_customer ON order_requirement(customer_code, customer_name);
        CREATE INDEX IF NOT EXISTS idx_order_req_type ON order_requirement(requirement_type);
        CREATE INDEX IF NOT EXISTS idx_order_req_product_line ON order_requirement(product_line);
        CREATE INDEX IF NOT EXISTS idx_order_req_duration_type ON order_requirement(duration_type);
        CREATE INDEX IF NOT EXISTS idx_order_req_owner ON order_requirement(owner_user_id);
        CREATE INDEX IF NOT EXISTS idx_order_req_sales_owner ON order_requirement(sales_owner_user_id);
        CREATE INDEX IF NOT EXISTS idx_order_req_entered ON order_requirement(entered_at);
        CREATE INDEX IF NOT EXISTS idx_order_req_validation ON order_requirement(validation_status);
        CREATE INDEX IF NOT EXISTS idx_order_req_nature ON order_requirement(demand_nature);
        CREATE INDEX IF NOT EXISTS idx_order_req_item_req ON order_requirement_item(requirement_no);
        CREATE INDEX IF NOT EXISTS idx_order_req_item_product ON order_requirement_item(product_code);
        CREATE INDEX IF NOT EXISTS idx_order_req_item_duration ON order_requirement_item(duration_type);
        CREATE INDEX IF NOT EXISTS idx_req_card_req ON quotation_requirement_card(requirement_no);
        CREATE INDEX IF NOT EXISTS idx_req_card_status ON quotation_requirement_card(status);
        """
    )


def migrate(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        added = []
        added += add_columns(conn, "order_requirement", ORDER_REQUIREMENT_COLUMNS)
        added += add_columns(conn, "order_requirement_item", ORDER_REQUIREMENT_ITEM_COLUMNS)
        added += add_columns(conn, "quotation_requirement_card", CARD_COLUMNS)
        create_indexes(conn)
        conn.commit()
        return {"db": str(db_path), "added": added, "added_count": len(added)}
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate HubAI project requirement quotation M1 schema")
    parser.add_argument("db", nargs="*", type=Path, help="SQLite DB paths; default finance_wukong.db + hubai_quotes.db")
    args = parser.parse_args()
    paths = args.db or DEFAULT_DBS
    for path in paths:
        if path.exists():
            print(migrate(path))
        else:
            print({"db": str(path), "skipped": "not_exists"})


if __name__ == "__main__":
    main()
