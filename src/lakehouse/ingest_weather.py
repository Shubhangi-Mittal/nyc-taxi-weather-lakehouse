import argparse

import requests

from lakehouse.spark import get_spark

LAT, LON = 40.7128, -74.0060
VARS = ["temperature_2m", "precipitation", "snowfall", "wind_speed_10m"]
TABLE = "lakehouse.bronze.weather"


def fetch_rows(start: str, end: str) -> list[dict]:
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LAT}&longitude={LON}"
        f"&start_date={start}&end_date={end}"
        f"&hourly={','.join(VARS)}"
        "&timezone=America/New_York"
    )
    print(f"Fetching {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    hourly = resp.json()["hourly"]
    times = hourly["time"]
    return [
        {"time": times[i], **{v: hourly[v][i] for v in VARS}}
        for i in range(len(times))
    ]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--year", default="2024")
    args = p.parse_args()

    rows = fetch_rows(f"{args.year}-01-01", f"{args.year}-12-31")
    print(f"Got {len(rows)} hourly records")

    spark = get_spark("ingest-weather")
    df = spark.createDataFrame(rows)
    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.bronze")
    df.writeTo(TABLE).createOrReplace()

    print(f"\nRows in {TABLE}: {spark.table(TABLE).count():,}")
    spark.stop()


if __name__ == "__main__":
    main()