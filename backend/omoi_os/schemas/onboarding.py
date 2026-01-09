"""Pydantic schemas for onboarding."""

from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OnboardingStatusResponse(BaseModel):
    """Response schema for onboarding status."""

    is_completed: bool
    current_step: str
    completed_steps: list[str]
    completed_checklist_items: list[str]
    completed_at: Optional[datetime] = None
    data: dict = Field(default_factory=dict)
    sync_version: int

    model_config = ConfigDict(from_attributes=True)


class OnboardingStepUpdate(BaseModel):
    """Request schema for updating onboarding step."""

    step: str = Field(..., min_length=1, max_length=50)
    data: dict = Field(default_factory=dict)


class OnboardingCompleteRequest(BaseModel):
    """Request schema for completing onboarding."""

    data: dict = Field(default_factory=dict)


class OnboardingResetRequest(BaseModel):
    """Request schema for resetting onboarding."""

    admin_override: bool = False


class DetectedStepState(BaseModel):
    """State of an auto-detected onboarding step."""

    completed: bool
    current: Optional[dict] = None
    can_change: bool = True


class OnboardingDetectResponse(BaseModel):
    """Response schema for auto-detected onboarding state."""

    github: DetectedStepState
    organization: DetectedStepState
    repo: DetectedStepState
    plan: DetectedStepState
    suggested_step: str


class OnboardingSyncRequest(BaseModel):
    """Request schema for syncing onboarding state from client."""

    current_step: str
    completed_steps: list[str]
    completed_checklist_items: list[str]
    data: dict = Field(default_factory=dict)
    local_sync_version: int
