import json
import inspect

from crewai import Task
from business_plan import config, object_store, storage
from business_plan.crew import build_agent, validate_crew_configuration
from business_plan.models import BusinessIdea
from business_plan.workflow import _validate_output, run_proposal_workflow


def _research():
    return {
        "business_idea_summary": "A neighborhood coffee subscription",
        "target_customers": ["Local coffee drinkers"],
        "customer_problems": ["Finding convenient quality coffee"],
        "market_size_assumptions": {"basis": "Local survey required"},
        "industry_trends": ["Subscription purchasing"],
        "competitors": ["Independent cafes"],
        "competitive_advantages": ["Home delivery"],
        "market_opportunities": ["Underserved neighborhoods"],
        "market_risks": ["Established competitors"],
        "research_sources": [],
        "additional_notes": ["Field interview required"],
    }


def _strategy():
    return {
        "value_proposition": "Convenient local coffee",
        "target_market": {"primary": "Local coffee drinkers"},
        "customer_segments": ["Busy professionals"],
        "product_positioning": "A convenient neighborhood service",
        "revenue_model": {"type": "subscription"},
        "pricing_strategy": {"approach": "Test with pilot customers"},
        "go_to_market_strategy": {"launch": "Start in one neighborhood"},
        "marketing_channels": ["Local partnerships"],
        "sales_strategy": {"channel": "Online"},
        "operational_requirements": ["Delivery operations"],
        "key_performance_indicators": ["Retention"],
        "strategic_risks": ["Low retention"],
        "risk_mitigations": ["Pilot and measure repeat orders"],
    }


def _review():
    return {
        "executive_summary": "Pilot the subscription before scaling.",
        "business_strengths": ["Clear customer benefit"],
        "business_weaknesses": ["Demand is unproven"],
        "identified_gaps": ["Willingness to pay"],
        "financial_assumptions": {"pricing": "To be tested"},
        "feasibility_assessment": {"assessment": "Pilot first"},
        "legal_risks": [],
        "operational_risks": ["Delivery costs"],
        "technical_risks": [],
        "recommended_improvements": ["Test two price points"],
        "launch_readiness_score": 45,
        "overall_recommendation": "Proceed with a limited validation pilot.",
        "next_steps": ["Interview customers", "Run a small pilot"],
    }


def _idea():
    return BusinessIdea(
        name="Neighborhood Coffee",
        description="A local coffee subscription service.",
        target_market="Coffee drinkers in Montreal",
        location="Montreal",
    )


def test_crew_yaml_configuration_is_valid():
    validate_crew_configuration()
    assert "output_pydantic" in inspect.signature(Task).parameters


def test_business_planner_agent_uses_yaml_configuration(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-only-key")
    agent = build_agent()
    assert agent.role == "Business Planning Specialist"
    assert agent.max_retry_limit == 1


def test_structured_output_parser_accepts_json_fences():
    from business_plan.models import MarketResearchOutput

    parsed = _validate_output(
        MarketResearchOutput,
        f"```json\n{json.dumps(_research())}\n```",
    )
    assert parsed.business_idea_summary == _research()["business_idea_summary"]


def test_workflow_validates_passes_and_persists_outputs(monkeypatch):
    monkeypatch.setattr(object_store, "upload_proposal_json", lambda *args: "s3://test")
    calls = []

    def task_runner(task_name, inputs, agent):
        calls.append((task_name, inputs))
        if task_name == "MarketResearch":
            assert "market_research_json" not in inputs
            return _research()
        if task_name == "BusinessStrategy":
            assert "market_research_json" in inputs
            return _strategy()
        assert "market_research_json" in inputs
        assert "business_strategy_json" in inputs
        return _review()

    run_proposal_workflow("proposal-test-1", _idea(), task_runner=task_runner)

    assert [name for name, _ in calls] == [
        "MarketResearch",
        "BusinessStrategy",
        "BusinessPlanReview",
    ]
    assert storage.read_json("proposal-test-1", "metadata.json") == {
        "proposal_id": "proposal-test-1",
        "status": "completed",
    }
    proposal = storage.read_json("proposal-test-1", "final-proposal.json")
    assert proposal["market_research"]["competitors"] == ["Independent cafes"]
    assert proposal["market_research"]["additional_notes"] == ["Field interview required"]
    assert proposal["business_strategy"]["value_proposition"] == "Convenient local coffee"
    assert proposal["business_plan_review"]["launch_readiness_score"] == 45
    assert proposal["executive_summary"] == _review()["executive_summary"]
    assert proposal["workflow_status"] == "completed"


def test_invalid_task_output_stops_pipeline_and_persists_safe_failure(monkeypatch):
    monkeypatch.setattr(object_store, "upload_proposal_json", lambda *args: "s3://test")
    calls = []

    def task_runner(task_name, inputs, agent):
        calls.append(task_name)
        return "{}"

    run_proposal_workflow("proposal-test-2", _idea(), task_runner=task_runner)

    status = storage.read_json("proposal-test-2", "metadata.json")
    assert calls == ["MarketResearch"]
    assert status["status"] == "failed"
    assert status["error"]["task"] == "MarketResearch"
    assert "schema" in status["error"]["message"]
    assert not storage.artifact_path("proposal-test-2", "final-proposal.json").exists()
