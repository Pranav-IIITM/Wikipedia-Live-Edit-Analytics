import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { BarChart, type BarDatum } from "@/components/BarChart";
import { Badge, Card, Empty, NotConfigured, Section, Stat } from "@/components/ui";
import { getTopicData } from "@/lib/data";
import { fmt, fmtBytes, fmtCompact, fmtDay } from "@/lib/format";
import type { Bucket } from "@/lib/types";
import { articleUrl, WIKIS, wikiName } from "@/lib/wikis";

export const metadata: Metadata = { title: "Topic" };

const HOUR = 3600 * 1000;

function safeDecode(value: string) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export default function TopicPage({ params }: PageProps<"/topic/[wiki]/[title]">) {
  return (
    <Suspense fallback={<p className="text-muted">Loading topic…</p>}>
      {params.then(({ wiki, title }) => <Topic wiki={wiki} title={safeDecode(title)} />)}
    </Suspense>
  );
}

async function Topic({ wiki, title }: { wiki: string; title: string }) {
  if (!WIKIS[wiki]) return <Empty>Unknown wiki “{wiki}”.</Empty>;
  const data = await getTopicData(wiki, title);
  if (!data) return <NotConfigured />;
  const { summary, buckets, trending, alerts, topRead, digest } = data;

  const human = buckets.reduce((n, b) => n + b.human_edits, 0);
  const bots = buckets.reduce((n, b) => n + b.bot_edits, 0);
  const bytes = buckets.reduce((n, b) => n + b.bytes_changed, 0);
  const editors = new Set(buckets.flatMap((b) => b.editors)).size;
  const url = summary?.page_url ?? articleUrl(wiki, title);

  return (
    <article>
      <p className="mb-4 text-sm text-muted"><Link href="/" className="hover:underline">← Back to the pulse</Link></p>
      <header className="mb-8 flex flex-col-reverse gap-6 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-2xl">
          <div className="mb-2 flex flex-wrap gap-2">
            <Badge>{wikiName(wiki)} Wikipedia</Badge>
            {trending && <Badge>#{trending.rank} trending in {wikiName(wiki)}</Badge>}
            {trending?.is_breaking && <Badge tone="hot">Breaking</Badge>}
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
          {summary?.description && <p className="mt-1 text-muted">{summary.description}</p>}
          {summary?.extract && <p className="mt-4 leading-relaxed">{summary.extract}</p>}
          <a href={url} className="mt-4 inline-block text-sm text-accent hover:underline">Read on Wikipedia →</a>
        </div>
        {summary?.thumbnail_url && (
          // eslint-disable-next-line @next/next/no-img-element -- Wikimedia thumbnails are already sized
          <img src={summary.thumbnail_url} alt="" className="max-h-56 w-auto self-start rounded-xl border border-line" />
        )}
      </header>

      <div className="mb-10 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Human edits" value={fmt(human)} hint="last 72 hours" />
        <Stat label="Editors" value={fmt(editors)} hint="distinct people" />
        <Stat label="Bot edits" value={fmt(bots)} />
        <Stat label="Size change" value={fmtBytes(bytes)} />
      </div>

      <Section title="Edit timeline" note="Edits per hour, last 48 hours (UTC)">
        {buckets.length ? (
          <Card><BarChart data={hourlyBars(buckets)} primaryLabel="Human edits" secondaryLabel="Bot edits" labelEvery={6} /></Card>
        ) : (
          <Empty>No edits recorded for this article in the last 72 hours.</Empty>
        )}
      </Section>

      <div className="grid gap-8 md:grid-cols-2">
        <Section title="Read vs edited" note="Daily rank among most-read articles">
          {topRead.length ? (
            <ul className="divide-y divide-line rounded-xl border border-line bg-surface text-sm">
              {topRead.map((r) => (
                <li key={r.day} className="flex justify-between px-4 py-2.5">
                  <span>{fmtDay(r.day)}</span>
                  <span className="text-muted">#{r.rank} · {fmtCompact(r.views)} views</span>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>Not in the daily top-50 most-read list recently.</Empty>
          )}
        </Section>
        <Section title="History">
          {alerts.length || digest.length ? (
            <ul className="divide-y divide-line rounded-xl border border-line bg-surface text-sm">
              {alerts.map((a) => (
                <li key={`a-${a.alert_date}`} className="flex justify-between px-4 py-2.5">
                  <span>{fmtDay(a.alert_date)}</span>
                  <span className="text-hot">Breaking · peak {Number(a.peak_spike_score).toFixed(0)}×, {a.peak_editors} editors</span>
                </li>
              ))}
              {digest.map((d) => (
                <li key={`d-${d.day}`} className="flex justify-between px-4 py-2.5">
                  <Link href={`/digest/${d.day}`} className="hover:underline">{fmtDay(d.day)}</Link>
                  <span className="text-muted">#{d.rank} most edited that day</span>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>No breaking alerts or digest appearances yet.</Empty>
          )}
        </Section>
      </div>
    </article>
  );
}

function hourlyBars(buckets: Bucket[]): BarDatum[] {
  const last = Math.max(...buckets.map((b) => new Date(b.bucket_start).getTime()));
  const end = Math.floor(last / HOUR) * HOUR;
  const hours = Array.from({ length: 48 }, (_, i) => end - (47 - i) * HOUR);
  const byHour = new Map(hours.map((h) => [h, { human: 0, bot: 0 }]));
  for (const b of buckets) {
    const h = Math.floor(new Date(b.bucket_start).getTime() / HOUR) * HOUR;
    const slot = byHour.get(h);
    if (slot) {
      slot.human += b.human_edits;
      slot.bot += b.bot_edits;
    }
  }
  return hours.map((h) => {
    const d = new Date(h);
    const label = `${String(d.getUTCHours()).padStart(2, "0")}:00`;
    const { human, bot } = byHour.get(h)!;
    return { label, primary: human, secondary: bot, tooltip: `${d.toUTCString().slice(5, 22)} — ${human} human, ${bot} bot` };
  });
}
