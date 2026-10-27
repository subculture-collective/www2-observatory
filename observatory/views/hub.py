from __future__ import annotations

import html
import sqlite3

from .components import fmt_bytes, fmt_ts, render_switcher
from .. import analytics

HUB_CSS = """
:root {
    --bg: #07090e;
    --card-bg: #0e131f;
    --card-border: #1e293b;
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --accent: #38bdf8;
    --font-mono: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, monospace;
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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
    border-bottom: 1px solid #1e293b;
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

.hub-container { max-width: 1400px; margin: 0 auto; padding: 32px 24px 64px; }
.hub-hero { text-align: center; max-width: 840px; margin: 20px auto 44px; }
.hub-tag { display: inline-block; padding: 4px 12px; border-radius: 20px; background: rgba(56, 189, 248, 0.12); color: #38bdf8; font-size: 12px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 14px; border: 1px solid rgba(56, 189, 248, 0.25); font-family: var(--font-mono); }
.hub-hero h1 { font-size: 40px; font-weight: 800; letter-spacing: -0.025em; margin: 0 0 16px; color: #f8fafc; line-height: 1.15; }
.hub-hero p { font-size: 17px; color: #94a3b8; line-height: 1.6; margin: 0; }

.hub-metrics-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 40px;
}
.hub-metric-box {
    background: #0d121d;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 16px;
    display: flex;
    flex-direction: column;
}
.hub-metric-box .label { font-size: 12px; color: #64748b; font-family: var(--font-mono); text-transform: uppercase; margin-bottom: 4px; }
.hub-metric-box .val { font-size: 26px; font-weight: 700; color: #f8fafc; font-family: var(--font-mono); }
.hub-metric-box .sub { font-size: 11px; color: #10b981; margin-top: 4px; }

.hub-options-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(580px, 1fr));
    gap: 24px;
    margin-bottom: 48px;
}
@media (max-width: 768px) {
    .hub-options-grid { grid-template-columns: 1fr; }
}

.opt-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 28px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}
.opt-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 30px rgba(0,0,0,0.4);
}
.opt-1:hover { border-color: #06b6d4; }
.opt-2:hover { border-color: #38bdf8; }
.opt-3:hover { border-color: #8b5cf6; }
.opt-4:hover { border-color: #22c55e; }

.opt-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.opt-num { font-family: var(--font-mono); font-size: 13px; font-weight: 700; padding: 2px 8px; border-radius: 4px; }
.opt-1 .opt-num { color: #06b6d4; background: rgba(6, 182, 212, 0.15); border: 1px solid rgba(6, 182, 212, 0.3); }
.opt-2 .opt-num { color: #38bdf8; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); }
.opt-3 .opt-num { color: #a78bfa; background: rgba(167, 139, 250, 0.15); border: 1px solid rgba(167, 139, 250, 0.3); }
.opt-4 .opt-num { color: #22c55e; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); }

.opt-badge { font-size: 11px; padding: 3px 8px; border-radius: 12px; background: #1e293b; color: #94a3b8; font-family: var(--font-mono); }
.opt-title { font-size: 24px; font-weight: 700; color: #f8fafc; margin: 0 0 6px; }
.opt-tagline { font-size: 14px; color: #94a3b8; margin: 0 0 16px; font-weight: 400; }
.opt-desc { font-size: 14px; color: #cbd5e1; line-height: 1.6; margin-bottom: 20px; }

.opt-feature-list { list-style: none; padding: 0; margin: 0 0 24px; display: flex; flex-direction: column; gap: 8px; }
.opt-feature-list li { font-size: 13px; color: #94a3b8; display: flex; align-items: center; gap: 8px; }
.opt-feature-list li strong { color: #e2e8f0; }
.opt-bullet { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.opt-1 .opt-bullet { background: #06b6d4; }
.opt-2 .opt-bullet { background: #38bdf8; }
.opt-3 .opt-bullet { background: #a78bfa; }
.opt-4 .opt-bullet { background: #22c55e; }

.opt-card-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #1e293b; padding-top: 18px; margin-top: auto; }
.opt-persona { font-size: 12px; color: #64748b; font-family: var(--font-mono); }
.opt-launch-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.2s ease;
    font-family: var(--font-mono);
}
.opt-1 .opt-launch-btn { background: #0891b2; color: #ffffff; }
.opt-1 .opt-launch-btn:hover { background: #06b6d4; }
.opt-2 .opt-launch-btn { background: #0284c7; color: #ffffff; }
.opt-2 .opt-launch-btn:hover { background: #38bdf8; }
.opt-3 .opt-launch-btn { background: #7c3aed; color: #ffffff; }
.opt-3 .opt-launch-btn:hover { background: #8b5cf6; }
.opt-4 .opt-launch-btn { background: #16a34a; color: #ffffff; }
.opt-4 .opt-launch-btn:hover { background: #22c55e; }

.hub-spec-section {
    background: #0c101a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 24px;
    margin-top: 24px;
}
.hub-spec-section h3 { font-size: 16px; margin: 0 0 16px; color: #f8fafc; font-family: var(--font-mono); }
table.spec-table { width: 100%; border-collapse: collapse; font-size: 13px; font-family: var(--font-mono); }
table.spec-table th, table.spec-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #1e293b; }
table.spec-table th { color: #64748b; font-weight: 500; }
table.spec-table td.dim { color: #64748b; }
"""

