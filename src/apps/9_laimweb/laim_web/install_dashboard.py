"""Dashboard de Registro para laimweb.

Port de ``installmetrics.BuildDashboard`` (laim_maintenance). Reflex solo
pinta los SVG; la aritmética vive aquí. El serial de la tabla sale enmascarado.
"""

from __future__ import annotations

import html
import math
from typing import Any

from laim_web.display_format import edition_label, format_display_datetime

HERO_TEAL = "#0f766e"
HERO_CYAN = "#0e7490"
HERO_ORANGE = "#ea580c"
HERO_GOLD = "#d97706"
INK = "#111827"
MUTED = "#1f2937"
GRID = "#d1d5db"
CARD_FACE = "#ffffff"

OS_SERIES = (
    {"name": "Windows", "color": "#2563eb"},
    {"name": "macOS", "color": "#d97706"},
    {"name": "Linux", "color": "#059669"},
    {"name": "Total", "color": "#7c3aed"},
)


def _round(value: float) -> int:
    if value >= 0:
        return int(math.floor(value + 0.5))
    return int(math.ceil(value - 0.5))


def mask_serial(serial: str) -> str:
    """Oculta los grupos centrales. El último grupo queda para cotejar un ticket."""
    keep = [part for part in str(serial or "").split("-") if part]
    if len(keep) < 2:
        return "••••"
    middle = ["••••"] * (len(keep) - 2)
    return "-".join([keep[0], *middle, keep[-1]])


def _month_delta(vals: list[float]) -> str:
    if not vals:
        return "▬ 0"
    if len(vals) == 1:
        n = _round(vals[0])
        if n > 0:
            return f"▲ {n}"
        return "▬ 0"
    delta = _round(vals[-1] - vals[-2])
    if delta > 0:
        return f"▲ {delta}"
    if delta < 0:
        return f"▼ {-delta}"
    return "▬ 0"


def _spark_svg(vals: list[float], color: str) -> str:
    if not vals:
        return ""
    width, height = 160.0, 22.0
    max_v = max(1.0, max(vals))

    def point(index: int, value: float) -> tuple[float, float]:
        x = 2.0
        if len(vals) > 1:
            x = 2 + (width - 4) * index / (len(vals) - 1)
        y = height - 3 - (height - 6) * (value / max_v)
        return x, y

    line: list[str] = []
    area = [f"{point(0, vals[0])[0]:.1f},{height - 1:.1f}"]
    for index, value in enumerate(vals):
        x, y = point(index, value)
        line.append(f"{x:.1f},{y:.1f}")
        area.append(f"{x:.1f},{y:.1f}")
    end_x, _ = point(len(vals) - 1, vals[-1])
    area.append(f"{end_x:.1f},{height - 1:.1f}")
    fill = color + "55" if len(color) == 7 else color
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'width="100%" height="22" aria-hidden="true">'
        f'<polygon fill="{fill}" points="{" ".join(area)}"/>'
        f'<polyline fill="none" stroke="{color}" stroke-width="2.2" '
        f'stroke-linejoin="round" points="{" ".join(line)}"/></svg>'
    )


def _gauge_svg(pct: float, color: str) -> str:
    pct = min(100.0, max(0.0, pct))
    cx, cy, radius = 70.0, 52.0, 36.0
    start = 150.0 * math.pi / 180.0
    sweep = 240.0 * math.pi / 180.0

    def arc(portion: float) -> tuple[float, float, float, float, int]:
        a0 = start
        a1 = start + sweep * portion / 100
        large = 1 if sweep * portion / 100 > math.pi else 0
        return (
            cx + radius * math.cos(a0),
            cy + radius * math.sin(a0),
            cx + radius * math.cos(a1),
            cy + radius * math.sin(a1),
            large,
        )

    bx1, by1, bx2, by2, large_bg = arc(100)
    fx1, fy1, fx2, fy2, large_fg = arc(pct)
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 72" width="100%" '
            f'height="64" role="img" aria-label="Cuota {pct:.0f} por ciento">'
        ),
        (
            f'<path d="M {bx1:.1f} {by1:.1f} A {radius:.1f} {radius:.1f} 0 {large_bg} 1 '
            f'{bx2:.1f} {by2:.1f}" fill="none" stroke="#f3f4f6" stroke-width="10" '
            f'stroke-linecap="round"/>'
        ),
    ]
    if pct > 0.5:
        parts.append(
            f'<path d="M {fx1:.1f} {fy1:.1f} A {radius:.1f} {radius:.1f} 0 {large_fg} 1 '
            f'{fx2:.1f} {fy2:.1f}" fill="none" stroke="{color}" stroke-width="10" '
            f'stroke-linecap="round"/>'
        )
    parts.append(
        f'<text x="70" y="56" text-anchor="middle" font-size="20" font-weight="700" '
        f'fill="#ffffff">{pct:.0f}</text></svg>'
    )
    return "".join(parts)


