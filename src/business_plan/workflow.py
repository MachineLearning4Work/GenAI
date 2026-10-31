"""Business-proposal orchestration and persistent workflow status."""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Callable, Literal

from pydantic import BaseModel, ValidationError

from . import object_store, storage
from .crew import build_agent, run_crew_task
from .models import (
    BusinessIdea,
    BusinessPlanReviewOutput,
    BusinessStrategyOutput,
    FinalBusinessProposal,
    MarketResearchOutput,
    ProposalError,
    ProposalStatus,
)

logger = logging.getLogger(__name__)
_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.IGNORECASE | re.DOTALL)
_TASKS = (
    ("MarketResearch", MarketResearchOutput),
    ("BusinessStrategy", BusinessStrategyOutput),
    ("BusinessPlanReview", BusinessPlanReviewOutput),
)
TaskRunner = Callable[[str, dict, object | None], BaseModel | dict | str]


class TaskOutputError(ValueError):
    """Raised when a CrewAI task does not satisfy its Pydantic output contract."""


def new_proposal_id() -> str:
    from uuid import uuid4

    return uuid4().hex


def _validate_output(model: type[BaseModel], output) -> BaseModel:
    if isinstance(output, model):
        return output
    if isinstance(output, BaseModel):
        output = output.model_dump()
    if not isinstance(output, (dict, str)):
        raise TaskOutputError("Task returned an unsupported output type")
    if isinstance(output, str):
        fenced = _JSON_FENCE_RE.fullmatch(output)
        if fenced:
            output = fenced.group(1)
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            raise TaskOutputError("Task output was not valid JSON") from None
    try:
        return model.model_validate(output)
    except ValidationError:
        raise TaskOutputError("Task output did not match its required schema") from None


def _persist_status(proposal_id: str, status: ProposalStatus) -> None:
    payload = status.model_dump(mode="json", exclude_none=True)
    storage.write_proposal_json(proposal_id, "metadata.json", payload)


def run_proposal_workflow(
    proposal_id: str,
    idea: BusinessIdea,
    task_runner: TaskRunner | None = None,
) -> None:
    """Generate, validate, and persist all proposal outputs in dependency order."""
    current_task: str | None = None
    current_status = ProposalStatus(proposal_id=proposal_id, status="running")
    try:
        _persist_status(proposal_id, current_status)
        agent = build_agent() if task_runner is None else None
        idea_payload = idea.model_dump(mode="json", exclude_none=True)
        outputs: dict[str, BaseModel] = {}
        for task_name, output_model in _TASKS:
            current_task = task_name
            current_status = ProposalStatus(
                proposal_id=proposal_id,
                status="running",
                task=task_name,
            )
            _persist_status(proposal_id, current_status)
            inputs = {
                "business_idea_json": json.dumps(idea_payload, ensure_ascii=False),
            }
            if "MarketResearch" in outputs:
                inputs["market_research_json"] = outputs["MarketResearch"].model_dump_json()
            if "BusinessStrategy" in outputs:
                inputs["business_strategy_json"] = outputs["BusinessStrategy"].model_dump_json()
            if task_runner is None:
                output = run_crew_task(task_name, inputs, agent)
            else:
                output = task_runner(task_name, inputs, None)
            validated = _validate_output(output_model, output)
            outputs[task_name] = validated
            filename = {
                "MarketResearch": "market-research.json",
                "BusinessStrategy": "business-strategy.json",
                "BusinessPlanReview": "business-plan-review.json",
            }[task_name]
            storage.write_proposal_json(
                proposal_id,
                filename,
                validated.model_dump(mode="json"),
            )

        research = MarketResearchOutput.model_validate(outputs["MarketResearch"])
        strategy = BusinessStrategyOutput.model_validate(outputs["BusinessStrategy"])
        review = BusinessPlanReviewOutput.model_validate(outputs["BusinessPlanReview"])
        proposal = FinalBusinessProposal(
            proposal_id=proposal_id,
            business_idea=idea,
            market_research=research,
            business_strategy=strategy,
            business_plan_review=review,
            executive_summary=review.executive_summary,
            final_recommendation=review.overall_recommendation,
            created_at=datetime.now(timezone.utc),
            workflow_status="completed",
        )
        storage.write_proposal_json(
            proposal_id,
            "final-proposal.json",
            proposal.model_dump(mode="json"),
        )
        _persist_status(
            proposal_id,
            ProposalStatus(proposal_id=proposal_id, status="completed"),
        )
        logger.info("Proposal workflow completed proposal_id=%s", proposal_id)
    except object_store.ObjectStoreError:
        _fail(
            proposal_id,
            current_task,
            "STORAGE_FAILED",
            "Proposal artifacts could not be stored.",
        )
    except OSError:
        logger.error(
            "Proposal local storage failed proposal_id=%s task=%s",
            proposal_id,
            current_task or "unknown",
        )
        _fail(
            proposal_id,
            current_task,
            "STORAGE_FAILED",
            "Proposal artifacts could not be stored.",
        )
    except TaskOutputError as exc:
        logger.error(
            "Proposal output invalid proposal_id=%s task=%s",
            proposal_id,
            current_task or "unknown",
        )
        _fail(proposal_id, current_task, "TASK_FAILED", str(exc))
    except Exception:
        logger.error(
            "Proposal workflow failed proposal_id=%s task=%s category=task_failure",
            proposal_id,
            current_task or "configuration",
        )
        _fail(
            proposal_id,
            current_task,
            "TASK_FAILED",
            "The proposal workflow could not complete this task.",
        )


def _fail(
    proposal_id: str,
    task: str | None,
    code: Literal["TASK_FAILED", "STORAGE_FAILED", "CONFIGURATION_ERROR"],
    message: str,
) -> None:
    failure_status = ProposalStatus(
        proposal_id=proposal_id,
        status="failed",
        error=ProposalError(code=code, task=task, message=message),
    )
    try:
        _persist_status(proposal_id, failure_status)
    except (object_store.ObjectStoreError, OSError):
        logger.error("Proposal failure status could not be persisted proposal_id=%s", proposal_id)
