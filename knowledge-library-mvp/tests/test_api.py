from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_sales_can_query_own_metric():
    resp = client.post("/api/chat", json={"user_id": "u_sales_zhang", "message": "查我上个月销售额"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "metric"
    assert "销售额" in body["markdown"]
    assert body["data"]["value"] > 0


def test_sales_cannot_compare_departments():
    resp = client.post("/api/chat", json={"user_id": "u_sales_zhang", "message": "各部门销售额对比"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "permission_denied"


def test_admin_can_compare_departments():
    resp = client.post("/api/chat", json={"user_id": "u_finance_admin", "message": "各部门销售额对比"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "compare"
    assert "部门经营对比" in body["markdown"]


def test_alerts():
    resp = client.post("/api/chat", json={"user_id": "u_finance_admin", "message": "看看有没有异常预警"})
    assert resp.status_code == 200
    assert "预警" in resp.json()["markdown"]
