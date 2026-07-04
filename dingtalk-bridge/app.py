from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

APP_DIR = Path(__file__).resolve().parent
TOKEN = os.environ.get("DINGTALK_BRIDGE_TOKEN", "")
OPENCLAW_BIN = os.environ.get("OPENCLAW_BIN", "/home/xhb-szwl/.npm-global/bin/openclaw")
OPENCLAW_AGENT = os.environ.get("OPENCLAW_AGENT", "main")
OPENCLAW_TIMEOUT = int(os.environ.get("OPENCLAW_TIMEOUT", "300"))
HOST = os.environ.get("DINGTALK_BRIDGE_HOST", "0.0.0.0")
PORT = int(os.environ.get("DINGTALK_BRIDGE_PORT", "18088"))
MAX_BODY = int(os.environ.get("DINGTALK_BRIDGE_MAX_BODY", str(1024 * 1024)))
HUBAI_MVP_DIR = APP_DIR.parent / "Knowledge-Library-MVP"
if HUBAI_MVP_DIR.exists() and str(HUBAI_MVP_DIR) not in sys.path:
    sys.path.insert(0, str(HUBAI_MVP_DIR))

try:
    from app.quotation_flow import classify_quotation_entry, quotation_flow_prompt
except Exception as exc:  # pragma: no cover - bridge must keep serving even if MVP is unavailable
    print(f"[WARNING] HubAI quotation classifier unavailable: {exc}", file=sys.stderr, flush=True)
    classify_quotation_entry = None
    quotation_flow_prompt = None

WUYING_SKILL_SCRIPTS = Path.home() / "hubai" / "skills" / "product-wuying-pc" / "scripts"
if WUYING_SKILL_SCRIPTS.exists() and str(WUYING_SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WUYING_SKILL_SCRIPTS))
try:
    from price_engine import WuyingPCPriceEngine
except Exception as exc:  # pragma: no cover
    print(f"[WARNING] Wuying price engine unavailable: {exc}", file=sys.stderr, flush=True)
    WuyingPCPriceEngine = None


def dingtalk_quotation_preflight(text: str) -> str | None:
    """Fast path for DingTalk quote entry classification.

    钉钉桥接服务会直接调用 OpenClaw agent。为了避免报价入口判断被大模型自由发挥，
    在通道入口先做一次产品无关的报价入口分流：
    - 泛化“提供报价/报价”直接追问入口类型；
    - 明确客户/项目/方案/P0 信号直接要求客户需求表三；
    - 明确单品信号继续交给 OpenClaw/HubAI 生成参考报价。
    """
    if not classify_quotation_entry:
        return None
    if not any(k in text for k in ["报价", "提供报价", "价格", "查价", "多少钱", "quote", "quotation"]):
        return None
    decision = classify_quotation_entry(text)
    if decision.flow_type == "single_item":
        return None
    if decision.flow_type == "requirement_p0":
        return (
            "已识别为客户/项目/方案类报价。\n\n"
            "请先创建【客户需求表三】，再进入需求卡、分流、规则校验、审批和正式客户报价。\n"
            "当前不会绕过需求表三直接生成正式客户报价。"
        )
    prompt = quotation_flow_prompt() if quotation_flow_prompt else "请先确认本次是单品价格查询，还是客户需求表三/项目报价。"
    return f"{prompt}\n\n请直接回复：单品价格查询，或 客户需求表三。"


def dingtalk_single_item_quote(text: str) -> str | None:
    """Directly render single-item Wuying price query as a compact table.

    返回 None 表示放行给 OpenClaw；返回字符串表示桥接层已完成确定性回复。
    对无影单品查价，桥接层必须优先处理“时长类型必选”，避免进入大模型后绕过规则。
    """
    if not (classify_quotation_entry and WuyingPCPriceEngine):
        return None
    if not any(k in text for k in ["报价", "价格", "查价", "多少钱", "单品", "查询"]):
        return None
    decision = classify_quotation_entry(text)
    if decision.flow_type != "single_item":
        if decision.flow_type == "unclear" and any(k in text for k in ["无影", "云电脑"]) and any(k in text for k in ["报价", "价格", "查价", "多少钱", "查询"]):
            return "无法精准匹配到唯一价格配置，暂不输出报价，避免价格不准确。\n\n请先确认这是【单品查价】还是【项目/客户需求报价】；如果是单品查价，请补充：产品/配置、时长类型、数量、是否需要无影终端型号（如无影魔方AS05）。"
        return None

    def render_duration_prompt(result: dict) -> str | None:
        if result.get("error_code") != "DURATION_TYPE_REQUIRED":
            return None
        details = result.get("details") if isinstance(result.get("details"), dict) else {}
        options = details.get("duration_options") or []
        if not options:
            return result.get("error_message") or "该产品存在多个时长类型，请先选择时长类型。"
        lines = [
            "该产品/配置存在多个时长类型，请先选择一个时长类型后再查询报价：",
            "",
            "| 序号 | 时长类型 |",
            "|---:|---|",
        ]
        for idx, option in enumerate(options, start=1):
            lines.append(f"| {idx} | {option.get('label')} |")
        lines.extend([
            "",
            "请直接回复其中一个时长类型，例如：`120小时`、`200小时`、`不限时长1小时休眠`。",
        ])
        return "\n".join(lines)

    def render_precision_prompt(result: dict) -> str | None:
        if result.get("error_code") != "PRICE_MATCH_NOT_PRECISE":
            return None
        details = result.get("details") if isinstance(result.get("details"), dict) else {}
        lines = [
            "无法精准匹配到唯一价格配置，暂不输出报价，避免价格不准确。",
            "",
        ]
        missing = details.get("missing_fields") or []
        if missing:
            lines.append("需要补充：" + "、".join(missing))
        candidates = details.get("candidate_products") or []
        if candidates:
            lines.extend(["", "可能匹配的配置："])
            for idx, name in enumerate(candidates, start=1):
                lines.append(f"{idx}. {name}")
        options = details.get("duration_options") or []
        if options:
            lines.extend(["", "可选时长类型："])
            for idx, option in enumerate(options, start=1):
                lines.append(f"{idx}. {option.get('label')}")
        action = details.get("action") or "请补充准确的产品/配置/时长/数量后重新报价。"
        lines.extend(["", action])
        return "\n".join(lines)

    result = WuyingPCPriceEngine.query_single_item(query=text)
    if result.get("success"):
        return result.get("message") or None
    precision_prompt = render_precision_prompt(result)
    if precision_prompt:
        return precision_prompt
    duration_prompt = render_duration_prompt(result)
    if duration_prompt:
        return duration_prompt

    # 如果整句含“报价”等噪声导致匹配失败，去掉意图词再试一次。
    cleaned = re.sub(r"(单品|报价|价格|查价|多少钱|请|帮我|查询|提供|此产品|这个产品)", "", text).strip(" ，,。")
    if cleaned and cleaned != text:
        result = WuyingPCPriceEngine.query_single_item(query=cleaned)
        if result.get("success"):
            return result.get("message") or None
        precision_prompt = render_precision_prompt(result)
        if precision_prompt:
            return precision_prompt
        duration_prompt = render_duration_prompt(result)
        if duration_prompt:
            return duration_prompt
    return None


