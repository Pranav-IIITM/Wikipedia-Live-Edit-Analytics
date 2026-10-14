import json

import pytest


def make_event(n: int, **overrides) -> dict:
    """A recentchange event shaped like the real stream, with sensible defaults."""
    event = {
        "meta": {"id": f"evt-{n}", "dt": "2026-10-14T10:16:00Z", "domain": "en.wikipedia.org"},
        "type": "edit",
        "namespace": 0,
        "title": "Python (programming language)",
        "timestamp": 1791972960 + n,          # 2026-10-14T10:16:00Z + n seconds
        "user": "Alice",
        "bot": False,
        "minor": False,
        "wiki": "enwiki",
        "server_name": "en.wikipedia.org",
        "length": {"old": 1000, "new": 1050},
        "revision": {"old": 1, "new": 2},
    }
    for key, value in overrides.items():
        if key == "meta":
            event["meta"].update(value)
        else:
            event[key] = value
    return event


def bronze_row(event: dict, ingested_at: str = "2026-10-14T10:30:00+00:00") -> dict:
    return {
        "event_id": event["meta"].get("id"),
        "wiki": event.get("wiki"),
        "event_time": event["meta"].get("dt"),
        "raw_json": json.dumps(event),
        "ingested_at": ingested_at,
    }


@pytest.fixture
def event_factory():
    return make_event
