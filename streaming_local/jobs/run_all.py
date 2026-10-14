"""Runs bronze, silver and gold streaming queries in one Spark application (one JVM, laptop-friendly)."""

from streaming_local.jobs import bronze_to_silver, kafka_to_bronze, silver_to_gold
from streaming_local.jobs.common import spark_session

if __name__ == "__main__":
    spark = spark_session("wikipulse_streaming")
    spark.sparkContext.setLogLevel("WARN")
    kafka_to_bronze.start(spark)
    bronze_to_silver.start(spark)   # waits until bronze has its first commit
    silver_to_gold.start(spark)     # waits until silver has its first commit
    print("all streaming queries running; Spark UI at http://localhost:4040", flush=True)
    spark.streams.awaitAnyTermination()
