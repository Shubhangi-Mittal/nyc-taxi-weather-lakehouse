"""
Airflow DAG: orchestrate the NYC taxi + weather lakehouse end to end.

Airflow only conducts — each task shells out to the project's Poetry
environment, so your existing scripts and dbt do the actual work.
"""

import pendulum

from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

PROJECT_DIR = "/Users/shubhangimittal/nyc-taxi-weather-lakehouse"

# Prefix for every task:
#   unset VIRTUAL_ENV  -> ignore Airflow's venv so poetry uses the PROJECT's .venv
#   PATH               -> make Homebrew's poetry findable
#   JAVA_HOME          -> Spark needs it
#   cd                 -> run from the repo root so relative paths resolve
BASE = (
    'unset VIRTUAL_ENV && '
    'export PATH="/opt/homebrew/bin:$PATH" && '
    'export JAVA_HOME=$(/usr/libexec/java_home -v 17) && '
    f'cd {PROJECT_DIR} &&'
)

with DAG(
    dag_id="lakehouse_pipeline",
    description="ingest -> bronze -> dbt -> data-quality gate",
    schedule="@daily",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,            # don't backfill every day since the start_date
    max_active_tasks=1,       # one task at a time (see WHY below)
    tags=["lakehouse"],
) as dag:

    ingest_yellow = BashOperator(
        task_id="ingest_yellow",
        bash_command=f"{BASE} poetry run python -m lakehouse.ingest_yellow",
    )

    build_bronze_yellow = BashOperator(
        task_id="build_bronze_yellow",
        bash_command=f"{BASE} poetry run python -m lakehouse.build_bronze_yellow",
    )

    ingest_weather = BashOperator(
        task_id="ingest_weather",
        bash_command=f"{BASE} poetry run python -m lakehouse.ingest_weather",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"{BASE} SPARK_CONF_DIR={PROJECT_DIR}/spark-conf "
            f"poetry run dbt build --project-dir dbt --profiles-dir dbt"
        ),
    )

    validate_silver = BashOperator(
        task_id="validate_silver",
        bash_command=f"{BASE} poetry run python -m lakehouse.validate_silver",
    )

    ingest_yellow >> build_bronze_yellow >> ingest_weather >> dbt_build >> validate_silver