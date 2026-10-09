---
name: mcd-smart-order-optimizer
version: 1.0.0
description: 麦麦精算师 —— 基于麦当劳 MCP 的智能点餐优化技能。当用户要「用麦当劳 MCP 点餐 / 省钱 / 领券 / 查营养热量 / 按预算搭配套餐 / 用积分兑换 / 比价 / 一键下单」时使用。自动领券 + 实时菜单 + 营养数据 + 多目标优化引擎，给出预算内、热量达标、蛋白更高的「最优组合」与「到手价」，确认后再下单。
---

# 麦麦精算师 (McDonald's Smart Order Optimizer)

把麦当劳 MCP 的「查菜单 / 营养 / 领券 / 算价 / 积分 / 下单」能力，升级成一个会算账、懂营养的**点餐大脑**，而不是把工具结果原样甩给用户。

## 何时使用本技能

- 「帮我把这顿麦当劳点到最便宜」「自动帮我领券再用」
- 「我在控卡，800 大卡怎么点麦当劳最划算」「给我一份高蛋白低卡的搭配」
- 「我有多少积分，换什么最值」「用积分兑还是直接买」
- 「附近门店有哪些」「按预算给我配一份套餐」

## 前置条件

1. 已在 WorkBuddy 左侧【连接器】中配置并启用麦当劳 MCP（`mcd-mcp`）：
   ```json
   {
     "mcpServers": {
       "mcd-mcp": {
         "type": "streamablehttp",
         "url": "https://mcp.mcd.cn",
         "headers": { "Authorization": "Bearer ${MCD_MCP_TOKEN}" }
       }
     }
   }
   ```
   Token 通过环境变量 `${MCD_MCP_TOKEN}` 注入，**绝不要写死到文件里**（见 CONTEST_DECLARATION.md 信息安全声明）。
2. 本仓库 `src/` 已就位（无需第三方依赖，仅 Python 标准库）。

## 工作流

### 模式 A：省钱（给定想买的清单）
1. 调用 `auto-bind-coupons`（或 `available-coupons` / `query-my-coupons` / `query-store-coupons`）拿到可用券。
2. 调用 `query-meals` / `query-meal-detail` 拿到菜单与单价。
3. 把「清单 + 券」交给 `src/optimizer.py: apply_coupons / solve_savings` 计算最优用券后的**到手价**。
4. 把到手价与已用券列给用户，**确认后**再走下单流程。

### 模式 B：营养达标（给定热量/蛋白目标 + 预算）
1. `query-neals` + `list-nutrition-foods` 拿到餐品与营养。
2. 交 `find_best_combo / solve_nutrition`：在预算内枚举「每类至多 1 件」的组合，按
   `score = 蛋白*0.3 - |热量-目标|/5 - 价格*0.1` 取最优，输出贴合目标热量且蛋白更高的搭配。
3. 给出组合、总热量、总蛋白、到手价，确认后下单。

### 模式 C：积分策略（给定积分余额）
1. `query-my-account` 查余额，`mall-points-products` 查可兑商品。
2. 交 `rank_points_redeem / solve_points`：按「每千积分价值 = 市场价/积分*1000」排序，标出可兑项。
3. 给出「换什么最值 / 何时不如直接买」的建议。

### 下单（需用户明确确认）
- 外送：`delivery-query-addresses` →（无地址则 `delivery-create-address`）→ `delivery-query-stores` → `calculate-price` → **`create-order`**（返回支付链接）→ `query-order` 跟踪。
- 到店/自取：`query-nearby-stores` → `calculate-price` → `create-order`。
- ⚠️ 任何 `create-order` / `mall-create-order` / `mall-create-order-physical` 必须先向用户复述金额与内容并获确认，再调用。

## 安全与合规红线

- **绝不**在回复、日志、提交物中泄露真实 Token / 手机号 / 订单号。
- `create-order` 等写操作必须二次确认；宁可多问一句，不替用户剁手。
- 营养建议仅供参考，不构成专业医疗/膳食建议（见 CONTEST_DECLARATION.md）。
- 仅对麦当劳官方 MCP（`https://mcp.mcd.cn`）发起请求。
