type Props = {
  rows: { label: string; values: number[] }[];
  columnLabels: string[];
  /** Show every n-th column label. */
  labelEvery?: number;
  unit: string;
};

/** Grid heatmap; each row is scaled to its own maximum so small wikis stay readable. */
export function Heatmap({ rows, columnLabels, labelEvery = 3, unit }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-[2px] text-xs">
        <thead>
          <tr>
            <th />
            {columnLabels.map((c, i) => (
              <th key={i} className="font-normal text-muted">{i % labelEvery === 0 ? c : ""}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const max = Math.max(1, ...row.values);
            return (
              <tr key={row.label}>
                <th className="whitespace-nowrap pr-2 text-left font-medium">{row.label}</th>
                {row.values.map((v, i) => (
                  <td key={i} title={`${row.label}, ${columnLabels[i]}: ${Math.round(v)} ${unit}`}
                      className="h-5 min-w-4 rounded-[3px] bg-accent"
                      style={{ opacity: v ? 0.12 + 0.88 * (v / max) : 0.05 }} />
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
