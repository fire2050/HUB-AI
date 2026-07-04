from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import DB_PATH  # noqa: E402

try:
    import openpyxl
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"openpyxl is required: {exc}")

EXCEL_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app/data/uploads/原始数据/03-报价库存/20260624033509_不可外发-产品清单模板-商业版-V20260624.xlsx")


def norm(v: Any) -> str:
    return str(v or "").strip()


def to_float(v: Any, default: float = 0.0) -> float:
    if v is None or v == "":
        return default
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("￥", "").replace("元", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else default


def find_col(headers: list[str], *keywords: str) -> int | None:
    for idx, h in enumerate(headers):
        text = h.lower().replace(" ", "")
        if all(k.lower() in text for k in keywords):
            return idx
    return None


def first_col(headers: list[str], candidates: list[tuple[str, ...]]) -> int | None:
    for c in candidates:
        col = find_col(headers, *c)
        if col is not None:
            return col
    return None


def choose_price_col(headers: list[str]) -> int | None:
    """Prefer real price columns, avoid 报价条件/备注/链接."""
    best: tuple[int, int] | None = None
    for idx, h in enumerate(headers):
        text = h.lower().replace(" ", "")
        if not text or any(bad in text for bad in ["条件", "备注", "说明", "链接", "索引"]):
            continue
        score = 0
        for token in ["目录月价", "月价", "套餐价格", "价格", "单价", "price", "元/月", "元/小时", "元/年", "元"]:
            if token in text:
                score += 10
        if "价" in text:
            score += 2
        if score:
            if best is None or score > best[0]:
                best = (score, idx)
    return best[1] if best else None


def main() -> None:
    if not EXCEL_PATH.exists():
        raise SystemExit(f"Excel not found: {EXCEL_PATH}")

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 清空当前产品/报价/库存/规格/FAQ/文档/知识切片演示数据
    for table in [
        "knowledge_chunk_fts", "knowledge_chunk", "product_faq", "product_spec", "product_document",
        "inventory", "product_price", "quotation_line", "quotation_header", "quotation_policy", "product", "product_category",
    ]:
        try:
            cur.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass

    cur.execute("INSERT OR IGNORE INTO product_category (category_code, category_name, description) VALUES ('CAT_WUYING', '无影产品', '由无影产品 Excel 导入')")
    cur.execute("INSERT OR IGNORE INTO quotation_policy (policy_code, policy_name, discount_rate, min_quantity, status) VALUES ('POL-WUYING-STD', '无影标准报价政策', 1.0, 1, 'active')")

    imported = 0
    skipped = 0
    diagnostics: list[dict] = []

    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        # 找到最像表头的行：含产品/名称/型号/SKU/价格等关键词
        header_idx = None
        for i, row in enumerate(rows[:20]):
            joined = " ".join(norm(x) for x in row)
            if any(k in joined for k in ["产品", "名称", "型号", "SKU", "价格", "报价", "库存"]):
                header_idx = i
                break
        if header_idx is None:
            skipped += len(rows)
            continue
        headers = [norm(x) for x in rows[header_idx]]
        code_col = first_col(headers, [("产品", "编码"), ("产品", "代码"), ("商品", "编码"), ("SKU",), ("编码",), ("料号",)])
        name_col = first_col(headers, [("产品", "名称"), ("商品", "名称"), ("名称",), ("品名",)])
        model_col = first_col(headers, [("型号",), ("规格", "型号"), ("Model",)])
        price_col = choose_price_col(headers)
        stock_col = first_col(headers, [("库存",), ("数量",), ("stock",)])
        desc_col = first_col(headers, [("描述",), ("说明",), ("备注",), ("卖点",)])
        brand_col = first_col(headers, [("品牌",), ("brand",)])
        unit_col = first_col(headers, [("单位",), ("unit",)])
        category_col = first_col(headers, [("分类",), ("类别",), ("系列",)])

        diagnostics.append({"sheet": ws.title, "headers": headers, "cols": {"code": code_col, "name": name_col, "model": model_col, "price": price_col, "stock": stock_col}})
        if name_col is None and code_col is None:
            continue

        for row in rows[header_idx + 1:]:
            values = list(row)
            if not any(norm(x) for x in values):
                continue
            name = norm(values[name_col]) if name_col is not None and name_col < len(values) else ""
            code = norm(values[code_col]) if code_col is not None and code_col < len(values) else ""
            model = norm(values[model_col]) if model_col is not None and model_col < len(values) else ""
            if not name and not code:
                skipped += 1
                continue
            if not code:
                base = model or name
                code = "WY-" + re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", base).strip("-")[:40]
            if not name:
                name = code
            product_code = code[:80]
            product_name = name[:160]
            price = to_float(values[price_col]) if price_col is not None and price_col < len(values) else 0.0
            # If chosen column is empty due to merged header, scan numeric cells after name/model columns.
            if price <= 0:
                numeric_candidates = [to_float(x) for x in values]
                numeric_candidates = [x for x in numeric_candidates if x > 0]
                price = numeric_candidates[0] if numeric_candidates else 0.0
            stock = int(to_float(values[stock_col], 999)) if stock_col is not None and stock_col < len(values) else 999
            desc = norm(values[desc_col]) if desc_col is not None and desc_col < len(values) else ""
            brand = norm(values[brand_col]) if brand_col is not None and brand_col < len(values) else "无影"
            unit = norm(values[unit_col]) if unit_col is not None and unit_col < len(values) else "套"
            category = norm(values[category_col]) if category_col is not None and category_col < len(values) else "无影产品"
            category_code = "CAT_WUYING"

            cur.execute("UPDATE product_category SET category_name=? WHERE category_code=?", (category or "无影产品", category_code))
            cur.execute(
                """
                INSERT INTO product (product_code, product_name, category_code, brand, model, unit, short_description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                ON CONFLICT(product_code) DO UPDATE SET
                    product_name=excluded.product_name, brand=excluded.brand, model=excluded.model,
                    unit=excluded.unit, short_description=excluded.short_description, status='active', updated_at=CURRENT_TIMESTAMP
                """,
                (product_code, product_name, category_code, brand, model, unit, desc),
            )
            if price > 0:
                cur.execute("INSERT INTO product_price (product_code, unit_price, currency, price_type, status) VALUES (?, ?, 'CNY', 'standard', 'active')", (product_code, price))
            cur.execute("INSERT INTO inventory (product_code, warehouse_code, quantity, reserved_quantity, safety_stock) VALUES (?, 'WH-WUYING', ?, 0, 10)", (product_code, stock))
            if model:
                cur.execute("INSERT INTO product_spec (product_code, spec_name, spec_value, spec_group) VALUES (?, '型号', ?, '基础信息')", (product_code, model))
            if desc:
                cur.execute("INSERT INTO product_faq (product_code, question, answer, tags, source) VALUES (?, '产品主要说明是什么？', ?, '无影,产品说明', 'wuying_excel')", (product_code, desc))
            cur.execute(
                "INSERT INTO knowledge_chunk (source_type, source_id, title, chunk_text, chunk_index, tags) VALUES ('product_doc', ?, ?, ?, 0, '无影,产品')",
                (product_code, product_name, f"{product_name}\n型号：{model}\n价格：{price}\n库存：{stock}\n说明：{desc}"),
            )
            imported += 1

    conn.commit()
    counts = {}
    for table in ["product", "product_price", "inventory", "product_spec", "product_faq", "knowledge_chunk"]:
        counts[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    print({"excel": str(EXCEL_PATH), "imported": imported, "skipped": skipped, "counts": counts, "diagnostics": diagnostics[:5]})


if __name__ == "__main__":
    main()
