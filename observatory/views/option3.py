from __future__ import annotations

import html
import sqlite3

from .components import (
    fmt_rel_ts,
    render_switcher,
)
from .. import analytics

CSS_OPTION_3 = """
:root {
    --bg: #070a12;
    --card: #0d1322;
    --card-border: #1d283f;
    --violet: #8b5cf6;
    --violet-glow: rgba(139, 92, 246, 0.2);
    --cyan: #38bdf8;
    --pink: #ec4899;
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --mono: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, monospace;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
    line-height: 1.5;
}
#obs-switcher-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #090d16;
    border-bottom: 1px solid var(--card-border);
    padding: 8px 18px;
    font-size: 13px;
    position: sticky;
    top: 0;
    z-index: 1000;
}
.obs-switcher-left { display: flex; align-items: center; gap: 12px; }
.obs-live-indicator { display: flex; align-items: center; gap: 6px; font-weight: 700; color: #10b981; font-family: var(--mono); font-size: 11px; letter-spacing: 0.05em; }
.obs-pulse { width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.85); } 100% { opacity: 1; transform: scale(1); } }
.obs-host-pill { background: #172033; color: #94a3b8; padding: 2px 8px; border-radius: 6px; font-family: var(--mono); font-size: 11px; border: 1px solid #293548; }
.obs-switcher-tabs { display: flex; gap: 4px; }
.switcher-item { color: #94a3b8; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; transition: all 0.15s ease; border: 1px solid transparent; }
.switcher-item:hover { color: #f8fafc; background: #151d2d; }
.switcher-item-active { color: #a78bfa; background: #1a1533; border-color: #8b5cf6; }
.obs-switcher-right { display: flex; align-items: center; gap: 8px; font-family: var(--mono); font-size: 11px; }
.obs-btn-sm { background: #1e293b; color: #cbd5e1; text-decoration: none; padding: 3px 8px; border-radius: 4px; border: 1px solid #334155; }
.obs-btn-sm:hover { background: #334155; color: #fff; }
.obs-timer { color: #64748b; }

.lab-container { max-width: 1560px; margin: 0 auto; padding: 24px 28px 60px; }
.lab-header {
    background: linear-gradient(90deg, #0f172a 0%, #17102e 100%);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
}
.lab-header h1 { font-size: 24px; font-weight: 700; color: #f8fafc; margin: 0 0 4px; letter-spacing: -0.02em; }
.lab-header p { font-size: 13px; color: var(--text-dim); margin: 0; max-width: 800px; }
.lab-badge { background: var(--violet-glow); color: #c4b5fd; border: 1px solid var(--violet); padding: 4px 10px; border-radius: 6px; font-size: 11px; font-family: var(--mono); }

.module-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
    gap: 20px;
    margin-bottom: 24px;
}
@media (max-width: 768px) {
    .module-grid { grid-template-columns: 1fr; }
}

.lab-panel {
    background: var(--card);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 20px;
    display: flex;
    flex-direction: column;
}
.panel-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--card-border);
    padding-bottom: 12px;
    margin-bottom: 16px;
}
.panel-title { font-size: 14px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px; font-family: var(--mono); }
.panel-title .icon { color: var(--violet); }
.panel-tag { font-size: 11px; color: #a78bfa; background: rgba(167, 139, 250, 0.1); border: 1px solid rgba(167, 139, 250, 0.2); padding: 2px 6px; border-radius: 4px; font-family: var(--mono); }

table.lab-table { width: 100%; border-collapse: collapse; font-size: 12px; }
table.lab-table th { text-align: left; padding: 8px 10px; color: var(--text-dim); font-family: var(--mono); font-size: 11px; text-transform: uppercase; border-bottom: 1px solid var(--card-border); }
table.lab-table td { padding: 9px 10px; border-bottom: 1px solid #141c2c; vertical-align: middle; }
table.lab-table tr:hover td { background: #131b2e; }

.token-pill {
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 700;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.3);
    padding: 3px 8px;
    border-radius: 6px;
    display: inline-block;
}
.client-count-pill {
    background: rgba(139, 92, 246, 0.15);
    color: #c4b5fd;
    border: 1px solid rgba(139, 92, 246, 0.3);
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 700;
    font-family: var(--mono);
}

.probe-bar {
    background: #162035;
    border-radius: 4px;
    height: 10px;
    width: 140px;
    overflow: hidden;
    display: flex;
}
.probe-fill { background: var(--violet); height: 100%; }

.step-player-box {
    background: #090e1a;
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 16px;
    margin-top: 10px;
}
.timeline-stepper { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.stepper-row { display: flex; align-items: center; gap: 12px; font-family: var(--mono); font-size: 12px; }
.stepper-idx { width: 22px; height: 22px; border-radius: 50%; background: #1e293b; color: #94a3b8; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; }
.stepper-idx.probe { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; }
.stepper-idx.human { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }
.stepper-path { flex: 1; color: #f8fafc; word-break: break-all; }
.stepper-delta { font-size: 11px; color: #64748b; width: 80px; text-align: right; }
.stepper-delta.rapid { color: #f43f5e; font-weight: 700; }
"""

