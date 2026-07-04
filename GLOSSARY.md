# HubAI 关键词与名词表

## 核心概念

| 关键词 | 全称/解释 | 适用场景 | 来源 |
|---|---|---|---|
| **HubAI** | Enterprise AI Integration Platform for DingTalk | 企业级 AI 集成平台 | 项目名 |
| **统一入口分类器** | `classify_quotation_entry` | 报价需求接入分类（单品 / 需求 P0 / 不明确） | 报价系统 v4.1 |
| **客户需求表三** | Requirement Form III | 报价流程必需前置字段表（16个字段） | 统一报价入口规则 v1.0 |
| **单品/requirement_p0/unclear** | 报价入口三分类 | 需求识别策略（通过规则引擎自动分类） | hubai_service.py |
| **时长追问表格** | Duration Clarification Table | 针对不同场景追问有效期的配置表（4种时长：天/周/月/年） | DingTalk AI 表格 |
| **无影云电脑** | Wuying PC | 阿里云公有云电脑产品（算力型/通用型/图形型） | product-wuying-pc |
| **认知与执行分离** | Cognitive-Execution Separation | 大模型只负责调度/理解，Skill 负责确定性计算 | 架构原则 |

## 技术架构

| 关键词 | 全称/解释 | 技术实现 | 备注 |
|---|---|---|---|
| **Knowledge-Library-MVP** | 知识库最小可行性产品 | FastAPI + SQLite + FTS5 + Jina Reader | 离线知识库系统 |
| **FastAPI** | Python Web 框架 | main.py / hubai_service.py | 内部 API 网关 |
| **SQLite + FTS5** | 轻量级数据库 + 全文搜索 | finance_wukong.db / hubai_quotes.db | 本地存储 + 搜索 |
| **Jina Reader** | Web 内容解析库 | 知识库插件 | 网页内容自动解析 |
| **MCP (Model Context Protocol)** | 模型上下文协议 | OpenClaw Skills + MCP | 技能调用标准 |
| **OpenClaw Gateway** | 统一入口网关 | Gateway + Connectors | 多渠道接入（Web / DingTalk） |

## 文件结构

| 关键词 | 路径 | 功能 |
|---|---|---|
| **workspace/hubai_*.md** | `/home/xhb-szwl/.openclaw/workspace/hubai_*.md` | HubAI 项目主方案文档（保留最新15份） |
| **archive/hubai_deprecated_YYYYMMDDHHMM/** | `/home/xhb-szwl/.openclaw/workspace/archive/` | 过时文档归档（只移不删） |
| **memory/YYYY-MM-DD.md** | `/home/xhb-szwl/.openclaw/workspace/memory/` | 每日记忆记录（长期记忆基础） |
| **Knowledge-Library-MVP/** | `/home/xhb-szwl/.openclaw/workspace/Knowledge-Library-MVP/` | 知识库 MVP 代码 |
| **/home/xhb-szwl/hubai/skills/** | `/home/xhb-szwl/hubai/skills/` | HubAI 专用 Skills |
| **dingtalk-openclaw-bridge/** | `/home/xhb-szwl/.openclaw/workspace/dingtalk-openclaw-bridge/` | 钉钉 → OpenClaw 桥接服务 |

## Skills 体系

| 关键词 | 功能 | 包含模块 |
|---|---|---|
| **hubai_base** | 底座支持 | db.py / logger.py / auth.py / errors.py / config.py / mcp_client.py / product_router.py / requirement_base.py / dialogue_base.py |
| **smart_quotation** | 智能报价核心 | price_engine.py / rule_validator.py / route_engine.py / doc_generator.py / approval_engine.py / requirement_card.py / quotation_coordinator.py / session_manager.py / cross_product.py |
| **product-wuying-pc** | 无影云电脑产品报价 | 需求表定义 + 价格引擎 + SKILL.md |
| **product-cloud-desktop** | 云桌面产品报价 | 需求表定义 + 价格引擎 + SKILL.md |

## 流程与状态

| 关键词 | 流程/状态 | 适用阶段 |
|---|---|---|
| **认知阶段** | 大模型调度/分类/决策 | 输入解析 → 分类 → 路由 |
| **执行阶段** | Skill 确定性计算 | 规则验证 → 价格计算 → 文档生成 |
| **M1 Schema 迁移** | `order_requirement` 扩展至 90 列 | 数据库升级 |
| **单一真实来源** | `memory/2026-07-03.md` + 当前最新方案 | 长期记忆固化 |
| **当前唯一真实来源** | 最新 3 份方案 + 1 份长期记忆 + 1 份避坑清单 | 项目基准 |

## 业务规则

| 关键词 | 规则内容 | 约束性 | 备注 |
|---|---|---|---|
| **无价格不报价** | 无产品价格时直接拒绝报价 | 硬性 | `price_engine` 检查 |
| **无库存不承诺** | 库存为 0 时不承诺交付时间 | 硬性 | `inventory` 检查 |
| **无策略不折扣** | 无 discount policy 时不计算折扣价 | 硬性 | `quotation_policy` 表 |
| **历史项目仅参考** | 历史项目数据不参与当前报价规则 | 硬性 | 统一报价入口规则 v1.0 |
| **入口分类前置** | 先分类，再进入对应报价流程 | 硬性 | `classify_quotation_entry` 优先调用 |

## 运维监控

| 关键词 | 内容 | 位置 |
|---|---|---|
| **systemd units** | `dingtalk-openclaw-bridge.service` / `hubai.service` | `/etc/systemd/user/` |
| **cron jobs** | 每日/周度定时任务 | OpenClaw Gateway |
| **audit logs** | 操作审计日志 | `__pycache__` 之外的脚本输出 |
| **health check** | `/health` 端点 | Knowledge-Library-MVP (FastAPI) |
| **delivery queue** | 消息投递队列 | OpenClaw SQLite (`delivery_queue_entries`) |

## 外部系统

| 关键词 | 系统 | 用途 |
|---|---|---|
| **IMA 知识库** | 内部知识管理系统 | 方案文档存储与共享 |
| **DingTalk AI 表格** | 钉钉多维表格 | 客户需求表三收集 |
| **GitHub** | 代码托管平台 | 版本管理（待对接） |