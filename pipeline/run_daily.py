"""Daily job: top-read pageviews, daily digest, summaries for the digest, retention cleanup.

Run with:  python -m pipeline.run_daily [YYYY-MM-DD]   (defaults to yesterday, UTC)
"""

import logging
import sys
from datetime import date, datetime, timedelta, timezone

from pipeline import daily_batch, db, enrich, retention
from pipeline.lake import get_lake

log = logging.getLogger("daily")


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    started = datetime.now(timezone.utc)
    day = date.fromisoformat(argv[0]) if argv else (started.date() - timedelta(days=1))
    run = {"run_id": "daily_" + started.strftime("%Y%m%dT%H%M%SZ"), "job": "daily", "started_at": started}

    conn = db.connect()
    try:
        log.info("top-read rows for %s: %d", day, daily_batch.load_top_read(conn, day))
        log.info("digest rows for %s: %d", day, daily_batch.build_digest(conn, day))
        log.info("summaries fetched: %d", enrich.enrich_missing(conn, limit=200))
        log.info("lake files expired: %s", retention.expire_lake(get_lake(), started.date()))
        log.info("database rows expired: %s", retention.expire_database(conn))
        db.log_run(conn, {**run, "status": "success"})
        return 0
    except Exception as exc:
        log.exception("daily run failed")
        conn.rollback()
        db.log_run(conn, {**run, "status": "failed", "error": repr(exc)[:2000]})
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
