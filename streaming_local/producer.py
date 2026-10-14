"""Publishes tracked Wikipedia edits from EventStreams to the local Kafka topic.

Same filter as the batch collector (pipeline.rules.keep_event); keyed by wiki so each wiki's
events stay ordered within one partition.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import requests
from confluent_kafka import Producer

from pipeline.config import USER_AGENT
from pipeline.rules import keep_event
from pipeline.sse import open_stream

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
TOPIC = os.getenv("KAFKA_TOPIC", "wiki_recentchange")
LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", "30"))

log = logging.getLogger("producer")


def on_delivery(err, msg):
    if err is not None:
        log.warning("delivery failed: %s", err)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP, "linger.ms": 50, "acks": "all"})
    session = requests.Session()
    last_id = None
    since = (datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)).strftime("%Y-%m-%dT%H:%M:%SZ")
    sent = 0

    while True:
        try:
            for sse in open_stream(session, USER_AGENT, last_event_id=last_id, since=since):
                if sse.id:
                    last_id, since = sse.id, None
                try:
                    event = json.loads(sse.data)
                except json.JSONDecodeError:
                    continue
                if (event.get("meta") or {}).get("domain") == "canary" or not keep_event(event):
                    continue
                while True:
                    try:
                        producer.produce(TOPIC, key=event["wiki"].encode(), value=sse.data.encode(),
                                         on_delivery=on_delivery)
                        break
                    except BufferError:  # local queue full: let it drain (backpressure)
                        producer.poll(1)
                producer.poll(0)
                sent += 1
                if sent % 500 == 0:
                    log.info("sent %d events", sent)
        except requests.RequestException as exc:
            log.warning("stream dropped (%s); resuming in 5 s", exc)
            time.sleep(5)
        finally:
            producer.flush(10)


if __name__ == "__main__":
    main()
