"""Structured output schemas for quality prediction and recommendations."""

from pydantic import BaseModel, Field
from typing import List


class QualityRecommendation(BaseModel):
    """A quality improvement recommendation."""

    recommendation: str = Field(..., description="Recommendation text")
    priority: str = Field(..., description="Priority: high, medium, or low")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the recommendation"
    )


class QualityPrediction(BaseModel):
    """Structured output for quality prediction."""

    predicted_quality_score: float = Field(
        ..., ge=0.0, le=1.0, description="Predicted quality score (0.0-1.0)"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the prediction"
    )
    risk_level: str = Field(..., description="Risk level: low, medium, or high")
    recommendations: List[QualityRecommendation] = Field(
        default_factory=list, description="Quality improvement recommendations"
    )
    similar_task_count: int = Field(
        ..., ge=0, description="Number of similar tasks found"
    )
    pattern_count: int = Field(..., ge=0, description="Number of patterns matched")

