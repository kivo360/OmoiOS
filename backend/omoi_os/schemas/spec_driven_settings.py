"""Pydantic schemas for spec-driven settings API endpoints.

This module provides request/response schemas for the spec-driven settings
API endpoints. The main settings schema (SpecDrivenOptionsSchema) is defined
in omoi_os/services/spec_driven_settings.py for historical reasons.
"""

from typing import Optional

from pydantic import BaseModel, Field


class SpecDrivenSettingsUpdateSchema(BaseModel):
    """Schema for partial updates to spec-driven settings.

    All fields are optional to support PATCH semantics.
    Only provided fields will be updated.
    """

    spec_driven_mode_enabled: Optional[bool] = Field(
        default=None,
        description="Enable spec-driven workflow mode for this project.",
    )
    auto_advance_phases: Optional[bool] = Field(
        default=None,
        description="Automatically advance through spec phases.",
    )
    require_approval_gates: Optional[bool] = Field(
        default=None,
        description="Require manual approval at phase gates.",
    )
    auto_spawn_tasks: Optional[bool] = Field(
        default=None,
        description="Automatically spawn implementation tasks after SYNC phase.",
    )
