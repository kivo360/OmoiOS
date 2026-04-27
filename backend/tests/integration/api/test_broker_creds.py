"""Integration tests for broker credential dispatch endpoint.

Tests Requirements:
- REQ-BROKER-001: Resolve bearer_secret alias via HTTP
- REQ-BROKER-002: Resolve user_oauth alias via HTTP
- REQ-BROKER-003: Resolve github_app alias via HTTP
- REQ-BROKER-004: Unknown alias returns 404
- REQ-BROKER-005: Revoked session returns 401
- REQ-BROKER-006: Cross-workspace access denied
- REQ-BROKER-007: Audit log written on every success
"""

from __future__ import annotations

import os
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure encryption key is set before any omoi_os module that reads it at import time
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "a" * 64)

from omoi_os.api.dependencies import get_db_session as deps_get_db_session
from omoi_os.api.routes import broker_runtime
from omoi_os.models.credential_access_log import CredentialAccessLog
from omoi_os.models.credential_binding import CredentialBinding
from omoi_os.models.environment import Environment, EnvironmentVersion
from omoi_os.models.organization import Organization
from omoi_os.models.user import User
from omoi_os.models.user_credentials import UserCredential
from omoi_os.models.workspace import Workspace
from omoi_os.services.credential_broker import CredentialBrokerService
from omoi_os.services.credential_encryption import (
    CredentialEncryptionService,
    reset_credential_encryption_service,
)
from omoi_os.services.database import DatabaseService
from omoi_os.services.sandbox_session_service import SandboxSessionService
from omoi_os.utils.datetime import utc_now


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def encryption_key() -> str:
    """Return a valid 64-hex-char test encryption key."""
    return "a" * 64


@pytest.fixture
def encryption_service(encryption_key: str) -> CredentialEncryptionService:
    """Create an encryption service with the test key."""
    reset_credential_encryption_service()
    return CredentialEncryptionService(encryption_key=encryption_key)


@pytest.fixture
def credential_broker_service(
    db_service: DatabaseService,
    encryption_service: CredentialEncryptionService,
) -> CredentialBrokerService:
    """Create a credential broker service wired to the test database."""
    from omoi_os.services.credential_broker import reset_credential_broker_service

    reset_credential_broker_service()
    return CredentialBrokerService(db=db_service, encryption=encryption_service)


@pytest.fixture
def broker_app(
    db_service: DatabaseService,
    credential_broker_service: CredentialBrokerService,
) -> FastAPI:
    """Build a minimal FastAPI app with broker routes and test dependencies."""
    app = FastAPI()
    app.include_router(broker_runtime.router, prefix="/broker")

    # 1. Override the feature-flag gate so routes are reachable in tests
    app.dependency_overrides[broker_runtime.require_broker_enabled] = lambda: None

    # 2. Override the credential broker dependency
    app.dependency_overrides[broker_runtime.get_runtime_credential_broker] = lambda: (
        credential_broker_service
    )

    # 3. Override the async DB session dependency used by get_session_service
    async def override_get_db_session():
        async with db_service.get_async_session() as session:
            yield session

    app.dependency_overrides[deps_get_db_session] = override_get_db_session

    # 4. Skip Redis rate-limiting (None bypasses the limit check)
    app.dependency_overrides[broker_runtime.get_rate_limit_redis] = lambda: None

    return app


@pytest.fixture
def broker_client(broker_app: FastAPI) -> TestClient:
    """Return a TestClient for the broker test app."""
    return TestClient(broker_app)


@pytest.fixture
def broker_workspace_context(
    db_service: DatabaseService,
    test_user: User,
) -> dict[str, UUID]:
    """Create workspace, environment, and environment-version for broker tests."""
    with db_service.get_session() as session:
        org = Organization(
            id=uuid4(),
            name="Broker Test Org",
            slug=f"broker-test-org-{uuid4().hex[:8]}",
            owner_id=test_user.id,
        )
        session.add(org)
        session.flush()

        workspace = Workspace(
            id=uuid4(),
            organization_id=org.id,
            name="Broker Test Workspace",
            slug=f"broker-test-ws-{uuid4().hex[:8]}",
        )
        environment = Environment(
            id=uuid4(),
            org_id=org.id,
            name=f"broker-test-env-{uuid4().hex[:8]}",
        )
        session.add_all([workspace, environment])
        session.flush()

        env_version = EnvironmentVersion(
            id=uuid4(),
            environment_id=environment.id,
            version_number=1,
            variables={},
            credentials={},
        )
        session.add(env_version)
        session.commit()
        session.refresh(env_version)
        session.expunge_all()

        return {
            "workspace_id": workspace.id,
            "environment_id": environment.id,
            "environment_version_id": env_version.id,
            "user_id": test_user.id,
        }


