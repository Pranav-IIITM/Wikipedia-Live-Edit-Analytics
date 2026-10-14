"""Daily gold tables: most-read articles (Pageviews API) and the daily edit digest."""

import logging
from datetime import date
from urllib.parse import quote

import requests

from pipeline import config
from pipeline.rules import TRACKED_WIKIS, wiki_host

log = logging.getLogger(__name__)

TOP_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{project}/all-access/{y}/{m:02d}/{d:02d}"
SITEINFO_URL = "https://{host}/w/api.php?action=query&meta=siteinfo&siprop=general&format=json"
TOP_READ_LIMIT = 50
DIGEST_LIMIT = 30


def main_page_title(session, wiki: str) -> str | None:
    try:
        resp = session.get(SITEINFO_URL.format(host=wiki_host(wiki)),
                           headers={"User-Agent": config.USER_AGENT}, timeout=10)
        resp.raise_for_status()
        return resp.json()["query"]["general"]["mainpage"]
    except (requests.RequestException, KeyError, ValueError):
        return None


def top_read(session, wiki: str, day: date) -> list[tuple[str, int]]:
    """Top articles by views for a day, without the main page and special pages."""
    url = TOP_URL.format(project=quote(wiki_host(wiki)), y=day.year, m=day.month, d=day.day)
    resp = session.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=20)
    if resp.status_code == 404:
        return []  # data for that day not published yet
    resp.raise_for_status()
    articles = resp.json()["items"][0]["articles"]
    main_page = (main_page_title(session, wiki) or "").replace(" ", "_")
    out = []
    for a in articles:
        title = a["article"]
        if title == main_page or title == "Main_Page" or ":" in title or title == "-":
            continue
        out.append((title.replace("_", " "), int(a["views"])))
        if len(out) >= TOP_READ_LIMIT:
            break
    return out


def load_top_read(conn, day: date) -> int:
    session = requests.Session()
    total = 0
    for wiki in TRACKED_WIKIS:
        try:
            rows = top_read(session, wiki, day)
        except requests.RequestException as exc:
            log.warning("pageviews failed for %s: %s", wiki, exc)
            continue
        with conn.transaction():
            conn.execute("delete from public.daily_top_read where wiki = %s and day = %s", (wiki, day))
            with conn.cursor() as cur:
                cur.executemany(
                    "insert into public.daily_top_read (wiki, day, rank, title, views) values (%s, %s, %s, %s, %s)",
                    [(wiki, day, i + 1, title, views) for i, (title, views) in enumerate(rows)],
                )
        total += len(rows)
    return total


DIGEST_SQL = """
with day_pages as (
    select wiki, title,
           sum(human_edits)::int  as human_edits,
           sum(edits)::int        as total_edits,
           sum(bytes_changed)     as bytes_changed
    from public.page_activity_15m
    where bucket_start >= %(day)s::date and bucket_start < %(day)s::date + 1
    group by wiki, title
),
day_editors as (
    select p.wiki, p.title, count(distinct e)::int as editors
    from public.page_activity_15m p
    cross join lateral unnest(p.editors) as e
    where p.bucket_start >= %(day)s::date and p.bucket_start < %(day)s::date + 1
    group by p.wiki, p.title
),
ranked as (
    select d.*, coalesce(e.editors, 0) as editors,
           row_number() over (partition by d.wiki
                              order by coalesce(e.editors, 0) desc, d.human_edits desc, d.title) as rank
    from day_pages d left join day_editors e using (wiki, title)
    where d.human_edits > 0
)
insert into public.daily_digest (wiki, day, rank, title, human_edits, total_edits, editors, bytes_changed)
select wiki, %(day)s::date, rank, title, human_edits, total_edits, editors, bytes_changed
from ranked where rank <= %(limit)s
"""


def build_digest(conn, day: date) -> int:
    with conn.transaction():
        conn.execute("delete from public.daily_digest where day = %s", (day,))
        cur = conn.execute(DIGEST_SQL, {"day": day, "limit": DIGEST_LIMIT})
        return cur.rowcount
