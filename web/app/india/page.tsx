import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { Heatmap } from "@/components/Heatmap";
import { Card, Empty, Freshness, NotConfigured, PageHeader, Section } from "@/components/ui";
import { HOUR_LABELS, hourOfDayProfile, totalsByWiki } from "@/lib/activity";
import { getActivityData } from "@/lib/data";
import { fmt, fmtBytes, fmtPercent } from "@/lib/format";
import { INDIAN_WIKIS, topicHref, WIKIS } from "@/lib/wikis";

export const metadata: Metadata = { title: "India" };

const IST_OFFSET = 330;

export default function IndiaPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading…</p>}>
      <IndiaContent />
    </Suspense>
  );
}

async function IndiaContent() {
  const data = await getActivityData();
  if (!data) return <NotConfigured />;
  const { hourly, trending, lastRun } = data;
  const totals = totalsByWiki(hourly.filter((r) => INDIAN_WIKIS.includes(r.wiki)));
  const leader = [...totals].sort((a, b) => b.bytesAdded - a.bytesAdded);

  return (
    <>
      <PageHeader
        title="What India is editing"
        intro="Activity across ten Indian-language Wikipedias over the last seven days, and what each one is working on right now."
        aside={<Freshness run={lastRun} />}
      />

      <Section title="Trending by language" note="Last half hour">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {INDIAN_WIKIS.map((wiki) => {
            const top = trending.filter((t) => t.wiki === wiki).slice(0, 3);
            return (
              <Card key={wiki}>
                <p className="flex items-baseline justify-between">
                  <span className="font-semibold">{WIKIS[wiki].name}</span>
                  <span className="text-sm text-muted">{WIKIS[wiki].native}</span>
                </p>
                {top.length ? (
                  <ol className="mt-2 space-y-1 text-sm">
                    {top.map((t) => (
                      <li key={t.title} className="flex justify-between gap-2">
                        <Link href={topicHref(t.wiki, t.title)} className="truncate hover:underline">{t.title}</Link>
                        <span className="shrink-0 text-muted tabular-nums">{t.human_edits}</span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-2 text-sm text-muted">Quiet right now.</p>
                )}
              </Card>
            );
          })}
        </div>
      </Section>

      <Section title="When each language is active" note="Average edits per hour of day, IST, last 7 days">
        {hourly.length ? (
          <Card>
            <Heatmap
              unit="edits/hour"
              columnLabels={HOUR_LABELS}
              rows={INDIAN_WIKIS.map((w) => ({ label: WIKIS[w].name, values: hourOfDayProfile(hourly, w, IST_OFFSET) }))}
            />
            <p className="mt-2 text-xs text-muted">Each row is shaded relative to its own busiest hour.</p>
          </Card>
        ) : (
          <Empty>Activity appears after the first pipeline runs.</Empty>
        )}
      </Section>

      <Section title="Growth leaderboard" note="Last 7 days, ranked by content added">
        {leader.length ? (
          <div className="overflow-x-auto rounded-xl border border-line bg-surface">
            <table className="w-full text-sm">
              <thead className="text-left text-muted">
                <tr className="border-b border-line">
                  <th className="px-4 py-2 font-normal">#</th>
                  <th className="px-4 py-2 font-normal">Wikipedia</th>
                  <th className="px-4 py-2 text-right font-normal">Content added</th>
                  <th className="px-4 py-2 text-right font-normal">Article edits</th>
                  <th className="px-4 py-2 text-right font-normal">New articles</th>
                  <th className="px-4 py-2 text-right font-normal">By humans</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {leader.map((t, i) => (
                  <tr key={t.wiki} className="border-b border-line last:border-0">
                    <td className="px-4 py-2 text-muted">{i + 1}</td>
                    <td className="px-4 py-2">{WIKIS[t.wiki].name} <span className="text-muted">{WIKIS[t.wiki].native}</span></td>
                    <td className="px-4 py-2 text-right">{fmtBytes(t.bytesAdded)}</td>
                    <td className="px-4 py-2 text-right">{fmt(t.edits)}</td>
                    <td className="px-4 py-2 text-right">{fmt(t.newPages)}</td>
                    <td className="px-4 py-2 text-right">{fmtPercent(t.human, t.edits)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty>No activity recorded yet.</Empty>
        )}
      </Section>
    </>
  );
}
