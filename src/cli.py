"""麦麦精算师 — 命令行入口（无需 WorkBuddy 也能直接跑）。

用法：
  python -m src.cli save --items mcrib,coke_m
  python -m src.cli nutrition --kcal 800 --budget 45
  python -m src.cli points --balance 5000
  python -m src.cli live            # 需设置环境变量 MCD_MCP_TOKEN，验证真实 MCP 连接

默认 dry-run（使用 src/mock_data.py 样例数据），便于无 Token 直接体验算法。
"""
from __future__ import annotations

import argparse
import os
import sys
from . import mock_data
from .optimizer import solve_nutrition, solve_points, solve_savings


def _money(x: float) -> str:
    return f"¥{x:.2f}"


def run_save(items, coupons, wanted_codes: list):
    r = solve_savings(items, coupons, wanted_codes)
    price = r["price"]
    print("== 省钱模式 ==")
    for it in r["wanted"]:
        print(f"  - {it.name} ({it.code})")
    if r["missing_codes"]:
        print(f"  [提示] 以下 code 不在菜单中: {r['missing_codes']}")
    print(f"  小计      : {_money(price['subtotal'])}")
    print(f"  单品券省  : {_money(price['single_save'])}")
    print(f"  订单券省  : {_money(price['order_save'])}")
    print(f"  >>> 到手价: {_money(price['total'])}")
    if price["applied"]:
        print(f"  已用券    : {', '.join(price['applied'])}")


def run_nutrition(items, kcal: float, budget: float):
    print("== 营养达标模式 ==")
    combo = solve_nutrition(items, kcal, budget)
    if combo is None:
        print(f"  预算 {budget:.0f} 元内无可行组合，请提高预算或放宽目标。")
        return
    print(f"  推荐组合(共 {len(combo['items'])} 件):")
    for it in combo["items"]:
        print(f"    - {it.name}: {it.energy_kcal:.0f} kcal, 蛋白 {it.protein:.0f}g, "
              f"¥{it.price:.0f}")
    print(f"  总热量 : {combo['total_kcal']:.0f} kcal (目标 {kcal:.0f})")
    print(f"  总蛋白 : {combo['protein']:.0f} g")
    print(f"  菜单原价: {_money(combo['total_price'])}")
    print(f"  >>> 到手价(无券): {_money(combo['with_coupon_total'])}")


def run_points(products, balance: int):
    print("== 积分策略模式 ==")
    print(f"  当前积分: {balance}")
    for r in solve_points(products, balance):
        tag = "可兑" if r["affordable"] else "积分不足"
        print(f"  - {r['name']}: {r['points_cost']}分≈¥{r['cash_value']:.0f} | "
              f"每千积分价值¥{r['value_per_1000_points']:.1f} | {tag}")


def run_live():
    token = os.environ.get("MCD_MCP_TOKEN")
    if not token:
        print("[错误] 未设置环境变量 MCD_MCP_TOKEN", file=sys.stderr)
        sys.exit(2)
    from .mcp_client import McdMCP, McdMCPError

    try:
        mcp = McdMCP(token)
        mcp.initialize()
        tools = mcp.list_tools()
    except McdMCPError as e:
        print(f"[错误] 连接麦当劳 MCP 失败: {e}", file=sys.stderr)
        sys.exit(3)
    print(f"[live] 已连接麦当劳 MCP，可用工具 {len(tools)} 个:")
    for t in tools:
        desc = (t.get("description") or "")[:48].replace("\n", " ")
        print(f"  - {t.get('name')}: {desc}")
    print("[live] 完整点餐/营养/积分闭环请在 WorkBuddy 中加载本 Skill 后执行（见 SKILL.md）。")


def main():
    ap = argparse.ArgumentParser(description="麦麦精算师 — 麦当劳智能点餐优化器")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_save = sub.add_parser("save", help="省钱模式：给定想买的清单，自动选最优券")
    p_save.add_argument("--items", required=True, help="餐品 code，逗号分隔，如 mcrib,coke_m")

    p_nut = sub.add_parser("nutrition", help="营养达标：给定热量目标求最优组合")
    p_nut.add_argument("--kcal", type=float, required=True, help="目标热量(kcal)")
    p_nut.add_argument("--budget", type=float, default=50.0, help="预算上限(元)")

    p_pt = sub.add_parser("points", help="积分策略：按每千积分价值推荐兑换")
    p_pt.add_argument("--balance", type=int, required=True, help="积分余额")

    sub.add_parser("live", help="验证真实 MCP 连接（需 MCD_MCP_TOKEN）")

    args = ap.parse_args()

    if args.cmd == "save":
        codes = [c.strip() for c in args.items.split(",") if c.strip()]
        run_save(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS, codes)
    elif args.cmd == "nutrition":
        run_nutrition(mock_data.MOCK_MENU, args.kcal, args.budget)
    elif args.cmd == "points":
        run_points(mock_data.MOCK_POINTS_PRODUCTS, args.balance)
    elif args.cmd == "live":
        run_live()


if __name__ == "__main__":
    main()
