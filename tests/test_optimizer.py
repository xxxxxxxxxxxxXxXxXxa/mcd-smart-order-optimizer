"""麦麦精算师 — 优化引擎单元测试（dry-run，无需任何 Token）。

运行：python tests/test_optimizer.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.optimizer import (  # noqa: E402
    apply_coupons,
    find_best_combo,
    rank_points_redeem,
    solve_nutrition,
    solve_points,
    solve_savings,
)
from src import mock_data  # noqa: E402


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


if __name__ == "__main__":
    passed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            passed += 1
            print("PASS", name)
    print(f"\nALL PASS ({passed} tests)")
