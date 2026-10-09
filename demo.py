"""麦麦精算师 — 一站式演示（dry-run，无需 Token）。

运行：python demo.py
"""
import sys

from src import mock_data
from src.cli import run_save, run_nutrition, run_points

print("=" * 30, "省钱模式", "=" * 30)
run_save(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS, ["mcrib", "coke_m"])

print("\n" + "=" * 30, "营养达标 800kcal / 预算45", "=" * 30)
run_nutrition(mock_data.MOCK_MENU, 800, 45)

print("\n" + "=" * 30, "积分策略 余额5000", "=" * 30)
run_points(mock_data.MOCK_POINTS_PRODUCTS, 5000)
