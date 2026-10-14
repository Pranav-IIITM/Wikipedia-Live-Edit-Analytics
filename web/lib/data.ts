import { cacheLife, cacheTag } from "next/cache";
import { getSupabase } from "./supabase";
import { INDIAN_WIKIS } from "./wikis";
import type {
  BreakingAlert,
  Bucket,
  DigestRow,
  HourlyActivity,
  PipelineRun,
  Summary,
  TopRead,
  Trending,
  TrendingItem,
} from "./types";

// The pipeline publishes hourly (or on Sync) and then revalidates the "gold" tag;
// the time-based refresh below is a fallback.
const LIVE = { stale: 60, revalidate: 300, expire: 3600 };
const DAILY = { stale: 300, revalidate: 3600, expire: 86400 };

const SPARK_HOURS = 6;
const BUCKET_MS = 15 * 60 * 1000;

type Result<T> = { data: T[] | null; error: { message: string } | null };

function rows<T>(res: Result<T>, label: string): T[] {
  if (res.error) console.error(`[data] ${label}: ${res.error.message}`);
  return res.data ?? [];
}

/** Runs a query per chunk of values (keeps `in.(...)` URLs short), concatenating results. */
async function chunked<T>(values: string[], size: number, run: (chunk: string[]) => PromiseLike<Result<T>>, label: string) {
  const out: T[] = [];
  for (let i = 0; i < values.length; i += size) {
    out.push(...rows(await run(values.slice(i, i + size)), label));
  }
  return out;
}

/** Fetches every row of a query in pages (the API returns at most 1000 rows per request). */
async function paged<T>(run: (from: number, to: number) => PromiseLike<Result<T>>, label: string) {
  const out: T[] = [];
  for (let from = 0; ; from += 1000) {
    const page = rows(await run(from, from + 999), label);
    out.push(...page);
    if (page.length < 1000) return out;
  }
}

const key = (wiki: string, title: string) => `${wiki}\u0000${title}`;

async function summariesFor(pairs: { wiki: string; title: string }[]) {
  const sb = getSupabase()!;
  const titles = [...new Set(pairs.map((p) => p.title))];
  const found = await chunked<Summary>(titles, 25, (chunk) =>
    sb.from("page_summaries")
      .select("wiki,title,display_title,description,extract,thumbnail_url,page_url")
      .in("title", chunk), "summaries");
  return new Map(found.map((s) => [key(s.wiki, s.title), s]));
}

/** Human edits per 15-minute bucket over the last SPARK_HOURS for each article. */
async function sparklinesFor(pairs: { wiki: string; title: string }[], now: number) {
  const sb = getSupabase()!;
  const since = new Date(now - SPARK_HOURS * 3600 * 1000);
  const titles = [...new Set(pairs.map((p) => p.title))];
  const buckets = await chunked<Pick<Bucket, "wiki" | "title" | "bucket_start" | "human_edits">>(titles, 25, (chunk) =>
    sb.from("page_activity_15m")
      .select("wiki,title,bucket_start,human_edits")
      .in("title", chunk)
      .gte("bucket_start", since.toISOString()), "sparklines");

  const slots = (SPARK_HOURS * 3600 * 1000) / BUCKET_MS;
  const start = Math.floor(since.getTime() / BUCKET_MS) * BUCKET_MS;
  const series = new Map<string, number[]>();
  for (const b of buckets) {
    const k = key(b.wiki, b.title);
    const arr = series.get(k) ?? new Array(slots + 1).fill(0);
    const idx = Math.floor((new Date(b.bucket_start).getTime() - start) / BUCKET_MS);
    if (idx >= 0 && idx < arr.length) arr[idx] += b.human_edits;
    series.set(k, arr);
  }
  return series;
}

export type HomeData = {
  items: TrendingItem[];
  alerts: BreakingAlert[];
  topRead: TopRead[];
  lastRun: PipelineRun | null;
};

export async function getHomeData(): Promise<HomeData | null> {
  "use cache";
  cacheLife(LIVE);
  cacheTag("gold");
  const sb = getSupabase();
  if (!sb) return null;

  const [trendingRes, alertsRes, runRes, topDayRes] = await Promise.all([
    sb.from("trending_now").select("*")
      .order("editors", { ascending: false })
      .order("human_edits", { ascending: false })
      .limit(400),
    sb.from("breaking_alerts").select("*").order("last_seen_at", { ascending: false }).limit(10),
    sb.from("pipeline_runs")
      .select("run_id,job,started_at,finished_at,status,events_seen,events_kept,max_event_time")
      .eq("job", "pipeline").eq("status", "success")
      .order("started_at", { ascending: false }).limit(1),
    sb.from("daily_top_read").select("day").order("day", { ascending: false }).limit(1),
  ]);

  const trending = rows<Trending>(trendingRes, "trending");
  // Keep the strongest 40 English and 40 Indian-language articles for the board.
  const english = trending.filter((t) => t.wiki === "enwiki").slice(0, 40);
  const indian = trending.filter((t) => t.wiki !== "enwiki").slice(0, 40);
  const picked = [...english, ...indian];

  const now = Date.now();
  const [summaries, sparks] = await Promise.all([summariesFor(picked), sparklinesFor(picked, now)]);
  const items: TrendingItem[] = picked.map((t) => ({
    ...t,
    summary: summaries.get(key(t.wiki, t.title)) ?? null,
    spark: sparks.get(key(t.wiki, t.title)) ?? [],
  }));

  const topDay = rows<{ day: string }>(topDayRes, "top-read day")[0]?.day;
  let topRead: TopRead[] = [];
  if (topDay) {
    topRead = rows<TopRead>(
      await sb.from("daily_top_read").select("*").eq("day", topDay).lte("rank", 10).order("rank"),
      "top-read",
    );
  }

  return {
    items,
    alerts: rows<BreakingAlert>(alertsRes, "alerts"),
    topRead,
    lastRun: rows<PipelineRun>(runRes, "last run")[0] ?? null,
  };
}

