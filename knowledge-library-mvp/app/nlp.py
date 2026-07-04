from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    metric: str | None = None
    year: int = 2026
    quarter: int | None = None
    month: int | None = None
    department: str | None = None


DEPARTMENTS = ["华东销售部", "华南销售部", "华北销售部", "市场部", "研发部", "行政部"]


def parse_query(text: str) -> Intent:
    raw = text.strip()
    year_match = re.search(r"(20\d{2})\s*年?", raw)
    year = int(year_match.group(1)) if year_match else 2026

    quarter = None
    q_match = re.search(r"Q([1-4])|第?([一二三四1234])季度", raw, re.I)
    if q_match:
        token = q_match.group(1) or q_match.group(2)
        quarter = {"一": 1, "二": 2, "三": 3, "四": 4}.get(token, int(token) if token.isdigit() else 1)

    month = None
    m_match = re.search(r"(\d{1,2})\s*月", raw)
    if m_match:
        month = max(1, min(12, int(m_match.group(1))))
    elif "上个月" in raw:
        month = 5
    elif "本月" in raw or "这个月" in raw:
        month = 6

    department = next((d for d in DEPARTMENTS if d in raw), None)

    if any(k in raw for k in ["预警", "异常", "风险", "低于", "超标"]):
        return Intent("alerts", year=year, quarter=quarter, month=month, department=department)
    if any(k in raw for k in ["预算", "执行率", "达标", "完成度", "还差"]):
        return Intent("kpi", metric="budget_rate", year=year, quarter=quarter, month=month, department=department)
    if any(k in raw for k in ["对比", "排名", "排行", "谁最高", "各部门"]):
        return Intent("compare", year=year, quarter=quarter, month=month, department=department)
    if any(k in raw for k in ["回款", "收款"]):
        return Intent("metric", metric="collection_amount", year=year, quarter=quarter, month=month, department=department)
    if any(k in raw for k in ["利润", "毛利"]):
        return Intent("metric", metric="profit", year=year, quarter=quarter, month=month, department=department)
    if any(k in raw for k in ["销售额", "收入", "业绩"]):
        return Intent("metric", metric="sales_amount", year=year, quarter=quarter, month=month, department=department)
    return Intent("help", year=year)


def period_where(intent: Intent) -> tuple[str, tuple]:
    clauses = ["year = ?"]
    params: list[int | str] = [intent.year]
    if intent.quarter:
        clauses.append("quarter = ?")
        params.append(intent.quarter)
    if intent.month:
        clauses.append("month = ?")
        params.append(intent.month)
    if intent.department:
        clauses.append("department = ?")
        params.append(intent.department)
    return " AND ".join(clauses), tuple(params)


def period_label(intent: Intent) -> str:
    if intent.month:
        return f"{intent.year}年{intent.month}月"
    if intent.quarter:
        return f"{intent.year}年Q{intent.quarter}"
    return f"{intent.year}年"
