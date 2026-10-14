from datetime import datetime, timezone

import pytest

from conftest import bronze_row, make_event
from pipeline import transform
from pipeline.collect import CollectResult
from pipeline.quality import QualityError, enforce, run_checks


@pytest.fixture
def con(tmp_path):
    def build(events, extra_rows=()):
        c = transform.new_connection()
        rows = [bronze_row(e) for e in events] + list(extra_rows)
        transform.load_bronze(c, rows, tmp_path)
        transform.build_silver(c)
        transform.build_gold(c)
        return c
    return build


def silver(c, columns):
    return c.execute(f"SELECT {columns} FROM silver ORDER BY event_id").fetchall()


def test_silver_types_and_derived_columns(con):
    c = con([
        make_event(1),
        make_event(2, user="203.0.113.7"),
        make_event(3, user="2001:db8::1"),
        make_event(4, user="~2026-12345-6"),
        make_event(5, user="CleanupBot", bot=True, length={"old": 500, "new": 100}),
        make_event(6, type="new", length={"new": 4210}),
    ])
    rows = silver(c, "event_id, is_bot, is_anonymous, bytes_changed")
    assert rows == [
        ("evt-1", False, False, 50),
        ("evt-2", False, True, 50),
        ("evt-3", False, True, 50),
        ("evt-4", False, True, 50),
        ("evt-5", True, False, -400),
        ("evt-6", False, False, 4210),
    ]
    event_time, lag = c.execute(
        "SELECT CAST(event_time AS TIMESTAMP), ingest_lag_sec FROM silver WHERE event_id = 'evt-1'"
    ).fetchone()
    assert event_time == datetime(2026, 10, 14, 10, 16, 1)
    assert lag == 839  # ingested 10:30:00, edited 10:16:01


def test_silver_dedupes_and_quarantines(con):
    bad = make_event(9)
    del bad["title"]
    c = con([make_event(1), make_event(1), bad])
    assert transform.count(c, "silver") == 1
    assert transform.count(c, "quarantine") == 1


def test_gold_page_buckets_and_editor_lists(con):
    c = con([
        make_event(1, user="Alice"),
        make_event(2, user="Bob"),
        make_event(3, user="Alice"),
        make_event(4, user="HelperBot", bot=True),
        make_event(5, title="Other page", timestamp=1791972960 + 1200),  # 10:36 -> next bucket
    ])
    rows = {(r[1], r[2].strftime("%H:%M")): r for r in transform.fetch_page_rows(c)}
    python = rows[("Python (programming language)", "10:15")]
    _, _, bucket, edits, human, bots, new_pages, bytes_changed, editors = python
    assert bucket.tzinfo == timezone.utc
    assert (edits, human, bots, new_pages, bytes_changed) == (4, 3, 1, 0, 200)
    assert editors == ["Alice", "Bob"]                       # distinct humans only, sorted
    assert ("Other page", "10:30") in rows


def test_gold_hourly_counts(con):
    c = con([
        make_event(1),
        make_event(2, user="203.0.113.7"),
        make_event(3, bot=True, user="Bot", length={"old": 10, "new": 0}),
        make_event(4, wiki="hiwiki", type="new", length={"new": 300}),
    ])
    rows = {r[0]: r for r in transform.fetch_hourly_rows(c)}
    _, hour, edits, human, bots, anon, new_pages, bytes_changed, bytes_added = rows["enwiki"]
    assert hour == datetime(2026, 10, 14, 10, tzinfo=timezone.utc)
    assert (edits, human, bots, anon, new_pages, bytes_changed, bytes_added) == (3, 2, 1, 1, 0, 90, 100)
    assert rows["hiwiki"][6] == 1


def test_empty_run_produces_empty_gold(con):
    c = con([])
    assert transform.fetch_page_rows(c) == []
    assert transform.fetch_hourly_rows(c) == []


def test_parquet_written_only_when_rows_exist(con, tmp_path):
    c = con([make_event(1)])
    assert transform.write_parquet(c, "silver", tmp_path / "s.parquet") == 1
    assert (tmp_path / "s.parquet").exists()
    assert transform.write_parquet(c, "quarantine", tmp_path / "q.parquet") == 0
    assert not (tmp_path / "q.parquet").exists()


def test_quality_checks_pass_and_fail(con):
    now = datetime(2026, 10, 14, 10, 30, tzinfo=timezone.utc)
    c = con([make_event(i) for i in range(60)])
    ok = CollectResult(rows=[{}] * 60, events_seen=600, caught_up=True)
    enforce(run_checks(c, ok, now))

    broken = [bronze_row(make_event(100 + i, title=None)) for i in range(5)]
    c = con([make_event(i) for i in range(60)], extra_rows=broken)
    with pytest.raises(QualityError, match="quarantine_rate"):
        enforce(run_checks(c, ok, now))

    nothing_kept = CollectResult(rows=[], events_seen=9000, caught_up=True)
    with pytest.raises(QualityError, match="events_kept"):
        enforce(run_checks(con([]), nothing_kept, now))
