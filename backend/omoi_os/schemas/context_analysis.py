"""Structured output schemas for context summarization."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class Decision(BaseModel):
    """A decision made during workflow execution."""

    decision: str = Field(..., description="Decision description")
    phase_id: Optional[str] = Field(None, description="Phase where decision was made")
    rationale: Optional[str] = Field(None, description="Rationale for the decision")


class Risk(BaseModel):
    """A risk identified during workflow execution."""

    risk: str = Field(..., description="Risk description")
    severity: str = Field(..., description="Severity: high, medium, or low")
    phase_id: Optional[str] = Field(None, description="Phase where risk was identified")
    mitigation: Optional[str] = Field(None, description="Mitigation strategy")


class ContextSummary(BaseModel):
    """Structured output for context summarization."""

    key_decisions: List[Decision] = Field(
        default_factory=list, description="Key decisions made"
    )
    risks: List[Risk] = Field(default_factory=list, description="Identified risks")
    highlights: List[str] = Field(
        default_factory=list, description="Key highlights or insights"
    )
    phase_summaries: Dict[str, str] = Field(
        default_factory=dict, description="Summary for each phase"
    )
