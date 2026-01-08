# Supervisor System Architecture

## System Context

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              External Environment                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌─────────────────────────────┐     ┌─────────────────────────────────────────┐
│   Operators / Admins        │     │         OmoiOS Platform                 │
│   - Deploy supervisor       │     │                                         │
│   - Monitor health          │     │  ┌───────────────────────────────────┐ │
│   - Configure behavior      │     │  │       Supervisor System           │ │
│   - Respond to alerts       │     │  │                                   │ │
└─────────────────────────────┘     │  │  ┌─────────────────────────────┐  │ │
                                     │  │  │    Process Lifecycle        │  │ │
                                     │  │  │    - Start/Stop/Restart     │  │ │
                                     │  │  │    - Dependency Management  │  │ │
                                     │  │  └─────────────────────────────┘  │ │
                                     │  │                                   │ │
┌─────────────────────────────┐     │  │  ┌─────────────────────────────┐  │ │
│   Frontend Dashboard        │     │  │  │    Health Monitoring         │  │ │
│   - Supervisor status       │─────┼──┼──│    - Heartbeat Detection     │  │ │
│   - Process health          │     │  │  │    - Resource Metrics        │  │ │
│   - Event timeline          │     │  │  │    - Threshold Evaluation    │  │ │
└─────────────────────────────┘     │  │  └─────────────────────────────┘  │ │
                                     │  │                                   │ │
                                     │  │  ┌─────────────────────────────┐  │ │
                                     │  │  │    State Management         │  │ │
                                     │  │  │    - Process Registry       │  │ │
                                     │  │  │    - Event History          │  │ │
                                     │  │  │    - Recovery State         │  │ │
                                     │  │  └─────────────────────────────┘  │ │
                                     │  │                                   │ │
                                     │  └───────────────────────────────────┘ │
                                     │                                         │
                                     │  ┌───────────────────────────────────┐ │
                                     │  │       Supervised Processes        │ │
                                     │  │                                   │ │
                                     │  │  ┌─────┐  ┌─────┐  ┌───────────┐ │ │
                                     │  │  │Wkr 1│  │Wkr 2│  │Monitoring │ │ │
                                     │  │  │     │  │     │  │   Loop    │ │ │
                                     │  │  └─────┘  └─────┘  └───────────┘ │ │
                                     │  │                                   │ │
                                     │  └───────────────────────────────────┘ │
                                     │                                         │
                                     └─────────────────────────────────────────┘
```

## Component Decomposition

### Supervisor System Core

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               SupervisorSystem                                  │
│                                                                                 │
│  Responsibilities:                                                              │
│  - Process lifecycle coordination                                              │
│  - Health monitoring and recovery                                              │
│  - Configuration management                                                     │
│  - Event emission and logging                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│ ProcessManager   │        │ HealthMonitor    │        │ LifecycleManager │
├──────────────────┤        ├──────────────────┤        ├──────────────────┤
│                  │        │                  │        │                  │
│ • start()        │        │ • check()        │        │ • startup_all()  │
│ • stop()         │        │ • get_metrics()  │        │ • shutdown_all() │
│ • restart()      │        │ • evaluate()     │        │ • coordinate()   │
│ • get_status()   │        │ • alert()        │        │ • graceful()     │
└──────────────────┘        └──────────────────┘        └──────────────────┘
        │                              │                              │
        └──────────────────────────────┼──────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  ConfigManager   │        │  EventBusPub     │        │   StateStore     │
├──────────────────┤        ├──────────────────┤        ├──────────────────┤
│                  │        │                  │        │                  │
│ • load()         │        │ • publish()      │        │ • save()         │
│ • reload()       │        │ • emit()         │        │ • restore()      │
│ • validate()     │        │ • alert()        │        │ • query()        │
└──────────────────┘        └──────────────────┘        └──────────────────┘
```

