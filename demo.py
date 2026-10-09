"""麦麦精算师 — 一站式演示（dry-run，无需 Token，无需 WorkBuddy）。

运行：python demo.py
覆盖：省钱 / 营养 / 积分 / 套餐拆解 / 性价比榜 / 多天计划 / 券包排程 / 分享报告
"""
from src import mock_data
from src.cli import (
    run_combo,
    run_coupons,
    run_nutrition,
    run_plan,
    run_points,
    run_report,
    run_save,
    run_value,
)


def title(text: str):
    print("\n" + "=" * 12, text, "=" * 12)


title("① 省钱模式：想买 麦辣鸡腿堡 + 可乐(中)")
run_save(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS, ["mcrib", "coke_m"])

title("② 营养达标：700 kcal / 预算 40")
run_nutrition(mock_data.MOCK_MENU, 700, 40)

title("③ 忌口营养：素食，600 kcal / 预算 35")
run_nutrition(mock_data.MOCK_MENU, 600, 35, vegetarian=True)

title("④ 积分策略：余额 5000")
run_points(mock_data.MOCK_POINTS_PRODUCTS, 5000)

title("⑤ 套餐拆解：麦辣鸡腿堡 + 薯条(中) + 可乐(中)")
run_combo(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS,
          mock_data.MOCK_DEALS, ["mcrib", "fries_m", "coke_m"])

title("⑥ 性价比榜：每元能买到多少蛋白（TOP 6）")
run_value(mock_data.MOCK_MENU, "protein", 6)

title("⑦ 多天饮食计划：5 天 / 700 kcal / 每餐 40 元")
run_plan(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS, 5, 700, 40)

title("⑧ 券包排程：多张带到期日的券怎么用在各订单")
run_coupons(mock_data.MOCK_COUPONS, mock_data.MOCK_ORDERS)

title("⑨ 生成可分享 HTML 报告")
run_report(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS,
           mock_data.MOCK_DEALS, mock_data.MOCK_POINTS_PRODUCTS,
           "mcd_report.html")

print("\n演示结束。以上全部为 dry-run（样例数据），无需麦当劳 Token。")
