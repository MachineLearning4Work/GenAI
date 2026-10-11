from business_plan.models import MarketResearch, BusinessStrategy, BusinessPlanReview, TargetSegment


def test_market_research_model():
    mr = MarketResearch(
        idea_summary="idea",
        target_segments=[TargetSegment(name='A')],
        customer_pain_points=['p'],
        market_assumptions=['a'],
        alternatives_and_competitors=['x'],
        validation_questions=['q'],
        recommended_research_actions=['r'],
    )
    assert mr.idea_summary == 'idea'


def test_business_strategy_model():
    bs = BusinessStrategy(
        positioning_statement='p',
        value_proposition='v',
        course_offer={"format":"online"},
        pricing_hypotheses=['p'] ,
        go_to_market_plan=['g']
    )
    assert bs.positioning_statement == 'p'


def test_business_plan_review_model():
    br = BusinessPlanReview(
        overall_assessment='ok',
        strengths=['s'],
        critical_risks=[{"severity":"low","explanation":"e"}],
        unsupported_or_missing_evidence=['u'],
        decision='proceed'
    )
    assert br.decision == 'proceed'
