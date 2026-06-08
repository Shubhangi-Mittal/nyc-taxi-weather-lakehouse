import requests
from google.cloud import bigquery

LAT, LON = 40.7128, -74.0060
START, END = "2024-01-01", "2024-01-31"
VARS = ["temperature_2m", "precipitation", "snowfall", "wind_speed_10m"]
TABLE = "nyc-lakehouse.bronze.weather"

URL = (
    "https://archive-api.open-meteo.com/v1/archive"
    f"?latitude={LAT}&longitude={LON}"
    f"&start_date={START}&end_date={END}"
    f"&hourly={','.join(VARS)}"
    "&timezone=America/New_York"
)


def main() -> None:
    hourly = requests.get(URL, timeout=60).json()["hourly"]
    rows = [
        {"time": hourly["time"][i], **{v: hourly[v][i] for v in VARS}}
        for i in range(len(hourly["time"]))
    ]

    client = bigquery.Client()                       # uses your gcloud ADC login
    job = client.load_table_from_json(
        rows,
        TABLE,
        job_config=bigquery.LoadJobConfig(
            autodetect=True,
            write_disposition="WRITE_TRUNCATE",      # replace on re-run
        ),
    )
    job.result()                                     # wait for the load to finish
    print(f"Loaded {len(rows)} rows into {TABLE}")


if __name__ == "__main__":
    main()