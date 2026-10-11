"""Create MinIO bucket using boto3 S3 client configured to the MinIO endpoint.

This script reads environment variables set by Docker Compose and attempts to
create the configured bucket. It is idempotent: if the bucket exists it exits
successfully.
"""
import os
import boto3
from botocore.client import Config


def main():
    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    access_key = os.getenv("MINIO_ROOT_USER", "minioadmin")
    secret_key = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
    bucket = os.getenv("MINIO_BUCKET_NAME", "business-plan-bucket")

    # Ensure endpoint_url includes scheme
    if not endpoint.startswith("http"):
        endpoint_url = f"http://{endpoint}"
    else:
        endpoint_url = endpoint

    s3 = boto3.resource(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

    try:
        bucket_obj = s3.Bucket(bucket)
        if bucket_obj.creation_date:
            print(f"Bucket '{bucket}' already exists")
            return 0
        # Create bucket (MinIO ignores location constraint)
        s3.create_bucket(Bucket=bucket)
        print(f"Bucket '{bucket}' created")
        return 0
    except Exception as e:
        print("Failed to create or verify bucket:", e)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
