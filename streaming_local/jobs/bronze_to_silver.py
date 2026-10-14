"""Bronze -> Silver: parse, type, derive columns, dedupe within a watermark; bad rows to quarantine.

Mirrors pipeline/sql/silver.sql, using the shared rules in pipeline/rules.py.
"""

from pyspark.sql import functions as F

from pipeline.rules import ANON_USER_REGEX
from streaming_local.jobs.common import (
    BRONZE, CHECKPOINTS, QUARANTINE, RECENTCHANGE_SCHEMA, SILVER, spark_session, wait_for_table,
)


def start(spark):
    wait_for_table(BRONZE)
    parsed = (
        spark.readStream.format("delta").load(BRONZE)
        .withColumn("e", F.from_json("raw_json", RECENTCHANGE_SCHEMA))
    )
    valid = (
        F.col("e.meta.id").isNotNull() & F.col("e.timestamp").isNotNull()
        & F.col("e.title").isNotNull() & F.col("e.wiki").isNotNull()
    )

    silver = (
        parsed.filter(valid)
        .select(
            F.col("e.meta.id").alias("event_id"),
            F.col("e.type").alias("change_type"),
            F.col("e.wiki").alias("wiki"),
            F.col("e.title").alias("title"),
            F.col("e.namespace").alias("namespace"),
            F.col("e.user").alias("user_name"),
            F.coalesce(F.col("e.bot"), F.lit(False)).alias("is_bot"),
            F.coalesce(F.col("e.minor"), F.lit(False)).alias("is_minor"),
            F.coalesce(F.col("e.user"), F.lit("")).rlike(ANON_USER_REGEX).alias("is_anonymous"),
            (F.coalesce(F.col("e.length.new"), F.lit(0)) - F.coalesce(F.col("e.length.old"), F.lit(0)))
                .alias("bytes_changed"),
            F.col("e.revision.new").alias("revision_id"),
            F.timestamp_seconds(F.col("e.timestamp")).alias("event_time"),
            "ingested_at",
        )
        .withColumn("event_date", F.to_date("event_time"))
        .withColumn("ingest_lag_sec", F.unix_timestamp("ingested_at") - F.unix_timestamp("event_time"))
        # Remember event ids for 10 minutes of event time, then drop that state.
        .withWatermark("event_time", "10 minutes")
        .dropDuplicatesWithinWatermark(["event_id"])
    )

    silver_query = (
        silver.writeStream.format("delta")
        .outputMode("append")
        .option("checkpointLocation", f"{CHECKPOINTS}/silver")
        .partitionBy("event_date")
        .trigger(processingTime="30 seconds")
        .queryName("bronze_to_silver")
        .start(SILVER)
    )

    quarantine_query = (
        parsed.filter(~valid | F.col("e").isNull())
        .select("raw_json", "ingested_at", F.lit("missing_required_fields").alias("reason"))
        .writeStream.format("delta")
        .outputMode("append")
        .option("checkpointLocation", f"{CHECKPOINTS}/quarantine")
        .trigger(processingTime="1 minute")
        .queryName("quarantine")
        .start(QUARANTINE)
    )
    return [silver_query, quarantine_query]


if __name__ == "__main__":
    spark = spark_session("bronze_to_silver")
    start(spark)
    spark.streams.awaitAnyTermination()
