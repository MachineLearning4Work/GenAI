import os
import json
from datetime import datetime
from . import config


def make_run_id():
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def write_json(run_id: str, filename: str, obj: dict):
    run_dir = os.path.join(config.RUNS_DIR.lstrip('/'), run_id)
    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2)
    return path


def write_text(run_id: str, filename: str, text: str):
    run_dir = os.path.join(config.RUNS_DIR.lstrip('/'), run_id)
    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return path
