from __future__ import annotations

import csv
import io
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.security import DEMO_USERS, get_user
from app.service import answer_query
from app.hubai_service import (
    product_search,
    product_detail,
    product_ask,
    check_stock,
    generate_quotation,
    blog_search,
    blog_ask,
    knowledge_search,
    knowledge_ask,
    route_assistant,
    upsert_product_records,
)
from app.db import fetch_all, fetch_one, get_conn
from app.quotation_flow import classify_quotation_entry

app = FastAPI(
    title="HubAI 企业知识库基础版",
    description="HubAI 基础版：财务/产品/报价/博文四类数字员工统一底座，支持 SQLite + FTS5 关键词检索。",
    version="0.2.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

UPLOAD_ROOT = Path("/app/data/uploads") if Path("/app").exists() else Path("data/uploads")
STORAGE_PATHS = {
    "map": {"label": "00-知识地图", "path": "企业知识库/00-知识地图", "desc": "知识库总览、主题索引、场景索引、FAQ索引、版本维护记录"},
    "shared_product": {"label": "01-共享知识库/产品资料", "path": "企业知识库/01-共享知识库/产品资料", "desc": "产品彩页、产品说明、成功案例、通用FAQ"},
    "finance": {"label": "02-财务知识库", "path": "企业知识库/02-财务知识库", "desc": "财务制度、预算规则、报表模板、指标口径、审计规范"},
    "commerce": {"label": "03-商务知识库", "path": "企业知识库/03-商务知识库", "desc": "合同模板、报价政策、库存规则、订单流程、供应商档案"},
    "sales": {"label": "04-销售知识库", "path": "企业知识库/04-销售知识库", "desc": "销售话术、客户案例、竞品资料、商机流程、报价参考"},
    "tech": {"label": "05-技术知识库", "path": "企业知识库/05-技术知识库", "desc": "产品参数、技术方案、实施文档、故障手册、API文档"},
    "index": {"label": "06-知识切片与索引", "path": "企业知识库/06-知识切片与索引", "desc": "chunks、vectors、graph、metadata 等索引产物"},
    "eval": {"label": "07-评测集", "path": "企业知识库/07-评测集", "desc": "财务/商务/销售/技术问答测试集、权限边界、幻觉检测"},
    "raw_finance": {"label": "原始数据/财务报表", "path": "原始数据/01-财务报表", "desc": "Excel/CSV 财务报表、销售回款、预算执行原始数据"},
    "raw_product": {"label": "原始数据/产品主数据", "path": "原始数据/02-产品主数据", "desc": "产品主数据、规格、FAQ、产品价格 CSV/JSON"},
    "raw_quotation": {"label": "原始数据/报价库存", "path": "原始数据/03-报价库存", "desc": "价格表、折扣策略、库存表、报价单原始数据"},
    "raw_blog": {"label": "原始数据/博文资料", "path": "原始数据/04-博文资料", "desc": "悟空系列文章、选题、素材、Markdown 文档"},
}


def ensure_storage_paths() -> None:
    for item in STORAGE_PATHS.values():
        (UPLOAD_ROOT / item["path"]).mkdir(parents=True, exist_ok=True)


def infer_storage_key(filename: str, selected_key: str = "auto") -> tuple[str, str]:
    """Rule-based path classifier for uploaded raw files.

    基础版优先使用规则判断，避免为了简单分类引入本地大模型。
    后续若需要识别 Excel 表头语义/多 sheet 内容，再接入本地 Qwen/Ollama。
    """
    if selected_key and selected_key != "auto":
        return selected_key, "manual_selected"
    name = (filename or "").lower()
    quote_words = ["报价", "价格", "价目", "price", "quotation", "quote", "库存", "inventory", "stock", "折扣", "discount", "商业版", "订单", "合同"]
    product_words = ["产品", "product", "sku", "清单", "规格", "参数", "型号", "faq"]
    finance_words = ["财务", "销售额", "回款", "预算", "利润", "报表", "finance", "sales", "budget"]
    blog_words = ["博文", "文章", "悟空", "素材", "选题", "blog", "article"]
    tech_words = ["技术", "方案", "部署", "api", "接口", "实施", "故障"]

    if any(w in name for w in quote_words):
        return "raw_quotation", "auto_filename_quotation"
    if any(w in name for w in finance_words):
        return "raw_finance", "auto_filename_finance"
    if any(w in name for w in blog_words):
        return "raw_blog", "auto_filename_blog"
    if any(w in name for w in tech_words):
        return "tech", "auto_filename_tech"
    if any(w in name for w in product_words):
        return "raw_product", "auto_filename_product"
    return "raw_product", "auto_default_product"


class ChatRequest(BaseModel):
    message: str = Field(..., examples=["查我上个月销售额"])
    user_id: str = Field("u_sales_zhang", examples=["u_sales_zhang"])


class ProductSearchRequest(BaseModel):
    query: str = ""
    category: str | None = None


class ProductAskRequest(BaseModel):
    question: str
    product_code: str | None = None


class ProductUpsertRequest(BaseModel):
    records: list[dict]
    source: str = "api_json"


class QuotationRequest(BaseModel):
    customer_code: str = "C001"
    items: list[dict]
    created_by: str = "system"
    flow_type: str | None = None
    quotation_type: str | None = None
    message: str | None = None


class QuotationClassifyRequest(BaseModel):
    message: str = ""
    payload: dict | None = None


class OrderRequirementCreateRequest(BaseModel):
    customer_name: str
    customer_contact_name: str | None = None
    source_channel: str = "web"
    raw_requirement: str
    attachment_links: str | None = None
    customer_expected_time: str | None = None
    is_urgent: bool = False
    has_historical_project: bool = False
    sales_owner_user_id: str | None = None
    output_proposal_required: bool = False
    output_quotation_required: bool = True
    created_by: str = "web"


class BlogSearchRequest(BaseModel):
    query: str = ""
    status: str | None = None


class KnowledgeSearchRequest(BaseModel):
    query: str
    filters: dict | None = None


class KnowledgeAskRequest(BaseModel):
    question: str
    user_id: str = "u_sales_zhang"


# Health --------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "hubai-knowledge-base", "version": "0.2.0"}


# Home ----------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    ensure_storage_paths()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "users": DEMO_USERS,
            "storage_paths": STORAGE_PATHS,
            "upload_root": str(UPLOAD_ROOT),
            "examples": [
                "查我上个月销售额",
                "Q1 回款多少",
                "各部门销售额对比",
                "HubAI 智能网关有哪些参数",
                "报价 P-AI-GW-001 1 套",
                "P-AI-GW-001 库存多少",
                "悟空系列中哪篇讲 RAG",
                "怎么构建企业知识库",
                "看看有没有异常预警",
            ],
        },
    )


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    ensure_storage_paths()
    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "storage_paths": STORAGE_PATHS,
            "upload_root": str(UPLOAD_ROOT),
        },
    )


