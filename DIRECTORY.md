# HubAI 项目统一目录规范

## 总览

HubAI 项目文件分为 **方案文档**、**代码实现**、**记忆记录**、**归档文件** 四个核心分区，遵循"单一真实来源"和"认知与执行分离"原则。

## 目录结构

```text
/home/xhb-szwl/.openclaw/workspace/
├── hubai_*.md                        # 方案文档（15份最新文档，白名单）
│   ├── hubai_knowledge_base_*.md     # 知识库相关方案
│   ├── hubai_quotation_*.md          # 报价系统相关方案
│   ├── hubai_deployment_*.md         # 部署与架构方案
│   ├── hubai_unified_*.md            # 统一入口与架构方案
│   ├── hubai_project_*.md            # 项目规划方案
│   ├── hubai_multi_product_*.md      # 多产品线方案
│   ├── hubai_weekly_summary_*.md     # 周度变更摘要（保留在根目录）
│   └── hubai_*.md                    # 其他方案
├── Knowledge-Library-MVP/            # 知识库最小可行性产品（代码实现）
│   ├── app/                          # FastAPI 主应用
│   │   ├── db.py                     # 数据库连接
│   │   ├── hubai_service.py          # 统一报价入口服务
│   │   ├── main.py                   # FastAPI 入口
│   │   ├── nlp.py                    # 自然语言处理
│   │   ├── service.py                # 知识检索服务
│   │   ├── security.py               # 安全模块
│   │   ├── static/                   # 静态资源
│   │   ├── templates/                # 页面模板
│   │   └── __pycache__/
│   ├── scripts/                      # 数据库与数据处理脚本
│   │   ├── init_*.py                 # 初始化脚本
│   │   ├── import_*.py               # 数据导入脚本
│   │   ├── audit_*.py                # 数据审计脚本
│   │   ├── migrate_*.py              # 数据库迁移脚本
│   │   └── __pycache__/
│   ├── tests/                        # 单元测试（待补充）
│   ├── .pytest_cache/                # 测试缓存
│   ├── reports/                      # 报告生成
│   ├── .venv/                        # 虚拟环境
│   ├── .trash/                       # 删除的数据备份
│   ├── finance_wukong.db             # 财务/产品数据（主库）
│   └── hubai_quotes.db               # 报价数据（副库）
├── memory/                           # 每日记忆记录
│   ├── YYYY-MM-DD.md                 # 每日详细记录（2026-07-03.md 为长期记忆）
│   └── *.md                          # 其他日期记录
├── archive/                          # 过时文档归档
│   ├── hubai_deprecated_YYYYMMDDHHMM/  # 完整文档备份
│   │   ├── *.md                      # 归档文档（10 份）
│   │   └── README.md                 # 归档说明
│   └── hubai_deprecated_YYYYMMDD/    # 补跑确认（README）
├── dingtalk-openclaw-bridge/         # 钉钉 -> OpenClaw 桥接服务
│   ├── app.py                        # Flask 应用
│   ├── dingtalk_api.py               # 钉钉 API 封装
│   ├── create_table.py               # 需求表创建脚本
│   ├── requirements.txt              # Python 依赖
│   ├── .venv/                        # 虚拟环境
│   └── .env                         # 环境变量（含敏感信息）
├── skills/                           # 本地 Skills（软链接到 /home/xhb-szwl/.openclaw/skills）
│   ├── hubai_base/                  # 底座支持
│   ├── smart_quotation/             # 智能报价核心
│   ├── product-wuying-pc/          # 无影云电脑产品报价
│   └── product-cloud-desktop/       # 云桌面产品报价（待完善）
├── /home/xhb-szwl/hubai/skills/      # HubAI 专用 Skills（硬链接到 workspace）
│   ├── hubai_base/
│   ├── smart_quotation/
│   ├── product-wuying-pc/
│   └── product-cloud-desktop/
├── HUBAI_GLOSSARY.md                 # 关键词与名词表（本文件）
├── HUBAI_DIRECTORY.md                # 统一目录规范（本文件）
├── HUBAI_README.md                   # 系统 README（待生成）
├── HUBAI_CHANGELOG.md                # 版本变更记录（待生成）
└── dingtalk_notify_target.json       # 钉钉通知配置
```

