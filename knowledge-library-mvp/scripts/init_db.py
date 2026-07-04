from __future__ import annotations

import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import DB_PATH  # noqa: E402

DEPTS = [
    ("华东销售部", ["张三", "赵六"]),
    ("华南销售部", ["李四", "钱七"]),
    ("华北销售部", ["孙八", "周九"]),
]


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS sales_monthly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            quarter INTEGER NOT NULL,
            month INTEGER NOT NULL,
            department TEXT NOT NULL,
            salesperson TEXT NOT NULL,
            sales_amount REAL NOT NULL,
            collection_amount REAL NOT NULL,
            profit REAL NOT NULL,
            target_amount REAL NOT NULL,
            budget_rate REAL NOT NULL,
            collection_rate REAL NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_sales_period ON sales_monthly(year, quarter, month);
        CREATE INDEX IF NOT EXISTS idx_sales_scope ON sales_monthly(department, salesperson);
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            query_text TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    count = cur.execute("SELECT COUNT(*) FROM sales_monthly").fetchone()[0]
    if count:
        print(f"Database already initialized: {DB_PATH} ({count} sales rows)")
        conn.close()
        return

    random.seed(42)
    rows = []
    for month in range(1, 7):
        quarter = (month - 1) // 3 + 1
        for dept, people in DEPTS:
            dept_factor = {"华东销售部": 1.25, "华南销售部": 1.08, "华北销售部": 0.92}[dept]
            for person in people:
                base = random.randint(260_000, 520_000) * dept_factor
                if person == "张三":
                    base *= 1.12
                target = 430_000 * dept_factor
                collection_rate = random.uniform(72, 96)
                budget_rate = random.uniform(62, 94)
                if dept == "华南销售部" and month in (5, 6):
                    collection_rate -= 8
                if dept == "华东销售部" and month == 6:
                    budget_rate += 7
                collection = base * collection_rate / 100
                profit = base * random.uniform(0.16, 0.28)
                rows.append((2026, quarter, month, dept, person, round(base, 2), round(collection, 2), round(profit, 2), round(target, 2), round(budget_rate, 2), round(collection_rate, 2)))

    cur.executemany(
        """
        INSERT INTO sales_monthly
        (year, quarter, month, department, salesperson, sales_amount, collection_amount, profit, target_amount, budget_rate, collection_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()
    print(f"Initialized database: {DB_PATH} ({len(rows)} sales rows)")


if __name__ == "__main__":
    main()
