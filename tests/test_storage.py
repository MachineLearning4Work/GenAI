import json
from pathlib import Path

import pytest

from business_plan import config, storage


def test_write_json_lands_under_configured_runs_dir():
    path = Path(storage.write_json("run-1", "a.json", {"k": "v"}))
    assert path.parent.parent == Path(config.RUNS_DIR)
    assert json.loads(path.read_text(encoding="utf-8")) == {"k": "v"}


def test_write_text_roundtrip():
    storage.write_text("run-1", "notes.md", "# hello")
    assert storage.artifact_path("run-1", "notes.md").read_text(encoding="utf-8") == "# hello"


def test_absolute_runs_dir_is_not_mangled(tmp_path, monkeypatch):
    """Regression: the old code stripped the leading separator from RUNS_DIR."""
    target = tmp_path / "abs-runs"
    monkeypatch.setattr(config, "RUNS_DIR", str(target))
    path = Path(storage.write_json("run-2", "a.json", {}))
    assert path == target / "run-2" / "a.json"
    assert path.is_file()


def test_read_json_returns_none_for_missing_run():
    assert storage.read_json("no-such-run", "status.json") is None


def test_make_run_id_format():
    run_id = storage.make_run_id()
    assert len(run_id) == 16 and run_id.endswith("Z")
    assert storage.validate_run_id(run_id) == run_id


@pytest.mark.parametrize("bad", ["../escape", "a/b", "..", "", "with space", "x" * 100])
def test_invalid_run_ids_rejected(bad):
    with pytest.raises(ValueError):
        storage.run_dir(bad)


def test_run_dir_not_created_unless_requested():
    assert not storage.run_dir("lazy").exists()
    assert storage.run_dir("lazy", create=True).is_dir()
