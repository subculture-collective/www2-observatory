import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { DiagnosticsReport } from "../api/types.ts";
import { useSettings } from "../lib/settings.tsx";
import { n, pct, windowLabel } from "../lib/format.ts";

type Point = [number, number, number];
type Model = "orbital" | "relay" | "torus";

/** Decorative 3D projection, driven by observed source volumes. No map or threat simulation. */
export function TelemetryCore({ report }: { report: DiagnosticsReport }) {
  const { motion, hours } = useSettings();
  const canvas = useRef<HTMLCanvasElement>(null);
  const [model, setModel] = useState<Model>("orbital");
  useEffect(() => {
    const el = canvas.current;
    if (!el) return;
    const ctx = el.getContext("2d");
    if (!ctx) return;
    let frame = 0,
      last = 0,
      angle = 0.38;
    const draw = (time: number) => {
      if (motion) frame = requestAnimationFrame(draw);
      if (motion && (document.hidden || time - last < 40)) return;
      if (motion) angle += (time - last > 200 ? 40 : time - last) * 0.00018;
      last = time;
      const w = el.clientWidth,
        h = el.clientHeight,
        dpr = Math.min(2, window.devicePixelRatio || 1);
      if (
        el.width !== Math.round(w * dpr) ||
        el.height !== Math.round(h * dpr)
      ) {
        el.width = Math.round(w * dpr);
        el.height = Math.round(h * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const styles = getComputedStyle(el),
        green = styles.getPropertyValue("--accent").trim(),
        cyan = styles.getPropertyValue("--cyan").trim(),
        orange = styles.getPropertyValue("--orange").trim();
      const radius = Math.min(w * 0.3, h * 0.36);
      const project = ([x, y, z]: Point) => {
        const xx = x * Math.cos(angle) + z * Math.sin(angle),
          zz = -x * Math.sin(angle) + z * Math.cos(angle);
        const yy = y * Math.cos(0.38) - zz * Math.sin(0.38),
          z2 = y * Math.sin(0.38) + zz * Math.cos(0.38),
          pers = 3.8 / (3.8 + z2);
        return {
          x: w / 2 + xx * radius * pers,
          y: h / 2 + yy * radius * pers,
          z: z2,
        };
      };
      const line = (points: Point[], color: string, alpha = 0.5) => {
        ctx.beginPath();
        points.forEach((p, i) => {
          const v = project(p);
          if (i) ctx.lineTo(v.x, v.y);
          else ctx.moveTo(v.x, v.y);
        });
        ctx.strokeStyle = color;
        ctx.globalAlpha = alpha;
        ctx.lineWidth = 0.8;
        ctx.stroke();
        ctx.globalAlpha = 1;
      };
      const ring = (f: (a: number) => Point, color: string, alpha = 0.5) =>
        line(
          Array.from({ length: 73 }, (_, i) => f((i * Math.PI) / 36)),
          color,
          alpha,
        );
      // The model rotates; instrument labels and charts stay in a flat plane.
      if (model === "orbital") {
        for (let j = -3; j <= 3; j++) {
          const y = j / 4,
            r = Math.sqrt(1 - y * y);
          ring((a) => [Math.cos(a) * r, y, Math.sin(a) * r], green, 0.34);
        }
        for (let j = 0; j < 10; j++) {
          const b = (j * Math.PI) / 10;
          ring(
            (a) => [
              Math.cos(a) * Math.cos(b),
              Math.sin(a),
              Math.cos(a) * Math.sin(b),
            ],
            green,
            0.34,
          );
        }
      } else if (model === "torus") {
        for (let j = 0; j < 14; j++) {
          const b = (j * Math.PI) / 7;
          ring(
            (a) => [
              (0.78 + 0.3 * Math.cos(a)) * Math.cos(b),
              0.3 * Math.sin(a),
              (0.78 + 0.3 * Math.cos(a)) * Math.sin(b),
            ],
            green,
            0.55,
          );
        }
        for (let j = 0; j < 8; j++) {
          const b = (j * Math.PI) / 4;
          ring(
            (a) => [
              (0.78 + 0.3 * Math.cos(b)) * Math.cos(a),
              0.3 * Math.sin(b),
              (0.78 + 0.3 * Math.cos(b)) * Math.sin(a),
            ],
            cyan,
            0.38,
          );
        }
      } else {
        const vertices: Point[] = [
          [1, 0, 0],
          [-1, 0, 0],
          [0, 1.2, 0],
          [0, -1.2, 0],
          [0, 0, 1],
          [0, 0, -1],
        ];
        vertices.forEach((a, i) =>
          vertices.forEach((b, j) => {
            if (i < j && !(a[0] === -b[0] && a[1] === -b[1] && a[2] === -b[2]))
              line([a, b], green, 0.8);
          }),
        );
        for (const scale of [0.55, 1.4])
          line(
            [...vertices, vertices[0]].map(
              (p) => p.map((v) => v * scale) as Point,
            ),
            cyan,
            0.35,
          );
      }
      ring(
        (a) => [Math.cos(a) * 1.38, Math.sin(a) * 0.12, Math.sin(a) * 1.38],
        cyan,
        0.7,
      );
      ring(
        (a) => [Math.cos(a) * 1.6, Math.sin(a) * 1.15, Math.sin(a) * 0.45],
        green,
        0.3,
      );
      report.sources.slice(0, 24).forEach((s, i) => {
        const t = i * 2.399963,
          u = 0.8 - (i / 24) * 1.6,
          r = Math.sqrt(1 - u * u),
          p = project([Math.cos(t) * r * 1.2, u * 1.2, Math.sin(t) * r * 1.2]);
        const size = 1.5 + Math.min(6, Math.log1p(s.requests) / 2),
          color = s.probes > s.requests / 2 ? orange : cyan;
        ctx.fillStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      });
      ctx.strokeStyle = green;
      ctx.globalAlpha = 0.35;
      ctx.setLineDash([2, 6]);
      ctx.beginPath();
      ctx.moveTo(20, h / 2);
      ctx.lineTo(w - 20, h / 2);
      ctx.moveTo(w / 2, 18);
      ctx.lineTo(w / 2, h - 18);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    };
    if (motion) frame = requestAnimationFrame(draw);
    else draw(0);
    const observer = new ResizeObserver(() => {
      if (!motion) draw(0);
    });
    observer.observe(el);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [motion, model, report]);
  const s = report.summary;
  return (
    <section className="telemetry-core" aria-label="Orbital access array">
      <div className="core-topline">
        <span>
          <i className="live-dot" /> OBSERVATORY / WWW2
        </span>
        <span>CLASSIFIED: EXTREMELY PUBLIC</span>
      </div>
      <div className="core-title">
        <div>
          <span className="eyebrow">
            unnecessary orbital command // ordinary HTTP
          </span>
          <h1>
            ACCESS
            <br />
            <em>CONTROL ROOM</em>
          </h1>
        </div>
        <span className="core-serial">
          OBS–02
          <br />
          {windowLabel(hours).toUpperCase()} / TELEMETRY
        </span>
      </div>
      <div className="core-stage">
        <canvas ref={canvas} aria-hidden="true" />
        <div className="core-callout left">
          <span>OBSERVED SOURCES</span>
          <b>{n(s.sources)}</b>
          <small>address pseudonyms</small>
        </div>
        <div className="core-callout right">
          <span>PROBE-SHAPED</span>
          <b>{pct(s.probes, s.requests)}</b>
          <small>{n(s.probes)} requests</small>
        </div>
        <span className="core-axis">X 00.00 / Y HTTP / Z GET</span>
        <span className="core-model">
          MODEL // {model.toUpperCase()}
          <br />
          NODES = TOP {Math.min(24, report.sources.length)} SOURCES
        </span>
      </div>
      <div className="core-bottom">
        <div className="seg" role="group" aria-label="Wireframe model">
          {(["orbital", "relay", "torus"] as Model[]).map((m) => (
            <button
              key={m}
              className={model === m ? "active" : ""}
              aria-pressed={model === m}
              onClick={() => setModel(m)}
            >
              {m}
            </button>
          ))}
        </div>
        <Link to="/diagnostics">investigate signals ↗</Link>
      </div>
      <p className="core-caption">
        Decorative geometry, real counts. Node size follows source volume;
        orange means most requests matched probe patterns. No location or threat
        severity is implied.
      </p>
    </section>
  );
}
