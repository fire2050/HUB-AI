from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta

from app.db import fetch_all, fetch_one, get_conn
from app.security import UserContext, role_label
from app.service import answer_query as finance_answer_query
from app.quotation_flow import classify_quotation_entry, quotation_flow_prompt


def _like_query(query: str) -> tuple[str, str]:
    q = f"%{query.strip()}%"
    return q, q


def _money(value: float | int | None) -> str:
    return f"{float(value or 0):,.2f} 元"


def _is_wuying_line(line: dict) -> bool:
    text = " ".join(str(line.get(k, "")) for k in ["product_code", "product_name", "product_config", "source_sheet"])
    return any(token in text for token in ["无影", "WUYING", "wuying", "云电脑", "TERMINAL"])


def _is_terminal_line(line: dict) -> bool:
    text = " ".join(str(line.get(k, "")) for k in ["product_code", "product_name", "product_config", "source_sheet"])
    return any(token in text for token in ["终端", "无影魔方", "一体机", "方舟", "网关", "信创", "TERMINAL"])


def _duration_from_line(line: dict) -> str:
    text = " ".join(str(line.get(k, "")) for k in ["duration_label", "duration_type", "source_sheet", "product_name", "product_code"])
    if "200小时" in text:
        return "200小时"
    if "120小时" in text:
        return "120小时"
    if "1小时休眠" in text:
        return "不限时长（1小时休眠）"
    if "教育办公" in text:
        return "教育办公"
    if "不限时长" in text:
        return "不限时长"
    return line.get("duration_label") or line.get("duration_type") or "-"


def _format_wuying_unified_markdown(quotation_no: str, customer_code: str, lines: list[dict]) -> str:
    cloud = [x for x in lines if not _is_terminal_line(x)]
    terminal = [x for x in lines if _is_terminal_line(x)]
    md = [
        "💰 **商务报价单（草稿）**", "",
        f"- 报价单号：{quotation_no}",
        f"- 客户：{customer_code}", "",
        "云电脑资源报价：", "",
        "| 序号 | 产品名称 | 时长类型 | 产品/配置 | 数量 | 月价 | 总价（月） | 一年总价 |",
        "|---:|---|---|---|---:|---:|---:|---:|",
    ]
    cloud_month_sum = 0.0
    cloud_year_sum = 0.0
    if cloud:
        for idx, line in enumerate(cloud, start=1):
            qty = int(float(line.get("quantity") or 1))
            month_price = float(line.get("unit_price") or line.get("unit_price_final") or 0)
            month_total = qty * month_price
            year_total = month_total * 12
            cloud_month_sum += month_total
            cloud_year_sum += year_total
            md.append(f"| {idx} | 无影云电脑 | {_duration_from_line(line)} | {line.get('product_name') or line.get('product_code') or '-'} | {qty} | {_money(month_price)} | {_money(month_total)} | {_money(year_total)} |")
    else:
        md.append("| - | 无影云电脑 | - | 未选择/未匹配 | 0 | - | 0.00 元 | 0.00 元 |")
    md.extend(["", "无影终端报价：", "", "| 序号 | 产品名称 | 产品/配置 | 数量 | 单价 | 总价 |", "|---:|---|---|---:|---:|---:|"])
    terminal_sum = 0.0
    if terminal:
        for idx, line in enumerate(terminal, start=1):
            qty = int(float(line.get("quantity") or 1))
            unit_price = float(line.get("unit_price") or line.get("unit_price_final") or 0)
            total = qty * unit_price
            terminal_sum += total
            md.append(f"| {idx} | 无影终端 | {line.get('product_name') or line.get('product_code') or '-'} | {qty} | {_money(unit_price)} | {_money(total)} |")
    else:
        md.append("| - | 无影终端 | 未选择/不需要 | 0 | 0.00 元 | 0.00 元 |")
    md.extend([
        "", "汇总：",
        f"- 云电脑资源月总价：{_money(cloud_month_sum)}",
        f"- 云电脑资源一年总价：{_money(cloud_year_sum)}",
        f"- 无影终端总价：{_money(terminal_sum)}",
        f"- 首月合计（云电脑月总价 + 终端总价）：{_money(cloud_month_sum + terminal_sum)}",
        f"- 一年合计（云电脑一年总价 + 终端总价）：{_money(cloud_year_sum + terminal_sum)}",
        "", "计算口径：总价（月）= 数量 × 月价；一年总价 = 总价（月） × 12；无影终端总价 = 数量 × 单价。",
    ])
    return "\n".join(md)


