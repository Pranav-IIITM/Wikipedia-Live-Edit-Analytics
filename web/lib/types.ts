export type Trending = {
  wiki: string;
  title: string;
  rank: number;
  human_edits: number;
  total_edits: number;
  editors: number;
  bytes_changed: number;
  baseline: number;
  spike_score: number;
  is_breaking: boolean;
  window_start: string;
  computed_at: string;
};

export type Summary = {
  wiki: string;
  title: string;
  display_title: string | null;
  description: string | null;
  extract: string | null;
  thumbnail_url: string | null;
  page_url: string | null;
};

export type Bucket = {
  wiki: string;
  title: string;
  bucket_start: string;
  edits: number;
  human_edits: number;
  bot_edits: number;
  bytes_changed: number;
  editors: string[];
};

export type HourlyActivity = {
  wiki: string;
  hour_start: string;
  edits: number;
  human_edits: number;
  bot_edits: number;
  anon_edits: number;
  new_pages: number;
  bytes_changed: number;
  bytes_added: number;
};

export type BreakingAlert = {
  wiki: string;
  title: string;
  alert_date: string;
  first_detected_at: string;
  last_seen_at: string;
  peak_spike_score: number;
  peak_human_edits: number;
  peak_editors: number;
};

export type TopRead = { wiki: string; day: string; rank: number; title: string; views: number };

export type DigestRow = {
  wiki: string;
  day: string;
  rank: number;
  title: string;
  human_edits: number;
  total_edits: number;
  editors: number;
  bytes_changed: number;
};

export type PipelineRun = {
  run_id: string;
  job: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  events_seen: number | null;
  events_kept: number | null;
  max_event_time: string | null;
};

/** A trending article joined with its summary and a short edit history. */
export type TrendingItem = Trending & { summary: Summary | null; spark: number[] };