def _donut_slice(cx, cy, outer, inner, a0, a1, color, name, count) -> str:
    large = 1 if a1 - a0 > math.pi else 0
    ox0, oy0 = cx + outer * math.cos(a0), cy + outer * math.sin(a0)
    ox1, oy1 = cx + outer * math.cos(a1), cy + outer * math.sin(a1)
    ix0, iy0 = cx + inner * math.cos(a0), cy + inner * math.sin(a0)
    ix1, iy1 = cx + inner * math.cos(a1), cy + inner * math.sin(a1)
    label = html.escape(name)
    return (
        f'<path d="M {ox0:.2f} {oy0:.2f} A {outer:.1f} {outer:.1f} 0 {large} 1 '
        f'{ox1:.2f} {oy1:.2f} L {ix1:.2f} {iy1:.2f} A {inner:.1f} {inner:.1f} 0 '
        f'{large} 0 {ix0:.2f} {iy0:.2f} Z" fill="{color}">'
        f"<title>{label} · {count}</title></path>"
    )


def _donut_svg(windows: int, mac: int, linux: int) -> str:
    parts = (
        ("Windows", windows, OS_SERIES[0]["color"]),
        ("macOS", mac, OS_SERIES[1]["color"]),
        ("Linux", linux, OS_SERIES[2]["color"]),
    )
    total = windows + mac + linux
    if total == 0:
        return ""
    cx, cy, outer, inner = 70.0, 62.0, 50.0, 30.0
    angle = -math.pi / 2
    slices = []
    for name, count, color in parts:
        if count <= 0:
            continue
        sweep = 2 * math.pi * count / total
        slices.append((name, count, color, angle, angle + sweep))
        angle += sweep
    chunks = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 124" width="100%" '
        'height="124" role="img" aria-label="Mix de sistemas">'
    ]
    if len(slices) == 1:
        color = slices[0][2]
        chunks.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{outer:.1f}" fill="{color}"/>')
        chunks.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{inner:.1f}" fill="{CARD_FACE}"/>')
    else:
        for name, count, color, start, end in slices:
            chunks.append(_donut_slice(cx, cy, outer, inner, start, end, color, name, count))
    chunks.append(
        f'<text x="{cx:.1f}" y="60" text-anchor="middle" font-size="16" font-weight="700" '
        f'fill="{INK}">{total}</text>'
    )
    chunks.append(
        f'<text x="{cx:.1f}" y="76" text-anchor="middle" font-size="12" fill="{MUTED}">total</text>'
    )
    legend_y = 18.0
    for name, count, color in parts:
        pct = _round(100 * count / total) if total else 0
        chunks.append(
            f'<rect x="150" y="{legend_y:.1f}" width="10" height="10" rx="2" fill="{color}"/>'
        )
        chunks.append(
            f'<text x="166" y="{legend_y + 10:.1f}" font-size="13" fill="{INK}">'
            f"{html.escape(name)} {pct}%</text>"
        )
        legend_y += 20
    chunks.append("</svg>")
    return "".join(chunks)


