# 财务悟空 MVP

本项目是“财务部门 AI 助理 / 钉钉悟空”的本地可运行 MVP，用于快速演示：

- 中文自然语言财务查询
- SQLite 本地示例财务数据
- 角色权限过滤
- 聚合报表输出
- 异常预警
- Web 演示页
- 钉钉 Webhook 业务入口占位
- Docker 一键启动

> MVP 原则：先跑通业务闭环，不上传原始明细，不接真实财务数据，不暴露敏感信息。

## 目录结构

```text
finance-wukong-mvp/
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── service.py       # 业务问答逻辑
│   ├── nlp.py           # 简易中文意图识别
│   ├── security.py      # 演示用户与权限范围
│   ├── db.py            # SQLite 连接
│   ├── templates/       # Web 页面
│   └── static/          # 样式
├── scripts/init_db.py   # 初始化示例数据库
├── tests/test_api.py    # API 测试
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 快速启动：Docker

```bash
cd finance-wukong-mvp
docker compose up --build
```

访问：

- Web 演示页：http://localhost:8000/
- 健康检查：http://localhost:8000/health
- API 文档：http://localhost:8000/docs

## 本地 Python 启动

```bash
cd finance-wukong-mvp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 演示身份

| user_id | 姓名 | 角色 | 权限范围 |
|---|---|---|---|
| `u_sales_zhang` | 张三 | sales | 只能看本人聚合数据 |
| `u_sales_li` | 李四 | sales | 只能看本人聚合数据 |
| `u_mgr_east` | 王经理 | manager | 只能看华东销售部聚合数据 |
| `u_finance_admin` | 财务管理员 | finance_admin | 可看全局聚合数据 |

## 示例问题

```text
查我上个月销售额
Q1 回款多少
今年目标完成度
华东销售部预算执行率
各部门销售额对比
看看有没有异常预警
```

## API 示例

```bash
curl -s http://localhost:8000/api/query \
  --get \
  --data-urlencode 'user_id=u_finance_admin' \
  --data-urlencode 'message=各部门销售额对比'
```

```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"u_sales_zhang","message":"查我上个月销售额"}'
```

## 钉钉集成预留

`POST /dingtalk/webhook` 是钉钉事件回调占位接口。真实上线时需要补充：

1. 钉钉签名校验；
2. 消息解密；
3. 用户 ID 与组织身份映射；
4. 异步回复接口调用；
5. 审计日志持久化；
6. 生产级密钥管理。

## 安全边界

当前 MVP 已包含最小权限演示：

- 销售只能查本人汇总；
- 部门经理只能查本部门汇总；
- 财务管理员可查全局汇总；
- 普通销售无法查看部门排行；
- 默认输出聚合结果，不返回原始凭证、薪资、账号等敏感明细。

## 下一步建议

1. 接入真实 Excel 清洗脚本；
2. 加入钉钉 OAuth / 通讯录身份映射；
3. 接入钉钉机器人/企业内部应用回调；
4. 增加 LLM 意图识别，但 SQL 查询仍走白名单模板；
5. 增加操作审计、报表导出和 DING 预警推送。
