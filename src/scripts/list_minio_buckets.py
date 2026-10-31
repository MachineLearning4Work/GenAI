"""List buckets in the MinIO server using boto3 configured for the Compose network."""
import os

import boto3
from botocore.client import Config


def main():
    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    access_key = os.getenv("MINIO_ROOT_USER")
    secret_key = os.getenv("MINIO_ROOT_PASSWORD")
    if not access_key or not secret_key:
        raise SystemExit(
            "MINIO_ROOT_USER and MINIO_ROOT_PASSWORD must be set."
        )

    if not endpoint.startswith("http"):
        endpoint_url = f"http://{endpoint}"
    else:
        endpoint_url = endpoint

    s3 = boto3.client('s3', endpoint_url=endpoint_url,
                      aws_access_key_id=access_key,
                      aws_secret_access_key=secret_key,
                      config=Config(signature_version='s3v4'))

    buckets = s3.list_buckets().get('Buckets', [])
    print([b['Name'] for b in buckets])

if __name__ == '__main__':
    main()
