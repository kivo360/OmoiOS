# Phase 4 Parallel Implementation Plan

**Purpose**: Outline the parallel execution strategy, squad assignments, deliverables, and integration points for Phase 4 Monitoring & Observability implementation.
**Related**: docs/migrations/versions/005_monitoring_observability.py, docs/monitoring/metrics.md, docs/observability/setup.md, docs/alerting/rules.md, docs/watchdog/policies.md, docs/architecture/phase3_telemetry.md

---


**Created**: 2025-11-17  
**Status**: ACTIVE  
**Target**: Complete Phase 4 (Monitoring & Observability) in parallel execution

---

## Parallel Execution Strategy

### Timeline Overview

**Week 7 (Days 1-5):**
- Day 1-2: Monitor + Observability Squads start (parallel, independent)
- Day 3-5: Alerting + Watchdog Squads start (consume Monitor outputs)

**Week 8 (Days 1-5):**
- Day 1-3: All squads integrate and resolve cross-dependencies
- Day 4-5: Game-day validation (anomaly → alert → remediation loop)

---

## Squad Assignments

### 🔵 **Monitor Squad** (Can Start: Day 1)
**Dependencies:** Phase 3 telemetry (✅ already emitting)  
**Blocks:** Alerting Squad (needs metrics schema)

**Deliverables:**
1. ✅ Monitor models (MonitorAnomaly, Alert) — DONE
2. ✅ MonitorService with metrics collection — DONE
3. ✅ Telemetry contracts (`omoi_os/telemetry/`) — DONE
4. ⏳ Dashboard API routes (`/api/v1/monitor`)
5. ⏳ Anomaly detection refinement (rolling p95, trend analysis)
6. ⏳ Tests: `test_monitor.py` (metric collection, anomaly detection)

**Hand-offs:**
- Metrics schema → Alerting Squad (Day 2)
- Anomaly events → Watchdog Squad (Day 3)

---

### 🟢 **Observability Squad** (Can Start: Day 1, fully independent)
**Dependencies:** None  
**Blocks:** None (parallel stream)

**Deliverables:**
1. ⏳ OpenTelemetry integration (traces for service calls)
2. ⏳ Structured logging setup (JSON logs with correlation IDs)
3. ⏳ Performance profiling hooks
4. ⏳ Log aggregation pipeline
5. ⏳ Tests: `test_observability.py`

**Output:**
- Trace context propagation across services
- Structured logs ready for ELK/Loki
- Performance profiles for optimization

---

### 🟡 **Alerting Squad** (Can Start: Day 3, needs Monitor)
**Dependencies:** Monitor metrics schema (2-day delay)  
**Blocks:** Watchdog Squad (needs alert events)

**Deliverables:**
1. ⏳ AlertService with rule evaluation engine
2. ⏳ Alert rule definitions (YAML configs)
3. ⏳ Routing adapters (email/Slack/webhook mocks)
4. ⏳ Alert API routes (`/api/v1/alerts`)
5. ⏳ Tests: `test_alerting.py`, `test_alert_rules.py`

**Hand-offs:**
- Alert events (`monitor.alert.triggered`) → Watchdog Squad
- Alert payload schema → shared telemetry config

---

### 🔴 **Watchdog Squad** (Can Start: Day 3, needs Alerting + Registry)
**Dependencies:** Alert events (Day 3), Phase 3 Registry APIs (✅ exists)  
**Blocks:** None (end of chain)

**Deliverables:**
1. ⏳ WatchdogService with remediation policies
2. ⏳ Policy definitions (YAML: restart, failover, escalate)
3. ⏳ Registry integration (mark unhealthy, request replacement)
4. ⏳ Watchdog API routes (`/api/v1/watchdog`)
5. ⏳ Tests: `test_watchdog.py`, `test_remediation.py`

**Output:**
- Automated remediation (agent restart, task reassignment)
- Escalation to Guardian agent (Phase 5 hook)

---

## Shared Infrastructure (Already Created ✅)

