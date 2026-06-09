from lakehouse.spark import get_spark

SOURCE = "s3a://raw/zones/taxi_zone_lookup.csv"
TABLE = "lakehouse.bronze.taxi_zones"


def main() -> None:
    spark = get_spark("build-bronze-zones")

    print(f"Reading {SOURCE}")
    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(SOURCE)
    )

    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.bronze")
    print(f"Writing Iceberg table {TABLE}")
    df.writeTo(TABLE).createOrReplace()

    print(f"\nRows in {TABLE}: {spark.table(TABLE).count():,}")
    spark.table(TABLE).show(5, truncate=False)
    spark.stop()


if __name__ == "__main__":
    main()