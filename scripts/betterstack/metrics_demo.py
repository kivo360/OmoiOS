#!/usr/bin/env python3
"""Send metrics to BetterStack — two protocols, same source.

BetterStack metrics ingestion is part of the Telemetry product (NOT the
Errors product), so you authenticate with the *source token*, not the
Sentry DSN.

Two supported transports:
    --mode http   POST {"name","gauge|counter|histogram","tags","dt"} to
                  https://<ingesting-host>/metrics  (simplest path, one POST)
    --mode otlp   OpenTelemetry SDK with OTLP/HTTP exporter to
                  https://in-otel.logs.betterstack.com/v1/metrics

Usage:
    # Simplest: direct HTTP, just a source token + host
    python -m scripts.betterstack.metrics_demo \\
        --token <source-token> --host <ingesting-host> --mode http

    # OTLP: requires `opentelemetry-exporter-otlp-proto-http`
    python -m scripts.betterstack.metrics_demo \\
        --token <source-token> --mode otlp

    # Or pull credentials from a source by ID via the API
    python -m scripts.betterstack.metrics_demo --source-id 2397698 --mode http
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import httpx

OTLP_METRICS_URL = "https://in-otel.logs.betterstack.com/v1/metrics"


# ---------------------------------------------------------------------------
# Mode 1: direct HTTP /metrics endpoint
# ---------------------------------------------------------------------------


def send_http_metrics(token: str, host: str) -> None:
    url = f"https://{host}/metrics"
    now = time.time()
    metrics: list[dict[str, Any]] = [
        # Gauge — point-in-time value
        {
            "name": "demo_queue_depth",
            "gauge": {"value": 42},
            "tags": {"queue": "default", "env": "smoke"},
            "dt": now,
        },
        # Counter — monotonic increment
        {
            "name": "demo_requests_total",
            "counter": {"value": 7},
            "tags": {"endpoint": "/api/v1/health", "method": "GET"},
            "dt": now,
        },
        # Histogram — sampled observations
        {
            "name": "demo_request_duration_ms",
            "histogram": {
                "values": [12.5, 18.1, 22.3, 7.9, 14.6],
            },
            "tags": {"endpoint": "/api/v1/health"},
            "dt": now,
        },
    ]

    print(f"[http] POST {url}")
    print(f"[http] payload: {json.dumps(metrics, indent=2)}")
    resp = httpx.post(
        url,
        json=metrics,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    print(f"[http] HTTP {resp.status_code}  body={resp.text!r}")
    if resp.status_code >= 300:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Mode 2: OTLP/HTTP via the OpenTelemetry SDK
# ---------------------------------------------------------------------------


def send_otlp_metrics(token: str, host: str | None = None) -> None:
    """Send via OTLP/HTTP. Use the source-specific ingesting host —
    the global `in-otel.logs.betterstack.com` endpoint authenticates
    differently (rejects per-source tokens with 401)."""
    try:
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry import metrics as otel_metrics
    except ImportError as e:
        print(
            f"OTLP metrics need opentelemetry SDK + http exporter: {e}\n"
            "Install: uv pip install opentelemetry-sdk "
            "opentelemetry-exporter-otlp-proto-http",
            file=sys.stderr,
        )
        raise SystemExit(1)

    resource = Resource.create(
        {
            "service.name": "betterstack-metrics-demo",
            "deployment.environment": "smoke",
        }
    )
    endpoint = f"https://{host}/v1/metrics" if host else OTLP_METRICS_URL
    exporter = OTLPMetricExporter(
        endpoint=endpoint,
        headers={"Authorization": f"Bearer {token}"},
    )
    print(f"[otlp] endpoint: {endpoint}")
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=2_000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    otel_metrics.set_meter_provider(provider)

    meter = otel_metrics.get_meter("betterstack-metrics-demo")
    counter = meter.create_counter(
        "demo_requests_total", description="demo counter from OTLP"
    )
    histogram = meter.create_histogram(
        "demo_request_duration_ms", unit="ms"
    )
    gauge = meter.create_gauge(
        "demo_queue_depth", description="queue depth gauge"
    )

    counter.add(7, {"endpoint": "/api/v1/health", "method": "GET"})
    for v in (12.5, 18.1, 22.3, 7.9, 14.6):
        histogram.record(v, {"endpoint": "/api/v1/health"})
    gauge.set(42, {"queue": "default", "env": "smoke"})

    print(f"[otlp] flushing ...")
    provider.force_flush(timeout_millis=10_000)
    provider.shutdown()
    print("[otlp] done — check BetterStack -> Telemetry source for the metrics")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--token", help="Source token (Telemetry source's token)")
    p.add_argument("--host", help="Ingesting host (only needed for --mode http)")
    p.add_argument(
        "--source-id",
        type=int,
        help="Pull --token and --host from this source via the management API.",
    )
    p.add_argument("--mode", choices=("http", "otlp"), default="http")
    args = p.parse_args()

    token = args.token
    host = args.host
    if args.source_id and (not token or not host):
        from .api import BetterStack

        with BetterStack() as bs:
            src = bs.get_source(args.source_id)
            attrs = src.get("attributes") or src
            token = token or attrs.get("token")
            host = host or attrs.get("ingesting_host")
            print(f"[setup] source {args.source_id}: token={token} host={host}")

    if not token:
        print("Need --token (or --source-id)", file=sys.stderr)
        return 1

    if args.mode == "http":
        if not host:
            print("--mode http needs --host (or --source-id)", file=sys.stderr)
            return 1
        send_http_metrics(token, host)
    else:
        send_otlp_metrics(token, host)

    return 0


if __name__ == "__main__":
    sys.exit(main())
