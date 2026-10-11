"""List buckets in the MinIO server using boto3 configured for the Compose network."""
import os
from botocore.client import Config
import boto3

def main():
    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    if not endpoint.startswith("http"):
        endpoint_url = f"http://{endpoint}"
    else:
        endpoint_url = endpoint

    s3 = boto3.client('s3', endpoint_url=endpoint_url,
                      aws_access_key_id=os.getenv('MINIO_ROOT_USER','minioadmin'),
                      aws_secret_access_key=os.getenv('MINIO_ROOT_PASSWORD','minioadmin'),
                      config=Config(signature_version='s3v4'))

    buckets = s3.list_buckets().get('Buckets', [])
    print([b['Name'] for b in buckets])

if __name__ == '__main__':
    main()
