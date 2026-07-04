# DingTalk → OpenClaw Bridge

本服务提供钉钉机器人/HTTP 回调入口，将钉钉文本消息转发到本机 OpenClaw：

- 健康检查：`GET /health`
- 钉钉入口：`POST /dingtalk/<DINGTALK_BRIDGE_TOKEN>`
- 本地测试：`POST /test/<DINGTALK_BRIDGE_TOKEN>`

钉钉机器人回调地址应填写：

```text
http(s)://<你的公网域名或内网穿透域名>/dingtalk/<DINGTALK_BRIDGE_TOKEN>
```

安全建议：

1. 只通过 HTTPS 暴露；
2. 不要把 OpenClaw Gateway token 暴露给钉钉；
3. 定期轮换 `.env` 中的 `DINGTALK_BRIDGE_TOKEN`；
4. 生产环境建议在反向代理层加 IP 白名单或额外签名。
