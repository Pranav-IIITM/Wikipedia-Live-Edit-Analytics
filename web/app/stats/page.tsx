import type { Metadata } from "next";
import { Suspense } from "react";
import { BarChart, type BarDatum } from "@/components/BarChart";
import { Heatmap } from "@/components/Heatmap";
import { Card, Empty, Freshness, NotConfigured, PageHeader, Section, Stat } from "@/components/ui";
import { HOUR_LABELS, totalsByWiki, weekGrid, WEEKDAYS } from "@/lib/activity";
import { getActivityData } from "@/lib/data";
import { fmt, fmtBytes, fmtPercent } from "@/lib/format";
import type { HourlyActivity } from "@/lib/types";
import { WIKIS } from "@/lib/wikis";

export const metadata: Metadata = { title: "Stats" };

export default function StatsPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading…</p>}>
      <StatsContent />
    </Suspense>
  );
}

async function StatsContent() {
  const data = await getActivityData();
  if (!data) return <NotConfigured />;
  const { hourly, lastRun } = data;
  const totals = totalsByWiki(hourly);
  const all = totals.reduce(
    (a, t) => ({ edits: a.edits + t.edits, bots: a.bots + t.bots, anon: a.anon + t.anon, newPages: a.newPages + t.newPages }),
    { edits: 0, bots: 0, anon: 0, newPages: 0 },
  );

  return (
    <>
      <PageHeader
        title="Who edits, and when"
        intro="Article edits across all tracked Wikipedias over the last seven days."
        aside={<Freshness run={lastRun} />}
      />
      {hourly.length === 0 ? (
        <Empty>Statistics appear after the first pipeline runs.</Empty>
      ) : (
        <>
          <div className="mb-10 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Article edits" value={fmt(all.edits)} hint="last 7 days" />
            <Stat label="Made by bots" value={fmtPercent(all.bots, all.edits)} hint={`${fmt(all.bots)} edits`} />
            <Stat label="Anonymous editors" value={fmtPercent(all.anon, all.edits)} hint="IP or temporary accounts" />
            <Stat label="New articles" value={fmt(all.newPages)} />
          </div>

          <Section title="English Wikipedia, hour by hour" note="Last 48 hours (UTC)">
            <Card><BarChart data={last48Hours(hourly, "enwiki")} primaryLabel="Human edits" secondaryLabel="Bot edits" labelEvery={6} /></Card>
          </Section>

          <Section title="Weekly rhythm" note="English Wikipedia edits by weekday and hour (UTC)">
            <Card>
              <Heatmap unit="edits" columnLabels={HOUR_LABELS}
                       rows={weekGrid(hourly, "enwiki").map((values, i) => ({ label: WEEKDAYS[i], values }))} />
            </Card>
          </Section>

          <Section title="By Wikipedia">
            <div className="overflow-x-auto rounded-xl border border-line bg-surface">
              <table className="w-full text-sm">
                <thead className="text-left text-muted">
                  <tr className="border-b border-line">
                    <th className="px-4 py-2 font-normal">Wikipedia</th>
                    <th className="px-4 py-2 text-right font-normal">Edits</th>
                    <th className="px-4 py-2 text-right font-normal">Bots</th>
                    <th className="px-4 py-2 text-right font-normal">Anonymous</th>
                    <th className="px-4 py-2 text-right font-normal">New articles</th>
                    <th className="px-4 py-2 text-right font-normal">Content added</th>
                  </tr>
                </thead>
                <tbody className="tabular-nums">
                  {totals.map((t) => (
                    <tr key={t.wiki} className="border-b border-line last:border-0">
                      <td className="px-4 py-2">{WIKIS[t.wiki]?.name ?? t.wiki}</td>
                      <td className="px-4 py-2 text-right">{fmt(t.edits)}</td>
                      <td className="px-4 py-2 text-right">{fmtPercent(t.bots, t.edits)}</td>
                      <td className="px-4 py-2 text-right">{fmtPercent(t.anon, t.edits)}</td>
                      <td className="px-4 py-2 text-right">{fmt(t.newPages)}</td>
                      <td className="px-4 py-2 text-right">{fmtBytes(t.bytesAdded)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        </>
      )}
    </>
  );
}

function last48Hours(rows: HourlyActivity[], wiki: string): BarDatum[] {
  const mine = rows.filter((r) => r.wiki === wiki);
  if (!mine.length) return [];
  const HOUR = 3600 * 1000;
  const end = Math.max(...mine.map((r) => new Date(r.hour_start).getTime()));
  const byHour = new Map(mine.map((r) => [new Date(r.hour_start).getTime(), r]));
  return Array.from({ length: 48 }, (_, i) => {
    const h = end - (47 - i) * HOUR;
    const r = byHour.get(h);
    const d = new Date(h);
    return {
      label: `${String(d.getUTCHours()).padStart(2, "0")}:00`,
      primary: r?.human_edits ?? 0,
      secondary: r?.bot_edits ?? 0,
    };
  });
}
