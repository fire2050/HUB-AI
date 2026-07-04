---
name: hubai-base
description: >
  HubAI 报价系统基础能力包。
  提供数据库连接、配置管理、日志审计、权限校验等底层能力。
  被 smart-quotation 等业务 Skill 依赖。
allowed-tools:
  - Read
  - Write
  - Edit
  - exec
dependencies: []
---

# HubAI Base - 基础能力包

## 核心能力

1. **数据库连接池**：SQLite/PostgreSQL 统一连接管理
2. **配置管理**：多环境配置加载与热更新
3. **日志审计**：统一日志格式、自动轮转、审计追踪
4. **权限校验**：基于角色的访问控制（RBAC）
5. **工具函数**：数据转换、格式校验、加密解密、日期处理
