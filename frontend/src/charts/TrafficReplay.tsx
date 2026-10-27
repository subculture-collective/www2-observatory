import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { DiagnosticsReport } from "../api/types.ts";
import { useSettings } from "../lib/settings.tsx";
import { n, pct } from "../lib/format.ts";
import { Panel } from "../ui/Panel.tsx";

/** Replay aggregate buckets, not invented packets or inferred actors. */
export function TrafficReplay({ report }: { report: DiagnosticsReport }) {
  const { motion } = useSettings();
  const buckets = useMemo(() => {
    const step = report.hours > 168 ? 86400 : 3600,
      end = Math.floor(Date.now() / 1000 / step) * step,
      count = Math.ceil((report.hours * 3600) / step) + 1;
    const map = new Map(
      report.timeline.map((b) => [
        Date.parse(
          b.bucket.replace(" ", "T") +
            (b.bucket.length === 10 ? "T00:00:00Z" : ":00Z"),
        ) / 1000,
        b,
      ]),
    );
    return Array.from({ length: count }, (_, i) => {
      const ts = end - (count - 1 - i) * step;
      return {
        ts,
        step,
        requests: 0,
        probes: 0,
        missing: 0,
        server_errors: 0,
        sources: 0,
        ...map.get(ts),
      };
    });
  }, [report]);
  const busiest = buckets.reduce(
    (best, b, i) => (b.requests > buckets[best].requests ? i : best),
    0,
  );
  const [index, setIndex] = useState(busiest);
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    setIndex(busiest);
    setPlaying(false);
  }, [report.hours]); // Reset only when the selected window changes.
  useEffect(() => {
    if (!motion) setPlaying(false);
  }, [motion]);
  useEffect(() => {
    if (!playing || !motion) return;
    const timer = window.setInterval(
      () => setIndex((i) => (i + 1) % buckets.length),
      1000,
    );
    return () => clearInterval(timer);
  }, [playing, motion, buckets.length]);
  const current = buckets[Math.min(index, buckets.length - 1)],
    max = Math.max(1, ...buckets.map((b) => b.requests));
  const choose = (i: number) => {
    setPlaying(false);
    setIndex(i);
  };
  return (
    <Panel
      title="Traffic replay // event horizon"
      id="replay"
      span={4}
      chip={`${report.hours > 168 ? "daily" : "hourly"} buckets · recorded aggregates`}
      className="replay-panel"
    >
      <div className="replay-layout">
        <div className="replay-console">
          <span className="eyebrow">
            {playing ? "REPLAY IN PROGRESS" : "REPLAY STANDBY"}
          </span>
          <b className="replay-date">
            {new Date(current.ts * 1000)
              .toISOString()
              .slice(0, report.hours > 168 ? 10 : 16)
              .replace("T", " ")}
            <small>UTC</small>
          </b>
          <div className="seg" role="group" aria-label="Replay controls">
            <button
              disabled={!motion || !report.timeline.length}
              onClick={() => setPlaying((p) => !p)}
              aria-pressed={playing}
            >
              {playing ? "Ⅱ pause" : "▶ play"}
            </button>
            <button
              onClick={() => choose(Math.max(0, index - 1))}
              disabled={index === 0}
            >
              ← step
            </button>
            <button
              onClick={() => choose(Math.min(buckets.length - 1, index + 1))}
              disabled={index >= buckets.length - 1}
            >
              step →
            </button>
            <button onClick={() => choose(busiest)}>busiest bucket</button>
          </div>
          <p className="note">
            {motion
              ? "One bucket per second. Playback is a view of recorded counts, not a live packet stream."
              : "Reduce Motion is active. Use the slider or step controls to inspect a static bucket."}
          </p>
        </div>
        <div className="replay-trace">
          <div
            className="replay-bars"
            role="group"
            aria-label="Choose replay bucket"
          >
            {buckets.map((b, i) => (
              <button
                key={b.ts}
                aria-label={`${new Date(b.ts * 1000).toISOString()}: ${b.requests} requests, ${b.probes} probes, ${b.missing} missing`}
                aria-pressed={index === i}
                onClick={() => choose(i)}
                className={index === i ? "active" : ""}
                style={{ height: `${Math.max(4, (b.requests / max) * 100)}%` }}
              >
                <i
                  style={{
                    height: `${b.requests ? (b.probes / b.requests) * 100 : 0}%`,
                  }}
                />
              </button>
            ))}
          </div>
          <input
            type="range"
            min={0}
            max={buckets.length - 1}
            value={index}
            onChange={(e) => choose(Number(e.target.value))}
            aria-label="Replay position"
            aria-valuetext={`${new Date(current.ts * 1000).toISOString()}, ${current.requests} requests`}
          />
          <div className="replay-readout">
            <span>
              <b>{n(current.requests)}</b>requests
            </span>
            <span>
              <b>{n(current.probes)}</b>probe-shaped
            </span>
            <span>
              <b>{n(current.missing)}</b>404s
            </span>
            <span>
              <b>{n(current.sources)}</b>sources
            </span>
            <span>
              <b>{pct(current.probes, current.requests)}</b>probe share
            </span>
            <Link
              to={`/events?since=${current.ts}&until=${current.ts + current.step}`}
            >
              inspect this bucket ↗
            </Link>
          </div>
        </div>
      </div>
    </Panel>
  );
}
