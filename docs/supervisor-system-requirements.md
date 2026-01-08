# Supervisor System Requirements

## Overview

The Supervisor System is a long-running process management layer designed to ensure continuous operation of the OmoiOS multi-agent orchestration platform. It monitors, manages, and recovers worker processes and monitoring loops to enable uninterrupted operation over extended periods (days, weeks, or longer).

## Problem Statement

The current OmoiOS system has robust internal monitoring and health checking, but lacks a top-level supervision mechanism to ensure long-running stability:

1. **Worker Process Vulnerability**: If a worker process crashes, it must be manually restarted
2. **Monitoring Loop Single Point of Failure**: The MonitoringLoop service can crash, halting all trajectory analysis and system coherence monitoring
3. **No Automatic Recovery**: Failed processes require manual intervention
4. **Limited Long-Running Support**: No built-in mechanisms for handling resource leaks, memory growth, or process degradation over time
5. **No Graceful Shutdown Coordination**: Processes don't coordinate shutdown during system stops

## Goals

Enable OmoiOS to run continuously for extended periods with:

- **Automatic Process Recovery**: Restart failed workers and monitoring loops automatically
- **Health-Based Supervision**: Monitor supervised processes and intervene before complete failure
- **Resource Management**: Detect and handle resource exhaustion or degradation
- **Graceful Lifecycle Management**: Coordinate startup, shutdown, and restart of all components
- **Observability**: Provide comprehensive visibility into supervisor and supervised process health

## Existing Architecture Analysis

### Current Long-Running Patterns

The codebase already implements several patterns for long-running processes:

#### 1. Worker Pattern (`/backend/omoi_os/worker.py`)
- **HeartbeatManager**: Adaptive heartbeat with sequence tracking (30s IDLE, 15s RUNNING, 10s HIGH_LOAD)
- **TimeoutManager**: Background task timeout monitoring with 10s intervals
- **Retry with Exponential Backoff**: 1s, 2s, 4s, 8s with ±25% jitter
- **ThreadPoolExecutor**: Concurrent task execution with configurable max_workers
- **Graceful Shutdown**: KeyboardInterrupt handling with cleanup

#### 2. MonitoringLoop Pattern (`/backend/omoi_os/services/monitoring_loop.py`)
- **Async Background Loops**: Separate tasks for Guardian (60s), Conductor (300s), Health Check (30s)
- **Error Recovery**: Continue running after exceptions with brief pauses (5-10s)
- **Graceful Shutdown**: Task cancellation with exception gathering
- **Cycle Tracking**: Comprehensive metrics and state management

#### 3. Health Monitoring (`/backend/omoi_os/services/agent_health.py`)
- **Heartbeat Timeout Detection**: 90s default timeout for stale agents
- **Automatic Status Updates**: Stale agents marked automatically
- **Comprehensive Statistics**: Per-agent and system-wide health metrics

### Gaps Addressed by Supervisor

| Gap | Current State | Supervisor Solution |
|-----|---------------|---------------------|
| Process Restart | Manual restart required | Automatic restart on failure |
| Resource Leaks | No detection | Memory/CPU monitoring with restart thresholds |
| Monitoring Loop Failure | System stops | Automatic monitoring loop restart |
| Coordination | Independent processes | Unified lifecycle management |
| Degradation Detection | No proactive intervention | Health-based preventive restarts |

## Requirements

### Functional Requirements

#### REQ-SUP-001: Process Supervision
**WHEN** a supervised process (worker or monitoring loop) is started,
**THE SYSTEM SHALL** register the process with the supervisor and track its PID, start time, and health status.

**Acceptance Criteria**:
- Supervisor maintains registry of all supervised processes
- Each process has unique ID, PID, start timestamp, and current status
- Registration occurs within 1 second of process start
- Process metadata is persisted to database for recovery

