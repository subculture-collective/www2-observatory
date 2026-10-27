export function Sparkline({ values, color = "currentColor", height = 22 }: { values: number[]; color?: string; height?: number }) {
  const w = 120;
  const max = Math.max(1, ...values);
  const step = w / Math.max(1, values.length - 1);
  const pts = values.map((v, i) => `${(i * step).toFixed(1)},${(height - 2 - (v / max) * (height - 4)).toFixed(1)}`);
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${height}`} width={w} height={height} aria-hidden="true">
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.4" />
      <polygon points={`0,${height} ${pts.join(" ")} ${w},${height}`} fill={color} opacity=".12" />
    </svg>
  );
}