### Health Monitoring Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Health Monitoring Loop                                 │
│                                                                                 │
│  Every 5 seconds:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  1. Check Heartbeat Status                                               │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ For each supervised process:                                │     │   │
│  │     │   • Get last_heartbeat timestamp                            │     │   │
│  │     │   • Compare to expected interval:                            │     │   │
│  │     │     - Worker: 45s (1.5x heartbeat timeout)                  │     │   │
│  │     │     - MonitoringLoop: 45s (1.5x health check interval)      │     │   │
│  │     │   • Status: healthy | stale | critical                      │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                            │   │
│  │  2. Collect Resource Metrics                                               │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ For each running process:                                    │     │   │
│  │     │   • CPU percent (over 5 minute window)                       │     │   │
│  │     │   • Memory usage (MB)                                        │     │   │
│  │     │   • File descriptor count                                    │     │   │
│  │     │   • Process age ( uptime )                                   │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                            │   │
│  │  3. Evaluate Health Status                                                 │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Decision Logic:                                              │     │   │
│  │     │                                                              │     │   │
│  │     │ IF heartbeat_stale AND restart_eligible THEN                │     │   │
│  │     │   → Trigger restart (ProcessManager.restart())              │     │   │
│  │     │                                                              │     │   │
│  │     │ IF memory > threshold (2GB) THEN                             │     │   │
│  │     │   → Trigger graceful restart                                 │     │   │
│  │     │                                                              │     │   │
│  │     │ IF cpu > threshold (80%) for 5 minutes THEN                 │     │   │
│  │     │   → Trigger graceful restart                                 │     │   │
│  │     │                                                              │     │   │
│  │     │ IF fd_count > threshold (80% system limit) THEN             │     │   │
│  │     │   → Trigger graceful restart                                 │     │   │
│  │     │                                                              │     │   │
│  │     │ ELSE                                                         │     │   │
│  │     │   → Update health_status in database                        │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                            │   │
│  │  4. Emit Health Events                                                     │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Events published to Redis event bus:                        │     │   │
│  │     │   • supervisor.health.checked                               │     │   │
│  │     │   • supervisor.health.changed (on status change)            │     │   │
│  │     │   • supervisor.restart.initiated (on restart decision)      │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Process Restart Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Process Restart Sequence                              │
│                                                                                 │
│  Trigger: Health check failure OR process crash detection                       │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  1. Failure Detection                                                    │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Detection Method:                                            │     │   │
│  │     │   • Heartbeat timeout (no heartbeat for 2x interval)         │     │   │
│  │     │   • Process exit (poll() returns)                            │     │   │
│  │     │   • Resource threshold violation                             │     │   │
│  │     │   • Health check failure                                     │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  2. Restart Eligibility Check                                          │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Check:                                                       │     │   │
│  │     │   • Restart count in last hour < max_restarts_per_hour (5)   │     │   │
│  │     │   • Time since last restart > backoff delay                  │     │   │
│  │     │   • Not in maintenance mode                                  │     │   │
│  │     │                                                              │     │   │
│  │     │ IF eligible THEN proceed to step 3                          │     │   │
│  │     │ ELSE skip restart, emit alert, require manual intervention  │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  3. Calculate Backoff Delay                                             │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Exponential backoff:                                         │     │   │
│  │     │   delay = min(base * (2 ^ restart_count), max)              │     │   │
│  │     │   delay = min(5 * (2 ^ restart_count), 80)                  │     │   │
│  │     │                                                              │     │   │
│  │     │ Examples:                                                    │     │   │
│  │     │   • 1st restart: 5s                                          │     │   │
│  │     │   • 2nd restart: 10s                                         │     │   │
│  │     │   • 3rd restart: 20s                                         │     │   │
│  │     │   • 4th restart: 40s                                         │     │   │
│  │     │   • 5th+ restart: 80s                                        │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  4. Graceful Shutdown (if process still running)                        │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Process-specific graceful shutdown:                          │     │   │
│  │     │   • Worker: Complete current task, timeout 30s              │     │   │
│  │     │   • MonitoringLoop: Complete current cycle, timeout 30s     │     │   │
│  │     │                                                              │     │   │
│  │     │ IF timeout exceeded THEN force kill (SIGKILL)               │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  5. State Preservation                                                  │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Worker:                                                      │     │   │
│  │     │   • Mark in-progress tasks as "pending" for retry            │     │   │
│  │     │   • Save agent_id for re-registration                        │     │   │
│  │     │   • Persist worker position in queue                         │     │   │
│  │     │                                                              │     │   │
│  │     │ MonitoringLoop:                                              │     │   │
│  │     │   • Save current cycle_id                                    │     │   │
│  │     │   • Save last run timestamps                                 │     │   │
│  │     │   • Save metrics totals                                      │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  6. Process Launch                                                      │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Launch new process with:                                      │     │   │
│  │     │   • Original command and arguments                           │     │   │
│  │     │   • Environment variables (including recovery flags)         │     │   │
│  │     │   • Restored state from step 5                               │     │   │
│  │     │   • New PID tracking                                         │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  7. Health Verification                                                │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Wait for:                                                     │     │   │
│  │     │   • First heartbeat received                                 │     │   │
│  │     │   • Process registration complete                            │     │   │
│  │     │   • Status = "running"                                       │     │   │
│  │     │                                                              │     │   │
│  │     │ Timeout: 60 seconds                                         │     │   │
│  │     │   • IF timeout → Restart failed, emit critical alert        │     │   │
│  │     │   • ELSE → Restart successful                                │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  8. Update State and Emit Events                                       │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Database:                                                    │     │   │
│  │     │   • Update process.status = "running"                        │     │   │
│  │     │   • Increment restart_count                                  │     │   │
│  │     │   • Update last_restart_time                                 │     │   │
│  │     │   • Log restart event                                        │     │   │
│  │     │                                                              │     │   │
│  │     │ Event Bus:                                                   │     │   │
│  │     │   • supervisor.process.restarted                             │     │   │
│  │     │   • supervisor.health.changed                                │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Graceful Shutdown Coordination

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Graceful Shutdown Sequence                               │
│                                                                                 │
│  Trigger: SIGTERM, SIGINT, or API request                                       │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  1. Shutdown Signal Received                                             │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Actions:                                                     │     │   │
│  │     │   • Set supervisor.status = "stopping"                       │     │   │
│  │     │   • Emit supervisor.shutdown.started event                   │     │   │
│  │     │   • Calculate dependency order for shutdown                  │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  2. Stop MonitoringLoop First (Dependency: Monitoring → Workers)         │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Send SIGTERM to MonitoringLoop:                              │     │   │
│  │     │   • Wait for final cycle to complete                         │     │   │
│  │     │   • Timeout: 30 seconds                                      │     │   │
│  │     │   • Force SIGKILL if timeout exceeded                        │     │   │
│  │     │   • Verify process terminated                                │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  3. Stop Worker Processes (Parallel)                                    │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Send SIGTERM to all workers in parallel:                     │     │   │
│  │     │   • Wait for current tasks to complete                       │     │   │
│  │     │   • Timeout per worker: 30 seconds                           │     │   │
│  │     │   • Force SIGKILL if timeout exceeded                        │     │   │
│  │     │   • Mark incomplete tasks as "pending"                        │     │   │
│  │     │   • Update agent status = "terminated"                        │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  4. Cleanup and Finalization                                            │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Cleanup actions:                                             │     │   │
│  │     │   • Close database connections                               │     │   │
│  │     │   • Close Redis/event bus connections                        │     │   │
│  │     │   • Flush logs                                              │     │   │
│  │     │   • Save final state snapshot                               │     │   │
│  │     │   • Update supervisor.status = "stopped"                     │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  5. Emit Shutdown Complete Event                                        │   │
│  │     ┌─────────────────────────────────────────────────────────────┐     │   │
│  │     │ Event: supervisor.shutdown.completed                          │     │   │
│  │     │ Payload:                                                      │     │   │
│  │     │   • duration: total shutdown time                            │     │   │
│  │     │   • processes_stopped: count                                 │     │   │
│  │     │   • processes_forced: count (SIGKILL)                        │     │   │
│  │     │   • tasks_interrupted: count                                 │     │   │
│  │     └─────────────────────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Database Schema Extension

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             New Tables                                          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  Table: supervised_processes                                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Column              │ Type          │ Description                              │
├─────────────────────┼───────────────┼──────────────────────────────────────────┤
│  id                  │ UUID          │ Primary key                              │
│  process_type        │ VARCHAR(50)   │ 'worker', 'monitoring_loop', 'supervisor'│
│  pid                 │ INTEGER       │ Process ID (NULL if stopped)             │
│  command             │ TEXT          │ Launch command                           │
│  args                │ JSONB         │ Launch arguments                         │
│  status              │ VARCHAR(20)   │ 'starting', 'running', 'stopping',       │
│                      │               │ 'stopped', 'failed', 'crashed'           │
│  start_time          │ TIMESTAMPTZ   │ Process start timestamp                  │
│  last_heartbeat      │ TIMESTAMPTZ   │ Last heartbeat received                  │
│  restart_count       │ INTEGER       │ Total restart attempts                   │
│  last_restart_time   │ TIMESTAMPTZ   │ Last restart timestamp                   │
│  health_status       │ VARCHAR(20)   │ 'healthy', 'degraded', 'unhealthy'       │
│  resource_metrics    │ JSONB         │ {cpu_percent, memory_mb, fd_count}       │
│  config              │ JSONB         │ Process-specific configuration           │
│  created_at          │ TIMESTAMPTZ   │ Creation timestamp                       │
│  updated_at          │ TIMESTAMPTZ   │ Last update timestamp                    │
├─────────────────────┴───────────────┴──────────────────────────────────────────┤
│  Indexes:                                                                       │
│    - supervised_processes_process_type_idx                                     │
│    - supervised_processes_status_idx                                           │
│    - supervised_processes_last_heartbeat_idx                                    │
│    - supervised_processes_health_status_idx                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  Table: supervisor_events                                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Column              │ Type          │ Description                              │
├─────────────────────┼───────────────┼──────────────────────────────────────────┤
│  id                  │ UUID          │ Primary key                              │
│  event_type          │ VARCHAR(50)   │ 'process_started', 'process_stopped',    │
│                      │               │ 'process_restarted', 'health_changed',   │
│                      │               │ 'shutdown_initiated'                     │
│  process_id          │ UUID          │ FK to supervised_processes.id            │
│  process_type        │ VARCHAR(50)   │ Process type (denormalized)              │
│  timestamp           │ TIMESTAMPTZ   │ Event timestamp                          │
│  details             │ JSONB         │ Event details (reason, context, etc.)   │
│  severity            │ VARCHAR(20)   │ 'info', 'warning', 'error', 'critical'   │
│  acknowledged        │ BOOLEAN       │ Whether event was acknowledged           │
│  acknowledged_at     │ TIMESTAMPTZ   │ Acknowledgment timestamp                 │
│  acknowledged_by     │ VARCHAR(100)  │ Who acknowledged (user/system)           │
├─────────────────────┴───────────────┴──────────────────────────────────────────┤
│  Indexes:                                                                       │
│    - supervisor_events_event_type_idx                                          │
│    - supervisor_events_process_id_idx                                          │
│    - supervisor_events_timestamp_idx                                            │
│    - supervisor_events_severity_idx                                             │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  Table: supervisor_config                                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Column              │ Type          │ Description                              │
├─────────────────────┼───────────────┼──────────────────────────────────────────┤
│  id                  │ UUID          │ Primary key                              │
│  config_name         │ VARCHAR(100)  │ Configuration name/key                   │
│  config_value        │ JSONB         │ Configuration value                      │
│  description         │ TEXT          │ Configuration description                │
│  is_active           │ BOOLEAN       │ Whether this config is active            │
│  created_at          │ TIMESTAMPTZ   │ Creation timestamp                       │
│  updated_at          │ TIMESTAMPTZ   │ Last update timestamp                    │
├─────────────────────┴───────────────┴──────────────────────────────────────────┤
│  Indexes:                                                                       │
│    - supervisor_config_config_name_idx (unique)                                 │
│    - supervisor_config_is_active_idx                                            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  Extended Table: agents                                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│  New Columns:                                                                    │
│  supervisor_process_id │ UUID          │ FK to supervised_processes.id          │
│  supervised_since      │ TIMESTAMPTZ   │ When supervision started                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### API Endpoints

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           REST API Endpoints                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

