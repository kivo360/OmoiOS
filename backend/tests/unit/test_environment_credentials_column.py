"""Test environment_versions credentials column.

Tests the credentials JSONB column on EnvironmentVersion model.
"""

import pytest
from sqlalchemy import select

from omoi_os.models.environment import Environment, EnvironmentVersion
from omoi_os.services.database import DatabaseService


@pytest.mark.unit
class TestEnvironmentCredentialsColumn:
    """Test suite for environment_versions credentials column."""

    def test_credentials_defaults_to_empty_dict(
        self, db_service: DatabaseService
    ) -> None:
        """Test that credentials defaults to empty dict on insert."""
        with db_service.get_session() as session:
            env = Environment(
                org_id="12345678-1234-1234-1234-123456789abc",
                name="test-env",
            )
            session.add(env)
            session.flush()

            version = EnvironmentVersion(
                environment_id=env.id,
                version_number=1,
                variables={},
            )
            session.add(version)
            session.commit()

            result = session.execute(
                select(EnvironmentVersion.credentials).where(
                    EnvironmentVersion.id == version.id
                )
            ).scalar()

            assert result == {}

    def test_credentials_stores_alias_map(self, db_service: DatabaseService) -> None:
        """Test that credentials can store alias map with binding references."""
        with db_service.get_session() as session:
            env = Environment(
                org_id="12345678-1234-1234-1234-123456789abc",
                name="test-env-with-creds",
            )
            session.add(env)
            session.flush()

            credentials_data = {
                "anthropic": {
                    "kind": "bearer_secret",
                    "binding_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                },
                "github": {
                    "kind": "github_app",
                    "app_id": "123456",
                    "installation_id": "78901234",
                },
            }

            version = EnvironmentVersion(
                environment_id=env.id,
                version_number=1,
                variables={},
                credentials=credentials_data,
            )
            session.add(version)
            session.commit()

            session.refresh(version)

            assert version.credentials is not None
            assert version.credentials == credentials_data
            assert version.credentials["anthropic"]["kind"] == "bearer_secret"
            assert version.credentials["github"]["kind"] == "github_app"

    def test_credentials_is_nullable(self, db_service: DatabaseService) -> None:
        """Test that credentials column accepts NULL."""
        with db_service.get_session() as session:
            env = Environment(
                org_id="12345678-1234-1234-1234-123456789abc",
                name="test-env-null-creds",
            )
            session.add(env)
            session.flush()

            version = EnvironmentVersion(
                environment_id=env.id,
                version_number=1,
                variables={},
                credentials=None,
            )
            session.add(version)
            session.commit()

            session.refresh(version)

            assert version.credentials is None

    def test_credentials_empty_dict_not_null(self, db_service: DatabaseService) -> None:
        """Test that empty dict is stored, not converted to NULL."""
        with db_service.get_session() as session:
            env = Environment(
                org_id="12345678-1234-1234-1234-123456789abc",
                name="test-env-empty-creds",
            )
            session.add(env)
            session.flush()

            version = EnvironmentVersion(
                environment_id=env.id,
                version_number=1,
                variables={},
                credentials={},
            )
            session.add(version)
            session.commit()

            result = session.execute(
                select(EnvironmentVersion.credentials).where(
                    EnvironmentVersion.id == version.id
                )
            ).scalar()

            assert result == {}
            assert result is not None
