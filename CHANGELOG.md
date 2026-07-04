# HubAI 版本变更记录

## v1.3.0 (2026-07-04)

### 发布说明

HubAI v1.3.0 是**统一架构阶段的最终版本**，完成了从最初原型到企业级集成平台的升级，确立了"认知与执行分离"架构原则和"单一真实来源"记忆体系。

### 主要特性

1. **统一入口分类**：实现 `classify_quotation_entry`，支持 `single_item`/`requirement_p0`/`unclear` 三分类
2. **长期记忆体系**：`memory/2026-07-03.md` + MEMORY.md 固化全项目认知
3. **文档管理**：自动归档机制，建立当前唯一真实来源（根目录 15 份方案 + 长期记忆）
4. **定时任务**：每日归档 + 记忆更新 + 周度摘要（钉钉推送）
5. **产品化**：无影云电脑产品线完整报价流程，通过多个测试场景验证

### 功能模块更新

#### 1. 智能报价系统 (v4.1)

| 变更 | 文件/技能 | 说明 |
|---|---|---|
| **新增统一入口分类器** | `hubai_unified_quotation_entry_rules_scheme_v1.0_202607011745.md` | 3 种需求类型识别策略，通过 5 个测试场景验证 |
| **时长追问去代码列** | `/home/xhb-szwl/hubai/skills/smart_quotation/scripts/quotation_coordinator.py` <br> `/home/xhb-szwl/.openclaw/workspace/dingtalk-openclaw-bridge/app.py` <br> DingTalk Connector | 彻底解决代码列泄露问题，4 处同步修改 |
| **M1 Schema 迁移** | `Knowledge-Library-MVP/scripts/migrate_project_requirement_m1.py` | `order_requirement` 扩展至 90 列，创建 17 个索引 |
| **首条正式需求验证** | `hubai_project_requirement_quotation_next_steps_202607011710.md` | "东方融创公司提供无影云电脑报价" 正确分类为 `requirement_p0` |
| **无影云电脑产品化** | `product-wuying-pc/config/requirement.json` (v1.3.0) | 项目需求字段表更新，统一报价入口支持 |

#### 2. 知识库系统 (v3.1)

| 变更 | 文件 | 说明 |
|---|---|---|
| **架构统一方案** | `hubai_knowledge_base_latest_solution_202607031650.md` | 整合所有历史方案，确定统一架构（四层架构 + 数据底座） |
| **长期记忆固化** | `hubai_knowledge_base_history_and_avoidance_list_202607031615.md` | 历史演进梳理（3个阶段）+ 避坑清单（7项错误修正） |
| **文档管理机制** | `archive/hubai_deprecated_202607031800/README.md` | 自动化归档逻辑，保留所有历史版本以便溯源 |
| **数据库初始化** | `Knowledge-Library-MVP/scripts/init_hubai_db.py` <br> `Knowledge-Library-MVP/finance_wukong.db` | 数据库重建，清除无效记录，保留 177 产品 + 2081 价格 + 499 库存 |

#### 3. 运维与监控

| 变更 | 文件/功能 | 说明 |
|---|---|---|
| **每日定时任务** | OpenClaw Gateway `hubai_daily_archive_memory_update` | 每日 23:00 变更检测，有更新才动作 |
| **钉钉通知配置** | `dingtalk_notify_target.json` <br> `hubai_daily_archive_dingtalk_notification` (cron) | 每日 08:40 推送前一日执行摘要到钉钉 |
| **周度统计** | `hubai_weekly_summary_*.md` (自动生成) | 每周一 10:00 生成上一周周度摘要 |
| **健康检查** | `Knowledge-Library-MVP/app/main.py` | `/health` 端点实现 |
| **服务管理** | `/etc/systemd/user/dingtalk-openclaw-bridge.service` | 系统服务化部署 |

### 架构与设计变更

#### 统一架构原则

| 原则 | 说明 | 文件 |
|---|---|---|
| **认知与执行分离** | 大模型只负责调度，Skill 负责确定性计算（价格/规则/文档） | `HUBAI_GLOSSARY.md` |
| **统一入口** | 所有报价请求必须通过统一分类器，不允许绕过 | `hubai_unified_quotation_entry_rules_scheme_v1.0_202607011745.md` |
| **需求表三必经** | 报价流程必须收集完整的客户需求表三字段 | `hubai_deployment_roadmap_v1.0_202606291750.md` |
| **单一真实来源** | 所有引用必须基于根目录方案或长期记忆 | `HUBAI_DIRECTORY.md` |