GET  /api/supervisor/status
├── Response: {
│     "running": true,
│     "uptime_seconds": 1234567,
│     "supervised_processes": 5,
│     "healthy_processes": 4,
│     "degraded_processes": 1,
│     "unhealthy_processes": 0,
│     "total_restarts": 12,
│     "last_health_check": "2026-01-08T12:34:56Z"
│   }

GET  /api/supervisor/processes
├── Response: [
│     {
│       "id": "uuid",
│       "process_type": "worker",
│       "status": "running",
│       "health_status": "healthy",
│       "pid": 12345,
│       "start_time": "2026-01-08T10:00:00Z",
│       "last_heartbeat": "2026-01-08T12:34:50Z",
│       "restart_count": 2,
│       "resource_metrics": {
│         "cpu_percent": 45.2,
│         "memory_mb": 512,
│         "fd_count": 128
│       }
│     },
│     ...
│   ]

GET  /api/supervisor/processes/{process_id}
├── Response: { ... } (single process details)

POST /api/supervisor/processes/{process_id}/restart
├── Response: {
│     "success": true,
│     "message": "Restart initiated",
│     "estimated_restart_time": "2026-01-08T12:35:10Z"
│   }

POST /api/supervisor/shutdown
├── Body: { "force": false, "timeout": 30 }
├── Response: {
│     "success": true,
│     "message": "Shutdown initiated",
│     "estimated_completion": "2026-01-08T12:35:30Z"
│   }

