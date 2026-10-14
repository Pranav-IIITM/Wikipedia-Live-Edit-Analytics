"""Keeps storage bounded: expires old lake files and old database rows."""

import logging
from datetime import date, timedelta

from pipeline import config
from pipeline.lake import key_date

log = logging.getLogger(__name__)


def expire_lake(lake, today: date) -> dict[str, int]:
    limits = {
        "bronze/": config.BRONZE_RETENTION_DAYS,
        "silver/": config.SILVER_RETENTION_DAYS,
        "quarantine/": config.SILVER_RETENTION_DAYS,
    }
    deleted = {}
    for prefix, days in limits.items():
        cutoff = (today - timedelta(days=days)).isoformat()
        old = [key for key, _ in lake.list(prefix) if (key_date(key) or "9999") < cutoff]
        if old:
            lake.delete(old)
        deleted[prefix.rstrip("/")] = len(old)
    return deleted


DB_RULES = [
    ("page_activity_15m", "bucket_start", config.PAGE_ACTIVITY_RETENTION_DAYS),
    ("pipeline_runs", "started_at", config.RUN_LOG_RETENTION_DAYS),
    ("breaking_alerts", "last_seen_at", config.ALERT_RETENTION_DAYS),
    ("daily_top_read", "day", config.ALERT_RETENTION_DAYS),
]


def expire_database(conn) -> dict[str, int]:
    deleted = {}
    with conn.transaction():
        for table, column, days in DB_RULES:
            cur = conn.execute(
                f"delete from public.{table} where {column} < now() - make_interval(days => %s)", (days,)
            )
            deleted[table] = cur.rowcount
        # summaries no longer referenced by trending or the digest
        cur = conn.execute("""
            delete from public.page_summaries s
            where s.fetched_at < now() - interval '30 days'
              and not exists (select 1 from public.trending_now t where t.wiki = s.wiki and t.title = s.title)
        """)
        deleted["page_summaries"] = cur.rowcount
    return deleted
