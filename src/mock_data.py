"""麦麦精算师 — 样例数据（dry-run 模式使用，无需真实 MCP Token）。

数据取自麦当劳常见餐品与优惠的近似公开信息，仅用于演示算法；
真实价格 / 热量 / 券以麦当劳 MCP 实时返回为准。
"""
from __future__ import annotations

from .optimizer import MenuItem, Coupon, PointsProduct

# 近似菜单（价格单位：元；热量单位：kcal）
MOCK_MENU: List[MenuItem] = [
    MenuItem("bigmac", "巨无霸", 24.0, 563, 28.0, 32.0, 42.0, 1010, "主食"),
    MenuItem("mcrib", "麦辣鸡腿堡", 21.0, 517, 25.0, 28.0, 41.0, 980, "主食"),
    MenuItem("fillet", "麦香鱼", 22.0, 396, 18.0, 18.0, 39.0, 720, "主食"),
    MenuItem("quarter", "四分之一磅牛肉堡", 25.0, 630, 33.0, 36.0, 46.0, 1180, "主食"),
    MenuItem("mcchicken", "麦香鸡", 17.0, 430, 19.0, 24.0, 36.0, 800, "主食"),
    MenuItem("nuggets6", "麦乐鸡(6块)", 18.0, 296, 16.0, 17.0, 17.0, 620, "小食"),
    MenuItem("fries_m", "薯条(中)", 12.0, 337, 4.0, 16.0, 42.0, 240, "小食"),
    MenuItem("corn", "玉米杯", 9.0, 112, 4.0, 2.0, 22.0, 10, "小食"),
    MenuItem("hashbrown", "薯饼", 7.0, 160, 2.0, 9.0, 18.0, 300, "小食"),
    MenuItem("coke_m", "可乐(中)", 10.0, 150, 0.0, 0.0, 38.0, 20, "饮料"),
    MenuItem("sprite_m", "雪碧(中)", 10.0, 145, 0.0, 0.0, 36.0, 20, "饮料"),
    MenuItem("orange", "鲜煮咖啡", 13.0, 15, 1.0, 0.5, 2.0, 5, "饮料"),
    MenuItem("mcflurry", "麦旋风(奥利奥)", 14.0, 330, 6.0, 12.0, 49.0, 150, "甜品"),
    MenuItem("apple", "苹果片", 8.0, 35, 0.0, 0.0, 8.0, 0, "甜品"),
    MenuItem("combo_bigmac", "巨无霸套餐", 42.0, 880, 38.0, 41.0, 92.0, 1400, "套餐",
             ["含饮料", "含小食"]),
    MenuItem("combo_mcrib", "麦辣鸡腿堡套餐", 39.0, 820, 35.0, 40.0, 90.0, 1350, "套餐"),
]

# 近似优惠券
MOCK_COUPONS: List[Coupon] = [
    Coupon("c1", "麦辣鸡腿堡特价¥10", "single", value=10.0, applies_to=["mcrib"]),
    Coupon("c2", "麦乐鸡(6块)特价¥12", "single", value=12.0, applies_to=["nuggets6"]),
    Coupon("c3", "可乐(中)特价¥6", "single", value=6.0, applies_to=["coke_m"]),
    Coupon("c4", "满30减5", "fullreduce", threshold=30.0, value=5.0),
    Coupon("c5", "满50减10", "fullreduce", threshold=50.0, value=10.0),
    Coupon("c6", "全单85折", "percent", threshold=25.0, value=0.85),
]

# 近似积分商城
MOCK_POINTS_PRODUCTS: List[PointsProduct] = [
    PointsProduct("p1", "薯条(中)兑换券", 1200, 12.0, "coupon"),
    PointsProduct("p2", "麦辣鸡腿堡兑换券", 1800, 21.0, "coupon"),
    PointsProduct("p3", "巨无霸兑换券", 2000, 24.0, "coupon"),
    PointsProduct("p4", "麦旋风兑换券", 1500, 14.0, "coupon"),
    PointsProduct("p5", "麦当劳保温杯(实物)", 6000, 49.0, "physical"),
    PointsProduct("p6", "麦麦公仔(实物)", 8000, 59.0, "physical"),
]
