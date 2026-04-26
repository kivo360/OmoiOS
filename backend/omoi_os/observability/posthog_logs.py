"""PostHog Logs ingest via OpenTelemetry OTLP.

Wires Python's standard ``logging`` module through OpenTelemetry into
PostHog's Logs ingest endpoint (``<host>/i/v1/logs``), so application
logs surface alongside captured exceptions in the PostHog Error Tracking
UI for debugging context.

Off by default. Opt in per-environment by setting
``POSTHOG_LOGS_ENABLED=true``. Default level is ``WARNING`` because
DEBUG/INFO traffic at scale gets noisy and PostHog Logs is event-billable
— set ``POSTHOG_LOGS_LEVEL=DEBUG`` for verbose dev capture.

The OTel logs SDK comes in transitively via Pydantic Logfire; no new
dependency. If the SDK isn't importable for any reason (e.g. someone
strips Logfire in a slim image), this module degrades to a no-op
``init`` so boot never fails because of telemetry plumbing.

Usage (called once at boot, after ``init_posthog_observability()``):

    from omoi_os.observability.posthog_logs import init_posthog_logs
    init_posthog_logs()
"""

from __future__ import annotations

import atexit
import logging

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger

logger = get_logger(__name__)

# Module-level state mirrors observability.posthog so we can no-op a
# second call and so a shutdown handler can find the provider to flush.
_posthog_logs_initialized = False
_logger_provider = None  # type: Optional[object]


def _resolve_log_level(level: str) -> int:
    """Map a string log level (env-supplied) to a logging int level."""
    return getattr(logging, level.upper(), logging.WARNING)


def init_posthog_logs() -> bool:
    """Wire Python ``logging`` to PostHog's OTLP Logs endpoint.

    Returns True if the bridge is now active, False if disabled, not
    configured, or the OTel SDK couldn't be imported.
    """
    global _posthog_logs_initialized, _logger_provider

    if _posthog_logs_initialized:
        return _logger_provider is not None

    settings = get_app_settings().posthog
    if not settings.is_configured:
        logger.debug("PostHog Logs skipped (POSTHOG_API_KEY not set)")
        _posthog_logs_initialized = True
        return False

    if not settings.logs_enabled:
        logger.debug("PostHog Logs skipped (POSTHOG_LOGS_ENABLED=false)")
        _posthog_logs_initialized = True
        return False

    try:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import (
            OTLPLogExporter,
        )
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    except ImportError as e:
        logger.warning(f"PostHog Logs disabled — OTel SDK not importable: {e}")
        _posthog_logs_initialized = True
        return False

    # PostHog's Logs endpoint lives at /i/v1/logs (note the /i/ prefix —
    # different from /v1/logs which is the older general OTLP path).
    endpoint = f"{settings.host.rstrip('/')}/i/v1/logs"
    api_key = settings.api_key or ""

    try:
        resource = Resource.create({SERVICE_NAME: "omoios-api"})
        provider = LoggerProvider(resource=resource)
        exporter = OTLPLogExporter(
            endpoint=endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        set_logger_provider(provider)

        # Bridge stdlib logging → OTel. Use a level filter so we don't
        # ship the entire DEBUG firehose to PostHog.
        otel_handler = LoggingHandler(
            level=_resolve_log_level(settings.logs_level),
            logger_provider=provider,
        )
        logging.getLogger().addHandler(otel_handler)

        atexit.register(_safe_shutdown)
        _logger_provider = provider
        _posthog_logs_initialized = True

        logger.info(
            "PostHog Logs initialized",
            endpoint=endpoint,
            level=settings.logs_level,
        )
        return True

    except Exception as e:  # noqa: BLE001 — telemetry must never block boot
        logger.warning(f"PostHog Logs init failed: {e}")
        _posthog_logs_initialized = True
        return False


def _safe_shutdown() -> None:
    """atexit-safe flush of the logger provider."""
    if _logger_provider is None:
        return
    try:
        # LoggerProvider.shutdown() flushes buffered records.
        _logger_provider.shutdown()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"PostHog Logs shutdown raised: {e}")


def shutdown() -> None:
    """Public flush helper for serverless / Modal entrypoints."""
    _safe_shutdown()


__all__ = ["init_posthog_logs", "shutdown"]
