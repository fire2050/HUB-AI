# HubAI 过时文档归档说明

> 归档时间：2026-07-03 18:00
> 归档目录：`archive/hubai_deprecated_202607031800/`
> 用途：备份不再作为搜索和调研入口的旧版本文档

## 一、归档原则

- **不删除，只归档**：所有文档原样保留，可查历史
- **不参与调研**：这些文档不再作为方案设计、开发实现、报价规则的依据
- **只做溯源**：仅供追溯项目演进历史时查阅

## 二、归档清单

| 序号 | 文件 | 版本类型 | 归档原因 | 被谁取代 |
|:---:|---|---|---|---|
| 1 | `hubai_knowledge_base_design_scheme.md` | 知识库设计 v1 无版本号原始版 | 后续已按时间戳规范重命名 | `hubai_knowledge_base_design_scheme_v3.1_202606251723.md` |
| 2 | `hubai_knowledge_base_design_scheme_202606231720.md` | 知识库设计 v1.0 | 架构已重构，仅四类助理雏形 | 同上 |
| 3 | `hubai_knowledge_base_design_scheme_v2_202606231819.md` | 知识库设计 v2.0 | RBAC/RAG 加固版，已并入 v3.1 | 同上 |
| 4 | `hubai_knowledge_base_design_scheme_v3_202606251418.md` | 知识库设计 v3.0 | 未含需求表三+钉钉AI表格双入口 | `hubai_knowledge_base_design_scheme_v3.1_202606251723.md` |
| 5 | `hubai_knowledge_base_implementation_plan.md` | 基础版实施计划 | 已并入统一方案 v1.3 | `hubai_unified_solution_v1.3_202606291723.md` |
| 6 | `hubai_unified_solution_v1_202606261030.md` | 统一方案 v1.0 | 未含多产品线架构与 Guardrails | `hubai_unified_solution_v1.3_202606291723.md` |
| 7 | `hubai_quotation_workflow_design_v1_202606241345.md` | 报价工作流 v1 | 10 步流程雏形，无表三约束 | `hubai_quotation_workflow_design_v3_202606250952.md` |
| 8 | `hubai_quotation_workflow_design_v2_202606241449.md` | 报价工作流 v2 | 历史项目参与定价（已废除） | 同上 |
| 9 | `hubai_quotation_dialog_design_v1_202606261200.md` | 报价对话设计 v1.0 | 已升级到 v1.1 | `hubai_quotation_dialog_design_v1.1_202606261220.md` |
| 10 | `order_requirement_table_schema_v2_202606241534.md` | 需求表 Schema v2 | 记录 64 列/178 产品，与实际 90 列/177 产品不符 | 以 `Knowledge-Library-MVP/scripts/migrate_project_requirement_m1.py` 和 `init_hubai_db.py` 为准 |

**共归档 10 份文件。**

## 三、归档后当前有效文档清单

### 3.1 最新主文档（当前唯一真实来源）

| 文件 | 用途 |
|---|---|
| `hubai_knowledge_base_latest_solution_202607031650.md` | 最新完整建设方案 |
| `hubai_knowledge_base_history_and_avoidance_list_202607031615.md` | 历史演进 + 避坑清单 |
| `memory/2026-07-03.md` | 长期记忆（单一真实来源） |

### 3.2 保留的现行方案文档

| 文件 | 用途 |
|---|---|
| `hubai_unified_solution_v1.3_202606291723.md` | 统一方案（已合并至最新方案） |
| `hubai_knowledge_base_design_scheme_v3.1_202606251723.md` | 知识库设计 v3.1（双入口报价体系） |
| `hubai_quotation_workflow_design_v3_202606250952.md` | 报价工作流 v3（客户需求表三必经） |
| `hubai_quotation_execution_plan_v3_202606250952.md` | 报价执行计划 v3 |
| `hubai_openclaw_quotation_system_plan_v4_202606251244.md` | OpenClaw 统一入口 v4.1 |
| `hubai_quotation_guardrails_v1.0_202606291823.md` | 报价 Guardrails v1.0 |
| `hubai_quotation_dialog_design_v1.1_202606261220.md` | 报价对话设计 v1.1 |
| `hubai_multi_product_architecture_design_202606261730.md` | 多产品线架构设计 |
| `hubai_skill_foundation_capability_design_202606261510.md` | Skill 底座能力设计 |
| `hubai_skill_infrastructure_deployment_202606261440.md` | Skill 基础设施部署 |
| `hubai_deployment_roadmap_v1.0_202606291750.md` | 部署路线图 v1.0 |
| `hubai_unified_quotation_entry_rules_scheme_v1.0_202607011745.md` | 统一报价入口规则 v1.0 |
| `hubai_project_requirement_quotation_next_steps_202607011710.md` | 项目需求报价下一步 |

## 四、恢复归档说明

如果需要重新参考归档文档，可以从 `archive/hubai_deprecated_202607031800/` 目录中查阅。

**注意**：查阅时必须以最新主文档为准，归档文档中的规则/字段/流程与当前系统可能存在冲突。