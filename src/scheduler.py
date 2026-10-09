"""麦麦精算师 — 预订单 / 定时点单（本地存储 + 到期判定 + 安全闸门）。

设计红线：**默认绝不自动扣款 / 自动下单**。

预订单到点后只做三件事：
  1. 重新拉实时菜单核价（价格、券、在售状态都会变，不能沿用建单时的旧价）；
  2. 跑安全闸门 —— 餐品是否还在售、到手价是否超出预算上限；
  3. 生成一张「待确认订单卡片」。

只有用户**明确确认**（或显式开启 `auto_confirm` 并再次确认）才会调用 `create-order`。
真正的下单动作发生在 WorkBuddy 内（走 MCP），CLI 只负责管理与模拟，永不直接下单。
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List, Optional

from .optimizer import apply_coupons

DEFAULT_STORE = os.path.join(os.path.expanduser("~"), ".mcd_scheduled_orders.json")
GRACE_MINUTES = 5          # 到点后的宽限窗口（分钟），避免调度器晚跑几分钟就漏单


@dataclass
class ScheduledOrder:
    """一条预订单。"""
    order_id: str
    name: str
    item_codes: List[str]
    hour: int = 12
    minute: int = 0
    days: List[int] = field(default_factory=list)   # 0=周一 … 6=周日；空 = 每天
    store: str = ""                                  # 门店名/ID，空 = 默认门店
    budget_cap: float = 0.0                          # 预算上限(元)，0 = 不限制
    auto_confirm: bool = False                       # ⚠️ 建议保持 False
    enabled: bool = True
    note: str = ""
    last_run: str = ""

    def time_str(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    def days_str(self) -> str:
        if not self.days:
            return "每天"
        names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return "、".join(names[d] for d in sorted(self.days) if 0 <= d <= 6)


def make_order_id(name: str, hour: int, minute: int) -> str:
    """由名称+时间生成稳定 id（不用内置 hash，避免跨进程不稳定）。"""
    raw = f"{name}|{hour:02d}:{minute:02d}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()[:8]


def load_orders(path: str = DEFAULT_STORE) -> List[ScheduledOrder]:
    """从本地 JSON 读取预订单；文件不存在则返回空列表。"""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    if isinstance(data, dict):
        data = data.get("orders", [])
    fields = set(ScheduledOrder.__dataclass_fields__)
    out: List[ScheduledOrder] = []
    for d in data or []:
        try:
            out.append(ScheduledOrder(**{k: v for k, v in d.items() if k in fields}))
        except TypeError:
            continue
    return out


def save_orders(orders: List[ScheduledOrder], path: str = DEFAULT_STORE) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(o) for o in orders], f, ensure_ascii=False, indent=2)
    return path


def add_order(order: ScheduledOrder, path: str = DEFAULT_STORE) -> List[ScheduledOrder]:
    """新增（同 id 覆盖）。"""
    orders = [o for o in load_orders(path) if o.order_id != order.order_id]
    orders.append(order)
    orders.sort(key=lambda o: (o.hour, o.minute))
    save_orders(orders, path)
    return orders


def remove_order(order_id: str, path: str = DEFAULT_STORE) -> bool:
    orders = load_orders(path)
    left = [o for o in orders if o.order_id != order_id]
    if len(left) == len(orders):
        return False
    save_orders(left, path)
    return True


def is_due(order: ScheduledOrder, now: Optional[datetime] = None,
           grace_minutes: int = GRACE_MINUTES) -> bool:
    """判断预订单当前是否「到点」。

    条件：已启用 + 今天是指定星期（days 为空则每天）+ 当前时刻落在
    [预定时刻, 预定时刻 + grace_minutes] 窗口内。
    """
    now = now or datetime.now()
    if not order.enabled:
        return False
    if order.days and now.weekday() not in order.days:
        return False
    sched = order.hour * 60 + order.minute
    current = now.hour * 60 + now.minute
    return 0 <= (current - sched) <= grace_minutes


def due_orders(orders: List[ScheduledOrder], now: Optional[datetime] = None,
               grace_minutes: int = GRACE_MINUTES) -> List[ScheduledOrder]:
    return [o for o in orders if is_due(o, now=now, grace_minutes=grace_minutes)]


def evaluate_order(order: ScheduledOrder, menu, coupons,
                   now: Optional[datetime] = None) -> dict:
    """安全闸门：把一条预订单换算成「能不能下单」的结论 + 理由。

    注意：这里**始终**用传入的实时 menu/coupons 重新核价，
    绝不沿用建单时算出的旧价格（价格与在售状态随时会变）。
    """
    by_code = {it.code: it for it in menu}
    found, missing = [], []
    for code in order.item_codes:
        (found.append(by_code[code]) if code in by_code else missing.append(code))

    price = apply_coupons(found, coupons)
    reasons: List[str] = []
    if missing:
        reasons.append(f"以下餐品不在菜单/可能售罄: {', '.join(missing)}")
    if not found:
        reasons.append("没有任何可下单的餐品")
    if order.budget_cap > 0 and price["total"] > order.budget_cap:
        reasons.append(
            f"到手价 ¥{price['total']:.2f} 超出预算上限 ¥{order.budget_cap:.2f}")

    return {
        "order": order,
        "time": order.time_str(),
        "items": found,
        "missing_codes": missing,
        "subtotal": price["subtotal"],
        "total": price["total"],
        "applied": price["applied"],
        "ready": not reasons,
        "reasons": reasons,
        # 恒定 True：任何预订单都必须人工确认后才允许 create-order
        "needs_confirm": True,
        "auto_confirm": order.auto_confirm,
        "checked_at": (now or datetime.now()).strftime("%Y-%m-%d %H:%M"),
    }


def format_card(result: dict) -> str:
    """把评估结果渲染成一张「待确认订单卡片」（纯文本）。"""
    o: ScheduledOrder = result["order"]
    lines = [
        f"  ┌ 预订单: {o.name}  ({o.order_id})",
        f"  │ 时间: {o.days_str()} {o.time_str()}"
        + (f" | 门店: {o.store}" if o.store else "")
        + (f" | 预算上限: ¥{o.budget_cap:.0f}" if o.budget_cap > 0 else ""),
        f"  │ 餐品: {', '.join(it.name for it in result['items']) or '（无）'}",
        f"  │ 到手价: ¥{result['total']:.2f}"
        + (f"  (已用券: {', '.join(result['applied'])})" if result["applied"] else ""),
    ]
    if result["ready"]:
        lines.append("  └ 状态: ✅ 可下单 —— 待你确认后才会调用 create-order")
    else:
        lines.append("  └ 状态: ⛔ 已拦截，不会下单")
        for r in result["reasons"]:
            lines.append(f"       - {r}")
    return "\n".join(lines)
