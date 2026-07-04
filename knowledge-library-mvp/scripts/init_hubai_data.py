from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.db import get_conn  # noqa: E402


def init_products(conn) -> None:
    categories = [
        ("CAT_AI_HARDWARE", "AI 硬件", None),
        ("CAT_AI_SOFTWARE", "AI 软件", None),
        ("CAT_SERVICE", "专业服务", None),
    ]
    for row in categories:
        conn.execute("INSERT OR IGNORE INTO product_category (category_code, category_name, parent_category_code) VALUES (?,?,?)", row)

    products = [
        ("P-AI-GW-001", "HubAI 智能网关", "CAT_AI_HARDWARE", "HubAI", "GW-Pro-2026", "套",
         "企业级 AI 网关，支持本地化/私有云/混合云部署，提供统一 API 入口、负载均衡、日志审计。"),
        ("P-AI-KB-002", "HubAI 知识库底座", "CAT_AI_SOFTWARE", "HubAI", "KB-2026", "套",
         "企业级一体化知识库底座，支持 RAG 检索、向量搜索、权限隔离与知识图谱扩展。"),
        ("P-AI-BOT-003", "数字员工编排平台", "CAT_AI_SOFTWARE", "HubAI", "BOT-2026", "套",
         "多部门数字员工统一编排平台，支持财务、商务、销售、技术四类助理。"),
        ("P-SV-IMPL-004", "实施与交付服务", "CAT_SERVICE", "HubAI", "SV-IMPL", "次",
         "现场部署、数据迁移、用户培训、持续运维支持。"),
    ]
    for row in products:
        conn.execute(
            "INSERT OR IGNORE INTO product (product_code, product_name, category_code, brand, model, unit, short_description) VALUES (?,?,?,?,?,?,?)",
            row,
        )

    specs = [
        ("P-AI-GW-001", "并发会话数", "500", "路", "性能", 1),
        ("P-AI-GW-001", "支持协议", "HTTP/HTTPS/MQTT", "", "接口", 2),
        ("P-AI-GW-001", "部署方式", "本地化/私有云/混合云", "", "部署", 3),
        ("P-AI-GW-001", "接口规格", "RESTful + gRPC", "", "接口", 4),
        ("P-AI-KB-002", "存储引擎", "SQLite + FTS5（可扩展 PostgreSQL）", "", "架构", 1),
        ("P-AI-KB-002", "检索能力", "关键词 + 向量检索（预留）", "", "能力", 2),
        ("P-AI-KB-002", "权限模型", "RBAC + 部门隔离", "", "安全", 3),
        ("P-AI-BOT-003", "数字员工类型", "财务/商务/销售/技术", "", "功能", 1),
        ("P-AI-BOT-003", "对接渠道", "Web / 钉钉 / API", "", "集成", 2),
        ("P-SV-IMPL-004", "交付周期", "2-4 周", "", "服务", 1),
        ("P-SV-IMPL-004", "服务内容", "部署+迁移+培训+运维", "", "服务", 2),
    ]
    for row in specs:
        conn.execute(
            "INSERT OR IGNORE INTO product_spec (product_code, spec_name, spec_value, spec_unit, spec_group, sort_order) VALUES (?,?,?,?,?,?)",
            row,
        )

    faqs = [
        ("P-AI-GW-001", "支持哪些部署方式？", "支持本地化部署、私有云部署和混合云部署三种模式。", "部署"),
        ("P-AI-GW-001", "最大并发会话数是多少？", "官方标称 500 路并发，实际视服务器配置而定。", "性能"),
        ("P-AI-KB-002", "支持哪些数据库？", "基础版使用 SQLite + FTS5；企业版可平滑迁移到 PostgreSQL + Qdrant/Chroma。", "架构"),
        ("P-AI-KB-002", "知识检索支持向量搜索吗？", "基础版支持 FTS5 关键词检索；增强版预留向量库接口，后续可接入 Qdrant/Chroma。", "能力"),
        ("P-AI-BOT-003", "可以对接钉钉吗？", "可以，预留了钉钉 Webhook 入口和 OAuth 身份映射接口。", "集成"),
        ("P-SV-IMPL-004", "实施周期多长？", "标准场景 2-4 周，含部署、数据迁移、培训和首月运维。", "服务"),
    ]
    for row in faqs:
        conn.execute(
            "INSERT OR IGNORE INTO product_faq (product_code, question, answer, tags) VALUES (?,?,?,?)",
            row,
        )

    docs = [
        ("P-AI-GW-001", "HubAI 智能网关部署手册", "manual", "1.0", "internal",
         "## 部署手册\n\n1. 准备 Linux 服务器（推荐 Ubuntu 22.04）。\n2. 安装 Docker 与 Docker Compose。\n3. 执行 `docker compose up --build`。\n4. 访问 http://localhost:8000 验证。\n"),
        ("P-AI-KB-002", "HubAI 知识库使用指南", "guide", "1.0", "internal",
         "## 使用指南\n\n- 产品助理：查询产品参数、FAQ。\n- 报价助理：生成报价单、查看库存。\n- 博文助理：检索悟空系列文章。\n- 财务助理：查询销售、回款、预算。\n"),
    ]
    for row in docs:
        conn.execute(
            "INSERT OR IGNORE INTO product_document (product_code, title, doc_type, version, permission_level, markdown_content) VALUES (?,?,?,?,?,?)",
            row,
        )


