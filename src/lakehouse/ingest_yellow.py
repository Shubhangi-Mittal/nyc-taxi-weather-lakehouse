import argparse
import os
from pathlib import Path

import boto3
import requests
from botocore.client import Config
from dotenv import load_dotenv

MINIO_ENDPOINT = "http://localhost:9000"
RAW_BUCKET = "raw"
DATASET = "yellow"

load_dotenv()
ACCESS_KEY = os.environ["MINIO_ROOT_USER"]
SECRET_KEY = os.environ["MINIO_ROOT_PASSWORD"]


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}")
    with requests.get(url, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
    print(f"Saved -> {dest} ({dest.stat().st_size / 1_000_000:.1f} MB)")


def ingest(year: str, month: str) -> None:
    filename = f"{DATASET}_tripdata_{year}-{month}.parquet"
    source_url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/{filename}"
    local_path = Path("data") / filename
    object_key = f"{DATASET}/{filename}"

    s3 = get_s3_client()
    download(source_url, local_path)
    print(f"Uploading -> s3://{RAW_BUCKET}/{object_key}")
    s3.upload_file(str(local_path), RAW_BUCKET, object_key)
    head = s3.head_object(Bucket=RAW_BUCKET, Key=object_key)
    print(f"Done. {object_key} in MinIO ({head['ContentLength'] / 1_000_000:.1f} MB)")


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest one month of yellow-taxi data to MinIO raw.")
    p.add_argument("--year", default="2024")
    p.add_argument("--month", default="01")
    args = p.parse_args()
    ingest(args.year, args.month)


if __name__ == "__main__":
    main()