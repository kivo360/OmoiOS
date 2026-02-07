"""Pydantic schemas for organizations."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class OrganizationBase(BaseModel):
    """Base organization schema."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$", max_length=255)
    description: Optional[str] = None
    billing_email: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    """Schema for creating organization."""

    pass


class OrganizationUpdate(BaseModel):
    """Schema for updating organization."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    billing_email: Optional[str] = None
    settings: Optional[dict] = None
    max_concurrent_agents: Optional[int] = Field(None, ge=1, le=100)
    max_agent_runtime_hours: Optional[float] = Field(None, ge=0)


class OrganizationResponse(OrganizationBase):
    """Schema for organization response."""

    id: UUID
    owner_id: UUID
    is_active: bool
    max_concurrent_agents: int
    max_agent_runtime_hours: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationSummary(BaseModel):
    """Summary schema for organization (in user lists)."""

    id: UUID
    name: str
    slug: str
    role: str  # User's role in this org

    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    """Base role schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class RoleCreate(RoleBase):
    """Schema for creating role."""

    organization_id: UUID
    inherits_from: Optional[UUID] = None


class RoleUpdate(BaseModel):
    """Schema for updating role."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    inherits_from: Optional[UUID] = None


class RoleResponse(RoleBase):
    """Schema for role response."""

    id: UUID
    organization_id: Optional[UUID]
    is_system: bool
    inherits_from: Optional[UUID]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MembershipCreate(BaseModel):
    """Schema for creating membership."""

    user_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    role_id: UUID

    @field_validator("user_id", "agent_id")
    @classmethod
    def validate_actor(cls, v, info):
        """Ensure either user_id or agent_id is provided, not both."""
        values = info.data
        user_id = values.get("user_id")
        agent_id = values.get("agent_id")

        if user_id and agent_id:
            raise ValueError("Cannot specify both user_id and agent_id")
        if not user_id and not agent_id:
            raise ValueError("Must specify either user_id or agent_id")

        return v


class MembershipUpdate(BaseModel):
    """Schema for updating membership."""

    role_id: UUID


class MembershipResponse(BaseModel):
    """Schema for membership response."""

    id: UUID
    user_id: Optional[UUID]
    agent_id: Optional[UUID]
    organization_id: UUID
    role_id: UUID
    role_name: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InviteMemberRequest(BaseModel):
    """Schema for inviting member to organization."""

    email: str
    role_id: UUID
    send_email: bool = True


class UserWithOrganizations(BaseModel):
    """User with their organizations."""

    id: UUID
    email: str
    full_name: Optional[str]
    organizations: List[OrganizationSummary]

    model_config = ConfigDict(from_attributes=True)
