from __future__ import annotations

from datetime import datetime
import html
import math
import time

def fmt_ts(ts: float) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(float(ts)).astimezone().strftime("%Y-%m-%d %H:%M:%S")

def fmt_short_ts(ts: float) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(float(ts)).astimezone().strftime("%H:%M:%S")

def fmt_rel_ts(ts: float) -> str:
    if not ts:
        return "—"
    diff = time.time() - float(ts)
    if diff < 0:
        return "just now"
    if diff < 60:
        return f"{int(diff)}s ago"
    if diff < 3600:
        return f"{int(diff / 60)}m ago"
    if diff < 86400:
        return f"{int(diff / 3600)}h ago"
    return f"{int(diff / 86400)}d ago"

def fmt_bytes(b: int) -> str:
    if not b:
        return "0 B"
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b / (1024 * 1024):.2f} MB"

def status_color(status: int) -> tuple[str, str]:
    if 200 <= status < 300:
        return "#10b981", "rgba(16, 185, 129, 0.15)"
    if 300 <= status < 400:
        return "#06b6d4", "rgba(6, 182, 212, 0.15)"
    if 400 <= status < 500:
        return "#f59e0b", "rgba(245, 158, 11, 0.15)"
    return "#ef4444", "rgba(239, 68, 68, 0.15)"

def status_badge(status: int) -> str:
    c, bg = status_color(status)
    return f'<span class="badge" style="color:{c};background:{bg};border:1px solid {c}44;">{status}</span>'

def auto_badge(score: int, level: str) -> str:
    if level == "high":
        c, bg = "#ef4444", "rgba(239, 68, 68, 0.2)"
    elif level == "medium":
        c, bg = "#f59e0b", "rgba(245, 158, 11, 0.2)"
    else:
        c, bg = "#10b981", "rgba(16, 185, 129, 0.15)"
    return f'<span class="badge auto-{level}" style="color:{c};background:{bg};border:1px solid {c}44;" title="Score: {score} ({level})">{score} {level.upper()}</span>'

def method_badge(method: str) -> str:
    m = method.upper()
    colors = {
        "GET": ("#06b6d4", "rgba(6, 182, 212, 0.15)"),
        "POST": ("#10b981", "rgba(16, 185, 129, 0.15)"),
        "OPTIONS": ("#a855f7", "rgba(168, 85, 247, 0.2)"),
        "HEAD": ("#f59e0b", "rgba(245, 158, 11, 0.15)"),
        "PUT": ("#ec4899", "rgba(236, 72, 153, 0.15)"),
        "DELETE": ("#ef4444", "rgba(239, 68, 68, 0.15)"),
    }
    c, bg = colors.get(m, ("#94a3b8", "rgba(148, 163, 184, 0.15)"))
    return f'<span class="badge method-{m.lower()}" style="color:{c};background:{bg};border:1px solid {c}44;font-family:monospace;">{html.escape(m)}</span>'

def render_switcher(active_page: str) -> str:
    options = [
        ("/4", "Telemetry HUD", "Real-Time Tactical Bento & Waveform HUD"),
        ("/1", "1. Ops Console", "Deep Space Telemetry Stream"),
        ("/2", "2. Executive", "Modern SaaS & Briefing"),
        ("/3", "3. Forensics Lab", "Protocol & Convention Research"),
        ("/hub", "Showcase Hub", "Overview & Architecture Matrix"),
    ]
    links = []
    for path, title, desc in options:
        is_active = (
            (active_page == path)
            or (active_page == path.lstrip("/"))
            or (path == "/4" and active_page in ("/", ""))
        )
        active_cls = " switcher-item-active" if is_active else ""
        links.append(f"""
        <a href="{path}" class="switcher-item{active_cls}" title="{desc}">
            <span class="switcher-title">{title}</span>
        </a>
        """)
    return f"""
    <div id="obs-switcher-bar">
        <div class="obs-switcher-left">
            <span class="obs-live-indicator"><span class="obs-pulse"></span> PASSIVE INGEST</span>
            <span class="obs-host-pill">www2.onnwee.me</span>
        </div>
        <div class="obs-switcher-tabs">
            {"".join(links)}
        </div>
        <div class="obs-switcher-right">
            <a href="/api/summary" target="_blank" class="obs-btn-sm" title="View JSON summary">API</a>
            <a href="/api/export.ndjson?limit=500" class="obs-btn-sm" title="Export NDJSON stream">EXPORT</a>
            <span class="obs-timer" id="obs-refresh-countdown" title="Auto-refreshing in seconds">15s</span>
        </div>
    </div>
    """

