import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { Empty, NotConfigured, PageHeader } from "@/components/ui";
import { getDigestDays } from "@/lib/data";
import { fmtDay } from "@/lib/format";

export const metadata: Metadata = { title: "Daily digest" };

export default function DigestIndex() {
  return (
    <>
      <PageHeader title="Daily digest" intro="The most-edited articles of each day, by number of people editing them." />
      <Suspense fallback={<p className="text-muted">Loading…</p>}>
        <DayList />
      </Suspense>
    </>
  );
}

async function DayList() {
  const days = await getDigestDays();
  if (!days) return <NotConfigured />;
  if (!days.length) return <Empty>The first digest is built by the daily job.</Empty>;
  return (
    <ul className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
      {days.map((day) => (
        <li key={day}>
          <Link href={`/digest/${day}`} className="block rounded-xl border border-line bg-surface px-4 py-3 hover:border-accent">
            {fmtDay(day)}
          </Link>
        </li>
      ))}
    </ul>
  );
}
