from datetime import datetime
from typing import Literal, List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    # populate_by_name lets callers pass `day_30_action_plan=...` while the
    # serialized artifact keeps the published `30_day_action_plan` name.
    model_config = ConfigDict(populate_by_name=True)

    overall_assessment: str
    strengths: List[str]
    critical_risks: List[dict]
    unsupported_or_missing_evidence: List[str]
    consistency_checks: Optional[List[str]] = None
    recommended_experiments: Optional[List[str]] = None
    day_30_action_plan: Optional[List[str]] = Field(None, alias="30_day_action_plan")
    decision: str


class BusinessIdea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    target_market: str = Field(min_length=1, max_length=1000)
    location: Optional[str] = Field(default=None, max_length=500)
    budget: Optional[str] = Field(default=None, max_length=500)
    additional_context: Optional[str] = Field(default=None, max_length=5000)


class BusinessProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_idea: BusinessIdea


class ProposalTaskOutput(BaseModel):
    model_config = ConfigDict(extra="allow")


class MarketResearchOutput(ProposalTaskOutput):
    business_idea_summary: str
    target_customers: List[str]
    customer_problems: List[str]
    market_size_assumptions: dict[str, object]
    industry_trends: List[str]
    competitors: List[str]
    competitive_advantages: List[str]
    market_opportunities: List[str]
    market_risks: List[str]
    research_sources: List[str]


class BusinessStrategyOutput(ProposalTaskOutput):
    value_proposition: str
    target_market: dict[str, object]
    customer_segments: List[str]
    product_positioning: str
    revenue_model: dict[str, object]
    pricing_strategy: dict[str, object]
    go_to_market_strategy: dict[str, object]
    marketing_channels: List[str]
    sales_strategy: dict[str, object]
    operational_requirements: List[str]
    key_performance_indicators: List[str]
    strategic_risks: List[str]
    risk_mitigations: List[str]


class BusinessPlanReviewOutput(ProposalTaskOutput):
    executive_summary: str
    business_strengths: List[str]
    business_weaknesses: List[str]
    identified_gaps: List[str]
    financial_assumptions: dict[str, object]
    feasibility_assessment: dict[str, object]
    legal_risks: List[str]
    operational_risks: List[str]
    technical_risks: List[str]
    recommended_improvements: List[str]
    launch_readiness_score: int = Field(ge=0, le=100)
    overall_recommendation: str
    next_steps: List[str]


class ProposalError(BaseModel):
    code: Literal["TASK_FAILED", "STORAGE_FAILED", "CONFIGURATION_ERROR"]
    task: Optional[str] = None
    message: str


class ProposalStatus(BaseModel):
    proposal_id: str
    status: Literal["pending", "running", "completed", "failed"]
    task: Optional[str] = None
    error: Optional[ProposalError] = None


class FinalBusinessProposal(BaseModel):
    proposal_id: str
    business_idea: BusinessIdea
    market_research: MarketResearchOutput
    business_strategy: BusinessStrategyOutput
    business_plan_review: BusinessPlanReviewOutput
    executive_summary: str
    final_recommendation: str
    created_at: datetime
    workflow_status: Literal["completed"]
