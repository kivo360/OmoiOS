"""HTTP client for BetterStack — Telemetry, Errors, Uptime.

All three product APIs share Bearer-token auth. A single Global API token
(https://betterstack.com/settings/global-api-tokens) works against all of
them; team-scoped tokens can substitute for whichever product they cover.

Reference: docs/betterstack-reference.md
"""

from __future__ import annotations

import os
from typing import Any, Iterable

import httpx

# Default token. Override via env var BETTERSTACK_API_KEY or constructor arg.
# Throwaway key — rotate at https://betterstack.com/settings/global-api-tokens
DEFAULT_TOKEN = "gosbHVnBbCF6eDdWn7FCWqSd"

TELEMETRY_BASE = "https://telemetry.betterstack.com"
UPTIME_BASE = "https://uptime.betterstack.com"
ERRORS_BASE = "https://errors.betterstack.com"

OTLP_GLOBAL_HOST = "https://in-otel.logs.betterstack.com"
OTLP_PATHS = {
    "traces": f"{OTLP_GLOBAL_HOST}/v1/traces",
    "logs": f"{OTLP_GLOBAL_HOST}/v1/logs",
    "metrics": f"{OTLP_GLOBAL_HOST}/v1/metrics",
}


class BetterStackAPIError(RuntimeError):
    """Raised when an API call returns a non-2xx response."""

    def __init__(self, response: httpx.Response):
        self.response = response
        body = response.text[:1000]
        super().__init__(
            f"BetterStack API error {response.status_code} on "
            f"{response.request.method} {response.request.url}: {body}"
        )


class ResourceNotFound(BetterStackAPIError):
    """404 from the API."""


