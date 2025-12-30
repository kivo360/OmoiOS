"""
Workers module - Long-running processes for sandboxes.

Contains worker scripts that run inside Daytona sandboxes and communicate
with the main server via HTTP callbacks (webhook pattern).

Uses the Claude Agent SDK (claude_code_sdk) for Claude interactions.

Workers:
- SandboxWorker: Production worker with integrated continuous mode support
  - Single-run mode: Execute task once and wait for messages
  - Continuous mode: Iterate until task truly completes (code pushed, PR created)
  - Enabled by default for implementation and validation execution modes
- ContinuousSandboxWorker: Deprecated - use SandboxWorker with continuous_mode=True
"""

# Main production worker (claude_sandbox_worker.py)
from omoi_os.workers.claude_sandbox_worker import (
    EventReporter,
    MessagePoller,
    SandboxWorker,
    WorkerConfig,
    IterationState,
    check_git_status,
)

# Legacy compat: process_sdk_response from simple worker
from omoi_os.workers.sandbox_agent_worker import process_sdk_response

# Keep continuous worker for backwards compatibility
from omoi_os.workers.continuous_sandbox_worker import (
    ContinuousSandboxWorker,
    ContinuousWorkerConfig,
)

__all__ = [
    # Base worker (with integrated continuous mode)
    "EventReporter",
    "MessagePoller",
    "SandboxWorker",
    "WorkerConfig",
    "process_sdk_response",
    "IterationState",
    "check_git_status",
    # Continuous worker (deprecated - use SandboxWorker with continuous_mode=True)
    "ContinuousSandboxWorker",
    "ContinuousWorkerConfig",
]
