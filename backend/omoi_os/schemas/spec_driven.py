"""Pydantic schemas for spec-driven settings."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class StrictnessLevel(str, Enum):
    """Strictness level for spec-driven development."""

    STRICT = "strict"
    MODERATE = "moderate"
    RELAXED = "relaxed"


class SpecDrivenOptionsSchema(BaseModel):
    """Schema for spec-driven development options.

    These settings control how strictly the system enforces spec-driven
    development practices within a project.
    """

    enabled: bool = Field(
        default=False,
        description="Whether spec-driven development is enabled for this project",
    )

    strictness: StrictnessLevel = Field(
        default=StrictnessLevel.MODERATE,
        description="How strictly to enforce spec-driven practices",
    )

    require_spec_approval: bool = Field(
        default=True,
        description="Whether specs must be approved before implementation can begin",
    )

    min_test_coverage: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Minimum test coverage percentage required (0-100)",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "enabled": True,
                "strictness": "moderate",
                "require_spec_approval": True,
                "min_test_coverage": 80.0,
            }
        },
    )

    @field_validator("min_test_coverage")
    @classmethod
    def validate_coverage(cls, v: float) -> float:
        """Validate that coverage is a valid percentage."""
        if v < 0:
            raise ValueError("min_test_coverage must be >= 0")
        if v > 100:
            raise ValueError("min_test_coverage must be <= 100")
        return v


class SpecDrivenOptionsUpdate(BaseModel):
    """Schema for partial updates to spec-driven options.

    All fields are optional to support partial updates.
    """

    enabled: Optional[bool] = None
    strictness: Optional[StrictnessLevel] = None
    require_spec_approval: Optional[bool] = None
    min_test_coverage: Optional[float] = Field(default=None, ge=0.0, le=100.0)

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("min_test_coverage")
    @classmethod
    def validate_coverage(cls, v: Optional[float]) -> Optional[float]:
        """Validate that coverage is a valid percentage if provided."""
        if v is None:
            return v
        if v < 0:
            raise ValueError("min_test_coverage must be >= 0")
        if v > 100:
            raise ValueError("min_test_coverage must be <= 100")
        return v
