from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.2.0"


def test_finance_metric():
    resp = client.post("/api/finance/chat", json={"user_id": "u_sales_zhang", "message": "查我上个月销售额"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "metric"
    assert "销售额" in body["markdown"]


def test_product_search():
    resp = client.get("/api/products?query=网关")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    assert any("网关" in (item.get("product_name") or "") for item in body["items"])


def test_product_detail():
    resp = client.get("/api/products/P-AI-GW-001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["product"]["product_name"] == "HubAI 智能网关"
    assert len(body["specs"]) >= 1


def test_product_ask():
    resp = client.post("/api/products/ask", json={"question": "支持哪些部署方式？"})
    assert resp.status_code == 200
    body = resp.json()
    assert "部署" in body["answer"]


def test_stock():
    resp = client.get("/api/quotations/stock?product_code=P-AI-GW-001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available_quantity"] >= 0


def test_quotation_generate():
    resp = client.post(
        "/api/quotations/generate",
        json={"customer_code": "C001", "items": [{"product_code": "P-AI-GW-001", "qty": 2}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "quotation_no" in body
    assert body["total_amount"] > 0


def test_blog_search():
    resp = client.get("/api/blogs?query=RAG")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["items"], list)


def test_blog_ask():
    resp = client.post("/api/blogs/ask", json={"query": "悟空系列"})
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body


def test_knowledge_search():
    resp = client.post("/api/knowledge/search", json={"query": "部署", "filters": {"source_type": "faq"}})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["items"], list)


def test_knowledge_ask():
    resp = client.post("/api/knowledge/ask", json={"question": "怎么部署知识库", "user_id": "u_sales_zhang"})
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body


def test_unified_chat_finance():
    resp = client.post("/api/chat", json={"user_id": "u_finance_admin", "message": "Q1 回款多少"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["assistant"] == "finance"


def test_unified_chat_product():
    resp = client.post("/api/chat", json={"user_id": "u_sales_zhang", "message": "HubAI 智能网关有什么参数"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["assistant"] == "product"


def test_unified_chat_quotation():
    resp = client.post("/api/chat", json={"user_id": "u_sales_zhang", "message": "P-AI-GW-001 报价"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["assistant"] == "quotation"


def test_unified_chat_blog():
    resp = client.post("/api/chat", json={"user_id": "u_sales_zhang", "message": "悟空系列讲了什么"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["assistant"] == "blog"
