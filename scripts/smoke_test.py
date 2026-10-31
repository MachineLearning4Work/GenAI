"""Check real API authentication and MinIO round trips without calling an LLM."""

import os
import time
import urllib.error
import urllib.request
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def http_status(url: str, token: str | None = None) -> int:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=headers), timeout=3
        ) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def wait_for_health(url: str, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if http_status(url) == 200:
                return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(2)
    raise RuntimeError("Service did not become healthy before the smoke-test deadline")


def main() -> None:
    api_url = "http://localhost:8000"
    secure = os.getenv("MINIO_SECURE", "false").lower() in {"1", "true", "yes", "on"}
    endpoint = f"{'https' if secure else 'http'}://{os.environ['MINIO_ENDPOINT']}"
    wait_for_health(f"{api_url}/health")
    wait_for_health(f"{endpoint}/minio/health/ready")

    proposal_url = f"{api_url}/business-proposals/smoke-{uuid4().hex}"
    if http_status(proposal_url) != 401:
        raise RuntimeError("Proposal API did not reject an unauthenticated request")
    if http_status(proposal_url, os.environ["API_ACCESS_TOKEN"]) != 404:
        raise RuntimeError("Authenticated proposal lookup did not return the expected 404")

    region = os.getenv("MINIO_REGION", "us-east-1")
    bucket = os.getenv("MINIO_BUCKET_NAME", "business-plan-bucket")
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        region_name=region,
        config=Config(
            connect_timeout=3,
            read_timeout=5,
            retries={"total_max_attempts": 1},
            s3={"addressing_style": "path"},
        ),
    )
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        options = {} if region == "us-east-1" else {
            "CreateBucketConfiguration": {"LocationConstraint": region}
        }
        client.create_bucket(Bucket=bucket, **options)

    key = f"ci-smoke/{uuid4().hex}.txt"
    payload = b"business-plan storage smoke test"
    client.put_object(Bucket=bucket, Key=key, Body=payload, ContentType="text/plain")
    try:
        body = client.get_object(Bucket=bucket, Key=key)["Body"]
        try:
            if body.read() != payload:
                raise RuntimeError("MinIO round-trip contents differ")
        finally:
            body.close()
    finally:
        client.delete_object(Bucket=bucket, Key=key)
    print("Smoke test passed: API health, authentication, and MinIO write/read/delete")


if __name__ == "__main__":
    main()
