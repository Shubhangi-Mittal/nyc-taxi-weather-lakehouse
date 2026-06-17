import argparse

from lakehouse.spark import get_spark

TABLE = "lakehouse.bronze.yellow_trips"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="yellow")
    p.add_argument("--year", default="2024")
    args = p.parse_args()

    source = f"s3a://raw/{args.dataset}/{args.dataset}_tripdata_{args.year}-*.parquet"
    table = f"lakehouse.bronze.{args.dataset}_trips"
    spark = get_spark(f"build-bronze-{args.dataset}")

    print(f"Reading {source}")
    df = spark.read.option("mergeSchema", "true").parquet(source)
    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.bronze")
    print(f"Writing Iceberg table {table}")
    df.writeTo(table).createOrReplace()
    print(f"\nRows in {table}: {spark.table(table).count():,}")
    spark.stop()



if __name__ == "__main__":
    main()