@app.get("/api/storage/paths")
def api_storage_paths() -> dict:
    ensure_storage_paths()
    return {"upload_root": str(UPLOAD_ROOT), "paths": STORAGE_PATHS}


@app.post("/api/storage/upload")
async def api_storage_upload(
    file: UploadFile = File(...),
    storage_key: str = Form("auto"),
    auto_import: bool = Form(False),
) -> dict:
    ensure_storage_paths()
    safe_name = Path(file.filename or "upload.bin").name
    resolved_key, infer_reason = infer_storage_key(safe_name, storage_key)
    if resolved_key not in STORAGE_PATHS:
        return {"error": "invalid_storage_key", "storage_key": storage_key, "valid_keys": ["auto", *list(STORAGE_PATHS)]}
    target_dir = UPLOAD_ROOT / STORAGE_PATHS[resolved_key]["path"]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    target_path = target_dir / f"{timestamp}_{safe_name}"
    with target_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    result = {
        "filename": file.filename,
        "requested_storage_key": storage_key,
        "storage_key": resolved_key,
        "storage_label": STORAGE_PATHS[resolved_key]["label"],
        "storage_path": STORAGE_PATHS[resolved_key]["path"],
        "infer_reason": infer_reason,
        "stored_path": str(target_path),
        "auto_import": auto_import,
    }
    if auto_import and safe_name.lower().endswith(".csv") and resolved_key in {"raw_product", "raw_quotation", "shared_product", "commerce"}:
        content = target_path.read_text(encoding="utf-8-sig")
        records = [dict(row) for row in csv.DictReader(io.StringIO(content))]
        result["import_result"] = upsert_product_records(records, f"upload:{resolved_key}:{safe_name}")
    return result


