import Link from "next/link";
import { Suspense } from "react";
import { TrendingBoard } from "@/components/TrendingBoard";
import { Card, Empty, Freshness, NotConfigured, PageHeader, Section } from "@/components/ui";
import { getHomeData } from "@/lib/data";
import { fmtCompact, fmtDay } from "@/lib/format";
import { topicHref, wikiName } from "@/lib/wikis";

export default function Home() {
  return (
    <Suspense fallback={<p className="text-muted">Loading the pulse…</p>}>
      <HomeContent />
    </Suspense>
  );
}

async function HomeContent() {
  const data = await getHomeData();
  if (!data) return <NotConfigured />;
  const { items, alerts, topRead, lastRun } = data;
  const breaking = items.filter((i) => i.is_breaking);

  return (
    <>
      <PageHeader
        title="What the world is editing right now"
        intro="Wikipedia editors update articles within minutes of real-world events. These are the articles with the most people editing them in the last half hour."
        aside={<Freshness run={lastRun} />}
      />

      {breaking.length > 0 && (
        <Section title="Breaking" note="Edit activity at least 5× its usual rate, by 3+ editors">
          <ul className="grid gap-3 sm:grid-cols-2">
            {breaking.slice(0, 4).map((b) => (
              <li key={`${b.wiki}/${b.title}`}>
                <Card className="border-hot/40">
                  <p className="text-xs font-medium uppercase tracking-wide text-hot">
                    {wikiName(b.wiki)} · {Number(b.spike_score).toFixed(0)}× usual activity
                  </p>
                  <Link href={topicHref(b.wiki, b.title)} className="mt-1 block text-lg font-semibold hover:underline">
                    {b.title}
                  </Link>
                  {b.summary?.description && <p className="text-sm text-muted">{b.summary.description}</p>}
                  <p className="mt-2 text-sm">{b.human_edits} edits by {b.editors} editors in the last half hour</p>
                </Card>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Trending now">
        {items.length ? <TrendingBoard items={items} /> : <Empty>No trending articles yet. The pipeline publishes every hour.</Empty>}
      </Section>

      <div className="grid gap-8 md:grid-cols-2">
        <Section title="Most read yesterday" note={topRead[0] ? fmtDay(topRead[0].day) : undefined}>
          {topRead.length ? (
            <TopReadList rows={topRead.filter((r) => r.wiki === "enwiki").slice(0, 8)} />
          ) : (
            <Empty>Pageview rankings arrive with the daily job.</Empty>
          )}
        </Section>
        <Section title="Recent breaking alerts">
          {alerts.length ? (
            <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
              {alerts.map((a) => (
                <li key={`${a.wiki}/${a.title}/${a.alert_date}`} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
                  <Link href={topicHref(a.wiki, a.title)} className="truncate hover:underline">{a.title}</Link>
                  <span className="shrink-0 text-xs text-muted">{wikiName(a.wiki)} · peak {Number(a.peak_spike_score).toFixed(0)}×</span>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>No alerts yet.</Empty>
          )}
        </Section>
      </div>
    </>
  );
}

function TopReadList({ rows }: { rows: { wiki: string; title: string; views: number; rank: number }[] }) {
  return (
    <ol className="divide-y divide-line rounded-xl border border-line bg-surface">
      {rows.map((r) => (
        <li key={r.rank} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
          <span className="flex min-w-0 gap-3">
            <span className="w-4 text-muted tabular-nums">{r.rank}</span>
            <Link href={topicHref(r.wiki, r.title)} className="truncate hover:underline">{r.title}</Link>
          </span>
          <span className="shrink-0 text-xs text-muted tabular-nums">{fmtCompact(r.views)} views</span>
        </li>
      ))}
    </ol>
  );
}
