"""Pydantic models for OmoiOS API types."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field, field_validator


class BindingKind(str, Enum):
    """Credential binding kinds."""

    BEARER_SECRET = "bearer_secret"
    USER_OAUTH = "user_oauth"
    GITHUB_APP = "github_app"


class VariableType(str, Enum):
    """Environment variable types."""

    STRING = "string"
    SECRET = "secret"
    JSON = "json"


class WebhookEvent(str, Enum):
    """Webhook event types."""

    SPEC_CREATED = "spec.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    SESSION_CREATED = "session.created"
    ARTIFACT_UPLOADED = "artifact.uploaded"


class Credential(BaseModel):
    """Credential resource."""

    id: str = Field(..., description="Unique identifier")
    workspace_id: str = Field(..., description="Workspace ID")
    kind: BindingKind = Field(..., description="Credential binding kind")
    name: str = Field(..., description="User-friendly name")
    config: Optional[Dict[str, Any]] = Field(
        None, description="Additional configuration"
    )
    version: int = Field(1, description="Credential version")
    created_at: datetime = Field(..., description="Creation timestamp")
    rotated_at: Optional[datetime] = Field(
        None, description="Last rotation timestamp"
    )


class CreateCredentialRequest(BaseModel):
    """Request to create a credential."""

    workspace_id: str = Field(..., description="Workspace ID")
    kind: BindingKind = Field(..., description="Credential binding kind")
    name: str = Field(..., description="User-friendly name")
    value: str = Field(..., description="Credential value (encrypted at rest)")
    config: Optional[Dict[str, Any]] = Field(
        None, description="Additional configuration (e.g., OAuth scopes)"
    )


class EnvironmentVariable(BaseModel):
    """Environment variable definition."""

    type: VariableType = Field(..., description="Variable type")
    value: Union[str, Dict[str, Any]] = Field(..., description="Variable value")


class Environment(BaseModel):
    """Environment resource."""

    id: str = Field(..., description="Unique identifier")
    org_id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Environment name")
    description: Optional[str] = Field(None, description="Optional description")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class EnvironmentVersion(BaseModel):
    """Environment version (immutable snapshot)."""

    id: str = Field(..., description="Unique identifier")
    environment_id: str = Field(..., description="Parent environment ID")
    version_number: int = Field(..., description="Version number (1, 2, 3...)")
    variables: Dict[str, EnvironmentVariable] = Field(
        ..., description="Environment variables"
    )
    created_at: datetime = Field(..., description="Creation timestamp")


class CreateEnvironmentRequest(BaseModel):
    """Request to create an environment."""

    name: str = Field(..., description="Environment name")
    description: Optional[str] = Field(None, description="Optional description")
    org_id: str = Field(..., description="Organization ID")


class CreateEnvironmentVersionRequest(BaseModel):
    """Request to create an environment version."""

    variables: Dict[str, EnvironmentVariable] = Field(
        ..., description="Environment variables"
    )


class Artifact(BaseModel):
    """Artifact resource."""

    id: str = Field(..., description="Unique identifier")
    workspace_id: str = Field(..., description="Workspace ID")
    name: str = Field(..., description="Artifact name")
    storage_backend: str = Field(..., description="Storage backend (local, s3)")
    storage_path: Optional[str] = Field(None, description="Storage path")
    checksum: str = Field(..., description="SHA-256 checksum")
    size_bytes: int = Field(..., description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME content type")
    artifact_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class WebhookSubscription(BaseModel):
    """Webhook subscription resource."""

    id: str = Field(..., description="Unique identifier")
    org_id: str = Field(..., description="Organization ID")
    url: str = Field(..., description="Webhook URL")
    events: list[WebhookEvent] = Field(..., description="Subscribed events")
    active: bool = Field(..., description="Whether subscription is active")
    created_at: datetime = Field(..., description="Creation timestamp")


class WebhookDelivery(BaseModel):
    """Webhook delivery record."""

    id: str = Field(..., description="Unique identifier")
    subscription_id: str = Field(..., description="Parent subscription ID")
    event: WebhookEvent = Field(..., description="Event type")
    payload: Dict[str, Any] = Field(..., description="Event payload")
    status: str = Field(..., description="Delivery status")
    attempts: int = Field(..., description="Number of delivery attempts")
    next_retry_at: Optional[datetime] = Field(
        None, description="Next retry timestamp"
    )
    created_at: datetime = Field(..., description="Creation timestamp")


class CreateWebhookRequest(BaseModel):
    """Request to create a webhook subscription."""

    url: str = Field(..., description="Webhook URL")
    events: list[WebhookEvent] = Field(..., description="Events to subscribe to")
    secret: str = Field(..., description="Secret for signature verification")


class WorkspaceSettings(BaseModel):
    """Workspace settings resource."""

    id: str = Field(..., description="Unique identifier")
    workspace_id: str = Field(..., description="Workspace ID")
    egress_allowlist: list[str] = Field(
        ..., description="Allowed egress hostnames"
    )
    max_artifact_size_mb: int = Field(
        ..., description="Maximum artifact size in MB"
    )
    allowed_binding_kinds: list[BindingKind] = Field(
        ..., description="Allowed credential binding kinds"
    )


class UpdateWorkspaceSettingsRequest(BaseModel):
    """Request to update workspace settings."""

    egress_allowlist: Optional[list[str]] = Field(
        None, description="Allowed egress hostnames"
    )
    max_artifact_size_mb: Optional[int] = Field(
        None, description="Maximum artifact size in MB"
    )
    allowed_binding_kinds: Optional[list[BindingKind]] = Field(
        None, description="Allowed credential binding kinds"
    )


# ────────────────────────────────────────────────────────────────────────────
# Spec §03 session surface
# ────────────────────────────────────────────────────────────────────────────


class Session(BaseModel):
    """A session — the unit of agent execution (spec §02).

    Backed by the `tasks` table today; the API surface is session-shaped.
    `session_token` populates only on the `create` response; it's the
    one-time sandbox bearer from `agent-platform-gaps.md` Task 5 and must
    never be logged or persisted on the client side.

    `ticket_id` is nullable since migration 071 — SDK-direct sessions have
    no ticket. Legacy ticket-driven rows created by the dashboard still
    populate it.
    """

    id: str
    session_id: Optional[str] = None  # legacy alias, still echoed by backend
    ticket_id: Optional[str] = None
    workspace_id: Optional[str] = None
    environment_id: Optional[str] = None
    environment_version: Optional[int] = None
    environment_version_id: Optional[str] = None
    github_repo: Optional[str] = None
    status: Optional[str] = None
    initial_prompt: Optional[str] = Field(None, description="Prompt used on create")
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    session_token: Optional[str] = Field(
        None,
        description=(
            "One-time sandbox bearer returned on `create`. Null on reads."
        ),
    )

    model_config = {"extra": "allow"}


class Event(BaseModel):
    """Spec §03 event envelope — every frame in the SSE stream / WS channel."""

    id: str
    seq: int
    type: str
    session_id: str
    actor: str
    timestamp: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class Grant(BaseModel):
    """One ACL grant for POST /sessions/{id}/share (spec §07)."""

    user_id: str
    role: str = Field(..., pattern="^(owner|editor|viewer)$")


class CreateSessionRequest(BaseModel):
    """Body for POST /api/v1/sessions (spec §03).

    Either `workspace_id` or `github_repo` must be supplied. `prompt` is the
    primary payload; workflow fields like `phase_id` / `priority` remain as
    optional escape hatches for callers integrating with the dashboard
    workflow engine.
    """

    model_config = {"extra": "ignore"}

    workspace_id: Optional[str] = None
    environment_id: Optional[str] = None
    prompt: str = Field(..., min_length=1)
    github_repo: Optional[str] = Field(
        default=None, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    )
    share_with: list[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class ForkRequest(BaseModel):
    """Body for POST /api/v1/sessions/{id}/fork."""

    from_seq: int = Field(..., ge=0)
    prompt: str = Field(..., min_length=1)


class ReplyRequest(BaseModel):
    """Body for POST /api/v1/sessions/{id}/messages."""

    text: str = Field(..., min_length=1)


class ShareRequest(BaseModel):
    """Body for POST /api/v1/sessions/{id}/share."""

    grants: list[Grant] = Field(default_factory=list)
