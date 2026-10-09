"""麦麦精算师 — 命令行入口（无需 WorkBuddy 也能直接跑）。

用法：
  python -m src.cli save      --items mcrib,coke_m
  python -m src.cli nutrition --kcal 800 --budget 45 [--avoid 牛肉] [--vegetarian]
  python -m src.cli points    --balance 5000
  python -m src.cli combo     --items mcrib,fries_m,coke_m      # 套餐拆解
  python -m src.cli value     [--by protein|kcal|value]         # 性价比榜
  python -m src.cli plan      [--days 7] [--kcal 700] [--budget 40]
  python -m src.cli coupons                                      # 券包排程
  python -m src.cli report    [--out mcd_report.html]            # 生成分享报告
  python -m src.cli live                                         # 验证真实 MCP 连接

默认 dry-run（使用 src/mock_data.py 样例数据），便于无 Token 直接体验算法。
"""
from __future__ import annotations

import argparse
import os
import sys
from . import mock_data
from .optimizer import (
    plan_coupon_usage,
    plan_week,
    rank_value,
    solve_combo_deal,
    solve_nutrition,
    solve_nutrition_diet,
    solve_points,
    solve_savings,
)
from .report import render_report_html, write_report


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


def run_nutrition(items, kcal: float, budget: float, avoid=None, vegetarian=False):
    print("== 营养达标模式 ==")
    if avoid or vegetarian:
        tag = f"（忌口: {avoid or '无'}{'，素食' if vegetarian else ''}）"
        combo = solve_nutrition_diet(items, kcal, budget, avoid=avoid,
                                     vegetarian=vegetarian)
        print(f"  已按条件过滤菜单 {tag}")
    else:
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


def run_combo(items, coupons, deals, codes: list):
    print("== 套餐拆解模式 ==")
    print(f"  想买: {', '.join(codes)}")
    r = solve_combo_deal(items, coupons, codes, deals)
    for route in r["routes"]:
        mark = "  <<< 最优" if route is r["best"] else ""
        print(f"  [{route['kind']}] {route['route']}: {_money(route['total'])}{mark}")
        print(f"        {route['title']} — {route['detail']}")
    print(f"  >>> 相对「单品直购」省: {_money(r['saving_vs_base'])}")


def run_value(items, by: str, top: int):
    label = {"protein": "每元蛋白(健身党)", "kcal": "每元热量(吃饱党)",
             "value": "综合性价比"}.get(by, by)
    print(f"== 性价比排行（{label}）==")
    for i, r in enumerate(rank_value(items, by=by, top_n=top), 1):
        print(f"  {i:>2}. {r['name']:<14} ¥{r['price']:.0f} | "
              f"蛋白 {r['protein']:.0f}g ({r['protein_per_yuan']:.2f} g/元) | "
              f"热量 {r['kcal']:.0f} ({r['kcal_per_yuan']:.0f} kcal/元) | "
              f"指数 {r['value_index']:.1f}")


def run_plan(items, coupons, days: int, kcal: float, budget: float, avoid=None):
    print(f"== 多天饮食计划（{days} 天 / 目标 {kcal:.0f} kcal / 每餐预算 {budget:.0f} 元）==")
    r = plan_week(items, coupons, days=days, kcal=kcal, budget=budget, avoid=avoid)
    for d in r["days"]:
        names = " + ".join(d["names"])
        off = f"  [省{_money(d['list_price'] - d['total'])}]" if d["total"] < d["list_price"] else ""
        print(f"  第{d['day']}天: {names}")
        print(f"         {d['kcal']:.0f} kcal / 蛋白 {d['protein']:.0f}g / "
              f"{_money(d['total'])}{off}")
    print(f"  >>> 合计 {_money(r['total'])} | 日均 {r['avg_kcal']:.0f} kcal | "
          f"日均花费 {_money(r['avg_price'])}")


def run_coupons(coupons, orders):
    print("== 券包排程（哪张券用在哪个订单）==")
    r = plan_coupon_usage(coupons, orders)
    if not r["plan"]:
        print("  没有可用券 / 订单组合。")
    for p in r["plan"]:
        print(f"  第{p['day']}天 {p['order_id']}: 用「{p['coupon']}」省 {_money(p['saving'])}"
              f"（该券 {p['expire_days']} 天后过期）")
    print(f"  >>> 排程总省: {_money(r['total_saving'])}")
    if r["unused"]:
        print(f"  未用上（可能不匹配任何订单）: "
              f"{', '.join(u['title'] for u in r['unused'])}")


