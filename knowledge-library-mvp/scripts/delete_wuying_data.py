from __future__ import annotations

import sqlite3
from app.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

wy_codes = [
    r["product_code"]
    for r in cur.execute(
        """
        SELECT product_code FROM product
        WHERE product_code LIKE 'WY-%'
           OR brand = '无影'
           OR category_code LIKE 'CAT_WUYING%'
           OR product_type IN ('compute','storage','bandwidth','traffic_package','terminal','ai_assistant','addon','core_hour_package')
        """
    )
]
print("wy_codes_to_delete", len(wy_codes))

if wy_codes:
    placeholders = ",".join("?" for _ in wy_codes)
    for table in ["product_faq", "product_spec", "product_document", "inventory", "product_price", "quotation_line"]:
        cur.execute(f"DELETE FROM {table} WHERE product_code IN ({placeholders})", wy_codes)
        print(table, cur.rowcount)
    cur.execute(f"DELETE FROM knowledge_chunk WHERE source_id IN ({placeholders})", wy_codes)
    print("knowledge_chunk", cur.rowcount)
    cur.execute(f"DELETE FROM product WHERE product_code IN ({placeholders})", wy_codes)
    print("product", cur.rowcount)

cur.execute("DELETE FROM product_category WHERE category_code LIKE 'CAT_WUYING%'")
print("product_category", cur.rowcount)
cur.execute("DELETE FROM quotation_policy WHERE policy_code LIKE 'POL-WUYING%' OR policy_name LIKE '%无影%'")
print("quotation_policy", cur.rowcount)

conn.commit()

# Rebuild/clear FTS shadow content safely by deleting all product_doc residue if any.
try:
    cur.execute("INSERT INTO knowledge_chunk_fts(knowledge_chunk_fts) VALUES('optimize')")
    conn.commit()
except Exception as e:
    print("fts_optimize_skip", e)

checks = {
    "product_total": "SELECT COUNT(*) FROM product",
    "wy_product": "SELECT COUNT(*) FROM product WHERE product_code LIKE 'WY-%' OR brand='无影' OR category_code LIKE 'CAT_WUYING%'",
    "product_price_total": "SELECT COUNT(*) FROM product_price",
    "inventory_total": "SELECT COUNT(*) FROM inventory",
    "product_spec_total": "SELECT COUNT(*) FROM product_spec",
    "knowledge_product_doc": "SELECT COUNT(*) FROM knowledge_chunk WHERE source_type='product_doc'",
    "wy_category": "SELECT COUNT(*) FROM product_category WHERE category_code LIKE 'CAT_WUYING%'",
    "quotation_policy": "SELECT COUNT(*) FROM quotation_policy",
    "order_requirement": "SELECT COUNT(*) FROM order_requirement",
}
for name, sql in checks.items():
    print(name, cur.execute(sql).fetchone()[0])
conn.close()
