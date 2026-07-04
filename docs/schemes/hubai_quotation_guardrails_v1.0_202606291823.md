# HubAI 报价系统数据安全规则（无数据不编造）

> 版本：v1.0  
> 日期：2026-06-29  
> 原则：**宁可报不了价，绝不编造数据**

---

## 一、核心原则

### 1.1 数据完整性三原则

| 原则 | 说明 | 违反后果 |
|------|------|---------|
| **无价格不报价** | 产品价格必须从权威数据源获取，禁止估算/假设 | 拒绝报价，提示补充 |
| **无库存不承诺** | 库存数据缺失时，不承诺交付时间 | 标注"待确认"，转人工 |
| **无策略不折扣** | 折扣必须有策略依据，禁止口头折扣 | 按原价计算，标注"无折扣" |

### 1.2 数据源优先级（从高到低）

```
P0: 数据库 product_price 表（实时权威）
P1: 产品 Skill 配置文件 config/price.json（静态配置）
P2: 报价策略表 quotation_policy（策略驱动）
P3: ❌ 绝对禁止：大模型估算、经验值、假设值
```

---

## 二、通用检查规则（Guardrails）

### 2.1 报价前必检清单（Checklist）

| 检查项 | 数据源 | 缺失时行为 | 错误码 |
|--------|--------|-----------|--------|
| 产品是否存在 | 数据库/配置 | ❌ 拒绝报价 | Q001 |
| 产品是否上架 | 数据库/配置 | ❌ 拒绝报价 | Q002 |
| 价格是否存在 | 数据库/配置 | ❌ 拒绝报价 | Q003 |
| 价格是否过期 | 数据库 valid_to | ⚠️ 提示过期，拒绝报价 | Q203 |
| 库存是否充足 | 数据库 inventory | ⚠️ 标注"待确认"，不承诺交付 | Q101 |
| 折扣策略是否存在 | 数据库 policy | ℹ️ 按原价计算，无折扣 | - |
| 成本价是否存在 | 数据库/配置 | ⚠️ 不计算毛利率 | - |

### 2.2 规则校验流程

```
用户发起报价请求
    ↓
[Step 1] 产品存在性检查
    ├── 数据库有记录 → 继续
    ├── 配置文件有数据 → 继续
    └── 都无 → ❌ 返回 "产品未配置，无法报价"
    ↓
[Step 2] 价格有效性检查
    ├── 数据库有有效价格 → 使用数据库价格
    ├── 配置文件有价格 → 使用配置价格（标注"配置价"）
    └── 都无 → ❌ 返回 "价格数据缺失，无法报价"
    ↓
[Step 3] 折扣策略检查
    ├── 数据库有策略 → 应用策略折扣
    ├── 配置有折扣 → 应用配置折扣
    └── 都无 → ℹ️ 原价计算，标注"无折扣策略"
    ↓
[Step 4] 库存检查
    ├── 数据库有库存且充足 → 标注"现货"
    ├── 数据库有库存但不足 → ⚠️ 标注"库存不足，需确认"
    └── 数据库无库存数据 → ⚠️ 标注"库存待确认"
    ↓
[Step 5] 成本价检查
    ├── 有成本价 → 计算毛利率
    └── 无成本价 → ⚠️ 不计算毛利率，标注"毛利待确认"
    ↓
生成报价单（标注数据来源）
```

---

## 三、产品 Skill 配置化价格方案

### 3.1 为什么需要配置化价格

当前问题：数据库未落地，但报价系统需要能运行。
解决方案：**配置文件作为数据库的降级数据源**，数据库有数据时优先用数据库，数据库不可用或数据缺失时用配置文件。

### 3.2 配置文件规范

每个产品 Skill 增加 `config/price.json`：

```json
{
  "product_code": "cloud-desktop",
  "product_name": "云桌面",
  "version": "1.0.0",
  "data_source": "config",  // config | database
  "prices": [
    {
      "spec_code": "basic",
      "spec_name": "基础型（2核4G）",
      "unit_price": 45.00,
      "cost_price": 28.00,
      "unit": "点/月",
      "valid_from": "2026-01-01",
      "valid_to": null,
      "status": "active"
    },
    {
      "spec_code": "standard",
      "spec_name": "标准型（4核8G）",
      "unit_price": 88.00,
      "cost_price": 55.00,
      "unit": "点/月",
      "valid_from": "2026-01-01",
      "valid_to": null,
      "status": "active"
    }
  ],
  "discount_policies": [
    {
      "policy_code": "SCALE_DISCOUNT",
      "policy_name": "规模折扣",
      "rules": [
        {"min_quantity": 1, "max_quantity": 10, "discount_rate": 1.00},
        {"min_quantity": 11, "max_quantity": 50, "discount_rate": 0.97},
        {"min_quantity": 51, "max_quantity": 100, "discount_rate": 0.93},
        {"min_quantity": 101, "max_quantity": 300, "discount_rate": 0.88},
        {"min_quantity": 301, "max_quantity": null, "discount_rate": 0.83}
      ]
    }
  ],
  "inventory": {
    "track_inventory": false,
    "default_available": 9999
  }
}
```

### 3.3 价格引擎改造逻辑