export type TopicData = {
  summary: Summary | null;
  buckets: Bucket[];
  trending: Trending | null;
  alerts: BreakingAlert[];
  topRead: TopRead[];
  digest: DigestRow[];
};

export async function getTopicData(wiki: string, title: string): Promise<TopicData | null> {
  "use cache";
  cacheLife(LIVE);
  cacheTag("gold");
  const sb = getSupabase();
  if (!sb) return null;

  const since = new Date(Date.now() - 72 * 3600 * 1000).toISOString();
  const [summaryRes, bucketRes, trendingRes, alertRes, readRes, digestRes] = await Promise.all([
    sb.from("page_summaries").select("*").eq("wiki", wiki).eq("title", title).limit(1),
    sb.from("page_activity_15m").select("*").eq("wiki", wiki).eq("title", title)
      .gte("bucket_start", since).order("bucket_start"),
    sb.from("trending_now").select("*").eq("wiki", wiki).eq("title", title).limit(1),
    sb.from("breaking_alerts").select("*").eq("wiki", wiki).eq("title", title)
      .order("alert_date", { ascending: false }).limit(10),
    sb.from("daily_top_read").select("*").eq("wiki", wiki).eq("title", title)
      .order("day", { ascending: false }).limit(14),
    sb.from("daily_digest").select("*").eq("wiki", wiki).eq("title", title)
      .order("day", { ascending: false }).limit(14),
  ]);

  return {
    summary: rows<Summary>(summaryRes, "summary")[0] ?? null,
    buckets: rows<Bucket>(bucketRes, "buckets"),
    trending: rows<Trending>(trendingRes, "trending row")[0] ?? null,
    alerts: rows<BreakingAlert>(alertRes, "alerts"),
    topRead: rows<TopRead>(readRes, "top read"),
    digest: rows<DigestRow>(digestRes, "digest"),
  };
}

export type ActivityData = {
  hourly: HourlyActivity[];
  trending: Trending[];
  lastRun: PipelineRun | null;
};

/** Hourly activity for every tracked wiki over the last 7 days, plus current trending. */
export async function getActivityData(): Promise<ActivityData | null> {
  "use cache";
  cacheLife(LIVE);
  cacheTag("gold");
  const sb = getSupabase();
  if (!sb) return null;

  const since = new Date(Date.now() - 7 * 24 * 3600 * 1000).toISOString();
  const [hourly, trendingRes, runRes] = await Promise.all([
    paged<HourlyActivity>((from, to) =>
      sb.from("wiki_activity_hourly").select("*").gte("hour_start", since)
        .order("hour_start").order("wiki").range(from, to), "hourly"),
    sb.from("trending_now").select("*").in("wiki", INDIAN_WIKIS).lte("rank", 5).order("rank"),
    sb.from("pipeline_runs")
      .select("run_id,job,started_at,finished_at,status,events_seen,events_kept,max_event_time")
      .eq("job", "pipeline").eq("status", "success")
      .order("started_at", { ascending: false }).limit(1),
  ]);

  return {
    hourly,
    trending: rows<Trending>(trendingRes, "indian trending"),
    lastRun: rows<PipelineRun>(runRes, "last run")[0] ?? null,
  };
}

export async function getDigestDays(): Promise<string[] | null> {
  "use cache";
  cacheLife(DAILY);
  cacheTag("gold");
  const sb = getSupabase();
  if (!sb) return null;
  const res = await sb.from("daily_digest").select("day").eq("rank", 1).order("day", { ascending: false }).limit(500);
  return [...new Set(rows<{ day: string }>(res, "digest days").map((r) => r.day))].slice(0, 90);
}

export type DigestData = { rows: DigestRow[]; summaries: Record<string, Summary> };

export async function getDigest(day: string): Promise<DigestData | null> {
  "use cache";
  cacheLife(DAILY);
  cacheTag("gold");
  const sb = getSupabase();
  if (!sb) return null;
  const digest = rows<DigestRow>(
    await sb.from("daily_digest").select("*").eq("day", day).lte("rank", 10).order("wiki").order("rank"),
    "digest",
  );
  const featured = digest.filter((r) => r.rank <= (r.wiki === "enwiki" ? 10 : 3));
  const map = await summariesFor(featured);
  const summaries: Record<string, Summary> = {};
  for (const r of featured) {
    const s = map.get(key(r.wiki, r.title));
    if (s) summaries[`${r.wiki}/${r.title}`] = s;
  }
  return { rows: digest, summaries };
}
