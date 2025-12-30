"""
Workers module - Long-running processes for sandboxes.

Contains worker scripts that run inside Daytona sandboxes and communicate
with the main server via HTTP callbacks (webhook pattern).

Uses the Claude Agent SDK (claude_code_sdk) for Claude interactions.

Workers:
- SandboxWorker: Base worker for single-run task execution
- ContinuousSandboxWorker: Iterative worker that runs until task is complete
  (code pushed, PR created) or limits are reached
"""

from omoi_os.workers.sandbox_agent_worker import (
    EventReporter,
    MessagePoller,
    SandboxWorker,
    WorkerConfig,
    process_sdk_response,
)

from omoi_os.workers.continuous_sandbox_worker import (
    ContinuousSandboxWorker,
    ContinuousWorkerConfig,
    IterationState,
)

__all__ = [
    # Base worker
    "EventReporter",
    "MessagePoller",
    "SandboxWorker",
    "WorkerConfig",
    "process_sdk_response",
    # Continuous worker
    "ContinuousSandboxWorker",
    "ContinuousWorkerConfig",
    "IterationState",
]
