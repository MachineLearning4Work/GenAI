from typing import Any
from .models import MarketResearch, BusinessStrategy, BusinessPlanReview


def render_markdown(mr: MarketResearch, bs: BusinessStrategy, br: BusinessPlanReview) -> str:
    lines = []
    lines.append(f"# Business Plan\n\n")
    lines.append("## Idea Summary\n")
    lines.append(mr.idea_summary + "\n")
    lines.append("## Market Research\n")
    for seg in mr.target_segments:
        lines.append(f"- Segment: {seg.name} — {seg.characteristics or ''}")
    lines.append("\n## Business Strategy\n")
    lines.append(bs.positioning_statement + "\n")
    lines.append("\n## Review\n")
    lines.append(br.overall_assessment + "\n")
    return "\n".join(lines)
