import logging
import hashlib
import json
import secrets
import threading
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import config, object_store, storage
from .main import run as pipeline_run
from .models import BusinessProposalRequest, ProposalStatus
from .workflow import new_proposal_id, run_proposal_workflow

logger = logging.getLogger(__name__)

STATUS_FILE = 'status.json'
_PROPOSAL_CREATE_LOCK = threading.Lock()


class Idea(BaseModel):
    idea: str = Field(min_length=1, max_length=10_000)


app = FastAPI(title="CrewAI Business Plan API")


@app.exception_handler(RequestValidationError)
async def validation_error_response(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return validation locations without echoing submitted values."""
    errors = [
        {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


def _set_status(run_id: str, status: str, details: dict | None = None):
    payload = {"status": status}
    if details:
        payload.update(details)
    storage.write_json(run_id, STATUS_FILE, payload)


def _background_run(idea_text: str, run_id: str):
    try:
        _set_status(run_id, 'running')
        pipeline_run(idea_text, run_id=run_id)
        _set_status(run_id, 'completed')
    except Exception:
        logger.error("Legacy demo run failed run_id=%s", run_id)
        _set_status(run_id, 'failed', {"error": "The demo run could not be completed."})


def require_api_access(authorization: str | None = Header(default=None)) -> None:
    """Require a configured bearer token before exposing proposal data."""
    expected = config.API_ACCESS_TOKEN
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="API access is not configured.",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="A bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    supplied = authorization.removeprefix("Bearer ")
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get('/health')
def health():
    """Liveness/readiness probe that never exposes the raw API key."""
    return {
        "status": "ok",
        "runs_dir": config.RUNS_DIR,
        "openai": {
            "configured": config.has_openai_key(),
            "key": config.masked_openai_key(),
            "model": config.OPENAI_MODEL,
        },
        "object_store": object_store.health(),
    }


@app.post("/submit", dependencies=[Depends(require_api_access)])
def submit(idea: Idea, background_tasks: BackgroundTasks):
    """Enqueue a pipeline run and return the run id immediately."""
    run_id = storage.make_run_id()
    # record queued status
    _set_status(run_id, 'queued')
    background_tasks.add_task(_background_run, idea.idea, run_id)
    return {"run_id": run_id, "status": "queued"}


@app.get('/status/{run_id}', dependencies=[Depends(require_api_access)])
def status(run_id: str):
    try:
        payload = storage.read_json(run_id, STATUS_FILE)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if payload is None:
        raise HTTPException(status_code=404, detail='run not found')
    return payload


@app.get('/runs/{run_id}/artifacts', dependencies=[Depends(require_api_access)])
def artifacts(run_id: str):
    """List the artifact filenames produced by a run."""
    try:
        run_dir = storage.run_dir(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail='run not found')
    return {
        "run_id": run_id,
        "artifacts": sorted(p.name for p in run_dir.iterdir() if p.is_file()),
    }


@app.post(
    "/business-proposals",
    status_code=202,
    response_model=ProposalStatus,
    dependencies=[Depends(require_api_access)],
)
def create_business_proposal(
    request: BusinessProposalRequest,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ProposalStatus:
    """Queue proposal generation after validating required runtime configuration."""
    if not config.has_openai_key():
        raise HTTPException(
            status_code=503,
            detail="Proposal generation is unavailable: LLM configuration is missing.",
        )
    if not config.CREWAI_LLM.startswith("openai/"):
        raise HTTPException(
            status_code=503,
            detail="Proposal generation is unavailable: the configured LLM provider is unsupported.",
        )
    if not config.MINIO_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Proposal generation is unavailable: MinIO storage is disabled.",
        )
    if not config.MINIO_ROOT_USER or not config.MINIO_ROOT_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="Proposal generation is unavailable: MinIO credentials are missing.",
        )

    if idempotency_key is not None and (
        not idempotency_key
        or len(idempotency_key) > 200
        or idempotency_key.strip() != idempotency_key
    ):
        raise HTTPException(status_code=400, detail="Invalid Idempotency-Key.")

    idea_payload = request.business_idea.model_dump(mode="json", exclude_none=True)
    request_hash = hashlib.sha256(
        json.dumps(idea_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    with _PROPOSAL_CREATE_LOCK:
        if idempotency_key is None:
            proposal_id = new_proposal_id()
            exists = False
        else:
            try:
                proposal_id = storage.find_idempotent_proposal(
                    idempotency_key,
                    request_hash,
                )
                exists = proposal_id is not None
            except storage.IdempotencyConflict:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency-Key was already used with different input.",
                ) from None
            except (OSError, ValueError):
                raise HTTPException(
                    status_code=503,
                    detail="Proposal request state is temporarily unavailable.",
                ) from None

        if exists:
            assert proposal_id is not None
            try:
                status_payload = storage.read_json(proposal_id, "metadata.json")
                if status_payload is None:
                    status_payload = object_store.download_proposal_json(
                        proposal_id,
                        "metadata.json",
                    )
                if status_payload is None:
                    raise HTTPException(
                        status_code=503,
                        detail="The previous proposal request is temporarily unavailable.",
                    )
                return ProposalStatus.model_validate(status_payload)
            except object_store.ObjectStoreError:
                raise HTTPException(
                    status_code=503,
                    detail="Proposal status is temporarily unavailable.",
                ) from None
            except ValueError:
                raise HTTPException(
                    status_code=500,
                    detail="Stored proposal status is invalid.",
                ) from None

        if proposal_id is None:
            proposal_id = new_proposal_id()
        pending = ProposalStatus(proposal_id=proposal_id, status="pending")
        try:
            storage.write_proposal_json(
                proposal_id,
                "input.json",
                idea_payload,
            )
            storage.write_proposal_json(
                proposal_id,
                "metadata.json",
                pending.model_dump(mode="json", exclude_none=True),
            )
            if idempotency_key is not None:
                storage.save_idempotency_key(
                    idempotency_key,
                    request_hash,
                    proposal_id,
                )
        except storage.IdempotencyConflict:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key was already used with different input.",
            ) from None
        except (object_store.ObjectStoreError, OSError, ValueError):
            raise HTTPException(
                status_code=503,
                detail="Proposal storage is unavailable. Please retry later.",
            ) from None
        background_tasks.add_task(
            run_proposal_workflow,
            proposal_id,
            request.business_idea,
        )
        return pending


@app.get(
    "/business-proposals/{proposal_id}",
    dependencies=[Depends(require_api_access)],
)
def get_business_proposal(proposal_id: str) -> dict[str, Any]:
    try:
        storage.validate_run_id(proposal_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid proposal ID.") from None

    status_payload = storage.read_json(proposal_id, "metadata.json")
    if status_payload is None:
        try:
            status_payload = object_store.download_proposal_json(
                proposal_id,
                "metadata.json",
            )
        except object_store.ObjectStoreError:
            raise HTTPException(
                status_code=503,
                detail="Proposal status is temporarily unavailable.",
            ) from None
    if status_payload is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")

    try:
        status = ProposalStatus.model_validate(status_payload)
    except ValueError:
        raise HTTPException(
            status_code=500,
            detail="Stored proposal status is invalid.",
        ) from None
    response = status.model_dump(mode="json", exclude_none=True)
    if status.status == "completed":
        try:
            proposal = object_store.download_proposal_json(
                proposal_id,
                "final-proposal.json",
            )
        except object_store.ObjectStoreError:
            raise HTTPException(
                status_code=503,
                detail="Completed proposal is temporarily unavailable.",
            ) from None
        if proposal is None:
            raise HTTPException(
                status_code=503,
                detail="Completed proposal artifact is missing.",
            )
        response["proposal"] = proposal
    return response
