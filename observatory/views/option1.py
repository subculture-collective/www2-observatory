from __future__ import annotations

import html
import json
import sqlite3

from .components import (
    auto_badge,
    fmt_bytes,
    fmt_rel_ts,
    fmt_short_ts,
    fmt_ts,
    method_badge,
    render_switcher,
    status_badge,
    svg_donut_chart,
    svg_stacked_bar_chart,
)
from .. import analytics

CSS_OPTION_1 = """
:root {
    --bg: #07090e;
    --panel: #0d121c;
    --panel-border: #1a2333;
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --cyan: #06b6d4;
    --green: #10b981;
    --amber: #f59e0b;
    --red: #ef4444;
    --mono: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, monospace;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: var(--mono);
    font-size: 13px;
    line-height: 1.45;
}
#obs-switcher-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #090d16;
    border-bottom: 1px solid #1e293b;
    padding: 8px 18px;
    font-size: 13px;
    position: sticky;
    top: 0;
    z-index: 1000;
}
.obs-switcher-left { display: flex; align-items: center; gap: 12px; }
.obs-live-indicator { display: flex; align-items: center; gap: 6px; font-weight: 700; color: #10b981; font-size: 11px; letter-spacing: 0.05em; }
.obs-pulse { width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.85); } 100% { opacity: 1; transform: scale(1); } }
.obs-host-pill { background: #172033; color: #94a3b8; padding: 2px 8px; border-radius: 6px; font-size: 11px; border: 1px solid #293548; }
.obs-switcher-tabs { display: flex; gap: 4px; }
.switcher-item { color: #94a3b8; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; transition: all 0.15s ease; border: 1px solid transparent; font-family: -apple-system, sans-serif; }
.switcher-item:hover { color: #f8fafc; background: #151d2d; }
.switcher-item-active { color: #06b6d4; background: #0c212b; border-color: #0891b2; }
.obs-switcher-right { display: flex; align-items: center; gap: 8px; font-size: 11px; }
.obs-btn-sm { background: #1e293b; color: #cbd5e1; text-decoration: none; padding: 3px 8px; border-radius: 4px; border: 1px solid #334155; }
.obs-btn-sm:hover { background: #334155; color: #fff; }
.obs-timer { color: #64748b; }

.app-wrapper { max-width: 1600px; margin: 0 auto; padding: 20px 24px 60px; }
.telemetry-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #090e17;
    border: 1px solid var(--panel-border);
    padding: 14px 20px;
    border-radius: 8px;
    margin-bottom: 20px;
}
.banner-title { display: flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 700; color: #f8fafc; letter-spacing: 0.05em; }
.banner-title .chip { font-size: 10px; background: rgba(6, 182, 212, 0.15); color: var(--cyan); border: 1px solid var(--cyan); padding: 2px 6px; border-radius: 4px; }
.banner-stats { display: flex; gap: 24px; font-size: 12px; color: var(--text-dim); }
.banner-stats strong { color: #f8fafc; }

.kpi-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
}
.kpi-card {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    padding: 14px 18px;
    position: relative;
    overflow: hidden;
}
.kpi-card::after { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 2px; background: var(--cyan); opacity: 0.3; }
.kpi-label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
.kpi-value { font-size: 26px; font-weight: 700; color: #f8fafc; display: flex; align-items: baseline; gap: 8px; }
.kpi-sub { font-size: 11px; color: #64748b; margin-top: 4px; }

.chart-grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
}
@media (max-width: 1024px) {
    .chart-grid { grid-template-columns: 1fr; }
}
.chart-card {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    padding: 16px;
}
.chart-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}
.chart-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--cyan); }
.chart-legend { display: flex; gap: 12px; font-size: 11px; color: var(--text-dim); }
.chart-legend span { display: inline-flex; align-items: center; gap: 5px; }
.dot-human { width: 8px; height: 8px; border-radius: 2px; background: #10b981; }
.dot-cli { width: 8px; height: 8px; border-radius: 2px; background: #f59e0b; }
.dot-bot { width: 8px; height: 8px; border-radius: 2px; background: #ef4444; }

.toolbar-strip {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    background: #0a0f19;
    border: 1px solid var(--panel-border);
    padding: 10px 16px;
    border-radius: 6px;
    margin-bottom: 12px;
}
.toolbar-filters { display: flex; align-items: center; gap: 12px; }
.search-input {
    background: #06090f;
    border: 1px solid #253348;
    color: #e2e8f0;
    padding: 6px 12px;
    border-radius: 4px;
    font-family: var(--mono);
    font-size: 12px;
    width: 260px;
}
.search-input:focus { outline: none; border-color: var(--cyan); }
.filter-select {
    background: #06090f;
    border: 1px solid #253348;
    color: #e2e8f0;
    padding: 6px 10px;
    border-radius: 4px;
    font-family: var(--mono);
    font-size: 12px;
}
.filter-select:focus { outline: none; border-color: var(--cyan); }

.table-container {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    overflow-x: auto;
    margin-bottom: 28px;
}
table.telemetry-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}
table.telemetry-table th {
    background: #090d16;
    color: var(--text-dim);
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid var(--panel-border);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.05em;
}
table.telemetry-table td {
    padding: 9px 12px;
    border-bottom: 1px solid #141c2b;
    vertical-align: middle;
}
table.telemetry-table tr.log-row {
    cursor: pointer;
    transition: background 0.15s ease;
}
table.telemetry-table tr.log-row:hover {
    background: #131c2c;
}
.cell-code { font-family: var(--mono); word-break: break-all; }
.badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; text-align: center; }

/* Slide-over packet inspector drawer */
#inspector-drawer {
    position: fixed;
    top: 0;
    right: -520px;
    width: 500px;
    height: 100vh;
    background: #090e18;
    border-left: 1px solid #223249;
    box-shadow: -10px 0 30px rgba(0,0,0,0.6);
    z-index: 2000;
    transition: right 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
}
#inspector-drawer.open { right: 0; }
.drawer-header {
    padding: 16px 20px;
    border-bottom: 1px solid #1e2d42;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #0d1424;
}
.drawer-title { font-size: 14px; font-weight: 700; color: var(--cyan); letter-spacing: 0.05em; }
.drawer-close { background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer; padding: 4px; }
.drawer-close:hover { color: #fff; }
.drawer-body { padding: 20px; overflow-y: auto; flex: 1; font-size: 12px; }
.drawer-section { margin-bottom: 20px; }
.drawer-section-title { font-size: 11px; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; margin-bottom: 8px; border-bottom: 1px solid #1a2538; padding-bottom: 4px; }
.drawer-field { display: flex; justify-content: space-between; padding: 4px 0; gap: 10px; }
.drawer-field .field-name { color: #94a3b8; flex-shrink: 0; }
.drawer-field .field-val { color: #f8fafc; word-break: break-all; text-align: right; }
.signals-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.signal-chip { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); padding: 2px 6px; border-radius: 4px; font-size: 11px; }

.section-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 28px;
}
@media (max-width: 900px) {
    .section-grid { grid-template-columns: 1fr; }
}
.session-card {
    background: #090e17;
    border: 1px solid var(--panel-border);
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 10px;
}
.session-header { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 11px; color: var(--text-dim); }
.session-trail-flow { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 11px; }
.step-chip { background: #131c2d; border: 1px solid #23334c; padding: 2px 6px; border-radius: 4px; }
.step-arrow { color: var(--cyan); }
"""

