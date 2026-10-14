# Local learning mode: Kafka + Spark Structured Streaming

The production pipeline runs as hourly micro-batches on GitHub Actions. This folder runs
the same logic as a **continuous stream** on your machine, to learn the streaming concepts.

```
EventStreams ──▶ producer.py ──▶ Kafka topic wiki_recentchange (3 partitions, key = wiki)
                                      │
                                      ▼
                     Spark Structured Streaming (one app, three stages)
                      kafka_to_bronze   raw JSON + Kafka partition/offset      → data/bronze
                      bronze_to_silver  parse, type, watermark dedupe          → data/silver
                                        malformed rows                         → data/quarantine
                      silver_to_gold    15-min / 1-hour tumbling windows       → data/gold/…
                                        30-min sliding window every 5 min      → data/gold/trending_30m
```

## Run

Requires Docker with about 3 GB of free memory.

```bash
docker compose -f streaming_local/docker-compose.yml up -d
docker compose -f streaming_local/docker-compose.yml logs -f spark
```

- Spark UI: <http://localhost:4040> (Structured Streaming tab shows input rate, batch duration, state)
- Kafka from your machine: `localhost:29092`
- Delta tables: `streaming_local/data/`

Inspect the tables from the host (uses DuckDB's Delta reader):

```bash
python -m streaming_local.inspect_lake
```

Stop with `docker compose -f streaming_local/docker-compose.yml down`. Restart later and every
stage continues from its checkpoint in `data/_checkpoints/`.

## Concepts to look for

| Concept | Where |
|---|---|
| Kafka keys and partitions | `producer.py`: the wiki is the key, so one wiki's edits stay ordered |
| Backpressure | `producer.py` waits on `BufferError`; `maxOffsetsPerTrigger` caps each micro-batch |
| Checkpoints / exactly-once | `checkpointLocation` on every query. Kill the container and restart: no gaps, no duplicates |
| Event time vs processing time | `event_time` comes from the edit; `ingested_at` is when Spark saw it |
| Watermarks | `withWatermark("event_time", "10 minutes")` bounds dedupe state and finalizes windows |
| Dedupe within a watermark | `dropDuplicatesWithinWatermark(["event_id"])` in `bronze_to_silver.py` |
| Tumbling vs sliding windows | `silver_to_gold.py`: 15 min and 1 h tumbling; 30 min sliding every 5 min |
| Append output mode | A window is written once, after the watermark passes its end, so gold lags about 10 minutes |
| Quarantine pattern | Malformed rows go to `data/quarantine` instead of disappearing |

## Differences from the production pipeline

| | Production (`pipeline/`) | Local (`streaming_local/`) |
|---|---|---|
| Engine | DuckDB, hourly micro-batches | Spark Structured Streaming, 30-second triggers |
| Buffer and replay | EventStreams + saved `Last-Event-ID` | Kafka offsets in Spark checkpoints |
| Storage | Parquet in Supabase Storage, gold in Postgres | Delta Lake on local disk |
| Distinct editors | exact (editor lists merged in Postgres) | approximate (`approx_count_distinct`) |
| Runs on | GitHub Actions + Supabase | your laptop (Docker) |
