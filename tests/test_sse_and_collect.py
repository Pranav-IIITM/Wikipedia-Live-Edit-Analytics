import json
from datetime import datetime, timezone

from conftest import make_event
from pipeline.collect import collect
from pipeline.rules import keep_event
from pipeline.sse import SseEvent, parse_sse

RUN_START = datetime(2026, 10, 14, 10, 30, tzinfo=timezone.utc)


def test_parse_sse_handles_ids_comments_and_multiline_data():
    lines = [
        ":ok", "",
        "event: message", 'id: [{"offset":1}]', 'data: {"a":', "data: 1}", "",
        "event: message", 'data: {"b":2}', "",
        'data: {"partial":',  # no terminating blank line -> dropped
    ]
    events = list(parse_sse(lines))
    assert [e.data for e in events] == ['{"a":\n1}', '{"b":2}']
    assert events[0].id == '[{"offset":1}]'
    assert events[1].id == '[{"offset":1}]'  # id carries over per SSE spec


def test_keep_event_filters_wiki_namespace_and_type():
    assert keep_event(make_event(1))
    assert keep_event(make_event(1, type="new", wiki="hiwiki"))
    assert not keep_event(make_event(1, wiki="wikidatawiki"))
    assert not keep_event(make_event(1, namespace=1))
    assert not keep_event(make_event(1, type="log"))


def _opener(events):
    def opener(session, user_agent, last_event_id=None, since=None):
        opener.calls.append({"last_event_id": last_event_id, "since": since})
        for i, ev in enumerate(events):
            yield SseEvent(id=f"id-{i}", event="message", data=ev if isinstance(ev, str) else json.dumps(ev))
    opener.calls = []
    return opener


def test_collect_stops_at_live_edge_and_tracks_checkpoint():
    events = [
        make_event(1, meta={"dt": "2026-10-14T10:20:00Z"}),
        make_event(2, wiki="wikidatawiki", meta={"dt": "2026-10-14T10:25:00Z"}),
        make_event(3, meta={"domain": "canary", "dt": "2026-10-14T10:26:00Z"}),
        "{not json",
        make_event(4, meta={"dt": "2026-10-14T10:31:00Z"}),   # past run start -> caught up
        make_event(5, meta={"dt": "2026-10-14T10:32:00Z"}),   # never read
    ]
    opener = _opener(events)
    result = collect(None, RUN_START, max_seconds=60, lookback_minutes=15,
                     user_agent="test", session=object(), stream_opener=opener)

    assert result.caught_up
    assert result.events_seen == 3          # canary and malformed are not counted
    assert result.malformed == 1
    assert [r["event_id"] for r in result.rows] == ["evt-1", "evt-4"]
    assert result.last_event_id == "id-4"
    assert opener.calls == [{"last_event_id": None, "since": "2026-10-14T10:15:00Z"}]


def test_collect_resumes_from_checkpoint_instead_of_since():
    opener = _opener([make_event(1, meta={"dt": "2026-10-14T10:31:00Z"})])
    collect("saved-id", RUN_START, max_seconds=60, lookback_minutes=15,
            user_agent="test", session=object(), stream_opener=opener)
    assert opener.calls[0] == {"last_event_id": "saved-id", "since": None}


def test_collect_respects_time_budget():
    ticks = iter(range(0, 1000, 100))
    opener = _opener([make_event(i, meta={"dt": "2026-10-14T10:20:00Z"}) for i in range(20)])
    result = collect(None, RUN_START, max_seconds=250, lookback_minutes=15, user_agent="test",
                     session=object(), stream_opener=opener, clock=lambda: next(ticks))
    assert not result.caught_up
    assert 0 < result.events_kept < 20