def render_option1(conn: sqlite3.Connection) -> str:
    s = analytics.summary(conn, 24)
    tl = analytics.timeline(conn, 24)
    recent_events = analytics.recent(conn, 60)
    status_counts = analytics.status_distribution(conn, 24)
    method_counts = analytics.method_distribution(conn, 24)
    sess = analytics.sessions(conn, 168, 15)
    sig = analytics.signals(conn, 168)

    # Donut data for status
    status_donut_items = []
    for sc in status_counts:
        code = sc.get("status", 200)
        cnt = sc.get("count", 0)
        c = "#10b981" if 200 <= code < 300 else ("#06b6d4" if 300 <= code < 400 else ("#f59e0b" if 400 <= code < 500 else "#ef4444"))
        status_donut_items.append((str(code), cnt, c))

    status_donut = svg_donut_chart(status_donut_items, size=130)
    timeline_chart = svg_stacked_bar_chart(tl, width=900, height=160)

    # Table rows
    table_rows = []
    events_json = []
    for r in recent_events:
        score = r.get("automation_score", 0)
        level = r.get("automation_level", "low")
        st = r.get("status", 200)
        m = r.get("method", "GET")
        p = r.get("path", "")
        q = r.get("query", "")
        full_p = f"{p}?{q}" if q else p
        cid = r.get("client_id", "")[:12]
        ua = r.get("user_agent", "")[:60]
        ts_str = fmt_short_ts(r.get("ts", 0))

        # Store JSON for drawer inspector
        row_dict = {
            "ts": fmt_ts(r.get("ts", 0)),
            "rel_ts": fmt_rel_ts(r.get("ts", 0)),
            "method": m,
            "path": p,
            "query": q,
            "status": st,
            "score": score,
            "level": level,
            "client_id": r.get("client_id", ""),
            "session_id": r.get("session_id", ""),
            "user_agent": r.get("user_agent", ""),
            "accept": r.get("accept_header", ""),
            "referer": r.get("referer", ""),
            "bytes": fmt_bytes(r.get("response_bytes", 0)),
            "signals": json.loads(r.get("signals_json", "[]")),
        }
        events_json.append(row_dict)

        table_rows.append(f"""
        <tr class="log-row" data-idx="{len(events_json)-1}" onclick="inspectEvent({len(events_json)-1})">
            <td style="color:#64748b;">{ts_str}</td>
            <td>{auto_badge(score, level)}</td>
            <td>{method_badge(m)}</td>
            <td class="cell-code" style="color:#f8fafc;">{html.escape(full_p)}</td>
            <td>{status_badge(st)}</td>
            <td class="cell-code" style="color:#38bdf8;">{html.escape(cid)}</td>
            <td class="cell-code" style="color:#94a3b8; max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{html.escape(ua)}</td>
        </tr>
        """)

    # Session trail cards
    sess_cards = []
    for s_item in sess[:6]:
        trail = s_item.get("trail", "") or ""
        steps = trail.split(" → ")
        chips = []
        for i, step in enumerate(steps[:6]):
            if i > 0:
                chips.append('<span class="step-arrow">&rarr;</span>')
            chips.append(f'<span class="step-chip">{html.escape(step)}</span>')
        if len(steps) > 6:
            chips.append(f'<span class="step-chip dim">+{len(steps)-6} more</span>')

        sess_cards.append(f"""
        <div class="session-card">
            <div class="session-header">
                <span>SESSION: <code>{html.escape(s_item.get('session_id', '')[:12])}</code></span>
                <span>{s_item.get('requests', 0)} requests &middot; max auto: <strong>{s_item.get('max_automation', 0)}</strong> &middot; {fmt_rel_ts(s_item.get('started', 0))}</span>
            </div>
            <div class="session-trail-flow">
                {"".join(chips)}
            </div>
        </div>
        """)

    switcher = render_switcher("/1")

    script = f"""
    <script>
    const EVENTS_DATA = {json.dumps(events_json)};
    function inspectEvent(idx) {{
        const ev = EVENTS_DATA[idx];
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
            sigContainer.innerHTML = '<span style="color:#64748b;">No automation heuristic signals triggered.</span>';
        }}
        document.getElementById('inspector-drawer').classList.add('open');
    }}
    function closeInspector() {{
        document.getElementById('inspector-drawer').classList.remove('open');
    }}
    function filterLogs() {{
        const q = document.getElementById('search-box').value.toLowerCase();
        const m = document.getElementById('method-filter').value;
        const l = document.getElementById('level-filter').value;
        const rows = document.querySelectorAll('table.telemetry-table tr.log-row');
        rows.forEach(r => {{
            const idx = parseInt(r.getAttribute('data-idx'));
            const ev = EVENTS_DATA[idx];
            if (!ev) return;
            const matchQ = !q || ev.path.toLowerCase().includes(q) || ev.user_agent.toLowerCase().includes(q) || ev.client_id.toLowerCase().includes(q);
            const matchM = !m || ev.method === m;
            const matchL = !l || ev.level === l;
            r.style.display = (matchQ && matchM && matchL) ? '' : 'none';
        }});
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
    {switcher}
    <div class="app-wrapper">
        <div class="telemetry-banner">
            <div class="banner-title">
                <span>DEEP SPACE TELEMETRY OPS</span>
                <span class="chip">NODE 01</span>
                <span class="chip" style="color:var(--green); border-color:var(--green); background:rgba(16,185,129,0.1);">LIVE PASSIVE STREAM</span>
            </div>
            <div class="banner-stats">
                <span>INGESTION: <strong>NOMINAL</strong></span>
                <span>RETENTION: <strong>INDEFINITE</strong></span>
                <span>PRIVACY: <strong>HMAC-256</strong></span>
            </div>
        </div>

        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-label">24h Requests</div>
                <div class="kpi-value">{s.get('requests', 0):,}</div>
                <div class="kpi-sub">Total inbound telemetry</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Unique Clients</div>
                <div class="kpi-value">{s.get('clients', 0):,}</div>
                <div class="kpi-sub">Pseudonymous signatures</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Reconstructed Sessions</div>
                <div class="kpi-value">{s.get('sessions', 0):,}</div>
                <div class="kpi-sub">Navigation chains</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Automation Index</div>
                <div class="kpi-value" style="color:var(--amber);">{s.get('avg_score', 0)} <span style="font-size:14px;color:#94a3b8;">/ 12 avg</span></div>
                <div class="kpi-sub">{s.get('high_auto', 0)} high &middot; {s.get('med_auto', 0)} med &middot; {s.get('low_auto', 0)} low</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Bandwidth Egress</div>
                <div class="kpi-value">{fmt_bytes(s.get('total_bytes', 0))}</div>
                <div class="kpi-sub">Total response payload</div>
            </div>
        </div>

        <div class="chart-grid">
            <div class="chart-card">
                <div class="chart-card-header">
                    <span class="chart-title">24h Hourly Traffic Spectrum</span>
                    <div class="chart-legend">
                        <span><span class="dot-human"></span> Human (low)</span>
                        <span><span class="dot-cli"></span> Probe (med)</span>
                        <span><span class="dot-bot"></span> Bot (high)</span>
                    </div>
                </div>
                {timeline_chart}
            </div>

            <div class="chart-card" style="display:flex; flex-direction:column; justify-content:space-between;">
                <div class="chart-card-header">
                    <span class="chart-title">Status Code Ratio</span>
                </div>
                <div style="display:flex; align-items:center; justify-content:space-around; padding:10px 0;">
                    {status_donut}
                    <div style="font-size:12px; display:flex; flex-direction:column; gap:6px;">
                        {''.join(f'<div><span style="color:#94a3b8;">HTTP {sc.get("status")}:</span> <strong>{sc.get("count")}</strong></div>' for sc in status_counts[:4])}
                    </div>
                </div>
                <div style="border-top:1px solid var(--panel-border); padding-top:10px; font-size:11px; color:#64748b;">
                    Methods: {' &middot; '.join(f'<strong>{m.get("method")}</strong>: {m.get("count")}' for m in method_counts[:4])}
                </div>
            </div>
        </div>

        <div class="toolbar-strip">
            <div class="toolbar-filters">
                <input type="text" id="search-box" class="search-input" placeholder="Search path, client, user agent..." oninput="filterLogs()">
                <select id="method-filter" class="filter-select" onchange="filterLogs()">
                    <option value="">METHOD: ALL</option>
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="OPTIONS">OPTIONS</option>
                    <option value="HEAD">HEAD</option>
                    <option value="PUT">PUT</option>
                </select>
                <select id="level-filter" class="filter-select" onchange="filterLogs()">
                    <option value="">AUTOMATION: ALL</option>
                    <option value="low">Low (Human)</option>
                    <option value="medium">Medium (CLI/Probe)</option>
                    <option value="high">High (Bot/Agent)</option>
                </select>
            </div>
            <div style="font-size:11px; color:#64748b;">
                Click any row to open slide-over Packet Telemetry Inspector
            </div>
        </div>

        <div class="table-container">
            <table class="telemetry-table">
                <thead>
                    <tr>
                        <th style="width:100px;">Time</th>
                        <th style="width:130px;">Automation</th>
                        <th style="width:80px;">Method</th>
                        <th>Path &amp; Query</th>
                        <th style="width:80px;">Status</th>
                        <th style="width:130px;">Client Hash</th>
                        <th>User Agent</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(table_rows)}
                </tbody>
            </table>
        </div>

        <div class="section-grid">
            <div class="chart-card">
                <div class="chart-card-header">
                    <span class="chart-title">Reconstructed Session Trails</span>
                </div>
                <div>
                    {"".join(sess_cards)}
                </div>
            </div>

            <div class="chart-card">
                <div class="chart-card-header">
                    <span class="chart-title">Behavioral Signals &amp; Probing Vectors</span>
                </div>
                <table style="width:100%; border-collapse:collapse; font-size:12px;">
                    <thead>
                        <tr style="border-bottom:1px solid var(--panel-border); color:#64748b; text-align:left;">
                            <th style="padding:6px 0;">Signal Name</th>
                            <th style="padding:6px 0; text-align:right;">Events</th>
                            <th style="padding:6px 0; text-align:right;">Clients</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(f'<tr style="border-bottom:1px solid #141c2b;"><td style="padding:8px 0; color:#38bdf8;"><code>{html.escape(sg.get("signal",""))}</code></td><td style="padding:8px 0; text-align:right; font-weight:700;">{sg.get("events",0)}</td><td style="padding:8px 0; text-align:right; color:#94a3b8;">{sg.get("clients",0)}</td></tr>' for sg in sig[:8])}
                    </tbody>
                </table>
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
                <div class="drawer-section-title">Client Identity (HMAC-256 Pseudonym)</div>
                <div class="drawer-field"><span class="field-name">Client Hash:</span><span class="field-val" id="ins-client"></span></div>
                <div class="drawer-field"><span class="field-name">Session Hash:</span><span class="field-val" id="ins-session"></span></div>
            </div>
            <div class="drawer-section">
                <div class="drawer-section-title">Automation Heuristic Engine</div>
                <div class="drawer-field"><span class="field-name">Assessment:</span><span class="field-val" id="ins-score"></span></div>
                <div style="margin-top:6px;"><span class="field-name">Triggered Rules:</span></div>
                <div class="signals-list" id="ins-signals"></div>
            </div>
            <div class="drawer-section">
                <div class="drawer-section-title">HTTP Headers</div>
                <div class="drawer-field"><span class="field-name">User-Agent:</span><span class="field-val" id="ins-ua"></span></div>
                <div class="drawer-field"><span class="field-name">Accept:</span><span class="field-val" id="ins-accept"></span></div>
                <div class="drawer-field"><span class="field-name">Referer:</span><span class="field-val" id="ins-referer"></span></div>
            </div>
        </div>
    </div>
    {script}
    """
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>www2 observatory — Telemetry Ops (Option 1)</title><style>{CSS_OPTION_1}</style></head><body>{body}</body></html>"