```python
def calculate_price(product_code: str, quantity: int, customer_level: str = "standard") -> dict:
    """计算价格 - 支持数据库和配置双数据源"""
    
    # Step 1: 尝试从数据库获取
    db_price = get_price_from_database(product_code)
    if db_price:
        data_source = "database"
        price = db_price
    else:
        # Step 2: 数据库无数据，尝试配置文件
        config_price = get_price_from_config(product_code)
        if config_price:
            data_source = "config"
            price = config_price
        else:
            # Step 3: 都无数据 → 拒绝报价
            return {
                "success": False,
                "error_code": "Q003",
                "error_message": "产品无有效价格",
                "details": {
                    "product_code": product_code,
                    "reason": "数据库和配置文件均未找到价格数据",
                    "action": "请联系管理员配置产品价格"
                }
            }
    
    # Step 4: 应用折扣策略
    discount = get_discount_from_database(quantity, customer_level) \
               or get_discount_from_config(quantity, customer_level) \
               or {"discount_rate": 1.0, "source": "none"}
    
    # Step 5: 计算
    unit_price_final = price["unit_price"] * discount["discount_rate"]
    line_amount = unit_price_final * quantity
    
    # Step 6: 计算毛利率（有成本价时）
    margin_info = {}
    if price.get("cost_price"):
        margin_rate = (unit_price_final - price["cost_price"]) / unit_price_final
        margin_info = {
            "margin_rate": round(margin_rate, 4),
            "margin_amount": round((unit_price_final - price["cost_price"]) * quantity, 2)
        }
    else:
        margin_info = {
            "margin_rate": None,
            "margin_note": "成本价未配置，无法计算毛利率"
        }
    
    return {
        "success": True,
        "product_code": product_code,
        "data_source": data_source,  // 标注数据来源
        "unit_price_original": price["unit_price"],
        "discount_rate": discount["discount_rate"],
        "discount_source": discount.get("source", "none"),
        "unit_price_final": unit_price_final,
        "quantity": quantity,
        "line_amount": line_amount,
        **margin_info
    }
```

---

## 四、无数据提示话术模板

### 4.1 产品不存在

```
❌ 无法报价

产品 "{product_code}" 未在系统中注册。

可能原因：
- 产品编码错误
- 产品尚未上架

建议操作：
1. 确认产品名称/编码是否正确
2. 联系管理员添加该产品
```

### 4.2 价格缺失

```
❌ 无法报价 — 价格数据缺失

产品：{product_name}
状态：已上架，但价格未配置

当前情况：
- 数据库价格表：无数据
- 配置文件：无价格

建议操作：
1. 联系产品管理员配置价格
2. 或使用人工报价流程

⚠️ 重要：系统不会估算或假设价格，以确保报价准确性。
```

### 4.3 库存待确认

```
⚠️ 报价草稿已生成（库存待确认）

产品：{product_name} x {quantity}
单价：¥{unit_price_final}
小计：¥{line_amount}

库存状态：待确认
- 系统未获取到实时库存数据
- 交付时间需人工确认

建议操作：
1. 联系供应链确认库存
2. 确认后更新报价单

[查看报价单] [转人工确认]
```

### 4.4 原价计算（无折扣策略）

```
✅ 报价草稿已生成（无折扣）

产品：{product_name} x {quantity}
原价：¥{unit_price_original}
折扣：无折扣策略配置
实价：¥{unit_price_final}
小计：¥{line_amount}

说明：
- 未找到匹配的折扣策略
- 按原价计算
- 如需申请折扣，请联系销售经理

[查看报价单] [申请折扣]
```

---

## 五、实施检查清单

### 5.1 产品 Skill 改造

- [ ] 每个产品创建 `config/price.json`
- [ ] `price_engine.py` 改造：支持 config/database 双数据源
- [ ] `price_engine.py` 改造：无数据时返回错误而非估算
- [ ] `rule_validator.py` 改造：增加配置数据源检查

### 5.2 话术模板补充

- [ ] 补充 "产品不存在" 提示话术
- [ ] 补充 "价格缺失" 提示话术
- [ ] 补充 "库存待确认" 提示话术
- [ ] 补充 "原价计算" 提示话术

### 5.3 底座增强

- [ ] `errors.py` 增加 "CONFIG_PRICE_NOT_FOUND" 错误码
- [ ] `config.py` 增加配置加载校验逻辑

---

## 六、兜底规则

### 6.1 最终防线

如果所有数据源都不可用的极端情况：

```
❌ 系统暂不可用

当前状态：
- 数据库：未连接
- 配置文件：未找到

系统不会进行以下操作：
❌ 估算价格
❌ 假设折扣
❌ 编造库存
❌ 推测成本

请稍后再试，或联系管理员。
```

### 6.2 人工介入触发条件

| 条件 | 自动行为 | 人工介入 |
|------|---------|---------|
| 产品存在 + 价格存在 + 库存充足 | ✅ 自动报价 | 无需 |
| 产品存在 + 价格存在 + 库存不足 | ⚠️ 报价+标注"库存不足" | 供应链确认 |
| 产品存在 + 价格缺失 | ❌ 拒绝报价 | 产品管理员补录价格 |
| 产品不存在 | ❌ 拒绝报价 | 管理员新增产品 |
| 所有数据源不可用 | ❌ 系统不可用 | 技术排查 |

---

**编制人**：AI+比特虾 🦐  
**日期**：2026-06-29  
**版本**：v1.0
