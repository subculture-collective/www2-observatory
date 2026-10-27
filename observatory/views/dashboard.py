from __future__ import annotations

import html
import json
import sqlite3

from .components import (
    fmt_bytes,
    fmt_rel_ts,
    fmt_short_ts,
    fmt_ts,
)
from .. import analytics

DASHBOARD_CSS = """
:root {
    /* Canonical Command-Center Palette from colors.toml */
    --accent: #9CF23A;          /* Hyper Acid Green */
    --accent-bright: #A8FF3E;   /* Neon Acid Green Glow */
    --selection: #4B286D;       /* Deep Imperial Purple */
    --purple-glow: rgba(143, 75, 200, 0.35);
    --muted: #665577;           /* Slate Purple */
    
    --bg: #0B0810;              /* Command Void Black */
    --bg-darker: #060408;       /* Deepest Black */
    --panel: #120D18;           /* Primary Tactical Deck */
    --panel-border: #4B286D;    /* Rich Purple Border */
    --panel-lighter: #24172F;   /* Meter & Inner Card Background */
    
    --fg: #E8E1EF;              /* Crisp Off-White */
    --fg-dim: #8E809A;          /* Muted Lavender Grey */
    --fg-light: #D2C6DC;        /* Soft White */
    --fg-bright: #FFFFFF;       /* Pure White */
    
    /* Vibrant Tactical Spectrum */
    --red: #D52032;             /* High Alert Red */
    --bright-red: #FF4055;      /* Crimson Flash */
    --yellow: #F6D447;          /* Warning Yellow */
    --bright-yellow: #FFE36A;   /* Bright Gold */
    --orange: #F28C28;          /* Safety / Probe Orange */
    --green: #75C936;           /* Nominal / Human Green */
    --cyan: #4FD6C8;            /* Signal Cyan */
    --bright-cyan: #75F2E4;     /* Electric Teal */
    --blue: #5577CC;            /* Protocol Blue */
    --bright-blue: #7799FF;     /* Laser Blue */
    --magenta: #A855D4;         /* Telemetry Violet */
    --bright-magenta: #D477FF;  /* High Resonance Purple */
    
    --mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
}

/* Palette Presets derived from wallpaper art direction */
body[data-theme="crimson"] {
    --accent: #FF4055;
    --accent-bright: #FF7080;
    --selection: #66101A;
    --panel-border: #991B24;
    --panel: #140A0D;
    --panel-lighter: #261016;
    --purple-glow: rgba(255, 64, 85, 0.3);
}
body[data-theme="amber"] {
    --accent: #F6D447;
    --accent-bright: #FFE36A;
    --selection: #5E4610;
    --panel-border: #9E7416;
    --panel: #151108;
    --panel-lighter: #261D0C;
    --purple-glow: rgba(246, 212, 71, 0.3);
}
body[data-theme="alert"] {
    --accent: #FF4055;
    --accent-bright: #FFE36A;
    --selection: #4A1224;
    --panel-border: #E11D48;
    --panel: #13070C;
    --panel-lighter: #280C19;
    --purple-glow: rgba(225, 29, 72, 0.35);
}
body[data-theme="optic"] {
    --accent: #4FD6C8;
    --accent-bright: #75F2E4;
    --selection: #1A3448;
    --panel-border: #2B577A;
    --panel: #0A1118;
    --panel-lighter: #122130;
    --purple-glow: rgba(79, 214, 200, 0.3);
}
body[data-theme="hazard"] {
    --accent: #F28C28;
    --accent-bright: #FF9F43;
    --selection: #5C270A;
    --panel-border: #C2410C;
    --panel: #160B06;
    --panel-lighter: #2E150B;
    --purple-glow: rgba(242, 140, 40, 0.35);
}

* { box-sizing: border-box; }
body {
    margin: 0;
    background: var(--bg);
    color: var(--fg);
    font-family: var(--mono);
    font-size: 12px;
    line-height: 1.45;
    background-image: 
        radial-gradient(ellipse at top right, rgba(143, 75, 200, 0.12) 0%, transparent 60%),
        radial-gradient(ellipse at bottom left, rgba(79, 214, 200, 0.07) 0%, transparent 60%);
    background-attachment: fixed;
}
body.scanlines::before {
    content: " ";
    display: block;
    position: fixed;
    top: 0; left: 0; bottom: 0; right: 0;
    background: linear-gradient(rgba(18, 13, 24, 0) 50%, rgba(6, 4, 8, 0.32) 50%), linear-gradient(90deg, rgba(213, 32, 50, 0.03), rgba(156, 242, 58, 0.02), rgba(79, 214, 200, 0.03));
    z-index: 9999;
    background-size: 100% 3px, 3px 100%;
    pointer-events: none;
    opacity: 0.85;
}

/* Master Tactical Header Bar */
#obs-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--bg-darker);
    border-bottom: 1px solid var(--panel-border);
    padding: 8px 18px;
    font-size: 11px;
    position: sticky;
    top: 0;
    z-index: 1000;
}
.header-left { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.brand-title { font-weight: 800; color: var(--accent); letter-spacing: 0.08em; font-size: 12px; display: flex; align-items: center; gap: 8px; }
.live-badge { display: flex; align-items: center; gap: 6px; font-weight: 700; color: var(--accent); font-size: 11px; }
.pulse-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 8px var(--accent); animation: pulse 1.8s infinite; }
@keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(0.8); } 100% { opacity: 1; transform: scale(1); } }
.pill { background: var(--selection); color: var(--fg-bright); padding: 2px 8px; border: 1px solid var(--panel-border); border-radius: 3px; font-weight: 700; }

.header-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.palette-group { display: flex; align-items: center; gap: 5px; }
.palette-btn {
    background: var(--panel-lighter);
    border: 1px solid var(--panel-border);
    color: var(--fg-dim);
    font-family: var(--mono);
    font-size: 10px;
    cursor: pointer;
    padding: 3px 8px;
    border-radius: 3px;
    transition: all 0.15s ease;
}
.palette-btn:hover { color: var(--fg-bright); border-color: var(--accent); }
.palette-btn.active { color: var(--accent); background: var(--selection); border-color: var(--accent); font-weight: 700; }
.action-btn {
    background: var(--selection);
    color: var(--fg-bright);
    text-decoration: none;
    padding: 3px 9px;
    border: 1px solid var(--panel-border);
    border-radius: 3px;
    font-size: 11px;
    font-weight: 600;
    transition: all 0.15s ease;
}
.action-btn:hover { background: var(--magenta); color: #fff; border-color: var(--accent); }
.refresh-timer {
    color: var(--yellow);
    font-weight: 700;
    cursor: pointer;
    padding: 2px 6px;
    border: 1px dashed rgba(246, 212, 71, 0.4);
    border-radius: 3px;
}
.refresh-timer:hover { background: rgba(246, 212, 71, 0.15); }

/* Automation Alert Ticker */
.alert-ticker {
    background: repeating-linear-gradient(-45deg, #0B0810, #0B0810 14px, #D52032 14px, #D52032 28px);
    padding: 2px;
    margin: 8px 16px 0;
    border-radius: 4px;
}
.alert-inner {
    background: #14070B;
    border: 1px solid var(--bright-red);
    padding: 6px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: var(--bright-red);
    font-weight: 700;
    letter-spacing: 0.06em;
}
.alert-blink { animation: alertPulse 1.2s infinite; }
@keyframes alertPulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }

/* Telemetry KPI Ribbon */
.kpi-ribbon {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 10px;
    padding: 10px 16px 0;
}
.kpi-node {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: hidden;
}
.kpi-node::before {
    content: "";
    position: absolute;
    top: 0; left: 0; bottom: 0;
    width: 3px;
}
.kpi-traffic::before { background: var(--accent); }
.kpi-clients::before { background: var(--cyan); }
.kpi-auto::before { background: var(--orange); }
.kpi-security::before { background: var(--magenta); }
.kpi-bandwidth::before { background: var(--blue); }

.kpi-head { display: flex; justify-content: space-between; font-size: 10px; color: var(--fg-dim); font-weight: 700; text-transform: uppercase; margin-bottom: 2px; }
.kpi-val { font-size: 22px; font-weight: 800; color: var(--fg-bright); letter-spacing: -0.02em; }
.kpi-sub { font-size: 11px; color: var(--fg-light); margin-top: 2px; }

/* 6-Pane Bento HUD Layout */
.hud-layout {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
    padding: 12px 16px;
    max-width: 1720px;
    margin: 0 auto;
}
@media (max-width: 1280px) {
    .hud-layout { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 800px) {
    .hud-layout { grid-template-columns: 1fr; }
}

.pane {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    padding: 12px;
    position: relative;
    display: flex;
    flex-direction: column;
    min-height: 270px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    transition: border-color 0.2s ease;
}
.pane:hover {
    border-color: var(--accent);
}
.pane.maximized {
    position: fixed;
    top: 50px; left: 14px; right: 14px; bottom: 50px;
    z-index: 5000;
    min-height: auto;
    border-color: var(--accent);
    box-shadow: 0 0 35px var(--purple-glow);
}
.pane-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px dashed var(--panel-border);
    padding-bottom: 7px;
    margin-bottom: 10px;
    font-size: 11px;
}
.pane-title { font-weight: 800; color: var(--accent); display: flex; align-items: center; gap: 7px; letter-spacing: 0.04em; }
.pane-hotkey { color: var(--yellow); border: 1px solid var(--yellow); padding: 0 5px; font-size: 10px; border-radius: 2px; font-weight: 700; }
.pane-controls button {
    background: var(--panel-lighter); border: 1px solid var(--panel-border); color: var(--fg);
    font-family: var(--mono); font-size: 10px; cursor: pointer; padding: 2px 6px; border-radius: 2px;
}
.pane-controls button:hover { background: var(--selection); color: #fff; border-color: var(--accent); }
.pane-content { flex: 1; overflow: auto; }

/* Oscilloscope */
.oscilloscope-box {
    background: var(--bg-darker);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    padding: 6px;
    margin-bottom: 8px;
}

/* Wire Feed */
.wire-feed-scroll {
    max-height: 280px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.wire-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 6px;
    border-bottom: 1px solid rgba(75, 40, 109, 0.4);
    font-size: 11px;
    white-space: nowrap;
    border-radius: 2px;
    cursor: pointer;
    transition: background 0.12s ease;
}
.wire-row:hover { background: var(--selection); }
.wire-ts { color: var(--fg-dim); width: 62px; font-size: 10px; }
.wire-tag { padding: 1px 5px; font-size: 10px; border-radius: 2px; font-weight: 700; }
.tag-high { background: rgba(213, 32, 50, 0.25); color: var(--bright-red); border: 1px solid var(--bright-red); text-shadow: 0 0 4px var(--bright-red); }
.tag-med { background: rgba(242, 140, 40, 0.2); color: var(--orange); border: 1px solid var(--orange); }
.tag-low { background: rgba(117, 201, 54, 0.2); color: var(--green); border: 1px solid var(--green); }
.wire-status { font-weight: 700; width: 34px; font-size: 11px; }
.status-2xx { color: var(--cyan); }
.status-3xx { color: var(--blue); }
.status-4xx { color: var(--yellow); }
.status-5xx { color: var(--bright-red); }

.wire-meth { font-weight: 700; width: 52px; font-size: 11px; }
.meth-get { color: var(--cyan); }
.meth-post { color: var(--orange); }
.meth-options { color: var(--magenta); }
.meth-head { color: var(--yellow); }
.meth-put { color: var(--bright-magenta); }
.meth-delete { color: var(--bright-red); }

.wire-path { color: var(--fg-bright); flex: 1; overflow: hidden; text-overflow: ellipsis; }
.wire-client { color: var(--bright-cyan); width: 70px; font-size: 10px; overflow: hidden; text-overflow: ellipsis; }

/* Heuristic Gauges */
.gauge-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px solid rgba(75, 40, 109, 0.35);
    font-size: 11px;
}
.gauge-name { color: var(--fg-light); width: 155px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gauge-bar-wrapper { flex: 1; margin: 0 10px; font-family: var(--mono); }
.gauge-count { font-weight: 700; color: var(--fg-bright); width: 40px; text-align: right; }

/* Session Topology Tree */
.tree-node {
    margin-bottom: 10px;
    padding: 8px;
    background: var(--bg-darker);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
}
.tree-head { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px; }
.tree-sid { color: var(--magenta); font-weight: 700; }
.tree-client { color: var(--cyan); }
.tree-body { font-size: 11px; color: var(--fg-dim); line-height: 1.4; }

/* Relay Wiretap */
.wiretap-item {
    padding: 8px;
    background: var(--bg-darker);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    margin-bottom: 8px;
}
.wiretap-header { display: flex; justify-content: space-between; font-size: 10px; color: var(--orange); font-weight: 700; margin-bottom: 4px; }
.wiretap-body { color: var(--fg-bright); font-size: 11px; line-height: 1.4; word-break: break-all; }
.wiretap-hash { color: var(--cyan); font-size: 10px; margin-top: 4px; }

/* Node Diagnostics Grid */
.diag-row {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px solid rgba(75, 40, 109, 0.4);
    font-size: 11px;
}
.diag-label { color: var(--fg-dim); }
.diag-val { color: var(--fg-bright); font-weight: 600; text-align: right; }

/* Slide-over Packet Inspector Drawer */
#inspector-drawer {
    position: fixed;
    top: 0;
    right: -520px;
    width: 500px;
    height: 100vh;
    background: #0D0814;
    border-left: 1px solid var(--panel-border);
    box-shadow: -10px 0 35px rgba(0,0,0,0.7);
    z-index: 6000;
    transition: right 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
}
#inspector-drawer.open { right: 0; }
.drawer-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--panel-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--panel);
}
.drawer-title { font-size: 13px; font-weight: 800; color: var(--accent); letter-spacing: 0.06em; }
.drawer-close { background: none; border: none; color: var(--fg-dim); font-size: 22px; cursor: pointer; padding: 2px 6px; line-height: 1; }
.drawer-close:hover { color: #fff; }
.drawer-body { padding: 20px; overflow-y: auto; flex: 1; font-size: 12px; }
.drawer-section { margin-bottom: 20px; }
.drawer-section-title { font-size: 11px; text-transform: uppercase; color: var(--fg-dim); letter-spacing: 0.05em; margin-bottom: 8px; border-bottom: 1px solid var(--panel-lighter); padding-bottom: 4px; font-weight: 700; }
.drawer-field { display: flex; justify-content: space-between; padding: 4px 0; gap: 10px; }
.drawer-field .field-name { color: var(--fg-dim); flex-shrink: 0; }
.drawer-field .field-val { color: var(--fg-bright); word-break: break-all; text-align: right; font-weight: 600; }
.signals-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.signal-chip { background: rgba(242, 140, 40, 0.18); color: var(--orange); border: 1px solid rgba(242, 140, 40, 0.35); padding: 2px 7px; border-radius: 4px; font-size: 11px; font-weight: 600; }

/* Bottom Command Line Bar */
.cli-bar {
    position: sticky;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--bg-darker);
    border-top: 1px solid var(--panel-border);
    padding: 8px 18px;
    display: flex;
    align-items: center;
    gap: 12px;
    z-index: 1000;
}
.cli-prompt { color: var(--accent); font-weight: 800; font-size: 14px; text-shadow: 0 0 5px var(--accent); }
.cli-input {
    background: none;
    border: none;
    color: var(--accent-bright);
    font-family: var(--mono);
    font-size: 12px;
    flex: 1;
    outline: none;
    font-weight: 600;
}
.cli-input::placeholder { color: var(--muted); }
.cli-help-pill { color: var(--fg-dim); font-size: 11px; }
"""

