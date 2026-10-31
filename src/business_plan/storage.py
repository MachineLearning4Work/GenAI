"""Local filesystem persistence for run artifacts, mirrored to MinIO.

Artifacts are always written to disk under ``config.RUNS_DIR``; the MinIO
upload is best-effort and never fails a run.
"""
import json
import hashlib
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from . import config, object_store

# Run ids come from URL path parameters, so restrict them to a safe charset to
# prevent directory traversal such as ../../etc.
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_IDEMPOTENCY_LOCK = threading.Lock()


class IdempotencyConflict(ValueError):
    """Raised when a client reuses an idempotency key for different input."""


def validate_run_id(run_id: str) -> str:
    if not _RUN_ID_RE.match(run_id or "") or ".." in run_id:
        raise ValueError(f"invalid run id: {run_id!r}")
    return run_id


def make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def runs_root() -> Path:
    return Path(config.RUNS_DIR)


def run_dir(run_id: str, create: bool = False) -> Path:
    """Return the directory holding a run's artifacts."""
    path = runs_root() / validate_run_id(run_id)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def artifact_path(run_id: str, filename: str) -> Path:
    return run_dir(run_id) / filename


def write_text(run_id: str, filename: str, text: str) -> str:
    path = run_dir(run_id, create=True) / filename
    path.write_text(text, encoding="utf-8")
    object_store.upload_artifact(run_id, path)
    return str(path)


def write_json(run_id: str, filename: str, obj: dict) -> str:
    return write_text(run_id, filename, json.dumps(obj, indent=2))


def write_proposal_json(proposal_id: str, filename: str, obj: dict) -> str:
    """Persist a proposal artifact locally and require its MinIO upload."""
    path = run_dir(proposal_id, create=True) / filename
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    object_store.upload_proposal_json(proposal_id, filename, obj)
    return str(path)


def read_json(run_id: str, filename: str) -> dict | None:
    """Return parsed JSON for an artifact, or None when it does not exist."""
    path = artifact_path(run_id, filename)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_idempotent_proposal(
    key: str,
    request_hash: str,
) -> str | None:
    """Return the proposal mapped to a key, rejecting a different request body."""
    root = runs_root()
    index_path = root / ".proposal-idempotency.json"
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    with _IDEMPOTENCY_LOCK:
        if not index_path.exists():
            return None
        with index_path.open("r", encoding="utf-8") as handle:
            entries = json.load(handle)
        if not isinstance(entries, dict):
            raise OSError("Proposal idempotency registry is invalid")
        entry = entries.get(key_hash)
        if entry is None:
            return None
        if not isinstance(entry, dict) or "request_hash" not in entry or "proposal_id" not in entry:
            raise OSError("Proposal idempotency registry is invalid")
        if entry["request_hash"] != request_hash:
            raise IdempotencyConflict(
                "Idempotency-Key was already used with different input."
            )
        return entry["proposal_id"]


def save_idempotency_key(key: str, request_hash: str, proposal_id: str) -> None:
    """Persist a completed proposal submission's idempotency mapping."""
    root = runs_root()
    root.mkdir(parents=True, exist_ok=True)
    index_path = root / ".proposal-idempotency.json"
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    with _IDEMPOTENCY_LOCK:
        if index_path.exists():
            with index_path.open("r", encoding="utf-8") as handle:
                entries = json.load(handle)
        else:
            entries = {}
        if not isinstance(entries, dict):
            raise OSError("Proposal idempotency registry is invalid")
        entry = entries.get(key_hash)
        if entry is not None:
            if not isinstance(entry, dict) or "request_hash" not in entry:
                raise OSError("Proposal idempotency registry is invalid")
            if entry["request_hash"] != request_hash:
                raise IdempotencyConflict(
                    "Idempotency-Key was already used with different input."
                )
            return
        entries[key_hash] = {"request_hash": request_hash, "proposal_id": proposal_id}
        temp_path = root / f".proposal-idempotency-{proposal_id}.tmp"
        try:
            temp_path.write_text(
                json.dumps(entries, separators=(",", ":")),
                encoding="utf-8",
            )
            temp_path.replace(index_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
