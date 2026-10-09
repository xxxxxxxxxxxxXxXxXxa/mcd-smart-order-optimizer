"""麦麦精算师 — 优化引擎单元测试（dry-run，无需任何 Token）。

运行：python tests/test_optimizer.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.optimizer import (  # noqa: E402
    Coupon,
    apply_coupons,
    filter_menu,
    find_best_combo,
    plan_coupon_usage,
    plan_week,
    rank_points_redeem,
    rank_value,
    solve_combo_deal,
    solve_nutrition,
    solve_nutrition_diet,
    solve_points,
    solve_savings,
)
from src.report import render_report_html, svg_bars  # noqa: E402
from src.scheduler import (  # noqa: E402
    ScheduledOrder,
    add_order,
    evaluate_order,
    is_due,
    load_orders,
    remove_order,
)
from src import mock_data  # noqa: E402

from datetime import datetime  # noqa: E402
import os  # noqa: E402
import tempfile  # noqa: E402


def test_apply_coupons_single_and_order():
    items = [mock_data.MOCK_MENU[1], mock_data.MOCK_MENU[9]]  # mcrib, coke_m
    r = apply_coupons(items, mock_data.MOCK_COUPONS)
    assert r["single_save"] == 15.0, r
    assert r["total"] == 16.0, r  # 10+6，未达满减/折扣门槛
    assert "麦辣鸡腿堡特价¥10" in r["applied"]


def test_apply_coupons_order_fullreduce_beats_percent():
    items = [mock_data.MOCK_MENU[0], mock_data.MOCK_MENU[3]]  # bigmac+quarter=49
    r = apply_coupons(items, mock_data.MOCK_COUPONS)
    assert r["subtotal"] == 49.0
    # 85折省 7.35 > 满30减5，应取折扣
    assert abs(r["order_save"] - round(49 * 0.15, 2)) < 1e-6, r
    assert r["total"] == round(49 * 0.85, 2), r


def test_find_best_combo_hits_target_band():
    combo = find_best_combo(mock_data.MOCK_MENU, target_kcal=800, budget=60)
    assert combo is not None
    assert 680 <= combo["total_kcal"] <= 920, combo
    groups = [it.group for it in combo["items"]]
    assert len(groups) == len(set(groups))  # 同类不重复


def test_find_best_combo_budget_constrained_returns_none():
    assert find_best_combo(mock_data.MOCK_MENU, target_kcal=800, budget=5) is None


def test_rank_points_redeem_sorted_and_value():
    rows = rank_points_redeem(mock_data.MOCK_POINTS_PRODUCTS, balance=2000)
    vals = [r["value_per_1000_points"] for r in rows]
    assert vals == sorted(vals, reverse=True)
    assert "巨无霸兑换券" in [r["name"] for r in rows]
    # 巨无霸券 2000分/¥24 -> 每千积分价值 12.0
    jb = [r for r in rows if r["name"] == "巨无霸兑换券"][0]
    assert jb["value_per_1000_points"] == 12.0, jb


def test_solve_savings_reports_missing_code():
    r = solve_savings(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS, ["mcrib", "notexists"])
    assert "notexists" in r["missing_codes"]


def test_solve_nutrition_attaches_coupon_total():
    c = solve_nutrition(mock_data.MOCK_MENU, 800, 60)
    assert c is not None and "with_coupon_total" in c


def test_solve_points_affordable_flag():
    rows = solve_points(mock_data.MOCK_POINTS_PRODUCTS, 1500)
    for r in rows:
        assert r["affordable"] == (r["points_cost"] <= 1500)


# ---------------------------------------------------------------------------
# v2 新增能力测试
# ---------------------------------------------------------------------------


def test_filter_menu_vegetarian():
    out = filter_menu(mock_data.MOCK_MENU, vegetarian=True)
    assert out, "素食过滤后不应为空"
    assert all(it.vegetarian for it in out)
    names = {it.name for it in out}
    assert "田园沙拉" in names
    assert "巨无霸" not in names


def test_filter_menu_avoid_allergen():
    out = filter_menu(mock_data.MOCK_MENU, avoid=["牛肉"])
    assert all("牛肉" not in it.allergens for it in out)
    assert "巨无霸" not in {it.name for it in out}
    assert len(out) < len(mock_data.MOCK_MENU)


def test_rank_value_sorted_by_protein():
    rows = rank_value(mock_data.MOCK_MENU, by="protein", top_n=8)
    vals = [r["protein_per_yuan"] for r in rows]
    assert len(rows) == 8
    assert vals == sorted(vals, reverse=True)
    assert all(v > 0 for v in vals)


def test_solve_combo_deal_picks_cheapest_route():
    # mcrib(21)+fries_m(12)+coke_m(10)：单品直购 23.8，套餐 36，1+1随心配 19.9
    r = solve_combo_deal(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS,
                         ["mcrib", "fries_m", "coke_m"], mock_data.MOCK_DEALS)
    assert r["best"]["kind"] == "pick2", r["best"]
    assert r["best"]["total"] == 19.9, r["best"]
    assert r["saving_vs_base"] == 3.9, r


def test_plan_coupon_usage_skips_expired_coupon():
    # 券 1 天后过期，订单在第 3 天 —— 不该被分配
    c = Coupon("t1", "测试满20减4", "fullreduce", threshold=20.0, value=4.0,
               expire_days=1)
    orders = [{"order_id": "o1", "day": 3, "items": [mock_data.MOCK_MENU[0]]}]
    r = plan_coupon_usage([c], orders)
    assert r["plan"] == [], r
    assert r["total_saving"] == 0.0


def test_plan_coupon_usage_assigns_and_sums():
    c = Coupon("t2", "测试满20减4", "fullreduce", threshold=20.0, value=4.0,
               expire_days=5)
    orders = [{"order_id": "o1", "day": 3, "items": [mock_data.MOCK_MENU[0]]}]
    r = plan_coupon_usage([c, c], orders)
    assert len(r["plan"]) == 1  # 一个订单只用一张券
    assert r["plan"][0]["saving"] == 4.0
    assert r["total_saving"] == 4.0


def test_plan_coupon_usage_mock_data_saves_money():
    r = plan_coupon_usage(mock_data.MOCK_COUPONS, mock_data.MOCK_ORDERS)
    assert r["total_saving"] > 0, r
    for p in r["plan"]:
        assert p["saving"] > 0
        assert p["expire_days"] >= p["day"]  # 不会用到已过期的券


def test_plan_week_produces_distinct_days():
    r = plan_week(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS, days=5,
                  kcal=700, budget=40)
    assert len(r["days"]) == 5, r
    names = set()
    for d in r["days"]:
        names.update(d["names"])
    assert len(names) >= 5, names   # 尽量不重样
    assert r["avg_kcal"] > 0


def test_solve_nutrition_diet_respects_avoid():
    r = solve_nutrition_diet(mock_data.MOCK_MENU, 800, 60, avoid=["牛肉"])
    assert r is not None
    assert all("牛肉" not in it.allergens for it in r["items"])
    assert r["pool_size"] < len(mock_data.MOCK_MENU)


def test_report_renders_html_and_escapes():
    h = render_report_html("测试", [
        {"heading": "标题<h>", "rows": [("a", 1)],
         "chart": {"rows": [("x", 3.0)], "unit": "g"}},
    ])
    assert "<html" in h and "</html>" in h
    assert "&lt;h&gt;" in h, "标题中的尖括号必须被转义"
    assert svg_bars([("a", 1.0)]).startswith("<svg")
    assert svg_bars([]) == ""


# ---------------------------------------------------------------------------
# 预订单 / 定时点单（scheduler）测试
# ---------------------------------------------------------------------------


def test_scheduler_is_due_matching_time():
    # 2026-10-09 是周五
    o = ScheduledOrder("id1", "午餐", ["mcrib"], hour=11, minute=30)
    assert is_due(o, now=datetime(2026, 10, 9, 11, 32)) is True    # 到点+2分钟
    assert is_due(o, now=datetime(2026, 10, 9, 11, 30)) is True    # 正好到点
    assert is_due(o, now=datetime(2026, 10, 9, 11, 25)) is False   # 还没到
    assert is_due(o, now=datetime(2026, 10, 9, 12, 10)) is False   # 超出宽限窗口


def test_scheduler_is_due_respects_days_and_disabled():
    friday = datetime(2026, 10, 9, 11, 31)    # weekday()==4
    sunday = datetime(2026, 10, 11, 11, 31)   # weekday()==6
    workday_only = ScheduledOrder("id2", "工作日午餐", ["mcrib"],
                                  hour=11, minute=30, days=[0, 1, 2, 3, 4])
    assert is_due(workday_only, now=friday) is True
    assert is_due(workday_only, now=sunday) is False

    disabled = ScheduledOrder("id3", "停用的单", ["mcrib"],
                              hour=11, minute=30, enabled=False)
    assert is_due(disabled, now=friday) is False


def test_scheduler_evaluate_blocks_over_budget_but_always_needs_confirm():
    # bigmac + quarter = 49，85折后 41.65 > 上限 30 → 必须被拦截
    o = ScheduledOrder("id4", "大餐", ["bigmac", "quarter"],
                       hour=12, minute=0, budget_cap=30.0)
    r = evaluate_order(o, mock_data.MOCK_MENU, mock_data.MOCK_COUPONS)
    assert r["total"] > 30.0
    assert r["ready"] is False
    assert any("超出预算上限" in x for x in r["reasons"])

    # 预算充足可以通过，但「仍需人工确认」这条红线不能破
    o2 = ScheduledOrder("id5", "便宜午餐", ["hashbrown"],
                        hour=12, minute=0, budget_cap=50.0)
    r2 = evaluate_order(o2, mock_data.MOCK_MENU, mock_data.MOCK_COUPONS)
    assert r2["ready"] is True
    assert r2["needs_confirm"] is True


def test_scheduler_save_load_roundtrip():
    tmp = os.path.join(tempfile.mkdtemp(), "orders.json")
    o = ScheduledOrder("id6", "测试单", ["mcrib", "coke_m"],
                       hour=9, minute=5, days=[1, 3], budget_cap=25.0,
                       store="滨江店")
    add_order(o, path=tmp)
    loaded = load_orders(tmp)
    assert len(loaded) == 1
    got = loaded[0]
    assert got.name == "测试单"
    assert got.days == [1, 3]
    assert got.budget_cap == 25.0
    assert got.store == "滨江店"
    assert got.hour == 9 and got.minute == 5
    assert remove_order("id6", path=tmp) is True
    assert load_orders(tmp) == []


if __name__ == "__main__":
    passed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            passed += 1
            print("PASS", name)
    print(f"\nALL PASS ({passed} tests)")
