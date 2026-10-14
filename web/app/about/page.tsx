import type { Metadata } from "next";
import Image from "next/image";
import { Card, PageHeader, Section } from "@/components/ui";

export const metadata: Metadata = { title: "How it works" };

const STEPS = [
  {
    title: "Collect",
    body: "Every 15 minutes a scheduled job reconnects to the Wikimedia EventStreams feed, resuming from the exact event where the previous run stopped, and keeps article edits from English and ten Indian-language Wikipedias.",
  },
  {
    title: "Bronze → Silver",
    body: "Raw events are stored as Parquet files (bronze). DuckDB parses them into typed rows, removes duplicates, flags bots and anonymous editors, and sets malformed records aside in a quarantine area (silver).",
  },
  {
    title: "Gold",
    body: "Edits are rolled up into 15-minute buckets per article and hourly totals per wiki, then merged into Postgres. Trending articles are ranked by how many different people are editing them.",
  },
  {
    title: "Quality gates",
    body: "Each run checks for duplicates, too many malformed records and impossible timestamps. A failed check stops the run before anything is published, and the next run retries from the same point.",
  },
  {
    title: "Breaking detection",
    body: "An article is marked breaking when it gets at least 8 human edits from 3 or more editors in half an hour, at 5× or more its usual rate over the previous day.",
  },
  {
    title: "Daily batch",
    body: "Once a day the pipeline loads the most-read articles from the Pageviews API, builds the daily digest and expires old data so everything fits in free-tier storage.",
  },
];

export default function AboutPage() {
  return (
    <>
      <PageHeader
        title="How WikiPulse works"
        intro="A small data lakehouse that runs on free tiers: scheduled jobs, object storage for the raw and cleaned layers, and Postgres for the tables this site reads."
      />
      <Section title="Pipeline">
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((s, i) => (
            <li key={s.title}>
              <Card className="h-full">
                <p className="text-sm text-muted">Step {i + 1}</p>
                <h3 className="font-semibold">{s.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-muted">{s.body}</p>
              </Card>
            </li>
          ))}
        </ol>
      </Section>
      <Section title="Architecture">
        <Card className="overflow-x-auto bg-white">
          <Image src="/architecture.png" alt="WikiPulse architecture diagram" width={2800} height={2240}
                 className="h-auto w-full min-w-[640px]" priority />
        </Card>
      </Section>
      <Section title="Source">
        <p className="text-sm text-muted">
          Code, tests and setup instructions are on{" "}
          <a className="text-accent hover:underline" href="https://github.com/Pranav-IIITM/Wikipedia-Live-Edit-Analytics">GitHub</a>.
        </p>
      </Section>
    </>
  );
}
