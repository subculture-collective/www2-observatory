from __future__ import annotations

import html
import sqlite3

from .components import (
    auto_badge,
    fmt_bytes,
    fmt_rel_ts,
    render_switcher,
    svg_sparkline,
    svg_spline_area_chart,
)
from .. import analytics

CSS_OPTION_2 = """
:root {
    --bg: #090d16;
    --card-bg: #111726;
    --card-hover: #161e31;
    --border: #1e293b;
    --border-focus: #38bdf8;
    --text: #f8fafc;
    --text-muted: #94a3b8;
    --accent: #38bdf8;
    --accent-glow: rgba(56, 189, 248, 0.15);
    --font-sans: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
    --font-mono: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, monospace;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-sans);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
}
#obs-switcher-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #090d16;
    border-bottom: 1px solid var(--border);
    padding: 8px 18px;
    font-size: 13px;
    position: sticky;
    top: 0;
    z-index: 1000;
}
.obs-switcher-left { display: flex; align-items: center; gap: 12px; }
.obs-live-indicator { display: flex; align-items: center; gap: 6px; font-weight: 700; color: #10b981; font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.05em; }
.obs-pulse { width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.85); } 100% { opacity: 1; transform: scale(1); } }
.obs-host-pill { background: #172033; color: #94a3b8; padding: 2px 8px; border-radius: 6px; font-family: var(--font-mono); font-size: 11px; border: 1px solid #293548; }
.obs-switcher-tabs { display: flex; gap: 4px; }
.switcher-item { color: #94a3b8; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; transition: all 0.15s ease; border: 1px solid transparent; }
.switcher-item:hover { color: #f8fafc; background: #151d2d; }
.switcher-item-active { color: #38bdf8; background: #132238; border-color: #0284c7; }
.obs-switcher-right { display: flex; align-items: center; gap: 8px; font-family: var(--font-mono); font-size: 11px; }
.obs-btn-sm { background: #1e293b; color: #cbd5e1; text-decoration: none; padding: 3px 8px; border-radius: 4px; border: 1px solid #334155; }
.obs-btn-sm:hover { background: #334155; color: #fff; }
.obs-timer { color: #64748b; }

.exec-container { max-width: 1500px; margin: 0 auto; padding: 24px 28px 60px; }
.exec-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 24px;
}
.exec-title-area h1 { font-size: 26px; font-weight: 700; margin: 0 0 4px; letter-spacing: -0.02em; }
.exec-title-area p { font-size: 14px; color: var(--text-muted); margin: 0; }
.exec-controls { display: flex; align-items: center; gap: 12px; }
.timeframe-group { display: flex; background: #101624; border: 1px solid var(--border); border-radius: 8px; padding: 3px; }
.tf-btn {
    background: none; border: none; color: var(--text-muted); padding: 5px 12px; font-size: 12px; font-weight: 500;
    border-radius: 6px; cursor: pointer; transition: all 0.15s ease;
}
.tf-btn:hover { color: #fff; }
.tf-btn.active { background: #1e293b; color: #fff; font-weight: 600; }

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
}
.kpi-card-exec {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}
.kpi-info .kpi-label { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
.kpi-info .kpi-num { font-size: 32px; font-weight: 800; letter-spacing: -0.03em; line-height: 1; }
.kpi-info .kpi-delta { font-size: 12px; margin-top: 8px; display: flex; align-items: center; gap: 4px; font-weight: 500; }
.delta-pos { color: #10b981; }
.delta-neutral { color: #94a3b8; }

.tab-nav {
    display: flex;
    gap: 8px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
    padding-bottom: 4px;
}
.tab-link {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 14px;
    font-weight: 500;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s ease;
}
.tab-link:hover { color: #fff; background: rgba(255,255,255,0.04); }
.tab-link.active { color: var(--accent); background: var(--accent-glow); font-weight: 600; }

.tab-panel { display: none; }
.tab-panel.active { display: block; }

.card-box {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
}
.card-box-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
}
.card-box-title { font-size: 16px; font-weight: 600; color: #f8fafc; margin: 0; }
.card-box-sub { font-size: 13px; color: var(--text-muted); margin-top: 2px; }

.split-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}
@media (max-width: 960px) {
    .split-2 { grid-template-columns: 1fr; }
}

table.exec-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
table.exec-table th {
    text-align: left;
    padding: 10px 14px;
    color: var(--text-muted);
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--border);
}
table.exec-table td {
    padding: 12px 14px;
    border-bottom: 1px solid #182235;
    vertical-align: middle;
}
table.exec-table tr:hover td {
    background: var(--card-hover);
}
.progress-bar-bg { background: #1e293b; border-radius: 4px; height: 6px; width: 100px; overflow: hidden; }
.progress-bar-fill { background: var(--accent); height: 100%; border-radius: 4px; }
.badge { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 11px; font-weight: 600; font-family: var(--font-mono); }
"""

