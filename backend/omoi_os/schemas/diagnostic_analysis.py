"""Structured output schemas for diagnostic analysis and hypothesis generation."""

from pydantic import BaseModel, Field
from typing import List, Optional


class Hypothesis(BaseModel):
    """A hypothesis about the root cause of a workflow issue."""

    statement: str = Field(..., description="Hypothesis statement")
    likelihood: float = Field(
        ..., ge=0.0, le=1.0, description="Likelihood score (0.0-1.0)"
    )
    supporting_evidence: List[str] = Field(
        default_factory=list, description="Evidence supporting this hypothesis"
    )
    counterpoints: List[str] = Field(
        default_factory=list, description="Evidence against this hypothesis"
    )


class Recommendation(BaseModel):
    """A recommendation for resolving a workflow issue."""

    description: str = Field(..., description="Description of the recommendation")
    priority: str = Field(..., description="Priority: CRITICAL, HIGH, MEDIUM, or LOW")
    estimated_effort: str = Field(..., description="Estimated effort: S, M, or L")
    creates_followup_task: bool = Field(
        default=False, description="Whether this should create a follow-up task"
    )


class DiagnosticAnalysis(BaseModel):
    """Structured output for diagnostic analysis of stuck workflows."""

    root_cause: Optional[str] = Field(
        None, description="Identified root cause if known"
    )
    hypotheses: List[Hypothesis] = Field(
        default_factory=list, description="Ranked list of hypotheses"
    )
    recommendations: List[Recommendation] = Field(
        default_factory=list, description="Actionable recommendations"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall confidence in the analysis"
    )