### Telemetry Contracts
- ✅ `omoi_os/telemetry/__init__.py` — Metric/Alert DTOs, standard metrics catalog
- ✅ `omoi_os/models/monitor_anomaly.py` — MonitorAnomaly, Alert models
- ✅ `omoi_os/services/monitor.py` — MonitorService skeleton

### Event Types (To Be Published)
- `monitor.anomaly.detected` ✅
- `monitor.alert.triggered` ⏳
- `monitor.alert.acknowledged` ⏳
- `monitor.alert.resolved` ⏳
- `watchdog.remediation.started` ⏳
- `watchdog.remediation.completed` ⏳

---

## Migration Strategy

### Migration 005: Monitoring Tables
**File:** `migrations/versions/005_monitoring_observability.py`  
**Parent:** `004_collaboration_and_locking`

**Tables to Create:**
- `monitor_anomalies` (Monitor Squad)
- `alerts` (Alerting Squad)
- `alert_rules` (Alerting Squad)
- `watchdog_actions` (Watchdog Squad)
- `trace_spans` (Observability Squad, optional if using external APM)

---

## Integration Points

### Monitor → Alerting
**Contract:** Metrics API endpoint returns `List[MetricSample]`

```python
GET /api/v1/monitor/metrics?phase_id=PHASE_IMPLEMENTATION
Response: [
  {
    "metric_name": "tasks_queued_total",
    "value": 15,
    "labels": {"phase_id": "PHASE_IMPLEMENTATION"},
    "timestamp": "2025-11-17T01:00:00Z"
  }
]
```

**Integration Test:** Alerting can poll Monitor API and evaluate rules

---

### Alerting → Watchdog
**Contract:** Alert events on EventBus

```python
SystemEvent(
    event_type="monitor.alert.triggered",
    entity_type="alert",
    entity_id="alert-123",
    payload={
        "rule_id": "high_queue_depth",
        "severity": "warning",
        "metric_name": "tasks_queued_total",
        "current_value": 50,
        "threshold": 20,
        "labels": {"phase_id": "PHASE_IMPLEMENTATION"}
    }
)
```

**Integration Test:** Watchdog subscribes to alert events and triggers remediation

---

### Monitor/Alerting → Observability
**Contract:** Trace context in service calls

```python
# Every service method call includes trace context
with tracer.start_span("monitor.collect_metrics") as span:
    span.set_attribute("phase_id", phase_id)
    metrics = monitor.collect_task_metrics(phase_id)
```

**Integration Test:** End-to-end trace captured across service boundaries

---

## Test Strategy

### Unit Tests (Per Squad)
- Monitor: Metric collection accuracy, anomaly detection logic
- Alerting: Rule evaluation, severity escalation, deduplication
- Watchdog: Policy selection, remediation actions, idempotency
- Observability: Trace propagation, log formatting, correlation IDs

### Integration Tests (Cross-Squad)
- Monitor metrics → Alerting rules → Alert events ✅
- Alert events → Watchdog → Remediation action ✅
- All services → Observability → Complete trace ✅

### Game-Day Scenario
1. Inject high queue depth → Monitor detects anomaly
2. Anomaly triggers alert rule → Alerting fires event
3. Watchdog receives alert → Spawns additional worker
4. Observability captures full trace → Verify end-to-end

---

## Files to Create (30+ files)

### Monitor Squad (7 files)
- ✅ `omoi_os/models/monitor_anomaly.py`
- ✅ `omoi_os/services/monitor.py`
- ✅ `omoi_os/telemetry/__init__.py`
- ⏳ `omoi_os/api/routes/monitor.py`
- ⏳ `tests/test_monitor.py`
- ⏳ `tests/test_anomaly_detection.py`
- ⏳ `docs/monitoring/metrics.md`

