"""Structured output schemas for validation analysis."""

from pydantic import BaseModel, Field
from typing import List, Optional


class BlockingIssue(BaseModel):
    """A blocking issue found during validation."""

    issue: str = Field(..., description="Description of the blocking issue")
    severity: str = Field(
        ..., description="Severity: critical, high, medium, or low"
    )
    artifact_path: Optional[str] = Field(
        None, description="Path to the artifact with the issue"
    )


class ValidationResult(BaseModel):
    """Structured output for phase completion validation."""

    passed: bool = Field(..., description="Whether validation passed")
    feedback: str = Field(..., description="Validation feedback text")
    blocking_reasons: List[BlockingIssue] = Field(
        default_factory=list, description="List of blocking issues"
    )
    completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Artifact completeness score (0.0-1.0)"
    )
    missing_artifacts: List[str] = Field(
        default_factory=list, description="List of missing required artifacts"
    )

