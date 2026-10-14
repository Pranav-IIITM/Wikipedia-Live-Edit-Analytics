"use client";

import Link from "next/link";
import { useState } from "react";
import type { TrendingItem } from "@/lib/types";
import { fmtBytes } from "@/lib/format";
import { topicHref, WIKIS } from "@/lib/wikis";
import { Sparkline } from "./Sparkline";

const TABS = [
  { id: "all", label: "All" },
  { id: "en", label: "English" },
  { id: "indic", label: "Indian languages" },
] as const;
type Tab = (typeof TABS)[number]["id"];

function matches(tab: Tab, wiki: string) {
  if (tab === "en") return wiki === "enwiki";
  if (tab === "indic") return wiki !== "enwiki";
  return true;
}

export function TrendingBoard({ items }: { items: TrendingItem[] }) {
  const [tab, setTab] = useState<Tab>("all");
  const shown = items
    .filter((i) => matches(tab, i.wiki))
    .sort((a, b) => b.editors - a.editors || b.human_edits - a.human_edits)
    .slice(0, 24);

  return (
    <div>
      <div role="tablist" aria-label="Filter by language" className="mb-4 inline-flex rounded-lg border border-line bg-surface p-1">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}
                  className={`rounded-md px-3 py-1.5 text-sm ${tab === t.id ? "bg-foreground text-background" : "text-muted hover:text-foreground"}`}>
            {t.label}
          </button>
        ))}
      </div>
      {shown.length === 0 ? (
        <p className="rounded-xl border border-dashed border-line p-6 text-center text-sm text-muted">
          Nothing trending here in the last half hour.
        </p>
      ) : (
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {shown.map((item, i) => <TrendingCard key={`${item.wiki}/${item.title}`} item={item} position={i + 1} />)}
        </ol>
      )}
    </div>
  );
}

function TrendingCard({ item, position }: { item: TrendingItem; position: number }) {
  const s = item.summary;
  const wiki = WIKIS[item.wiki];
  return (
    <li className="flex flex-col rounded-xl border border-line bg-surface p-4">
      <div className="flex gap-3">
        <span className="w-5 shrink-0 pt-0.5 text-sm tabular-nums text-muted">{position}</span>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-1.5 text-xs">
            <span className="rounded-full bg-line/60 px-2 py-0.5 text-muted">{wiki?.name ?? item.wiki}</span>
            {item.is_breaking && <span className="rounded-full bg-hot/15 px-2 py-0.5 font-medium text-hot">Breaking</span>}
          </div>
          <Link href={topicHref(item.wiki, item.title)} className="font-medium leading-snug hover:underline">
            {s?.display_title ? stripTags(s.display_title) : item.title}
          </Link>
          {s?.description && <p className="mt-0.5 line-clamp-2 text-sm text-muted">{s.description}</p>}
        </div>
        {s?.thumbnail_url && (
          // eslint-disable-next-line @next/next/no-img-element -- Wikimedia thumbnails are already sized
          <img src={s.thumbnail_url} alt="" loading="lazy" className="size-16 shrink-0 rounded-lg object-cover" />
        )}
      </div>
      <div className="mt-auto flex items-end justify-between gap-3 pt-3 pl-8">
        <dl className="flex gap-4 text-xs text-muted">
          <div><dt className="sr-only">Edits</dt><dd><b className="text-foreground tabular-nums">{item.human_edits}</b> edits</dd></div>
          <div><dt className="sr-only">Editors</dt><dd><b className="text-foreground tabular-nums">{item.editors}</b> editors</dd></div>
          <div><dt className="sr-only">Size change</dt><dd className="tabular-nums">{fmtBytes(item.bytes_changed)}</dd></div>
        </dl>
        <Sparkline values={item.spark} />
      </div>
    </li>
  );
}

/** Summary display titles can contain HTML markup (e.g. italics). */
function stripTags(html: string) {
  return html.replace(/<[^>]*>/g, "");
}