def product_search(query: str = "", category: str | None = None, product_type: str | None = None, scenario: str | None = None, limit: int = 20) -> dict:
    clauses = ["p.status = 'active'"]
    params: list[str] = []
    if query:
        clauses.append("(p.product_name LIKE ? OR p.product_code LIKE ? OR p.short_description LIKE ? OR p.product_config_description LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"])
    if category:
        clauses.append("p.category_code = ?")
        params.append(category)
    if product_type:
        clauses.append("p.product_type = ?")
        params.append(product_type)
    if scenario:
        if scenario == "domestic":
            clauses.append("p.region_scope = 'domestic'")
        elif scenario == "international":
            clauses.append("p.region_scope = 'international'")
        elif scenario == "education":
            clauses.append("(p.source_sheet LIKE '%教育%' OR p.category_code = 'CAT_WUYING_EDU_COMPUTE')")
        elif scenario == "enterprise":
            clauses.append("p.region_scope = 'enterprise'")
        elif scenario == "common":
            clauses.append("p.region_scope = 'common'")
    rows = fetch_all(
        f"""
        SELECT p.product_code, p.product_name, p.category_code, p.product_type,
               p.product_type_name, p.region_scope, p.source_sheet, p.brand, p.model,
               p.unit, p.product_config_description, p.short_description, c.category_name
        FROM product p
        LEFT JOIN product_category c ON c.category_code = p.category_code
        WHERE {' AND '.join(clauses)}
        ORDER BY CASE p.product_type WHEN 'compute' THEN 0 WHEN 'terminal' THEN 1 WHEN 'storage' THEN 2 WHEN 'bandwidth' THEN 3 ELSE 9 END,
                 p.region_scope, p.product_code
        LIMIT ?
        """,
        tuple([*params, int(limit or 20)]),
    )
    return {"items": rows, "count": len(rows)}


def product_detail(product_code: str) -> dict:
    product = fetch_one("SELECT * FROM product WHERE product_code = ?", (product_code,))
    if not product:
        return {"error": "product_not_found", "message": f"未找到产品 {product_code}"}
    specs = fetch_all("SELECT spec_name, spec_value, spec_unit, spec_group FROM product_spec WHERE product_code = ? ORDER BY spec_group, sort_order, id", (product_code,))
    faqs = fetch_all("SELECT question, answer, tags FROM product_faq WHERE product_code = ? ORDER BY id", (product_code,))
    docs = fetch_all("SELECT title, doc_type, version, permission_level FROM product_document WHERE product_code = ? ORDER BY id", (product_code,))
    return {"product": product, "specs": specs, "faqs": faqs, "documents": docs}


def product_ask(question: str, product_code: str | None = None) -> dict:
    filters: dict[str, str] = {"source_type": "faq"}
    if product_code:
        filters["source_id"] = product_code
    results = knowledge_search(question, filters=filters)["items"]
    if not results:
        results = knowledge_search(question, filters={"source_type": "product_doc"}).get("items", [])
    if not results:
        return {"answer": "暂未检索到匹配的产品知识，请补充产品型号或问题关键词。", "sources": []}
    top = results[:3]
    lines = ["📦 **产品助理回答**", ""]
    for item in top:
        lines.append(f"- {item['title']}：{item['chunk_text'][:220]}{'…' if len(item['chunk_text']) > 220 else ''}")
    lines.append("\n📚 来源：" + "；".join(f"{i['source_type']}:{i['source_id']}#{i['id']}" for i in top))
    return {"answer": "\n".join(lines), "sources": top}


def check_stock(product_code: str) -> dict:
    rows = fetch_all(
        """
        SELECT product_code, warehouse_code, quantity, reserved_quantity,
               quantity - reserved_quantity AS available_quantity, safety_stock, last_updated
        FROM inventory WHERE product_code = ? ORDER BY warehouse_code
        """,
        (product_code,),
    )
    total = sum(int(r["available_quantity"] or 0) for r in rows)
    return {"product_code": product_code, "available_quantity": total, "warehouses": rows}


