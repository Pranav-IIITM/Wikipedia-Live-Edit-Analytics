"""Hourly job: collect -> bronze -> silver -> gold -> quality -> lake upload -> publish -> enrich.

Run with:  python -m pipeline.run_pipeline
"""

import logging
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pipeline import config, db, enrich, notify, transform
from pipeline.collect import collect
from pipeline.lake import get_lake, object_key
from pipeline.quality import QualityError, enforce, run_checks

log = logging.getLogger("pipeline")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    run = {"run_id": run_id, "job": "pipeline", "started_at": started}

    conn = db.connect()
    try:
        checkpoint = db.get_checkpoint(conn)
        log.info("run %s, resuming from %s", run_id, "checkpoint" if checkpoint else "lookback window")

        collected = collect(
            checkpoint, started,
            max_seconds=config.MAX_COLLECT_SECONDS,
            lookback_minutes=config.INITIAL_LOOKBACK_MINUTES,
            user_agent=config.USER_AGENT,
        )
        log.info("seen %d events, kept %d, caught up: %s",
                 collected.events_seen, collected.events_kept, collected.caught_up)
        run.update(events_seen=collected.events_seen, events_kept=collected.events_kept,
                   caught_up=collected.caught_up, max_event_time=collected.max_event_time)

        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            con = transform.new_connection()
            transform.load_bronze(con, collected.rows, workdir)
            transform.build_silver(con)
            transform.build_gold(con)

            checks = run_checks(con, collected, datetime.now(timezone.utc))
            run["checks"] = [c.as_dict() for c in checks]
            enforce(checks)

            run["silver_rows"] = transform.count(con, "silver")
            run["quarantined"] = transform.count(con, "quarantine")

            lake = get_lake()
            day = started.strftime("%Y-%m-%d")
            for layer, table in (("bronze", "bronze"), ("silver", "silver"), ("quarantine", "quarantine")):
                path = workdir / f"{layer}.parquet"
                if transform.write_parquet(con, table, path):
                    lake.upload(path, object_key(layer, day, run_id))
            log.info("lake files written to %s", lake.describe())

            page_rows = transform.fetch_page_rows(con)
            hourly_rows = transform.fetch_hourly_rows(con)
            con.close()

        trending_as_of = collected.max_event_time or started
        run["trending_rows"] = db.publish(conn, page_rows, hourly_rows,
                                          collected.last_event_id, trending_as_of)
        log.info("published %d page buckets, %d hourly rows, %d trending",
                 len(page_rows), len(hourly_rows), run["trending_rows"])

        try:
            enriched = enrich.enrich_missing(conn)
            log.info("enriched %d article summaries", enriched)
        except Exception:  # enrichment is best-effort; never fail the run for it
            conn.rollback()
            log.exception("enrichment failed")

        run["status"] = "success"
        db.log_run(conn, run)
        if notify.revalidate_site():
            log.info("website cache refreshed")
        return 0
    except QualityError as exc:
        log.error(str(exc))
        conn.rollback()
        db.log_run(conn, {**run, "status": "failed_quality", "error": str(exc)})
        return 1
    except Exception as exc:
        log.exception("run failed")
        conn.rollback()
        db.log_run(conn, {**run, "status": "failed", "error": repr(exc)[:2000]})
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
