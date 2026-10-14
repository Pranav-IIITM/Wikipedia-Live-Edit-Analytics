import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { Card, Empty, NotConfigured, PageHeader, Section } from "@/components/ui";
import { getDigest } from "@/lib/data";
import { fmtDay } from "@/lib/format";
import type { DigestRow, Summary } from "@/lib/types";
import { INDIAN_WIKIS, topicHref, WIKIS } from "@/lib/wikis";

export const metadata: Metadata = { title: "Daily digest" };

export default function DigestDayPage({ params }: PageProps<"/digest/[date]">) {
  return (
    <Suspense fallback={<p className="text-muted">Loading…</p>}>
      {params.then(({ date }) => <Digest day={date} />)}
    </Suspense>
  );
}

async function Digest({ day }: { day: string }) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return <Empty>Not a valid date.</Empty>;
  const data = await getDigest(day);
  if (!data) return <NotConfigured />;
  const { rows, summaries } = data;
  const english = rows.filter((r) => r.wiki === "enwiki");

  return (
    <>
      <p className="mb-4 text-sm text-muted"><Link href="/digest" className="hover:underline">← All days</Link></p>
      <PageHeader title={`What the world edited on ${fmtDay(day)}`} intro="Ranked by the number of people editing each article that day (UTC)." />
      {rows.length === 0 ? (
        <Empty>No digest for this day.</Empty>
      ) : (
        <>
          <Section title="English Wikipedia">
            <ol className="space-y-3">
              {english.map((r) => <DigestItem key={r.rank} row={r} summary={summaries[`${r.wiki}/${r.title}`]} />)}
            </ol>
          </Section>
          <Section title="Indian languages" note="Top 3 per language">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {INDIAN_WIKIS.map((wiki) => {
                const top = rows.filter((r) => r.wiki === wiki).slice(0, 3);
                if (!top.length) return null;
                return (
                  <Card key={wiki}>
                    <p className="font-semibold">{WIKIS[wiki].name} <span className="font-normal text-muted">{WIKIS[wiki].native}</span></p>
                    <ol className="mt-2 space-y-1 text-sm">
                      {top.map((r) => (
                        <li key={r.rank} className="flex justify-between gap-2">
                          <Link href={topicHref(r.wiki, r.title)} className="truncate hover:underline">{r.title}</Link>
                          <span className="shrink-0 text-muted">{r.editors} editors</span>
                        </li>
                      ))}
                    </ol>
                  </Card>
                );
              })}
            </div>
          </Section>
        </>
      )}
    </>
  );
}

function DigestItem({ row, summary }: { row: DigestRow; summary?: Summary }) {
  return (
    <li className="flex gap-4 rounded-xl border border-line bg-surface p-4">
      <span className="w-6 text-lg font-semibold tabular-nums text-muted">{row.rank}</span>
      <div className="min-w-0 flex-1">
        <Link href={topicHref(row.wiki, row.title)} className="font-medium hover:underline">{row.title}</Link>
        {summary?.description && <p className="text-sm text-muted">{summary.description}</p>}
        <p className="mt-1 text-xs text-muted">{row.editors} editors · {row.human_edits} human edits</p>
      </div>
      {summary?.thumbnail_url && (
        // eslint-disable-next-line @next/next/no-img-element -- Wikimedia thumbnails are already sized
        <img src={summary.thumbnail_url} alt="" loading="lazy" className="size-14 shrink-0 rounded-lg object-cover" />
      )}
    </li>
  );
}