# Unified assistant chat ----------------------------------------------
@app.post("/api/chat")
def chat(payload: ChatRequest) -> JSONResponse:
    user = get_user(payload.user_id)
    result = route_assistant(payload.message, user)
    return JSONResponse({"user": user.__dict__, **result})


@app.get("/api/query")
def query(message: str = Query(...), user_id: str = Query("u_sales_zhang")) -> JSONResponse:
    user = get_user(user_id)
    result = route_assistant(message, user)
    return JSONResponse({"user": user.__dict__, **result})


# Finance (backward-compatible) ---------------------------------------
@app.post("/api/finance/chat")
def finance_chat(payload: ChatRequest) -> JSONResponse:
    user = get_user(payload.user_id)
    result = answer_query(payload.message, user)
    return JSONResponse({"user": user.__dict__, **result})


# Product assistant ---------------------------------------------------
@app.get("/api/products")
def api_products(
    query: str = Query(""),
    category: str | None = Query(None),
    product_type: str | None = Query(None),
    scenario: str | None = Query(None),
    limit: int = Query(20),
) -> dict:
    return product_search(query, category, product_type, scenario, limit)


@app.get("/api/sales/demo-data")
def api_sales_demo_data(product_type: str | None = Query(None), scenario: str | None = Query(None), price_type: str | None = Query(None)) -> dict:
    """Sales assistant display data sourced from current database."""
    products = product_search("", None, product_type, scenario, 16).get("items", [])
    price_clauses = ["pp.status = 'active'"]
    price_params: list[str] = []
    if product_type:
        price_clauses.append("p.product_type = ?")
        price_params.append(product_type)
    if scenario:
        if scenario == "domestic":
            price_clauses.append("p.region_scope = 'domestic'")
        elif scenario == "international":
            price_clauses.append("p.region_scope = 'international'")
        elif scenario == "education":
            price_clauses.append("(p.source_sheet LIKE '%教育%' OR p.category_code = 'CAT_WUYING_EDU_COMPUTE')")
        elif scenario == "enterprise":
            price_clauses.append("p.region_scope = 'enterprise'")
        elif scenario == "common":
            price_clauses.append("p.region_scope = 'common'")
    price_rows = fetch_all(
        f"""
        SELECT pp.price_type, COALESCE(NULLIF(pp.billing_period,''), pp.price_type) AS billing_period, COUNT(*) AS count
        FROM product_price pp
        JOIN product p ON p.product_code = pp.product_code
        WHERE {' AND '.join(price_clauses)}
        GROUP BY pp.price_type, COALESCE(NULLIF(pp.billing_period,''), pp.price_type)
        ORDER BY CASE pp.price_type
          WHEN '1month' THEN 1 WHEN '1year' THEN 2 WHEN '2year' THEN 3 WHEN '3year' THEN 4
          WHEN '4year' THEN 5 WHEN '5year' THEN 6 WHEN '6year' THEN 7 WHEN 'standard' THEN 8 WHEN 'hourly' THEN 9 ELSE 99 END
        """,
        tuple(price_params),
    )
    price_type_options = [{"value": "", "label": "默认价格"}]
    seen_price = set()
    label_map = {"1month": "1个月", "1year": "1年", "2year": "2年", "3year": "3年", "4year": "4年", "5year": "5年", "6year": "6年", "standard": "标准价/台", "hourly": "小时价", "unlimited": "不限时"}
    for r in price_rows:
        v = r["price_type"]
        if v in seen_price:
            continue
        seen_price.add(v)
        price_type_options.append({"value": v, "label": label_map.get(v, r["billing_period"] or v)})

    enriched = []
    selected_price_type = price_type or ""
    for item in products:
        product_code = item["product_code"]
        stock = check_stock(product_code)
        detail = product_detail(product_code)
        prices = fetch_all(
            """
            SELECT price_type, billing_period, unit_price, unit_label, source_column
            FROM product_price
            WHERE product_code = ? AND status = 'active'
            ORDER BY CASE price_type
              WHEN '1month' THEN 1 WHEN '1year' THEN 2 WHEN '2year' THEN 3 WHEN '3year' THEN 4
              WHEN '4year' THEN 5 WHEN '5year' THEN 6 WHEN '6year' THEN 7 WHEN 'standard' THEN 8 WHEN 'hourly' THEN 9 ELSE 99 END,
              id
            """,
            (product_code,),
        )
        selected_price = None
        if selected_price_type:
            selected_price = next((p for p in prices if p["price_type"] == selected_price_type), None)
        if not selected_price and prices:
            selected_price = next((p for p in prices if p["price_type"] == "1month"), None) or prices[0]
        enriched.append({
            **item,
            "available_quantity": stock.get("available_quantity", 0),
            "specs": detail.get("specs", [])[:3],
            "faqs": detail.get("faqs", [])[:2],
            "prices": prices,
            "selected_price": selected_price,
            "unit_price": float(selected_price["unit_price"]) if selected_price else 0,
            "selected_price_type": selected_price["price_type"] if selected_price else "",
            "selected_billing_period": selected_price["billing_period"] if selected_price else "",
        })
    filters = {
        "product_types": [
            {"value": "", "label": "全部产品类型"},
            {"value": "compute", "label": "计算规格"},
            {"value": "terminal", "label": "终端外设"},
            {"value": "storage", "label": "磁盘/存储"},
            {"value": "bandwidth", "label": "带宽规格"},
            {"value": "addon", "label": "增值组件"},
            {"value": "core_hour_package", "label": "核时包"},
            {"value": "ai_assistant", "label": "AI 助手"},
        ],
        "scenarios": [
            {"value": "", "label": "全部场景"},
            {"value": "domestic", "label": "国内 region"},
            {"value": "international", "label": "国际 region"},
            {"value": "education", "label": "教育办公"},
            {"value": "enterprise", "label": "企业版"},
            {"value": "common", "label": "通用/外设组件"},
        ],
        "price_types": price_type_options,
    }
    return {"products": enriched, "count": len(enriched), "filters": filters, "selected": {"product_type": product_type or "", "scenario": scenario or "", "price_type": selected_price_type}}


