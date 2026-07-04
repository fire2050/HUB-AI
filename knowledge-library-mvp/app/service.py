from __future__ import annotations

from app.db import fetch_all, fetch_one
from app.nlp import Intent, parse_query, period_label, period_where
from app.security import UserContext, role_label, scope_filter

METRIC_LABELS = {
    "sales_amount": "销售额",
    "collection_amount": "回款额",
    "profit": "利润",
    "budget_rate": "预算执行率",
}


def money(value: float | int | None) -> str:
    value = float(value or 0)
    return f"{value / 10000:.2f} 万元"


def pct(value: float | int | None) -> str:
    return f"{float(value or 0):.1f}%"


def answer_query(text: str, user: UserContext) -> dict:
    intent = parse_query(text)
    if intent.name == "metric":
        return metric_answer(intent, user)
    if intent.name == "kpi":
        return kpi_answer(intent, user)
    if intent.name == "compare":
        return compare_answer(intent, user)
    if intent.name == "alerts":
        return alerts_answer(intent, user)
    return help_answer(user)


def build_where(intent: Intent, user: UserContext) -> tuple[str, tuple]:
    period_sql, period_params = period_where(intent)
    scope_sql, scope_params = scope_filter(user)
    return f"{period_sql} AND {scope_sql}", period_params + scope_params


def metric_answer(intent: Intent, user: UserContext) -> dict:
    metric = intent.metric or "sales_amount"
    where_sql, params = build_where(intent, user)
    row = fetch_one(f"SELECT SUM({metric}) AS value FROM sales_monthly WHERE {where_sql}", params)
    value = row["value"] if row else 0
    markdown = f"""📊 **财务悟空查询结果**

- 查询对象：{user.name}（{role_label(user.role)}）
- 查询周期：{period_label(intent)}
- 指标：{METRIC_LABELS[metric]}
- 结果：**{money(value)}**

🔒 权限说明：已按你的角色自动过滤可见数据，未返回原始明细。"""
    return {"intent": intent.name, "markdown": markdown, "data": {"metric": metric, "value": value}}


def kpi_answer(intent: Intent, user: UserContext) -> dict:
    where_sql, params = build_where(intent, user)
    row = fetch_one(
        f"""
        SELECT SUM(sales_amount) AS sales, SUM(target_amount) AS target,
               AVG(budget_rate) AS budget_rate, AVG(collection_rate) AS collection_rate
        FROM sales_monthly WHERE {where_sql}
        """,
        params,
    ) or {}
    sales = row.get("sales") or 0
    target = row.get("target") or 0
    completion = sales / target * 100 if target else 0
    markdown = f"""🎯 **年度 KPI / 预算执行追踪**

- 查询对象：{user.name}（{role_label(user.role)}）
- 查询周期：{period_label(intent)}
- 销售完成度：**{pct(completion)}**（{money(sales)} / {money(target)}）
- 平均预算执行率：**{pct(row.get('budget_rate'))}**
- 平均回款率：**{pct(row.get('collection_rate'))}**

{'⚠️ 建议关注：预算执行率偏高或回款率不足。' if (row.get('budget_rate') or 0) > 90 or (row.get('collection_rate') or 100) < 80 else '✅ 当前指标处于可控区间。'}"""
    return {"intent": intent.name, "markdown": markdown, "data": dict(row)}


def compare_answer(intent: Intent, user: UserContext) -> dict:
    if user.role == "sales":
        return {
            "intent": "permission_denied",
            "markdown": "🔒 你当前是销售个人角色，只能查看本人汇总指标，不能查看部门/人员对比排行。",
            "data": {},
        }
    where_sql, params = build_where(intent, user)
    rows = fetch_all(
        f"""
        SELECT department, SUM(sales_amount) AS sales, SUM(collection_amount) AS collection,
               AVG(budget_rate) AS budget_rate
        FROM sales_monthly
        WHERE {where_sql}
        GROUP BY department
        ORDER BY sales DESC
        LIMIT 8
        """,
        params,
    )
    lines = ["📈 **部门经营对比**", "", f"- 查询周期：{period_label(intent)}", ""]
    for idx, row in enumerate(rows, start=1):
        lines.append(f"{idx}. {row['department']}：销售 {money(row['sales'])}，回款 {money(row['collection'])}，预算执行率 {pct(row['budget_rate'])}")
    lines.append("\n🔒 已按角色范围聚合展示，不暴露个人原始明细。")
    return {"intent": intent.name, "markdown": "\n".join(lines), "data": rows}


def alerts_answer(intent: Intent, user: UserContext) -> dict:
    where_sql, params = build_where(intent, user)
    rows = fetch_all(
        f"""
        SELECT department, salesperson, month, budget_rate, collection_rate, sales_amount
        FROM sales_monthly
        WHERE {where_sql} AND (budget_rate >= 90 OR collection_rate < 80)
        ORDER BY budget_rate DESC, collection_rate ASC
        LIMIT 10
        """,
        params,
    )
    if not rows:
        markdown = f"✅ **异常预警**\n\n{period_label(intent)} 当前可见范围内暂无预算超 90% 或回款率低于 80% 的异常项。"
    else:
        lines = ["⚠️ **异常预警清单**", "", f"- 查询周期：{period_label(intent)}", ""]
        for row in rows:
            subject = row["department"] if user.role != "sales" else user.name
            lines.append(f"- {row['month']}月 {subject}：预算执行率 {pct(row['budget_rate'])}，回款率 {pct(row['collection_rate'])}，销售 {money(row['sales_amount'])}")
        markdown = "\n".join(lines)
    return {"intent": intent.name, "markdown": markdown, "data": rows}


def help_answer(user: UserContext) -> dict:
    markdown = f"""👋 我是 **财务悟空 MVP**，当前身份：{user.name}（{role_label(user.role)}）。

你可以这样问：
- 查我上个月销售额
- Q1 回款多少
- 今年目标完成度
- 华东销售部预算执行率
- 各部门销售额对比
- 看看有没有异常预警

MVP 安全策略：默认只返回聚合数据，不返回原始凭证、个人薪资、账号等敏感明细。"""
    return {"intent": "help", "markdown": markdown, "data": {}}
