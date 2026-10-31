"""Runtime configuration, sourced exclusively from environment variables.

Secrets such as ``OPENAI_API_KEY`` are **never** hardcoded in this file and
must never be committed. Supply them through one of:

* a local ``.env`` file (git-ignored, see ``.env.example``)
* Docker Compose ``environment:`` / ``env_file:`` entries
* Jenkins credentials bound to environment variables

Only :func:`masked_openai_key` should ever be logged or returned by an API.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# config.py lives at <root>/src/business_plan/config.py, so parents[2] is the
# project root locally and /app inside the container. This keeps the default
# runs directory valid on both Windows and Linux without path surgery.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

_TRUTHY = {"1", "true", "yes", "on"}


def _env(name: str, default: str = "") -> str:
    """Read an environment variable, treating whitespace-only values as unset."""
    return (os.getenv(name) or "").strip() or default


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name)
    return raw.lower() in _TRUTHY if raw else default


MINIO_ENDPOINT = _env("MINIO_ENDPOINT", "minio:9000")
MINIO_ROOT_USER = _env("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = _env("MINIO_ROOT_PASSWORD")
MINIO_BUCKET_NAME = _env("MINIO_BUCKET_NAME", "business-plan-bucket")
MINIO_REGION = _env("MINIO_REGION", "us-east-1")
MINIO_SECURE = _env_bool("MINIO_SECURE", False)

# Set MINIO_ENABLED=false to skip object-storage uploads entirely, which is
# useful for offline local runs and for unit tests.
MINIO_ENABLED = _env_bool("MINIO_ENABLED", True)
MINIO_CONNECT_TIMEOUT = float(_env("MINIO_CONNECT_TIMEOUT", "3"))
MINIO_READ_TIMEOUT = float(_env("MINIO_READ_TIMEOUT", "10"))

# Secret: provided via environment only. An empty value means "not configured",
# which keeps the pipeline running against its offline stub tasks.
OPENAI_API_KEY = _env("OPENAI_API_KEY")
OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = _env("OPENAI_BASE_URL")
CREWAI_LLM = _env("CREWAI_LLM", f"openai/{OPENAI_MODEL}")
API_ACCESS_TOKEN = _env("API_ACCESS_TOKEN")

RUNS_DIR = _env("RUNS_DIR") or str(_PROJECT_ROOT / "runs")


def has_openai_key() -> bool:
    """Return True when an OpenAI API key is configured."""
    return bool(OPENAI_API_KEY)


def require_openai_key() -> str:
    """Return the OpenAI API key, or raise a helpful error when it is missing."""
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your local .env file (see "
            ".env.example) or export it in the environment. Never commit the key."
        )
    return OPENAI_API_KEY


def masked_openai_key() -> str:
    """Return a redacted form of the key that is safe to log or expose."""
    if not OPENAI_API_KEY:
        return "<not set>"
    if len(OPENAI_API_KEY) <= 8:
        return "*" * len(OPENAI_API_KEY)
    return f"{OPENAI_API_KEY[:3]}...{OPENAI_API_KEY[-4:]}"


def minio_endpoint_url() -> str:
    """Return the MinIO endpoint as a full URL including a scheme."""
    if MINIO_ENDPOINT.startswith(("http://", "https://")):
        return MINIO_ENDPOINT
    return f"{'https' if MINIO_SECURE else 'http'}://{MINIO_ENDPOINT}"