# ----------------- Pure SVG Chart Helpers -----------------

def svg_stacked_bar_chart(buckets: list[dict], width: int = 760, height: int = 150) -> str:
    if not buckets:
        return f'<div class="chart-empty">No timeline activity recorded in this period.</div>'
    
    pad_left, pad_right, pad_top, pad_bottom = 36, 16, 20, 24
    chart_w = width - pad_left - pad_right
    chart_h = height - pad_top - pad_bottom

    max_val = max(b.get("total", 0) for b in buckets) or 1
    # round up max_val nicely
    max_y = math.ceil(max_val * 1.25)
    if max_y < 5: max_y = 5

    n = len(buckets)
    bar_width = max(4, min(24, int((chart_w / n) * 0.72)))
    gap = (chart_w - (n * bar_width)) / max(1, n)

    # Grid lines
    grid_lines = []
    for step in [0, 0.5, 1.0]:
        y_val = int(max_y * step)
        y_pos = pad_top + chart_h - (chart_h * step)
        grid_lines.append(f'<line x1="{pad_left}" y1="{y_pos}" x2="{width - pad_right}" y2="{y_pos}" stroke="rgba(255,255,255,0.07)" stroke-dasharray="3,3" />')
        grid_lines.append(f'<text x="{pad_left - 8}" y="{y_pos + 4}" fill="#64748b" font-size="10" text-anchor="end" font-family="monospace">{y_val}</text>')

    bars = []
    labels = []
    for i, b in enumerate(buckets):
        x = pad_left + i * (bar_width + gap) + gap / 2
        total = b.get("total", 0)
        high = b.get("high", 0)
        med = b.get("medium", 0)
        low = b.get("low", 0)

        # heights
        h_high = (high / max_y) * chart_h
        h_med = (med / max_y) * chart_h
        h_low = (low / max_y) * chart_h

        y_base = pad_top + chart_h
        # stack low (green), med (amber), high (red)
        y_low = y_base - h_low
        y_med = y_low - h_med
        y_high = y_med - h_high

        time_label = b.get("bucket", "").split(" ")[-1] if " " in b.get("bucket", "") else b.get("bucket", "")

        # tooltip payload
        tip = f"{b.get('bucket','')}: {total} reqs ({low} human, {med} cli, {high} bot/probe)"

        if low > 0:
            bars.append(f'<rect x="{x}" y="{y_low}" width="{bar_width}" height="{h_low}" fill="#10b981" rx="1"><title>{tip}</title></rect>')
        if med > 0:
            bars.append(f'<rect x="{x}" y="{y_med}" width="{bar_width}" height="{h_med}" fill="#f59e0b" rx="1"><title>{tip}</title></rect>')
        if high > 0:
            bars.append(f'<rect x="{x}" y="{y_high}" width="{bar_width}" height="{h_high}" fill="#ef4444" rx="1"><title>{tip}</title></rect>')

        if n <= 16 or i % max(1, n // 8) == 0:
            labels.append(f'<text x="{x + bar_width/2}" y="{height - 6}" fill="#64748b" font-size="9" text-anchor="middle" font-family="monospace">{time_label}</text>')

    return f"""
    <svg viewBox="0 0 {width} {height}" class="obs-svg-chart" preserveAspectRatio="none">
        {"".join(grid_lines)}
        {"".join(bars)}
        {"".join(labels)}
    </svg>
    """

def svg_spline_area_chart(buckets: list[dict], width: int = 760, height: int = 160) -> str:
    if not buckets:
        return f'<div class="chart-empty">No activity data available</div>'
    
    pad_left, pad_right, pad_top, pad_bottom = 36, 16, 20, 24
    chart_w = width - pad_left - pad_right
    chart_h = height - pad_top - pad_bottom

    points = [b.get("total", 0) for b in buckets]
    max_val = max(points) or 1
    max_y = math.ceil(max_val * 1.25)
    if max_y < 5: max_y = 5

    n = len(points)
    step_x = chart_w / max(1, n - 1) if n > 1 else chart_w

    coords = []
    for i, val in enumerate(points):
        x = pad_left + i * step_x
        y = pad_top + chart_h - ((val / max_y) * chart_h)
        coords.append((x, y))

    # Construct smooth SVG path
    path_d = [f"M {coords[0][0]},{coords[0][1]}"]
    for i in range(1, len(coords)):
        x0, y0 = coords[i - 1]
        x1, y1 = coords[i]
        cx = (x0 + x1) / 2
        path_d.append(f"C {cx},{y0} {cx},{y1} {x1},{y1}")

    stroke_d = " ".join(path_d)
    area_d = f"{stroke_d} L {coords[-1][0]},{pad_top + chart_h} L {coords[0][0]},{pad_top + chart_h} Z"

    # Grid
    grid_lines = []
    for step in [0, 0.5, 1.0]:
        y_val = int(max_y * step)
        y_pos = pad_top + chart_h - (chart_h * step)
        grid_lines.append(f'<line x1="{pad_left}" y1="{y_pos}" x2="{width - pad_right}" y2="{y_pos}" stroke="rgba(255,255,255,0.06)" />')
        grid_lines.append(f'<text x="{pad_left - 8}" y="{y_pos + 4}" fill="#64748b" font-size="10" text-anchor="end">{y_val}</text>')

    # Dot markers
    dots = []
    for i, (x, y) in enumerate(coords):
        b = buckets[i]
        time_label = b.get("bucket", "").split(" ")[-1] if " " in b.get("bucket", "") else b.get("bucket", "")
        tip = f"{time_label}: {points[i]} requests"
        dots.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="#38bdf8" stroke="#0f172a" stroke-width="2"><title>{tip}</title></circle>')

    return f"""
    <svg viewBox="0 0 {width} {height}" class="obs-svg-chart">
        <defs>
            <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.35"/>
                <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.0"/>
            </linearGradient>
        </defs>
        {"".join(grid_lines)}
        <path d="{area_d}" fill="url(#areaGrad)" />
        <path d="{stroke_d}" fill="none" stroke="#38bdf8" stroke-width="2.5" />
        {"".join(dots)}
    </svg>
    """

def svg_donut_chart(items: list[tuple[str, int, str]], size: int = 150) -> str:
    """items: list of (label, count, color)"""
    total = sum(c for _, c, _ in items)
    if total == 0:
        return f'<svg width="{size}" height="{size}"><circle cx="{size/2}" cy="{size/2}" r="{size/3}" fill="none" stroke="#2a313b" stroke-width="14" /></svg>'

    r = size * 0.36
    cx, cy = size / 2, size / 2
    circ = 2 * math.pi * r

    paths = []
    offset = 0.0
    for label, count, color in items:
        if count <= 0: continue
        frac = count / total
        dash = frac * circ
        paths.append(f"""
        <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="14"
                stroke-dasharray="{dash} {circ - dash}" stroke-dashoffset="{-offset}">
            <title>{label}: {count} ({int(frac*100)}%)</title>
        </circle>
        """)
        offset += dash

    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
        <g transform="rotate(-90 {cx} {cy})">
            {"".join(paths)}
        </g>
        <text x="{cx}" y="{cy + 5}" text-anchor="middle" font-size="14" font-weight="700" fill="#f8fafc">{total}</text>
    </svg>
    """

def svg_sparkline(values: list[float], width: int = 90, height: int = 24, stroke: str = "#10b981") -> str:
    if not values or len(values) < 2:
        return ""
    min_v, max_v = min(values), max(values)
    rng = max(1.0, max_v - min_v)
    step_x = width / (len(values) - 1)
    pts = []
    for i, v in enumerate(values):
        x = i * step_x
        y = height - ((v - min_v) / rng) * (height - 6) - 3
        pts.append(f"{x:.1f},{y:.1f}")
    return f'<svg width="{width}" height="{height}" class="sparkline"><polyline points="{" ".join(pts)}" fill="none" stroke="{stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
