const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const full = new Intl.NumberFormat("en");

export const fmt = (n: number) => full.format(n);
export const fmtCompact = (n: number) => compact.format(n);

export function fmtBytes(n: number): string {
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(1)} MB`;
  if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(1)} KB`;
  return `${sign}${abs} B`;
}

export function fmtPercent(part: number, total: number): string {
  return total ? `${Math.round((part / total) * 100)}%` : "–";
}

export function fmtDay(day: string): string {
  return new Date(`${day}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
  });
}

export function fmtTimeUtc(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" }) + " UTC";
}
