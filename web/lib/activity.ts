import type { HourlyActivity } from "./types";

export type WikiTotals = {
  wiki: string;
  edits: number;
  human: number;
  bots: number;
  anon: number;
  newPages: number;
  bytesAdded: number;
};

export function totalsByWiki(rows: HourlyActivity[]): WikiTotals[] {
  const map = new Map<string, WikiTotals>();
  for (const r of rows) {
    const t = map.get(r.wiki) ?? { wiki: r.wiki, edits: 0, human: 0, bots: 0, anon: 0, newPages: 0, bytesAdded: 0 };
    t.edits += r.edits;
    t.human += r.human_edits;
    t.bots += r.bot_edits;
    t.anon += r.anon_edits;
    t.newPages += r.new_pages;
    t.bytesAdded += Number(r.bytes_added);
    map.set(r.wiki, t);
  }
  return [...map.values()].sort((a, b) => b.edits - a.edits);
}

/** Average edits per hour-of-day, in a fixed UTC offset (minutes). */
export function hourOfDayProfile(rows: HourlyActivity[], wiki: string, offsetMinutes: number): number[] {
  const sums = new Array(24).fill(0);
  const days = new Set<string>();
  for (const r of rows) {
    if (r.wiki !== wiki) continue;
    const local = new Date(new Date(r.hour_start).getTime() + offsetMinutes * 60000);
    sums[local.getUTCHours()] += r.edits;
    days.add(local.toISOString().slice(0, 10));
  }
  return sums.map((s) => s / Math.max(1, days.size));
}

/** Total edits per weekday (Mon..Sun) x hour (UTC). */
export function weekGrid(rows: HourlyActivity[], wiki: string): number[][] {
  const grid = Array.from({ length: 7 }, () => new Array(24).fill(0));
  for (const r of rows) {
    if (r.wiki !== wiki) continue;
    const d = new Date(r.hour_start);
    grid[(d.getUTCDay() + 6) % 7][d.getUTCHours()] += r.edits;
  }
  return grid;
}

export const HOUR_LABELS = Array.from({ length: 24 }, (_, h) => String(h).padStart(2, "0"));
export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
