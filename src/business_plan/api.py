from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from . import storage
from .main import run as pipeline_run
import os
import json


class Idea(BaseModel):
    idea: str


app = FastAPI(title="CrewAI Business Plan API")


def _set_status(run_id: str, status: str, details: dict | None = None):
    payload = {"status": status}
    if details:
        payload.update(details)
    storage.write_json(run_id, 'status.json', payload)


def _background_run(idea_text: str, run_id: str):
    try:
        _set_status(run_id, 'running')
        pipeline_run(idea_text, run_id=run_id)
        _set_status(run_id, 'completed')
    except Exception as exc:
        _set_status(run_id, 'failed', {"error": str(exc)})


@app.post("/submit")
def submit(idea: Idea, background_tasks: BackgroundTasks):
    """Enqueue a pipeline run and return the run id immediately."""
    run_id = storage.make_run_id()
    # record queued status
    _set_status(run_id, 'queued')
    background_tasks.add_task(_background_run, idea.idea, run_id)
    return {"run_id": run_id, "status": "queued"}


@app.get('/status/{run_id}')
def status(run_id: str):
    path = os.path.join(os.getenv('RUNS_DIR', '/app/runs').lstrip('/'), run_id, 'status.json')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='run not found')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
