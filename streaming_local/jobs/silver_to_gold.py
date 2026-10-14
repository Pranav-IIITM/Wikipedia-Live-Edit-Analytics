"""Silver -> Gold with event-time windows.

- page_activity_15m:   tumbling 15-minute windows per article (same grain as the batch pipeline)
- wiki_activity_hourly: tumbling 1-hour windows per wiki
- trending_30m:        sliding 30-minute windows every 5 minutes, human edits only

Append mode writes a window once the watermark passes its end, so gold lags ~10 minutes.
"""

from pyspark.sql import functions as F

from pipeline.rules import BUCKET_MINUTES, TRENDING_MIN_HUMAN_EDITS
from streaming_local.jobs.common import (
    CHECKPOINTS, GOLD_PAGE_15M, GOLD_TRENDING, GOLD_WIKI_HOURLY, SILVER, spark_session, wait_for_table,
)

def _human():
    return (~F.col("is_bot")).cast("int")


def _bot():
    return F.col("is_bot").cast("int")


def _write(df, path, name, partition=None):
    writer = (
        df.writeStream.format("delta")
        .outputMode("append")
        .option("checkpointLocation", f"{CHECKPOINTS}/{name}")
        .trigger(processingTime="1 minute")
        .queryName(name)
    )
    if partition:
        writer = writer.partitionBy(partition)
    return writer.start(path)


def start(spark):
    wait_for_table(SILVER)
    silver = spark.readStream.format("delta").load(SILVER).withWatermark("event_time", "10 minutes")

    page_15m = (
        silver.groupBy(F.window("event_time", f"{BUCKET_MINUTES} minutes"), "wiki", "title")
        .agg(
            F.count("*").alias("edits"),
            F.sum(_human()).alias("human_edits"),
            F.sum(_bot()).alias("bot_edits"),
            F.sum((F.col("change_type") == "new").cast("int")).alias("new_pages"),
            F.sum("bytes_changed").alias("bytes_changed"),
            F.approx_count_distinct(F.when(~F.col("is_bot"), F.col("user_name"))).alias("editors"),
        )
        .select(F.col("window.start").alias("bucket_start"), "wiki", "title", "edits", "human_edits",
                "bot_edits", "new_pages", "bytes_changed", "editors")
        .withColumn("bucket_date", F.to_date("bucket_start"))
    )

    wiki_hourly = (
        silver.groupBy(F.window("event_time", "1 hour"), "wiki")
        .agg(
            F.count("*").alias("edits"),
            F.sum(_human()).alias("human_edits"),
            F.sum(_bot()).alias("bot_edits"),
            F.sum(F.col("is_anonymous").cast("int")).alias("anon_edits"),
            F.sum((F.col("change_type") == "new").cast("int")).alias("new_pages"),
            F.sum("bytes_changed").alias("bytes_changed"),
            F.sum(F.greatest(F.col("bytes_changed"), F.lit(0))).alias("bytes_added"),
        )
        .select(F.col("window.start").alias("hour_start"), "wiki", "edits", "human_edits", "bot_edits",
                "anon_edits", "new_pages", "bytes_changed", "bytes_added")
    )

    trending = (
        silver.filter(~F.col("is_bot"))
        .groupBy(F.window("event_time", "30 minutes", "5 minutes"), "wiki", "title")
        .agg(
            F.count("*").alias("human_edits"),
            F.approx_count_distinct("user_name").alias("editors"),
        )
        .filter(F.col("human_edits") >= TRENDING_MIN_HUMAN_EDITS)
        .select(F.col("window.start").alias("window_start"), F.col("window.end").alias("window_end"),
                "wiki", "title", "human_edits", "editors")
    )

    return [
        _write(page_15m, GOLD_PAGE_15M, "gold_page_15m", partition="bucket_date"),
        _write(wiki_hourly, GOLD_WIKI_HOURLY, "gold_wiki_hourly"),
        _write(trending, GOLD_TRENDING, "gold_trending_30m"),
    ]


if __name__ == "__main__":
    spark = spark_session("silver_to_gold")
    start(spark)
    spark.streams.awaitAnyTermination()