#### REQ-SUP-002: Health Monitoring
**WHEN** a supervised process is running,
**THE SYSTEM SHALL** monitor process health via heartbeat detection and system resource metrics.

**Acceptance Criteria**:
- Heartbeats received within expected intervals (based on process type)
- CPU and memory usage tracked per process
- Health status updated in real-time
- Health metrics persisted for historical analysis
- Alerts generated for health degradation

#### REQ-SUP-003: Automatic Restart
**WHEN** a supervised process fails (crashes, hangs, or violates health thresholds),
**THE SYSTEM SHALL** automatically restart the process within configurable time limits.

**Acceptance Criteria**:
- Process crash detected within 5 seconds
- Restart attempted within 10 seconds of detection
- Maximum restart count enforced (default: 5 per hour)
- Exponential backoff between restart attempts (5s, 10s, 20s, 40s, 80s)
- Persistent failure triggers alert and manual intervention requirement
- Restart attempts logged with timestamps and reasons

#### REQ-SUP-004: Resource Threshold Enforcement
**WHEN** a supervised process exceeds resource limits (CPU, memory, file descriptors),
**THE SYSTEM SHALL** gracefully restart the process before it causes system instability.

**Acceptance Criteria**:
- Configurable memory threshold (default: 2GB)
- Configurable CPU threshold (default: 80% sustained for 5 minutes)
- Configurable file descriptor threshold (default: 80% of system limit)
- Graceful shutdown initiated before forceful termination
- Resource usage tracked and logged

#### REQ-SUP-005: Monitoring Loop Supervision
**WHEN** the MonitoringLoop service crashes or becomes unresponsive,
**THE SYSTEM SHALL** detect the failure and restart the monitoring loop with state preservation.

**Acceptance Criteria**:
- Monitoring loop heartbeat monitored (expected: 30s interval)
- Crash detected within 15 seconds
- State (cycle ID, last run times) restored after restart
- No more than 10 seconds of monitoring interruption
- Guardian and Conductor analyses resume automatically

#### REQ-SUP-006: Worker Process Supervision
**WHEN** a worker process crashes or becomes unresponsive,
**THE SYSTEM SHALL** detect the failure and restart the worker with task state preservation.

**Acceptance Criteria**:
- Worker heartbeat monitored (adaptive: 10-30s based on status)
- Crash detected within 45 seconds (1.5x heartbeat timeout)
- In-progress task status recovered and marked for retry
- Agent capacity preserved across restart
- Worker re-registers with existing agent ID or new ID if corrupted

#### REQ-SUP-007: Graceful Shutdown Coordination
**WHEN** a shutdown signal is received (SIGTERM, SIGINT),
**THE SYSTEM SHALL** coordinate graceful shutdown of all supervised processes in dependency order.

**Acceptance Criteria**:
- Shutdown signal propagated to all processes
- Monitoring loop stops first (allows final analysis)
- Workers stop after completing current tasks (with timeout)
- Processes force-terminated if graceful shutdown exceeds timeout (default: 30s)
- Shutdown status logged and reported
- Cleanup completed (resources released, connections closed)

#### REQ-SUP-008: Supervisor Self-Monitoring
**WHEN** the supervisor is running,
**THE SYSTEM SHALL** monitor its own health and report status via heartbeat and metrics.

**Acceptance Criteria**:
- Supervisor heartbeat published every 10 seconds
- Self-health checks (memory, CPU, deadlock detection)
- Supervised process count and status reported
- Restart statistics (success/failure rates) reported
- Health endpoint available for external monitoring

#### REQ-SUP-009: Configuration Management
**WHEN** the supervisor starts or receives SIGHUP,
**THE SYSTEM SHALL** load and apply configuration from file and environment variables.

**Acceptance Criteria**:
- Configuration file path configurable via environment
- Hot reload on SIGHUP without restart
- Configuration validation before application
- Invalid configuration rejected with error message
- Default configuration provided for all settings

