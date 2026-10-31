"""MinIO artifact storage (S3-compatible).

The legacy demo mirrors artifacts on a best-effort basis. Proposal artifacts
use the strict JSON methods and fail visibly if MinIO is unavailable.
"""
import json
import logging
import threading
from pathlib import Path
from typing import Any

from . import config

logger = logging.getLogger(__name__)


class ObjectStoreError(RuntimeError):
    """Raised when a required proposal artifact cannot be stored or retrieved."""


_lock = threading.Lock()
_client = None
_bucket_ready = False
_disabled_reason: str | None = None

CONTENT_TYPES = {
    ".json": "application/json",
    ".md": "text/markdown",
    ".txt": "text/plain",
}


def content_type_for(path: Path) -> str:
    return CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


def object_key(run_id: str, filename: str) -> str:
    return f"runs/{run_id}/{filename}"


def _disable(reason: str) -> None:
    """Record the first failure so later uploads short-circuit silently."""
    global _disabled_reason, _bucket_ready
    _disabled_reason = reason
    _bucket_ready = False
    logger.warning(
        "MinIO operations disabled for this process (%s). Local artifacts remain "
        "under %s.",
        reason,
        config.RUNS_DIR,
    )


def _build_client():
    import boto3
    from botocore.client import Config as BotoConfig

    if not config.MINIO_ROOT_USER or not config.MINIO_ROOT_PASSWORD:
        raise RuntimeError("MinIO credentials are not configured")
    return boto3.client(
        "s3",
        endpoint_url=config.minio_endpoint_url(),
        aws_access_key_id=config.MINIO_ROOT_USER,
        aws_secret_access_key=config.MINIO_ROOT_PASSWORD,
        region_name=config.MINIO_REGION,
        config=BotoConfig(
            signature_version="s3v4",
            connect_timeout=config.MINIO_CONNECT_TIMEOUT,
            read_timeout=config.MINIO_READ_TIMEOUT,
            retries={"max_attempts": 1},
        ),
    )


def get_client(strict: bool = False):
    """Return a cached S3 client or raise for unavailable strict operations."""
    global _client
    if not config.MINIO_ENABLED:
        if strict:
            raise ObjectStoreError("MinIO storage is disabled")
        return None
    if _disabled_reason and not strict:
        return None
    with _lock:
        if _client is None:
            try:
                _client = _build_client()
            except Exception:
                if strict:
                    raise ObjectStoreError("MinIO client initialization failed") from None
                _disable("client initialization failed")
                return None
    return _client


def ensure_bucket(strict: bool = False) -> bool:
    """Create the configured bucket if needed. Returns True when usable."""
    global _bucket_ready
    if not config.MINIO_ENABLED:
        if strict:
            raise ObjectStoreError("MinIO storage is disabled")
        return False
    if _disabled_reason and not strict:
        return False
    if _bucket_ready:
        return True
    client = get_client(strict=strict)
    if client is None:
        return False
    from botocore.exceptions import ClientError

    with _lock:
        if _bucket_ready:
            return True
        try:
            client.head_bucket(Bucket=config.MINIO_BUCKET_NAME)
            _bucket_ready = True
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status != 404:
                if strict:
                    raise ObjectStoreError("MinIO bucket check failed") from None
                _disable("bucket check failed")
                return False
            try:
                client.create_bucket(Bucket=config.MINIO_BUCKET_NAME)
                _bucket_ready = True
            except Exception:
                if strict:
                    raise ObjectStoreError("MinIO bucket creation failed") from None
                _disable("bucket creation failed")
                return False
        except Exception:
            if strict:
                raise ObjectStoreError("MinIO is unreachable") from None
            _disable("MinIO is unreachable")
            return False
    return _bucket_ready


def upload_artifact(run_id: str, path: Path) -> str | None:
    """Upload a single artifact. Returns its ``s3://`` URI, or None on failure."""
    if not config.MINIO_ENABLED or _disabled_reason:
        return None
    if not ensure_bucket():
        return None
    client = get_client()
    if client is None:
        return None

    key = object_key(run_id, path.name)
    try:
        client.upload_file(
            str(path),
            config.MINIO_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": content_type_for(path)},
        )
    except Exception:
        _disable(f"artifact upload failed for {key}")
        return None
    uri = f"s3://{config.MINIO_BUCKET_NAME}/{key}"
    logger.info("Uploaded artifact %s", uri)
    return uri


def proposal_object_key(proposal_id: str, filename: str) -> str:
    return f"business-proposals/{proposal_id}/{filename}"


def _require_bucket():
    if not ensure_bucket(strict=True):
        raise ObjectStoreError("MinIO bucket is unavailable")
    client = get_client(strict=True)
    if client is None:
        raise ObjectStoreError("MinIO client is unavailable")
    return client


def upload_proposal_json(proposal_id: str, filename: str, value: dict[str, Any]) -> str:
    """Upload a required proposal JSON artifact or raise a safe storage error."""
    client = _require_bucket()
    key = proposal_object_key(proposal_id, filename)
    body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    try:
        client.put_object(
            Bucket=config.MINIO_BUCKET_NAME,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
    except Exception:
        logger.warning("Required MinIO upload failed key=%s", key)
        raise ObjectStoreError("MinIO could not store a proposal artifact") from None
    return f"s3://{config.MINIO_BUCKET_NAME}/{key}"


def download_proposal_json(proposal_id: str, filename: str) -> dict[str, Any] | None:
    """Retrieve proposal JSON from MinIO, returning None for a missing object."""
    client = _require_bucket()
    key = proposal_object_key(proposal_id, filename)
    try:
        response = client.get_object(Bucket=config.MINIO_BUCKET_NAME, Key=key)
        payload = json.loads(response["Body"].read().decode("utf-8"))
    except Exception as exc:
        from botocore.exceptions import ClientError

        if isinstance(exc, ClientError):
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"NoSuchKey", "404", "NotFound"}:
                return None
        logger.warning("Required MinIO retrieval failed key=%s", key)
        raise ObjectStoreError("MinIO could not retrieve a proposal artifact") from None
    if not isinstance(payload, dict):
        raise ObjectStoreError("Stored proposal artifact is not a JSON object")
    return payload


def health() -> dict:
    """Report object-storage reachability for the /health endpoint."""
    if not config.MINIO_ENABLED:
        return {"enabled": False, "reachable": False, "detail": "disabled via MINIO_ENABLED"}
    if _disabled_reason:
        return {
            "enabled": True,
            "reachable": False,
            "bucket": config.MINIO_BUCKET_NAME,
            "detail": _disabled_reason,
        }
    try:
        reachable = ensure_bucket(strict=True)
        detail = None
    except ObjectStoreError as exc:
        reachable = False
        detail = str(exc)
    return {
        "enabled": True,
        "reachable": reachable,
        "bucket": config.MINIO_BUCKET_NAME,
        "detail": detail or _disabled_reason,
    }


def reset_for_tests() -> None:
    """Clear cached client/bucket state. Used by the test-suite only."""
    global _client, _bucket_ready, _disabled_reason
    with _lock:
        _client = None
        _bucket_ready = False
        _disabled_reason = None