@app.get("/api/products/{product_code}")
def api_product_detail(product_code: str) -> dict:
    return product_detail(product_code)


@app.post("/api/products/ask")
def api_product_ask(body: ProductAskRequest) -> dict:
    return product_ask(body.question, body.product_code)


@app.post("/api/products/upsert")
def api_products_upsert(body: ProductUpsertRequest) -> dict:
    """JSON 批量上传/更新产品、报价、库存、规格、FAQ。"""
    return upsert_product_records(body.records, body.source)


@app.post("/api/products/upload-csv")
async def api_products_upload_csv(file: UploadFile = File(...), source: str = Form("csv_upload")) -> dict:
    """CSV 上传/更新产品原始数据。

    CSV header 支持：product_code, product_name, category_code, category_name,
    brand, model, unit, short_description, unit_price, warehouse_code,
    inventory_quantity, reserved_quantity, spec_name, spec_value, spec_unit,
    spec_group, faq_question, faq_answer, tags。
    """
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    records = [dict(row) for row in reader]
    stats = upsert_product_records(records, source)
    return {"filename": file.filename, **stats}


# Order requirement / quotation workflow ------------------------------
@app.post("/api/order-requirements")
def api_create_order_requirement(body: OrderRequirementCreateRequest) -> dict:
    """Create 客户需求表三 before any customer-demand quotation.

    Web 端、Agent 端（含钉钉/企微 MVP）必须共用该入口。
    历史项目字段仅用于后续参考检索，不作为报价规则。
    """
    allowed_channels = {"web", "agent", "dingtalk", "wecom", "wechat", "email", "phone", "import"}
    source_channel = (body.source_channel or "web").strip().lower()
    if source_channel not in allowed_channels:
        return {"error": "invalid_source_channel", "allowed_channels": sorted(allowed_channels)}
    requirement_no = "REQ" + datetime.now().strftime("%Y%m%d%H%M%S")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO order_requirement (
                requirement_no, source_channel, attachment_links, entered_at,
                customer_name, customer_contact_name, raw_requirement,
                customer_expected_time, is_urgent, has_historical_project,
                sales_owner_user_id, output_proposal_required, output_quotation_required,
                human_validated, validation_status, status, created_by, updated_by
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'pending', 'draft', ?, ?)
            """,
            (
                requirement_no,
                source_channel,
                body.attachment_links,
                body.customer_name,
                body.customer_contact_name,
                body.raw_requirement,
                body.customer_expected_time,
                1 if body.is_urgent else 0,
                1 if body.has_historical_project else 0,
                body.sales_owner_user_id,
                1 if body.output_proposal_required else 0,
                1 if body.output_quotation_required else 0,
                body.created_by,
                body.created_by,
            ),
        )
        conn.commit()
    return {
        "requirement_no": requirement_no,
        "source_channel": source_channel,
        "status": "draft",
        "validation_status": "pending",
        "history_usage": "历史项目仅作为报价参考，不作为报价规则。",
        "next_step": "请先由人工确认需求真实有效并指定推进负责人，然后再进入正式客户需求报价单生成。",
    }


# Quotation assistant -------------------------------------------------
@app.get("/api/quotations/stock")
def api_stock(product_code: str = Query(...)) -> dict:
    return check_stock(product_code)


@app.post("/api/quotations/classify")
def api_classify_quotation(body: QuotationClassifyRequest) -> dict:
    """Universal quotation entry classifier shared by all products."""
    payload = body.payload or {}
    decision = classify_quotation_entry(body.message, payload)
    return decision.to_dict()


@app.post("/api/quotations/generate")
def api_generate_quotation(body: QuotationRequest) -> dict:
    payload = body.model_dump()
    decision = classify_quotation_entry(body.message or "", payload)
    if decision.requires_order_requirement:
        return {
            "error": "order_requirement_required",
            "message": "客户/项目/方案/P0/正式报价必须先创建客户需求表三，不能直接调用快速报价接口。",
            "flow_decision": decision.to_dict(),
            "next_api": "POST /api/order-requirements",
        }
    result = generate_quotation(body.customer_code, body.items, body.created_by)
    result["flow_decision"] = decision.to_dict()
    result["quote_scope"] = "single_item_reference"
    return result


# Blog assistant ------------------------------------------------------
@app.get("/api/blogs")
def api_blogs(query: str = Query(""), status: str | None = Query(None)) -> dict:
    return blog_search(query, status)


@app.post("/api/blogs/ask")
def api_blog_ask(body: BlogSearchRequest) -> dict:
    return blog_ask(body.query)


# Knowledge search ----------------------------------------------------
@app.post("/api/knowledge/search")
def api_knowledge_search(body: KnowledgeSearchRequest) -> dict:
    return knowledge_search(body.query, body.filters)


@app.post("/api/knowledge/ask")
def api_knowledge_ask(body: KnowledgeAskRequest) -> dict:
    user = get_user(body.user_id)
    return knowledge_ask(body.question, user)


# DingTalk webhook placeholder ----------------------------------------
@app.post("/dingtalk/webhook")
def dingtalk_webhook(content: str = Form(...), sender_id: str = Form("u_sales_zhang")) -> dict:
    """钉钉事件回调占位接口。
    真实上线时应在这里加入钉钉签名校验、消息解密与异步回复 API。
    """
    user = get_user(sender_id)
    return route_assistant(content, user)


# AI 表格 webhook 回调接口 ------------------------------------------------
@app.post("/api/aitable/callback")
async def aitable_callback(request: Request) -> JSONResponse:
    """
    钉钉 AI 表格 webhook 回调接口
    
    处理以下事件：
    - 记录新增：当销售在 AI 表格中新增需求记录时，自动触发报价流程
    - 记录更新：当状态变更时，同步更新报价状态
    - 记录删除：同步删除关联的报价单（可选）
    
    钉钉事件回调格式：
    {
      "eventType": "record_added|record_updated|record_deleted",
      "baseId": "xxx",
      "tableId": "xxx",
      "recordId": "xxx",
      "data": { "fields": {...} },
      "timestamp": 1234567890
    }
    """
    try:
        body = await request.json()
        event_type = body.get("eventType", "")
        base_id = body.get("baseId", "")
        table_id = body.get("tableId", "")
        record_id = body.get("recordId", "")
        data = body.get("data", {})
        fields = data.get("fields", {})
        
        print(f"[AI 表格回调] 收到事件: {event_type}, baseId={base_id}, recordId={record_id}")
        
        # 验证是否为「客户需求表三」
        if base_id != "1R7q3QmWee72K0KxHNbZQvpaWxkXOEP2":
            return JSONResponse({"success": True, "message": "非目标表格，跳过"}, status_code=200)
        
        # 处理记录新增事件
        if event_type == "record_added":
            # 提取字段
            customer_name = fields.get("客户名称", "")
            customer_company = fields.get("客户公司", "")
            product_list = fields.get("产品清单", "")
            quantity = fields.get("采购数量", 0)
            budget = fields.get("预算范围", "")
            status = fields.get("状态", "草稿")
            
            print(f"  -> 新增需求: 客户={customer_name}, 产品={product_list}, 数量={quantity}")
            
            # 如果状态为「已提交」，自动触发报价生成
            if status == "已提交" and quantity > 0:
                print("  -> 状态为已提交，自动触发报价生成...")
                # TODO: 调用 generate_quotation() 生成报价
                # 1. 查询产品价格
                # 2. 应用折扣策略
                # 3. 生成报价单草稿
                # 4. 更新 AI 表格中的「关联报价单」字段
            
            return JSONResponse({
                "success": True, 
                "message": "记录新增处理完成",
                "recordId": record_id,
                "trigger_quotation": status == "已提交"
            }, status_code=200)
        
        # 处理记录更新事件
        elif event_type == "record_updated":
            old_status = data.get("oldFields", {}).get("状态", "")
            new_status = fields.get("状态", "")
            
            print(f"  -> 状态变更: {old_status} -> {new_status}")
            
            # 状态从「草稿」变为「已提交」，触发报价
            if old_status != "已提交" and new_status == "已提交":
                print("  -> 状态变更为已提交，触发报价生成...")
                # TODO: 触发报价流程
            
            return JSONResponse({
                "success": True, 
                "message": "记录更新处理完成",
                "status_changed": f"{old_status} -> {new_status}"
            }, status_code=200)
        
        # 处理记录删除事件
        elif event_type == "record_deleted":
            print(f"  -> 记录已删除: {record_id}")
            # TODO: 清理关联的报价单草稿
            return JSONResponse({"success": True, "message": "记录删除已处理"}, status_code=200)
        
        # URL 校验（钉钉首次配置 webhook 时的校验请求）
        elif event_type == "check_url":
            return JSONResponse({"success": True, "message": "URL 校验通过"}, status_code=200)
        
        else:
            return JSONResponse({"success": True, "message": f"未知事件类型: {event_type}"}, status_code=200)
    
    except Exception as e:
        print(f"[AI 表格回调] 处理异常: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