def _scatter_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    width, height = 360.0, 124.0
    left, right, top, bottom = 36.0, 12.0, 14.0, 26.0
    max_y = 1.0
    for row in rows:
        max_y = max(max_y, float(row["windows"]), float(row["mac"]), float(row["linux"]))
    plot_w, plot_h = width - left - right, height - top - bottom
    count = len(rows)

    def x_at(index: int, series: int) -> float:
        base = left + plot_w / 2
        if count > 1:
            base = left + plot_w * index / (count - 1)
        return base + (series - 1) * 7

    def y_at(value: float) -> float:
        return top + plot_h * (1 - value / max_y)

    chunks = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 124" width="100%" '
        'height="124" role="img" aria-label="Actividad mensual por plataforma">'
    ]
    for grid in (0.0, 0.5, 1.0):
        y = y_at(grid * max_y)
        chunks.append(
            f'<line x1="{left:.1f}" x2="{left + plot_w:.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>'
        )
        chunks.append(
            f'<text x="{left - 4:.1f}" y="{y + 3:.1f}" font-size="12" fill="{MUTED}" '
            f'text-anchor="end">{grid * max_y:.0f}</text>'
        )
    chunks.append(
        f'<text x="{left:.1f}" y="{height - 6:.1f}" font-size="12" fill="{MUTED}">'
        f"{html.escape(_short_month(rows[0]['month']))}</text>"
    )
    chunks.append(
        f'<text x="{left + plot_w:.1f}" y="{height - 6:.1f}" font-size="12" fill="{MUTED}" '
        f'text-anchor="end">{html.escape(_short_month(rows[-1]["month"]))}</text>'
    )
    series = (
        ("windows", OS_SERIES[0]["color"], "Windows"),
        ("mac", OS_SERIES[1]["color"], "macOS"),
        ("linux", OS_SERIES[2]["color"], "Linux"),
    )
    for index, row in enumerate(rows):
        for series_index, (key, color, name) in enumerate(series):
            value = int(row[key])
            if value <= 0:
                continue
            chunks.append(
                f'<circle cx="{x_at(index, series_index):.1f}" cy="{y_at(float(value)):.1f}" '
                f'r="6" fill="{color}" fill-opacity="0.85">'
                f"<title>{html.escape(str(row['month']))} · {name} · {value}</title></circle>"
            )
    chunks.append("</svg>")
    return "".join(chunks)


def _hbar_svg(windows: int, mac: int, linux: int) -> str:
    rows = (
        ("Windows", windows, OS_SERIES[0]["color"]),
        ("macOS", mac, OS_SERIES[1]["color"]),
        ("Linux", linux, OS_SERIES[2]["color"]),
    )
    max_v = max(1, *(count for _, count, _ in rows))
    chunks = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 100" width="100%" '
        'height="100" role="img" aria-label="Totales por sistema">'
    ]
    for index, (name, count, color) in enumerate(rows):
        y = 8 + index * 30
        bar = 180 * count / max_v
        chunks.append(
            f'<text x="0" y="{y + 12:.1f}" font-size="13" fill="{INK}">{html.escape(name)}</text>'
        )
        chunks.append(
            f'<rect x="72" y="{y:.1f}" width="{bar:.1f}" height="14" rx="3" fill="{color}"/>'
        )
        chunks.append(
            f'<text x="{80 + bar:.1f}" y="{y + 12:.1f}" font-size="13" font-weight="600" '
            f'fill="{INK}">{count}</text>'
        )
    chunks.append("</svg>")
    return "".join(chunks)


def _short_month(month: str) -> str:
    if len(month) >= 7:
        return month[2:]
    return month


