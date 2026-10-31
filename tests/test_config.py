import pytest

from business_plan import config


def test_env_treats_blank_as_unset(monkeypatch):
    monkeypatch.setenv("BP_TEST_VALUE", "   ")
    assert config._env("BP_TEST_VALUE", "fallback") == "fallback"


def test_env_strips_whitespace(monkeypatch):
    monkeypatch.setenv("BP_TEST_VALUE", "  hello  ")
    assert config._env("BP_TEST_VALUE") == "hello"


@pytest.mark.parametrize("raw,expected", [("1", True), ("TRUE", True), ("on", True), ("0", False), ("no", False)])
def test_env_bool_parsing(monkeypatch, raw, expected):
    monkeypatch.setenv("BP_TEST_FLAG", raw)
    assert config._env_bool("BP_TEST_FLAG", not expected) is expected


def test_env_bool_falls_back_when_unset(monkeypatch):
    monkeypatch.delenv("BP_TEST_FLAG", raising=False)
    assert config._env_bool("BP_TEST_FLAG", True) is True


def test_runs_dir_default_is_absolute():
    """Regression: RUNS_DIR used to be mangled into a relative path."""
    import os

    assert os.path.isabs(config.RUNS_DIR)


def test_missing_openai_key_is_reported(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    assert config.has_openai_key() is False
    assert config.masked_openai_key() == "<not set>"
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        config.require_openai_key()


def test_present_openai_key_is_masked(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-super-secret-value-1234")
    assert config.has_openai_key() is True
    assert config.require_openai_key() == "sk-super-secret-value-1234"
    masked = config.masked_openai_key()
    assert masked == "sk-...1234"
    assert "super-secret" not in masked


def test_short_openai_key_fully_masked(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "abc123")
    assert config.masked_openai_key() == "******"


def test_api_access_token_is_environment_configured():
    assert isinstance(config.API_ACCESS_TOKEN, str)


@pytest.mark.parametrize(
    "endpoint,secure,expected",
    [
        ("minio:9000", False, "http://minio:9000"),
        ("minio:9000", True, "https://minio:9000"),
        ("https://example.com", False, "https://example.com"),
    ],
)
def test_minio_endpoint_url(monkeypatch, endpoint, secure, expected):
    monkeypatch.setattr(config, "MINIO_ENDPOINT", endpoint)
    monkeypatch.setattr(config, "MINIO_SECURE", secure)
    assert config.minio_endpoint_url() == expected