GET  /api/supervisor/events
├── Query: ?limit=100&severity=warning&process_id=uuid
├── Response: [
│     {
│       "id": "uuid",
│       "event_type": "process_restarted",
│       "process_id": "uuid",
│       "timestamp": "2026-01-08T12:34:00Z",
│       "severity": "warning",
│       "details": { "reason": "heartbeat_timeout", "restart_count": 3 }
│     },
│     ...
│   ]

POST /api/supervisor/events/{event_id}/acknowledge
├── Response: { "success": true, "acknowledged_at": "..." }

GET  /api/supervisor/config
├── Response: {
│     "heartbeat_interval": 10,
│     "health_check_interval": 5,
│     "max_restarts_per_hour": 5,
│     "memory_threshold_mb": 2048,
│     ...
│   }

PUT  /api/supervisor/config
├── Body: { "max_restarts_per_hour": 10, ... }
├── Response: { "success": true, "config": { ... } }

POST /api/supervisor/config/reload
├── Response: { "success": true, "message": "Config reloaded" }
```

### WebSocket Events

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         WebSocket Events (Real-time)                             │
└─────────────────────────────────────────────────────────────────────────────────┘

Channel: supervisor:status
├── Event: status_changed
│   {
│     "running": true,
│     "healthy_processes": 4,
│     "unhealthy_processes": 1,
│     "timestamp": "2026-01-08T12:34:56Z"
│   }

Channel: supervisor:processes
├── Event: process_started
│   {
│     "process_id": "uuid",
│     "process_type": "worker",
│     "pid": 12345,
│     "timestamp": "2026-01-08T12:34:00Z"
│   }
│
├── Event: process_stopped
│   {
│     "process_id": "uuid",
│     "process_type": "worker",
│     "reason": "shutdown_requested",
│     "timestamp": "2026-01-08T12:34:30Z"
│   }
│
├── Event: process_restarted
│   {
│     "process_id": "uuid",
│     "process_type": "worker",
│     "restart_count": 3,
│     "reason": "heartbeat_timeout",
│     "timestamp": "2026-01-08T12:34:45Z"
│   }
│
├── Event: health_changed
│   {
│     "process_id": "uuid",
│     "old_status": "healthy",
│     "new_status": "degraded",
│     "reason": "memory_threshold_exceeded",
│     "timestamp": "2026-01-08T12:34:15Z"
│   }

Channel: supervisor:events
├── Event: new_event
│   {
│     "event_id": "uuid",
│     "event_type": "process_restarted",
│     "severity": "warning",
│     "details": { ... },
│     "timestamp": "2026-01-08T12:34:45Z"
│   }
│
├── Event: critical_alert
│   {
│     "event_id": "uuid",
│     "event_type": "restart_limit_exceeded",
│     "severity": "critical",
│     "message": "Manual intervention required",
│     "process_id": "uuid",
│     "timestamp": "2026-01-08T12:34:50Z"
│   }

Channel: supervisor:shutdown
├── Event: shutdown_started
│   {
│     "timeout": 30,
│     "process_count": 5,
│     "timestamp": "2026-01-08T12:34:00Z"
│   }
│
├── Event: shutdown_progress
│   {
│     "stopped_count": 3,
│     "remaining_count": 2,
│     "timestamp": "2026-01-08T12:34:10Z"
│   }
│
├── Event: shutdown_completed
│   {
│     "total_duration_seconds": 25,
│     "stopped_count": 5,
│     "forced_count": 0,
│     "timestamp": "2026-01-08T12:34:25Z"
│   }
```

---

**Document Version**: 1.0
**Last Updated**: 2026-01-08
**Related Documents**: supervisor-system-requirements.md
