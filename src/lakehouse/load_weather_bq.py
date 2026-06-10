import argparse

import requests
from google.cloud import bigquery

LAT, LON = 40.7128, -74.0060
VARS = ["temperature_2m", "precipitation", "snowfall", "wind_speed_10m"]
TABLE = "nyc-lakehouse.bronze.weather"


def fetch_rows(start: str, end: str) -> list[dict]:
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LAT}&longitude={LON}"
        f"&start_date={start}&end_date={end}"
        f"&hourly={','.join(VARS)}"
        "&timezone=America/New_York"
    )
    hourly = requests.get(url, timeout=120).json()["hourly"]
    return [
        {"time": hourly["time"][i], **{v: hourly[v][i] for v in VARS}}
        for i in range(len(hourly["time"]))
    ]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--year", default="2024")
    args = p.parse_args()

    rows = fetch_rows(f"{args.year}-01-01", f"{args.year}-12-31")
    client = bigquery.Client()
    job = client.load_table_from_json(
        rows,
        TABLE,
        job_config=bigquery.LoadJobConfig(
            autodetect=True,
            write_disposition="WRITE_TRUNCATE",
        ),
    )
    job.result()
    print(f"Loaded {len(rows)} rows into {TABLE}")


if __name__ == "__main__":
    main()