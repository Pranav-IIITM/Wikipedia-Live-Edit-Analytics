import { revalidateTag } from "next/cache";
import { connection, type NextRequest } from "next/server";
import { dispatchRun, isActive, latestRun, syncConfigured } from "@/lib/github";
import { getSupabase } from "@/lib/supabase";

// Anyone can press Sync, so a new run is only started when none is active and the
// last publish is older than this.
const COOLDOWN_MS = 10 * 60 * 1000;
const REFRESH_WINDOW_MS = 15 * 60 * 1000;

async function lastPublishedAt(): Promise<string | null> {
  const sb = getSupabase();
  if (!sb) return null;
  const { data } = await sb
    .from("pipeline_runs")
    .select("finished_at")
    .eq("job", "pipeline")
    .eq("status", "success")
    .order("started_at", { ascending: false })
    .limit(1);
  return data?.[0]?.finished_at ?? null;
}

/**
 * Current state, polled by the Sync button while a run is in progress.
 * With ?refresh=1 (sent once the button sees its run succeed) the page cache is cleared too,
 * but only for a run that finished recently, so the cache cannot be flushed at will.
 */
export async function GET(request: NextRequest) {
  await connection();
  if (!syncConfigured()) return Response.json({ configured: false });
  try {
    const [run, publishedAt] = await Promise.all([latestRun(), lastPublishedAt()]);
    if (request.nextUrl.searchParams.get("refresh") === "1" && run?.conclusion === "success"
        && publishedAt && Date.now() - new Date(publishedAt).getTime() < REFRESH_WINDOW_MS) {
      revalidateTag("gold", { expire: 0 });
    }
    return Response.json({ configured: true, run, publishedAt });
  } catch (err) {
    console.error("[sync] status failed", err);
    return Response.json({ configured: true, error: "status unavailable" }, { status: 502 });
  }
}

/** Starts the pipeline workflow unless a run is active or the data is already fresh. */
export async function POST() {
  if (!syncConfigured()) return Response.json({ state: "not_configured" }, { status: 501 });
  try {
    const [run, publishedAt] = await Promise.all([latestRun(), lastPublishedAt()]);
    if (isActive(run)) return Response.json({ state: "running", run }, { status: 409 });

    const age = publishedAt ? Date.now() - new Date(publishedAt).getTime() : Infinity;
    if (age < COOLDOWN_MS) {
      return Response.json(
        { state: "fresh", publishedAt, retryAfterSeconds: Math.ceil((COOLDOWN_MS - age) / 1000) },
        { status: 429 },
      );
    }

    await dispatchRun();
    return Response.json({ state: "started", requestedAt: new Date().toISOString() }, { status: 202 });
  } catch (err) {
    console.error("[sync] dispatch failed", err);
    return Response.json({ state: "error" }, { status: 502 });
  }
}