def stable_session_key(sender: str, conversation: str | None = None) -> str:
    raw = f"{conversation or 'direct'}:{sender or 'unknown'}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"dingtalk_{digest}"


def extract_text(payload: dict) -> str:
    text = payload.get("text")
    if isinstance(text, dict) and isinstance(text.get("content"), str):
        return text["content"].strip()
    if isinstance(text, str):
        return text.strip()
    for key in ("content", "message", "msg", "prompt", "query"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def clean_bot_mention(text: str) -> str:
    return re.sub(r"^@\S+\s+", "", text.strip()).strip()


def sender_id(payload: dict) -> str:
    for key in ("senderStaffId", "senderId", "senderNick", "userId", "userid"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    sender = payload.get("sender")
    if isinstance(sender, dict):
        for key in ("staffId", "id", "nick"):
            val = sender.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return "unknown"


def conversation_id(payload: dict) -> str | None:
    for key in ("conversationId", "conversationTitle", "chatbotUserId"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def find_json_object(text: str) -> dict | None:
    for idx, ch in enumerate(text):
        if ch == "{":
            try:
                data = json.loads(text[idx:])
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                continue
    return None


def run_openclaw(prompt: str, session_key: str) -> str:
    cmd = [
        OPENCLAW_BIN,
        "agent",
        "--agent", OPENCLAW_AGENT,
        "--session-key", session_key,
        "--message", prompt,
        "--json",
        "--timeout", str(OPENCLAW_TIMEOUT),
    ]
    proc = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=OPENCLAW_TIMEOUT + 30,
        cwd=str(APP_DIR.parent),
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout)[-1500:])

    data = find_json_object(proc.stdout.strip())
    if not data:
        return (proc.stdout.strip() or "OpenClaw 已处理，但没有返回可见文本。")[-3800:]

    payloads = data.get("payloads")
    if isinstance(payloads, list):
        texts = [p.get("text") for p in payloads if isinstance(p, dict) and isinstance(p.get("text"), str)]
        if texts:
            return "\n".join(texts).strip()

    for key in ("finalAssistantVisibleText", "finalAssistantRawText", "text"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return "OpenClaw 已处理，但没有返回可见文本。"


def json_bytes(obj: dict) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "DingTalkOpenClawBridge/0.1"

    def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            return self._send(200, json_bytes({"status": "ok", "service": "dingtalk-openclaw-bridge"}))
        return self._send(404, json_bytes({"error": "not found"}))

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        parts = [p for p in path.split("/") if p]
        if len(parts) != 2 or parts[0] not in {"dingtalk", "test"}:
            return self._send(404, json_bytes({"error": "not found"}))
        if not TOKEN or not hmac.compare_digest(parts[1], TOKEN):
            return self._send(404, json_bytes({"error": "not found"}))

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            return self._send(400, json_bytes({"error": "invalid body length"}))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception as exc:
            return self._send(400, json_bytes({"error": f"invalid json: {exc}"}))
        if not isinstance(payload, dict):
            return self._send(400, json_bytes({"error": "json object required"}))

        text = clean_bot_mention(extract_text(payload))
        if not text:
            reply = "请发送文本消息。"
        else:
            preflight_reply = dingtalk_quotation_preflight(text)
            if preflight_reply:
                reply = preflight_reply
            else:
                direct_quote_reply = dingtalk_single_item_quote(text)
                if direct_quote_reply:
                    reply = direct_quote_reply
                else:
                    try:
                        reply = run_openclaw(text, stable_session_key(sender_id(payload), conversation_id(payload)))
                    except subprocess.TimeoutExpired:
                        reply = "OpenClaw 处理超时，请稍后重试或缩短问题。"
                    except Exception as exc:
                        reply = f"OpenClaw 调用失败：{str(exc)[-1500:]}"

        if parts[0] == "test":
            return self._send(200, reply.encode("utf-8"), "text/plain; charset=utf-8")
        # DingTalk robot sync response format.
        return self._send(200, json_bytes({"msgtype": "text", "text": {"content": reply[:3800]}}))

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DINGTALK_BRIDGE_TOKEN is required")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"DingTalk → OpenClaw bridge listening on {HOST}:{PORT}", flush=True)
    httpd.serve_forever()
