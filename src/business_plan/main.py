"""Legacy deterministic CLI demonstration.

The authenticated FastAPI proposal endpoints use the real CrewAI workflow in
:mod:`business_plan.workflow`. This CLI is retained for the original
offline-friendly teaching example and does not call an LLM.
"""
import argparse
import logging

from . import config
from .models import MarketResearch, BusinessStrategy, BusinessPlanReview, TargetSegment
from .storage import make_run_id, write_json, write_text
from .report import render_markdown

logger = logging.getLogger(__name__)


def task1(idea: str) -> MarketResearch:
    mr = MarketResearch(
        idea_summary=idea,
        target_segments=[TargetSegment(name="Professionals", characteristics="working professionals", needs="practical skills", barriers="time/cost")],
        customer_pain_points=["Need practical ML for work"],
        market_assumptions=["Professionals prefer evening/weekend courses"],
        alternatives_and_competitors=["Local universities, online courses"],
        validation_questions=["Would you pay for a 10-week evening course?"],
        recommended_research_actions=["Survey 100 local professionals"],
        confidence_notes="Low — hypothesis"
    )
    return mr


def task2(mr: MarketResearch) -> BusinessStrategy:
    bs = BusinessStrategy(
        positioning_statement="Affordable practical ML course for working professionals",
        value_proposition="Hands-on, relevant projects that apply at work",
        course_offer={"format":"hybrid","duration":"10 weeks"},
        pricing_hypotheses=["$499 per learner"],
        go_to_market_plan=["Local meetup partnerships"],
        revenue_model="Course fees",
        key_resources_and_cost_categories=["Instructor, venue, materials"],
        success_metrics=["% of learners using skills at work"],
        dependencies_and_assumptions=["Instructor availability"]
    )
    return bs


def task3(mr: MarketResearch, bs: BusinessStrategy) -> BusinessPlanReview:
    br = BusinessPlanReview(
        overall_assessment="Plausible but needs validation",
        strengths=["Clear audience and deliverables"],
        critical_risks=[{"severity":"medium","explanation":"Pricing may be too high"}],
        unsupported_or_missing_evidence=["Actual willingness to pay"],
        consistency_checks=["Assumptions align with offer"],
        recommended_experiments=["Pilot cohort"],
        day_30_action_plan=["Design survey, recruit 10 pilot learners"],
        decision="proceed_to_validation"
    )
    return br


def run(idea: str, run_id: str | None = None):
    """Execute the three-task pipeline for the supplied idea.

    If `run_id` is provided the run will use it; otherwise a new id is generated.
    Returns the `run_id` used.
    """
    if run_id is None:
        run_id = make_run_id()

    logger.info(
        "Starting run %s (openai_key=%s, model=%s)",
        run_id,
        config.masked_openai_key(),
        config.OPENAI_MODEL,
    )

    mr = task1(idea)
    bs = task2(mr)
    br = task3(mr, bs)

    path1 = write_json(run_id, '01_market_research.json', mr.model_dump(by_alias=True))
    path2 = write_json(run_id, '02_business_strategy.json', bs.model_dump(by_alias=True))
    path3 = write_json(run_id, '03_business_plan_review.json', br.model_dump(by_alias=True))

    md = render_markdown(mr, bs, br)
    md_path = write_text(run_id, 'business_plan.md', md)

    logger.info("Run completed: %s", run_id)
    print(f"Run completed: {run_id}")
    print(path1, path2, path3, md_path)
    return run_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--idea', '-i', default='An affordable practical ML course in Montreal')
    parser.add_argument('--run-id', default=None, help='Reuse an existing run id')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
    run(args.idea, run_id=args.run_id)


if __name__ == '__main__':
    main()
