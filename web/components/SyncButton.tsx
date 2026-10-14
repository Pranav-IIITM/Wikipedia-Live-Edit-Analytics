"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

type Run = { status: string; conclusion: string | null; created_at: string };
type Status = { configured: boolean; run?: Run | null; publishedAt?: string | null };

type State =
  | { kind: "hidden" }
  | { kind: "idle" }
  | { kind: "starting" }
  | { kind: "running"; since: number }
  | { kind: "message"; text: string; tone: "ok" | "info" | "error" };

const POLL_MS = 8000;
const GIVE_UP_MS = 12 * 60 * 1000;
const ACTIVE = ["queued", "in_progress", "waiting", "requested", "pending"];

async function fetchStatus(): Promise<Status | null> {
  try {
    const res = await fetch("/api/sync", { cache: "no-store" });
    return res.ok ? ((await res.json()) as Status) : null;
  } catch {
    return null;
  }
}

/** Starts a pipeline run on demand and refreshes the page when it has published. */
export function SyncButton() {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "hidden" });
  const [now, setNow] = useState(0); // set by the ticker while a sync runs
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flash = useCallback((text: string, tone: "ok" | "info" | "error") => {
    setState({ kind: "message", text, tone });
    timer.current = setTimeout(() => setState({ kind: "idle" }), 7000);
  }, []);

  // Watch for the run started at or after `since` and react when it completes.
  const poll = useCallback(
    (since: number) => {
      setState({ kind: "running", since });
      const tick = async () => {
        if (Date.now() - since > GIVE_UP_MS) return flash("Sync is taking too long; check back later", "error");
        const status = await fetchStatus();
        const run = status?.run;
        const ours = run && new Date(run.created_at).getTime() >= since - 15_000;
        if (ours && !ACTIVE.includes(run.status)) {
          if (run.conclusion === "success") {
            await fetch("/api/sync?refresh=1", { cache: "no-store" }).catch(() => null);
            router.refresh();
            return flash("Updated with the latest edits", "ok");
          }
          return flash("Sync failed; the next hourly run will retry", "error");
        }
        timer.current = setTimeout(tick, POLL_MS);
      };
      timer.current = setTimeout(tick, POLL_MS);
    },
    [flash, router],
  );

  // On load: show the button only when syncing is configured; resume watching an active run.
  useEffect(() => {
    let cancelled = false;
    fetchStatus().then((status) => {
      if (cancelled || !status?.configured) return;
      const run = status.run;
      if (run && ACTIVE.includes(run.status)) poll(new Date(run.created_at).getTime());
      else setState({ kind: "idle" });
    });
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [poll]);

  useEffect(() => {
    if (state.kind !== "running") return;
    const tick = () => setNow(Date.now());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [state.kind]);

  async function start() {
    setState({ kind: "starting" });
    try {
      const res = await fetch("/api/sync", { method: "POST" });
      const body = await res.json();
      if (res.status === 202) return poll(new Date(body.requestedAt).getTime());
      if (res.status === 409) return poll(new Date(body.run.created_at).getTime());
      if (res.status === 429) {
        const mins = Math.max(1, Math.round((Date.now() - new Date(body.publishedAt).getTime()) / 60000));
        return flash(`Already fresh: updated ${mins} min ago`, "info");
      }
      flash("Could not start a sync", "error");
    } catch {
      flash("Could not start a sync", "error");
    }
  }

  if (state.kind === "hidden") return null;

  if (state.kind === "message") {
    const color = state.tone === "ok" ? "text-live" : state.tone === "error" ? "text-hot" : "text-muted";
    return <p role="status" className={`text-sm ${color}`}>{state.text}</p>;
  }

  const busy = state.kind === "starting" || state.kind === "running";
  const elapsed = state.kind === "running" ? Math.max(0, Math.floor((now - state.since) / 1000)) : 0;
  const label = state.kind === "starting"
    ? "Starting…"
    : state.kind === "running"
      ? `Syncing… ${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")}`
      : "Sync now";

  return (
    <button
      type="button"
      onClick={start}
      disabled={busy}
      aria-live="polite"
      title="Fetch the latest Wikipedia edits now (takes about 2 minutes)"
      className="inline-flex items-center gap-2 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm hover:border-accent disabled:cursor-progress disabled:opacity-80"
    >
      <svg viewBox="0 0 24 24" className={`size-4 ${busy ? "animate-spin" : ""}`} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d="M21 12a9 9 0 1 1-2.64-6.36" strokeLinecap="round" />
        <path d="M21 3v6h-6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {label}
    </button>
  );
}
