import type { ReactNode } from "react";
import type { PipelineRun } from "@/lib/types";
import { TimeAgo } from "./TimeAgo";

export function PageHeader({ title, intro, aside }: { title: string; intro?: ReactNode; aside?: ReactNode }) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        {intro && <p className="mt-2 text-muted">{intro}</p>}
      </div>
      {aside}
    </header>
  );
}

export function Section({ title, note, children }: { title: string; note?: ReactNode; children: ReactNode }) {
  return (
    <section className="mb-10">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">{title}</h2>
        {note && <p className="text-sm text-muted">{note}</p>}
      </div>
      {children}
    </section>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-line bg-surface p-4 ${className}`}>{children}</div>;
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <Card>
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </Card>
  );
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "hot" }) {
  const styles = tone === "hot"
    ? "bg-hot/15 text-hot"
    : "bg-line/60 text-muted";
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${styles}`}>{children}</span>;
}

export function Freshness({ run }: { run: PipelineRun | null }) {
  if (!run) return <p className="text-sm text-muted">Waiting for the first pipeline run</p>;
  return (
    <p className="flex items-center gap-2 text-sm text-muted">
      <span className="relative flex size-2">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-live opacity-60" />
        <span className="relative inline-flex size-2 rounded-full bg-live" />
      </span>
      Updated <TimeAgo iso={run.finished_at ?? run.started_at} />
    </p>
  );
}

export function NotConfigured() {
  return (
    <Card className="mx-auto max-w-xl text-center">
      <h2 className="text-lg font-semibold">Data source not configured</h2>
      <p className="mt-2 text-sm text-muted">
        Set <code>NEXT_PUBLIC_SUPABASE_URL</code> and <code>NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY</code> to
        connect the site to the pipeline&apos;s gold tables.
      </p>
    </Card>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded-xl border border-dashed border-line p-6 text-center text-sm text-muted">{children}</p>;
}
