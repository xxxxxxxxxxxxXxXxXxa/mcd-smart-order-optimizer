# 麦当劳 MCP 工具清单（参考）

> 来源：https://github.com/M-China/mcd-mcp-server （截至 2026-10 公开能力整理）
> 本项目实际用到的工具在 `MCP_INTEGRATION.md` 第 2 节；此处给出更完整的目录，便于扩展。

## 点餐与订单
- `query-meals` 查询当前门店可售卖餐品列表（分类/编码/标签）
- `query-meal-detail` 餐品详情（套餐组成、默认选择）
- `calculate-price` 商品价格计算（含券后金额、配送费、应付总价）
- `create-order` 创建订单（返回订单详情与支付链接）
- `query-order` 查询订单详情/进度
- `delivery-query-addresses` 可配送地址列表
- `delivery-create-address` 新增配送地址
- `delivery-query-stores` 外送场景可配送门店
- `query-nearby-stores` 附近门店
- `query-store-coupons` 当前门店可用券
- `query-meal-assistance` 企业团餐助餐服务查询

## 优惠与券
- `available-coupons` 麦麦省可领券列表
- `auto-bind-coupons` 一键领券（领取所有可用券）
- `query-my-coupons` 我的优惠券列表

## 营养
- `list-nutrition-foods` 餐品营养信息（能量/蛋白/脂肪/碳水/钠/钙）

## 积分与商城
- `query-my-account` 我的积分（可用/累计/冻结/即将过期）
- `mall-points-products` 积分兑换商品列表（餐券）
- `mall-product-detail` 积分兑换商品详情
- `mall-create-order` 积分兑换餐券下单
- `mall-create-order-physical` 积分兑换实物下单
- `mall-order-list` 麦麦商城订单列表
- `mall-order-detail` 麦麦商城订单详情

## 活动与杂项
- `campaign-calendar` 活动日历（进行中/往期/未来）
- `now-time-info` 当前时间信息
- （2026 新能力）派对/品鉴会查询预约、积分抽奖、取消订单、餐具选择、麦乐送订单备注、堂食外带取餐柜二维码、麦金卡/早餐卡随单购买等
