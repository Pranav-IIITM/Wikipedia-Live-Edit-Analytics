export type BarDatum = { label: string; primary: number; secondary?: number; tooltip?: string };

type Props = {
  data: BarDatum[];
  height?: number;
  primaryLabel: string;
  secondaryLabel?: string;
  /** Show every n-th x label. */
  labelEvery?: number;
};

/** Stacked bars (primary at the bottom, secondary on top), drawn as SVG. */
export function BarChart({ data, height = 180, primaryLabel, secondaryLabel, labelEvery = 1 }: Props) {
  const width = 720;
  const pad = { top: 8, bottom: 22, left: 34, right: 4 };
  const innerH = height - pad.top - pad.bottom;
  const innerW = width - pad.left - pad.right;
  const max = Math.max(1, ...data.map((d) => d.primary + (d.secondary ?? 0)));
  const barW = innerW / Math.max(1, data.length);
  const y = (v: number) => pad.top + innerH - (v / max) * innerH;

  return (
    <figure>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img"
           aria-label={`${primaryLabel}${secondaryLabel ? ` and ${secondaryLabel}` : ""} chart`}>
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={pad.left} x2={width - pad.right} y1={y(max * f)} y2={y(max * f)} className="stroke-line" />
            <text x={pad.left - 6} y={y(max * f) + 4} textAnchor="end" className="fill-muted text-[10px]">
              {Math.round(max * f)}
            </text>
          </g>
        ))}
        {data.map((d, i) => {
          const x = pad.left + i * barW + barW * 0.12;
          const w = Math.max(1, barW * 0.76);
          const sec = d.secondary ?? 0;
          return (
            <g key={i}>
              <title>{d.tooltip ?? `${d.label}: ${d.primary}${secondaryLabel ? ` + ${sec}` : ""}`}</title>
              <rect x={x} y={y(d.primary)} width={w} height={innerH + pad.top - y(d.primary)} className="fill-accent" rx={1} />
              {sec > 0 && (
                <rect x={x} y={y(d.primary + sec)} width={w} height={y(d.primary) - y(d.primary + sec)}
                      className="fill-muted opacity-40" rx={1} />
              )}
              {i % labelEvery === 0 && (
                <text x={x + w / 2} y={height - 6} textAnchor="middle" className="fill-muted text-[10px]">{d.label}</text>
              )}
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-1 flex gap-4 text-xs text-muted">
        <span className="flex items-center gap-1"><i className="inline-block size-2.5 rounded-sm bg-accent" />{primaryLabel}</span>
        {secondaryLabel && (
          <span className="flex items-center gap-1"><i className="inline-block size-2.5 rounded-sm bg-muted opacity-40" />{secondaryLabel}</span>
        )}
      </figcaption>
    </figure>
  );
}
