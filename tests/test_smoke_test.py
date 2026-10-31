import importlib.util
import io
from pathlib import Path
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError


@pytest.fixture
def smoke(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts" / "smoke_test.py"
    spec = importlib.util.spec_from_file_location("smoke_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_ROOT_USER", "test-user")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "test-password")
    monkeypatch.setenv("API_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("MINIO_REGION", "us-east-1")
    monkeypatch.setenv("MINIO_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(module, "wait_for_health", Mock())
    monkeypatch.setattr(module, "http_status", Mock(side_effect=[401, 404]))
    return module


def test_smoke_creates_bucket_and_cleans_up_object(smoke, monkeypatch):
    client = Mock()
    client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404"}}, "HeadBucket"
    )
    body = io.BytesIO(b"business-plan storage smoke test")
    client.get_object.return_value = {"Body": body}
    monkeypatch.setattr(smoke.boto3, "client", Mock(return_value=client))

    smoke.main()

    client.create_bucket.assert_called_once_with(Bucket="test-bucket")
    key = client.put_object.call_args.kwargs["Key"]
    client.delete_object.assert_called_once_with(Bucket="test-bucket", Key=key)
    assert body.closed


def test_smoke_cleans_up_after_corrupt_read(smoke, monkeypatch):
    client = Mock()
    body = io.BytesIO(b"wrong contents")
    client.get_object.return_value = {"Body": body}
    monkeypatch.setattr(smoke.boto3, "client", Mock(return_value=client))

    with pytest.raises(RuntimeError, match="contents differ"):
        smoke.main()

    client.delete_object.assert_called_once()
    assert body.closed


def test_smoke_does_not_hide_storage_permission_failure(smoke, monkeypatch):
    client = Mock()
    client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "403"}}, "HeadBucket"
    )
    monkeypatch.setattr(smoke.boto3, "client", Mock(return_value=client))

    with pytest.raises(ClientError):
        smoke.main()

    client.create_bucket.assert_not_called()


def test_smoke_rejects_missing_api_authentication(smoke, monkeypatch):
    monkeypatch.setattr(smoke, "http_status", Mock(return_value=200))
    with pytest.raises(RuntimeError, match="unauthenticated"):
        smoke.main()
