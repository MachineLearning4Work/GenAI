import pytest
from fastapi.testclient import TestClient

from business_plan import config
from business_plan.api import app


@pytest.fixture
def client():
    with TestClient(
        app,
        headers={"Authorization": "Bearer test-api-token"},
    ) as test_client:
        yield test_client


def test_health_reports_missing_key_without_leaking_it(client, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["openai"]["configured"] is False
    assert body["openai"]["key"] == "<not set>"
    assert body["object_store"]["enabled"] is False


def test_health_never_exposes_the_raw_key(client, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-do-not-leak-me-9999")
    body = client.get("/health").json()
    assert body["openai"]["configured"] is True
    assert "do-not-leak-me" not in str(body)


def test_submit_then_status_completes(client):
    run_id = client.post("/submit", json={"idea": "artisan coffee subscription"}).json()["run_id"]
    assert client.get(f"/status/{run_id}").json()["status"] == "completed"


def test_submit_returns_queued_immediately(client):
    body = client.post("/submit", json={"idea": "x"}).json()
    assert body["status"] == "queued"
    assert body["run_id"]


def test_business_proposal_requires_llm_configuration(client):
    response = client.post(
        "/business-proposals",
        json={
            "business_idea": {
                "name": "Example",
                "description": "An example business",
                "target_market": "Local customers",
            }
        },
    )
    assert response.status_code == 503
    assert "LLM configuration is missing" in response.json()["detail"]


def test_business_proposal_requires_minio_credentials(client, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "configured-for-test")
    monkeypatch.setattr(config, "MINIO_ENABLED", True)
    monkeypatch.setattr(config, "MINIO_ROOT_USER", "")
    monkeypatch.setattr(config, "MINIO_ROOT_PASSWORD", "")
    response = client.post(
        "/business-proposals",
        json={
            "business_idea": {
                "name": "Example",
                "description": "An example business",
                "target_market": "Local customers",
            }
        },
    )
    assert response.status_code == 503
    assert "MinIO credentials are missing" in response.json()["detail"]


def test_business_proposal_requires_bearer_token():
    with TestClient(app) as unauthenticated:
        response = unauthenticated.get("/business-proposals/not-a-proposal")
    assert response.status_code == 401


def test_business_proposal_retrieves_completed_artifact(client, monkeypatch):
    from business_plan import object_store, storage

    monkeypatch.setattr(
        storage,
        "read_json",
        lambda proposal_id, filename: {
            "proposal_id": proposal_id,
            "status": "completed",
        },
    )
    monkeypatch.setattr(
        object_store,
        "download_proposal_json",
        lambda proposal_id, filename: {"proposal_id": proposal_id},
    )
    response = client.get("/business-proposals/proposal-123")
    assert response.status_code == 200
    assert response.json() == {
        "proposal_id": "proposal-123",
        "status": "completed",
        "proposal": {"proposal_id": "proposal-123"},
    }


def test_business_proposal_validates_input(client, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "configured-for-test")
    response = client.post(
        "/business-proposals",
        json={"business_idea": {"name": "Incomplete"}},
    )
    assert response.status_code == 422


def test_request_validation_does_not_echo_submitted_values(client, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "configured-for-test")
    secret_like_value = "do-not-echo-this-sensitive-value"
    response = client.post(
        "/business-proposals",
        json={
            "business_idea": {
                "name": secret_like_value,
                "description": None,
                "target_market": "Local customers",
            }
        },
    )
    assert response.status_code == 422
    assert secret_like_value not in response.text


def test_end_to_end_proposal_request_and_retrieval(client, monkeypatch):
    from business_plan import object_store, workflow

    artifacts = {}
    outputs = {
        "MarketResearch": {
            "business_idea_summary": "A local bike repair service",
            "target_customers": ["Commuters"],
            "customer_problems": ["Slow repairs"],
            "market_size_assumptions": {"basis": "Needs local validation"},
            "industry_trends": ["Cycling"],
            "competitors": ["Local repair shops"],
            "competitive_advantages": ["Mobile service"],
            "market_opportunities": ["Workplace service"],
            "market_risks": ["Seasonality"],
            "research_sources": [],
        },
        "BusinessStrategy": {
            "value_proposition": "Convenient repairs",
            "target_market": {"primary": "Commuters"},
            "customer_segments": ["Urban cyclists"],
            "product_positioning": "Mobile repair service",
            "revenue_model": {"type": "service fee"},
            "pricing_strategy": {"approach": "Pilot pricing"},
            "go_to_market_strategy": {"launch": "One neighborhood"},
            "marketing_channels": ["Local partnerships"],
            "sales_strategy": {"channel": "Online"},
            "operational_requirements": ["Mechanic and van"],
            "key_performance_indicators": ["Repeat service rate"],
            "strategic_risks": ["Low utilization"],
            "risk_mitigations": ["Start with a small service area"],
        },
        "BusinessPlanReview": {
            "executive_summary": "Validate local demand first.",
            "business_strengths": ["Convenience"],
            "business_weaknesses": ["Demand is unproven"],
            "identified_gaps": ["Peak-season capacity"],
            "financial_assumptions": {"pricing": "To be tested"},
            "feasibility_assessment": {"assessment": "Pilot first"},
            "legal_risks": [],
            "operational_risks": ["Seasonality"],
            "technical_risks": [],
            "recommended_improvements": ["Test a small service area"],
            "launch_readiness_score": 50,
            "overall_recommendation": "Proceed with a limited pilot.",
            "next_steps": ["Interview commuters"],
        },
    }

    monkeypatch.setattr(config, "OPENAI_API_KEY", "configured-for-test")
    monkeypatch.setattr(config, "MINIO_ENABLED", True)
    monkeypatch.setattr(
        object_store,
        "upload_proposal_json",
        lambda proposal_id, filename, payload: artifacts.__setitem__(
            (proposal_id, filename),
            payload,
        ),
    )
    monkeypatch.setattr(
        object_store,
        "download_proposal_json",
        lambda proposal_id, filename: artifacts.get((proposal_id, filename)),
    )
    monkeypatch.setattr(workflow, "build_agent", lambda: object())
    monkeypatch.setattr(
        workflow,
        "run_crew_task",
        lambda task_name, inputs, agent: outputs[task_name],
    )

    submitted = client.post(
        "/business-proposals",
        json={
            "business_idea": {
                "name": "Mobile Bike Repair",
                "description": "A mobile service for bicycle repairs.",
                "target_market": "Urban commuters",
            }
        },
    )
    assert submitted.status_code == 202
    proposal_id = submitted.json()["proposal_id"]
    completed = client.get(f"/business-proposals/{proposal_id}")

    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == "completed"
    assert body["proposal"]["business_idea"]["name"] == "Mobile Bike Repair"
    assert body["proposal"]["market_research"]["target_customers"] == ["Commuters"]
    assert body["proposal"]["business_strategy"]["value_proposition"] == "Convenient repairs"
    assert body["proposal"]["business_plan_review"]["launch_readiness_score"] == 50
    assert (proposal_id, "final-proposal.json") in artifacts
    assert (proposal_id, "input.json") in artifacts


def test_idempotency_key_deduplicates_matching_requests(client, monkeypatch):
    from business_plan import api, object_store

    monkeypatch.setattr(config, "OPENAI_API_KEY", "configured-for-test")
    monkeypatch.setattr(config, "MINIO_ENABLED", True)
    monkeypatch.setattr(object_store, "upload_proposal_json", lambda *args: "s3://test")
    monkeypatch.setattr(api, "run_proposal_workflow", lambda *args: None)
    headers = {"Idempotency-Key": "request-123"}
    payload = {
        "business_idea": {
            "name": "Example",
            "description": "An example business",
            "target_market": "Local customers",
        }
    }

    first = client.post("/business-proposals", json=payload, headers=headers)
    duplicate = client.post("/business-proposals", json=payload, headers=headers)
    conflict = client.post(
        "/business-proposals",
        json={
            "business_idea": {
                **payload["business_idea"],
                "description": "A different business",
            }
        },
        headers=headers,
    )

    assert first.status_code == duplicate.status_code == 202
    assert first.json()["proposal_id"] == duplicate.json()["proposal_id"]
    assert conflict.status_code == 409


def test_business_proposal_is_persisted_and_queued(client, monkeypatch):
    from business_plan import object_store
    from business_plan import api

    monkeypatch.setattr(config, "OPENAI_API_KEY", "configured-for-test")
    monkeypatch.setattr(config, "MINIO_ENABLED", True)
    monkeypatch.setattr(object_store, "upload_proposal_json", lambda *args: "s3://test")
    monkeypatch.setattr(api, "run_proposal_workflow", lambda *args: None)

    response = client.post(
        "/business-proposals",
        json={
            "business_idea": {
                "name": "Example",
                "description": "An example business",
                "target_market": "Local customers",
            }
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert len(body["proposal_id"]) == 32


def test_artifacts_listed_after_run(client):
    run_id = client.post("/submit", json={"idea": "x"}).json()["run_id"]
    artifacts = client.get(f"/runs/{run_id}/artifacts").json()["artifacts"]
    assert "business_plan.md" in artifacts
    assert "status.json" in artifacts


def test_unknown_run_returns_404(client):
    assert client.get("/status/20200101T000000Z").status_code == 404
    assert client.get("/runs/20200101T000000Z/artifacts").status_code == 404


@pytest.mark.parametrize("bad", ["..", "%2e%2e", "a b"])
def test_path_traversal_rejected(client, bad):
    assert client.get(f"/status/{bad}").status_code in (400, 404)
    assert client.get(f"/runs/{bad}/artifacts").status_code in (400, 404)
