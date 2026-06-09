import os
from pathlib import Path

import boto3
import requests
from botocore.client import Config
from dotenv import load_dotenv

MINIO_ENDPOINT = "http://localhost:9000"
RAW_BUCKET = "raw"

FILENAME = "taxi_zone_lookup.csv"
SOURCE_URL = f"https://d37ci6vzurychx.cloudfront.net/misc/{FILENAME}"
LOCAL_PATH = Path("data") / FILENAME
OBJECT_KEY = f"zones/{FILENAME}"

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
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
    print(f"Saved -> {dest} ({dest.stat().st_size / 1000:.1f} KB)")


def main() -> None:
    s3 = get_s3_client()
    download(SOURCE_URL, LOCAL_PATH)
    print(f"Uploading -> s3://{RAW_BUCKET}/{OBJECT_KEY}")
    s3.upload_file(str(LOCAL_PATH), RAW_BUCKET, OBJECT_KEY)
    head = s3.head_object(Bucket=RAW_BUCKET, Key=OBJECT_KEY)
    print(f"Done. {OBJECT_KEY} is in MinIO ({head['ContentLength'] / 1000:.1f} KB)")


if __name__ == "__main__":
    main()