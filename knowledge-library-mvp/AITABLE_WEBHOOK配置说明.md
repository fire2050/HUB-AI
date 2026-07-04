# 【HubAI】钉钉 AI 表格 Webhook 配置说明

> 版本：v1.0  
> 更新时间：2026-06-25  
> 功能：AI 表格数据变更自动触发 HubAI 报价流程

---

## 📋 概述

当销售在钉钉 AI 表格「【HubAI】客户需求表三」中：
1. ✅ **新增记录** → 自动进入报价预处理流程
2. ✅ **状态变更为「已提交」** → 自动触发报价生成
3. ✅ **记录更新** → 同步更新报价状态

---

## 🔗 回调接口信息

| 项目 | 值 |
|------|-----|
| **接口地址** | `https://你的域名/api/aitable/callback` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **目标表格** | 【HubAI】客户需求表三 |
| **Base ID** | `1R7q3QmWee72K0KxHNbZQvpaWxkXOEP2` |

---

## 📝 钉钉开放平台配置步骤

### 步骤 1：进入事件订阅配置
1. 打开 [钉钉开放平台](https://open-dev.dingtalk.com/)
2. 进入 **应用开发** → **企业内部开发** → 选择你的应用
3. 左侧菜单 → **事件与回调** → **订阅事件**

### 步骤 2：配置回调 URL
- **请求网址（回调 URL）**：`https://你的域名/api/aitable/callback`
- **加密 aes_key**：自动生成或自定义（32 位字符）
- **签名 token**：自定义（用于签名验证）

### 步骤 3：订阅 AI 表格事件
在事件列表中搜索并订阅以下事件：

| 事件名称 | 事件代码 | 触发时机 |
|----------|----------|----------|
| AI表格记录新增 | `ai_table_record_added` | 新增一行记录时 |
| AI表格记录更新 | `ai_table_record_updated` | 修改记录内容时 |
| AI表格记录删除 | `ai_table_record_deleted` | 删除记录时 |

### 步骤 4：保存并验证
1. 点击「保存」
2. 钉钉会发送 `check_url` 事件到回调地址进行验证
3. 验证通过后，配置生效

---

## 📊 事件数据格式

### 记录新增事件
```json
{
  "eventType": "record_added",
  "eventId": "event_xxx",
  "baseId": "1R7q3QmWee72K0KxHNbZQvpaWxkXOEP2",
  "tableId": "hERWDMS",
  "recordId": "rec_xxx",
  "data": {
    "fields": {
      "需求编号": "REQ20260625001",
      "客户名称": "张三",
      "客户公司": "XX科技有限公司",
      "产品清单": ["无影云电脑-企业版"],
      "采购数量": 50,
      "预算范围": "5-10万",
      "状态": "草稿"
    }
  },
  "timestamp": 1750908000,
  "operator": "员工姓名"
}
```

### 记录更新事件
```json
{
  "eventType": "record_updated",
  "baseId": "1R7q3QmWee72K0KxHNbZQvpaWxkXOEP2",
  "tableId": "hERWDMS",
  "recordId": "rec_xxx",
  "data": {
    "fields": {
      "状态": "已提交"
    },
    "oldFields": {
      "状态": "草稿"
    }
  },
  "changedFields": ["状态"],
  "timestamp": 1750908000,
  "operator": "员工姓名"
}
```

---

## 🎯 自动触发规则

### 报价触发条件
当满足以下 **任一条件** 时，自动触发报价生成：

| 条件 | 说明 |
|------|------|
| ✅ 新增记录时 **状态 = "已提交"** | 销售直接录入完整数据并提交 |
| ✅ 状态从 **"草稿" → "已提交"** | 销售先存草稿，确认后提交 |
| ✅ 状态从 **"处理中" → "已提交"** | 销售补充信息后重新提交 |

### 不触发条件
- ❌ 状态 = "草稿" 或 "处理中"
- ❌ 采购数量 = 0 或空
- ❌ 产品清单为空

---

## 🔒 安全验证

### 签名验证（可选增强）
```python
# 钉钉签名验证逻辑（已在代码中预留位置）
def verify_dingtalk_signature(signature: str, timestamp: str, nonce: str, body: str) -> bool:
    """
    验证钉钉回调请求签名
    signature = sha1(token + timestamp + nonce + body)
    """
    import hashlib
    token = "你的签名token"
    sign_str = token + timestamp + nonce + body
    calc_sign = hashlib.sha1(sign_str.encode()).hexdigest()
    return calc_sign == signature
```

### IP 白名单
钉钉回调服务器 IP 段：
- `140.205.0.0/16`
- `106.11.0.0/16`
- `40.205.0.0/16`

建议在服务器防火墙或 WAF 中配置 IP 白名单。

---

## 📍 本地开发调试

### 使用内网穿透工具（如 ngrok）
```bash
# 启动 HubAI 服务（默认端口 8000）
cd Knowledge-Library-MVP
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 另开终端：启动内网穿透
ngrok http 8000

# 得到公网地址，如：https://abc123.ngrok.io
# 钉钉回调 URL 配置为：https://abc123.ngrok.io/api/aitable/callback
```

### 本地测试命令
```bash
# 测试 URL 校验
curl -X POST http://localhost:8000/api/aitable/callback \
  -H "Content-Type: application/json" \
  -d '{"eventType":"check_url"}'

# 测试记录新增
curl -X POST http://localhost:8000/api/aitable/callback \
  -H "Content-Type: application/json" \
  -d '{
    "eventType": "record_added",
    "baseId": "1R7q3QmWee72K0KxHNbZQvpaWxkXOEP2",
    "tableId": "hERWDMS",
    "recordId": "test_001",
    "data": {
      "fields": {
        "客户名称": "测试客户",
        "采购数量": 10,
        "状态": "已提交"
      }
    }
  }'
```

---

## 📈 日志监控

### 正常日志输出
```
[AI 表格回调] 收到事件: record_added, baseId=1R7q3QmWee72K0KxHNbZQvpaWxkXOEP2, recordId=rec_xxx
  -> 新增需求: 客户=测试客户, 产品=无影云电脑, 数量=50
  -> 状态为已提交，自动触发报价生成...
```

### 异常告警
建议配置以下告警规则：
- 🚨 回调接口 5xx 错误率 > 5%
- 🚨 回调超时 > 3 秒
- 🚨 签名验证失败 > 3 次/小时

---

## 🔄 后续功能规划

- [ ] **v1.1**：签名验证完整实现
- [ ] **v1.2**：报价生成后自动回写 AI 表格「关联报价单」字段
- [ ] **v1.3**：报价审批通过后自动更新 AI 表格状态
- [ ] **v1.4**：支持钉钉群消息通知（报价完成@销售）
- [ ] **v1.5**：重复需求检测与告警

---

## 📞 技术支持

如有问题，请检查：
1. HubAI 服务是否正常运行
2. 回调 URL 是否可公网访问
3. 钉钉事件订阅配置是否正确
4. 服务器防火墙/安全组是否放行钉钉 IP 段

---

**配置完成后，AI 表格数据将与 HubAI 报价系统实现无缝联动！ 🚀**
