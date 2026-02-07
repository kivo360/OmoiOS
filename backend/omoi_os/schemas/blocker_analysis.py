"""Structured output schemas for blocker analysis."""

from pydantic import BaseModel, Field
from typing import List


class UnblockingStep(BaseModel):
    """A step to unblock a ticket."""

    step: str = Field(..., description="Description of the unblocking step")
    priority: str = Field(..., description="Priority: CRITICAL, HIGH, MEDIUM, or LOW")
    estimated_effort: str = Field(..., description="Estimated effort: S, M, or L")


class BlockerAnalysis(BaseModel):
    """Structured output for blocker classification and analysis."""

    blocker_type: str = Field(
        ...,
        description="Blocker type: dependency, resource, validation, approval, etc.",
    )
    blocker_reason: str = Field(..., description="Reason for the blocker")
    unblocking_steps: List[UnblockingStep] = Field(
        default_factory=list, description="Steps to unblock the ticket"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the analysis"
    )
