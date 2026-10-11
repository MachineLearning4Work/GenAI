from pydantic import BaseModel, Field
from typing import List, Optional


class TargetSegment(BaseModel):
    name: str
    characteristics: Optional[str] = None
    needs: Optional[str] = None
    barriers: Optional[str] = None


class MarketResearch(BaseModel):
    idea_summary: str
    target_segments: List[TargetSegment]
    customer_pain_points: List[str]
    market_assumptions: List[str]
    alternatives_and_competitors: List[str]
    validation_questions: List[str]
    recommended_research_actions: List[str]
    confidence_notes: Optional[str] = None


class BusinessStrategy(BaseModel):
    positioning_statement: str
    value_proposition: str
    course_offer: dict
    pricing_hypotheses: List[str]
    go_to_market_plan: List[str]
    revenue_model: Optional[str] = None
    key_resources_and_cost_categories: Optional[List[str]] = None
    success_metrics: Optional[List[str]] = None
    dependencies_and_assumptions: Optional[List[str]] = None


class BusinessPlanReview(BaseModel):
    overall_assessment: str
    strengths: List[str]
    critical_risks: List[dict]
    unsupported_or_missing_evidence: List[str]
    consistency_checks: Optional[List[str]] = None
    recommended_experiments: Optional[List[str]] = None
    day_30_action_plan: Optional[List[str]] = Field(None, alias="30_day_action_plan")
    decision: str
