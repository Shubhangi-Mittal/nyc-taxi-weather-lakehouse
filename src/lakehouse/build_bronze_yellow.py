import argparse

from lakehouse.spark import get_spark

TABLE = "lakehouse.bronze.yellow_trips"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--year", default="2024")
    args = p.parse_args()

    source = f"s3a://raw/yellow/yellow_tripdata_{args.year}-*.parquet"
    spark = get_spark("build-bronze-yellow")

    print(f"Reading {source}")
    df = spark.read.option("mergeSchema", "true").parquet(source)

    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.bronze")
    print(f"Writing Iceberg table {TABLE}")
    df.writeTo(TABLE).createOrReplace()

    print(f"\nRows in {TABLE}: {spark.table(TABLE).count():,}")
    spark.stop()


if __name__ == "__main__":
    main()