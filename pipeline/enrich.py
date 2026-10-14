"""Adds a short description, extract and thumbnail for trending / digest articles (Wikipedia summary API)."""

import logging
from urllib.parse import quote

import requests

from pipeline import config
from pipeline.rules import wiki_host

log = logging.getLogger(__name__)

SUMMARY_URL = "https://{host}/api/rest_v1/page/summary/{title}"

# Articles in trending or recent digests that have no summary yet, or a stale one.
MISSING_SQL = """
with wanted as (
    select wiki, title from public.trending_now
    union
    select wiki, title from public.daily_digest where day >= current_date - 2 and rank <= 10
)
select w.wiki, w.title
from wanted w
left join public.page_summaries s using (wiki, title)
where s.title is null or s.fetched_at < now() - interval '1 day'
limit %s
"""

UPSERT_SQL = """
insert into public.page_summaries
    (wiki, title, display_title, description, extract, thumbnail_url, page_url, fetched_at)
values (%s, %s, %s, %s, %s, %s, %s, now())
on conflict (wiki, title) do update set
    display_title = excluded.display_title, description = excluded.description,
    extract = excluded.extract, thumbnail_url = excluded.thumbnail_url,
    page_url = excluded.page_url, fetched_at = now()
"""


def fetch_summary(session, wiki: str, title: str) -> tuple:
    host = wiki_host(wiki)
    url = SUMMARY_URL.format(host=host, title=quote(title.replace(" ", "_"), safe=""))
    page_url = f"https://{host}/wiki/{quote(title.replace(' ', '_'), safe='')}"
    try:
        resp = session.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=10)
    except requests.RequestException as exc:
        log.warning("summary fetch failed for %s/%s: %s", wiki, title, exc)
        return None
    if resp.status_code == 404:
        # deleted or moved page: store an empty row so we do not refetch it every run
        return (wiki, title, title, None, None, None, page_url)
    if not resp.ok:
        return None
    data = resp.json()
    return (
        wiki,
        title,
        data.get("title") or title,
        data.get("description"),
        data.get("extract"),
        (data.get("thumbnail") or {}).get("source"),
        ((data.get("content_urls") or {}).get("desktop") or {}).get("page") or page_url,
    )


def enrich_missing(conn, limit: int | None = None) -> int:
    limit = limit or config.ENRICH_BATCH_SIZE
    wanted = conn.execute(MISSING_SQL, (limit,)).fetchall()
    conn.commit()
    if not wanted:
        return 0
    session = requests.Session()
    rows = [r for r in (fetch_summary(session, w, t) for w, t in wanted) if r]
    with conn.transaction():
        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, rows)
    return len(rows)