#### REQ-SUP-010: Logging and Event Emission
**WHEN** significant supervisor events occur (start, stop, restart, health changes),
**THE SYSTEM SHALL** log the event and publish to the event bus for real-time monitoring.

**Acceptance Criteria**:
- Structured logging with severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- All restart attempts logged with full context
- Events published to Redis event bus
- Log rotation configured (default: 100MB per file, 10 files retained)
- Critical events trigger immediate alerts

### Non-Functional Requirements

#### REQ-SUP-NFR-001: Availability
The supervisor shall achieve 99.9% uptime, excluding planned maintenance.

#### REQ-SUP-NFR-002: Performance
- Health checks shall complete within 100ms per process
- Restart decisions shall be made within 1 second of failure detection
- Supervisor overhead shall not exceed 5% CPU and 50MB memory

#### REQ-SUP-NFR-003: Scalability
The supervisor shall support up to 50 concurrent worker processes and 5 monitoring loops.

#### REQ-SUP-NFR-004: Reliability
- False positive restart rate shall be less than 0.1%
- False negative (missed failure) rate shall be less than 0.01%
- Mean time to recovery (MTTR) shall be under 30 seconds

#### REQ-SUP-NFR-005: Security
- Process communication shall use authenticated channels
- Configuration shall support credential management
- Logs shall sanitize sensitive information
- Supervisor shall run with minimum required privileges

#### REQ-SUP-NFR-006: Maintainability
- Code shall follow existing OmoiOS patterns (async loops, heartbeat, event bus)
- Supervisor shall be testable in isolation (mock process management)
- Configuration shall be documented with examples
- Health metrics shall be exportable for external monitoring

### Data Model

#### SupervisedProcess
```python
class SupervisedProcess:
    id: UUID
    process_type: Enum[str]  # "worker", "monitoring_loop", "supervisor"
    pid: Optional[int]
    command: List[str]
    args: Dict[str, Any]
    status: Enum[str]  # "starting", "running", "stopping", "stopped", "failed", "crashed"
    start_time: datetime
    last_heartbeat: Optional[datetime]
    restart_count: int
    last_restart_time: Optional[datetime]
    health_status: Enum[str]  # "healthy", "degraded", "unhealthy"
    resource_metrics: Dict[str, Any]  # cpu_percent, memory_mb, fd_count
    config: Dict[str, Any]  # thresholds, intervals
```

#### SupervisorEvent
```python
class SupervisorEvent:
    id: UUID
    event_type: str  # "process_started", "process_stopped", "process_restarted", "health_changed", "shutdown_initiated"
    process_id: UUID
    process_type: str
    timestamp: datetime
    details: Dict[str, Any]
    severity: str  # "info", "warning", "error", "critical"
```

#### SupervisorConfig
```python
class SupervisorConfig:
    # General
    heartbeat_interval: int = 10  # seconds
    health_check_interval: int = 5  # seconds
    shutdown_timeout: int = 30  # seconds

    # Restart policy
    max_restarts_per_hour: int = 5
    restart_backoff_base: int = 5  # seconds
    restart_backoff_max: int = 80  # seconds

    # Resource thresholds
    memory_threshold_mb: int = 2048
    cpu_threshold_percent: int = 80
    cpu_duration_seconds: int = 300  # 5 minutes
    fd_threshold_percent: int = 80

    # Process-specific configs
    worker_heartbeat_timeout: int = 45  # seconds
    monitoring_loop_heartbeat_timeout: int = 45  # seconds
```