### Observability Squad (8 files)
- ⏳ `omoi_os/observability/__init__.py`
- ⏳ `omoi_os/observability/tracing.py`
- ⏳ `omoi_os/observability/logging.py`
- ⏳ `omoi_os/observability/profiling.py`
- ⏳ `tests/test_tracing.py`
- ⏳ `tests/test_logging.py`
- ⏳ `tests/test_profiling.py`
- ⏳ `docs/observability/setup.md`

### Alerting Squad (10 files)
- ⏳ `omoi_os/models/alert_rule.py`
- ⏳ `omoi_os/services/alerting.py`
- ⏳ `omoi_os/services/routing.py` (email/Slack/webhook adapters)
- ⏳ `omoi_os/api/routes/alerts.py`
- ⏳ `omoi_os/config/alert_rules/*.yaml` (3 example rules)
- ⏳ `tests/test_alerting.py`
- ⏳ `tests/test_alert_rules.py`
- ⏳ `tests/test_routing.py`
- ⏳ `docs/alerting/rules.md`

### Watchdog Squad (8 files)
- ⏳ `omoi_os/models/watchdog_action.py`
- ⏳ `omoi_os/services/watchdog.py`
- ⏳ `omoi_os/config/watchdog_policies/*.yaml`
- ⏳ `omoi_os/api/routes/watchdog.py`
- ⏳ `tests/test_watchdog.py`
- ⏳ `tests/test_remediation.py`
- ⏳ `tests/test_watchdog_policies.py`
- ⏳ `docs/watchdog/policies.md`

### Shared (3 files)
- ⏳ `migrations/versions/005_monitoring_observability.py`
- ⏳ `tests/test_phase4_integration.py`
- ⏳ `scripts/game_day_scenario.py`

**Total:** ~35 files (~2,000 lines of code)

---

## Current Progress

✅ **Completed (This Session):**
- Telemetry contracts and metric definitions
- Monitor models (MonitorAnomaly, Alert)
- MonitorService skeleton with metrics collection
- Anomaly detection algorithm (rolling statistics)

⏳ **Next Steps:**
1. Complete Monitor API routes and tests
2. Start Observability tracing integration (parallel)
3. Implement Alerting service (after Monitor metrics schema solidified)
4. Implement Watchdog service (after Alerting events schema solidified)

---

## Coordination Checkpoints

### Day 2 Sync
- Monitor Squad: Publish metrics API contract
- Observability Squad: Share trace context propagation pattern
- Review: Does alerting squad have what they need?

### Day 4 Sync
- Alerting Squad: Publish alert event schema
- Monitor + Observability: Integration test results
- Review: Does watchdog squad have what they need?

### Day 6 Sync
- All Squads: Cross-integration test results
- Prepare game-day scenario script
- Review: Any blocking issues?

### Day 8 Sync
- Game-day validation complete
- Documentation review
- Phase 4 sign-off

---

## Risk Mitigation

### Risks
1. **Schema Mismatch:** Monitor/Alerting/Watchdog use incompatible formats
2. **Event Lag:** EventBus latency causes delayed remediation
3. **Test Interference:** Parallel test runs conflict on shared DB
4. **Merge Conflicts:** Multiple agents modify same files

### Mitigations
1. ✅ Shared `telemetry/` module with DTOs (already created)
2. Use contract tests before integration
3. Separate test databases per squad (different DB names)
4. Coordinate on file ownership (Monitor owns monitor.py, etc.)

---

## Success Criteria

### Phase 4 Complete When:
- [ ] All 4 squad deliverables implemented
- [ ] 40+ new tests passing (10 per squad)
- [ ] Zero linting errors
- [ ] Migration 005 applied successfully
- [ ] Game-day scenario passes end-to-end
- [ ] Documentation complete (4 squad docs + integration guide)

**Expected Outcome:**
- Real-time monitoring dashboard
- Automated alerting with routing
- Self-healing via watchdog remediation
- Full observability with traces/logs/metrics

---

**Ready to proceed:** ✅ YES  
**Blocking issues:** ✅ NONE  
**Go/No-Go Decision:** ✅ GO FOR PARALLEL EXECUTION

