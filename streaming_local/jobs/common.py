"""Shared paths and helpers for the Spark Structured Streaming jobs."""

import os
import time

from pyspark.sql import SparkSession
from pyspark.sql.types import BooleanType, IntegerType, LongType, StringType, StructField, StructType

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "wiki_recentchange")
LAKE = os.getenv("LAKE_DIR", "/data")

BRONZE = f"{LAKE}/bronze"
SILVER = f"{LAKE}/silver"
QUARANTINE = f"{LAKE}/quarantine"
GOLD_PAGE_15M = f"{LAKE}/gold/page_activity_15m"
GOLD_WIKI_HOURLY = f"{LAKE}/gold/wiki_activity_hourly"
GOLD_TRENDING = f"{LAKE}/gold/trending_30m"
CHECKPOINTS = f"{LAKE}/_checkpoints"

_old_new = StructType([StructField("old", LongType()), StructField("new", LongType())])

RECENTCHANGE_SCHEMA = StructType([
    StructField("meta", StructType([
        StructField("id", StringType()),
        StructField("dt", StringType()),
        StructField("domain", StringType()),
    ])),
    StructField("type", StringType()),
    StructField("namespace", IntegerType()),
    StructField("title", StringType()),
    StructField("timestamp", LongType()),
    StructField("user", StringType()),
    StructField("bot", BooleanType()),
    StructField("minor", BooleanType()),
    StructField("wiki", StringType()),
    StructField("length", _old_new),
    StructField("revision", _old_new),
])


def spark_session(app_name: str) -> SparkSession:
    # Delta and Kafka packages are passed by spark-submit (see docker-compose.yml).
    return (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def wait_for_table(path: str, timeout_s: int = 900) -> None:
    """Blocks until the upstream job has created its Delta table (needed before readStream)."""
    deadline = time.time() + timeout_s
    while not os.path.isdir(f"{path}/_delta_log"):
        if time.time() > deadline:
            raise TimeoutError(f"no Delta table at {path}")
        print(f"waiting for {path} ...", flush=True)
        time.sleep(10)
