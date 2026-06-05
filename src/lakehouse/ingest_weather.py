import requests
from lakehouse.spark import get_spark

LAT, LON = 40.7128, -74.0060
START, END = "2024-01-01", "2024-01-31"
VARS = ["temperature_2m", "precipitation", "snowfall", "wind_speed_10m"]
TABLE = "lakehouse.bronze.weather"

URL = (
    "https://archive-api.open-meteo.com/v1/archive"
    f"?latitude={LAT}&longitude={LON}"
    f"&start_date={START}&end_date={END}"
    f"&hourly={','.join(VARS)}"
    "&timezone=America/New_York"
)


def fetch_rows() -> list[dict]:
    print(f"Fetching {URL}")
    resp = requests.get(URL, timeout=60)
    resp.raise_for_status()
    hourly = resp.json()["hourly"]   
    times = hourly["time"]
    return [
        {"time": times[i], **{v: hourly[v][i] for v in VARS}}
        for i in range(len(times))
    ]


def main() -> None:
    rows = fetch_rows()
    print(f"Got {len(rows)} hourly records")

    spark = get_spark("ingest-weather")
    df = spark.createDataFrame(rows)   

    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.bronze")
    df.writeTo(TABLE).createOrReplace()

    print(f"\nRows in {TABLE}: {spark.table(TABLE).count():,}")
    spark.table(TABLE).show(5, truncate=False)
    spark.stop()


if __name__ == "__main__":
    main()