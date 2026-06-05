import os
from dotenv import load_dotenv
from pyspark.sql import SparkSession

MINIO_ENDPOINT = "http://localhost:9000"
ICEBERG_VERSION = "1.10.2"        
HADOOP_AWS_VERSION = "3.3.4"   

SOURCE = "s3a://raw/yellow/yellow_tripdata_2024-01.parquet"
TABLE = "lakehouse.bronze.yellow_trips"

PACKAGES = (
    f"org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:{ICEBERG_VERSION},"
    f"org.apache.hadoop:hadoop-aws:{HADOOP_AWS_VERSION}"
)

load_dotenv()
ACCESS_KEY = os.environ["MINIO_ROOT_USER"]
SECRET_KEY = os.environ["MINIO_ROOT_PASSWORD"]

def get_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("build-bronze-yellow")
        .config("spark.jars.packages", PACKAGES)
        
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        
        .config("spark.sql.catalog.lakehouse", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.lakehouse.type", "hadoop")
        .config("spark.sql.catalog.lakehouse.warehouse", "s3a://warehouse/")
        
        .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
        .config("spark.hadoop.fs.s3a.access.key", ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key", SECRET_KEY)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")        
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")  
        .config("spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
        
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def main() -> None:
    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")  

    print(f"Reading {SOURCE}")
    df = spark.read.parquet(SOURCE)

    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.bronze")

    print(f"Writing Iceberg table {TABLE}")
    df.writeTo(TABLE).createOrReplace()   

    print(f"\nRows in {TABLE}: {spark.table(TABLE).count():,}")
    print("\nSchema:")
    spark.table(TABLE).printSchema()
    print("Snapshots (Iceberg's time-travel history):")
    spark.sql(f"SELECT snapshot_id, committed_at FROM {TABLE}.snapshots").show(truncate=False)

    spark.stop()

if __name__ == "__main__":
    main()
