"""Tests for the best-effort MinIO upload layer, using a stub S3 client."""
import io
import json

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from business_plan import config, object_store, storage


class FakeS3:
    def __init__(
        self,
        missing_bucket=False,
        fail_upload=False,
        unreachable=False,
        fail_put=False,
    ):
        self.missing_bucket = missing_bucket
        self.fail_upload = fail_upload
        self.unreachable = unreachable
        self.fail_put = fail_put
        self.created = []
        self.uploads = []
        self.objects = {}

    def head_bucket(self, Bucket):
        if self.unreachable:
            raise EndpointConnectionError(endpoint_url="http://minio:9000")
        if self.missing_bucket:
            raise ClientError({"ResponseMetadata": {"HTTPStatusCode": 404}}, "HeadBucket")

    def create_bucket(self, Bucket):
        self.created.append(Bucket)
        self.missing_bucket = False

    def upload_file(self, filename, bucket, key, ExtraArgs=None):
        if self.fail_upload:
            raise OSError("disk on fire")
        self.uploads.append((filename, bucket, key, ExtraArgs))

    def put_object(self, Bucket, Key, Body, ContentType):
        if self.fail_put:
            raise OSError("safe test failure")
        self.objects[Key] = (Body, ContentType)

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey"}},
                "GetObject",
            )
        body, _ = self.objects[Key]
        return {"Body": io.BytesIO(body)}


@pytest.fixture
def enable_minio(monkeypatch):
    """Enable uploads and swap in a fake S3 client."""

    def _install(fake):
        monkeypatch.setattr(config, "MINIO_ENABLED", True)
        monkeypatch.setattr(object_store, "_build_client", lambda: fake)
        object_store.reset_for_tests()
        return fake

    return _install


def test_upload_returns_s3_uri_and_sends_content_type(enable_minio):
    fake = enable_minio(FakeS3())
    storage.write_json("run-9", "01_market_research.json", {"a": 1})

    assert len(fake.uploads) == 1
    _, bucket, key, extra = fake.uploads[0]
    assert bucket == config.MINIO_BUCKET_NAME
    assert key == "runs/run-9/01_market_research.json"
    assert extra == {"ContentType": "application/json"}


def test_markdown_gets_markdown_content_type(enable_minio):
    fake = enable_minio(FakeS3())
    storage.write_text("run-9", "business_plan.md", "# hi")
    assert fake.uploads[0][3] == {"ContentType": "text/markdown"}


def test_missing_bucket_is_created_once(enable_minio):
    fake = enable_minio(FakeS3(missing_bucket=True))
    storage.write_text("run-9", "a.md", "x")
    storage.write_text("run-9", "b.md", "y")
    assert fake.created == [config.MINIO_BUCKET_NAME]
    assert len(fake.uploads) == 2


def test_unreachable_minio_does_not_fail_the_run(enable_minio, tmp_path):
    enable_minio(FakeS3(unreachable=True))
    path = storage.write_text("run-9", "a.md", "still written")
    assert object_store.upload_artifact("run-9", storage.artifact_path("run-9", "a.md")) is None
    # The local artifact is the source of truth and must survive.
    assert storage.artifact_path("run-9", "a.md").read_text(encoding="utf-8") == "still written"


def test_upload_failure_disables_further_attempts(enable_minio):
    fake = enable_minio(FakeS3(fail_upload=True))
    storage.write_text("run-9", "a.md", "x")
    storage.write_text("run-9", "b.md", "y")
    assert fake.uploads == []
    assert object_store.health()["reachable"] is False


def test_uploads_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(config, "MINIO_ENABLED", False)

    def explode():
        raise AssertionError("client must not be built when MinIO is disabled")

    monkeypatch.setattr(object_store, "_build_client", explode)
    object_store.reset_for_tests()
    storage.write_text("run-9", "a.md", "x")
    assert object_store.health() == {
        "enabled": False,
        "reachable": False,
        "detail": "disabled via MINIO_ENABLED",
    }


def test_health_reports_reachable_store(enable_minio):
    enable_minio(FakeS3())
    assert object_store.health()["reachable"] is True


def test_proposal_json_upload_and_retrieval_are_strict(enable_minio):
    fake = enable_minio(FakeS3())
    uri = object_store.upload_proposal_json(
        "proposal-1",
        "input.json",
        {"name": "Example"},
    )

    assert uri == "s3://business-plan-bucket/business-proposals/proposal-1/input.json"
    key = "business-proposals/proposal-1/input.json"
    body, content_type = fake.objects[key]
    assert json.loads(body) == {"name": "Example"}
    assert content_type == "application/json"
    assert object_store.download_proposal_json("proposal-1", "input.json") == {
        "name": "Example"
    }


def test_missing_proposal_artifact_returns_none(enable_minio):
    enable_minio(FakeS3())
    assert object_store.download_proposal_json("proposal-1", "missing.json") is None


def test_required_proposal_upload_fails_when_minio_is_disabled(monkeypatch):
    monkeypatch.setattr(config, "MINIO_ENABLED", False)
    with pytest.raises(object_store.ObjectStoreError):
        object_store.upload_proposal_json("proposal-1", "input.json", {})


def test_required_storage_failure_is_reported_without_latching_client(enable_minio):
    enable_minio(FakeS3(fail_put=True))
    with pytest.raises(object_store.ObjectStoreError, match="could not store"):
        object_store.upload_proposal_json("proposal-1", "input.json", {})
    assert object_store._disabled_reason is None


def test_health_check_does_not_permanently_disable_recovery(enable_minio):
    enable_minio(FakeS3(unreachable=True))
    assert object_store.health()["reachable"] is False
    assert object_store._disabled_reason is None
