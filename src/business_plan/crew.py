"""CrewAI configuration and one-task-at-a-time structured execution."""
from pathlib import Path
from typing import Any

import yaml
from crewai import Agent, Crew, LLM, Process, Task
from pydantic import BaseModel

from . import config
from .models import (
    BusinessPlanReviewOutput,
    BusinessStrategyOutput,
    MarketResearchOutput,
)

_CONFIG_DIR = Path(__file__).with_name("config")
_TASK_MODELS: dict[str, type[BaseModel]] = {
    "MarketResearch": MarketResearchOutput,
    "BusinessStrategy": BusinessStrategyOutput,
    "BusinessPlanReview": BusinessPlanReviewOutput,
}
_EXPECTED_TASKS = tuple(_TASK_MODELS)


def load_crew_config() -> tuple[dict, dict]:
    with (_CONFIG_DIR / "agents.yaml").open(encoding="utf-8") as stream:
        agents = yaml.safe_load(stream)
    with (_CONFIG_DIR / "tasks.yaml").open(encoding="utf-8") as stream:
        tasks = yaml.safe_load(stream)
    if not isinstance(agents, dict) or not isinstance(tasks, dict):
        raise ValueError("CrewAI configuration files must contain YAML mappings")
    return agents, tasks


def validate_crew_configuration() -> None:
    agents, tasks = load_crew_config()
    if "BusinessPlanner" not in agents:
        raise ValueError("agents.yaml must define BusinessPlanner")
    if tuple(tasks) != _EXPECTED_TASKS:
        raise ValueError("tasks.yaml must define the three proposal tasks in order")
    for task_name, task_config in tasks.items():
        if not isinstance(task_config, dict):
            raise ValueError(f"{task_name} configuration must be a mapping")
        if task_config.get("agent") != "BusinessPlanner":
            raise ValueError(f"{task_name} must use BusinessPlanner")
        if not isinstance(task_config.get("description"), str):
            raise ValueError(f"{task_name} must define a description")
        if not isinstance(task_config.get("expected_output"), str):
            raise ValueError(f"{task_name} must define expected_output")


def _make_agent() -> Agent:
    agents, _ = load_crew_config()
    if not config.CREWAI_LLM.startswith("openai/"):
        raise RuntimeError(
            "CREWAI_LLM must use an OpenAI-compatible model identifier."
        )
    llm = LLM(
        model=config.CREWAI_LLM,
        api_key=config.require_openai_key(),
        base_url=config.OPENAI_BASE_URL or None,
    )
    return Agent(
        config=agents["BusinessPlanner"],
        llm=llm,
        max_iter=10,
        max_execution_time=300,
        max_retry_limit=1,
    )


def _result_payload(result) -> Any:
    outputs = getattr(result, "tasks_output", None)
    if outputs:
        candidate = getattr(outputs[-1], "pydantic", None)
        if candidate is None:
            candidate = getattr(outputs[-1], "raw", None)
    else:
        candidate = getattr(result, "pydantic", None)
        if candidate is None:
            candidate = getattr(result, "raw", result)
    return candidate


def run_crew_task(
    task_name: str,
    inputs: dict,
    agent: Agent | None = None,
) -> BaseModel | dict | str | None:
    """Run and validate one sequential workflow task before returning it."""
    if task_name not in _TASK_MODELS:
        raise ValueError(f"Unknown proposal task: {task_name}")
    if agent is None:
        agent = _make_agent()
    _, task_configs = load_crew_config()
    task = Task(
        config=task_configs[task_name],
        agent=agent,
        output_pydantic=_TASK_MODELS[task_name],
        guardrail_max_retries=1,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    result = crew.kickoff(inputs=inputs)
    return _result_payload(result)


def build_agent() -> Agent:
    """Create the configured planner for a single proposal run."""
    validate_crew_configuration()
    return _make_agent()