## Architecture Design

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         SupervisorSystem                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  ProcessManager │  │  HealthMonitor  │  │  LifecycleMgr   │  │
│  │                 │  │                 │  │                 │  │
│  │ - start()       │  │ - check()       │  │ - shutdown()    │  │
│  │ - stop()        │  │ - get_metrics() │  │ - restart()     │  │
│  │ - restart()     │  │ - evaluate()    │  │ - coordinate()  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ ConfigManager   │  │  EventBusPub    │  │  StateStore     │  │
│  │                 │  │                 │  │                 │  │
│  │ - load()        │  │ - publish()     │  │ - save()        │  │
│  │ - reload()      │  │ - emit()        │  │ - restore()     │  │
│  │ - validate()    │  │ - alert()       │  │ - query()       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Supervised Processes                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Worker Process 1│  │ Worker Process 2│  │ MonitoringLoop  │  │
│  │                 │  │                 │  │                 │  │
│  │ - HeartbeatManager│ - HeartbeatManager│ - Async Loops    │  │
│  │ - ThreadPool    │  │ - ThreadPool    │  │ - Guardian      │  │
│  │ - TimeoutMgr    │  │ - TimeoutMgr    │  │ - Conductor     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. ProcessManager
- **Responsibility**: Start, stop, and restart supervised processes
- **Implementation**: Uses `subprocess.Popen` for process management
- **Key Methods**:
  - `start_process(config)`: Launch new process with PID tracking
  - `stop_process(pid, timeout)`: Graceful then forceful termination
  - `restart_process(process_id)`: Stop and start with state preservation

#### 2. HealthMonitor
- **Responsibility**: Monitor process health and detect failures
- **Implementation**: Async loop checking heartbeats and resources
- **Key Methods**:
  - `check_process_health(process_id)`: Evaluate health status
  - `get_resource_metrics(pid)`: Get CPU, memory, FD count
  - `evaluate_health(metrics)`: Determine if restart needed

#### 3. LifecycleManager
- **Responsibility**: Coordinate startup and shutdown of all processes
- **Implementation**: Dependency graph traversal with parallel execution
- **Key Methods**:
  - `startup_all()`: Start processes in dependency order
  - `shutdown_all()`: Graceful shutdown coordination
  - `graceful_restart(process_id)`: Restart without data loss

#### 4. ConfigManager
- **Responsibility**: Load and validate configuration
- **Implementation**: YAML file + environment variable override
- **Key Methods**:
  - `load_config(path)`: Load and parse configuration
  - `reload_config()`: Hot reload on SIGHUP
  - `validate_config(config)`: Schema validation

#### 5. EventBusPublisher
- **Responsibility**: Publish supervisor events to Redis
- **Implementation**: Wrapper around existing EventBusService
- **Key Methods**:
  - `publish_event(event)`: Publish structured event
  - `emit_alert(severity, message)`: Send alert notification

#### 6. StateStore
- **Responsibility**: Persist supervisor state for recovery
- **Implementation**: Database-backed state persistence
- **Key Methods**:
  - `save_process_state(process)`: Persist process metadata
  - `restore_process_state()`: Load state after supervisor restart
  - `query_process_history()`: Get restart history

### Integration with Existing Systems

#### Heartbeat Integration
- Supervisor extends `HeartbeatProtocolService` for process heartbeat tracking
- Uses existing heartbeat timeout detection logic
- Publishes heartbeat events to event bus

#### Event Bus Integration
- Supervisor publishes to existing Redis event bus
- Consumes monitoring events for decision-making
- Frontend receives real-time supervisor status via WebSocket

#### Database Integration
- New tables: `supervised_processes`, `supervisor_events`, `supervisor_config`
- Extends existing `Agent` model with supervisor reference
- Uses existing `DatabaseService` for persistence

#### API Integration
- New endpoints: `/api/supervisor/status`, `/api/supervisor/processes`, `/api/supervisor/events`
- Extends existing monitor API with supervisor metrics
- WebSocket events for real-time updates

## Implementation Plan

### Phase 1: Core Supervisor (Week 1)
1. Create `SupervisorSystem` class with basic structure
2. Implement `ProcessManager` with start/stop/restart
3. Implement `HealthMonitor` with heartbeat checking
4. Create database models for supervisor state
5. Add supervisor configuration file and loading