def render_dashboard(conn: sqlite3.Connection) -> str:
    s = analytics.summary(conn, 24)
    tl = analytics.timeline(conn, 24)
    recent_events = analytics.recent(conn, 50)
    sig = analytics.signals(conn, 168)
    sess = analytics.sessions(conn, 168, 8)
    wr = analytics.writes(conn, 10)
    sys_st = analytics.system_stats(conn)

    # 1. Multi-Gradient Oscilloscope Waveform (Traffic Velocity & Automation Curve)
    totals = [b.get("total", 0) for b in tl] or [1, 1]
    highs = [b.get("high", 0) for b in tl] or [0, 0]
    max_t = max(totals) or 1
    w_svg, h_svg = 520, 120
    step = w_svg / max(1, len(totals) - 1)

    pts_total = []
    pts_high = []
    area_pts = [f"0,{h_svg}"]
    for i, val in enumerate(totals):
        x = i * step
        y = h_svg - 14 - (val / max_t) * (h_svg - 32)
        pts_total.append(f"{x:.1f},{y:.1f}")
        area_pts.append(f"{x:.1f},{y:.1f}")

    for i, val in enumerate(highs):
        x = i * step
        y = h_svg - 14 - (val / max_t) * (h_svg - 32)
        pts_high.append(f"{x:.1f},{y:.1f}")

    area_pts.append(f"{w_svg},{h_svg}")

    oscilloscope = f"""
    <svg viewBox="0 0 {w_svg} {h_svg}" style="width:100%; height:130px;" preserveAspectRatio="none">
        <defs>
            <linearGradient id="dashWaveGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#9CF23A" stop-opacity="0.35"/>
                <stop offset="50%" stop-color="#8F4BC8" stop-opacity="0.2"/>
                <stop offset="100%" stop-color="#0B0810" stop-opacity="0.0"/>
            </linearGradient>
            <pattern id="dashGrid" width="26" height="26" patternUnits="userSpaceOnUse">
                <path d="M 26 0 L 0 0 0 26" fill="none" stroke="rgba(75,40,109,0.3)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="{w_svg}" height="{h_svg}" fill="#08050C" />
        <rect width="{w_svg}" height="{h_svg}" fill="url(#dashGrid)" />
        <polygon points="{' '.join(area_pts)}" fill="url(#dashWaveGrad)" />
        <polyline points="{' '.join(pts_total)}" fill="none" stroke="#9CF23A" stroke-width="2.5" stroke-linecap="round"/>
        <polyline points="{' '.join(pts_high)}" fill="none" stroke="#FF4055" stroke-width="1.8" stroke-dasharray="3,3"/>
        <text x="10" y="18" fill="#F6D447" font-size="10" font-weight="700" font-family="monospace">RADAR WAVEFORM: 24H INBOUND // PEAK: {max_t} REQ/HR</text>
        <text x="{w_svg - 145}" y="18" fill="#4FD6C8" font-size="9" font-family="monospace">HOST: www2.onnwee.me</text>
    </svg>
    """

    # 2. Live Inbound Packet Wire Rows + JSON Payload for Slide-Over Inspector
    wire_rows: list[str] = []
    events_json: list[dict[str, object]] = []
    for r in recent_events:
        score = r.get("automation_score", 0)
        level = r.get("automation_level", "low")
        st = r.get("status", 200)
        m = r.get("method", "GET").upper()
        p = r.get("path", "")
        q = r.get("query", "")
        full_p = f"{p}?{q}" if q else p
        cid = r.get("client_id", "")
        ts_str = fmt_short_ts(r.get("ts", 0))

        tag_cls = f"tag-{level}"
        st_cls = "status-2xx" if 200 <= st < 300 else ("status-3xx" if 300 <= st < 400 else ("status-4xx" if 400 <= st < 500 else "status-5xx"))
        meth_cls = f"meth-{m.lower()}"

        idx = len(events_json)
        events_json.append({
            "ts": fmt_ts(r.get("ts", 0)),
            "rel_ts": fmt_rel_ts(r.get("ts", 0)),
            "method": m,
            "path": p,
            "query": q,
            "status": st,
            "score": score,
            "level": level,
            "client_id": cid,
            "session_id": r.get("session_id", ""),
            "user_agent": r.get("user_agent", ""),
            "accept": r.get("accept_header", ""),
            "referer": r.get("referer", ""),
            "bytes": fmt_bytes(r.get("response_bytes", 0)),
            "signals": json.loads(r.get("signals_json", "[]")),
        })

        wire_rows.append(f"""
        <div class="wire-row" data-idx="{idx}" data-level="{level}" data-status="{st}" data-method="{m}" onclick="inspectPacket({idx})" title="Click to inspect packet headers &amp; heuristic score">
            <span class="wire-ts">{ts_str}</span>
            <span class="wire-tag {tag_cls}">A:{score:02d}</span>
            <span class="wire-status {st_cls}">{st}</span>
            <span class="wire-meth {meth_cls}">{m}</span>
            <span class="wire-client">#{cid[:8]}</span>
            <span class="wire-path">{html.escape(full_p)}</span>
        </div>
        """)

    # 3. Behavioral Heuristic Vectors (Multi-Color Gauges)
    probe_colors = ["#9CF23A", "#F6D447", "#F28C28", "#A855D4", "#4FD6C8", "#5577CC", "#FF4055"]
    max_ev = max((item.get("events", 1) for item in sig), default=1)
    gauge_rows = []
    for idx, item in enumerate(sig[:8]):
        name = item.get("signal", "")
        cnt = item.get("events", 0)
        c = probe_colors[idx % len(probe_colors)]
        bar_len = int((cnt / max_ev) * 16)
        bar = "█" * bar_len + "░" * (16 - bar_len)
        gauge_rows.append(f"""
        <div class="gauge-row">
            <span class="gauge-name" style="color:{c};" title="{html.escape(name)}">{html.escape(name)}</span>
            <span class="gauge-bar-wrapper" style="color:{c};">{bar}</span>
            <span class="gauge-count">{cnt}</span>
        </div>
        """)

    # 4. Session Topology Trees
    session_trees = []
    for idx, s_item in enumerate(sess[:4]):
        sid = s_item.get("session_id", "")[:10]
        cid = s_item.get("client_id", "")[:10]
        reqs = s_item.get("requests", 0)
        trail = s_item.get("trail", "") or ""
        steps = trail.split(" → ")

        step_lines = []
        for j, step in enumerate(steps[:5]):
            prefix = "└── " if j == len(steps[:5]) - 1 else "├── "
            step_lines.append(f"<div>{prefix}<span style='color:var(--fg-bright);'>{html.escape(str(step))}</span></div>")
        if len(steps) > 5:
            step_lines.append(f"<div style='color:var(--fg-dim);'>└── ... (+{len(steps)-5} additional hops)</div>")

        session_trees.append(f"""
        <div class="tree-node">
            <div class="tree-head">
                <span class="tree-sid">SESSION #{idx+1} [HASH:{sid}]</span>
                <span class="tree-client">CLIENT: #{cid}</span>
            </div>
            <div style="font-size:10px; color:var(--fg-dim); margin-bottom:6px;">
                {reqs} HOPS &middot; MAX AUTOMATION: <strong style="color:var(--yellow);">{s_item.get('max_automation',0)}</strong> &middot; {fmt_rel_ts(s_item.get('started',0))}
            </div>
            <div class="tree-body">
                {''.join(step_lines)}
            </div>
        </div>
        """)

    # 5. Application Relay Stream
    wiretap_items = []
    for w in wr[:5]:
        wiretap_items.append(f"""
        <div class="wiretap-item">
            <div class="wiretap-header">
                <span>RELAY EVENT // {html.escape(w.get('event','').upper())}</span>
                <span>{fmt_rel_ts(w.get('ts', 0))}</span>
            </div>
            <div style="color:var(--yellow); font-size:10px; margin-bottom:3px;">
                TARGET PATH: <code>{html.escape(w.get('path',''))}</code>
            </div>
            <div class="wiretap-body">&gt; {html.escape(w.get('content','')[:150])}</div>
            <div class="wiretap-hash">SHA-256: {html.escape(w.get('content_hash','')[:16])} &middot; CLIENT: #{html.escape(w.get('client_id','')[:8])}</div>
        </div>
        """)

    # High Automation Alert Banner
    high_auto_cnt = s.get("high_auto", 0)
    alert_banner = ""
    if high_auto_cnt > 0:
        alert_banner = f"""
        <div class="alert-ticker">
            <div class="alert-inner">
                <span class="alert-blink">&Delta; AUTOMATED CRAWLER DENSITY ELEVATED &Delta;</span>
                <span>HIGH AUTOMATION DETECTIONS: {high_auto_cnt} PROBE EVENTS IN 24H</span>
                <span style="color:var(--yellow);">INGESTION: PASSIVE CONTINUOUS CAPTURE</span>
            </div>
        </div>
        """

    script = f"""
    <script>
    const PACKETS_DATA = {json.dumps(events_json)};

    function setPalette(name) {{
        document.body.dataset.theme = name;
        localStorage.setItem('obs_theme', name);
        document.querySelectorAll('.palette-btn').forEach(btn => {{
            btn.classList.toggle('active', btn.getAttribute('data-theme') === name);
        }});
    }}
    // Load saved palette
    const savedTheme = localStorage.getItem('obs_theme') || 'matrix';
    setPalette(savedTheme);

    function toggleMaximize(id) {{
        const el = document.getElementById(id);
        el.classList.toggle('maximized');
    }}
    function toggleScanlines() {{
        document.body.classList.toggle('scanlines');
    }}

    function inspectPacket(idx) {{
        const ev = PACKETS_DATA[idx];
        if (!ev) return;
        document.getElementById('ins-ts').innerText = ev.ts + ' (' + ev.rel_ts + ')';
        document.getElementById('ins-method').innerText = ev.method;
        document.getElementById('ins-path').innerText = ev.path + (ev.query ? '?' + ev.query : '');
        document.getElementById('ins-status').innerText = ev.status;
        document.getElementById('ins-score').innerText = ev.score + ' (' + ev.level.toUpperCase() + ')';
        document.getElementById('ins-client').innerText = ev.client_id;
        document.getElementById('ins-session').innerText = ev.session_id;
        document.getElementById('ins-bytes').innerText = ev.bytes;
        document.getElementById('ins-ua').innerText = ev.user_agent || 'None';
        document.getElementById('ins-accept').innerText = ev.accept || 'None';
        document.getElementById('ins-referer').innerText = ev.referer || 'Direct / None';
        
        const sigContainer = document.getElementById('ins-signals');
        sigContainer.innerHTML = '';
        if (ev.signals && ev.signals.length) {{
            ev.signals.forEach(s => {{
                const el = document.createElement('span');
                el.className = 'signal-chip';
                el.innerText = s;
                sigContainer.appendChild(el);
            }});
        }} else {{
            sigContainer.innerHTML = '<span style="color:var(--fg-dim);">No automation heuristic rules triggered.</span>';
        }}
        document.getElementById('inspector-drawer').classList.add('open');
    }}

    function closeInspector() {{
        document.getElementById('inspector-drawer').classList.remove('open');
    }}

    document.addEventListener('keydown', (e) => {{
        if (e.target.tagName === 'INPUT') return;
        if (e.key >= '1' && e.key <= '6') {{
            toggleMaximize('pane-' + e.key);
        }} else if (e.key === 'Escape') {{
            closeInspector();
            document.querySelectorAll('.pane').forEach(p => p.classList.remove('maximized'));
        }}
    }});

    function runCommand(val) {{
        val = val.trim();
        if (!val) return;
        if (val === ':crt' || val === ':scanlines') {{
            toggleScanlines();
        }} else if (val.startsWith(':theme')) {{
            const parts = val.split(' ');
            if (parts[1]) setPalette(parts[1].toLowerCase());
        }} else if (val === ':export') {{
            window.location.href = '/api/export.ndjson?limit=500';
        }} else if (val.startsWith(':filter')) {{
            const filterTerm = val.replace(':filter', '').trim().toLowerCase();
            document.querySelectorAll('.wire-row').forEach(row => {{
                const lvl = (row.getAttribute('data-level') || '').toLowerCase();
                const st = row.getAttribute('data-status');
                const m = (row.getAttribute('data-method') || '').toLowerCase();
                if (lvl === filterTerm || st === filterTerm || m === filterTerm || filterTerm === 'all') {{
                    row.style.display = 'flex';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }} else if (val === ':help') {{
            alert('OBSERVATORY HUD COMMANDS:\\n:theme [matrix|crimson|amber|alert|optic|hazard]\\n:scanlines - Toggle CRT raster overlay\\n:filter [high|med|low|404|get|post|all]\\n:export - Download NDJSON stream\\n[1-6] - Maximize pane\\n[ESC] - Close drawer / reset grid');
        }}
        document.getElementById('cli-input').value = '';
    }}

    // Auto-refresh countdown
    let countdown = 15;
    setInterval(() => {{
        countdown--;
        const el = document.getElementById('obs-refresh-countdown');
        if (el) el.innerText = countdown + 's';
        if (countdown <= 0) {{
            countdown = 15;
            window.location.reload();
        }}
    }}, 1000);
    </script>
    """

    body = f"""
    <!-- Master Tactical Header -->
    <header id="obs-header">
        <div class="header-left">
            <span class="brand-title">
                <span>WWW2 OBSERVATORY</span>
            </span>
            <span class="live-badge"><span class="pulse-dot"></span> PASSIVE INGEST (WAL)</span>
            <span class="pill">HOST: www2.onnwee.me</span>
            <span class="pill" style="color:var(--cyan); background:rgba(79,214,200,0.12);">NODE: almaz-01</span>
        </div>
        <div class="header-right">
            <div class="palette-group">
                <button class="palette-btn" data-theme="matrix" onclick="setPalette('matrix')" title="Acid Green & Deep Purple">MATRIX</button>
                <button class="palette-btn" data-theme="crimson" onclick="setPalette('crimson')" title="Tactical Carmine & Red">CRIMSON</button>
                <button class="palette-btn" data-theme="amber" onclick="setPalette('amber')" title="Warm Monolith Amber & Gold">AMBER</button>
                <button class="palette-btn" data-theme="alert" onclick="setPalette('alert')" title="High Threat Alert Contrast">ALERT</button>
                <button class="palette-btn" data-theme="optic" onclick="setPalette('optic')" title="Cyan Optics & Cobalt Blue">OPTIC</button>
                <button class="palette-btn" data-theme="hazard" onclick="setPalette('hazard')" title="Safety Orange & Crimson">HAZARD</button>
                <button onclick="toggleScanlines()" class="palette-btn" style="border-color:var(--yellow); color:var(--yellow);">CRT</button>
            </div>
            <a href="/api/summary" target="_blank" class="action-btn" title="Inspect API summary JSON">API</a>
            <a href="/api/export.ndjson?limit=500" class="action-btn" title="Export recent 500 rows in NDJSON">EXPORT</a>
            <span class="refresh-timer" id="obs-refresh-countdown" onclick="window.location.reload()" title="Click to refresh now">15s</span>
        </div>
    </header>

    {alert_banner}

    <!-- Top KPI Telemetry Ribbon -->
    <div class="kpi-ribbon">
        <div class="kpi-node kpi-traffic">
            <div class="kpi-head"><span>Inbound Telemetry</span><span>24H</span></div>
            <div class="kpi-val">{s.get('requests', 0):,}</div>
            <div class="kpi-sub">Total access records parsed</div>
        </div>
        <div class="kpi-node kpi-clients">
            <div class="kpi-head"><span>Distinct Clients</span><span>HMAC</span></div>
            <div class="kpi-val" style="color:var(--cyan);">{s.get('clients', 0):,}</div>
            <div class="kpi-sub">{s.get('sessions', 0)} navigation sessions</div>
        </div>
        <div class="kpi-node kpi-auto">
            <div class="kpi-head"><span>Automation Index</span><span>HEURISTIC</span></div>
            <div class="kpi-val" style="color:var(--orange);">{s.get('high_auto', 0)} <span style="font-size:14px; color:var(--fg-dim);">bot / {s.get('med_auto', 0)} probe</span></div>
            <div class="kpi-sub">{s.get('low_auto', 0)} standard human requests</div>
        </div>
        <div class="kpi-node kpi-security">
            <div class="kpi-head"><span>Relay &amp; Writes</span><span>PUBLIC</span></div>
            <div class="kpi-val" style="color:var(--magenta);">{s.get('writes', 0):,}</div>
            <div class="kpi-sub">{sys_st.get('relay_records', 0)} scrubbed application events</div>
        </div>
        <div class="kpi-node kpi-bandwidth">
            <div class="kpi-head"><span>Payload Delivered</span><span>EGRESS</span></div>
            <div class="kpi-val" style="color:var(--blue);">{fmt_bytes(s.get('total_bytes', 0))}</div>
            <div class="kpi-sub">Zero tracking overhead</div>
        </div>
    </div>

    <!-- 6-Pane Bento Grid -->
    <div class="hud-layout">
        <!-- PANE 1 -->
        <div class="pane" id="pane-1">
            <div class="pane-header">
                <span class="pane-title"><span class="pane-hotkey">1</span> HOURLY TELEMETRY OSCILLOSCOPE</span>
                <div class="pane-controls"><button onclick="toggleMaximize('pane-1')">[MAX]</button></div>
            </div>
            <div class="pane-content">
                <div class="oscilloscope-box">
                    {oscilloscope}
                </div>
                <div style="display:flex; justify-content:space-between; font-size:11px; padding:2px 4px;">
                    <span>VOLUME: <strong style="color:var(--accent);">{s.get('requests', 0):,}</strong></span>
                    <span>HIGH AUTOMATION: <strong style="color:var(--bright-red);">{s.get('high_auto', 0)}</strong></span>
                    <span>BANDWIDTH: <strong style="color:var(--cyan);">{fmt_bytes(s.get('total_bytes', 0))}</strong></span>
                </div>
            </div>
        </div>

        <!-- PANE 2 -->
        <div class="pane" id="pane-2">
            <div class="pane-header">
                <span class="pane-title"><span class="pane-hotkey">2</span> REAL-TIME PACKET WIRE</span>
                <div class="pane-controls"><button onclick="toggleMaximize('pane-2')">[MAX]</button></div>
            </div>
            <div class="pane-content wire-feed-scroll" id="wire-feed">
                {"".join(wire_rows)}
            </div>
        </div>

        <!-- PANE 3 -->
        <div class="pane" id="pane-3">
            <div class="pane-header">
                <span class="pane-title"><span class="pane-hotkey">3</span> BEHAVIORAL HEURISTIC VECTORS</span>
                <div class="pane-controls"><button onclick="toggleMaximize('pane-3')">[MAX]</button></div>
            </div>
            <div class="pane-content">
                <div style="font-size:10px; color:var(--fg-dim); margin-bottom:8px; text-transform:uppercase;">
                    Automated Probing Signals &middot; {len(sig)} Vectors Evaluated
                </div>
                {"".join(gauge_rows)}
            </div>
        </div>

        <!-- PANE 4 -->
        <div class="pane" id="pane-4">
            <div class="pane-header">
                <span class="pane-title"><span class="pane-hotkey">4</span> SESSION TOPOLOGY &amp; TRAILS</span>
                <div class="pane-controls"><button onclick="toggleMaximize('pane-4')">[MAX]</button></div>
            </div>
            <div class="pane-content">
                {"".join(session_trees) or '<div style="color:var(--fg-dim);">No active reconstructed sessions.</div>'}
            </div>
        </div>

        <!-- PANE 5 -->
        <div class="pane" id="pane-5">
            <div class="pane-header">
                <span class="pane-title"><span class="pane-hotkey">5</span> APPLICATION RELAY STREAM (PUBLIC WRITES)</span>
                <div class="pane-controls"><button onclick="toggleMaximize('pane-5')">[MAX]</button></div>
            </div>
            <div class="pane-content">
                {"".join(wiretap_items) or '<div style="color:var(--fg-dim);">No intercepted relay events.</div>'}
            </div>
        </div>

        <!-- PANE 6 -->
        <div class="pane" id="pane-6">
            <div class="pane-header">
                <span class="pane-title"><span class="pane-hotkey">6</span> OBSERVATORY NODE DIAGNOSTICS</span>
                <div class="pane-controls"><button onclick="toggleMaximize('pane-6')">[MAX]</button></div>
            </div>
            <div class="pane-content">
                <div class="diag-row">
                    <span class="diag-label">OBSERVATORY NODE:</span>
                    <span class="diag-val" style="color:var(--accent);">almaz.onnwee.me (SOYUZ)</span>
                </div>
                <div class="diag-row">
                    <span class="diag-label">MONITORED TARGET:</span>
                    <span class="diag-val" style="color:var(--cyan);">www2.onnwee.me</span>
                </div>
                <div class="diag-row">
                    <span class="diag-label">STORAGE ENGINE:</span>
                    <span class="diag-val" style="color:var(--green);">SQLite 3 (WAL ACTIVE)</span>
                </div>
                <div class="diag-row">
                    <span class="diag-label">DATABASE SIZE:</span>
                    <span class="diag-val" style="color:var(--yellow);">{fmt_bytes(sys_st.get('db_size_bytes', 0))}</span>
                </div>
                <div class="diag-row">
                    <span class="diag-label">ACCESS LOG RECORDS:</span>
                    <span class="diag-val">{sys_st.get('access_records', 0):,}</span>
                </div>
                <div class="diag-row">
                    <span class="diag-label">RELAY WRITE EVENTS:</span>
                    <span class="diag-val" style="color:var(--magenta);">{sys_st.get('relay_records', 0):,}</span>
                </div>
                <div class="diag-row">
                    <span class="diag-label">PSEUDONYM INTEGRITY:</span>
                    <span class="diag-val" style="color:var(--accent);">HMAC-SHA256 KEY LOADED</span>
                </div>
                <div class="diag-row">
                    <span class="diag-label">PRIVACY AIRGAP:</span>
                    <span class="diag-val" style="color:var(--fg-bright);">RAW IP DISCARDED AT INGEST</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Slide-over Packet Inspector Drawer -->
    <div id="inspector-drawer">
        <div class="drawer-header">
            <span class="drawer-title">PACKET TELEMETRY INSPECTOR</span>
            <button class="drawer-close" onclick="closeInspector()">&times;</button>
        </div>
        <div class="drawer-body">
            <div class="drawer-section">
                <div class="drawer-section-title">Request Attributes</div>
                <div class="drawer-field"><span class="field-name">Timestamp:</span><span class="field-val" id="ins-ts"></span></div>
                <div class="drawer-field"><span class="field-name">Method:</span><span class="field-val" id="ins-method"></span></div>
                <div class="drawer-field"><span class="field-name">Path:</span><span class="field-val" id="ins-path"></span></div>
                <div class="drawer-field"><span class="field-name">Status:</span><span class="field-val" id="ins-status"></span></div>
                <div class="drawer-field"><span class="field-name">Response Bytes:</span><span class="field-val" id="ins-bytes"></span></div>
            </div>
            <div class="drawer-section">
                <div class="drawer-section-title">Pseudonym Identity (HMAC-SHA256)</div>
                <div class="drawer-field"><span class="field-name">Client Hash:</span><span class="field-val" id="ins-client"></span></div>
                <div class="drawer-field"><span class="field-name">Session Hash:</span><span class="field-val" id="ins-session"></span></div>
            </div>
            <div class="drawer-section">
                <div class="drawer-section-title">Automation Heuristic Evaluation</div>
                <div class="drawer-field"><span class="field-name">Calculated Score:</span><span class="field-val" id="ins-score"></span></div>
                <div style="margin-top:6px;"><span class="field-name" style="color:var(--fg-dim);">Triggered Rules:</span></div>
                <div class="signals-list" id="ins-signals"></div>
            </div>
            <div class="drawer-section">
                <div class="drawer-section-title">HTTP Request Headers</div>
                <div class="drawer-field"><span class="field-name">User-Agent:</span><span class="field-val" id="ins-ua"></span></div>
                <div class="drawer-field"><span class="field-name">Accept:</span><span class="field-val" id="ins-accept"></span></div>
                <div class="drawer-field"><span class="field-name">Referer:</span><span class="field-val" id="ins-referer"></span></div>
            </div>
        </div>
    </div>

    <!-- TACTICAL COMMAND PROMPT -->
    <div class="cli-bar">
        <span class="cli-prompt">&gt;</span>
        <input type="text" id="cli-input" class="cli-input" placeholder="Type :theme matrix, :theme crimson, :theme amber, :theme optic, :filter high, :crt, :help and press Enter" onkeydown="if(event.key==='Enter') runCommand(this.value)">
        <span class="cli-help-pill">PRESS ENTER TO EXECUTE &middot; HOTKEYS [1-6] MAXIMIZE &middot; [ESC] RESET</span>
    </div>
    {script}
    """
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>www2 observatory — Telemetry HUD</title><style>{DASHBOARD_CSS}</style></head><body class='scanlines' data-theme='matrix'>{body}</body></html>"
