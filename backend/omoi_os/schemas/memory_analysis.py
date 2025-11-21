"""Structured output schemas for memory classification and pattern extraction."""

from pydantic import BaseModel, Field
from typing import List


class MemoryClassification(BaseModel):
    """Structured output for memory type classification."""

    memory_type: str = Field(
        ...,
        description="Memory type: error_fix, decision, learning, warning, codebase_knowledge, or discovery",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for classification"
    )
    reasoning: str = Field(..., description="Brief explanation for the classification")


class PatternExtraction(BaseModel):
    """Structured output for pattern extraction from similar tasks."""

    pattern_name: str = Field(..., description="Name of the extracted pattern")
    success_indicators: List[str] = Field(
        default_factory=list, description="List of success indicators"
    )
    failure_indicators: List[str] = Field(
        default_factory=list, description="List of failure indicators"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the pattern"
    )
    sample_count: int = Field(..., ge=1, description="Number of samples used")

