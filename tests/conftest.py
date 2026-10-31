import pytest

from business_plan import config, object_store


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Point every test at a throwaway runs dir with object storage disabled."""
    monkeypatch.setattr(config, "RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr(config, "MINIO_ENABLED", False)
    monkeypatch.setattr(config, "MINIO_ROOT_USER", "test-minio-user")
    monkeypatch.setattr(config, "MINIO_ROOT_PASSWORD", "test-minio-password")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    monkeypatch.setattr(config, "API_ACCESS_TOKEN", "test-api-token")
    object_store.reset_for_tests()
    yield
    object_store.reset_for_tests()
