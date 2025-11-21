"""Structured output schemas for quality metrics extraction."""

from pydantic import BaseModel, Field
from typing import List, Optional


class LintError(BaseModel):
    """A lint error found in code."""

    file_path: str = Field(..., description="Path to the file with the error")
    line_number: Optional[int] = Field(None, description="Line number of the error")
    error_type: str = Field(..., description="Type of lint error")
    message: str = Field(..., description="Error message")
    severity: str = Field(..., description="Severity: error, warning, or info")


class QualityMetricsExtraction(BaseModel):
    """Structured output for quality metrics extraction from task results."""

    test_coverage: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Test coverage percentage"
    )
    lint_errors: List[LintError] = Field(
        default_factory=list, description="List of lint errors"
    )
    complexity_score: Optional[float] = Field(
        None, description="Code complexity score"
    )
    code_quality_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall code quality score (0.0-1.0)"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Quality improvement recommendations"
    )

