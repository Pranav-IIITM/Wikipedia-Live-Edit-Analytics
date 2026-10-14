type Props = { values: number[]; width?: number; height?: number; label?: string };

/** Tiny area chart of human edits per 15 minutes. */
export function Sparkline({ values, width = 120, height = 32, label }: Props) {
  if (values.length < 2) return <svg width={width} height={height} aria-hidden />;
  const max = Math.max(1, ...values);
  const step = width / (values.length - 1);
  const points = values.map((v, i) => `${(i * step).toFixed(1)},${(height - 2 - (v / max) * (height - 4)).toFixed(1)}`);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img"
         aria-label={label ?? "edits over the last 6 hours"} className="text-accent">
      <polygon points={`0,${height} ${points.join(" ")} ${width},${height}`} fill="currentColor" opacity={0.15} />
      <polyline points={points.join(" ")} fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinejoin="round" />
    </svg>
  );
}
