# Worker & Sandbox Monitoring System - TODO

**Created:** 2025-12-18  
**Status:** Planning phase  
**Related:** [Product Vision - Adaptive Monitoring Loop](../../product_vision.md#adaptive-monitoring-loop-architecture), [Monitoring Architecture](../../design/monitoring/monitoring_architecture.md)

## Overview

**Note:** This document focuses on **infrastructure/operational monitoring** (worker health, sandbox lifecycle, resource usage). For **task trajectory monitoring and steering** (Guardian/Conductor services), see the existing monitoring system documented in:
- `docs/product_vision.md` - Adaptive Monitoring Loop (Guardian agents, trajectory analysis, steering interventions)
- `docs/design/monitoring/monitoring_architecture.md` - Full monitoring architecture
- `backend/omoi_os/services/monitoring_loop.py` - Monitoring loop implementation
- `backend/omoi_os/services/intelligent_guardian.py` - Guardian service for trajectory analysis
- `backend/omoi_os/workers/monitoring_worker.py` - Monitoring worker process

### Existing Trajectory Monitoring System ✅

The system already has comprehensive **task trajectory monitoring**:
- **Guardian Service**: Monitors individual agent trajectories every 60 seconds, analyzes alignment with goals, provides steering interventions
- **Conductor Service**: System-wide coherence analysis, duplicate detection
- **Trajectory Context Builder**: Builds accumulated understanding from conversation history
- **Memory System**: Semantic memory for pattern storage and retrieval
- **Monitoring Loop**: Runs every 60 seconds, coordinates Guardian and Conductor

### What's Missing: Infrastructure Monitoring

This TODO focuses on **operational/infrastructure monitoring** that's needed for:
- **Orchestrator Workers** - Task dispatch and assignment health
- **Sandbox Workers** - Remote worker process health (running in Daytona sandboxes)
- **Sandboxes** - Resource usage, status, lifecycle (Daytona sandbox management)
- **Infrastructure Health** - Database connections, Redis, event delivery

## 🎯 Core Monitoring Requirements

### 1. Worker Health Monitoring

#### Orchestrator Worker
- [ ] **Heartbeat Tracking**
  - Track last heartbeat timestamp
  - Detect stale workers (no heartbeat in X minutes)
  - Alert on worker downtime
- [ ] **Task Processing Metrics**
  - Tasks assigned per minute/hour
  - Average time to assign task
  - Queue depth (pending tasks)
  - Failed task assignments
- [ ] **Database Connection Health**
  - Connection pool status
  - Query latency
  - Failed queries
- [ ] **Redis Connection Health**
  - Connection status
  - Message queue depth
  - Failed message publishes

#### Sandbox Worker (Remote)
- [ ] **Process Health**
  - Worker process status (running/stopped/crashed)
  - Last event timestamp
  - Heartbeat frequency
  - Memory/CPU usage (if accessible)
- [ ] **Task Execution Metrics**
  - Active tasks per worker
  - Average task duration
  - Task completion rate
  - Task failure rate
- [ ] **Event Reporting Health**
  - Events sent per minute
  - Failed event reports (502s, timeouts)
  - Event queue depth (if buffering)
- [ ] **SDK Health**
  - Claude SDK connection status
  - API call success rate
  - Token usage tracking
  - Rate limit status

### 2. Sandbox Lifecycle Monitoring

- [ ] **Sandbox Status Tracking**
  - Active sandboxes count
  - Sandbox age (time since creation)
  - Sandbox state (running/stopped/terminated)
  - Resource usage (memory, CPU, disk)
- [ ] **Sandbox Health**
  - Last event timestamp per sandbox
  - Sandbox heartbeat status
  - Detect "zombie" sandboxes (no events in X minutes)
- [ ] **Resource Monitoring**
  - Memory usage per sandbox
  - CPU usage per sandbox
  - Disk usage per sandbox
  - Network I/O (if available)
- [ ] **Sandbox Cleanup**
  - Automatic termination of idle sandboxes
  - Termination of sandboxes with no recent activity
  - Cleanup of completed/failed task sandboxes
  - Cost tracking (sandbox hours)

### 3. Task Monitoring (Operational)

**Note:** Task trajectory monitoring (alignment, steering, drift detection) is handled by the existing Guardian/Conductor system. This section focuses on operational metrics.

- [ ] **Task Status Dashboard**
  - Tasks by status (pending/assigned/running/completed/failed)
  - Task age (time in current status)
  - Stuck tasks detection (assigned but no progress) - *complements Guardian's stuck detection*
- [ ] **Task Performance Metrics**
  - Average task duration by type
  - Task completion rate
  - Task failure rate
  - Retry counts
- [ ] **Task Queue Analysis**
  - Queue depth over time
  - Average wait time
  - Priority distribution
  - User distribution

### 4. Event Monitoring

- [ ] **Event Volume Tracking**
  - Events per second/minute/hour
  - Events by type distribution
  - Event size distribution
  - Event processing latency
- [ ] **Event Storage Health**
  - Database write latency
  - Database storage growth
  - Event retention policies
  - Query performance
- [ ] **Event Delivery Health**
  - WebSocket delivery success rate
  - EventBus broadcast latency
  - Failed event deliveries

### 5. Error & Alerting

- [ ] **Error Tracking**
  - Error rate by type
  - Error trends over time
  - Critical error alerts
  - Error correlation (related errors)
- [ ] **Alerting System**
  - Worker downtime alerts
  - High error rate alerts
  - Resource exhaustion alerts
  - Task queue backlog alerts
  - Sandbox zombie detection alerts
- [ ] **Notification Channels**
  - Log aggregation (Sentry, Datadog, etc.)
  - Email/Slack notifications
  - Dashboard alerts
  - PagerDuty integration (for critical)

## 🏗️ Implementation Plan

### Phase 1: Basic Health Monitoring
1. **Worker Heartbeat Tracking**
   - Add heartbeat table/model
   - Update heartbeat on worker start/loop
   - Query for stale workers
   - Create monitoring endpoint

2. **Sandbox Status Dashboard**
   - Query active sandboxes
   - Calculate sandbox age
   - Track last event per sandbox
   - Create monitoring API endpoint

3. **Task Status Summary**
   - Count tasks by status
   - Identify stuck tasks
   - Create monitoring API endpoint

### Phase 2: Metrics Collection
1. **Metrics Storage**
   - Create metrics table/model
   - Store time-series metrics
   - Aggregate metrics (hourly/daily)

2. **Worker Metrics**
   - Track task assignment rate
   - Track event reporting rate
   - Track error rates

3. **Sandbox Metrics**
   - Track resource usage (if available from Daytona)
   - Track sandbox lifetime
   - Track task completion per sandbox

### Phase 3: Automated Cleanup
1. **Sandbox Pruning Worker**
   - Periodic job to identify idle sandboxes
   - Terminate sandboxes with no activity
   - Clean up completed task sandboxes
   - Update database status

2. **Task Cleanup**
   - Archive old completed tasks
   - Clean up failed tasks
   - Retry stuck tasks

### Phase 4: Alerting & Dashboards
1. **Alerting System**
   - Define alert rules
   - Implement alert triggers
   - Notification delivery

2. **Monitoring Dashboard**
   - Real-time metrics display
   - Historical trends
   - Health status indicators

## 📊 Proposed Database Schema

### Worker Heartbeats
```sql
CREATE TABLE worker_heartbeats (
    id UUID PRIMARY KEY,
    worker_type VARCHAR(50) NOT NULL,  -- 'orchestrator' | 'sandbox'
    worker_id VARCHAR(100) NOT NULL,
    last_heartbeat TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'healthy' | 'stale' | 'down'
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_worker_heartbeats_type_status ON worker_heartbeats(worker_type, status);
CREATE INDEX idx_worker_heartbeats_last_heartbeat ON worker_heartbeats(last_heartbeat);
```

### Monitoring Metrics
```sql
CREATE TABLE monitoring_metrics (
    id UUID PRIMARY KEY,
    metric_type VARCHAR(50) NOT NULL,  -- 'task_assigned' | 'event_count' | 'sandbox_active'
    metric_value NUMERIC NOT NULL,
    metric_unit VARCHAR(20),  -- 'count' | 'seconds' | 'bytes'
    tags JSONB,  -- {'worker_id': '...', 'sandbox_id': '...'}
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_monitoring_metrics_type_time ON monitoring_metrics(metric_type, recorded_at);
```

## 🔍 Monitoring Queries

### Find Stale Workers
```sql
SELECT * FROM worker_heartbeats
WHERE last_heartbeat < NOW() - INTERVAL '5 minutes'
  AND status = 'healthy';
```

### Active Sandboxes with No Recent Activity
```sql
SELECT s.sandbox_id, MAX(e.created_at) as last_event
FROM sandbox_events e
GROUP BY s.sandbox_id
HAVING MAX(e.created_at) < NOW() - INTERVAL '10 minutes';
```

### Task Status Summary
```sql
SELECT status, COUNT(*) as count
FROM tasks
GROUP BY status;
```

### Events per Hour
```sql
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    event_type,
    COUNT(*) as count
FROM sandbox_events
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour, event_type
ORDER BY hour DESC, count DESC;
```

## 🛠️ Tools & Services

### Recommended Stack
- **Metrics Storage**: PostgreSQL (time-series extension) or dedicated TSDB (InfluxDB, TimescaleDB)
- **Log Aggregation**: Sentry (already integrated), or Datadog/New Relic
- **Dashboards**: Grafana, or custom React dashboard
- **Alerting**: PagerDuty, Slack webhooks, or custom alerting service

### Integration Points
- **Sentry**: Already integrated for error tracking
- **EventBus**: Can be extended for metrics broadcasting
- **Database**: PostgreSQL for metrics storage
- **Redis**: For real-time metrics aggregation

## 📝 Notes

### Integration with Existing Monitoring

- **Trajectory Monitoring**: Guardian/Conductor system handles task alignment, steering, and drift detection
- **Infrastructure Monitoring**: This TODO focuses on operational health (workers, sandboxes, infrastructure)
- **Complementary Systems**: Both systems work together:
  - Guardian detects when agents drift/get stuck → Infrastructure monitoring detects if worker/sandbox is down
  - Trajectory monitoring analyzes agent behavior → Infrastructure monitoring tracks resource usage and health

### Implementation Strategy

- Start with basic health monitoring (Phase 1)
- Metrics can be added incrementally
- Consider using existing tools (Sentry) before building custom
- Dashboard can be built in frontend using existing API endpoints
- Automated cleanup should be conservative initially (long timeouts)
- Leverage existing monitoring worker (`monitoring_worker.py`) for infrastructure checks