class BetterStack:
    def __init__(self, token: str | None = None, *, timeout: float = 30.0) -> None:
        self.token = token or os.environ.get("BETTERSTACK_API_KEY") or DEFAULT_TOKEN
        if not self.token:
            raise RuntimeError("No BetterStack API token provided")
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "betterstack-toolkit/0.1",
            },
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "BetterStack":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Low-level
    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        resp = self.client.request(method, url, json=json, params=params)
        if resp.status_code == 404:
            raise ResourceNotFound(resp)
        if resp.status_code >= 400:
            raise BetterStackAPIError(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def _paginate(self, url: str, params: dict[str, Any] | None = None) -> Iterable[dict]:
        """Yield items across all pages of a JSON:API list endpoint."""
        params = dict(params or {})
        params.setdefault("per_page", 50)
        while url:
            payload = self._request("GET", url, params=params)
            for item in payload.get("data") or []:
                yield item
            next_url = (payload.get("pagination") or {}).get("next")
            if not next_url or next_url == url:
                break
            url = next_url
            params = None  # next_url already encodes them

    # ------------------------------------------------------------------
    # Telemetry — sources
    # ------------------------------------------------------------------
    def list_sources(self) -> list[dict]:
        return list(self._paginate(f"{TELEMETRY_BASE}/api/v1/sources"))

    def get_source(self, source_id: str | int) -> dict:
        return self._request("GET", f"{TELEMETRY_BASE}/api/v1/sources/{source_id}")["data"]

    def create_source(
        self,
        name: str,
        *,
        platform: str = "open_telemetry",
        data_region: str | None = None,
        logs_retention: int | None = None,
        metrics_retention: int | None = None,
        **extra: Any,
    ) -> dict:
        payload = {"name": name, "platform": platform, **extra}
        if data_region is not None:
            payload["data_region"] = data_region
        if logs_retention is not None:
            payload["logs_retention"] = logs_retention
        if metrics_retention is not None:
            payload["metrics_retention"] = metrics_retention
        return self._request("POST", f"{TELEMETRY_BASE}/api/v1/sources", json=payload)["data"]

    def delete_source(self, source_id: str | int) -> None:
        self._request("DELETE", f"{TELEMETRY_BASE}/api/v1/sources/{source_id}")

    # ------------------------------------------------------------------
    # Errors — applications (Sentry-compatible ingestion)
    # ------------------------------------------------------------------
    def list_apps(self) -> list[dict]:
        return list(self._paginate(f"{ERRORS_BASE}/api/v1/applications"))

    def get_app(self, app_id: str | int) -> dict:
        return self._request(
            "GET", f"{ERRORS_BASE}/api/v1/applications/{app_id}"
        )["data"]

    def create_app(
        self,
        name: str,
        *,
        platform: str | None = None,
        environment: str | None = None,
        **extra: Any,
    ) -> dict:
        platform = platform or "python"
        if not platform.endswith("_errors"):
            # BetterStack requires platform to be suffixed with "_errors"
            # Strip a "_telemetry" suffix some users might paste in.
            platform = platform.removesuffix("_telemetry") + "_errors"
        payload: dict[str, Any] = {"name": name, "platform": platform, **extra}
        if environment:
            payload["environment"] = environment
        return self._request(
            "POST", f"{ERRORS_BASE}/api/v1/applications", json=payload
        )["data"]

    def delete_app(self, app_id: str | int) -> None:
        self._request("DELETE", f"{ERRORS_BASE}/api/v1/applications/{app_id}")

    @staticmethod
    def app_dsn(app: dict) -> str | None:
        """Build a Sentry-compatible DSN from an application record.

        Format: https://<application-token>@<ingesting-host>/1
        """
        attrs = app.get("attributes") or app
        token = attrs.get("token") or attrs.get("application_token")
        host = attrs.get("ingesting_host")
        if not (token and host):
            return None
        return f"https://{token}@{host}/1"

    # ------------------------------------------------------------------
    # Uptime — monitors
    # ------------------------------------------------------------------
    def list_monitors(self, **filters: Any) -> list[dict]:
        return list(self._paginate(f"{UPTIME_BASE}/api/v2/monitors", params=filters))

    def get_monitor(self, monitor_id: str | int) -> dict:
        return self._request("GET", f"{UPTIME_BASE}/api/v2/monitors/{monitor_id}")["data"]

    def create_monitor(
        self,
        url: str,
        *,
        monitor_type: str = "status",
        check_frequency: int = 180,
        regions: list[str] | None = None,
        email: bool = True,
        sms: bool = False,
        call: bool = False,
        push: bool = True,
        request_timeout: int = 30,
        recovery_period: int = 0,
        confirmation_period: int = 0,
        verify_ssl: bool = True,
        expected_status_codes: list[int] | None = None,
        policy_id: int | None = None,
        pronounceable_name: str | None = None,
        **extra: Any,
    ) -> dict:
        payload: dict[str, Any] = {
            "url": url,
            "monitor_type": monitor_type,
            "check_frequency": check_frequency,
            "email": email,
            "sms": sms,
            "call": call,
            "push": push,
            "request_timeout": request_timeout,
            "recovery_period": recovery_period,
            "confirmation_period": confirmation_period,
            "verify_ssl": verify_ssl,
            **extra,
        }
        if regions:
            payload["regions"] = regions
        if expected_status_codes:
            payload["expected_status_codes"] = expected_status_codes
        if policy_id is not None:
            payload["policy_id"] = policy_id
        if pronounceable_name:
            payload["pronounceable_name"] = pronounceable_name
        return self._request("POST", f"{UPTIME_BASE}/api/v2/monitors", json=payload)["data"]

    def delete_monitor(self, monitor_id: str | int) -> None:
        self._request("DELETE", f"{UPTIME_BASE}/api/v2/monitors/{monitor_id}")

    # ------------------------------------------------------------------
    # Uptime — heartbeats
    # ------------------------------------------------------------------
    def list_heartbeats(self) -> list[dict]:
        return list(self._paginate(f"{UPTIME_BASE}/api/v2/heartbeats"))

    def get_heartbeat(self, heartbeat_id: str | int) -> dict:
        return self._request(
            "GET", f"{UPTIME_BASE}/api/v2/heartbeats/{heartbeat_id}"
        )["data"]

    def create_heartbeat(
        self,
        name: str,
        *,
        period: int = 60,
        grace: int = 30,
        email: bool = True,
        sms: bool = False,
        call: bool = False,
        push: bool = True,
        policy_id: int | None = None,
        **extra: Any,
    ) -> dict:
        payload: dict[str, Any] = {
            "name": name,
            "period": period,
            "grace": grace,
            "email": email,
            "sms": sms,
            "call": call,
            "push": push,
            **extra,
        }
        if policy_id is not None:
            payload["policy_id"] = policy_id
        return self._request("POST", f"{UPTIME_BASE}/api/v2/heartbeats", json=payload)["data"]

    def delete_heartbeat(self, heartbeat_id: str | int) -> None:
        self._request("DELETE", f"{UPTIME_BASE}/api/v2/heartbeats/{heartbeat_id}")

    # ------------------------------------------------------------------
    # Uptime — incidents (v3)
    # ------------------------------------------------------------------
    def list_incidents(self, **filters: Any) -> list[dict]:
        return list(self._paginate(f"{UPTIME_BASE}/api/v3/incidents", params=filters))

    def get_incident(self, incident_id: str | int) -> dict:
        return self._request("GET", f"{UPTIME_BASE}/api/v3/incidents/{incident_id}")["data"]

    def acknowledge_incident(self, incident_id: str | int) -> dict:
        return self._request(
            "POST", f"{UPTIME_BASE}/api/v3/incidents/{incident_id}/acknowledge"
        )

    def resolve_incident(self, incident_id: str | int) -> dict:
        return self._request(
            "POST", f"{UPTIME_BASE}/api/v3/incidents/{incident_id}/resolve"
        )

    # ------------------------------------------------------------------
    # Uptime — escalation policies (v3)
    # ------------------------------------------------------------------
    def list_policies(self) -> list[dict]:
        return list(self._paginate(f"{UPTIME_BASE}/api/v3/policies"))

    def get_policy(self, policy_id: str | int) -> dict:
        return self._request("GET", f"{UPTIME_BASE}/api/v3/policies/{policy_id}")["data"]

    # ------------------------------------------------------------------
    # Uptime — status pages
    # ------------------------------------------------------------------
    def list_status_pages(self) -> list[dict]:
        return list(self._paginate(f"{UPTIME_BASE}/api/v2/status-pages"))

    def get_status_page(self, page_id: str | int) -> dict:
        return self._request("GET", f"{UPTIME_BASE}/api/v2/status-pages/{page_id}")["data"]

    def create_status_page(
        self,
        company_name: str,
        subdomain: str,
        *,
        timezone: str = "UTC",
        **extra: Any,
    ) -> dict:
        payload = {
            "company_name": company_name,
            "subdomain": subdomain,
            "timezone": timezone,
            **extra,
        }
        return self._request(
            "POST", f"{UPTIME_BASE}/api/v2/status-pages", json=payload
        )["data"]

    # ------------------------------------------------------------------
    # Telemetry — alerts (v2)
    # ------------------------------------------------------------------
    def list_alerts(self) -> list[dict]:
        return list(self._paginate(f"{TELEMETRY_BASE}/api/v2/alerts"))

    def get_alert(self, alert_id: str | int) -> dict:
        return self._request(
            "GET", f"{TELEMETRY_BASE}/api/v2/alerts/{alert_id}"
        )["data"]

    def delete_alert(self, alert_id: str | int) -> None:
        self._request("DELETE", f"{TELEMETRY_BASE}/api/v2/alerts/{alert_id}")

    # ------------------------------------------------------------------
    # High-level: bootstrap a complete project
    # ------------------------------------------------------------------
    def bootstrap_project(
        self,
        name: str,
        *,
        monitor_url: str | None = None,
        heartbeat_name: str | None = None,
        platform: str = "open_telemetry",
        data_region: str | None = None,
    ) -> dict:
        """Create a Telemetry source, an Errors application, and (optionally)
        an Uptime monitor and heartbeat in one shot.

        Returns a dict with `source`, `app`, `monitor`, `heartbeat`, plus
        `dsn`, `otlp_headers`, and `ingesting_host` for immediate copy-paste.
        """
        result: dict[str, Any] = {"name": name}

        # 1. Telemetry source for OTLP traces/logs/metrics
        source = self.create_source(
            f"{name}-telemetry", platform=platform, data_region=data_region
        )
        sattrs = source.get("attributes") or source
        result["source"] = source
        result["source_token"] = sattrs.get("token")
        result["ingesting_host"] = sattrs.get("ingesting_host")

        # 2. Errors application for Sentry-SDK ingestion
        try:
            app = self.create_app(f"{name}-errors", platform="python")
            result["app"] = app
            result["dsn"] = self.app_dsn(app)
        except BetterStackAPIError as e:
            # Errors product may not be enabled on this team — record and continue
            result["app_error"] = str(e)

        # 3. Optional uptime monitor
        if monitor_url:
            result["monitor"] = self.create_monitor(monitor_url)

        # 4. Optional heartbeat
        if heartbeat_name:
            result["heartbeat"] = self.create_heartbeat(heartbeat_name)

        # 5. Convenience: pre-built env vars for the user to export
        if result["source_token"]:
            result["otlp_endpoint"] = OTLP_GLOBAL_HOST
            result["otlp_headers"] = f"Authorization=Bearer {result['source_token']}"
            result["otlp_paths"] = OTLP_PATHS

        return result
