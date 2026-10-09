"""麦麦精算师 — 多目标点餐优化引擎（纯算法，无第三方依赖，可单测）。

设计目标：把麦当劳 MCP 返回的「菜单 / 营养 / 优惠券 / 积分商城」数据，
转化为一个可解释的「最优决策」，而不是简单地把工具结果堆给用户。

三种决策模式：
  - save     省钱：给定想买的清单，自动选券，算到手价
  - nutrition 营养达标：给定热量(蛋白)目标与预算，求最优组合
  - points   积分策略：给定积分余额，按「每千积分价值」排序推荐兑换

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
