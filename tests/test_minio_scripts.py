import runpy
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "script_name",
    ["create_minio_bucket.py", "list_minio_buckets.py"],
)
def test_minio_scripts_require_credentials(script_name, monkeypatch):
    monkeypatch.delenv("MINIO_ROOT_USER", raising=False)
    monkeypatch.delenv("MINIO_ROOT_PASSWORD", raising=False)
    script_path = (
        Path(__file__).parents[1] / "src" / "scripts" / script_name
    )
    main = runpy.run_path(str(script_path))["main"]

    with pytest.raises(
        SystemExit,
        match="MINIO_ROOT_USER and MINIO_ROOT_PASSWORD must be set",
    ):
        main()