### Phase 2: Worker Supervision (Week 2)
1. Integrate worker process supervision
2. Implement worker restart with state recovery
3. Add worker-specific health monitoring
4. Test worker crash and restart scenarios
5. Add worker resource threshold enforcement

### Phase 3: Monitoring Loop Supervision (Week 2)
1. Integrate MonitoringLoop supervision
2. Implement monitoring loop restart with state preservation
3. Add monitoring loop-specific health monitoring
4. Test monitoring loop crash and restart
5. Add monitoring loop resource monitoring

### Phase 4: Lifecycle Management (Week 3)
1. Implement graceful shutdown coordination
2. Add dependency-based startup ordering
3. Implement supervisor self-monitoring
4. Add configuration hot-reload
5. Test full system lifecycle

### Phase 5: Observability (Week 3)
1. Add comprehensive logging
2. Implement event publishing to event bus
3. Create supervisor status API endpoints
4. Add frontend supervisor dashboard
5. Implement alerting for critical events

### Phase 6: Testing and Documentation (Week 4)
1. Write unit tests for all components
2. Write integration tests for supervisor scenarios
3. Test long-running stability (48+ hour run)
4. Document configuration options
5. Write deployment and operations guide

## Success Metrics

- **Mean Time To Recovery (MTTR)**: < 30 seconds for process failures
- **Supervisor Uptime**: > 99.9% over 30-day period
- **False Positive Rate**: < 0.1% (unnecessary restarts)
- **System Availability**: > 99.5% with supervisor active
- **Resource Overhead**: < 5% CPU, < 50MB memory
- **Configuration Time**: < 5 minutes to deploy and configure

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Supervisor becomes single point of failure | High | Low | Implement supervisor watchdog, add passive supervisor |
| Restart loops cause instability | High | Medium | Exponential backoff, max restart limits, manual intervention |
| Resource monitoring overhead affects performance | Medium | Low | Efficient metric collection, configurable check intervals |
| State corruption after crashes | High | Low | Regular state snapshots, validation on load |
| Difficulty debugging supervisor issues | Medium | Medium | Comprehensive logging, state export, diagnostic mode |

## Open Questions

1. **Supervisor Deployment**: Should supervisor run as separate systemd service or Docker container?
2. **Multi-Instance Support**: Should we support active-passive supervisor for high availability?
3. **Worker Scaling**: Should supervisor dynamically adjust worker count based on load?
4. **Remote Supervision**: Should supervisor support distributed workers across multiple hosts?
5. **Checkpointing**: Should we implement task checkpointing for faster recovery?

## Appendix: Related Code Locations

### Existing Implementation References

- **Worker**: `/workspace/backend/omoi_os/worker.py:348-472` - Main worker loop
- **HeartbeatManager**: `/workspace/backend/omoi_os/worker.py:26-203` - Heartbeat implementation
- **TimeoutManager**: `/workspace/backend/omoi_os/worker.py:205-346` - Timeout monitoring
- **MonitoringLoop**: `/workspace/backend/omoi_os/services/monitoring_loop.py:58-602` - Monitoring orchestration
- **AgentHealthService**: `/workspace/backend/omoi_os/services/agent_health.py` - Agent health tracking
- **EventBus**: `/workspace/backend/omoi_os/services/event_bus.py` - Event pub/sub
- **Database**: `/workspace/backend/omoi_os/services/database.py` - Database service

### Database Schema Reference

- **Agent Table**: `/workspace/backend/omoi_os/models/agent.py` - Existing agent model
- **Task Table**: `/workspace/backend/omoi_os/models/task.py` - Existing task model
- **HeartbeatMessage**: `/workspace/backend/omoi_os/models/heartbeat_message.py` - Heartbeat model

---

**Document Version**: 1.0
**Last Updated**: 2026-01-08
**Status**: Requirements Draft - Pending Review
