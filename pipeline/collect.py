"""Reads the live edit stream from the saved checkpoint until caught up, keeping tracked events."""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import requests

from pipeline.rules import keep_event
from pipeline.sse import open_stream

log = logging.getLogger(__name__)

MAX_RECONNECTS = 3


@dataclass
class CollectResult:
    rows: list[dict] = field(default_factory=list)
    events_seen: int = 0
    malformed: int = 0
    last_event_id: str | None = None
    max_event_time: datetime | None = None
    caught_up: bool = False
    reconnects: int = 0

    @property
    def events_kept(self) -> int:
        return len(self.rows)


def parse_event_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def collect(last_event_id: str | None, run_started_at: datetime, *, max_seconds: int,
            lookback_minutes: int, user_agent: str, session=None,
            stream_opener=open_stream, clock=time.monotonic) -> CollectResult:
    """Consumes events until one is newer than run_started_at, or max_seconds pass.

    Resumes from last_event_id when given; otherwise starts lookback_minutes before the run.
    """
    session = session or requests.Session()
    result = CollectResult(last_event_id=last_event_id)
    since = None
    if not last_event_id:
        since = (run_started_at - timedelta(minutes=lookback_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    deadline = clock() + max_seconds
    catch_up_at = run_started_at - timedelta(seconds=5)
    ingested_at = run_started_at.isoformat()

    while True:
        try:
            for sse in stream_opener(session, user_agent, last_event_id=result.last_event_id, since=since):
                if sse.event != "message" or not sse.data:
                    continue
                if sse.id:
                    result.last_event_id = sse.id
                since = None

                try:
                    event = json.loads(sse.data)
                except json.JSONDecodeError:
                    result.malformed += 1
                    continue

                meta = event.get("meta") or {}
                if meta.get("domain") == "canary":
                    continue  # Wikimedia test events

                result.events_seen += 1
                event_time = parse_event_time(meta.get("dt"))
                if event_time and (result.max_event_time is None or event_time > result.max_event_time):
                    result.max_event_time = event_time

                if keep_event(event):
                    result.rows.append({
                        "event_id": meta.get("id"),
                        "wiki": event.get("wiki"),
                        "event_time": meta.get("dt"),
                        "raw_json": sse.data,
                        "ingested_at": ingested_at,
                    })

                if event_time and event_time >= catch_up_at:
                    result.caught_up = True
                    return result
                if clock() > deadline:
                    log.warning("time budget used up before catching up; next run continues")
                    return result
            log.info("stream closed by server")
        except requests.RequestException as exc:
            log.warning("stream error: %s", exc)

        if result.reconnects >= MAX_RECONNECTS or clock() > deadline:
            return result
        result.reconnects += 1
        time.sleep(2)
