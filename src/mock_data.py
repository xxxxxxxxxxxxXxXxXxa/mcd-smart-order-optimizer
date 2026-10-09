"""麦麦精算师 — 样例数据（dry-run 模式使用，无需真实 MCP Token）。

数据取自麦当劳常见餐品与优惠的近似公开信息，仅用于演示算法；
真实价格 / 热量 / 券 / 过敏原以麦当劳 MCP 实时返回为准。

注意：前 16 个餐品的顺序与取值保持稳定，单元测试依赖其索引。
"""
from __future__ import annotations

from .optimizer import MenuItem, Coupon, PointsProduct, ComboDeal

# 近似菜单（价格单位：元；热量单位：kcal；钠单位：mg）
MOCK_MENU = [
    MenuItem("bigmac", "巨无霸", 24.0, 563, 28.0, 32.0, 42.0, 1010, "主食",
             [], ["牛肉", "小麦", "乳制品", "芝麻"]),
    MenuItem("mcrib", "麦辣鸡腿堡", 21.0, 517, 25.0, 28.0, 41.0, 980, "主食",
             [], ["鸡肉", "小麦", "麸质"]),
    MenuItem("fillet", "麦香鱼", 22.0, 396, 18.0, 18.0, 39.0, 720, "主食",
             [], ["鱼类", "小麦"]),
    MenuItem("quarter", "四分之一磅牛肉堡", 25.0, 630, 33.0, 36.0, 46.0, 1180, "主食",
             [], ["牛肉", "小麦"]),
    MenuItem("mcchicken", "麦香鸡", 17.0, 430, 19.0, 24.0, 36.0, 800, "主食",
             [], ["鸡肉", "小麦"]),
    MenuItem("nuggets6", "麦乐鸡(6块)", 18.0, 296, 16.0, 17.0, 17.0, 620, "小食",
             [], ["鸡肉", "小麦"]),
    MenuItem("fries_m", "薯条(中)", 12.0, 337, 4.0, 16.0, 42.0, 240, "小食",
             [], ["马铃薯"], True),
    MenuItem("corn", "玉米杯", 9.0, 112, 4.0, 2.0, 22.0, 10, "小食",
             [], [], True),
    MenuItem("hashbrown", "薯饼", 7.0, 160, 2.0, 9.0, 18.0, 300, "小食",
             [], ["马铃薯"], True),
    MenuItem("coke_m", "可乐(中)", 10.0, 150, 0.0, 0.0, 38.0, 20, "饮料"),
    MenuItem("sprite_m", "雪碧(中)", 10.0, 145, 0.0, 0.0, 36.0, 20, "饮料"),
    MenuItem("orange", "鲜煮咖啡", 13.0, 15, 1.0, 0.5, 2.0, 5, "饮料",
             [], ["咖啡因"], True),
    MenuItem("mcflurry", "麦旋风(奥利奥)", 14.0, 330, 6.0, 12.0, 49.0, 150, "甜品",
             [], ["乳制品", "小麦"]),
    MenuItem("apple", "苹果片", 8.0, 35, 0.0, 0.0, 8.0, 0, "甜品",
             [], [], True),
    MenuItem("combo_bigmac", "巨无霸套餐", 42.0, 880, 38.0, 41.0, 92.0, 1400, "套餐",
             ["含饮料", "含小食"], ["牛肉", "小麦", "乳制品"]),
    MenuItem("combo_mcrib", "麦辣鸡腿堡套餐", 39.0, 820, 35.0, 40.0, 90.0, 1350, "套餐",
             ["含饮料", "含小食"], ["鸡肉", "小麦"]),

    # ---- v2 新增餐品（早餐 / 轻食 / 素食 / 咖啡）----
    MenuItem("muffin", "吉士蛋麦满分", 15.0, 390, 22.0, 18.0, 36.0, 780, "主食",
             ["早餐"], ["鸡蛋", "小麦", "乳制品"]),
    MenuItem("congee", "皮蛋瘦肉粥", 12.0, 260, 12.0, 6.0, 34.0, 900, "主食",
             ["早餐"], ["猪肉", "鸡蛋"]),
    MenuItem("wings", "麦辣鸡翅(2块)", 13.0, 240, 14.0, 15.0, 12.0, 620, "小食",
             [], ["鸡肉", "小麦"]),
    MenuItem("salad", "田园沙拉", 16.0, 120, 6.0, 5.0, 12.0, 210, "小食",
             ["轻食"], [], True),
    MenuItem("milk", "热牛奶", 8.0, 130, 8.0, 7.0, 12.0, 120, "饮料",
             [], ["乳制品"]),
    MenuItem("latte", "拿铁", 18.0, 120, 10.0, 6.0, 12.0, 95, "饮料",
             [], ["乳制品", "咖啡因"]),
    MenuItem("sundae", "圆筒冰淇淋", 6.0, 200, 4.0, 6.0, 33.0, 80, "甜品",
             [], ["乳制品"]),
    MenuItem("nuggets10", "麦乐鸡(10块)", 26.0, 490, 27.0, 28.0, 28.0, 1030, "小食",
             [], ["鸡肉", "小麦"]),
    MenuItem("combo_breakfast", "早餐套餐", 22.0, 620, 30.0, 28.0, 62.0, 1200, "套餐",
             ["含饮料"], ["鸡蛋", "小麦", "乳制品"]),
    MenuItem("wrap", "鸡肉卷", 19.0, 480, 24.0, 22.0, 44.0, 980, "主食",
             [], ["鸡肉", "小麦"]),
]

