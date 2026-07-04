from fastapi.testclient import TestClient

from app.main import app
from app.quotation_flow import classify_quotation_entry

client = TestClient(app)


def test_quotation_flow_generic_quote_requires_route_confirmation():
    decision = classify_quotation_entry("提供报价")
    assert decision.flow_type == "unclear"
    assert decision.next_action == "ask_quotation_flow"


def test_quotation_flow_single_item_by_product_code():
    decision = classify_quotation_entry("P-AI-GW-001 报价")
    assert decision.flow_type == "single_item"
    assert decision.quotation_type == "单品查询"
    assert decision.requires_order_requirement is False


def test_quotation_flow_requirement_p0_project_quote_wins_over_price_word():
    decision = classify_quotation_entry("客户XX学校需要20台无影云电脑方案报价，预算3万，月底交付")
    assert decision.flow_type == "requirement_p0"
    assert decision.quotation_type == "方案报价"
    assert decision.requires_order_requirement is True


def test_quotation_flow_requirement_p0_by_payload_customer():
    decision = classify_quotation_entry("报价", {"customer_name": "某某公司", "raw_requirement": "需要一套方案"})
    assert decision.flow_type == "requirement_p0"
    assert decision.next_action == "create_order_requirement"


def test_api_chat_generic_quote_requires_route_confirmation():
    resp = client.post("/api/chat", json={"user_id": "u_sales_zhang", "message": "提供报价"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["assistant"] == "quotation"
    assert body["intent"] == "quotation_flow_unclear"
    assert body["data"]["flow_decision"]["flow_type"] == "unclear"


def test_quotation_flow_unclear():
    decision = classify_quotation_entry("你好")
    assert decision.flow_type == "unclear"
