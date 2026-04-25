"""OmoiOS SDK - Python client for the OmoiOS Agent Workspace Platform."""

from omoios.types import (
    BindingKind,
    Credential,
    CreateCredentialRequest,
    VariableType,
    EnvironmentVariable,
    Environment,
    EnvironmentVersion,
    CreateEnvironmentRequest,
    CreateEnvironmentVersionRequest,
    Artifact,
    WebhookEvent,
    WebhookSubscription,
    WebhookDelivery,
    CreateWebhookRequest,
    WorkspaceSettings,
    UpdateWorkspaceSettingsRequest,
    # Spec §03 session surface
    Session,
    Event,
    Grant,
    CreateSessionRequest,
    ForkRequest,
    ReplyRequest,
    ShareRequest,
)
from omoios.client import OmoiOSClient, AsyncOmoiOSClient
from omoios.mock_client import MockOmoiOSClient
from omoios.exceptions import OmoiOSError, AuthError, NotFoundError, ValidationError, ServerError

__version__ = "0.2.0"
__all__ = [
    # Types
    "BindingKind",
    "Credential",
    "CreateCredentialRequest",
    "VariableType",
    "EnvironmentVariable",
    "Environment",
    "EnvironmentVersion",
    "CreateEnvironmentRequest",
    "CreateEnvironmentVersionRequest",
    "Artifact",
    "WebhookEvent",
    "WebhookSubscription",
    "WebhookDelivery",
    "CreateWebhookRequest",
    "WorkspaceSettings",
    "UpdateWorkspaceSettingsRequest",
    # Spec §03
    "Session",
    "Event",
    "Grant",
    "CreateSessionRequest",
    "ForkRequest",
    "ReplyRequest",
    "ShareRequest",
    # Clients
    "OmoiOSClient",
    "AsyncOmoiOSClient",
    "MockOmoiOSClient",
    # Exceptions
    "OmoiOSError",
    "AuthError",
    "NotFoundError",
    "ValidationError",
    "ServerError",
]