def render_option2(conn: sqlite3.Connection) -> str:
    s = analytics.summary(conn, 24)
    tl = analytics.timeline(conn, 24)
    paths = analytics.top_paths(conn, 24, 10)
    refs = analytics.referrers(conn, 168, 10)
    uas = analytics.ua_breakdown(conn, 24, 8)
    sess = analytics.sessions(conn, 168, 12)
    wr = analytics.writes(conn, 15)

    # Sparkline numbers
    req_points = [float(b.get("total", 0)) for b in tl] if tl else [1.0, 1.0]
    spark_req = svg_sparkline(req_points, width=80, height=26, stroke="#38bdf8")

    area_chart = svg_spline_area_chart(tl, width=960, height=180)

    # Top paths rows
    max_hits = max((p.get("hits", 1) for p in paths), default=1)
    path_rows = []
    for p in paths:
        hits = p.get("hits", 0)
        pct = int((hits / max_hits) * 100)
        path_rows.append(f"""
        <tr>
            <td style="font-family:var(--font-mono); font-weight:500; color:#f8fafc;">{html.escape(p.get('path',''))}</td>
            <td style="font-weight:700;">{hits}</td>
            <td style="color:var(--text-muted);">{p.get('clients',0)}</td>
            <td>
                <div style="display:flex; align-items:center; gap:8px;">
                    <div class="progress-bar-bg"><div class="progress-bar-fill" style="width:{pct}%;"></div></div>
                    <span style="font-size:11px; color:#64748b;">{pct}%</span>
                </div>
            </td>
        </tr>
        """)

    # Referrers
    ref_rows = []
    for r in refs:
        ref_rows.append(f"""
        <tr>
            <td style="font-family:var(--font-mono); color:#38bdf8;">{html.escape(r.get('referer_host',''))}</td>
            <td style="font-weight:700;">{r.get('hits',0)}</td>
            <td style="color:var(--text-muted);">{r.get('clients',0)}</td>
        </tr>
        """)

    # User-Agents
    ua_rows = []
    for u in uas:
        score = u.get("avg_auto", 0)
        level = "high" if score >= 6 else ("medium" if score >= 3 else "low")
        ua_rows.append(f"""
        <tr>
            <td style="font-family:var(--font-mono); font-size:12px; color:#cbd5e1; max-width:340px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{html.escape(u.get('user_agent',''))}</td>
            <td style="font-weight:700;">{u.get('hits',0)}</td>
            <td>{auto_badge(int(score), level)}</td>
        </tr>
        """)

    # Sessions
    sess_rows = []
    for s_item in sess:
        sess_rows.append(f"""
        <tr>
            <td style="color:var(--text-muted); font-size:12px;">{fmt_rel_ts(s_item.get('started',0))}</td>
            <td style="font-family:var(--font-mono); color:#38bdf8;"><code>{html.escape(s_item.get('session_id','')[:12])}</code></td>
            <td style="font-weight:700;">{s_item.get('requests',0)}</td>
            <td>{s_item.get('unique_paths',0)}</td>
            <td style="font-family:var(--font-mono); font-size:11px; color:#94a3b8; max-width:360px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{html.escape(s_item.get('trail',''))}</td>
        </tr>
        """)

    # Write events
    write_rows = []
    for w in wr:
        write_rows.append(f"""
        <tr>
            <td style="color:var(--text-muted); font-size:12px;">{fmt_rel_ts(w.get('ts',0))}</td>
            <td><span class="badge" style="background:#1e293b; color:#38bdf8;">{html.escape(w.get('event',''))}</span></td>
            <td style="font-family:var(--font-mono); font-size:12px;">{html.escape(w.get('path',''))}</td>
            <td style="color:#e2e8f0; font-size:12px;">{html.escape(w.get('content','')[:120])}</td>
        </tr>
        """)

    switcher = render_switcher("/2")

    script = """
    <script>
    function setTab(tabId) {
        document.querySelectorAll('.tab-link').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
        document.querySelector('[data-tab="' + tabId + '"]').classList.add('active');
        document.getElementById('tab-' + tabId).classList.add('active');
    }
    </script>
    """

    body = f"""
    {switcher}
    <div class="exec-container">
        <div class="exec-header">
            <div class="exec-title-area">
                <h1>Executive Intelligence Brief</h1>
                <p>Audience behavior, automated crawlers, and resource telemetry for <code>www2.onnwee.me</code></p>
            </div>
            <div class="exec-controls">
                <div class="timeframe-group">
                    <button class="tf-btn" onclick="window.location.search='?hours=1'">1h</button>
                    <button class="tf-btn active" onclick="window.location.search='?hours=24'">24h</button>
                    <button class="tf-btn" onclick="window.location.search='?hours=168'">7d</button>
                    <button class="tf-btn" onclick="window.location.search='?hours=720'">30d</button>
                </div>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card-exec">
                <div class="kpi-info">
                    <div class="kpi-label">Total Inbound Requests</div>
                    <div class="kpi-num">{s.get('requests', 0):,}</div>
                    <div class="kpi-delta delta-pos">&uarr; Active Volume</div>
                </div>
                {spark_req}
            </div>
            <div class="kpi-card-exec">
                <div class="kpi-info">
                    <div class="kpi-label">Unique Clients</div>
                    <div class="kpi-num">{s.get('clients', 0):,}</div>
                    <div class="kpi-delta delta-neutral">{s.get('sessions', 0)} sessions formed</div>
                </div>
            </div>
            <div class="kpi-card-exec">
                <div class="kpi-info">
                    <div class="kpi-label">Automated Probing Ratio</div>
                    <div class="kpi-num" style="color:#f59e0b;">{int((s.get('high_auto', 0) / max(1, s.get('requests', 1))) * 100)}%</div>
                    <div class="kpi-delta delta-neutral">{s.get('high_auto', 0)} high / {s.get('med_auto', 0)} probe</div>
                </div>
            </div>
            <div class="kpi-card-exec">
                <div class="kpi-info">
                    <div class="kpi-label">Bandwidth Delivered</div>
                    <div class="kpi-num">{fmt_bytes(s.get('total_bytes', 0))}</div>
                    <div class="kpi-delta delta-pos">Zero Tracking Overhead</div>
                </div>
            </div>
        </div>

        <div class="tab-nav">
            <button class="tab-link active" data-tab="traffic" onclick="setTab('traffic')">Traffic &amp; Engagement</button>
            <button class="tab-link" data-tab="agents" onclick="setTab('agents')">Agent &amp; Bot Intelligence</button>
            <button class="tab-link" data-tab="journeys" onclick="setTab('journeys')">Visitor Journeys</button>
            <button class="tab-link" data-tab="relays" onclick="setTab('relays')">Relay Write Feed</button>
        </div>

        <!-- TAB 1: TRAFFIC -->
        <div id="tab-traffic" class="tab-panel active">
            <div class="card-box">
                <div class="card-box-header">
                    <div>
                        <h3 class="card-box-title">Request Volume Over Time</h3>
                        <div class="card-box-sub">Smoothed hourly request distribution across the selected window</div>
                    </div>
                </div>
                {area_chart}
            </div>

            <div class="split-2">
                <div class="card-box">
                    <div class="card-box-header">
                        <h3 class="card-box-title">Top Visited Resources</h3>
                    </div>
                    <table class="exec-table">
                        <thead>
                            <tr>
                                <th>Path</th>
                                <th>Hits</th>
                                <th>Clients</th>
                                <th>Share</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(path_rows)}
                        </tbody>
                    </table>
                </div>

                <div class="card-box">
                    <div class="card-box-header">
                        <h3 class="card-box-title">Referrer Attribution (7d)</h3>
                    </div>
                    <table class="exec-table">
                        <thead>
                            <tr>
                                <th>Referrer Host</th>
                                <th>Inbound Hits</th>
                                <th>Clients</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(ref_rows) or '<tr><td colspan="3" style="color:#64748b;">No external referrers logged yet.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 2: AGENTS -->
        <div id="tab-agents" class="tab-panel">
            <div class="card-box">
                <div class="card-box-header">
                    <div>
                        <h3 class="card-box-title">User-Agent Profiling &amp; Automation Scoring</h3>
                        <div class="card-box-sub">Behavioral fingerprinting based on HTTP headers, representation requests, and probe methods</div>
                    </div>
                </div>
                <table class="exec-table">
                    <thead>
                        <tr>
                            <th>User Agent Signature</th>
                            <th>Hits</th>
                            <th>Automation Assessment</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(ua_rows)}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- TAB 3: JOURNEYS -->
        <div id="tab-journeys" class="tab-panel">
            <div class="card-box">
                <div class="card-box-header">
                    <h3 class="card-box-title">Reconstructed Navigation Journeys</h3>
                </div>
                <table class="exec-table">
                    <thead>
                        <tr>
                            <th>Started</th>
                            <th>Session ID</th>
                            <th>Requests</th>
                            <th>Unique Paths</th>
                            <th>Navigation Trail</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(sess_rows)}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- TAB 4: RELAYS -->
        <div id="tab-relays" class="tab-panel">
            <div class="card-box">
                <div class="card-box-header">
                    <h3 class="card-box-title">Public Write &amp; Relay Submissions</h3>
                </div>
                <table class="exec-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Event Type</th>
                            <th>Target Path</th>
                            <th>Scrubbed Content Preview</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(write_rows) or '<tr><td colspan="4" style="color:#64748b;">No relay events recorded yet.</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    {script}
    """
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>www2 observatory — Executive Brief (Option 2)</title><style>{CSS_OPTION_2}</style></head><body>{body}</body></html>"
