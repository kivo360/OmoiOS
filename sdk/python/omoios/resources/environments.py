"""Environments resource for OmoiOS API."""

from typing import Dict, List, Optional

from omoios.resources.base import BaseResource
from omoios.types import (
    CreateEnvironmentRequest,
    CreateEnvironmentVersionRequest,
    Environment,
    EnvironmentVersion,
)


class EnvironmentsResource(BaseResource):
    """Resource for managing environments.

    Example:
        >>> client = AsyncOmoiOSClient("https://api.omoios.dev", api_key="key")
        >>> envs = await client.environments.list(org_id="org-1")
        >>> print(envs[0].name)
    """

    async def list(self, org_id: str) -> List[Environment]:
        """List environments in an organization.

        Args:
            org_id: Organization ID to filter by

        Returns:
            List of environments

        Example:
            >>> envs = await client.environments.list(org_id="org-1")
        """
        response = await self._client._request(
            "GET", "/api/v1/environments", params={"org_id": org_id}
        )
        return [Environment.model_validate(item) for item in response.json()]

    async def get(self, environment_id: str) -> Dict[str, object]:
        """Get environment by ID with its latest version.

        Args:
            environment_id: Environment ID

        Returns:
            Dict with 'environment' and 'latest_version' keys

        Raises:
            NotFoundError: If environment doesn't exist

        Example:
            >>> result = await client.environments.get("env-1")
            >>> print(result["environment"].name)
        """
        response = await self._client._request("GET", f"/api/v1/environments/{environment_id}")
        data = response.json()
        result: Dict[str, object] = {
            "environment": Environment.model_validate(data["environment"]),
        }
        if data.get("latest_version"):
            result["latest_version"] = EnvironmentVersion.model_validate(data["latest_version"])
        else:
            result["latest_version"] = None
        return result

    async def get_version(
        self, environment_id: str, version_number: int
    ) -> EnvironmentVersion:
        """Fetch a specific (non-latest) version by its sequential number.

        Used by `omoios environments rollback` and any caller that needs
        to read v(N-1) — versions are immutable, so this never changes.

        Raises:
            NotFoundError: If env or version doesn't exist.
        """
        response = await self._client._request(
            "GET",
            f"/api/v1/environments/{environment_id}/versions/{version_number}",
        )
        return EnvironmentVersion.model_validate(response.json())

    async def create(self, request: CreateEnvironmentRequest) -> Environment:
        """Create a new environment.

        Args:
            request: Create environment request

        Returns:
            Created environment

        Example:
            >>> request = CreateEnvironmentRequest(
            ...     name="staging", description="Staging env", org_id="org-1"
            ... )
            >>> env = await client.environments.create(request)
        """
        response = await self._client._request(
            "POST",
            "/api/v1/environments",
            json=request.model_dump(mode="json"),
        )
        return Environment.model_validate(response.json())

    async def create_version(
        self, environment_id: str, request: CreateEnvironmentVersionRequest
    ) -> EnvironmentVersion:
        """Create a new environment version.

        Args:
            environment_id: Environment ID
            request: Create version request

        Returns:
            Created environment version

        Raises:
            NotFoundError: If environment doesn't exist

        Example:
            >>> request = CreateEnvironmentVersionRequest(
            ...     variables={"DB_URL": EnvironmentVariable(type="string", value="...")}
            ... )
            >>> version = await client.environments.create_version("env-1", request)
        """
        response = await self._client._request(
            "POST",
            f"/api/v1/environments/{environment_id}/versions",
            json=request.model_dump(mode="json"),
        )
        return EnvironmentVersion.model_validate(response.json())
