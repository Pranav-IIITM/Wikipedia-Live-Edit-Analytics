"""Minimal Server-Sent Events reader for Wikimedia EventStreams."""

from dataclasses import dataclass
from typing import Iterable, Iterator

STREAM_URL = "https://stream.wikimedia.org/v2/stream/recentchange"


@dataclass
class SseEvent:
    id: str | None
    event: str
    data: str


def parse_sse(lines: Iterable[str]) -> Iterator[SseEvent]:
    """Turns raw SSE lines into events. The last seen id carries over, as in the SSE spec."""
    event_id = None
    event_type = "message"
    data: list[str] = []
    for raw in lines:
        line = raw.rstrip("\r")
        if line == "":
            if data:
                yield SseEvent(event_id, event_type, "\n".join(data))
            data = []
            event_type = "message"
            continue
        if line.startswith(":"):
            continue  # comment / keep-alive
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "data":
            data.append(value)
        elif field == "id":
            event_id = value
        elif field == "event":
            event_type = value
    # an unterminated trailing event is dropped, as the spec requires


def open_stream(session, user_agent: str, last_event_id: str | None = None,
                since: str | None = None, timeout=(10, 60)) -> Iterator[SseEvent]:
    """Opens the recentchange stream, resuming from last_event_id (preferred) or a timestamp."""
    headers = {"User-Agent": user_agent, "Accept": "text/event-stream"}
    params = {}
    if last_event_id:
        headers["Last-Event-ID"] = last_event_id
    elif since:
        params["since"] = since
    with session.get(STREAM_URL, headers=headers, params=params, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        lines = (line.decode("utf-8", errors="replace") for line in resp.iter_lines())
        yield from parse_sse(lines)