## 规范细则

### 1. 方案文档规范

| 规则 | 说明 |
|---|---|
| **命名规则** | `hubai_<功能>_<子功能>_<版本>_<时间>.md` |
| **白名单** | 根目录下的所有 `hubai_*.md` 均为有效方案 |
| **归档条件** | 主方案文档产生新版本时自动归档旧版本到 `archive/` |
| **保留期限** | 最新方案永久保留，旧版本通过 archive 目录回溯 |
| **引用规则** | 禁止直接引用归档文档，只能引用根目录方案 |
| **统一入口** | `hubai_unified_solution_v1.3_202606291723.md` 为架构统一入口 |

### 2. 代码实现规范

| 规则 | 说明 |
|---|---|
| **技能分层** | `hubai_base` (底座) → `smart_quotation` (核心) → `product-*` (产品线) |
| **确定性要求** | 价格计算、规则验证、文档生成必须为纯 Python 实现（禁止直接调用大模型） |
| **缓存管理** | `__pycache__`、`.venv` 不计入统计 |
| **数据存储** | 本地 SQLite 为主，外部数据通过 API 导入 |
| **备份策略** | 删除前先移到 `.trash/` 目录 |

### 3. 记忆记录规范

| 规则 | 说明 |
|---|---|
| **每日记录** | `memory/YYYY-MM-DD.md`，每日更新，记录关键决策与操作 |
| **长期记忆** | `MEMORY.md`，每周/重要变更后更新 |
| **内容格式** | 时间戳 + 操作 + 结果 + 决策依据 |
| **保留期限** | 永久保留，不清理 |

### 4. 归档规范

| 规则 | 说明 |
|---|---|
| **归档位置** | `/home/xhb-szwl/.openclaw/workspace/archive/` |
| **目录命名** | `hubai_deprecated_YYYYMMDDHHMM/`（精确到分钟）|
| **内容完整性** | 每个归档包必须包含完整文档 + README.md（说明归档原因与版本） |
| **禁止操作** | 禁止修改、删除归档内容 |
| **引用规则** | 禁止在方案文档中引用归档文档 |
| **恢复方法** | 直接复制回根目录，修改文件名版本号 |

### 5. 定时任务规范

| 规则 | 说明 |
|---|---|
| **运行时间** | 主任务：每日 23:00；通知任务：每日 08:40；周度任务：每周一 10:00 |
| **执行逻辑** | 检查变更 → 判断 → 归档/生成文档 → 记忆更新 → 通知 |
| **交付通道** | 钉钉单聊（userId: 013943402538407300） |
| **容错处理** | 失败 2 次后通过 failureAlert 通知 |

## 单一真实来源

当前项目的唯一真实来源为：

| 文件 | 内容 | 定位 |
|---|---|---|
| `memory/2026-07-03.md` | 长期记忆固化文档 | 项目基准架构与避坑清单 |
| `HUBAI_GLOSSARY.md` | 关键词与名词表 | 概念统一入口 |
| `HUBAI_DIRECTORY.md` | 统一目录规范 | 文件结构规范 |
| `hubai_knowledge_base_latest_solution_202607031650.md` | 最新完整知识库建设方案 | 架构统一方案 |
| `hubai_knowledge_base_history_and_avoidance_list_202607031615.md` | 历史演进梳理 + 避坑清单 | 经验总结 |
| 根目录 15 份 hubai_*.md 文档 | 各功能点方案 | 子系统方案 |

## 变更管理

1. 每日 23:00 自动检查变更
2. 有变更 → 生成当日记忆 → 更新归档 → 更新长期记忆 → IMA 上传
3. 无变更 → NO_REPLY，零副作用
4. 周度任务生成周度变更摘要（保留在根目录）