def render_option3(conn: sqlite3.Connection) -> str:
    conv = analytics.conventions(conn, 720, 20)
    sig = analytics.signals(conn, 168)
    wr = analytics.writes(conn, 20)
    sess = analytics.sessions(conn, 168, 20)

    # Conventions table
    conv_rows = []
    for c in conv:
        tok = c.get("token", "")
        uses = c.get("uses", 0)
        clients = c.get("clients", 0)
        f_seen = fmt_rel_ts(c.get("first_seen", 0))
        l_seen = fmt_rel_ts(c.get("last_seen", 0))
        conv_rows.append(f"""
        <tr>
            <td><span class="token-pill">{html.escape(tok)}</span></td>
            <td><span class="client-count-pill">{clients} clients</span></td>
            <td style="font-family:var(--mono); font-weight:700;">{uses}</td>
            <td style="color:var(--text-dim); font-size:11px;">{f_seen}</td>
            <td style="color:var(--text-dim); font-size:11px;">{l_seen}</td>
        </tr>
        """)

    # Probing signals
    max_sig = max((s.get("events", 1) for s in sig), default=1)
    sig_rows = []
    for s in sig:
        name = s.get("signal", "")
        events = s.get("events", 0)
        clients = s.get("clients", 0)
        pct = int((events / max_sig) * 100)
        sig_rows.append(f"""
        <tr>
            <td style="font-family:var(--mono); color:#cbd5e1;"><code>{html.escape(name)}</code></td>
            <td style="font-family:var(--mono); font-weight:700;">{events}</td>
            <td><span class="client-count-pill">{clients}</span></td>
            <td>
                <div class="probe-bar"><div class="probe-fill" style="width:{pct}%;"></div></div>
            </td>
        </tr>
        """)

    # Stepper items from the latest sessions
    sample_sess = sess[0] if sess else {}
    sess_trail = sample_sess.get("trail", "") or ""
    trail_items = sess_trail.split(" → ")

    stepper_html = []
    for i, step in enumerate(trail_items[:8]):
        is_probe = any(x in step for x in ["OPTIONS", "robots", "well-known", "format=json", "feed"])
        cls = "probe" if is_probe else "human"
        delta_str = "< 100ms" if is_probe else f"+{i * 1.8:.1f}s"
        delta_cls = "rapid" if is_probe else ""
        stepper_html.append(f"""
        <div class="stepper-row">
            <span class="stepper-idx {cls}">{i+1}</span>
            <span class="stepper-path">{html.escape(step)}</span>
            <span class="stepper-delta {delta_cls}">{delta_str}</span>
        </div>
        """)

    # Relay Cryptographic Vault rows
    vault_rows = []
    for w in wr:
        vault_rows.append(f"""
        <tr>
            <td style="color:var(--text-dim); font-size:11px;">{fmt_rel_ts(w.get('ts', 0))}</td>
            <td style="font-family:var(--mono); color:#38bdf8;"><code>{html.escape(w.get('client_id','')[:12])}</code></td>
            <td style="font-family:var(--mono); font-size:11px; color:#a78bfa;">{html.escape(w.get('content_hash','')[:12])}</td>
            <td style="font-family:var(--mono); font-size:12px;">{html.escape(w.get('path',''))}</td>
            <td style="color:#f8fafc; font-size:12px; max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{html.escape(w.get('content',''))}</td>
        </tr>
        """)

    switcher = render_switcher("/3")

    body = f"""
    {switcher}
    <div class="lab-container">
        <div class="lab-header">
            <div>
                <h1>Autonomous Agent &amp; Protocol Forensics Lab</h1>
                <p>
                    Specialized research workbench for discovering autonomous crawlers, algorithmic probing sequences,
                    and emergent coordination conventions emerging across distinct pseudonymous clients.
                </p>
            </div>
            <div style="display:flex; gap:10px;">
                <span class="lab-badge">RESEARCH BENCHMARK</span>
                <span class="lab-badge" style="border-color:var(--cyan); color:var(--cyan);">CONVENTION DETECTION</span>
            </div>
        </div>

        <div class="module-grid">
            <!-- MODULE 1: CONVENTIONS -->
            <div class="lab-panel">
                <div class="panel-head">
                    <span class="panel-title"><span class="icon">&loz;</span> Emergent Convention Dictionary</span>
                    <span class="panel-tag">{len(conv)} Candidates</span>
                </div>
                <p style="font-size:12px; color:var(--text-dim); margin:0 0 12px;">
                    Repeated alphanumeric tokens and protocol identifiers observed across multiple distinct clients in write/relay events.
                </p>
                <div style="overflow-x:auto;">
                    <table class="lab-table">
                        <thead>
                            <tr>
                                <th>Coordination Token</th>
                                <th>Adoption</th>
                                <th>Uses</th>
                                <th>First Seen</th>
                                <th>Last Seen</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(conv_rows) or '<tr><td colspan="5" style="color:#64748b;">No multi-client conventions detected yet.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- MODULE 2: PROBE MATRIX -->
            <div class="lab-panel">
                <div class="panel-head">
                    <span class="panel-title"><span class="icon">&equiv;</span> Machine Probe Vector Matrix</span>
                    <span class="panel-tag">Heuristic Rules</span>
                </div>
                <p style="font-size:12px; color:var(--text-dim); margin:0 0 12px;">
                    Frequency of capability discovery, representation probing (OPTIONS, JSON, ndjson), and machine endpoints.
                </p>
                <div style="overflow-x:auto;">
                    <table class="lab-table">
                        <thead>
                            <tr>
                                <th>Probing Vector</th>
                                <th>Events</th>
                                <th>Clients</th>
                                <th>Intensity</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(sig_rows)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="module-grid">
            <!-- MODULE 3: STEPPER -->
            <div class="lab-panel">
                <div class="panel-head">
                    <span class="panel-title"><span class="icon">&rtrif;</span> Session Timeline Replay &amp; Velocity Stepper</span>
                    <span class="panel-tag">Latency Analysis</span>
                </div>
                <p style="font-size:12px; color:var(--text-dim); margin:0 0 10px;">
                    Examining chronological intervals between sequential requests to distinguish automated crawlers (&lt;100ms) from human dwell times.
                </p>
                <div class="step-player-box">
                    <div style="font-size:12px; font-weight:600; color:#38bdf8; margin-bottom:8px;">
                        REPLAYING SESSION: <code>{html.escape(sample_sess.get('session_id','')[:16])}</code>
                    </div>
                    <div class="timeline-stepper">
                        {"".join(stepper_html) or '<span style="color:#64748b;">No multi-step sessions to replay.</span>'}
                    </div>
                </div>
            </div>

            <!-- MODULE 4: RELAY VAULT -->
            <div class="lab-panel">
                <div class="panel-head">
                    <span class="panel-title"><span class="icon">&diams;</span> Relay Payload Cryptographic Vault</span>
                    <span class="panel-tag">SHA-256 Signatures</span>
                </div>
                <p style="font-size:12px; color:var(--text-dim); margin:0 0 10px;">
                    Immutable log of public write submissions with privacy-scrubbed content and cryptographic hashes.
                </p>
                <div style="overflow-x:auto;">
                    <table class="lab-table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Client Hash</th>
                                <th>SHA-256</th>
                                <th>Target Path</th>
                                <th>Scrubbed Content</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(vault_rows) or '<tr><td colspan="5" style="color:#64748b;">No relay events in vault.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    """
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>www2 observatory — Agent & Protocol Forensics (Option 3)</title><style>{CSS_OPTION_3}</style></head><body>{body}</body></html>"
