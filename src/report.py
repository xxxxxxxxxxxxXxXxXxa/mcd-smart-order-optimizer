"""麦麦精算师 — 分享报告生成（纯标准库，输出自包含 HTML + 内联 SVG 图表）。

设计目标：把优化结果变成一张「能直接晒」的卡片式报告，
不依赖任何第三方库与外链资源（图表为内联 SVG），方便分享传播。
"""
from __future__ import annotations

import html
from typing import List, Optional

_CSS = """
:root{--gold:#FFC72C;--red:#DA291C;--ink:#292929;--muted:#6b6b6b;--line:#ececec;}
*{box-sizing:border-box;}
body{margin:0;padding:24px;background:#fafafa;color:var(--ink);
     font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;}
.wrap{max-width:720px;margin:0 auto;background:#fff;border:1px solid var(--line);
      border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);}
.hero{background:var(--red);color:#fff;padding:20px 24px;}
.hero h1{margin:0;font-size:20px;letter-spacing:.5px;}
.hero p{margin:6px 0 0;font-size:13px;opacity:.9;}
.body{padding:8px 24px 24px;}
.block{padding:16px 0;border-bottom:1px dashed var(--line);}
.block:last-child{border-bottom:0;}
h2{margin:0 0 8px;font-size:15px;color:var(--ink);}
h2::before{content:"";display:inline-block;width:4px;height:14px;background:var(--gold);
           margin-right:8px;vertical-align:-2px;border-radius:2px;}
p.note{margin:6px 0;font-size:13px;color:var(--muted);line-height:1.7;}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px;}
td{padding:6px 4px;border-bottom:1px solid var(--line);}
td.k{color:var(--muted);width:42%;}
td.v{text-align:right;font-weight:600;}
.badge{display:inline-block;background:var(--gold);color:#292929;font-size:12px;
       font-weight:700;padding:3px 10px;border-radius:999px;margin-top:8px;}
.chart{margin-top:10px;}
.foot{padding:12px 24px;background:#fbfbfb;font-size:12px;color:var(--muted);}
"""

_JS_FREE_NOTE = "本页由麦麦精算师自动生成 · 数据仅供参考，以麦当劳官方渠道实时结果为准"


def esc(s) -> str:
    """HTML 转义，防止餐品名中的特殊字符破坏结构。"""
    return html.escape(str(s), quote=True)


def svg_bars(rows: List[tuple], color: str = "#FFC72C", unit: str = "",
             width: int = 640, bar_h: int = 24, gap: int = 10,
             label_w: int = 180) -> str:
    """把 [(标签, 数值)] 渲染成内联 SVG 横向条形图。"""
    if not rows:
        return ""
    rows = [(str(k), float(v)) for k, v in rows]
    maxv = max(v for _, v in rows) or 1.0
    height = len(rows) * (bar_h + gap) + 8
    track = width - label_w - 90
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="chart">'
    ]
    for i, (label, value) in enumerate(rows):
        y = i * (bar_h + gap) + 4
        w = max(3, int((value / maxv) * track))
        parts.append(
            f'<text x="0" y="{y + bar_h * 0.68}" font-size="13" fill="#292929">{esc(label)}</text>'
        )
        parts.append(
            f'<rect x="{label_w}" y="{y}" width="{w}" height="{bar_h - 6}" rx="4" fill="{color}"/>'
        )
        shown = f"{value:g}{unit}"
        parts.append(
            f'<text x="{label_w + w + 8}" y="{y + bar_h * 0.68}" font-size="12" '
            f'fill="#6b6b6b">{esc(shown)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def render_report_html(title: str, blocks: List[dict],
                       footer: Optional[str] = None) -> str:
    """渲染报告。

    blocks: [
      {"heading": "标题",
       "note": "说明文字",
       "rows": [("键", "值"), ...],
       "badge": "可选的高亮标签",
       "chart": {"rows": [("标签", 数值)], "color": "#FFC72C", "unit": "g"}}
    ]
    """
    out: List[str] = [
        "<!DOCTYPE html>", '<html lang="zh-CN">', "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>{esc(title)}</title>",
        f"<style>{_CSS}</style>", "</head>", "<body>", '<div class="wrap">',
        '<div class="hero">', f"<h1>🍔 {esc(title)}</h1>",
        "<p>麦麦精算师 · 基于麦当劳 MCP 的智能点餐优化</p>", "</div>",
        '<div class="body">',
    ]

    for b in blocks:
        out.append('<div class="block">')
        if b.get("heading"):
            out.append(f"<h2>{esc(b['heading'])}</h2>")
        if b.get("note"):
            out.append(f'<p class="note">{esc(b["note"])}</p>')
        rows = b.get("rows") or []
        if rows:
            out.append("<table>")
            for k, v in rows:
                out.append(f"<tr><td class='k'>{esc(k)}</td><td class='v'>{esc(v)}</td></tr>")
            out.append("</table>")
        if b.get("badge"):
            out.append(f'<span class="badge">{esc(b["badge"])}</span>')
        chart = b.get("chart")
        if chart and chart.get("rows"):
            out.append('<div class="chart">')
            out.append(svg_bars(chart["rows"],
                                color=chart.get("color", "#FFC72C"),
                                unit=chart.get("unit", "")))
            out.append("</div>")
        out.append("</div>")

    out.append("</div>")
    out.append(f'<div class="foot">{esc(footer or _JS_FREE_NOTE)}</div>')
    out.append("</div></body></html>")
    return "\n".join(out)


def write_report(path: str, html_text: str) -> str:
    """把 HTML 写到文件，返回路径。"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_text)
    return path
