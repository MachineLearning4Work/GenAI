import json

from business_plan import storage
from business_plan.main import run


def test_run_writes_all_artifacts():
    run_id = run("a cooperative bakery in Montreal")
    produced = sorted(p.name for p in storage.run_dir(run_id).iterdir())
    assert produced == [
        "01_market_research.json",
        "02_business_strategy.json",
        "03_business_plan_review.json",
        "business_plan.md",
    ]


def test_run_honours_supplied_run_id():
    assert run("idea", run_id="custom-run") == "custom-run"
    assert storage.artifact_path("custom-run", "business_plan.md").is_file()


def test_idea_text_reaches_the_report():
    run_id = run("solar powered kayak rentals")
    plan = storage.artifact_path(run_id, "business_plan.md").read_text(encoding="utf-8")
    assert "solar powered kayak rentals" in plan


def test_markdown_artifact_is_markdown_not_json():
    """Regression: business_plan.md was previously wrapped in a JSON envelope."""
    run_id = run("idea")
    text = storage.artifact_path(run_id, "business_plan.md").read_text(encoding="utf-8")
    assert text.lstrip().startswith("# Business Plan")


def test_action_plan_is_persisted_under_its_alias():
    """Regression: the field alias silently dropped day_30_action_plan."""
    run_id = run("idea")
    review = storage.read_json(run_id, "03_business_plan_review.json")
    assert review["30_day_action_plan"] == ["Design survey, recruit 10 pilot learners"]
    assert "day_30_action_plan" not in review
