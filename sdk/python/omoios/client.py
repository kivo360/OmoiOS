"""Async HTTP client for OmoiOS API.

Provides AsyncOmoiOSClient for making async HTTP requests to the OmoiOS API,
along with the legacy OmoiOSClient abstract base class for backwards compatibility.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

import httpx

from omoios.exceptions import AuthError, NotFoundError, ServerError, ValidationError
from omoios.resources import (
    ArtifactsResource,
    CredentialsResource,
    EnvironmentsResource,
    WebhooksResource,
    WorkspacesResource,
)
from omoios.types import (
    Artifact,
    BindingKind,
    CreateCredentialRequest,
    CreateEnvironmentRequest,
    CreateEnvironmentVersionRequest,
    CreateWebhookRequest,
    Credential,
    Environment,
    EnvironmentVersion,
    WebhookDelivery,
    WebhookSubscription,
    WorkspaceSettings,
)


class OmoiOSClient(ABC):
    """Abstract base class for OmoiOS API clients.

    Implementations must provide concrete methods for all API operations.
    This base class defines the interface for both real and mock clients.
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize the client.

        Args:
            base_url: API base URL
            api_key: Optional API key for authentication
        """
        self.base_url = base_url
        self.api_key = api_key

    @abstractmethod
    def list_credentials(self, workspace_id: Optional[str] = None) -> List[Credential]:
        """List credentials."""
        pass

    @abstractmethod
    def get_credential(self, credential_id: str) -> Credential:
        """Get a credential by ID."""
        pass

    @abstractmethod
    def create_credential(self, request: CreateCredentialRequest) -> Credential:
        """Create a new credential."""
        pass

    @abstractmethod
    def delete_credential(self, credential_id: str) -> None:
        """Delete a credential."""
        pass

    @abstractmethod
    def list_environments(self) -> List[Environment]:
        """List all environments."""
        pass

    @abstractmethod
    def get_environment(
        self, environment_id: str
    ) -> Dict[str, Union[Environment, Optional[EnvironmentVersion]]]:
        """Get environment with latest version."""
        pass

    @abstractmethod
    def create_environment(self, request: CreateEnvironmentRequest) -> Environment:
        """Create a new environment."""
        pass

    @abstractmethod
    def create_environment_version(
        self, environment_id: str, request: CreateEnvironmentVersionRequest
    ) -> EnvironmentVersion:
        """Create a new environment version."""
        pass

    @abstractmethod
    def upload_artifact(
        self, file_content: bytes, workspace_id: Optional[str] = None
    ) -> Artifact:
        """Upload an artifact."""
        pass

    @abstractmethod
    def list_artifacts(self, workspace_id: Optional[str] = None) -> List[Artifact]:
        """List artifacts."""
        pass

    @abstractmethod
    def get_artifact(self, artifact_id: str) -> Artifact:
        """Get an artifact by ID."""
        pass

    @abstractmethod
    def download_artifact(self, artifact_id: str) -> bytes:
        """Download artifact content."""
        pass

    @abstractmethod
    def delete_artifact(self, artifact_id: str) -> None:
        """Delete an artifact."""
        pass

    @abstractmethod
    def list_webhooks(self) -> List[WebhookSubscription]:
        """List webhook subscriptions."""
        pass

    @abstractmethod
    def create_webhook(self, request: CreateWebhookRequest) -> WebhookSubscription:
        """Create a webhook subscription."""
        pass

    @abstractmethod
    def delete_webhook(self, webhook_id: str) -> None:
        """Delete a webhook subscription."""
        pass

    @abstractmethod
    def list_webhook_deliveries(self, subscription_id: str) -> List[WebhookDelivery]:
        """List webhook deliveries for a subscription."""
        pass

    @abstractmethod
    def get_workspace_settings(self, workspace_id: str) -> WorkspaceSettings:
        """Get workspace settings."""
        pass


class AsyncOmoiOSClient:
    """Async HTTP client for the OmoiOS Agent Workspace Platform.

    Uses httpx.AsyncClient for async HTTP requests. Supports both API key
    and JWT token authentication.

    Example:
        >>> async with AsyncOmoiOSClient("https://api.omoios.dev", api_key="key") as client:
        ...     creds = await client.credentials.list(workspace_id="ws-1")
        ...     print(creds[0].name)
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        jwt_token: Optional[str] = None,
        session_token: Optional[str] = None,
        timeout: float = 30.0,
        telemetry: Optional["Callable[[dict[str, Any]], None]"] = None,
    ):
        """Initialize the async client.

        Args:
            base_url: API base URL (e.g., "https://api.omoios.dev").
            api_key: Platform API key (`rpk_live_…`). Sent as
                ``Authorization: Bearer <key>`` to match spec §01. The legacy
                ``X-API-Key`` header is still sent in parallel so older
                backends keep working during the transition.
            jwt_token: User JWT (`eyJ…`). Sent as ``Authorization: Bearer``.
            session_token: Sandbox session bearer (`sess_tok_…`) for
                credential-broker calls from inside a sandbox. Sent as
                ``Authorization: Bearer``.
            timeout: HTTP request timeout in seconds (default: 30.0).
            telemetry: Optional callback invoked with a dict describing each
                HTTP lifecycle event — `{kind, method, path, status?,
                duration_ms?, error?}` where `kind` is one of
                `request | response | stream_open | stream_close | error`.
                Matches spec §18 §2's constructor option. Auth headers are
                NEVER included. Fire-and-forget; exceptions are swallowed.

        Raises:
            ValueError: If no credential is provided, or if more than one
                credential kind is set (they're mutually exclusive).
        """
        provided = [
            p for p in (api_key, jwt_token, session_token) if p
        ]
        if not provided:
            raise ValueError(
                "One of api_key, jwt_token, or session_token must be provided"
            )
        if len(provided) > 1:
            raise ValueError(
                "api_key, jwt_token, and session_token are mutually exclusive"
            )

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.jwt_token = jwt_token
        self.session_token = session_token
        self._http = httpx.AsyncClient(timeout=timeout)
        self._telemetry = telemetry

        self.credentials = CredentialsResource(self)
        self.environments = EnvironmentsResource(self)
        self.artifacts = ArtifactsResource(self)
        self.webhooks = WebhooksResource(self)
        self.workspaces = WorkspacesResource(self)

        # Spec §03 primary surface — sessions + events + multiplayer.
        from omoios.resources.sessions import SessionsResource

        self.sessions = SessionsResource(self)

        # Spec §18 §2 canonical resources — connections + usage.
        from omoios.resources.connections import ConnectionsResource
        from omoios.resources.usage import UsageResource

        self.connections = ConnectionsResource(self)
        self.usage = UsageResource(self)

    def _auth_token(self) -> Optional[str]:
        """Return the single active bearer token (whichever kind was set)."""
        return self.api_key or self.jwt_token or self.session_token

    def _headers(self) -> Dict[str, str]:
        """Build request headers with authentication.

        Spec §01 wants ``Authorization: Bearer <token>`` for all three token
        kinds. We also duplicate platform keys into ``X-API-Key`` so backends
        that haven't been migrated yet still recognize the caller.
        """
        headers: Dict[str, str] = {}
        token = self._auth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _handle_errors(self, response: httpx.Response) -> None:
        """Map HTTP error status codes to SDK exceptions.

        Args:
            response: httpx Response object

        Raises:
            AuthError: For 401 responses
            NotFoundError: For 404 responses
            ValidationError: For 400/422 responses
            ServerError: For 5xx responses
        """
        if response.status_code == 401:
            raise AuthError("Authentication failed")
        elif response.status_code == 404:
            detail = "Resource not found"
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise NotFoundError(detail)
        elif response.status_code in (400, 422):
            detail = "Validation failed"
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise ValidationError(detail)
        elif response.status_code >= 500:
            detail = "Server error"
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise ServerError(detail)

    def _emit_telemetry(self, event: Dict[str, Any]) -> None:
        """Deliver a telemetry event to the caller callback.

        Silently swallows exceptions — telemetry is observability plumbing,
        not a code path that should be able to break requests. Runs
        synchronously; the caller can offload to a queue if async delivery
        matters to them.
        """
        cb = self._telemetry
        if cb is None:
            return
        try:
            cb(event)
        except Exception:  # noqa: BLE001
            pass

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Make an authenticated HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., "/api/v1/credentials")
            **kwargs: Additional arguments passed to httpx, plus optional
                ``cancel_scope: anyio.CancelScope`` which wraps the request
                — canceling the scope cancels the in-flight HTTP call at
                the next await point. Matches spec §18 §1 principle 5
                ("cancellation via CancelScope in Python"). httpx already
                cooperates with asyncio task cancellation, so callers who
                prefer ``asyncio.wait_for`` don't need this kwarg — but
                having it means the cancellation surface is explicit in
                the SDK signature rather than implicit in the runtime.

        Returns:
            httpx Response object

        Raises:
            AuthError, NotFoundError, ValidationError, ServerError
        """
        import time

        cancel_scope = kwargs.pop("cancel_scope", None)

        url = f"{self.base_url}{path}"
        headers = {**self._headers(), **kwargs.pop("headers", {})}
        self._emit_telemetry({"kind": "request", "method": method, "path": path})
        started = time.perf_counter()

        async def _do_request() -> httpx.Response:
            return await self._http.request(method, url, headers=headers, **kwargs)

        try:
            if cancel_scope is None:
                response = await _do_request()
            else:
                # Run inside the caller's cancel scope so abort() halts the
                # httpx call at the next checkpoint.
                import anyio

                with cancel_scope:
                    response = await _do_request()
        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.perf_counter() - started) * 1000
            self._emit_telemetry(
                {
                    "kind": "error",
                    "method": method,
                    "path": path,
                    "duration_ms": duration_ms,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            raise
        duration_ms = (time.perf_counter() - started) * 1000
        self._emit_telemetry(
            {
                "kind": "response",
                "method": method,
                "path": path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            }
        )
        self._handle_errors(response)
        return response

    async def close(self) -> None:
        """Close the HTTP client and release connections."""
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncOmoiOSClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context manager, closing the client."""
        await self.close()
