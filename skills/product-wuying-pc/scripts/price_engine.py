"""无影云电脑价格引擎
安全规则：无数据不编造，价格全部来自配置/报价数据源，不估算，不打折扣。
字段口径：performance_level 为兼容字段名，业务展示名为“云产品资源配置”，对应报价数据“国内region计算规格名称”。
报价模式：单品查询可按配置/产品名称直接查价；方案报价必须先满足需求清单必要项。
"""
from typing import Dict, List, Optional
import os
import re


class WuyingPCPriceEngine:
    """无影云电脑价格引擎"""

    # 兼容基准价格（点/月）。正式资源配置选项以报价数据源/requirement.json 中“云产品资源配置”为准。
    BASE_PRICES = {
        "基础型（2核4G）": 58,
        "标准型（4核8G）": 118,
        "专业型（8核16G）": 238,
        "高性能型（16核64G+GPU）": 688,
    }

    # 云盘附加费用
    # 云盘附加费用：来自报价数据源“国内region存储规格名称 / 国内增加磁盘（可选）/GiB”。
    # 当前源数据明确给出 100GiB 月价；未明确的容量不估算、不线性推导。
    STORAGE_PRICES = {
        "100GB/用户": 25,
        "不需要": 0,
    }

    DATA_DB_PATH = os.path.expanduser("~/.openclaw/workspace/Knowledge-Library-MVP/hubai_quotes.db")

    HARDWARE_RECOMMENDATION_PRIORITY = [
        "无影魔方AS05（推荐）",
        "无影魔方Ultra-AX01",
        "硬件终端一体机US01",
        "无影方舟笔记本-NE01（推荐）",
    ]

    DURATION_TYPES = {
        "120h": {
            "label": "120小时",
            "aliases": ["120小时", "120h", "D21", "d21"],
            "sheet_keywords": ["120小时"],
        },
        "200h": {
            "label": "200小时",
            "aliases": ["200小时", "200h", "D22图形", "D22国内图形", "图形200小时"],
            "sheet_keywords": ["200小时"],
        },
        "unlimited_1h_sleep": {
            "label": "不限时长（1小时休眠）",
            "aliases": ["不限时长", "不限时", "1小时休眠", "办公1小时休眠", "D22不限时", "D21不限时"],
            "sheet_keywords": ["不限时长", "1小时休眠"],
        },
        "unlimited": {
            "label": "不限时长",
            "aliases": ["D23", "d23", "无强制休眠"],
            "sheet_keywords": ["D23", "不限时长"],
        },
        "education": {
            "label": "教育办公",
            "aliases": ["教育办公", "D1", "d1"],
            "sheet_keywords": ["教育办公"],
        },
    }

    STANDARD_COLUMNS = ["序号", "产品名称", "时长类型", "产品/配置", "数量", "月价", "总价（月）", "一年总价"]
    TERMINAL_COLUMNS = ["序号", "产品名称", "产品/配置", "数量", "单价", "总价"]

    @classmethod
    def _fmt_price(cls, value) -> str:
        try:
            v = float(value or 0)
            return f"¥{v:,.2f}".rstrip("0").rstrip(".")
        except Exception:
            return f"¥{value}"

    @classmethod
    def _money_value(cls, value) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0

    @classmethod
    def _quantity_value(cls, value) -> int:
        try:
            q = int(float(value or 1))
            return q if q > 0 else 1
        except Exception:
            return 1

    @classmethod
    def _extract_quantity_from_text(cls, text: str = "", default: int = 1) -> int:
        match = re.search(r"(\d+)\s*(?:台|套|点|个|人|用户|账号|终端|席)", text or "")
        if match:
            return cls._quantity_value(match.group(1))
        return cls._quantity_value(default)

    @classmethod
    def _normalize_query_text(cls, text: str = "") -> str:
        # 用户常把“无影魔方”写成“无影魔法”，统一到报价库里的产品名。
        return (text or "").replace("无影魔法", "无影魔方").replace("魔法AS", "魔方AS")

    @classmethod
    def _extract_terminal_query(cls, text: str = "") -> str:
        t = cls._normalize_query_text(text)
        patterns = [
            r"无影魔方\s*(?:AS05|Ultra-AX01|AX01)?",
            r"AS05",
            r"Ultra-AX01|AX01",
            r"US01",
            r"NE01",
            r"无影方舟",
            r"一体机",
        ]
        for pattern in patterns:
            m = re.search(pattern, t, flags=re.I)
            if m:
                value = m.group(0).strip()
                if re.fullmatch(r"AS05", value, flags=re.I):
                    return "无影魔方AS05"
                if re.fullmatch(r"AX01", value, flags=re.I):
                    return "无影魔方Ultra-AX01"
                return value
        return ""

    @classmethod
    def _extract_terminal_quantity(cls, text: str = "", default: int = 1) -> int:
        t = cls._normalize_query_text(text)
        # 优先取 AS05/魔方等硬件附近的数量，例如“无影魔方AS05 10台”。
        m = re.search(r"(?:无影魔方\s*(?:AS05|Ultra-AX01|AX01)?|AS05|AX01|US01|NE01|一体机|无影方舟)[^\d]{0,20}(\d+)\s*(?:台|套|个|终端)", t, flags=re.I)
        if not m:
            m = re.search(r"(\d+)\s*(?:台|套|个|终端)[^\n]{0,20}(?:无影魔方\s*(?:AS05|Ultra-AX01|AX01)?|AS05|AX01|US01|NE01|一体机|无影方舟)", t, flags=re.I)
        return cls._quantity_value(m.group(1)) if m else cls._quantity_value(default)


    @classmethod
    def _is_precise_compute_query(cls, query: str = "") -> bool:
        """判断云电脑资源查询是否具备可精准报价的最小条件。"""
        q = cls._normalize_query_text(query)
        if cls._extract_terminal_query(q) and not any(token in q for token in ["图形型", "办公型", "标准型", "核", "内存", "显存", "带宽", "云电脑"]):
            return True
        has_family = any(token in q for token in ["图形型", "办公型", "标准型", "云电脑"])
        has_cpu_mem = bool(re.search(r"\d+\s*核", q)) and bool(re.search(r"\d+\s*G", q, flags=re.I))
        has_duration = bool(cls._normalize_duration_type("", q))
        # 图形型通常还需要显存/GPU信息才能精准落库；办公型可不要求显存。
        if "图形型" in q:
            has_gpu = bool(re.search(r"\d+\s*G\s*显存|T4|5880|GPU", q, flags=re.I))
            return has_family and has_cpu_mem and has_duration and has_gpu
        return has_family and has_cpu_mem and has_duration

    @classmethod
    def _build_precision_question(cls, query: str, duration_options: List[Dict] = None, candidates: List[Dict] = None) -> Dict:
        duration_options = duration_options or []
        candidates = candidates or []
        candidate_names = []
        for row in candidates:
            name = row.get("product_name")
            if name and name not in candidate_names:
                candidate_names.append(name)
            if len(candidate_names) >= 5:
                break
        missing = []
        q = cls._normalize_query_text(query)
        if not any(token in q for token in ["图形型", "办公型", "标准型", "云电脑", "无影魔方", "AS05", "AX01", "US01", "NE01"]):
            missing.append("产品类型/产品名称")
        if not re.search(r"\d+\s*核", q):
            missing.append("CPU核数")
        if not re.search(r"\d+\s*G", q, flags=re.I):
            missing.append("内存规格")
        if "图形型" in q and not re.search(r"\d+\s*G\s*显存|T4|5880|GPU", q, flags=re.I):
            missing.append("显存/GPU规格")
        if not cls._normalize_duration_type("", q) and duration_options:
            missing.append("时长类型")
        if not re.search(r"\d+\s*(?:台|套|点|个|人|用户|账号|终端|席)", q):
            missing.append("数量")
        action_parts = ["请补充能够精准定位报价库的配置后再报价"]
        if missing:
            action_parts.append("缺少：" + "、".join(missing))
        if duration_options:
            action_parts.append("可选时长：" + "、".join(x.get("label", "") for x in duration_options))
        if candidate_names:
            action_parts.append("可能匹配的配置：" + "；".join(candidate_names))
        return {
            "success": False,
            "error_code": "PRICE_MATCH_NOT_PRECISE",
            "error_message": "无法精准匹配到唯一价格配置，需进一步确认后才能报价",
            "details": {
                "query": query,
                "missing_fields": missing,
                "duration_options": duration_options,
                "candidate_products": candidate_names,
                "action": "。".join(action_parts),
            },
        }

    @classmethod
    def _is_hardware_item(cls, item: Dict) -> bool:
        source = item.get("source_sheet") or ""
        name = item.get("name") or item.get("product_name") or ""
        code = item.get("product_code") or ""
        return (
            "终端" in source
            or "TERMINAL" in code.upper()
            or any(token in name for token in ["无影魔方", "终端", "一体机", "方舟", "网关", "信创"])
        )

    @classmethod
    def _hardware_priority(cls, name: str) -> int:
        if name in cls.HARDWARE_RECOMMENDATION_PRIORITY:
            return cls.HARDWARE_RECOMMENDATION_PRIORITY.index(name)
        return len(cls.HARDWARE_RECOMMENDATION_PRIORITY) + 100

    @classmethod
    def _duration_from_source_sheet(cls, source_sheet: str) -> str:
        s = source_sheet or ""
        if "200小时" in s:
            return "200h"
        if "120小时" in s:
            return "120h"
        if "1小时休眠" in s:
            return "unlimited_1h_sleep"
        if "D23" in s and "不限时长" in s:
            return "unlimited"
        if "教育办公" in s:
            return "education"
        return "other"

    @classmethod
    def _duration_label(cls, duration_type: str) -> str:
        return cls.DURATION_TYPES.get(duration_type, {}).get("label", "其他/通用")

    @classmethod
    def _normalize_duration_type(cls, duration_type: str = "", query: str = "") -> str:
        raw = f"{duration_type or ''} {query or ''}".strip()
        if not raw:
            return ""
        for code, cfg in cls.DURATION_TYPES.items():
            if duration_type == code:
                return code
            for alias in cfg["aliases"]:
                if alias and alias in raw:
                    return code
        return duration_type if duration_type in cls.DURATION_TYPES else ""

    @classmethod
    def list_duration_options(cls, rows: List[Dict]) -> List[Dict]:
        seen = []
        for row in rows:
            code = cls._duration_from_source_sheet(row.get("source_sheet") or "")
            if code not in seen:
                seen.append(code)
        return [{"value": code, "label": cls._duration_label(code)} for code in seen if code != "other"]

    @classmethod
    def _filter_by_duration_type(cls, rows: List[Dict], duration_type: str) -> List[Dict]:
        if not duration_type:
            return rows
        return [row for row in rows if cls._duration_from_source_sheet(row.get("source_sheet") or "") == duration_type]

    @classmethod
    def _query_catalog(cls, query: str) -> List[Dict]:
        """从报价数据源产品库按产品名/配置描述模糊查价。

        支持用户把多个关键词连在一起说，例如“图形型-8核16G D22国内图形200小时”。
        先做整体 LIKE；若无结果，再按中英数关键词拆分并用 AND 匹配，避免钉钉自然语言输入查不到。
        """
        import sqlite3
        if not query or not os.path.exists(cls.DATA_DB_PATH):
            return []

        def fetch(where_sql: str, params: tuple, limit: int = 80) -> List[Dict]:
            conn = sqlite3.connect(cls.DATA_DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            rows = cur.execute(
                f"""
                SELECT p.product_code, p.product_name, p.unit, p.brand, p.model, p.short_description,
                       pp.unit_price, pp.currency, pp.price_type,
                       COALESCE(pp.billing_period, '') AS billing_period,
                       COALESCE(pp.source_sheet, p.source_sheet, '') AS source_sheet,
                       COALESCE(pp.unit_label, '') AS unit_label
                FROM product p
                JOIN product_price pp ON pp.product_code = p.product_code AND pp.status = 'active'
                WHERE p.status = 'active'
                  AND ({where_sql})
                ORDER BY CASE WHEN p.product_name = ? THEN 0 WHEN p.product_name LIKE ? THEN 1 ELSE 2 END,
                         p.id,
                         CASE pp.price_type WHEN '1month' THEN 0 WHEN '1year' THEN 1 ELSE 2 END
                LIMIT {limit}
                """,
                params + (query, f"%{query}%"),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]

        like_params = (f"%{query}%", f"%{query}%", f"%{query}%")
        rows = fetch(
            "p.product_name LIKE ? OR COALESCE(p.short_description,'') LIKE ? OR COALESCE(p.model,'') LIKE ?",
            like_params,
        )
        if rows:
            return rows

        # 拆分复合输入；优先保留能显著缩小范围的 token。
        raw_tokens = re.findall(r"[A-Za-z]+\d*|\d+核|\d+G|\d+小时|[\u4e00-\u9fff]{2,}|\d+", query)
        stopwords = {"报价", "价格", "单品", "查询", "一下", "多少", "多少钱", "提供", "重新", "国内"}
        tokens = []
        for token in raw_tokens:
            t = token.strip()
            if not t or t in stopwords:
                continue
            if t not in tokens:
                tokens.append(t)

        # 单独输入价格场景（如 D22国内图形200小时）时，源数据通常在 source_sheet 而不是产品名。
        if tokens and any(re.fullmatch(r"D\d+", t, flags=re.I) for t in tokens):
            where_parts = []
            params = []
            for token in tokens:
                where_parts.append("(p.product_name LIKE ? OR COALESCE(p.short_description,'') LIKE ? OR COALESCE(p.model,'') LIKE ? OR COALESCE(pp.source_sheet, p.source_sheet, '') LIKE ?)")
                params.extend([f"%{token}%", f"%{token}%", f"%{token}%", f"%{token}%"])
            rows = fetch(" AND ".join(where_parts), tuple(params))
            if rows:
                return rows

        for count in range(min(len(tokens), 4), 0, -1):
            chosen = tokens[:count]
            where_parts = []
            params = []
            for token in chosen:
                where_parts.append("(p.product_name LIKE ? OR COALESCE(p.short_description,'') LIKE ? OR COALESCE(p.model,'') LIKE ?)")
                params.extend([f"%{token}%", f"%{token}%", f"%{token}%"])
            rows = fetch(" AND ".join(where_parts), tuple(params))
            if rows:
                return rows
        return []

    # 方案报价必要项：报价类型在协调器层先确认，这里校验方案报价内容项。
    REQUIRED_SOLUTION_FIELDS = [
        "customer_company",
        "contact_person",
        "deployment_scale",
        "usage_scenario",
        "performance_level",
        "sleep_policy",
        "quantity",
    ]

    @classmethod
    def get_price(cls, performance_level: str, duration_type: str = "") -> Optional[Dict]:
        """获取云产品资源配置价格。

        优先从正式报价数据库 product/product_price 查；仅在数据库无匹配时才回退到
        兼容 BASE_PRICES。无数据返回 None，不编造、不估算。
        """
        q = (performance_level or "").strip()
        normalized_duration = cls._normalize_duration_type(duration_type, q)
        if not q:
            return None

        catalog_matches = cls._query_catalog(q)
        if normalized_duration:
            filtered = cls._filter_by_duration_type(catalog_matches, normalized_duration)
            if filtered:
                catalog_matches = filtered
        exact_match = None
        if catalog_matches:
            exact_candidates = [row for row in catalog_matches if row.get("product_name") == q]
            price_candidates = exact_candidates or catalog_matches
            exact_match = next((row for row in price_candidates if row.get("price_type") == "1month"), price_candidates[0])

        if exact_match:
            return {
                "spec": exact_match.get("product_name") or q,
                "unit_price": exact_match.get("unit_price"),
                "currency": exact_match.get("currency") or "CNY",
                "unit": exact_match.get("unit") or "套",
                "product_code": exact_match.get("product_code"),
                "price_type": exact_match.get("price_type"),
                "billing_period": exact_match.get("billing_period"),
                "source_sheet": exact_match.get("source_sheet"),
                "unit_label": exact_match.get("unit_label"),
                "data_source": "product_price_db",
            }

        if q not in cls.BASE_PRICES:
            return None
        return {
            "spec": q,
            "unit_price": cls.BASE_PRICES[q],
            "currency": "CNY",
            "unit": "点/月",
            "data_source": "config",
        }

    @classmethod
    def get_discount(cls, scale: str = "") -> Dict:
        """报价系统不打折扣，始终返回原价。保留方法用于兼容旧调用。"""
        return {
            "discount_rate": 1.0,
            "data_source": "no_discount_policy",
            "note": "按报价数据源原价报价，不做折扣",
        }

    @classmethod
    def validate_solution_requirement(cls, requirement_data: Dict) -> Dict:
        """校验方案报价必要项。"""
        missing = []
        for field in cls.REQUIRED_SOLUTION_FIELDS:
            value = requirement_data.get(field)
            if value in (None, "", [], {}):
                missing.append(field)
        return {
            "ok": not missing,
            "missing_fields": missing,
            "required_fields": cls.REQUIRED_SOLUTION_FIELDS,
        }

    @classmethod
    def query_single_item(cls, query: str = "", product_name: str = "", config_name: str = "", duration_type: str = "", quantity: int = None) -> Dict:
        """单品查询：按配置或产品名称直接查价，并支持按时长类型过滤。"""
        q = cls._normalize_query_text((config_name or product_name or query or "").strip())
        quantity = cls._extract_quantity_from_text(q, default=quantity or 1)
        normalized_duration = cls._normalize_duration_type(duration_type, q)
        if not q:
            return {
                "success": False,
                "error_code": "SINGLE_ITEM_QUERY_EMPTY",
                "error_message": "请提供要查询的云产品资源配置、硬件设备或产品名称",
            }

        catalog_rows = cls._query_catalog(q)
        duration_options = cls.list_duration_options(catalog_rows)
        if normalized_duration:
            catalog_rows = cls._filter_by_duration_type(catalog_rows, normalized_duration)

        terminal_only_query = bool(cls._extract_terminal_query(q)) and not any(token in q for token in ["图形型", "办公型", "标准型", "云电脑", "核", "内存", "显存", "带宽"])
        if catalog_rows and not terminal_only_query and not cls._is_precise_compute_query(q):
            return cls._build_precision_question(q, duration_options=duration_options, candidates=catalog_rows)

        if not normalized_duration and len(duration_options) > 1:
            option_text = "、".join([x['label'] for x in duration_options])
            return {
                "success": False,
                "error_code": "DURATION_TYPE_REQUIRED",
                "error_message": "该产品存在多个时长类型，请先选择时长类型后再查询报价",
                "details": {
                    "query": q,
                    "duration_options": duration_options,
                    "action": f"请选择一个时长类型：{option_text}",
                },
            }

        preferred_price_types = {"1month", "1year"}
        preferred_rows = [row for row in catalog_rows if row.get("price_type") in preferred_price_types]
        # 产品查询对话只展示月价和一年价；若某类产品本身没有这两种周期，才保留原始可用价格。
        display_rows = preferred_rows or catalog_rows

        matches = []
        for row in display_rows:
            duration_code = cls._duration_from_source_sheet(row.get("source_sheet") or "")
            matches.append({
                "name": row.get("product_name"),
                "product_code": row.get("product_code"),
                "unit_price": row.get("unit_price"),
                "quantity": quantity,
                "currency": row.get("currency") or "CNY",
                "unit": row.get("unit") or "项",
                "price_type": row.get("price_type"),
                "billing_period": row.get("billing_period"),
                "source_sheet": row.get("source_sheet"),
                "duration_type": duration_code,
                "duration_label": cls._duration_label(duration_code),
                "unit_label": row.get("unit_label"),
                "data_source": "product_price_db",
                "discount_rate": 1.0,
                "discount_note": "按报价数据源原价报价，不做折扣",
            })

        for name, price in cls.BASE_PRICES.items():
            if q in name or name in q:
                matches.append({
                    "name": name,
                    "unit_price": price,
                    "quantity": quantity,
                    "currency": "CNY",
                    "unit": "点/月",
                    "duration_type": normalized_duration or "other",
                    "duration_label": cls._duration_label(normalized_duration or "other"),
                    "data_source": "config",
                    "discount_rate": 1.0,
                    "discount_note": "按报价数据源原价报价，不做折扣",
                })

        terminal_query = cls._extract_terminal_query(q)
        if terminal_query:
            terminal_price = cls._find_terminal_price(terminal_query)
            if terminal_price:
                terminal_qty = cls._extract_terminal_quantity(q, default=quantity)
                terminal_key = terminal_price.get("product_code") or terminal_price.get("name")
                if not any((m.get("product_code") or m.get("name")) == terminal_key for m in matches):
                    matches.append({
                        "name": terminal_price.get("name"),
                        "product_code": terminal_price.get("product_code"),
                        "unit_price": terminal_price.get("unit_price"),
                        "quantity": terminal_qty,
                        "currency": "CNY",
                        "unit": terminal_price.get("unit") or "台",
                        "price_type": terminal_price.get("price_type") or "standard",
                        "source_sheet": terminal_price.get("source_sheet") or "C0-终端描述汇总",
                        "duration_type": "terminal",
                        "duration_label": "-",
                        "unit_label": terminal_price.get("unit_label") or "元/台",
                        "data_source": terminal_price.get("data_source") or "product_price_db",
                        "discount_rate": 1.0,
                        "discount_note": "按报价数据源原价报价，不做折扣",
                    })

        matches.sort(key=lambda item: (cls._hardware_priority(item.get("name", "")), item.get("source_sheet", ""), item.get("name", "")))

        if not matches:
            if not cls._is_precise_compute_query(q) and not cls._extract_terminal_query(q):
                return cls._build_precision_question(q, duration_options=duration_options, candidates=catalog_rows)
            return {
                "success": False,
                "error_code": "SINGLE_ITEM_NOT_FOUND",
                "error_message": f"未找到单品 '{q}' 的价格配置",
                "details": {
                    "query": q,
                    "duration_type": normalized_duration,
                    "duration_options": duration_options,
                    "available_specs": list(cls.BASE_PRICES.keys()),
                    "action": "请提供准确的配置名称、产品名称和时长类型；如果是方案报价，请先选择【方案报价】并补齐需求清单",
                },
            }

        return {
            "success": True,
            "quote_type": "single_item",
            "query": q,
            "duration_type": normalized_duration,
            "duration_label": cls._duration_label(normalized_duration) if normalized_duration else "未指定",
            "duration_options": duration_options,
            "items": matches,
            "message": cls.format_single_item_quote(matches, query=q, duration_type=normalized_duration, quantity=quantity),
        }

    @classmethod
    def quote(cls, requirement_data: Dict) -> Dict:
        """统一报价接口。

        quotation_type:
        - 单品查询：可按 query/product_name/config_name/performance_level 直接查价。
        - 方案报价：必须补齐 REQUIRED_SOLUTION_FIELDS 后才能报价。
        """
        quotation_type = requirement_data.get("quotation_type") or requirement_data.get("quote_type")
        if quotation_type in ("单品查询", "single_item"):
            return cls.query_single_item(
                query=requirement_data.get("query", ""),
                product_name=requirement_data.get("product_name", ""),
                config_name=requirement_data.get("config_name") or requirement_data.get("performance_level", ""),
                duration_type=requirement_data.get("duration_type") or requirement_data.get("time_type") or requirement_data.get("billing_duration", ""),
                quantity=requirement_data.get("quantity", 1),
            )

        if quotation_type not in ("方案报价", "solution"):
            return {
                "success": False,
                "error_code": "QUOTATION_TYPE_REQUIRED",
                "error_message": "报价前必须先确认是【单品查询】还是【方案报价】",
                "details": {
                    "available_types": ["单品查询", "方案报价"],
                    "action": "请先选择报价类型",
                },
            }

        validation = cls.validate_solution_requirement(requirement_data)
        if not validation["ok"]:
            return {
                "success": False,
                "error_code": "REQUIREMENT_INCOMPLETE",
                "error_message": "方案报价需求清单必要项未补齐，暂不能报价",
                "details": validation,
            }

        performance = requirement_data.get("performance_level")
        sleep_policy = requirement_data.get("sleep_policy")
        scale = requirement_data.get("deployment_scale")
        storage = requirement_data.get("cloud_storage", "不需要")
        quantity = cls._quantity_value(requirement_data.get("quantity", 1))
        months = requirement_data.get("months", 12)
        duration_type = requirement_data.get("duration_type") or requirement_data.get("time_type") or requirement_data.get("billing_duration", "")

        price_info = cls.get_price(performance, duration_type=duration_type)
        if not price_info:
            return {
                "success": False,
                "error_code": "PRICE_NOT_FOUND",
                "error_message": f"云产品资源配置 '{performance}' 无价格配置",
                "details": {
                    "available_specs": list(cls.BASE_PRICES.keys()),
                    "action": "请选择有效的云产品资源配置",
                },
            }

        if storage not in cls.STORAGE_PRICES:
            return {
                "success": False,
                "error_code": "STORAGE_NOT_FOUND",
                "error_message": f"云盘配置 '{storage}' 无价格配置",
                "details": {
                    "available_storage": list(cls.STORAGE_PRICES.keys()),
                    "action": "请选择有效的云盘配置",
                },
            }

        unit_price = cls._money_value(price_info["unit_price"])  # 不打折扣
        storage_price = cls.STORAGE_PRICES[storage]
        cloud_month_price = unit_price + storage_price
        monthly_total = cloud_month_price * quantity
        one_year_total = monthly_total * 12
        total_amount = monthly_total * months

        terminal_items = []
        raw_device_types = requirement_data.get("device_type") or requirement_data.get("terminal_type") or requirement_data.get("hardware_device") or []
        if isinstance(raw_device_types, str):
            raw_device_types = [raw_device_types]
        for device_type in raw_device_types:
            terminal = cls._find_terminal_price(device_type)
            if terminal:
                terminal_items.append({**terminal, "quantity": quantity})
        terminal_rows = cls._group_terminal_rows(terminal_items, quantity)
        terminal_total = sum(cls._quantity_value(r.get("quantity")) * cls._money_value(r.get("unit_price")) for r in terminal_rows)

        cloud_rows = [{
            "product_name": "无影云电脑",
            "duration_label": cls._duration_label(duration_type) if duration_type else (price_info.get("source_sheet") or "未指定"),
            "config": performance,
            "quantity": quantity,
            "month_price": round(cloud_month_price, 2),
        }]
        message = cls._format_unified_quote_message(
            cloud_rows,
            terminal_rows,
            title="无影需求/项目报价（统一格式）",
            note="需求/项目报价按客户需求表三信息生成；正式对客户输出前仍需规则校验、人工确认和审批。",
        )

        return {
            "success": True,
            "quote_type": "solution",
            "product_code": "wuying-pc",
            "product_name": "无影云电脑",
            "data_source": price_info["data_source"],
            "performance_level": performance,
            "resource_config": performance,
            "sleep_policy": sleep_policy,
            "scale": scale,
            "storage": storage,
            "quantity": quantity,
            "months": months,
            "unit_price_original": price_info["unit_price"],
            "unit": price_info.get("unit", "套"),
            "price_product_code": price_info.get("product_code"),
            "price_type": price_info.get("price_type"),
            "discount_rate": 1.0,
            "discount_source": "no_discount_policy",
            "discount_note": "按报价数据源原价报价，不做折扣",
            "storage_price": storage_price,
            "unit_price_final": round(unit_price, 2),
            "cloud_month_price": round(cloud_month_price, 2),
            "monthly_total": round(monthly_total, 2),
            "one_year_total": round(one_year_total, 2),
            "terminal_total": round(terminal_total, 2),
            "combined_month_total": round(monthly_total + terminal_total, 2),
            "combined_one_year_total": round(one_year_total + terminal_total, 2),
            "total_amount": round(total_amount + terminal_total, 2),
            "currency": "CNY",
            "cloud_rows": cloud_rows,
            "terminal_rows": terminal_rows,
            "message": message,
        }

    @classmethod
    def calculate_price(cls, performance_level: str = None, scale: str = None,
                        storage: str = "不需要", months: int = 12,
                        quantity: int = 1, quotation_type: str = "方案报价", **kwargs) -> Dict:
        """兼容旧接口。"""
        data = dict(kwargs)
        data.update({
            "quotation_type": quotation_type,
            "performance_level": performance_level,
            "deployment_scale": scale,
            "cloud_storage": storage,
            "quantity": quantity,
            "months": months,
        })
        return cls.quote(data)

    @classmethod
    def _split_quote_items(cls, items: List[Dict]) -> tuple[List[Dict], List[Dict]]:
        cloud_items = []
        terminal_items = []
        for item in items:
            if cls._is_hardware_item(item):
                terminal_items.append(item)
            else:
                terminal_items.append(item) if item.get("price_type") == "standard" else cloud_items.append(item)
        return cloud_items, terminal_items

    @classmethod
    def _group_cloud_rows(cls, items: List[Dict], quantity: int) -> List[Dict]:
        grouped: Dict[str, Dict] = {}
        for item in items:
            key = f"{item.get('source_sheet') or '默认'}||{item.get('duration_type') or 'other'}||{item.get('name') or ''}"
            row = grouped.setdefault(key, {
                "product_name": "无影云电脑",
                "config": item.get("name") or "",
                "duration_label": item.get("duration_label") or cls._duration_label(item.get("duration_type") or "other"),
                "quantity": cls._quantity_value(item.get("quantity") or quantity),
                "month_price": None,
            })
            if item.get("price_type") == "1month":
                row["month_price"] = cls._money_value(item.get("unit_price"))
            elif row["month_price"] is None and item.get("price_type") not in {"1year", "2year", "3year", "4year", "5year", "6year"}:
                row["month_price"] = cls._money_value(item.get("unit_price"))
        return list(grouped.values())

    @classmethod
    def _group_terminal_rows(cls, items: List[Dict], quantity: int) -> List[Dict]:
        grouped: Dict[str, Dict] = {}
        for item in items:
            key = item.get("name") or item.get("product_code") or "默认终端"
            row = grouped.setdefault(key, {
                "product_name": "无影终端",
                "config": item.get("name") or "",
                "quantity": cls._quantity_value(item.get("quantity") or quantity),
                "unit_price": None,
            })
            if row["unit_price"] is None:
                row["unit_price"] = cls._money_value(item.get("unit_price"))
        return list(grouped.values())

    @classmethod
    def _format_unified_quote_message(
        cls,
        cloud_rows: List[Dict],
        terminal_rows: List[Dict],
        title: str = "无影报价（统一格式）",
        query: str = "",
        note: str = "以上为内部参考报价；正式客户/项目/方案报价必须先进入客户需求表三并经人工确认。",
    ) -> str:
        lines = [title]
        if query:
            lines.extend(["", f"- 查询对象：{query}"])
        lines.extend(["", "云电脑资源报价："])
        lines.extend([
            "",
            "| 序号 | 产品名称 | 时长类型 | 产品/配置 | 数量 | 月价 | 总价（月） | 一年总价 |",
            "|---:|---|---|---|---:|---:|---:|---:|",
        ])
        cloud_month_total_sum = 0.0
        cloud_year_total_sum = 0.0
        if cloud_rows:
            for idx, row in enumerate(cloud_rows, start=1):
                qty = cls._quantity_value(row.get("quantity"))
                month_price = row.get("month_price")
                if month_price is None:
                    month_price_display = "-"
                    month_total_display = "-"
                    year_total_display = "-"
                else:
                    month_price = cls._money_value(month_price)
                    month_total = qty * month_price
                    year_total = month_total * 12
                    cloud_month_total_sum += month_total
                    cloud_year_total_sum += year_total
                    month_price_display = cls._fmt_price(month_price)
                    month_total_display = cls._fmt_price(month_total)
                    year_total_display = cls._fmt_price(year_total)
                lines.append(
                    f"| {idx} | {row.get('product_name') or '无影云电脑'} | {row.get('duration_label') or '-'} | {row.get('config') or '-'} | {qty} | {month_price_display} | {month_total_display} | {year_total_display} |"
                )
        else:
            lines.append("| - | 无影云电脑 | - | 未选择/未匹配 | 0 | - | ¥0 | ¥0 |")

        lines.extend(["", "无影终端报价：", ""])
        lines.extend([
            "| 序号 | 产品名称 | 产品/配置 | 数量 | 单价 | 总价 |",
            "|---:|---|---|---:|---:|---:|",
        ])
        terminal_total_sum = 0.0
        if terminal_rows:
            for idx, row in enumerate(terminal_rows, start=1):
                qty = cls._quantity_value(row.get("quantity"))
                unit_price = cls._money_value(row.get("unit_price"))
                total = qty * unit_price
                terminal_total_sum += total
                lines.append(
                    f"| {idx} | {row.get('product_name') or '无影终端'} | {row.get('config') or '-'} | {qty} | {cls._fmt_price(unit_price)} | {cls._fmt_price(total)} |"
                )
        else:
            lines.append("| - | 无影终端 | 未选择/不需要 | 0 | ¥0 | ¥0 |")

        combined_month = cloud_month_total_sum + terminal_total_sum
        combined_year = cloud_year_total_sum + terminal_total_sum
        lines.extend([
            "",
            "汇总：",
            f"- 云电脑资源月总价：{cls._fmt_price(cloud_month_total_sum)}",
            f"- 云电脑资源一年总价：{cls._fmt_price(cloud_year_total_sum)}",
            f"- 无影终端总价：{cls._fmt_price(terminal_total_sum)}",
            f"- 首月合计（云电脑月总价 + 终端总价）：{cls._fmt_price(combined_month)}",
            f"- 一年合计（云电脑一年总价 + 终端总价）：{cls._fmt_price(combined_year)}",
            "",
            "计算口径：总价（月）= 数量 × 月价；一年总价 = 总价（月） × 12；无影终端总价 = 数量 × 单价。",
        ])
        if note:
            lines.extend(["", f"说明：{note}"])
        return "\n".join(lines).strip()

    @classmethod
    def _find_terminal_price(cls, device_type: str = "") -> Optional[Dict]:
        q = cls._normalize_query_text((device_type or "").strip())
        if not q or q in {"不需要", "暂不确定", "无"}:
            return None
        rows = [row for row in cls._query_catalog(q) if cls._is_hardware_item({
            "source_sheet": row.get("source_sheet"),
            "name": row.get("product_name"),
            "product_code": row.get("product_code"),
        })]
        if not rows:
            return None
        rows.sort(key=lambda row: (cls._hardware_priority(row.get("product_name", "")), row.get("product_name", "")))
        row = rows[0]
        return {
            "name": row.get("product_name") or q,
            "product_code": row.get("product_code"),
            "unit_price": cls._money_value(row.get("unit_price")),
            "unit": row.get("unit") or "台",
            "source_sheet": row.get("source_sheet"),
            "price_type": row.get("price_type"),
            "unit_label": row.get("unit_label"),
            "data_source": "product_price_db",
        }

    @classmethod
    def format_single_item_quote(cls, items: List[Dict], query: str = "", duration_type: str = "", quantity: int = 1) -> str:
        if not items:
            return "单品查询报价：暂无可展示价格。"
        quantity = cls._quantity_value(quantity or cls._extract_quantity_from_text(query, default=1))
        cloud_items, terminal_items = cls._split_quote_items(items)
        cloud_rows = cls._group_cloud_rows(cloud_items, quantity)
        terminal_rows = cls._group_terminal_rows(terminal_items, quantity)
        selected_duration = cls._duration_label(duration_type) if duration_type else "未指定"
        return cls._format_unified_quote_message(
            cloud_rows,
            terminal_rows,
            title="单品查询报价（统一格式）",
            query=query or "-",
            note=f"单品查询为内部参考报价；时长类型：{selected_duration}；正式客户/项目/方案报价必须先进入客户需求表三并经人工确认。",
        )

    @classmethod
    def generate_quotation_summary(cls, requirement_data: Dict) -> str:
        """生成报价摘要。"""
        result = cls.quote(requirement_data)

        if not result.get("success"):
            return f"""
❌ 报价失败
原因：{result.get('error_message', '未知错误')}

{result.get('details', {}).get('action', '请联系管理员')}
"""

        if result.get("quote_type") == "single_item":
            return result.get("message", "")

        if result.get("message"):
            return result.get("message")

        return f"""
无影云电脑方案报价摘要：
📦 云产品资源配置：{result['performance_level']}
👥 部署规模：{result['scale']}
🌙 休眠方式：{result.get('sleep_policy', 'N/A')}
💾 云盘空间：{result['storage']}
💰 计算单价：¥{result['unit_price_final']}/点/月
💾 云盘单价：¥{result['storage_price']}/点/月
📅 {result['months']}个月总价：¥{result['total_amount']}
📌 价格策略：按报价数据源原价报价，不做折扣
💾 数据来源：{result['data_source']}
"""
