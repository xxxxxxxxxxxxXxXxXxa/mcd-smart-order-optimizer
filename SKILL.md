---
name: mcd-smart-order-optimizer
version: 2.0.0
description: 麦麦精算师 —— 基于麦当劳 MCP 的智能点餐优化技能。当用户要「用麦当劳 MCP 点餐 / 省钱 / 领券 / 查营养热量 / 按预算搭配套餐 / 用积分兑换 / 比价 / 一键下单」时使用。九大能力：省钱用券、营养达标、积分策略、套餐拆解（单品 vs 官方套餐 vs 1+1随心配）、性价比榜（每元蛋白/每元热量）、忌口过滤（素食/过敏原/限钠）、券包排程（带到期日不浪费）、多天饮食计划（控热量控预算不重样）、可分享 HTML 报告。给出预算内、热量达标、蛋白更高的「最优组合」与「到手价」，确认后再下单。
---

# 麦麦精算师 (McDonald's Smart Order Optimizer)

把麦当劳 MCP 的「查菜单 / 营养 / 领券 / 算价 / 积分 / 下单」能力，升级成一个会算账、懂营养的**点餐大脑**，而不是把工具结果原样甩给用户。

## 何时使用本技能

- 「帮我把这顿麦当劳点到最便宜」「自动帮我领券再用」
- 「我在控卡，800 大卡怎么点麦当劳最划算」「给我一份高蛋白低卡的搭配」
- 「我有多少积分，换什么最值」「用积分兑还是直接买」
- 「附近门店有哪些」「按预算给我配一份套餐」
- 「这份清单买单品划算还是点套餐划算」「1+1 随心配怎么用最省」
- 「哪款麦当劳性价比最高」「同样 20 块买什么蛋白最多」
- 「我不吃牛肉 / 乳制品过敏 / 要素食 / 要限钠，怎么点」
- 「我有一堆快过期的券，怎么安排这几顿最划算」
- 「帮我排一周的麦当劳，控卡又省钱、别天天重复」

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

### 模式 D：套餐拆解（单品直购 vs 官方套餐 vs 1+1随心配）
1. `query-meals` 拿餐品与单价；若有套餐 / 随心配活动，构造 `ComboDeal`
   （`set`：套餐固定价覆盖若干件；`pick2`：固定价任选 N 件）。
2. 交 `solve_combo_deal`：并行对比三条路 —— 单品直购（自动用券）/ 官方套餐 /
   1+1随心配（固定价，取清单内**最贵的 2 件**替换最划算）。
3. 输出每条路线的总价、最优路线、相对「单品直购」省了多少，确认后下单。

### 模式 E：性价比榜（每元蛋白 / 每元热量）
1. `list-nutrition-foods` 拿营养数据。
2. 交 `rank_value`：算 **每元蛋白(g/元)**、**每元热量(kcal/元)**、综合性价比指数。
3. 输出 TOP N，直接回答「同样花一块钱，谁给的蛋白最多」。

### 模式 F：忌口过滤（素食 / 过敏原 / 限钠）
1. 问清忌口（「不吃牛肉」「乳制品过敏」「限钠 800mg」等）。
2. 交 `filter_menu` 过滤菜单，再走 `solve_nutrition_diet` 求最优组合。
3. **必须说明被过滤掉了什么**，避免用户吃到不该吃的。

### 模式 G：券包排程（带到期日，别浪费）
1. `query-my-coupons` 拿券包（含有效期 / 剩余天数）。
2. 向用户确认未来几笔计划订单（哪天买什么）。
3. 交 `plan_coupon_usage`：按「到期日升序、面额降序」贪心分配 —— 快过期的先用掉，
   且**不会把券分到它已过期的订单上**（下单日晚于到期日则跳过）。
4. 输出「哪张券用在哪个订单、各省多少、总省多少」，并列出没用上的券及原因。

### 模式 H：多天饮食计划（控热量 + 控预算 + 不重样）
1. 问清天数、每餐热量目标、每餐预算、忌口。
2. 交 `plan_week`：逐天求最优组合，并把**已用过的餐品排除**在下一天之外，实现「尽量不重样」。
3. 输出每天搭配、热量、蛋白、花费与省了多少，以及合计与日均。

### 模式 I：分享报告
调用 `src/report.py: render_report_html / write_report`，把优化结果生成为
**单文件 HTML**（内联 SVG 图表、无外链资源），可直接打开或分享。

### 模式 J：预订单 / 定时点单（⚠️ 默认必须人工确认）
1. 用户说「每天 11:30 帮我点 XX」「工作日午餐自动提醒我」时，用 `src/scheduler.py` 建预订单：
   `ScheduledOrder(name, item_codes, hour, minute, days, store, budget_cap)`，
   存到本地 `~/.mcd_scheduled_orders.json`。
2. 到点时（`is_due` / `due_orders`，带 5 分钟宽限窗口，调度器晚跑几分钟也不漏单）执行：
   - **必须用实时数据重新核价**（`query-meals` + `available-coupons`）；
     ⚠️ 绝不沿用建单时算出的旧价 —— 价格、券、在售状态随时会变。
   - 跑安全闸门 `evaluate_order`：餐品是否还在售、到手价是否超出 `budget_cap`。
   - 输出「待确认订单卡片」`format_card`。
3. **红线**：`needs_confirm` 恒为 `True` —— 任何预订单都必须先向用户复述金额与内容、
   获得明确确认后，才允许调用 `create-order`。
   `auto_confirm` 默认 `False`；用户要求开启前，**必须先讲清风险并取得同意**。
4. 被拦截（售罄 / 超预算）时**不下单**，只把原因告诉用户。

> 真正的「到点自动触发」由外部调度器完成（cron / Windows 任务计划程序 / WorkBuddy 定时自动化），
> 让它定时执行 `schedule due` 并把待确认卡片推给用户。CLI 本身不做后台常驻。
> 仓库已附 [`workbuddy.automation.json`](./workbuddy.automation.json)：一条「工作日 11:30」recurring 自动化配置，
> 含完整 prompt 与五条安全红线，复制即用；作者也已在本 WorkBuddy 中建好并设为 ACTIVE。

### 下单（需用户明确确认）
- 外送：`delivery-query-addresses` →（无地址则 `delivery-create-address`）→ `delivery-query-stores` → `calculate-price` → **`create-order`**（返回支付链接）→ `query-order` 跟踪。
- 到店/自取：`query-nearby-stores` → `calculate-price` → `create-order`。
- ⚠️ 任何 `create-order` / `mall-create-order` / `mall-create-order-physical` 必须先向用户复述金额与内容并获确认，再调用。

## 安全与合规红线

- **绝不**在回复、日志、提交物中泄露真实 Token / 手机号 / 订单号。
- `create-order` 等写操作必须二次确认；宁可多问一句，不替用户剁手。
- 营养建议仅供参考，不构成专业医疗/膳食建议（见 CONTEST_DECLARATION.md）。
- 仅对麦当劳官方 MCP（`https://mcp.mcd.cn`）发起请求。
