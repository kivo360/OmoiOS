"""BetterStack observability wiring — Errors + Telemetry + Uptime.

This module owns the side-effects of integrating with BetterStack:

* **Errors** — initialize the Sentry SDK with the BetterStack-issued
  Sentry-compatible DSN. The SDK ships exceptions, transactions, and
  breadcrumbs to BetterStack's Errors product.

* **Telemetry** — wire OpenTelemetry providers (TracerProvider,
  MeterProvider, LoggerProvider) with OTLP/HTTP exporters pointed at the
  source-specific ingesting host. The TracerProvider also runs a
  ``SentrySpanProcessor`` so spans fan out to both Sentry and BetterStack
  Telemetry.

* **Uptime** — run an asyncio heartbeat task that pings the configured
  heartbeat URL every ``heartbeat_period_seconds``.

Public entrypoint: :func:`init_betterstack` (idempotent, safe to call
multiple times — second and subsequent calls return the same handle).

The module degrades gracefully when:

* No DSN is configured → Sentry init is skipped.
* No source token is configured → OTel exporters are skipped.
* No heartbeat token is configured → the heartbeat task is skipped.

So the same code can run in dev (everything off), staging (errors + traces),
and production (everything on) by toggling env vars only.

Reference: docs/architecture/observability_unified.md
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from omoi_os.config import BetterStackSettings, ObservabilitySettings, get_app_settings
from omoi_os.logging import get_logger
from omoi_os.utils.asyncio_tasks import fire_and_forget

logger = get_logger(__name__)

UPTIME_HEARTBEAT_URL = "https://uptime.betterstack.com/api/v1/heartbeat"


@dataclass
class BetterStackHandle:
    """Holds the live providers + heartbeat task so callers can flush/cancel.

    Use as a context manager in scripts; long-running services should call
    :meth:`flush` on shutdown to make sure buffered telemetry ships.
    """

    sentry_initialized: bool = False
    tracer_provider: Optional[Any] = None
    meter_provider: Optional[Any] = None
    logger_provider: Optional[Any] = None
    heartbeat_task: Optional[asyncio.Task] = None
    instrumented: list[str] = field(default_factory=list)

    def flush(self, timeout_seconds: float = 5.0) -> None:
        """Force-flush every buffered exporter. Safe to call from shutdown hooks."""
        timeout_ms = int(timeout_seconds * 1000)
        if self.tracer_provider is not None:
            try:
                self.tracer_provider.force_flush(timeout_millis=timeout_ms)
            except Exception as exc:  # noqa: BLE001
                logger.debug("BetterStack tracer flush raised: %s", exc)
        if self.meter_provider is not None:
            try:
                self.meter_provider.force_flush(timeout_millis=timeout_ms)
            except Exception as exc:  # noqa: BLE001
                logger.debug("BetterStack meter flush raised: %s", exc)
        if self.logger_provider is not None:
            try:
                self.logger_provider.force_flush(timeout_millis=timeout_ms)
            except Exception as exc:  # noqa: BLE001
                logger.debug("BetterStack logger flush raised: %s", exc)
        if self.sentry_initialized:
            try:
                import sentry_sdk

                sentry_sdk.flush(timeout=timeout_seconds)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Sentry flush raised: %s", exc)

    def shutdown(self) -> None:
        if self.heartbeat_task is not None and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
        self.flush()


# Single live handle so init_betterstack() is idempotent.
_handle: Optional[BetterStackHandle] = None


def get_handle() -> Optional[BetterStackHandle]:
    """Return the current live handle (or None if not initialized)."""
    return _handle


def init_betterstack(
    *,
    settings: Optional[BetterStackSettings] = None,
    obs_settings: Optional[ObservabilitySettings] = None,
    start_heartbeat: bool = True,
) -> BetterStackHandle:
    """Initialize the BetterStack pipelines. Idempotent.

    Returns a :class:`BetterStackHandle` describing what's now live.
    """
    global _handle
    if _handle is not None:
        return _handle

    app = get_app_settings()
    settings = settings or app.betterstack
    obs_settings = obs_settings or app.observability

    handle = BetterStackHandle()

    handle.sentry_initialized = _init_sentry(settings, obs_settings)
    if settings.is_otlp_configured:
        resource = _build_resource(obs_settings)
        if settings.enable_traces:
            handle.tracer_provider = _init_tracer_provider(
                settings, resource, sentry_attached=handle.sentry_initialized
            )
        if settings.enable_metrics:
            handle.meter_provider = _init_meter_provider(settings, resource)
        if settings.enable_logs:
            handle.logger_provider = _init_logger_provider(settings, resource)

    if start_heartbeat and settings.heartbeat_token:
        handle.heartbeat_task = _start_heartbeat(settings)

    _handle = handle
    logger.info(
        "BetterStack observability initialized",
        sentry=handle.sentry_initialized,
        traces=handle.tracer_provider is not None,
        metrics=handle.meter_provider is not None,
        logs=handle.logger_provider is not None,
        heartbeat=handle.heartbeat_task is not None,
    )
    return handle


# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------


def _init_sentry(settings: BetterStackSettings, obs: ObservabilitySettings) -> bool:
    if not settings.is_errors_configured:
        return False
    try:
        import sentry_sdk
    except ImportError as exc:
        logger.warning("sentry-sdk import failed: %s", exc)
        return False

    deployment_environment = (
        obs.deployment_environment
        or os.environ.get("APP_ENV")
        or os.environ.get("OMOIOS_ENV")
        or "local"
    )

    sentry_sdk.init(
        dsn=settings.errors_dsn,
        environment=deployment_environment,
        release=obs.release,
        traces_sample_rate=settings.traces_sample_rate,
        profiles_sample_rate=settings.profiles_sample_rate,
        send_default_pii=False,
        # We manage the OTel TracerProvider explicitly below — letting Sentry
        # try to set one up too races with our setup. The SentrySpanProcessor
        # is what bridges the two worlds.
        instrumenter="otel",
    )
    return True


# ---------------------------------------------------------------------------
# OpenTelemetry providers
# ---------------------------------------------------------------------------


def _build_resource(obs: ObservabilitySettings):
    from opentelemetry.sdk.resources import Resource

    deployment_environment = (
        obs.deployment_environment
        or os.environ.get("APP_ENV")
        or os.environ.get("OMOIOS_ENV")
        or "local"
    )
    attrs: dict[str, Any] = {
        "service.name": obs.service_name,
        "deployment.environment": deployment_environment,
    }
    if obs.release:
        attrs["service.version"] = obs.release
    return Resource.create(attrs)


def _otlp_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _init_tracer_provider(
    settings: BetterStackSettings, resource, *, sentry_attached: bool
):
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otlp_endpoint("traces"),
                headers=_otlp_headers(settings.source_token),
            )
        )
    )

    if sentry_attached:
        # Fan out to Sentry too so transactions land in BetterStack Errors.
        try:
            from sentry_sdk.integrations.opentelemetry import (
                SentryPropagator,
                SentrySpanProcessor,
            )
            from opentelemetry.propagate import set_global_textmap

            provider.add_span_processor(SentrySpanProcessor())
            set_global_textmap(SentryPropagator())
        except ImportError as exc:
            logger.debug("SentrySpanProcessor not available: %s", exc)

    trace.set_tracer_provider(provider)
    return provider


def _init_meter_provider(settings: BetterStackSettings, resource):
    from opentelemetry import metrics
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    exporter = OTLPMetricExporter(
        endpoint=settings.otlp_endpoint("metrics"),
        headers=_otlp_headers(settings.source_token),
    )
    reader = PeriodicExportingMetricReader(
        exporter, export_interval_millis=settings.metrics_export_interval_ms
    )
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return provider


def _init_logger_provider(settings: BetterStackSettings, resource):
    """OTel LoggerProvider with BetterStack as primary; the existing
    PostHog logs bridge is preserved by leaving its provider alone."""
    import logging

    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=settings.otlp_endpoint("logs"),
                headers=_otlp_headers(settings.source_token),
            )
        )
    )
    set_logger_provider(provider)

    # Bridge stdlib logging → OTel at INFO and above.
    handler = LoggingHandler(level=logging.INFO, logger_provider=provider)
    logging.getLogger().addHandler(handler)

    return provider


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------


async def _heartbeat_loop(token: str, period: int) -> None:
    url = f"{UPTIME_HEARTBEAT_URL}/{token}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                resp = await client.get(url)
                if resp.status_code >= 400:
                    logger.warning(
                        "BetterStack heartbeat non-2xx",
                        status=resp.status_code,
                        token_prefix=token[:6],
                    )
            except Exception as exc:  # noqa: BLE001 — telemetry never blocks
                logger.debug("BetterStack heartbeat ping failed: %s", exc)
            await asyncio.sleep(period)


def _start_heartbeat(settings: BetterStackSettings) -> Optional[asyncio.Task]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running event loop — caller must call ``start_heartbeat_now()``
        # from inside an async context (e.g. FastAPI startup).
        return None

    return fire_and_forget(
        _heartbeat_loop(settings.heartbeat_token, settings.heartbeat_period_seconds),
        name="betterstack-heartbeat",
    )


def start_heartbeat_now() -> Optional[asyncio.Task]:
    """Start the heartbeat from inside an async context.

    Useful from FastAPI ``startup`` hooks where there is now an event loop
    but :func:`init_betterstack` may have run earlier (e.g. at import).
    """
    if _handle is None or _handle.heartbeat_task is not None:
        return _handle.heartbeat_task if _handle else None
    settings = get_app_settings().betterstack
    if not settings.heartbeat_token:
        return None
    _handle.heartbeat_task = _start_heartbeat(settings)
    return _handle.heartbeat_task


def shutdown() -> None:
    """Public flush + cancel for atexit / serverless entrypoints."""
    if _handle is not None:
        _handle.shutdown()


__all__ = [
    "BetterStackHandle",
    "get_handle",
    "init_betterstack",
    "shutdown",
    "start_heartbeat_now",
]