#### 四层架构设计

1. **用户接口层**：钉钉对话、网页管理后台（待开发）、飞书/企微集成（待开发）
2. **统一接入层**：OpenClaw Gateway、MCP 协议、多 Agent 协同
3. **核心业务层**：统一入口分类器、智能报价引擎、文档生成模块
4. **数据底座层**：SQLite + FTS5、内部系统集成、外部数据接口

### 代码统计

| 指标 | 数值 |
|---|---|
| **知识库 MVP 代码行数** | 4,258 行（新增 ~3,230 行） |
| **Python 文件数** | 13 个（新增 8 个） |
| **HubAI Skills** | 3 个（hubai_base / smart_quotation / product-wuying-pc） |
| **项目需求字段** | 16 个（7 个必填 + 9 个可选） |
| **产品规格库** | 177 个产品 + 4 个性能等级 + 2,081 个价格点 |

### 测试验证

#### 分类器验证

| 场景 | 分类 | 结果 | 文件 |
|---|---|---|---|
| 单品询价（例如"3台无影云电脑，配置C3"） | `single_item` | ✅ 通过 | `hubai_unified_quotation_entry_rules_scheme_v1.0_202607011745.md` |
| 需求方案（例如"东方融创公司提供无影云电脑报价"） | `requirement_p0` | ✅ 通过 | `hubai_project_requirement_quotation_next_steps_202607011710.md` |
| 模糊查询（例如"电脑报价"） | `unclear` | ✅ 通过 | `hubai_unified_quotation_entry_rules_scheme_v1.0_202607011745.md` |
| 复杂场景（例如"10台图形设计用云电脑，2年租期"） | `requirement_p0` | ✅ 通过 | `hubai_knowledge_base_latest_solution_202607031650.md` |

#### 价格计算验证

| 场景 | 产品 | 配置 | 结果 | 文件 |
|---|---|---|---|---|
| 基础计算 | 无影云电脑 | 算力型 C2（CPU:8/内存:16/存储:50） | ✅ 通过 | `product-wuying-pc/scripts/price_engine.py` |
| 时长追问 | 云桌面 | 通用型 U3（CPU:4/内存:8/存储:20） | ✅ 通过 | `/home/xhb-szwl/hubai/skills/smart_quotation/scripts/quotation_coordinator.py` |
| 库存检查 | 产品不存在 | 不存在的产品型号 | ✅ 正确拒绝 | `product-wuying-pc/scripts/price_engine.py` |
| 无价格 | 无价格产品 | 未配置价格的产品 | ✅ 正确拒绝 | `product-wuying-pc/scripts/price_engine.py` |

### 修复的问题

| 问题 | 影响 | 文件 |
|---|---|---|
| 代码列泄露 | 时长追问表格返回代码内容 | `/home/xhb-szwl/hubai/skills/smart_quotation/scripts/quotation_coordinator.py` |
| 入口绕过 | 部分产品线未使用统一分类器 | `hubai_unified_solution_v1.3_202606291723.md` |
| 文档冗余 | 存在多个版本方案，无统一入口 | `HUBAI_DIRECTORY.md` |
| 测试数据无效 | `test_hubai_api.py` 3 个测试用例失败 | `Memory.md` (待修复) |

### 后续工作

| 任务 | 优先级 | 状态 |
|---|---|---|
| 废弃测试用例重写 | 高 | ⚠️ 待开始 |
| 其他产品线验证（product-cloud-desktop） | 高 | ⚠️ 待开始 |
| Web 管理后台开发（Vue3） | 中 | ⚠️ 待开始 |
| 飞书/企微集成 | 中 | ⚠️ 待开始 |
| 入口限流实现 | 低 | ⚠️ 待开始 |

---

**变更历史**：此版本为 v1.3.0，之前的版本已归档到 `archive/` 目录。
**版本号规则**：`v<大版本>.<中版本>.<小版本>_<时间>`，例如 v1.3.0_202607041630。
**下一版本计划**：v1.4.0，主要内容为 Web 管理后台与其他产品线验证。