# NYC Taxi & Weather Lakehouse

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Apache Spark](https://img.shields.io/badge/Apache%20Spark-3.5-E25A1C?logo=apachespark&logoColor=white)
![Apache Iceberg](https://img.shields.io/badge/Apache%20Iceberg-1.10-1789D6)
![dbt](https://img.shields.io/badge/dbt-1.11-FF694B?logo=dbt&logoColor=white)
![BigQuery](https://img.shields.io/badge/Google%20BigQuery-cloud-4285F4?logo=googlebigquery&logoColor=white)
![Airflow](https://img.shields.io/badge/Apache%20Airflow-3.2-017CEE?logo=apacheairflow&logoColor=white)
[![Live Dashboard](https://img.shields.io/badge/Live-Dashboard-FF4B4B?logo=streamlit&logoColor=white)](https://nyc-taxi-weather-lakehouse-h7tb4h8imprmlqeyaau9rh.streamlit.app/)

An end-to-end **data lakehouse** that ingests a full year of NYC taxi trips (~41M rows across yellow and green services), joins them to hourly NYC weather and the official taxi-zone geography, and serves analytics-ready tables plus a live interactive map dashboard — built **twice**, once on a local open-source stack (MinIO + Spark + Iceberg) and once on **Google BigQuery**, from the same dbt models.

🔗 **Live dashboard:** https://nyc-taxi-weather-lakehouse-h7tb4h8imprmlqeyaau9rh.streamlit.app/
📦 **Repo:** https://github.com/Shubhangi-Mittal/nyc-taxi-weather-lakehouse

---

## The finding: a "rain effect" that turned out to be noise

The original question was *do people tip more in bad weather?* One month of data (January 2024) said yes — riders tipped about **3 points more** in the rain. It looked like a clean, publishable result.

Then I scaled the pipeline to the **full year**, and the effect disappeared:

| Weather | Trips | Avg distance | Avg fare | Card tip % |
|---------|------:|-------------:|---------:|-----------:|
| Clear   | 33,564,958 | 3.44 mi | $19.84 | **25.1%** |
| Rain    | 5,738,055  | 3.32 mi | $19.76 | **25.3%** |
| Snow    | 414,928    | 3.14 mi | $18.23 | **25.4%** |

Across 2024, tipping holds near **25% in every condition** — a spread of 0.3 points. January's "rain bonus" was a single-month sampling artifact, not behavior. Plotted month by month, the rain-vs-clear tip gap swings above and below zero and averages out to roughly nothing.

That negative result is the point. Scaling from one month to a full year is exactly what turned an exciting-but-fragile claim into an honest one — and knowing the difference between a signal and noise is the whole job.

*(Counts above are the yellow-taxi baseline; adding green's ~1M trips — about 2% of volume — leaves the tip pattern unchanged.)*

**Other findings that hold up across the year:**
- **Manhattan is ~90% of yellow-taxi pickups.** Yellow cabs are overwhelmingly a Manhattan service; green cabs (and, in reality, app-based for-hire vehicles) serve the outer boroughs — which the map makes obvious.
- **Queens pickups are long and expensive** — dominated by JFK and LaGuardia airport runs.
- **Demand has a clear seasonal ramp** (climbing from ~2.9M trips in January toward ~3.6M by late spring) and sharp **daily rhythms** — weekday rush-hour bands and Friday/Saturday late nights stand out in the hour-by-day heatmap.

---

## Architecture

```mermaid
flowchart LR
    subgraph SRC[Sources]
        Y[TLC yellow trips]
        GR[TLC green trips]
        OM[Open-Meteo weather]
        TZ[TLC taxi zones]
    end

    subgraph LOCAL[Local · MinIO + Spark + Iceberg]
        RAW[(MinIO raw)]
        BZ[bronze]
        SV[silver_trips_weather]
        GD[gold marts]
    end

    subgraph CLOUD[Google Cloud]
        BQB[bronze]
        BQS[silver]
        BQG[gold marts]
    end

    DASH[Streamlit dashboard]

    Y --> RAW
    GR --> RAW
    TZ --> RAW
    RAW --> BZ
    OM --> BZ
    BZ -->|dbt-spark| SV
    SV -->|dbt tests + Great Expectations| GD

    Y --> BQB
    GR --> BQB
    OM --> BQB
    TZ --> BQB
    BQB -->|dbt-bigquery| BQS
    BQS --> BQG
    BQG --> DASH
```

The pipeline follows a **medallion** layout on both engines:

- **Bronze** — raw data landed faithfully. Locally: parquet/CSV in MinIO, registered as Iceberg tables via Spark. On the cloud: loaded into BigQuery with `bq load`.
- **Silver** — `silver_trips_weather`, one cleaned, **conformed** fact table. Yellow and green trips are each mapped to a common schema (with a `service_type` label) in their own staging models, unioned in `conformed_trips`, then joined to the matching weather hour and to pickup/dropoff boroughs. Locally it is **incremental and partitioned by month**; on BigQuery it is a full table.
- **Gold** — small, purpose-built marts that power the dashboard: weather impact, borough demand, monthly volume, month × weather, zone demand, zone × month × service, and hour × day-of-week.

Orchestration is handled by **Airflow** (local stack), and a **Great Expectations** gate plus dbt tests validate the silver layer before the gold models are trusted.

### Dual-cloud, one set of models

The same dbt models run on both engines. Engine-specific SQL (timestamp parsing, hour/month/day keys) is isolated in macros (`dbt/macros/cross_db.sql`) that branch on `target.type`, so `dbt build` produces **identical gold tables** whether the target is Spark/Iceberg or BigQuery — the full-year numbers match row-for-row. The multi-source design extends cleanly to high-volume for-hire data (Uber/Lyft): the `stg_hvfhv` pattern is BigQuery-only via a target-aware `enabled` flag, deliberately left unloaded to stay within the free tier (see caveats).

---

## Dashboard

A live, interactive [Streamlit dashboard](https://nyc-taxi-weather-lakehouse-h7tb4h8imprmlqeyaau9rh.streamlit.app/) reads the BigQuery gold tables:

- **Filters** — service (yellow / green) and borough, cascading across every view.
- **Map** — a zone-level choropleth you can scrub month by month, colored by trips or average fare.
- **Trends** — an animated borough "trip race" and a volume-vs-fare bubble animation, plus a busiest-zones leaderboard.
- **Patterns** — an hour-by-day-of-week heatmap of ridership, plus trips by hour.
- **Weather** — the tip-vs-weather finding above.

---

## Tech stack

| Layer | Tools |
|-------|-------|
| Language / packaging | Python 3.11, Poetry |
| Object storage | MinIO (S3-compatible), Docker Compose |
| Compute | Apache Spark 3.5 (PySpark) |
| Table format | Apache Iceberg 1.10 (JDBC/SQLite catalog) |
| Transformation | dbt 1.11 (`dbt-spark` session + `dbt-bigquery`) |
| Data quality | Great Expectations (Core 1.x) + dbt tests |
| Orchestration | Apache Airflow 3.2 |
| Geospatial | TLC zone shapefile → GeoJSON (reprojected to WGS84) |
| Dashboard | Streamlit + Plotly (deployed on Streamlit Community Cloud) |

---

## Repo structure

```
nyc-taxi-weather-lakehouse/
├── docker-compose.yml              # MinIO (S3-compatible object store)
├── pyproject.toml                  # Poetry project
├── spark-conf/                     # Spark/Iceberg/S3 config (gitignored)
├── src/lakehouse/
│   ├── spark.py                    # shared get_spark()
│   ├── ingest_yellow.py            # TLC parquet -> MinIO raw (--dataset yellow|green, --year, --month)
│   ├── ingest_weather.py           # Open-Meteo -> Iceberg bronze
│   ├── ingest_zones.py             # taxi-zone lookup -> MinIO raw
│   ├── build_bronze_yellow.py      # raw parquet (full-year glob) -> Iceberg bronze (--dataset)
│   ├── build_bronze_zones.py       # raw csv -> Iceberg bronze
│   ├── load_weather_bq.py          # weather -> BigQuery bronze
│   └── validate_silver.py          # Great Expectations data-quality gate
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml                # dev (Spark) + bq (BigQuery) targets
│   ├── macros/cross_db.sql         # cross-engine SQL (hour_key, month_key, hour_of_day, day_name, ...)
│   └── models/
│       ├── sources.yml
│       ├── schema.yml              # dbt tests
│       ├── staging/                # stg_yellow, stg_green, stg_weather, stg_zones, conformed_trips
│       ├── silver/                 # silver_trips_weather (conformed, incremental, partitioned)
│       └── gold/                   # weather_impact, borough_demand, monthly_volume, month_weather,
│                                   #   zone_demand, zone_month_service, hour_dow
├── dags/
│   └── lakehouse_pipeline.py       # Airflow DAG (ingest -> bronze -> dbt -> validate)
└── dashboard/
    ├── app.py                      # Streamlit dashboard over the BigQuery gold tables
    ├── make_geojson.py             # one-time: TLC shapefile -> WGS84 GeoJSON
    ├── taxi_zones.geojson          # zone geometries for the choropleth
    └── requirements.txt
```

---

## Running it

### Prerequisites
Docker, Python 3.11, Poetry, Java 17 (for Spark), and the `gcloud` CLI (for the BigQuery side).

### 1. Local lakehouse
```bash
docker compose up -d
poetry install

# ingest a full year of yellow + green taxi data
for m in 01 02 03 04 05 06 07 08 09 10 11 12; do
  poetry run python -m lakehouse.ingest_yellow --year 2024 --month $m
  poetry run python -m lakehouse.ingest_yellow --dataset green --year 2024 --month $m
done
poetry run python -m lakehouse.build_bronze_yellow --year 2024
poetry run python -m lakehouse.build_bronze_yellow --dataset green --year 2024

# weather + zones
poetry run python -m lakehouse.ingest_weather --year 2024
poetry run python -m lakehouse.ingest_zones
poetry run python -m lakehouse.build_bronze_zones

# transform + test
export SPARK_CONF_DIR="$PWD/spark-conf"
poetry run dbt build --project-dir dbt --profiles-dir dbt --full-refresh
poetry run python -m lakehouse.validate_silver
```

### 2. BigQuery mirror
```bash
gcloud auth application-default login
bq mk --location=US --dataset nyc-lakehouse:bronze
bq mk --location=US --dataset nyc-lakehouse:lakehouse

# load yellow, green, weather, zones, then run the same models on the cloud
bq load --replace --source_format=PARQUET nyc-lakehouse:bronze.yellow_trips data/yellow_tripdata_2024-01.parquet
for m in 02 03 04 05 06 07 08 09 10 11 12; do
  bq load --source_format=PARQUET nyc-lakehouse:bronze.yellow_trips data/yellow_tripdata_2024-$m.parquet
done
bq load --replace --source_format=PARQUET nyc-lakehouse:bronze.green_trips data/green_tripdata_2024-01.parquet
for m in 02 03 04 05 06 07 08 09 10 11 12; do
  bq load --source_format=PARQUET nyc-lakehouse:bronze.green_trips data/green_tripdata_2024-$m.parquet
done
poetry run python -m lakehouse.load_weather_bq --year 2024
bq load --replace --source_format=CSV --autodetect nyc-lakehouse:bronze.taxi_zones data/taxi_zone_lookup.csv

poetry run dbt build --target bq --project-dir dbt --profiles-dir dbt --full-refresh
```

### 3. Dashboard
```bash
python3.11 -m venv ~/dashboard-venv
source ~/dashboard-venv/bin/activate
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```
(The zone GeoJSON is generated once via `dashboard/make_geojson.py` and committed to the repo.)

### 4. Orchestration (Airflow)
The DAG `lakehouse_pipeline` runs the local flow (ingest → bronze → dbt → validate) as a linear chain. See `dags/lakehouse_pipeline.py`; it runs in an isolated Airflow virtualenv.

---

## Engineering notes & gotchas

The interesting problems solved along the way — the stuff that doesn't show up in a clean final commit:

- **Multi-source conformance.** Yellow and green have similar-but-different schemas (`tpep_` vs `lpep_` columns); each is mapped to a common shape in its own staging model and unioned in `conformed_trips`. HVFHV (Uber/Lyft) is wired the same way but BigQuery-only via a target-aware `enabled` flag.
- **Iceberg catalog choice.** Started with a Hadoop catalog, but dbt's view-based builds failed because listing namespaces over S3 isn't supported. Migrated to a **JDBC (SQLite) catalog** (with `jdbc.schema-version=V1` for views).
- **Memory tuning on 16 GB.** The full-year build (~41M raw rows) is the heavy step. Lowered Docker Desktop's RAM allocation to free host memory for Spark and bumped `spark.driver.memory` to 4 GB — in local mode the driver does all the work.
- **Cross-engine portability.** Engine differences (timestamp parsing, `hour`/`extract`, day-name formatting) live in `cross_db.sql` macros that branch on `target.type`, so the models themselves stay identical across Spark/Iceberg and BigQuery.
- **Incremental done correctly.** The silver model uses `insert_overwrite` partitioned by month, and the incremental filter re-selects *whole* months — overwriting by partition with a half-month would silently drop rows.
- **Geospatial reprojection.** The TLC zone shapefile ships in NY State Plane (EPSG:2263, feet); it's reprojected to WGS84 lat/lon for the web map — skip this and the choropleth renders blank.
- **Large-file Git push.** The ~4 MB GeoJSON failed to push with `HTTP 400 / sideband disconnect` until `git config http.postBuffer` was raised — a classic git-over-HTTPS limit.
- **Signal vs. noise.** The headline lesson: a result from one month (the rain-tip effect) didn't survive a full year.

---

## Data caveats

- **Scope:** 2024, yellow + green taxis. High-volume for-hire vehicles (Uber/Lyft, ~230M rows/year) are intentionally left out of the live build — the conformance code supports them, but loading them would push BigQuery past the 10 GB free storage tier, so it's a deliberate cost decision rather than a technical gap.
- **Tips:** only card payments record a tip, so all tip-percentage figures are over card trips (`payment_type = 1`).
- **Weather granularity:** a single city-wide hourly reading is joined to every trip in that hour; it doesn't capture neighborhood-level variation.
- **Correlational:** these are observed associations, not causal claims.

---

## Roadmap

- [x] Local lakehouse: MinIO + Spark + Iceberg, medallion layers
- [x] dbt transformations with tests
- [x] Great Expectations data-quality gate
- [x] Airflow orchestration
- [x] BigQuery dual-cloud mirror from the same models
- [x] Spatial dimension (taxi zones / boroughs) + interactive choropleth map
- [x] Full-year scale (~41M trips) with incremental, month-partitioned models
- [x] Multi-source conformance (yellow + green into one fact)
- [x] Live interactive, animated dashboard (service/borough filters, scrub map, hour-by-day heatmap, animated trends)
- [ ] High-volume for-hire (Uber/Lyft) at scale — wired for BigQuery, deferred to stay within the free tier
- [ ] CI: automated `dbt build` + data-quality checks on every push
- [ ] Streaming variant (Kafka + Spark Structured Streaming)