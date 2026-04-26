"""Webhooks resource for OmoiOS API."""

from typing import List

from omoios.resources.base import BaseResource
from omoios.types import CreateWebhookRequest, WebhookDelivery, WebhookSubscription


class WebhooksResource(BaseResource):
    """Resource for managing webhook subscriptions.

    Example:
        >>> client = AsyncOmoiOSClient("https://api.omoios.dev", api_key="key")
        >>> webhooks = await client.webhooks.list()
        >>> print(webhooks[0].url)
    """

    async def list(self) -> List[WebhookSubscription]:
        """List webhook subscriptions.

        Returns:
            List of webhook subscriptions

        Example:
            >>> webhooks = await client.webhooks.list()
        """
        response = await self._client._request(
            "GET", "/api/v1/webhooks/subscriptions"
        )
        return [WebhookSubscription.model_validate(item) for item in response.json()]

    async def create(self, request: CreateWebhookRequest) -> WebhookSubscription:
        """Create a webhook subscription.

        Args:
            request: Create webhook request

        Returns:
            Created webhook subscription

        Example:
            >>> request = CreateWebhookRequest(
            ...     url="https://myapp.com/webhook",
            ...     events=[WebhookEvent.SPEC_CREATED],
            ...     secret="webhook-secret",
            ... )
            >>> webhook = await client.webhooks.create(request)
        """
        response = await self._client._request(
            "POST",
            "/api/v1/webhooks/subscriptions",
            json=request.model_dump(mode="json"),
        )
        return WebhookSubscription.model_validate(response.json())

    async def delete(self, webhook_id: str) -> None:
        """Delete a webhook subscription.

        Args:
            webhook_id: Webhook ID to delete

        Raises:
            NotFoundError: If webhook doesn't exist

        Example:
            >>> await client.webhooks.delete("wh-1")
        """
        await self._client._request(
            "DELETE", f"/api/v1/webhooks/subscriptions/{webhook_id}"
        )

    async def list_deliveries(self, subscription_id: str) -> List[WebhookDelivery]:
        """List webhook deliveries for a subscription.

        Args:
            subscription_id: Subscription ID

        Returns:
            List of webhook deliveries

        Raises:
            NotFoundError: If subscription doesn't exist

        Example:
            >>> deliveries = await client.webhooks.list_deliveries("wh-1")
        """
        response = await self._client._request(
            "GET",
            f"/api/v1/webhooks/subscriptions/{subscription_id}/deliveries",
        )
        return [WebhookDelivery.model_validate(item) for item in response.json()]