def run_report(items, coupons, deals, products, out: str):
    print("== 分享报告生成 ==")
    best = solve_combo_deal(items, coupons, ["mcrib", "fries_m", "coke_m"], deals)
    nutri = solve_nutrition(items, 700, 40)
    values = rank_value(items, by="protein", top_n=8)
    coupon_plan = plan_coupon_usage(coupons, mock_data.MOCK_ORDERS)
    pts = solve_points(products, 5000, top_n=5)

    blocks: list = [
        {
            "heading": "套餐怎么买最省",
            "note": "同一份清单，对比「单品直购 / 官方套餐 / 1+1随心配」三条路。",
            "rows": [(r["route"], _money(r["total"])) for r in best["routes"]],
            "badge": f"最优: {best['best']['route']} · 省 {_money(best['saving_vs_base'])}",
        },
    ]
    if nutri:
        blocks.append({
            "heading": "控卡推荐组合（700 kcal / 预算 40）",
            "note": " / ".join(it.name for it in nutri["items"]),
            "rows": [("总热量", f"{nutri['total_kcal']:.0f} kcal"),
                     ("总蛋白", f"{nutri['protein']:.0f} g"),
                     ("到手价", _money(nutri["with_coupon_total"]))],
            "chart": {"rows": [(it.name, it.energy_kcal) for it in nutri["items"]],
                      "color": "#DA291C", "unit": " kcal"},
        })
    blocks.append({
        "heading": "性价比 TOP 8（每元能买到多少蛋白）",
        "note": "同样花一块钱，谁给的蛋白最多 —— 健身党最该看这张。",
        "chart": {"rows": [(r["name"], r["protein_per_yuan"]) for r in values],
                  "color": "#FFC72C", "unit": " g/元"},
    })
    blocks.append({
        "heading": "券包排程（按到期日优先用掉）",
        "note": "快过期的券先用，避免白白浪费。",
        "rows": [(f"第{p['day']}天 {p['order_id']}", f"{p['coupon']} 省{_money(p['saving'])}")
                 for p in coupon_plan["plan"]] or [("无可用排程", "—")],
        "badge": f"排程总省 {_money(coupon_plan['total_saving'])}",
    })
    blocks.append({
        "heading": "积分兑换优先级（每千积分价值）",
        "rows": [(r["name"], f"{r['points_cost']}分 ≈ ¥{r['cash_value']:.0f} · "
                             f"¥{r['value_per_1000_points']:.1f}/千分")
                 for r in pts],
        "chart": {"rows": [(r["name"], r["value_per_1000_points"]) for r in pts],
                  "color": "#FFC72C", "unit": " 元/千分"},
    })

    path = write_report(out, render_report_html("麦麦精算师 · 点餐优化报告", blocks))
    print(f"  >>> 已生成: {os.path.abspath(path)}")
    print("      （单文件 HTML，双击即可打开，可直接分享）")


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
    p_nut.add_argument("--avoid", default="", help="忌口/过敏原，逗号分隔，如 牛肉,乳制品")
    p_nut.add_argument("--vegetarian", action="store_true", help="只要素食")

    p_pt = sub.add_parser("points", help="积分策略：按每千积分价值推荐兑换")
    p_pt.add_argument("--balance", type=int, required=True, help="积分余额")

    p_cb = sub.add_parser("combo", help="套餐拆解：对比单品直购/官方套餐/1+1随心配")
    p_cb.add_argument("--items", required=True, help="餐品 code，逗号分隔")

    p_v = sub.add_parser("value", help="性价比排行：每元蛋白/每元热量")
    p_v.add_argument("--by", default="protein", choices=["protein", "kcal", "value"])
    p_v.add_argument("--top", type=int, default=8)

    p_pl = sub.add_parser("plan", help="多天饮食计划：控热量与预算、尽量不重样")
    p_pl.add_argument("--days", type=int, default=7)
    p_pl.add_argument("--kcal", type=float, default=700.0)
    p_pl.add_argument("--budget", type=float, default=40.0)
    p_pl.add_argument("--avoid", default="")

    sub.add_parser("coupons", help="券包排程：多张带到期日的券怎么用在各订单")

    p_rp = sub.add_parser("report", help="生成可分享的 HTML 报告（内联图表）")
    p_rp.add_argument("--out", default="mcd_report.html")

    sub.add_parser("live", help="验证真实 MCP 连接（需 MCD_MCP_TOKEN）")

    args = ap.parse_args()

    if args.cmd == "save":
        codes = [c.strip() for c in args.items.split(",") if c.strip()]
        run_save(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS, codes)
    elif args.cmd == "nutrition":
        avoid = [a.strip() for a in args.avoid.split(",") if a.strip()]
        run_nutrition(mock_data.MOCK_MENU, args.kcal, args.budget,
                      avoid=avoid, vegetarian=args.vegetarian)
    elif args.cmd == "points":
        run_points(mock_data.MOCK_POINTS_PRODUCTS, args.balance)
    elif args.cmd == "combo":
        codes = [c.strip() for c in args.items.split(",") if c.strip()]
        run_combo(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS,
                  mock_data.MOCK_DEALS, codes)
    elif args.cmd == "value":
        run_value(mock_data.MOCK_MENU, args.by, args.top)
    elif args.cmd == "plan":
        avoid = [a.strip() for a in args.avoid.split(",") if a.strip()]
        run_plan(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS,
                 args.days, args.kcal, args.budget, avoid=avoid)
    elif args.cmd == "coupons":
        run_coupons(mock_data.MOCK_COUPONS, mock_data.MOCK_ORDERS)
    elif args.cmd == "report":
        run_report(mock_data.MOCK_MENU, mock_data.MOCK_COUPONS,
                   mock_data.MOCK_DEALS, mock_data.MOCK_POINTS_PRODUCTS, args.out)
    elif args.cmd == "live":
        run_live()


if __name__ == "__main__":
    main()
