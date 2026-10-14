"""Kafka -> Bronze: land raw messages unchanged, with Kafka metadata for traceability."""

from pyspark.sql import functions as F

from streaming_local.jobs.common import BRONZE, CHECKPOINTS, KAFKA_BOOTSTRAP, TOPIC, spark_session


def start(spark):
    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", TOPIC)
        .option("startingOffsets", "earliest")
        .option("maxOffsetsPerTrigger", 20000)  # cap each micro-batch so a backlog cannot OOM the driver
        .load()
    )
    bronze = raw.select(
        F.col("key").cast("string").alias("wiki"),
        F.col("value").cast("string").alias("raw_json"),
        "partition",
        "offset",
        F.col("timestamp").alias("kafka_timestamp"),
        F.current_timestamp().alias("ingested_at"),
    ).withColumn("ingest_date", F.to_date("kafka_timestamp"))

    return (
        bronze.writeStream.format("delta")
        .outputMode("append")
        .option("checkpointLocation", f"{CHECKPOINTS}/bronze")  # never delete: it holds the Kafka offsets
        .partitionBy("ingest_date")
        .trigger(processingTime="30 seconds")
        .queryName("kafka_to_bronze")
        .start(BRONZE)
    )


if __name__ == "__main__":
    start(spark_session("kafka_to_bronze")).awaitTermination()
