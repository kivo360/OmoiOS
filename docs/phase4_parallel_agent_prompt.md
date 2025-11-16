# Phase 4 Parallel Agent Prompt – Monitoring & Observability (Weeks 7-8)

Use this prompt to launch **four coordinated agents** focused on monitoring, alerting, watchdog automation, and observability instrumentation. Copy the relevant role block when spawning each agent. Follow TDD, keep feature flags handy, and ensure telemetry contracts stay aligned with Phase 3 outputs.

---

## Shared Context & Readiness Checklist
- Phase 3 deliverables (registry, collaboration events, scheduler telemetry) are merged and emitting data into Redis/Postgres/EventBus.
- OpenTelemetry collectors and log sinks are provisioned via `docker-compose` or cloud equivalents.
- `telemetry-config` package exists (or is stubbed) to centralize exporters, metrics definitions, and log formats.
- Access to monitoring stack (Prometheus/Grafana or similar) for local validation.
- Run `uv run pytest` and `uv run ruff check` before handing off; add Playwright/E2E tests if dashboards have UI.

## Global Deliverables
1. Monitor agent/service aggregating metrics + exposing dashboard APIs.
2. Health metrics + alerting pipeline with routing to email/webhook/Slack stubs.
3. Watchdog agent automating remediation using registry APIs and alert feeds.
4. Observability integration (OpenTelemetry traces, structured logging, performance profiling).
5. Game-day validation proving anomaly detection → alerting → watchdog remediation loop.

---

## Agent Role 1 – **Monitor Squad (MetricsAgent + DashboardAgent)**
**Scope**
- Implement Monitor service (`omoi_os/services/monitor_agent.py`) that ingests data from scheduler, registry, event bus, and workers.
- Define metrics schema (task latency, queue depth, lock wait time, agent availability) using Prometheus/OpenTelemetry instruments.
- Build dashboard API endpoints under `omoi_os/api/routes/monitor.py` (list metrics, top offenders, anomaly summaries).
- Provide baseline anomaly detection (e.g., rolling p95 deviations) stored in `monitor_anomalies` table.

**Dependencies**
- Consumes registry capability data, scheduler telemetry, and collaboration events.
- Publishes metrics schema consumed by Alerting + Watchdog squads; share via `telemetry-config`.

**Tests**
- `tests/test_monitor_agent.py`: metric aggregation, anomaly detection accuracy, API responses.
- Contract tests ensuring monitor output schema matches Alerting expectations.

**Hand-offs**
- Deliver metrics catalog (name, type, labels) as markdown/JSON in `docs/monitoring/metrics.md`.
- Provide async client for reading metrics (used by Alerting Squad).

---

## Agent Role 2 – **Alerting Squad (SignalAgent + RouterAgent)**
**Scope**
- Build HealthMetricsService (`omoi_os/services/alerting.py`) that subscribes to Monitor metrics and evaluates alert rules.
- Implement alert definitions (YAML/JSON) with severity, thresholds, routing preferences.
- Create routing adapters for email/webhook/Slack (mock implementations fine for local dev).
- Add FastAPI endpoints under `omoi_os/api/routes/alerts.py` to list active alerts, acknowledge, resolve, and manage rules.

**Dependencies**
- Requires Monitor squad’s metrics schema + API client.
- Needs registry info (for mapping agent IDs to owners) provided by Phase 3.

**Tests**
- `tests/test_alerting.py`: threshold breaches, deduplication, severity escalation, routing logic (mock transport).
- `tests/test_alert_rules.py`: CRUD + validation for rule definitions.

**Hand-offs**
- Emit alert events (`monitor.alert.triggered`) on EventBus for Watchdog squad.
- Document alert payload schema in `telemetry-config`.

---

## Agent Role 3 – **Watchdog Squad (GuardianPrepAgent + AutoRecoveryAgent)**
**Scope**
- Implement Watchdog service (`omoi_os/services/watchdog.py`) that listens to alert events + heartbeat streams.
- Define remediation policies (restart worker, recycle agent token, escalate to Guardian agent once Phase 5 exists).
- Integrate with registry APIs to mark agents unhealthy, trigger failover, or request replacement.
- Provide configuration for escalation chains (YAML + environment overrides).
- Add API endpoints under `omoi_os/api/routes/watchdog.py` for manual actions and policy inspection.

**Dependencies**
- Consumes alert events from Role 2 and registry interfaces from Phase 3.
- Needs monitor metrics for context when deciding remediation.

**Tests**
- `tests/test_watchdog.py`: simulate heartbeat loss, verify remediation actions, idempotency.
- `tests/test_watchdog_policies.py`: ensure escalation timers + thresholds behave as expected.

**Hand-offs**
- Publish remediation audit logs to Observability squad for ingestion.
- Provide `watchdog.actions` metric spec for Monitor dashboards.

---

## Agent Role 4 – **Observability Squad (TracingAgent + LoggingAgent)**
**Scope**
- Instrument API, worker, scheduler, monitor, and watchdog services with OpenTelemetry traces (FastAPI middleware, Celery/async tasks if applicable).
- Standardize structured logging (JSON logs with ticket/task/agent IDs) and ship to aggregator (e.g., stdout → Loki/Elastic).
- Implement distributed tracing exporters (OTLP) and configure sampling.
- Add performance profiling hooks (e.g., `pyinstrument` snapshots) triggered via admin endpoint or CI job.
- Build developer docs explaining how to view traces/logs locally.

**Dependencies**
- Requires metrics + alert schemas to correlate logs/traces.
- Needs knowledge of scheduler + registry IDs for trace attributes (from Phase 3).

**Tests**
- `tests/test_observability.py`: ensure traces emitted for key endpoints, log schema validation, profiling trigger tests (mock actual profiler).
- Optional integration tests verifying trace IDs propagate across API → worker → monitor.

**Hand-offs**
- Provide instrumentation guidelines to all squads.
- Feed aggregated traces/logs back to Monitor dashboards (closing the loop).

---

## Coordination & Timeline
- **Week 7 / Days 1-2**: Monitor + Observability squads focus on metrics schema + tracing middleware; share stubs immediately.
- **Week 7 / Days 3-5**: Alerting builds atop Monitor outputs; Watchdog begins on mock alerts until real pipeline is ready.
- **Week 8 / Days 1-2**: Watchdog integrates with live alerts + registry; Observability finishes log aggregation + profiling harness.
- **Week 8 / Days 3-5**: Run joint “game day” script to trigger anomalies → alerts → watchdog actions while Observability captures traces/logs.

## Communication Rituals
- Shared `docs/monitoring/README.md` capturing schemas, alert rules, remediation policies.
- Daily async status updates; flag contract changes (metrics, alert payloads) immediately.
- Use shared fixtures under `tests/fixtures/phase4/` for metrics, alerts, remediation events.
- Maintain feature flags to avoid blocking merges; connect them once all squads sign off.

## Definition of Done (Phase 4)
- Metrics, alerts, watchdog, and observability pipelines operational end-to-end.
- Automated remediation proven via integration/game-day tests.
- Documentation + runbooks updated, including troubleshooting steps.
- Telemetry data accessible via dashboards/log viewers.
- No regressions (`uv run pytest`, `uv run ruff check`, CI profiling job) and Phase 3 functionality remains stable.
