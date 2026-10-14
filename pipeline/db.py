"""Postgres (Supabase) access: checkpoint, gold upserts, run log."""

import json

import psycopg

from pipeline import config

CHECKPOINT_KEY = "recentchange_last_event_id"


def connect() -> psycopg.Connection:
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set (see .env.example)")
    # prepare_threshold=None: Supabase poolers do not support prepared statements in transaction mode
    return psycopg.connect(config.DATABASE_URL, autocommit=False, prepare_threshold=None)


def get_checkpoint(conn) -> str | None:
    row = conn.execute(
        "select value from public.pipeline_state where key = %s", (CHECKPOINT_KEY,)
    ).fetchone()
    conn.commit()
    return row[0] if row else None


UPSERT_PAGE = """
insert into public.page_activity_15m as p
    (wiki, title, bucket_start, edits, human_edits, bot_edits, new_pages, bytes_changed, editors)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict (wiki, title, bucket_start) do update set
    edits         = p.edits + excluded.edits,
    human_edits   = p.human_edits + excluded.human_edits,
    bot_edits     = p.bot_edits + excluded.bot_edits,
    new_pages     = p.new_pages + excluded.new_pages,
    bytes_changed = p.bytes_changed + excluded.bytes_changed,
    editors       = array(select distinct e from unnest(p.editors || excluded.editors) as e order by e)
"""

UPSERT_HOURLY = """
insert into public.wiki_activity_hourly as h
    (wiki, hour_start, edits, human_edits, bot_edits, anon_edits, new_pages, bytes_changed, bytes_added)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict (wiki, hour_start) do update set
    edits         = h.edits + excluded.edits,
    human_edits   = h.human_edits + excluded.human_edits,
    bot_edits     = h.bot_edits + excluded.bot_edits,
    anon_edits    = h.anon_edits + excluded.anon_edits,
    new_pages     = h.new_pages + excluded.new_pages,
    bytes_changed = h.bytes_changed + excluded.bytes_changed,
    bytes_added   = h.bytes_added + excluded.bytes_added
"""


def publish(conn, page_rows, hourly_rows, new_checkpoint, trending_as_of) -> int:
    """Merges this run's gold rows, refreshes trending and advances the checkpoint atomically.

    Returns the number of trending rows.
    """
    with conn.transaction():
        with conn.cursor() as cur:
            if page_rows:
                cur.executemany(UPSERT_PAGE, page_rows)
            if hourly_rows:
                cur.executemany(UPSERT_HOURLY, hourly_rows)
            cur.execute("select public.refresh_trending(%s)", (trending_as_of,))
            trending = cur.fetchone()[0]
            if new_checkpoint:
                cur.execute(
                    """insert into public.pipeline_state (key, value, updated_at)
                       values (%s, %s, now())
                       on conflict (key) do update set value = excluded.value, updated_at = now()""",
                    (CHECKPOINT_KEY, new_checkpoint),
                )
    return trending


def log_run(conn, run: dict) -> None:
    with conn.transaction():
        conn.execute(
            """insert into public.pipeline_runs
                   (run_id, job, started_at, finished_at, status, events_seen, events_kept,
                    silver_rows, quarantined, trending_rows, caught_up, max_event_time, checks, error)
               values (%(run_id)s, %(job)s, %(started_at)s, now(), %(status)s, %(events_seen)s,
                       %(events_kept)s, %(silver_rows)s, %(quarantined)s, %(trending_rows)s,
                       %(caught_up)s, %(max_event_time)s, %(checks)s, %(error)s)
               on conflict (run_id) do nothing""",
            {
                "events_seen": None, "events_kept": None, "silver_rows": None, "quarantined": None,
                "trending_rows": None, "caught_up": None, "max_event_time": None, "error": None,
                **run,
                "checks": json.dumps(run.get("checks") or []),
            },
        )