# 近似优惠券（expire_days = 剩余有效天数，用于券包排程）
MOCK_COUPONS = [
    Coupon("c1", "麦辣鸡腿堡特价¥10", "single", value=10.0, applies_to=["mcrib"],
           expire_days=3),
    Coupon("c2", "麦乐鸡(6块)特价¥12", "single", value=12.0, applies_to=["nuggets6"],
           expire_days=7),
    Coupon("c3", "可乐(中)特价¥6", "single", value=6.0, applies_to=["coke_m"],
           expire_days=2),
    Coupon("c4", "满30减5", "fullreduce", threshold=30.0, value=5.0, expire_days=10),
    Coupon("c5", "满50减10", "fullreduce", threshold=50.0, value=10.0, expire_days=14),
    Coupon("c6", "全单85折", "percent", threshold=25.0, value=0.85, expire_days=5),
    # v2 新增（门槛设置避开既有单测的金额区间，保证旧断言稳定）
    Coupon("c7", "满60减12", "fullreduce", threshold=60.0, value=12.0, expire_days=20),
    Coupon("c8", "麦辣鸡翅特价¥8", "single", value=8.0, applies_to=["wings"],
           expire_days=6),
]

# 优惠组合：官方套餐(set) / 1+1随心配(pick2)
MOCK_DEALS = [
    ComboDeal("d1", "麦辣鸡腿堡套餐", "set", 36.0,
              includes=["mcrib", "fries_m", "coke_m"]),
    ComboDeal("d2", "1+1随心配", "pick2", 13.9,
              candidates=["mcrib", "mcchicken", "fillet", "nuggets6", "fries_m",
                          "coke_m", "sprite_m", "corn", "hashbrown", "apple",
                          "wings", "sundae"]),
    ComboDeal("d3", "早餐组合", "set", 20.0, includes=["muffin", "milk"]),
]

# 近似积分商城
MOCK_POINTS_PRODUCTS = [
    PointsProduct("p1", "薯条(中)兑换券", 1200, 12.0, "coupon"),
    PointsProduct("p2", "麦辣鸡腿堡兑换券", 1800, 21.0, "coupon"),
    PointsProduct("p3", "巨无霸兑换券", 2000, 24.0, "coupon"),
    PointsProduct("p4", "麦旋风兑换券", 1500, 14.0, "coupon"),
    PointsProduct("p5", "麦当劳保温杯(实物)", 6000, 49.0, "physical"),
    PointsProduct("p6", "麦麦公仔(实物)", 8000, 59.0, "physical"),
    PointsProduct("p7", "双层吉士汉堡券", 1500, 18.0, "coupon"),
    PointsProduct("p8", "早餐套餐券", 2200, 22.0, "coupon"),
]

# 示例「计划订单」（演示券包排程用：order_id / 第几天下单 / 买了什么）
MOCK_ORDERS = [
    {"order_id": "周一午餐", "day": 1, "items": [MOCK_MENU[1], MOCK_MENU[9]]},      # mcrib + coke_m
    {"order_id": "周三晚餐", "day": 3, "items": [MOCK_MENU[0], MOCK_MENU[5]]},      # bigmac + nuggets6
    {"order_id": "周五聚餐", "day": 5,
     "items": [MOCK_MENU[1], MOCK_MENU[18], MOCK_MENU[6]]},                          # mcrib + wings + fries_m
]