def render_hub(conn: sqlite3.Connection) -> str:
    s = analytics.summary(conn, 24)
    sys_st = analytics.system_stats(conn)
    
    switcher = render_switcher("/")
    
    body = f"""
    {switcher}
    <div class="hub-container">
        <div class="hub-hero">
            <span class="hub-tag">Passive Server-Side Surveillance</span>
            <h1>www2-observatory Frontend Overhaul</h1>
            <p>
                A completely invisible observatory monitoring server access logs for <code>www2.onnwee.me</code>.
                Below are <strong>4 distinct frontend archetypes and interaction philosophies</strong> built to inspect
                visitor behaviors, automated probe sequences, and emergent inter-agent conventions.
            </p>
        </div>

        <div class="hub-metrics-strip">
            <div class="hub-metric-box">
                <span class="label">24h Requests</span>
                <span class="val">{s.get('requests', 0):,}</span>
                <span class="sub">{s.get('low_auto', 0)} human &middot; {s.get('med_auto', 0)} cli &middot; {s.get('high_auto', 0)} bot</span>
            </div>
            <div class="hub-metric-box">
                <span class="label">Distinct Clients</span>
                <span class="val">{s.get('clients', 0):,}</span>
                <span class="sub">Keyed HMAC Pseudonyms</span>
            </div>
            <div class="hub-metric-box">
                <span class="label">Reconstructed Sessions</span>
                <span class="val">{s.get('sessions', 0):,}</span>
                <span class="sub">Path Trail Chains</span>
            </div>
            <div class="hub-metric-box">
                <span class="label">Write Probes & Relay</span>
                <span class="val">{s.get('writes', 0):,}</span>
                <span class="sub">{sys_st.get('relay_records', 0)} Public Relay Events</span>
            </div>
            <div class="hub-metric-box">
                <span class="label">Database State</span>
                <span class="val">{fmt_bytes(sys_st.get('db_size_bytes', 0))}</span>
                <span class="sub">WAL Mode &middot; Integrity OK</span>
            </div>
        </div>

        <div class="hub-options-grid">
            <!-- OPTION 1 -->
            <div class="opt-card opt-1">
                <div>
                    <div class="opt-card-header">
                        <span class="opt-num">OPTION 1</span>
                        <span class="opt-badge">Real-Time Operations</span>
                    </div>
                    <h2 class="opt-title">Telemetry Ops: Mission Control</h2>
                    <p class="opt-tagline">Dark Sci-Fi Mission Control & Real-Time Signal Telemetry</p>
                    <p class="opt-desc">
                        Built like a deep space radio telescope receiver. High-density dark telemetry grid with live pulse indicators, 
                        an interactive 24h stacked SVG spectrum of automation levels, heuristic radar meters, and a slide-over 
                        <strong>Packet Telemetry Inspector Drawer</strong> that dissects individual request headers and heuristic triggers.
                    </p>
                    <ul class="opt-feature-list">
                        <li><span class="opt-bullet"></span><strong>Stacked SVG Hourly Spectrum:</strong> Interactive bar/area histogram of traffic by automation tier.</li>
                        <li><span class="opt-bullet"></span><strong>Slide-over Packet Inspector:</strong> Click any log row to inspect headers, query params, and rule score breakdowns.</li>
                        <li><span class="opt-bullet"></span><strong>Session Trajectory Graph:</strong> Step-by-step visitor progression paths with duration metrics.</li>
                        <li><span class="opt-bullet"></span><strong>Live Stream Controls:</strong> Auto-refresh rate switcher, method/status filtering, and export tools.</li>
                    </ul>
                </div>
                <div class="opt-card-footer">
                    <span class="opt-persona">TARGET: Network & Operations Engineers</span>
                    <a href="/1" class="opt-launch-btn">Launch Option 1 &rarr;</a>
                </div>
            </div>

            <!-- OPTION 2 -->
            <div class="opt-card opt-2">
                <div>
                    <div class="opt-card-header">
                        <span class="opt-num">OPTION 2</span>
                        <span class="opt-badge">Executive Brief</span>
                    </div>
                    <h2 class="opt-title">Executive Intelligence Brief</h2>
                    <p class="opt-tagline">Modern SaaS Analytics (Linear / Stripe Radar Aesthetic)</p>
                    <p class="opt-desc">
                        An ultra-refined, elegant dashboard designed for executive clarity and content engagement. 
                        Features frosted glass card surfaces, sparkline metrics with period-over-period delta comparisons, 
                        and a clean tabbed navigation dividing high-level traffic from agent security intelligence.
                    </p>
                    <ul class="opt-feature-list">
                        <li><span class="opt-bullet"></span><strong>Executive KPI Ribbon:</strong> Sparklines showing 24h trends, bounce rate, and data egress.</li>
                        <li><span class="opt-bullet"></span><strong>Multi-Tab Architecture:</strong> Smooth tabs for Traffic, Agent Intelligence, Visitor Journeys, and Relays.</li>
                        <li><span class="opt-bullet"></span><strong>Smooth Spline Area Chart:</strong> High-resolution SVG curve of request volumes and peaks.</li>
                        <li><span class="opt-bullet"></span><strong>Timeframe Engine:</strong> Instant filtering by 1h, 24h, 7d, and 30d presets.</li>
                    </ul>
                </div>
                <div class="opt-card-footer">
                    <span class="opt-persona">TARGET: Site Owners & Product Strategists</span>
                    <a href="/2" class="opt-launch-btn">Launch Option 2 &rarr;</a>
                </div>
            </div>

            <!-- OPTION 3 -->
            <div class="opt-card opt-3">
                <div>
                    <div class="opt-card-header">
                        <span class="opt-num">OPTION 3</span>
                        <span class="opt-badge">Protocol Research</span>
                    </div>
                    <h2 class="opt-title">Agent & Protocol Forensics Lab</h2>
                    <p class="opt-tagline">Research Workbench for Machine Behavior & Emergent Conventions</p>
                    <p class="opt-desc">
                        Built around the observatory's core scientific mission: discovering autonomous AI crawlers and tracking 
                        emergent coordination conventions across distinct clients. Features an <strong>Emergent Convention Matrix</strong>, 
                        an interactive <strong>Session Timeline Step Player</strong>, and a Cryptographic Payload Vault.
                    </p>
                    <ul class="opt-feature-list">
                        <li><span class="opt-bullet"></span><strong>Emergent Convention Tracker:</strong> Token dictionary tracking phrases across multiple distinct clients.</li>
                        <li><span class="opt-bullet"></span><strong>Machine Probe Matrix:</strong> Scoring distribution curve and discovery sequence breakdown (OPTIONS, well-known).</li>
                        <li><span class="opt-bullet"></span><strong>Session Step Replay:</strong> Interactive stepper showing inter-request latency to differentiate humans vs bots.</li>
                        <li><span class="opt-bullet"></span><strong>Relay Cryptographic Vault:</strong> SHA-256 content hashes, PII scrubbing verification, and diff views.</li>
                    </ul>
                </div>
                <div class="opt-card-footer">
                    <span class="opt-persona">TARGET: AI Researchers & Security Analysts</span>
                    <a href="/3" class="opt-launch-btn">Launch Option 3 &rarr;</a>
                </div>
            </div>

            <!-- OPTION 4 -->
            <div class="opt-card opt-4">
                <div>
                    <div class="opt-card-header">
                        <span class="opt-num">OPTION 4</span>
                        <span class="opt-badge">Cyberpunk TUI</span>
                    </div>
                    <h2 class="opt-title">Cyberpunk Operations HUD & TUI</h2>
                    <p class="opt-tagline">Bloomberg Terminal Meets Retro-Futuristic CRT Hacker HUD</p>
                    <p class="opt-desc">
                        A keyboard-first, ultra-dense 6-pane tiling console with phosphor CRT aesthetics. 
                        Includes an interactive terminal command prompt (<code>:filter high</code>, <code>:export</code>, <code>:crt</code>), 
                        oscilloscope request waveforms, Unicode session trees, and hotkeys 1-6 to maximize any pane into full screen.
                    </p>
                    <ul class="opt-feature-list">
                        <li><span class="opt-bullet"></span><strong>6-Pane Bento Tiling:</strong> Scope, Wire Feed, Probe Vectors, Session Tree, Relay Wiretap, Node Stats.</li>
                        <li><span class="opt-bullet"></span><strong>Interactive Command Prompt:</strong> Type commands (:filter, :export, :time, :crt) directly into the HUD.</li>
                        <li><span class="opt-bullet"></span><strong>Keyboard Maximizer:</strong> Press 1-6 to focus any pane; press Esc to return to multi-pane HUD.</li>
                        <li><span class="opt-bullet"></span><strong>CRT Phosphor & Scanlines:</strong> Authentic retro CRT glow with toggleable phosphor scanlines.</li>
                    </ul>
                </div>
                <div class="opt-card-footer">
                    <span class="opt-persona">TARGET: Terminal Hackers & Minimalists</span>
                    <a href="/4" class="opt-launch-btn">Launch Option 4 &rarr;</a>
                </div>
            </div>
        </div>

        <div class="hub-spec-section">
            <h3>Architectural Comparison Matrix</h3>
            <div style="overflow-x:auto;">
                <table class="spec-table">
                    <thead>
                        <tr>
                            <th>Attribute</th>
                            <th>Option 1: Telemetry Ops</th>
                            <th>Option 2: Executive Brief</th>
                            <th>Option 3: Agent Forensics</th>
                            <th>Option 4: Cyberpunk TUI</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Primary Focus</strong></td>
                            <td>Real-time streaming & packets</td>
                            <td>Audience & content KPIs</td>
                            <td>Autonomous agents & conventions</td>
                            <td>High-density TUI monitoring</td>
                        </tr>
                        <tr>
                            <td><strong>Visual Language</strong></td>
                            <td>Dark mission telemetry & cyan glow</td>
                            <td>SaaS glassmorphism & slate</td>
                            <td>Deep navy, violet & cyan lab</td>
                            <td>Phosphor green CRT & scanlines</td>
                        </tr>
                        <tr>
                            <td><strong>Data Density</strong></td>
                            <td>High (inspectors, drawers)</td>
                            <td>Balanced (executive cards)</td>
                            <td>Deep analytical (matrix tables)</td>
                            <td>Maximum (tiled bento terminal)</td>
                        </tr>
                        <tr>
                            <td><strong>Navigation</strong></td>
                            <td>Single-page live telemetry</td>
                            <td>Multi-tab clean brief</td>
                            <td>Specialized research modules</td>
                            <td>Hotkeys (1-6) + command bar</td>
                        </tr>
                        <tr>
                            <td><strong>Charting</strong></td>
                            <td>Stacked automation spectrum</td>
                            <td>Spline volume area curve</td>
                            <td>Score distribution curve</td>
                            <td>SVG oscilloscope waveform</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>www2 observatory — Overhaul Showcase</title><style>{HUB_CSS}</style></head><body>{body}</body></html>"