def init_prices_and_policies(conn) -> None:
    prices = [
        ("P-AI-GW-001", 128000.0),
        ("P-AI-KB-002", 86000.0),
        ("P-AI-BOT-003", 56000.0),
        ("P-SV-IMPL-004", 32000.0),
    ]
    for row in prices:
        conn.execute(
            "INSERT OR IGNORE INTO product_price (product_code, unit_price, currency, price_type, status) VALUES (?,?,'CNY','standard','active')",
            row,
        )

    policies = [
        ("POL-STD", "标准折扣", None, None, 1.0, 1, 0),
        ("POL-CAT-HW", "AI 硬件批量折扣", None, "CAT_AI_HARDWARE", 0.95, 2, 0),
        ("POL-CAT-SW", "AI 软件批量折扣", None, "CAT_AI_SOFTWARE", 0.92, 3, 0),
        ("POL-AMT", "大额折扣", None, None, 0.90, 1, 300000),
    ]
    for row in policies:
        conn.execute(
            "INSERT OR IGNORE INTO quotation_policy (policy_code, policy_name, customer_level, product_category_code, discount_rate, min_quantity, min_amount) VALUES (?,?,?,?,?,?,?)",
            row,
        )


def init_inventory(conn) -> None:
    rows = [
        ("P-AI-GW-001", "WH-BJ", 120, 20),
        ("P-AI-GW-001", "WH-SH", 85, 10),
        ("P-AI-KB-002", "WH-BJ", 200, 30),
        ("P-AI-BOT-003", "WH-BJ", 150, 15),
        ("P-SV-IMPL-004", "WH-BJ", 9999, 0),
    ]
    for row in rows:
        conn.execute(
            "INSERT OR IGNORE INTO inventory (product_code, warehouse_code, quantity, reserved_quantity) VALUES (?,?,?,?)",
            row,
        )


def import_blog_archive(conn) -> None:
    base = Path(ROOT, "..", "wukong_series_archive")
    if not base.exists():
        base = Path("/home/xhb-szwl/.openclaw/workspace/wukong_series_archive")
    if not base.exists():
        base = Path("/app/wukong_series_archive")
    if not base.exists():
        print("Warning: wukong_series_archive not found, skipping blog import.")
        return
    count = 0
    for md_file in base.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        parts = md_file.relative_to(base).parts
        series_no = parts[0] if parts else "未分类"
        title = content.splitlines()[0].lstrip("# ").strip() or md_file.stem
        summary = content[:300] + "…" if len(content) > 300 else content
        status = "published" if "01-已发布" in str(md_file) or "01" in str(md_file) else "draft"
        article_code = f"BLOG-{md_file.stem[:40].upper()}"
        conn.execute(
            """
            INSERT OR IGNORE INTO blog_article
            (article_code, title, series_no, source_file, content_markdown, content_summary, status, keywords, tags)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (article_code, title, series_no, str(md_file), content, summary, status, "悟空系列", "AI,钉钉,知识库"),
        )
        count += conn.total_changes
    print(f"Blog articles imported from {base}: {count}")


def chunk_and_index(conn) -> None:
    # FAQ chunks
    faqs = conn.execute("SELECT id, product_code, question, answer FROM product_faq").fetchall()
    for row in faqs:
        conn.execute(
            """
            INSERT INTO knowledge_chunk (source_type, source_id, title, chunk_text, chunk_index, tags)
            VALUES ('faq', ?, ?, ?, 0, ?)
            """,
            (row["product_code"], row["question"], row["answer"], "FAQ," + row["product_code"]),
        )

    # Product doc chunks (simple chunking)
    docs = conn.execute("SELECT product_code, title, markdown_content FROM product_document").fetchall()
    for doc in docs:
        lines = doc["markdown_content"].splitlines()
        chunk = "\n".join(lines[:20])
        conn.execute(
            "INSERT INTO knowledge_chunk (source_type, source_id, title, chunk_text, chunk_index, tags) VALUES ('product_doc', ?, ?, ?, 0, ?)",
            (doc["product_code"], doc["title"], chunk, "产品文档"),
        )

    # Blog chunks (simple chunking by sections)
    articles = conn.execute("SELECT article_code, title, content_markdown FROM blog_article").fetchall()
    for art in articles:
        lines = art["content_markdown"].splitlines()
        chunk_size = 25
        idx = 0
        for i in range(0, len(lines), chunk_size):
            chunk = "\n".join(lines[i:i + chunk_size])
            conn.execute(
                "INSERT INTO knowledge_chunk (source_type, source_id, title, chunk_text, chunk_index, tags) VALUES ('blog_article', ?, ?, ?, ?, ?)",
                (art["article_code"], art["title"], chunk, idx, "博文," + art["article_code"]),
            )
            idx += 1


def main() -> None:
    with get_conn() as conn:
        init_products(conn)
        init_prices_and_policies(conn)
        init_inventory(conn)
        import_blog_archive(conn)
        chunk_and_index(conn)
        conn.commit()
    print("HubAI base data initialized successfully.")


if __name__ == "__main__":
    main()