def _trend_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    width, height = 760.0, 260.0
    left, right, top, bottom = 40.0, 90.0, 14.0, 30.0
    ink, muted, grid = "#111827", "#6b7280", "#e5e7eb"
    max_y = max(1.0, *(float(row["cumulative"]) for row in rows))
    plot_w, plot_h = width - left - right, height - top - bottom
    count = len(rows)

    def x_at(index: int) -> float:
        if count == 1:
            return left + plot_w / 2
        return left + plot_w * index / (count - 1)

    def y_at(value: float) -> float:
        return top + plot_h * (1 - value / max_y)

    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'width="100%" role="img" aria-label="Licencias acumuladas por mes">'
    ]
    for grid_step in (0, 0.25, 0.5, 0.75, 1):
        y = y_at(grid_step * max_y)
        chunks.append(
            f'<line x1="{left:.1f}" x2="{left + plot_w:.1f}" y1="{y:.1f}" y2="{y:.1f}" '
            f'stroke="{grid}" stroke-width="1"/>'
        )
        chunks.append(
            f'<text x="{left - 6:.1f}" y="{y + 3:.1f}" font-size="10" fill="{muted}" '
            f'text-anchor="end">{grid_step * max_y:.0f}</text>'
        )
    chunks.append(
        f'<text x="{left:.1f}" y="{height - 8:.1f}" font-size="10" fill="{muted}">'
        f"{html.escape(str(rows[0]['month']))}</text>"
    )
    chunks.append(
        f'<text x="{left + plot_w:.1f}" y="{height - 8:.1f}" font-size="10" fill="{muted}" '
        f'text-anchor="end">{html.escape(str(rows[-1]["month"]))}</text>'
    )
    cum_win = cum_mac = cum_lin = 0
    win_pts: list[str] = []
    mac_pts: list[str] = []
    lin_pts: list[str] = []
    tot_pts: list[str] = []
    for index, row in enumerate(rows):
        cum_win += int(row["windows"])
        cum_mac += int(row["mac"])
        cum_lin += int(row["linux"])
        win_pts.append(f"{x_at(index):.1f},{y_at(float(cum_win)):.1f}")
        mac_pts.append(f"{x_at(index):.1f},{y_at(float(cum_mac)):.1f}")
        lin_pts.append(f"{x_at(index):.1f},{y_at(float(cum_lin)):.1f}")
        tot_pts.append(f"{x_at(index):.1f},{y_at(float(row['cumulative'])):.1f}")
        chunks.append(
            f'<circle cx="{x_at(index):.1f}" cy="{y_at(float(row["cumulative"])):.1f}" r="3.5" '
            f'fill="{OS_SERIES[3]["color"]}"><title>{html.escape(str(row["month"]))} · '
            f'total {int(row["cumulative"])}</title></circle>'
        )
    for color, points, stroke in (
        (OS_SERIES[0]["color"], win_pts, "2"),
        (OS_SERIES[1]["color"], mac_pts, "2"),
        (OS_SERIES[2]["color"], lin_pts, "2"),
        (OS_SERIES[3]["color"], tot_pts, "2.4"),
    ):
        chunks.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="{stroke}" '
            f'points="{" ".join(points)}"/>'
        )
    chunks.append("</svg>")
    return "".join(chunks)


def _bars_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    width, height = 760.0, 150.0
    left, right, top, bottom = 36.0, 12.0, 20.0, 28.0
    max_y = 1.0
    for row in rows:
        max_y = max(max_y, float(row["windows"]), float(row["mac"]), float(row["linux"]))
    plot_w, plot_h = width - left - right, height - top - bottom
    slot = plot_w / len(rows)

    def y_at(value: float) -> float:
        return top + plot_h * (1 - value / max_y)

    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'width="100%" height="150" role="img" aria-label="Altas por mes y plataforma">'
    ]
    for grid_step in (0.0, 0.5, 1.0):
        y = y_at(grid_step * max_y)
        chunks.append(
            f'<line x1="{left:.1f}" x2="{left + plot_w:.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>'
        )
        chunks.append(
            f'<text x="{left - 6:.1f}" y="{y + 4:.1f}" font-size="12" fill="{MUTED}" '
            f'text-anchor="end">{grid_step * max_y:.0f}</text>'
        )
    bar_w = slot * 0.22
    names = ("Windows", "macOS", "Linux")
    for index, row in enumerate(rows):
        origin_x = left + slot * index + slot * 0.14
        values = (
            (float(row["windows"]), OS_SERIES[0]["color"]),
            (float(row["mac"]), OS_SERIES[1]["color"]),
            (float(row["linux"]), OS_SERIES[2]["color"]),
        )
        for series_index, (value, color) in enumerate(values):
            if value <= 0:
                continue
            bar_h = plot_h * (value / max_y)
            x = origin_x + bar_w * series_index
            chunks.append(
                f'<rect x="{x:.1f}" y="{y_at(value):.1f}" width="{bar_w * 0.9:.1f}" '
                f'height="{bar_h:.1f}" fill="{color}"><title>{html.escape(str(row["month"]))} · '
                f"{names[series_index]} · {int(value)}</title></rect>"
            )
            chunks.append(
                f'<text x="{x + bar_w * 0.45:.1f}" y="{y_at(value) - 3:.1f}" font-size="12" '
                f'fill="{INK}" text-anchor="middle">{value:.0f}</text>'
            )
        label = _short_month(str(row["month"]))
        chunks.append(
            f'<text x="{origin_x + bar_w * 1.5:.1f}" y="{height - 6:.1f}" font-size="12" '
            f'fill="{MUTED}" text-anchor="middle">{html.escape(label)}</text>'
        )
    chunks.append("</svg>")
    return "".join(chunks)


