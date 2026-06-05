from lakehouse.spark import get_spark

SOURCE = "s3a://raw/yellow/yellow_tripdata_2024-01.parquet"
TABLE = "lakehouse.bronze.yellow_trips"


def main() -> None:
    spark = get_spark("build-bronze-yellow")

    print(f"Reading {SOURCE}")
    df = spark.read.parquet(SOURCE)

    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.bronze")
    print(f"Writing Iceberg table {TABLE}")
    df.writeTo(TABLE).createOrReplace()

    print(f"\nRows in {TABLE}: {spark.table(TABLE).count():,}")
    spark.stop()


if __name__ == "__main__":
    main()