@pytest.fixture
async def broker_sandbox_session(
    db_service: DatabaseService,
    broker_workspace_context: dict[str, UUID],
) -> dict:
    """Mint a sandbox session and return the plaintext token + session record."""
    workspace_id = broker_workspace_context["workspace_id"]
    env_version_id = broker_workspace_context["environment_version_id"]

    async with db_service.get_async_session() as session:
        service = SandboxSessionService(session)
        token, sandbox_session = await service.create_session(
            workspace_id=workspace_id,
            environment_version_id=env_version_id,
            ttl_seconds=3600,
        )
        await session.refresh(sandbox_session)
        return {
            "token": token,
            "sandbox_session": sandbox_session,
            "workspace_id": workspace_id,
            "environment_version_id": env_version_id,
        }


# ============================================================================
# Helpers
# ============================================================================


def _set_environment_credentials(
    db_service: DatabaseService,
    environment_version_id: UUID,
    credentials: dict,
) -> None:
    """Persist credential alias mappings for a test environment version."""
    with db_service.get_session() as session:
        env_version = session.get(EnvironmentVersion, environment_version_id)
        assert env_version is not None
        env_version.credentials = credentials
        session.commit()


def _create_bearer_binding(
    credential_broker_service: CredentialBrokerService,
    workspace_id: UUID,
    name: str,
    value: str,
) -> CredentialBinding:
    """Helper to create a bearer_secret binding."""
    return credential_broker_service.create_binding(
        workspace_id=workspace_id,
        kind="bearer_secret",
        name=name,
        value=value,
    )


def _create_user_credential(
    db_service: DatabaseService,
    encryption_service: CredentialEncryptionService,
    user_id: UUID,
    provider: str,
    name: str,
    access_token: str,
    expires_at,
) -> UUID:
    """Helper to create a UserCredential record and return its ID."""
    with db_service.get_session() as session:
        credential = UserCredential(
            id=uuid4(),
            user_id=user_id,
            provider=provider,
            name=name,
            api_key="legacy-token",
            encrypted_value=encryption_service.encrypt(access_token),
            config_data={"expires_at": expires_at.isoformat()},
            is_active=True,
        )
        session.add(credential)
        session.commit()
        session.refresh(credential)
        return credential.id


