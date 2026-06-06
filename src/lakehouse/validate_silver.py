import great_expectations as gx
from great_expectations import expectations as E

from lakehouse.spark import get_spark

TABLE = "lakehouse.silver.silver_trips_weather"

EXPECTATIONS = [
    E.ExpectColumnValuesToNotBeNull(column="pickup_at"),
    E.ExpectColumnValuesToNotBeNull(column="temperature_c"),       # every trip matched a weather hour
    E.ExpectColumnValuesToBeBetween(column="fare_usd", min_value=0, max_value=10000),
    E.ExpectColumnValuesToBeBetween(column="trip_distance_mi", min_value=0, max_value=100),
    E.ExpectColumnValuesToBeBetween(column="passenger_count", min_value=0, max_value=8, mostly=0.99),
]


def main() -> None:
    spark = get_spark("great-expectations")
    df = spark.table(TABLE)

    context = gx.get_context()
    batch = (
        context.data_sources.add_spark("spark")
        .add_dataframe_asset("silver_trips_weather")
        .add_batch_definition_whole_dataframe("batch")
        .get_batch(batch_parameters={"dataframe": df})
    )

    all_passed = True
    for expectation in EXPECTATIONS:
        result = batch.validate(expectation)
        col = getattr(expectation, "column", "")
        print(f"[{'PASS' if result.success else 'FAIL'}] {type(expectation).__name__}({col})")
        all_passed = all_passed and result.success

    spark.stop()

    if not all_passed:
        raise SystemExit("\nData quality checks FAILED - stopping the pipeline.")
    print("\nAll data quality checks passed.")


if __name__ == "__main__":
    main()