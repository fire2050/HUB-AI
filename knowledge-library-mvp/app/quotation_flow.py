"""Universal quotation entry classifier for HubAI.

This module is intentionally product-agnostic. It decides the quotation entry
path before any product-specific price engine is invoked, so current and future
products share the same guardrail:

- single_item: quick internal price lookup / reference quotation.
- requirement_p0: customer/project/solution quotation; must create 客户需求表三.
- unclear: ask the user to choose one of the two paths.

Rules are deterministic and conservative: when a message contains customer,
project, solution, delivery, budget, attachment, multi-product, or formal quote
signals, it is treated as requirement_p0 even if it also includes price words.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


_SINGLE_ITEM_KEYWORDS = [
    "单品",
    "查价",
    "查一下",
    "查多少钱",
    "多少钱",
    "价格",
    "价钱",
    "单价",
    "库存",
    "现货",
    "price",
    "stock",
]

_GENERIC_QUOTE_KEYWORDS = [
    "提供报价",
    "报价",
    "quote",
    "quotation",
]

_REQUIREMENT_KEYWORDS = [
    "客户需求表三",
    "需求表三",
    "需求表",
    "需求清单",
    "客户需求",
    "P0",
    "p0",
    "方案报价",
    "正式报价",
    "客户报价",
    "项目报价",
    "项目需求报价",
    "做项目",
    "做方案",
    "正式客户报价",
    "整套",
    "全套",
    "方案",
    "项目",
    "交付",
    "实施",
    "部署",
    "上线",
    "验收",
    "预算",
    "附件",
    "招标",
    "投标",
    "合同",
    "审批",
    "联系人",
    "对接人",
    "客户名称",
    "客户公司",
    "公司",
    "集团",
    "学校",
    "医院",
    "有限公司",
]

_FORMAL_OUTPUT_KEYWORDS = [
    "客户版",
    "盖章",
    "正式版",
    "报价单",
    "方案书",
    "交付方案",
    "技术方案",
    "客户正式报价",
    "正式客户报价",
]

_MULTI_PRODUCT_PATTERNS = [
    r"\d+\s*(?:种|类|款)",
    r"(?:多个|多款|多种|组合|打包|套餐)",
]

_QUANTITY_PATTERNS = [
    r"\d+\s*(?:台|套|点|个|人|用户|账号|终端|席)",
]

_PROJECT_QUANTITY_PATTERNS = [
    r"\d+\s*(?:人|用户|点|台|套|终端|席).*(?:项目|客户|部署|交付|上线|公司|学校|医院|集团|预算)",
    r"(?:项目|客户|部署|交付|上线|公司|学校|医院|集团|预算).*\d+\s*(?:人|用户|点|台|套|终端|席)",
]

_PRODUCT_CODE_RE = re.compile(r"(?:WY|P)-[^\s，。；;、]+", re.I)


@dataclass(frozen=True)
class QuotationFlowDecision:
    """Classifier output used by every product quotation entry."""

    flow_type: str
    confidence: float
    reason: str
    signals: list[str] = field(default_factory=list)
    next_action: str = ""
    requires_order_requirement: bool = False
    quotation_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _contains_any(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if kw and kw in text]


def _matches_any(text: str, patterns: list[str]) -> list[str]:
    signals: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, re.I):
            signals.append(pattern)
    return signals


def classify_quotation_entry(message: str | None, payload: dict[str, Any] | None = None) -> QuotationFlowDecision:
    """Classify quotation request as single_item, requirement_p0, or unclear.

    The function is pure and product-agnostic. Product-specific Skills may pass
    their own payload, but the returned flow must remain the shared contract for
    all products.
    """
    raw = (message or "").strip()
    payload = payload or {}
    normalized = raw.lower()

    explicit_flow = (payload.get("flow_type") or payload.get("quotation_flow") or "").strip()
    explicit_type = (payload.get("quotation_type") or payload.get("quote_type") or "").strip()

    if explicit_flow in {"single_item", "requirement_p0", "unclear"}:
        return _decision_from_flow(explicit_flow, [f"explicit_flow:{explicit_flow}"])
    if explicit_type in {"单品查询", "single_item"}:
        return _decision_from_flow("single_item", [f"explicit_quotation_type:{explicit_type}"])
    if explicit_type in {"方案报价", "solution", "requirement_p0", "客户需求表三"}:
        return _decision_from_flow("requirement_p0", [f"explicit_quotation_type:{explicit_type}"])

    requirement_signals = _contains_any(raw, _REQUIREMENT_KEYWORDS)
    requirement_signals += _contains_any(raw, _FORMAL_OUTPUT_KEYWORDS)
    requirement_signals += _matches_any(raw, _MULTI_PRODUCT_PATTERNS)
    requirement_signals += _matches_any(raw, _PROJECT_QUANTITY_PATTERNS)
    single_signals = _contains_any(raw, _SINGLE_ITEM_KEYWORDS)
    generic_quote_signals = _contains_any(raw, _GENERIC_QUOTE_KEYWORDS)

    quantity_signals = _matches_any(raw, _QUANTITY_PATTERNS)
    product_code_signals = ["product_code"] if _PRODUCT_CODE_RE.search(raw) else []

    # Payload-level P0 signals. Any structured customer/project info means this
    # is a customer-demand quotation, not a lightweight single-item lookup.
    for key in [
        "requirement_no",
        "customer_name",
        "customer_company",
        "customer_contact_name",
        "raw_requirement",
        "attachment_links",
        "budget_range",
        "budget_text",
        "source_channel",
    ]:
        if payload.get(key):
            requirement_signals.append(f"payload:{key}")

    items = payload.get("items") or payload.get("products") or []
    payload_single_item_signals = []
    if isinstance(items, list) and len(items) > 1:
        requirement_signals.append("payload:multi_items")
    elif isinstance(items, list) and len(items) == 1 and isinstance(items[0], dict) and items[0].get("product_code"):
        payload_single_item_signals.append("payload:single_item")

    # Conservative guardrail: formal/customer/project/P0 signals always win.
    if requirement_signals:
        confidence = 0.9 if single_signals else 0.86
        return QuotationFlowDecision(
            flow_type="requirement_p0",
            confidence=confidence,
            reason="命中客户/项目/方案/P0/正式输出信号，必须先进入客户需求表三。",
            signals=sorted(set(requirement_signals + generic_quote_signals + quantity_signals)),
            next_action="create_order_requirement",
            requires_order_requirement=True,
            quotation_type="方案报价",
        )

    # Single-item quick quote: explicit product/config + price/stock intent, or
    # short price lookup without project/customer signals.
    if single_signals or (generic_quote_signals and (product_code_signals or payload_single_item_signals)):
        confidence = 0.82
        if product_code_signals or payload_single_item_signals:
            confidence = 0.92
        elif quantity_signals:
            confidence = 0.78
        return QuotationFlowDecision(
            flow_type="single_item",
            confidence=confidence,
            reason="命中单品查价/库存/价格信号，且未发现客户需求表三或项目方案信号。",
            signals=sorted(set(single_signals + generic_quote_signals + product_code_signals + payload_single_item_signals + quantity_signals)),
            next_action="generate_single_item_reference_quote",
            requires_order_requirement=False,
            quotation_type="单品查询",
        )

    if generic_quote_signals:
        compact_text = raw
        for token in generic_quote_signals:
            compact_text = compact_text.replace(token, "")
        compact_text = compact_text.strip(" ，,。；;：:")
        # “提供报价/报价”本身要追问；但如果同时给出较长产品/配置名称，应视为单品查价。
        if len(compact_text) >= 8:
            return QuotationFlowDecision(
                flow_type="single_item",
                confidence=0.74,
                reason="命中泛化报价意图且包含较完整产品/配置描述，按单品价格查询处理。",
                signals=sorted(set(generic_quote_signals + ["product_description"])),
                next_action="generate_single_item_reference_quote",
                requires_order_requirement=False,
                quotation_type="单品查询",
            )
        return QuotationFlowDecision(
            flow_type="unclear",
            confidence=0.55,
            reason="仅命中泛化报价意图，缺少产品/配置或客户项目/P0信号，需要先确认报价入口。",
            signals=sorted(set(generic_quote_signals)),
            next_action="ask_quotation_flow",
            requires_order_requirement=False,
            quotation_type=None,
        )

    return QuotationFlowDecision(
        flow_type="unclear",
        confidence=0.45,
        reason="未能可靠判断报价入口类型，需要用户确认。",
        signals=[],
        next_action="ask_quotation_flow",
        requires_order_requirement=False,
        quotation_type=None,
    )


def _decision_from_flow(flow_type: str, signals: list[str]) -> QuotationFlowDecision:
    if flow_type == "single_item":
        return QuotationFlowDecision(
            flow_type="single_item",
            confidence=0.99,
            reason="调用方已明确指定单品快速报价。",
            signals=signals,
            next_action="generate_single_item_reference_quote",
            requires_order_requirement=False,
            quotation_type="单品查询",
        )
    if flow_type == "requirement_p0":
        return QuotationFlowDecision(
            flow_type="requirement_p0",
            confidence=0.99,
            reason="调用方已明确指定客户需求表三/P0标准流程。",
            signals=signals,
            next_action="create_order_requirement",
            requires_order_requirement=True,
            quotation_type="方案报价",
        )
    return QuotationFlowDecision(
        flow_type="unclear",
        confidence=0.5,
        reason="调用方指定为待确认报价入口。",
        signals=signals,
        next_action="ask_quotation_flow",
        requires_order_requirement=False,
    )


def quotation_flow_prompt() -> str:
    return (
        "请先确认本次报价入口：\n\n"
        "1️⃣ 单品价格查询：解决的是“查价格”。按产品编码/产品名称/配置直接查价，只输出内部参考报价，不进入正式客户报价流程。\n"
        "2️⃣ 项目需求报价：解决的是“正式客户报价流程”。客户/项目/方案/P0/正式报价必须先保存客户需求表三，再进入需求卡、分流、规则校验、人工确认和客户版输出。"
    )