# ============================================================================
# Success Cases — All 3 Kinds
# ============================================================================


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_get_bearer_secret_alias_200(
    broker_client: TestClient,
    db_service: DatabaseService,
    credential_broker_service: CredentialBrokerService,
    broker_workspace_context: dict[str, UUID],
    broker_sandbox_session: dict,
):
    """GET /broker/creds/<bearer_alias> returns decrypted secret payload."""
    workspace_id = broker_workspace_context["workspace_id"]
    env_version_id = broker_workspace_context["environment_version_id"]
    token = broker_sandbox_session["token"]

    binding = _create_bearer_binding(
        credential_broker_service,
        workspace_id=workspace_id,
        name="anthropic-api-key",
        value="sk-ant-test-secret-123",
    )

    _set_environment_credentials(
        db_service,
        env_version_id,
        {
            "anthropic": {
                "kind": "bearer_secret",
                "binding_id": str(binding.id),
            }
        },
    )

    response = broker_client.get(
        "/broker/creds/anthropic",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "kind": "bearer_secret",
        "value": "sk-ant-test-secret-123",
    }

    # Audit log assertion
    with db_service.get_session() as session:
        log_entry = (
            session.query(CredentialAccessLog)
            .filter(
                CredentialAccessLog.sandbox_session_id
                == broker_sandbox_session["sandbox_session"].id,
                CredentialAccessLog.action == "inject",
            )
            .one()
        )
        assert log_entry.workspace_id == workspace_id
        assert log_entry.access_metadata == {
            "alias": "anthropic",
            "kind": "bearer_secret",
        }


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_get_user_oauth_alias_200(
    broker_client: TestClient,
    db_service: DatabaseService,
    credential_broker_service: CredentialBrokerService,
    encryption_service: CredentialEncryptionService,
    broker_workspace_context: dict[str, UUID],
    broker_sandbox_session: dict,
):
    """GET /broker/creds/<oauth_alias> returns access_token + expires_at payload."""
    workspace_id = broker_workspace_context["workspace_id"]
    env_version_id = broker_workspace_context["environment_version_id"]
    user_id = broker_workspace_context["user_id"]
    token = broker_sandbox_session["token"]

    # Create a user credential that is NOT near expiry (so no refresh is triggered)
    future_expiry = utc_now() + timedelta(hours=1)
    credential_id = _create_user_credential(
        db_service,
        encryption_service,
        user_id=user_id,
        provider="github",
        name="github-oauth",
        access_token="gho_test_oauth_token_456",
        expires_at=future_expiry,
    )

    _set_environment_credentials(
        db_service,
        env_version_id,
        {
            "github": {
                "kind": "user_oauth",
                "credential_id": str(credential_id),
            }
        },
    )

    response = broker_client.get(
        "/broker/creds/github",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "user_oauth"
    assert payload["access_token"] == "gho_test_oauth_token_456"
    assert payload["expires_at"] == future_expiry.isoformat()

    # Audit log assertion
    with db_service.get_session() as session:
        log_entry = (
            session.query(CredentialAccessLog)
            .filter(
                CredentialAccessLog.sandbox_session_id
                == broker_sandbox_session["sandbox_session"].id,
                CredentialAccessLog.action == "inject",
            )
            .one()
        )
        assert log_entry.workspace_id == workspace_id
        assert log_entry.access_metadata == {
            "alias": "github",
            "kind": "user_oauth",
        }


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_get_github_app_alias_200(
    broker_client: TestClient,
    db_service: DatabaseService,
    credential_broker_service: CredentialBrokerService,
    broker_workspace_context: dict[str, UUID],
    broker_sandbox_session: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    """GET /broker/creds/<github_app_alias> returns minted installation token."""
    workspace_id = broker_workspace_context["workspace_id"]
    env_version_id = broker_workspace_context["environment_version_id"]
    token = broker_sandbox_session["token"]

    future_expiry = utc_now() + timedelta(minutes=30)

    async def mock_request_github_installation_token(mapping: dict) -> dict:
        assert mapping["installation_id"] == "78901234"
        return {
            "token": "ghs_test_installation_token_789",
            "expires_at": future_expiry.isoformat(),
        }

    monkeypatch.setattr(
        credential_broker_service,
        "_request_github_installation_token",
        mock_request_github_installation_token,
    )

    _set_environment_credentials(
        db_service,
        env_version_id,
        {
            "github-app": {
                "kind": "github_app",
                "app_id": "123456",
                "installation_id": "78901234",
            }
        },
    )

    response = broker_client.get(
        "/broker/creds/github-app",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "kind": "github_app",
        "token": "ghs_test_installation_token_789",
        "expires_at": future_expiry.isoformat(),
    }

    # Audit log assertion
    with db_service.get_session() as session:
        log_entry = (
            session.query(CredentialAccessLog)
            .filter(
                CredentialAccessLog.sandbox_session_id
                == broker_sandbox_session["sandbox_session"].id,
                CredentialAccessLog.action == "inject",
            )
            .one()
        )
        assert log_entry.workspace_id == workspace_id
        assert log_entry.access_metadata == {
            "alias": "github-app",
            "kind": "github_app",
        }


# ============================================================================
# Failure Cases
# ============================================================================


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_get_unknown_alias_404(
    broker_client: TestClient,
    broker_sandbox_session: dict,
):
    """Unknown alias returns 404."""
    token = broker_sandbox_session["token"]

    response = broker_client.get(
        "/broker/creds/nonexistent",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_revoked_session_401(
    broker_client: TestClient,
    db_service: DatabaseService,
    broker_workspace_context: dict[str, UUID],
    broker_sandbox_session: dict,
):
    """Revoked session token returns 401."""
    token = broker_sandbox_session["token"]
    session_id = broker_sandbox_session["sandbox_session"].id

    # Revoke the session via the database
    async with db_service.get_async_session() as session:
        svc = SandboxSessionService(session)
        await svc.revoke(session_id)

    response = broker_client.get(
        "/broker/creds/anything",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_cross_workspace_denial_404(
    broker_client: TestClient,
    db_service: DatabaseService,
    credential_broker_service: CredentialBrokerService,
    broker_workspace_context: dict[str, UUID],
    broker_sandbox_session: dict,
    test_user: User,
):
    """Session from workspace B cannot resolve alias defined in workspace A."""
    workspace_a_id = broker_workspace_context["workspace_id"]

    with db_service.get_session() as session:
        org_b = Organization(
            id=uuid4(),
            name="Broker Test Org B",
            slug=f"broker-test-org-b-{uuid4().hex[:8]}",
            owner_id=test_user.id,
        )
        session.add(org_b)
        session.flush()

        workspace_b = Workspace(
            id=uuid4(),
            organization_id=org_b.id,
            name="Broker Test Workspace B",
            slug=f"broker-test-ws-b-{uuid4().hex[:8]}",
        )
        environment_b = Environment(
            id=uuid4(),
            org_id=org_b.id,
            name=f"broker-test-env-b-{uuid4().hex[:8]}",
        )
        session.add_all([workspace_b, environment_b])
        session.flush()

        env_version_b = EnvironmentVersion(
            id=uuid4(),
            environment_id=environment_b.id,
            version_number=1,
            variables={},
            credentials={},
        )
        session.add(env_version_b)
        session.commit()
        session.refresh(env_version_b)

    # Create a sandbox session for workspace B
    async with db_service.get_async_session() as session:
        svc = SandboxSessionService(session)
        token_b, _session_b = await svc.create_session(
            workspace_id=workspace_b.id,
            environment_version_id=env_version_b.id,
            ttl_seconds=3600,
        )

    # Create a binding and alias map in workspace A
    binding = _create_bearer_binding(
        credential_broker_service,
        workspace_id=workspace_a_id,
        name="secret-key",
        value="workspace-a-secret",
    )

    _set_environment_credentials(
        db_service,
        broker_workspace_context["environment_version_id"],
        {
            "secret-key": {
                "kind": "bearer_secret",
                "binding_id": str(binding.id),
            }
        },
    )

    # Session from workspace B tries to access workspace A's alias
    response = broker_client.get(
        "/broker/creds/secret-key",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    # Should be 404 because workspace B's env-version does not have this alias
    assert response.status_code == 404
