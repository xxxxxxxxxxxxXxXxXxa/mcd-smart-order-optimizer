"""麦麦精算师 — 多目标点餐优化引擎（纯算法，无第三方依赖，可单测）。

设计目标：把麦当劳 MCP 返回的「菜单 / 营养 / 优惠券 / 积分商城」数据，
转化为一个可解释的「最优决策」，而不是简单地把工具结果堆给用户。

三种决策模式：
  - save     省钱：给定想买的清单，自动选券，算到手价
  - nutrition 营养达标：给定热量(蛋白)目标与预算，求最优组合
  - points   积分策略：给定积分余额，按「每千积分价值」排序推荐兑换

进阶能力（v2 新增）：
  - combo    套餐拆解：对比「单品直购 / 官方套餐 / 1+1随心配」，选最省的那条路
  - value    性价比榜：按「每元蛋白 / 每元热量 / 综合性价比」给餐品排名
  - diet     忌口过滤：素食 / 过敏原 / 限钠，过滤后再优化
  - coupons  券包排程：带到期日的多张券，算「哪张用在哪个订单」最省、不浪费
  - plan     多天计划：一周饮食规划，控热量与预算、尽量不重样
  - report   分享报告：生成自包含 HTML（内联 SVG 图表），可直接晒

所有函数均为纯函数，便于单元测试与在 WorkBuddy 内被 SKILL.md 调用。
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MenuItem:
    code: str
    name: str
    price: float
    energy_kcal: float
    protein: float = 0.0
    fat: float = 0.0
    carb: float = 0.0
    sodium: float = 0.0
    category: str = "其他"            # 主食 / 套餐 / 小食 / 饮料 / 甜品
    tags: List[str] = field(default_factory=list)
    allergens: List[str] = field(default_factory=list)   # 过敏原 / 忌口标签
    vegetarian: bool = False                             # 是否为素食

    @property
    def group(self) -> str:
        """用于组合枚举的分组，保证一份搭配里同类不重复。"""
        if self.category in ("主食", "套餐"):
            return "main"
        if self.category == "小食":
            return "side"
        if self.category == "饮料":
            return "drink"
        if self.category == "甜品":
            return "dessert"
        return "other"


@dataclass
class Coupon:
    coupon_id: str
    title: str
    kind: str                       # single 单品特价 | fullreduce 满减 | percent 折扣
    threshold: float = 0.0         # 满减/折扣的生效门槛
    value: float = 0.0             # single: 特价金额; fullreduce: 减额; percent: 折扣率(0.85=85折)
    applies_to: List[str] = field(default_factory=list)   # 空=全部(单品券必须指定)
    stackable: bool = True         # 与单品券是否可叠加
    expire_days: int = 999         # 剩余有效天数（券包排程用）


@dataclass
class PointsProduct:
    sku: str
    name: str
    points_cost: int
    cash_value: float             # 估算市场价值(元)
    kind: str = "coupon"          # coupon 餐券 | physical 实物


def round2(x: float) -> float:
    return round(x + 1e-9, 2)


def apply_coupons(items: List[MenuItem], coupons: List[Coupon]) -> dict:
    """给定已选清单，求「最优用券」后的到手价。

    策略（贴合麦当劳实际规则）：
      1) 每个单品取其「菜单价」与「最优适用单品券特价」的较小值 → 小计；
      2) 在单品券后的价格基础上，再叠加一张最优的「满减/折扣」订单券（满足门槛时）。
    返回包含小计、单品省、订单省、到手价、已用券标题。
    """
    if not items:
        return {"subtotal": 0.0, "single_save": 0.0, "order_save": 0.0,
                "total": 0.0, "applied": []}

    subtotal = 0.0
    single_save = 0.0
    applied: List[str] = []

    for it in items:
        best_price = it.price
        best_c: Optional[Coupon] = None
        for c in coupons:
            if c.kind != "single":
                continue
            if not c.applies_to:           # 单品券必须指定适用范围
                continue
            if it.code not in c.applies_to:
                continue
            if c.value < best_price:
                best_price = c.value
                best_c = c
        subtotal += best_price
        if best_c is not None:
            single_save += round2(it.price - best_price)
            applied.append(best_c.title)

    # 订单券：满减/折扣，仅叠加一张（符合多数「不可多张满减叠加」的实际规则）
    best_order_save = 0.0
    best_order_title: Optional[str] = None
    for c in coupons:
        if c.kind not in ("fullreduce", "percent"):
            continue
        if subtotal < c.threshold:
            continue
        if c.kind == "fullreduce":
            save = c.value
        else:  # percent
            save = round2(subtotal * (1 - c.value))
        if save > best_order_save:
            best_order_save = save
            best_order_title = c.title
    if best_order_title:
        applied.append(best_order_title)

    total = round2(subtotal - best_order_save)
    return {
        "subtotal": round2(subtotal),
        "single_save": round2(single_save),
        "order_save": round2(best_order_save),
        "total": total,
        "applied": applied,
    }


def find_best_combo(items: List[MenuItem], target_kcal: float, budget: float,
                    tol: float = 120.0, max_items: int = 3) -> Optional[dict]:
    """在预算内寻找总热量最接近 target_kcal 的组合，兼顾蛋白与省钱。

    score = 蛋白总量 + alpha * 热量贴合奖励 - 价格惩罚
    热量贴合奖励 = (tol - |kcal-target|)/tol * 50，落在容忍带内为满分。
    组合约束：每类(group)至多选 1 个，总件数 <= max_items（符合真实点餐）。
    返回最优组合 dict；若预算内无任何可行组合返回 None。
    """
    groups = {"main": [], "side": [], "drink": [], "dessert": [], "other": []}
    for it in items:
        groups[it.group].append(it)

    pool: List[MenuItem] = [it for lst in groups.values() for it in lst]
    best: Optional[dict] = None

    for r in range(1, max_items + 1):
        for combo in itertools.combinations(pool, r):
            if len({c.group for c in combo}) < len(combo):
                continue  # 同类重复，跳过
            kcal = sum(c.energy_kcal for c in combo)
            price = sum(c.price for c in combo)
            if price > budget:
                continue
            protein = sum(c.protein for c in combo)
            # 打分：热量贴合为第一优先级（连续惩罚），其次蛋白，最后价格。
            # 热量每偏离 5 kcal 扣 1 分，使最优组合尽量贴近目标而非单纯堆蛋白。
            score = protein * 0.3 - abs(kcal - target_kcal) / 5.0 - 0.1 * price
            cand = {
                "items": list(combo),
                "total_kcal": round2(kcal),
                "total_price": round2(price),
                "protein": round2(protein),
                "score": round2(score),
            }
            if best is None or cand["score"] > best["score"]:
                best = cand
    return best


def rank_points_redeem(products: List[PointsProduct], balance: int,
                       top_n: int = 5) -> List[dict]:
    """给定积分余额，按「每千积分价值」从高到低推荐可兑换项。"""
    result: List[dict] = []
    for p in products:
        if p.points_cost <= 0:
            continue
        vpp = round2(p.cash_value / p.points_cost * 1000.0)
        result.append({
            "sku": p.sku,
            "name": p.name,
            "points_cost": p.points_cost,
            "cash_value": p.cash_value,
            "kind": p.kind,
            "value_per_1000_points": vpp,
            "affordable": p.points_cost <= balance,
        })
    result.sort(key=lambda x: (-x["value_per_1000_points"], -x["affordable"]))
    return result[:top_n]


def solve_savings(items: List[MenuItem], coupons: List[Coupon],
                  wanted_codes: List[str]) -> dict:
    """省钱模式入口：把用户想买的 code 列表转成 MenuItem，求最优到手价。"""
    wanted = [it for it in items if it.code in wanted_codes]
    missing = [c for c in wanted_codes if c not in {it.code for it in items}]
    price = apply_coupons(wanted, coupons)
    return {"wanted": wanted, "missing_codes": missing, "price": price}


def solve_nutrition(items: List[MenuItem], target_kcal: float, budget: float,
                    tol: float = 120.0) -> Optional[dict]:
    """营养模式入口：求最优组合后再叠加最优券给出到手价。"""
    combo = find_best_combo(items, target_kcal, budget, tol=tol)
    if combo is None:
        return None
    coupon = apply_coupons(combo["items"], [])
    combo["with_coupon_total"] = coupon["total"]
    return combo


def solve_points(products: List[PointsProduct], balance: int,
                 top_n: int = 5) -> List[dict]:
    """积分模式入口。"""
    return rank_points_redeem(products, balance, top_n=top_n)


# ---------------------------------------------------------------------------
# v2 进阶能力
# ---------------------------------------------------------------------------


@dataclass
class ComboDeal:
    """优惠组合：官方套餐(set) 或 1+1随心配(pick2)。"""
    deal_id: str
    title: str
    kind: str                       # set 官方套餐 | pick2 1+1随心配
    price: float
    includes: List[str] = field(default_factory=list)    # set: 套餐包含的单品 code
    candidates: List[str] = field(default_factory=list)  # pick2: 可选范围内的单品 code


def filter_menu(items: List[MenuItem], avoid: Optional[List[str]] = None,
                vegetarian: bool = False,
                max_sodium: Optional[float] = None) -> List[MenuItem]:
    """忌口 / 过敏原 / 素食 / 限钠 过滤。

    avoid 可填过敏原（花生、海鲜…）、标签或品类（饮料、甜品…），命中即剔除。
    """
    avoid = [a for a in (avoid or []) if a]
    out: List[MenuItem] = []
    for it in items:
        if vegetarian and not it.vegetarian:
            continue
        haystack = set(it.allergens) | set(it.tags) | {it.category}
        if any(a in haystack for a in avoid):
            continue
        if max_sodium is not None and it.sodium > max_sodium:
            continue
        out.append(it)
    return out


def rank_value(items: List[MenuItem], by: str = "protein",
               top_n: int = 8) -> List[dict]:
    """性价比排行：量化「花同样的钱能买到多少蛋白 / 多少热量」。

    - 每元蛋白 protein_per_yuan = 蛋白(g) / 价格(元)   —— 健身党最关心
    - 每元热量 kcal_per_yuan    = 热量(kcal) / 价格(元) —— 吃饱党最关心
    - 综合性价比 value_index    = 蛋白效率×2 + 热量效率/50
    by: protein | kcal | value
    """
    rows: List[dict] = []
    for it in items:
        if it.price <= 0:
            continue
        kcal_per = round2(it.energy_kcal / it.price)
        pro_per = round2(it.protein / it.price)
        rows.append({
            "code": it.code,
            "name": it.name,
            "price": round2(it.price),
            "kcal": round2(it.energy_kcal),
            "protein": round2(it.protein),
            "kcal_per_yuan": kcal_per,
            "protein_per_yuan": pro_per,
            "value_index": round2(pro_per * 2.0 + kcal_per / 50.0),
        })
    key = {"protein": "protein_per_yuan",
           "kcal": "kcal_per_yuan",
           "value": "value_index"}.get(by, "protein_per_yuan")
    rows.sort(key=lambda r: -r[key])
    return rows[:top_n]


def solve_combo_deal(items: List[MenuItem], coupons: List[Coupon],
                     wanted_codes: List[str],
                     deals: List[ComboDeal]) -> dict:
    """套餐拆解：同一份清单，对比「单品直购 / 官方套餐 / 1+1随心配」哪条最省。

    - 单品直购：逐件买单，自动叠加最优券
    - 官方套餐(set)：套餐固定价覆盖其中若干件，其余单品继续用券
    - 1+1随心配(pick2)：固定价任选 2 件，取清单内「最贵的 2 件」替换最划算
    返回全部路线 + 最优路线 + 相对单品直购省了多少。
    """
    wanted = [it for it in items if it.code in wanted_codes]
    base = apply_coupons(wanted, coupons)
    price_of = {it.code: it.price for it in items}

    routes: List[dict] = [{
        "route": "单品直购",
        "title": "逐件买单 + 自动用券",
        "total": base["total"],
        "detail": ("已用券: " + ", ".join(base["applied"])) if base["applied"] else "无可用券",
        "kind": "base",
    }]

    for d in deals:
        if d.kind == "set":
            cover = [c for c in d.includes if c in wanted_codes]
            if not cover:
                continue
            rest = [c for c in wanted_codes if c not in d.includes]
            rp = apply_coupons([it for it in items if it.code in rest], coupons)
            routes.append({
                "route": d.title,
                "title": f"官方套餐 ¥{d.price:.0f} 覆盖 {len(cover)} 件",
                "total": round2(d.price + rp["total"]),
                "detail": "套餐为固定价，其余单品仍可继续用券",
                "kind": "set",
            })
        elif d.kind == "pick2":
            elig = [c for c in wanted_codes if c in d.candidates]
            if len(elig) < 2:
                continue
            top2 = sorted(elig, key=lambda c: -price_of[c])[:2]
            rest = [c for c in wanted_codes if c not in top2]
            rp = apply_coupons([it for it in items if it.code in rest], coupons)
            routes.append({
                "route": d.title,
                "title": f"固定价任选 2 件（{' + '.join(top2)}）",
                "total": round2(d.price + rp["total"]),
                "detail": "固定价，拿清单里最贵的 2 件最划算",
                "kind": "pick2",
            })

    best = min(routes, key=lambda r: r["total"])
    return {
        "wanted": wanted,
        "base_total": base["total"],
        "routes": routes,
        "best": best,
        "saving_vs_base": round2(base["total"] - best["total"]),
    }


def plan_coupon_usage(coupons: List[Coupon], orders: List[dict]) -> dict:
    """券包排程：多张带到期日的券 + 多笔计划订单，算「哪张券用在哪个订单」最省。

    orders: [{"order_id": str, "day": int(第几天), "items": [MenuItem]}]
    策略（贪心，可解释）：
      1) 券按「到期日升序、面额降序」处理 —— 快过期的先用掉，避免浪费；
      2) 每张券分配给「能带来最大省钱额」且「尚未占用、且下单日不晚于到期日」的订单；
      3) 简化约束：一个订单只用一张券（贴合多数「不可叠加多张」规则）。
    """
    remaining = sorted(coupons, key=lambda c: (c.expire_days, -c.value))
    used: dict = {}
    plan: List[dict] = []

    for c in remaining:
        best = None
        for o in orders:
            if used.get(o["order_id"]):
                continue
            if c.expire_days < o.get("day", 0):
                continue  # 这张券在该订单下单日之前就过期了
            before = apply_coupons(o["items"], [])["total"]
            after = apply_coupons(o["items"], [c])["total"]
            save = round2(before - after)
            if save > 0 and (best is None or save > best[1]):
                best = (o, save)
        if best:
            o, save = best
            used[o["order_id"]] = c.title
            plan.append({
                "order_id": o["order_id"],
                "day": o.get("day", 0),
                "coupon": c.title,
                "saving": save,
                "expire_days": c.expire_days,
            })

    used_ids = {c.coupon_id for c in coupons
                for p in plan if p["coupon"] == c.title}
    unused = [{"title": c.title, "expire_days": c.expire_days}
              for c in remaining if c.coupon_id not in used_ids]
    return {
        "plan": plan,
        "total_saving": round2(sum(p["saving"] for p in plan)),
        "unused": unused,
    }


def plan_week(items: List[MenuItem], coupons: List[Coupon], days: int = 7,
              kcal: float = 700.0, budget: float = 40.0,
              avoid: Optional[List[str]] = None,
              vegetarian: bool = False) -> dict:
    """多天饮食计划：连续 N 天，每天在预算内凑到目标热量，且尽量不重样。

    做法：逐天求解最优组合（find_best_combo），并把已用过的餐品记为「已用过」，
    下一天优先从「没用过」的池子里选 —— 实现「不重样」的朴素去重用。
    """
    pool = filter_menu(items, avoid=avoid, vegetarian=vegetarian) \
        if (avoid or vegetarian) else list(items)
    used_codes: set = set()
    out: List[dict] = []

    for d in range(days):
        fresh = [it for it in pool if it.code not in used_codes]
        combo = find_best_combo(fresh, kcal, budget) if fresh else None
        if combo is None:  # 新鲜池子凑不出（预算/品类限制），退回全池
            combo = find_best_combo(pool, kcal, budget)
        if combo is None:
            break
        for it in combo["items"]:
            used_codes.add(it.code)
        price = apply_coupons(combo["items"], coupons)
        out.append({
            "day": d + 1,
            "names": [it.name for it in combo["items"]],
            "items": combo["items"],
            "kcal": combo["total_kcal"],
            "protein": combo["protein"],
            "list_price": combo["total_price"],
            "total": price["total"],
            "applied": price["applied"],
        })

    return {
        "days": out,
        "total": round2(sum(o["total"] for o in out)),
        "avg_kcal": round2(sum(o["kcal"] for o in out) / len(out)) if out else 0.0,
        "avg_price": round2(sum(o["total"] for o in out) / len(out)) if out else 0.0,
    }


def solve_nutrition_diet(items: List[MenuItem], target_kcal: float, budget: float,
                         avoid: Optional[List[str]] = None,
                         vegetarian: bool = False,
                         max_sodium: Optional[float] = None) -> Optional[dict]:
    """忌口版营养模式：先按忌口/素食/限钠过滤，再求最优组合。"""
    pool = filter_menu(items, avoid=avoid, vegetarian=vegetarian,
                       max_sodium=max_sodium)
    combo = find_best_combo(pool, target_kcal, budget)
    if combo is None:
        return None
    combo["pool_size"] = len(pool)
    combo["with_coupon_total"] = apply_coupons(combo["items"], [])["total"]
    return combo
