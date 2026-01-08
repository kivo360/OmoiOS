# Sandbox Agent System - Current Status

**Last Updated:** 2025-12-18  
**Status:** ✅ Core functionality working, ready for frontend integration

## ✅ What's Working

### 1. Sandbox Spawning & Configuration
- **Daytona Integration**: Sandboxes spawn successfully with configurable resources
  - Memory: 4-8 GB (configurable via `SANDBOX_MEMORY_GB` or YAML)
  - CPU: 2-4 cores (configurable via `SANDBOX_CPU` or YAML)
  - Disk: 8-10 GB (configurable via `SANDBOX_DISK_GB` or YAML)
  - Snapshot support: Default `ai-agent-dev-light` (configurable via `SANDBOX_SNAPSHOT` or YAML)
- **Pre-Sandbox Branch Creation**: GitHub branches created before sandbox spawn using user's OAuth token
  - GitFlow-compliant branch names (e.g., `feature/calculate-binomial-coefficient`)
  - Branch name passed to sandbox via `BRANCH_NAME` environment variable
- **Configuration Priority**: Parameters > Environment Variables > YAML Config > Defaults

### 2. Event Tracking & Persistence
- **Event Types Tracked** (9+ types):
  - `agent.started` - Worker initialization
  - `agent.system_message` - System prompts
  - `agent.assistant_message` - LLM responses
  - `agent.message` - Text content blocks
  - `agent.tool_use` - Tool invocations (Write, Edit, Bash, etc.)
  - `agent.tool_completed` - Tool completion with results
  - `agent.user_tool_result` - Tool result messages
  - `agent.file_edited` - File changes with unified diffs
  - `agent.completed` - Task completion
  - `agent.waiting` - Worker waiting for messages
  - `agent.heartbeat` - Periodic health checks (every 30s)
- **Database Persistence**: All events stored in `sandbox_events` table
- **API Endpoints**:
  - `POST /api/v1/sandboxes/{sandbox_id}/events` - Receive events from workers
  - `GET /api/v1/sandboxes/{sandbox_id}/events` - Query events (with pagination/filtering)
  - `GET /api/v1/sandboxes/health` - Health check endpoint

### 3. File Change Tracking
- **Unified Diffs**: File edits tracked with full unified diff format
- **Event Data**: `agent.file_edited` events include:
  - `file_path`: Path to modified file
  - `full_diff`: Complete unified diff (can be large, truncated in logs)
  - `turn`: Turn number when edit occurred
- **Tools Supported**: Write, Edit (file modifications tracked automatically)

### 4. Task Management
- **Task Status Flow**: `pending` → `assigned` → `running` → `completed`/`failed`
- **Task Pickup Detection**: Enhanced logic checks:
  - Database status updates
  - Sandbox ID assignment
  - Event activity (conversation logs, tool usage)
- **Completion Reporting**: Robust completion reporting with retry logic

### 5. Worker Robustness
- **Error Handling**:
  - 502 errors suppressed for non-critical events (heartbeats)
  - SIGKILL (-9) errors detected with diagnostic messages
  - Stream errors handled gracefully with partial output return
- **Session Management**: Session resume support via `resume_session_id`
- **Resource Limits**: Memory/CPU limits prevent OOM kills (configurable)

### 6. Claude Agent SDK Integration
- **Tools Enabled**: Read, Write, Bash, Edit, Glob, Grep, Task, Skill
- **Sub-agents & Skills**: Enabled via `enable_skills=True` and `enable_subagents=True`
- **Model Support**: GLM 4.6 (128k context), configurable via environment variables
- **Permission Mode**: `acceptEdits` (configurable)

## 📊 Test Results

### Successful Test Runs
All recent test runs show consistent patterns:
- **Event Count**: 44-71 events per run
- **Duration**: 567-1397 seconds
- **Core Events**: All runs include:
  - 1x `agent.started`
  - 3x `agent.tool_use` (Write, Edit, Bash)
  - 2x `agent.file_edited` (file creation + modification)
  - 1x `agent.completed`
  - Variable `agent.heartbeat` events (18-45, depending on post-completion wait time)

### Example Successful Run
- **Sandbox**: `omoios-886da5fe-0a9fee`
- **Task**: Calculate binomial coefficient C(50,25)
- **Result**: ✅ Completed successfully
- **Events**: 71 total (26 activity events + 45 heartbeats)
- **File Edits**: 2 (creation + modification of `binomial.py`)

## 🔧 Configuration

### Environment Variables
See `backend/docs/SANDBOX_ENVIRONMENT_VARIABLES.md` for complete list.

Key variables:
- `SANDBOX_MEMORY_GB` - Memory allocation (default: 4)
- `SANDBOX_CPU` - CPU cores (default: 2)
- `SANDBOX_DISK_GB` - Disk space (default: 8)
- `SANDBOX_SNAPSHOT` - Snapshot name (default: `ai-agent-dev-light`)
- `SANDBOX_IMAGE` - Base image (fallback if snapshot not set)
- `CALLBACK_URL` - API endpoint for event reporting
- `TASK_DESCRIPTION` - Task description
- `TASK_DATA_BASE64` - Base64-encoded task data

### YAML Configuration
Configuration files: `backend/config/base.yaml`, `backend/config/production.yaml`

```yaml
daytona:
  snapshot: "ai-agent-dev-light"
  sandbox_memory_gb: 4
  sandbox_cpu: 2
  sandbox_disk_gb: 8
```

## 📁 Key Files

### Core Components
- `backend/omoi_os/workers/claude_sandbox_worker.py` - Standalone worker script
- `backend/omoi_os/services/daytona_spawner.py` - Sandbox spawning service
- `backend/omoi_os/api/routes/sandbox.py` - Event API endpoints
- `backend/omoi_os/models/sandbox_event.py` - Event database model

### Test Scripts
- `backend/scripts/test_api_sandbox_spawn.py` - End-to-end API test
- `backend/scripts/query_sandbox_events.py` - Query events from database
- `backend/scripts/compare_sandbox_events.py` - Compare events across sandboxes
- `backend/scripts/list_recent_sandboxes.py` - List recent sandboxes

## 🚀 Next Steps

### Immediate (Frontend Integration)
- [ ] Test event streaming in frontend UI
- [ ] Implement FileChangeCard component with diff viewer
- [ ] Real-time event updates via WebSocket
- [ ] Activity feed rendering

### Future Enhancements
- [ ] Automated sandbox pruning worker
- [ ] Enhanced monitoring system (see `MONITORING_TODO.md`)
- [ ] Event batching for high-volume scenarios
- [ ] Redis event storage for faster queries
- [ ] Session replay functionality

## 📝 Notes

- All events are persisted to PostgreSQL `sandbox_events` table
- Events are broadcast via EventBus to WebSocket clients (when connected)
- File diffs can be large; consider truncation for UI display
- Heartbeat events occur every 30 seconds while worker is alive
- Worker continues running after task completion (waits for new messages)