def _present_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items or []:
        alias = str(item.get("display_name") or "").strip() or str(item.get("hostname") or "")
        edition = edition_label(item.get("edition")) if item.get("edition") else ""
        rows.append(
            {
                "installation_id": int(item.get("installation_id") or 0),
                "user_id": int(item.get("user_id") or 0),
                "alias": alias,
                "hostname": str(item.get("hostname") or ""),
                "serial_masked": mask_serial(str(item.get("serial_number") or "")),
                "operating_system": str(item.get("operating_system") or ""),
                "edition": edition,
                "origin": str(item.get("origin") or ""),
                "status": str(item.get("status") or ""),
                "registered_at": format_display_datetime(item.get("registered_at")),
            }
        )
    return rows


def _channels(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in items or []:
        key = str(item.get("origin") or "").strip() or "—"
        counts[key] = counts.get(key, 0) + 1
    kinds = ("teal", "orange", "gold", "cyan", "grey")
    backgrounds = ("#99f6e4", "#fed7aa", "#fde68a", "#a5f3fc", "#e5e7eb")
    channels = []
    for index, key in enumerate(sorted(counts)):
        channels.append(
            {
                "label": key,
                "count": counts[key],
                "kind": kinds[index % len(kinds)],
                "background": backgrounds[index % len(backgrounds)],
            }
        )
    return channels


def _dominant_os(totals: dict[str, int]) -> tuple[str, float, str]:
    candidates = (
        ("Windows", int(totals.get("windows") or 0), OS_SERIES[0]["color"]),
        ("macOS", int(totals.get("mac") or 0), OS_SERIES[1]["color"]),
        ("Linux", int(totals.get("linux") or 0), OS_SERIES[2]["color"]),
    )
    name, count, color = candidates[0]
    for candidate in candidates[1:]:
        if candidate[1] > count:
            name, count, color = candidate
    total = sum(item[1] for item in candidates)
    if total == 0:
        return name, 0.0, color
    return name, 100 * count / total, color


def _monthly_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [float(row.get(key) or 0) for row in rows]


def build_dashboard(
    environment: str,
    metrics: dict[str, Any] | None,
    items: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Arma el JSON que pinta el modal Evolución. Sin ``master_key`` ni serial en claro."""
    env = str(environment or "").strip()
    metrics = metrics or {}
    raw_totals = metrics.get("totals") or {}
    totals = {
        "registered": int(raw_totals.get("registered") or 0),
        "windows": int(raw_totals.get("windows") or 0),
        "mac": int(raw_totals.get("mac") or 0),
        "linux": int(raw_totals.get("linux") or 0),
        "this_month": int(raw_totals.get("this_month") or 0),
        "licenses": int(raw_totals.get("licenses") or 0),
    }
    monthly = list(metrics.get("monthly") or [])
    dashboard: dict[str, Any] = {
        "title": "Evolución de registros",
        "subtitle": "",
        "environment": env,
        "totals": totals,
        "highlights": [],
        "tiles": [],
        "kpis": [],
        "monthly": monthly,
        "series": [dict(item) for item in OS_SERIES],
        "channels": [],
        "svg_trend": "",
        "svg_monthly": "",
        "svg_mix": "",
        "svg_scatter": "",
        "svg_os": "",
        "svg_gauge": "",
        "items": _present_items(items),
    }
    if totals["registered"] == 0:
        dashboard["subtitle"] = f"Aún no hay licencias registradas en {env}."
        return dashboard
    first = str(monthly[0]["month"]) if monthly else ""
    last = str(monthly[-1]["month"]) if monthly else ""
    dashboard["subtitle"] = (
        f"{env} · {totals['registered']} licencias · {first} → {last} · "
        "incrementos mensuales por plataforma"
    )
    windows = _monthly_values(monthly, "windows")
    mac = _monthly_values(monthly, "mac")
    linux = _monthly_values(monthly, "linux")
    total = _monthly_values(monthly, "total")
    cumulative = _monthly_values(monthly, "cumulative")
    os_name, os_pct, os_color = _dominant_os(totals)
    dashboard["highlights"] = [
        {
            "title": "Licencias registradas",
            "value": str(totals["licenses"]),
            "kind": "teal",
            "delta": _month_delta(cumulative),
            "spark_svg": _spark_svg(cumulative, "#ffffff"),
            "background": HERO_TEAL,
        },
        {
            "title": "Altas este mes",
            "value": str(totals["this_month"]),
            "kind": "cyan",
            "delta": _month_delta(total),
            "spark_svg": _spark_svg(total, "#ffffff"),
            "background": HERO_CYAN,
        },
        {
            "title": "Windows",
            "value": str(totals["windows"]),
            "kind": "orange",
            "delta": _month_delta(windows),
            "spark_svg": _spark_svg(windows, "#ffffff"),
            "background": HERO_ORANGE,
        },
        {
            "title": "Cuota principal",
            "value": f"{os_pct:.0f}%",
            "kind": "gold",
            "delta": os_name,
            "spark_svg": _gauge_svg(os_pct, "#ffffff"),
            "background": HERO_GOLD,
        },
    ]
    dashboard["tiles"] = [
        {"label": "Total", "value": str(totals["registered"]), "kind": "purple"},
        {"label": "Windows", "value": str(totals["windows"]), "kind": "blue"},
        {"label": "macOS", "value": str(totals["mac"]), "kind": "orange"},
        {"label": "Linux", "value": str(totals["linux"]), "kind": "green"},
        {"label": "Este mes", "value": str(totals["this_month"]), "kind": "green"},
        {"label": "Community Edition", "value": str(totals["licenses"]), "kind": "grey"},
    ]
    dashboard["kpis"] = [
        {
            "label": "Windows / mes",
            "value": f"{totals['windows']} acumuladas",
            "spark_svg": _spark_svg(windows, OS_SERIES[0]["color"]),
        },
        {
            "label": "macOS / mes",
            "value": f"{totals['mac']} acumuladas",
            "spark_svg": _spark_svg(mac, OS_SERIES[1]["color"]),
        },
        {
            "label": "Linux / mes",
            "value": f"{totals['linux']} acumuladas",
            "spark_svg": _spark_svg(linux, OS_SERIES[2]["color"]),
        },
        {
            "label": "Altas / mes",
            "value": f"{totals['licenses']} acumuladas",
            "spark_svg": _spark_svg(total, OS_SERIES[3]["color"]),
        },
    ]
    dashboard["channels"] = _channels(items)
    dashboard["svg_trend"] = _trend_svg(monthly)
    dashboard["svg_monthly"] = _bars_svg(monthly)
    dashboard["svg_mix"] = _donut_svg(totals["windows"], totals["mac"], totals["linux"])
    dashboard["svg_scatter"] = _scatter_svg(monthly)
    dashboard["svg_os"] = _hbar_svg(totals["windows"], totals["mac"], totals["linux"])
    dashboard["svg_gauge"] = _gauge_svg(os_pct, os_color)
    return dashboard