def generate_quotation(customer_code: str, items: list[dict], created_by: str = "system") -> dict:
    quotation_no = "Q" + date.today().strftime("%Y%m%d") + "-" + hashlib.sha1(f"{customer_code}{items}{date.today()}".encode()).hexdigest()[:6].upper()
    lines = []
    total = 0.0
    discount_amount = 0.0
    with get_conn() as conn:
        conn.execute("DELETE FROM quotation_line WHERE quotation_no = ?", (quotation_no,))
        conn.execute("DELETE FROM quotation_header WHERE quotation_no = ?", (quotation_no,))
        for item in items:
            product_code = item["product_code"]
            qty = int(item.get("qty") or item.get("quantity") or 1)
            price_type = item.get("price_type") or "1month"
            price_row = conn.execute(
                """
                SELECT unit_price, price_type FROM product_price
                WHERE product_code = ? AND status = 'active' AND price_type = ?
                ORDER BY valid_from DESC, id DESC LIMIT 1
                """,
                (product_code, price_type),
            ).fetchone()
            if not price_row:
                price_row = conn.execute(
                    """
                    SELECT unit_price, price_type FROM product_price
                    WHERE product_code = ? AND status = 'active'
                    ORDER BY CASE price_type WHEN '1month' THEN 0 WHEN 'standard' THEN 1 WHEN '1year' THEN 2 ELSE 9 END, id DESC
                    LIMIT 1
                    """,
                    (product_code,),
                ).fetchone()
            product_row = conn.execute("SELECT product_name, category_code FROM product WHERE product_code = ?", (product_code,)).fetchone()
            if not price_row or not product_row:
                continue
            policy = conn.execute(
                """
                SELECT discount_rate FROM quotation_policy
                WHERE status='active' AND (product_category_code = ? OR product_category_code IS NULL)
                  AND min_quantity <= ?
                ORDER BY product_category_code DESC, min_quantity DESC, discount_rate ASC
                LIMIT 1
                """,
                (product_row["category_code"], qty),
            ).fetchone()
            discount_rate = float(policy["discount_rate"] if policy else 1.0)
            unit_price = float(price_row["unit_price"])
            raw_amount = unit_price * qty
            line_amount = raw_amount * discount_rate
            total += raw_amount
            discount_amount += raw_amount - line_amount
            conn.execute(
                """
                INSERT INTO quotation_line
                (quotation_no, product_code, quantity, unit_price, discount_rate, line_amount, delivery_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (quotation_no, product_code, qty, unit_price, discount_rate, line_amount, str(date.today() + timedelta(days=14))),
            )
            stock = conn.execute("SELECT COALESCE(SUM(quantity - reserved_quantity), 0) AS available FROM inventory WHERE product_code = ?", (product_code,)).fetchone()["available"]
            lines.append({
                "product_code": product_code,
                "product_name": product_row["product_name"],
                "quantity": qty,
                "unit_price": unit_price,
                "price_type": price_row["price_type"],
                "discount_rate": discount_rate,
                "line_amount": line_amount,
                "available_quantity": stock,
            })
        final_amount = total - discount_amount
        conn.execute(
            """
            INSERT INTO quotation_header
            (quotation_no, customer_code, quotation_date, valid_until, total_amount, discount_amount, final_amount, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', ?)
            """,
            (quotation_no, customer_code, str(date.today()), str(date.today() + timedelta(days=30)), total, discount_amount, final_amount, created_by),
        )
        conn.commit()
    if any(_is_wuying_line(line) for line in lines):
        markdown_text = _format_wuying_unified_markdown(quotation_no, customer_code, lines)
    else:
        markdown = ["💰 **商务报价单（草稿）**", "", f"- 报价单号：{quotation_no}", f"- 客户：{customer_code}", f"- 原价合计：{_money(total)}", f"- 优惠金额：{_money(discount_amount)}", f"- 应付合计：**{_money(final_amount)}**", ""]
        for line in lines:
            markdown.append(f"- {line['product_name']} × {line['quantity']}：{_money(line['line_amount'])}（折扣 {line['discount_rate']:.2f}，可用库存 {line['available_quantity']}）")
        markdown_text = "\n".join(markdown)
    return {"quotation_no": quotation_no, "markdown": markdown_text, "total_amount": total, "discount_amount": discount_amount, "final_amount": final_amount, "lines": lines}


def blog_search(query: str = "", status: str | None = None) -> dict:
    clauses: list[str] = []
    params: list[str] = []
    if query:
        clauses.append("(title LIKE ? OR content_summary LIKE ? OR keywords LIKE ? OR tags LIKE ?)")
        params.extend([f"%{query}%"] * 4)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    rows = fetch_all(
        f"""
        SELECT article_code, title, series_no, status, content_summary, keywords, tags, source_file
        FROM blog_article {where}
        ORDER BY CASE status WHEN 'published' THEN 0 ELSE 1 END, id DESC
        LIMIT 20
        """,
        tuple(params),
    )
    return {"items": rows, "count": len(rows)}


def blog_ask(question: str) -> dict:
    results = knowledge_search(question, filters={"source_type": "blog_article"})["items"]
    if not results:
        return {"answer": "悟空系列归档中暂未检索到相关内容。", "sources": []}
    lines = ["📝 **博文助理回答**", ""]
    for item in results[:5]:
        lines.append(f"- {item['title']}：{item['chunk_text'][:180]}{'…' if len(item['chunk_text']) > 180 else ''}")
    lines.append("\n📚 来源：" + "；".join(f"{i['source_id']}#{i['chunk_index']}" for i in results[:5]))
    return {"answer": "\n".join(lines), "sources": results[:5]}


def knowledge_search(query: str, filters: dict | None = None, limit: int = 8) -> dict:
    filters = filters or {}
    params: list[str | int] = []
    base_select = "SELECT kc.id, kc.source_type, kc.source_id, kc.title, kc.chunk_text, kc.chunk_index, kc.tags, kc.permission_level"
    clauses = []
    for key in ("source_type", "source_id", "permission_level"):
        if filters.get(key):
            clauses.append(f"kc.{key} = ?")
            params.append(filters[key])
    try:
        fts_query = " ".join(re.findall(r"[\w\u4e00-\u9fff]+", query)) or query
        rows = fetch_all(
            f"""
            {base_select}
            FROM knowledge_chunk_fts fts
            JOIN knowledge_chunk kc ON kc.id = fts.rowid
            WHERE knowledge_chunk_fts MATCH ? {'AND ' + ' AND '.join(clauses) if clauses else ''}
            ORDER BY rank
            LIMIT ?
            """,
            tuple([fts_query, *params, limit]),
        )
    except Exception:
        like = f"%{query}%"
        rows = fetch_all(
            f"""
            {base_select}
            FROM knowledge_chunk kc
            WHERE (kc.chunk_text LIKE ? OR kc.title LIKE ?) {'AND ' + ' AND '.join(clauses) if clauses else ''}
            ORDER BY kc.id DESC
            LIMIT ?
            """,
            tuple([like, like, *params, limit]),
        )
    return {"items": rows, "count": len(rows)}


def knowledge_ask(question: str, user: UserContext) -> dict:
    rows = knowledge_search(question, limit=5)["items"]
    if not rows:
        markdown = "【信息来源不足，仅供参考】当前知识库未找到可引用内容，请补充资料后重建索引。"
    else:
        markdown = "\n".join([
            "🔎 **统一知识检索回答**",
            f"- 提问人：{user.name}（{role_label(user.role)}）",
            "- 回答依据：",
            *[f"  {i+1}. {r['title']}：{r['chunk_text'][:180]}{'…' if len(r['chunk_text']) > 180 else ''}" for i, r in enumerate(rows)],
            "",
            "📚 来源：" + "；".join(f"{r['source_type']}:{r['source_id']}#{r['chunk_index']}" for r in rows),
        ])
    return {"answer": markdown, "sources": rows}


def upsert_product_records(records: list[dict], source: str = "manual_import") -> dict:
    """Upsert product master data, price, inventory, specs and FAQ from flat records.

    Supported optional fields:
    product_code, product_name, category_code, category_name, brand, model, unit,
    short_description, unit_price, warehouse_code, inventory_quantity,
    reserved_quantity, spec_name, spec_value, spec_unit, spec_group,
    faq_question, faq_answer, tags.
    """
    stats = {"records": len(records), "products": 0, "prices": 0, "inventory": 0, "specs": 0, "faqs": 0, "skipped": 0}
    with get_conn() as conn:
        for record in records:
            product_code = str(record.get("product_code") or "").strip()
            product_name = str(record.get("product_name") or "").strip()
            if not product_code or not product_name:
                stats["skipped"] += 1
                continue
            category_code = str(record.get("category_code") or "CAT_IMPORTED").strip()
            category_name = str(record.get("category_name") or "导入产品").strip()
            conn.execute(
                """
                INSERT INTO product_category (category_code, category_name, description)
                VALUES (?, ?, ?)
                ON CONFLICT(category_code) DO UPDATE SET category_name=excluded.category_name
                """,
                (category_code, category_name, f"Imported by {source}"),
            )
            conn.execute(
                """
                INSERT INTO product
                (product_code, product_name, category_code, brand, model, unit, short_description, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
                ON CONFLICT(product_code) DO UPDATE SET
                    product_name=excluded.product_name,
                    category_code=excluded.category_code,
                    brand=excluded.brand,
                    model=excluded.model,
                    unit=excluded.unit,
                    short_description=excluded.short_description,
                    status='active',
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    product_code,
                    product_name,
                    category_code,
                    record.get("brand"),
                    record.get("model"),
                    record.get("unit") or "套",
                    record.get("short_description") or record.get("description") or "",
                ),
            )
            stats["products"] += 1

            if record.get("unit_price") not in (None, ""):
                conn.execute(
                    "UPDATE product_price SET status='inactive' WHERE product_code=? AND price_type='standard' AND status='active'",
                    (product_code,),
                )
                conn.execute(
                    """
                    INSERT INTO product_price (product_code, unit_price, currency, price_type, status)
                    VALUES (?, ?, ?, 'standard', 'active')
                    """,
                    (product_code, float(record.get("unit_price") or 0), record.get("currency") or "CNY"),
                )
                stats["prices"] += 1

            if record.get("inventory_quantity") not in (None, "") or record.get("quantity") not in (None, ""):
                warehouse_code = str(record.get("warehouse_code") or "WH-DEFAULT").strip()
                quantity = int(float(record.get("inventory_quantity") or record.get("quantity") or 0))
                reserved_quantity = int(float(record.get("reserved_quantity") or 0))
                conn.execute("DELETE FROM inventory WHERE product_code=? AND warehouse_code=?", (product_code, warehouse_code))
                conn.execute(
                    """
                    INSERT INTO inventory (product_code, warehouse_code, quantity, reserved_quantity, safety_stock)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (product_code, warehouse_code, quantity, reserved_quantity, int(float(record.get("safety_stock") or 10))),
                )
                stats["inventory"] += 1

            if record.get("spec_name") and record.get("spec_value"):
                conn.execute(
                    "DELETE FROM product_spec WHERE product_code=? AND spec_name=?",
                    (product_code, record.get("spec_name")),
                )
                conn.execute(
                    """
                    INSERT INTO product_spec (product_code, spec_name, spec_value, spec_unit, spec_group, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product_code,
                        record.get("spec_name"),
                        record.get("spec_value"),
                        record.get("spec_unit"),
                        record.get("spec_group") or "导入规格",
                        int(float(record.get("sort_order") or 0)),
                    ),
                )
                stats["specs"] += 1

            if record.get("faq_question") and record.get("faq_answer"):
                exists = conn.execute(
                    "SELECT id FROM product_faq WHERE product_code=? AND question=?",
                    (product_code, record.get("faq_question")),
                ).fetchone()
                if exists:
                    conn.execute(
                        "UPDATE product_faq SET answer=?, tags=?, source=? WHERE id=?",
                        (record.get("faq_answer"), record.get("tags"), source, exists["id"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO product_faq (product_code, question, answer, tags, source) VALUES (?, ?, ?, ?, ?)",
                        (product_code, record.get("faq_question"), record.get("faq_answer"), record.get("tags"), source),
                    )
                stats["faqs"] += 1
        conn.commit()
    return stats


def resolve_product_code(text: str) -> str | None:
    raw = text.strip()
    # Explicit codes: WY-... or P-...
    explicit = re.search(r"(?:WY|P)-[^\s，。；;、]+", raw, re.I)
    if explicit:
        code = explicit.group(0).strip()
        row = fetch_one("SELECT product_code FROM product WHERE product_code = ? COLLATE NOCASE", (code,))
        return row["product_code"] if row else code
    # Prefer product names mentioned in text. Longest name first avoids partial collisions.
    rows = fetch_all("SELECT product_code, product_name FROM product WHERE status='active' ORDER BY LENGTH(product_name) DESC LIMIT 500")
    for row in rows:
        name = row.get("product_name") or ""
        code = row.get("product_code") or ""
        if (name and name in raw) or (code and code in raw):
            return code
    # Fuzzy keyword fallback: use first product whose name contains any meaningful token.
    tokens = [t for t in re.split(r"[\s，。；;、]+", raw) if len(t) >= 4]
    for token in tokens:
        for row in rows:
            if token in (row.get("product_name") or ""):
                return row.get("product_code")
    first = fetch_one("SELECT product_code FROM product WHERE status='active' ORDER BY product_code LIMIT 1")
    return first["product_code"] if first else None


def route_assistant(message: str, user: UserContext) -> dict:
    raw = message.strip()
    quotation_intent = any(k in raw for k in ["报价", "价格", "多少钱", "库存", "现货", "查价", "单品", "需求表", "P0", "p0", "方案报价", "正式报价", "客户报价", "项目报价"])
    if quotation_intent:
        decision = classify_quotation_entry(raw)
        flow = decision.flow_type

        if flow == "unclear":
            return {
                "assistant": "quotation",
                "intent": "quotation_flow_unclear",
                "markdown": quotation_flow_prompt(),
                "data": {"flow_decision": decision.to_dict()},
            }

        if flow == "requirement_p0":
            return {
                "assistant": "quotation",
                "intent": "quotation_requirement_required",
                "markdown": (
                    "已识别为客户需求/项目/方案类报价。\n\n"
                    "请先创建【客户需求表三】，再进入需求卡、分流、规则校验、审批和正式客户报价。\n"
                    "当前不会绕过需求表三直接生成正式客户报价。"
                ),
                "data": {
                    "flow_decision": decision.to_dict(),
                    "api": "POST /api/order-requirements",
                    "history_usage": "历史项目仅作为报价参考，不作为报价规则。",
                },
            }

        product_code = resolve_product_code(raw)
        if not product_code:
            return {"assistant": "quotation", "intent": "product_missing", "markdown": "未找到可报价产品，请先上传产品/报价数据。", "data": {"flow_decision": decision.to_dict()}}
        if any(k in raw for k in ["库存", "现货"]):
            stock = check_stock(product_code)
            return {"assistant": "quotation", "intent": "stock_check", "markdown": f"📦 {product_code} 当前可用库存：**{stock['available_quantity']}**。", "data": {"stock": stock, "flow_decision": decision.to_dict()}}
        price_type = "1year" if any(k in raw for k in ["一年", "1年", "年付", "包年", "年度"]) else "1month"
        qty_match = re.search(r"(\d+)\s*[台套点个人用户账号终端席]", raw)
        qty = int(qty_match.group(1)) if qty_match else 1
        quote = generate_quotation("C001", [{"product_code": product_code, "qty": qty, "price_type": price_type}], created_by=user.user_id)
        quote["flow_decision"] = decision.to_dict()
        return {"assistant": "quotation", "intent": "quotation_single_item_generate", "markdown": quote["markdown"], "data": quote}
    if any(k in raw for k in ["产品", "参数", "型号", "规格", "部署方式", "FAQ"]):
        ans = product_ask(raw)
        return {"assistant": "product", "intent": "product_ask", "markdown": ans["answer"], "data": ans}
    if any(k in raw for k in ["文章", "博文", "悟空系列", "怎么写", "RAG", "知识库"]):
        ans = blog_ask(raw)
        return {"assistant": "blog", "intent": "blog_ask", "markdown": ans["answer"], "data": ans}
    result = finance_answer_query(raw, user)
    return {"assistant": "finance", **result}
