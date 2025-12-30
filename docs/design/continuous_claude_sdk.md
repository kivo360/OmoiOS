# Continuous Claude SDK Design

**Created**: 2025-12-29
**Status**: Draft
**Purpose**: Design a Python implementation of continuous/iterative Claude Code execution using the Claude Agent SDK, equivalent to the `continuous-claude` bash script. Integrates with the existing OmoiOS sandbox worker infrastructure.

## Overview

This document describes a Python implementation that runs Claude Code iteratively with automatic session management, cost tracking, completion detection, and optional git integration. The implementation leverages the `claude-agent-sdk` Python package for native async interaction with Claude Code.

**Key Integration**: This design builds on the existing `claude_sandbox_worker.py` architecture, reusing its `EventReporter`, `MessagePoller`, `WorkerConfig`, and session management patterns.

## Problem Statement

The original `continuous-claude` bash script provides:
1. Iterative execution with configurable limits (runs, cost, duration)
2. Shared context via notes files between iterations
3. Completion signal detection to stop when project is done
4. Git integration (branch creation, PR management, merge queuing)
5. Cost tracking and budget enforcement

The goal is to replicate this functionality using the Python SDK for:
- Cleaner code with proper typing
- Native async/await patterns
- Direct access to SDK features (session resume, cost tracking, structured outputs)
- **Integration with existing OmoiOS infrastructure** (EventReporter, callbacks, session portability)

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     Continuous Claude Runner (ContinuousSandboxWorker)        │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐  │
│  │  WorkerConfig      │  │  IterationState    │  │  Git Integration       │  │
│  │  (extends existing)│  │  Tracker           │  │  (Optional)            │  │
│  └─────────┬──────────┘  └─────────┬──────────┘  └───────────┬────────────┘  │
│            │                       │                          │               │
│            └───────────────────────┼──────────────────────────┘               │
│                                    │                                          │
│                                    ▼                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                    Main Iteration Loop Controller                       │  │
│  │  - Checks limits (runs, cost, duration)                                 │  │
│  │  - Detects completion signals                                           │  │
│  │  - Manages iteration state                                              │  │
│  │  - Reports events via EventReporter                                     │  │
│  └──────────────────────────────────┬─────────────────────────────────────┘  │
│                                     │                                         │
│                                     ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │              Single Iteration Executor (reuses SandboxWorker._process)  │  │
│  │  - Builds enhanced prompt with context                                  │  │
│  │  - Calls ClaudeSDKClient.query()                                        │  │
│  │  - Processes messages (Assistant, Result, System)                       │  │
│  │  - Reports events via EventReporter                                     │  │
│  │  - Tracks cost and session ID                                           │  │
│  └──────────────────────────────────┬─────────────────────────────────────┘  │
│                                     │                                         │
├─────────────────────────────────────┼─────────────────────────────────────────┤
│                     Reused from claude_sandbox_worker.py                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐    │
│  │  EventReporter   │  │  MessagePoller   │  │  FileChangeTracker       │    │
│  │  (HTTP callbacks)│  │  (injected msgs) │  │  (diff generation)       │    │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘    │
└─────────────────────────────────────┼─────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         claude-agent-sdk                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│  ClaudeSDKClient     │  ClaudeAgentOptions    │  Message Types               │
│  (bidirectional)     │  (configuration)       │  (Assistant, Result, etc.)   │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                      OmoiOS Main Server (callback_url)                        │
├──────────────────────────────────────────────────────────────────────────────┤
│  POST /api/v1/sandboxes/{id}/events   │  GET /api/v1/sandboxes/{id}/messages │
│  (receives iteration events)           │  (provides injected messages)        │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. ContinuousWorkerConfig (extends existing WorkerConfig)

The continuous iteration config extends the existing `WorkerConfig` from `claude_sandbox_worker.py` with iteration-specific settings. This ensures full compatibility with the OmoiOS infrastructure.

```python
class ContinuousWorkerConfig(WorkerConfig):
    """Extended configuration for continuous Claude execution.

    Inherits all WorkerConfig features:
    - sandbox_id, task_id, agent_id, ticket_id
    - callback_url for EventReporter
    - model, api_key, permission_mode
    - resume_session_id, session_transcript_b64
    - enable_spec_tools, enable_skills, enable_subagents

    Adds iteration-specific settings from environment variables.
    """

    def __init__(self):
        super().__init__()

        # Iteration limits (at least one should be set)
        # Environment: CONTINUOUS_MAX_RUNS, CONTINUOUS_MAX_COST_USD, CONTINUOUS_MAX_DURATION
        self.max_runs: Optional[int] = self._get_int_env("CONTINUOUS_MAX_RUNS")
        self.max_cost_usd: Optional[float] = self._get_float_env("CONTINUOUS_MAX_COST_USD")
        self.max_duration_seconds: Optional[int] = self._get_int_env("CONTINUOUS_MAX_DURATION")

        # Completion detection
        self.completion_signal = os.environ.get(
            "CONTINUOUS_COMPLETION_SIGNAL",
            "CONTINUOUS_CLAUDE_PROJECT_COMPLETE"
        )
        self.completion_threshold = int(os.environ.get("CONTINUOUS_COMPLETION_THRESHOLD", "3"))

        # Notes file for cross-iteration context
        self.notes_file = os.environ.get("CONTINUOUS_NOTES_FILE", "SHARED_TASK_NOTES.md")

        # Git/GitHub settings (reuses existing github_token, github_repo, branch_name)
        self.enable_commits = os.environ.get("CONTINUOUS_ENABLE_COMMITS", "true").lower() == "true"
        self.git_branch_prefix = os.environ.get("CONTINUOUS_BRANCH_PREFIX", "continuous-claude/")
        self.merge_strategy = os.environ.get("CONTINUOUS_MERGE_STRATEGY", "squash")

        # Iteration mode flag
        self.continuous_mode = os.environ.get("CONTINUOUS_MODE", "false").lower() == "true"

    def _get_int_env(self, key: str) -> Optional[int]:
        val = os.environ.get(key)
        return int(val) if val else None

    def _get_float_env(self, key: str) -> Optional[float]:
        val = os.environ.get(key)
        return float(val) if val else None

    def validate_continuous(self) -> list[str]:
        """Validate continuous-specific configuration."""
        errors = super().validate()

        # At least one limit must be set
        if not any([self.max_runs, self.max_cost_usd, self.max_duration_seconds]):
            errors.append(
                "At least one limit required: CONTINUOUS_MAX_RUNS, "
                "CONTINUOUS_MAX_COST_USD, or CONTINUOUS_MAX_DURATION"
            )

        return errors
```

**Environment Variables for Continuous Mode:**

| Variable | Description | Default |
|----------|-------------|---------|
| `CONTINUOUS_MODE` | Enable continuous iteration mode | `false` |
| `CONTINUOUS_MAX_RUNS` | Maximum successful iterations | None |
| `CONTINUOUS_MAX_COST_USD` | Maximum total cost in USD | None |
| `CONTINUOUS_MAX_DURATION` | Maximum duration in seconds | None |
| `CONTINUOUS_COMPLETION_SIGNAL` | Phrase to detect completion | `CONTINUOUS_CLAUDE_PROJECT_COMPLETE` |
| `CONTINUOUS_COMPLETION_THRESHOLD` | Consecutive signals to stop | `3` |
| `CONTINUOUS_NOTES_FILE` | Notes file for context sharing | `SHARED_TASK_NOTES.md` |
| `CONTINUOUS_ENABLE_COMMITS` | Enable git commits per iteration | `true` |
| `CONTINUOUS_BRANCH_PREFIX` | Git branch prefix | `continuous-claude/` |
| `CONTINUOUS_MERGE_STRATEGY` | PR merge strategy | `squash` |

### 2. IterationState

Tracks runtime state across iterations. This is reported to the main server via `EventReporter` after each iteration.

```python
@dataclass
class IterationState:
    """Tracks state across iterations."""

    iteration_num: int = 0                   # Current iteration
    successful_iterations: int = 0           # Completed successfully
    error_count: int = 0                     # Consecutive errors
    extra_iterations: int = 0                # Added due to errors
    total_cost: float = 0.0                  # Accumulated cost
    completion_signal_count: int = 0         # Consecutive completion signals
    start_time: Optional[float] = None       # For duration tracking
    last_session_id: Optional[str] = None    # For potential resume
    last_transcript_b64: Optional[str] = None  # For cross-sandbox resumption

    def to_event_data(self) -> dict:
        """Convert state to event payload for EventReporter."""
        return {
            "iteration_num": self.iteration_num,
            "successful_iterations": self.successful_iterations,
            "error_count": self.error_count,
            "extra_iterations": self.extra_iterations,
            "total_cost_usd": self.total_cost,
            "completion_signal_count": self.completion_signal_count,
            "elapsed_seconds": time.time() - self.start_time if self.start_time else 0,
            "last_session_id": self.last_session_id,
        }
```

### 3. EventReporter Integration (Reused)

The continuous worker reuses the existing `EventReporter` from `claude_sandbox_worker.py` to report iteration events back to the main OmoiOS server.

```python
# Reused from claude_sandbox_worker.py - no changes needed
class EventReporter:
    """Reports events back to main server via HTTP POST."""

    async def report(
        self,
        event_type: str,
        event_data: dict[str, Any],
        source: str = "agent",
    ) -> bool:
        """Report event to main server with full context."""
        url = f"{self.config.callback_url}/api/v1/sandboxes/{self.config.sandbox_id}/events"
        # ... existing implementation
```

**Iteration-Specific Event Types:**

| Event Type | When Emitted | Payload |
|------------|--------------|---------|
| `iteration.started` | Before each iteration begins | `{iteration_num, prompt_preview, state}` |
| `iteration.completed` | After successful iteration | `{iteration_num, cost_usd, session_id, transcript_b64, output_preview}` |
| `iteration.failed` | After iteration error | `{iteration_num, error, error_type, retry_allowed}` |
| `iteration.completion_signal` | When completion signal detected | `{iteration_num, signal_count, threshold}` |
| `continuous.started` | At start of continuous run | `{config, limits, goal}` |
| `continuous.completed` | At end of continuous run | `{state, stop_reason, total_iterations, total_cost}` |
| `continuous.limit_reached` | When a limit is hit | `{limit_type, limit_value, current_value}` |

**Example Event Flow:**

```
continuous.started → iteration.started → agent.tool_use → agent.message →
iteration.completed → iteration.started → ... → iteration.completion_signal →
continuous.completed
```

### 4. Prompt Enhancement

Each iteration gets an enhanced prompt with:

1. **Workflow context** - Explains the continuous loop and completion signal
2. **Primary goal** - The user's original prompt
3. **Previous iteration notes** - Content from `SHARED_TASK_NOTES.md` if exists
4. **Notes update instructions** - How to update the notes file

```python
WORKFLOW_CONTEXT_TEMPLATE = """## CONTINUOUS WORKFLOW CONTEXT

This is part of a continuous development loop where work happens
incrementally across multiple iterations...

**Project Completion Signal**: If you determine that the ENTIRE project
goal is fully complete, include the exact phrase "{completion_signal}"
in your response...

## PRIMARY GOAL

{prompt}
"""
```

## Message Processing

The SDK provides typed messages that we process in the iteration:

| Message Type | SDK Class | Information Extracted |
|--------------|-----------|----------------------|
| System Init | `SystemMessage` | `session_id` |
| Claude Response | `AssistantMessage` | Text content, tool usage |
| Tool Results | `ToolResultBlock` | Tool execution results |
| Completion | `ResultMessage` | `total_cost_usd`, `is_error`, final `session_id` |

```python
async for message in query(prompt=enhanced_prompt, options=options):
    if isinstance(message, SystemMessage):
        if message.subtype == "init":
            session_id = message.data.get("session_id")

    elif isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                result_text += block.text

    elif isinstance(message, ResultMessage):
        iteration_cost = message.total_cost_usd
        if message.is_error:
            # Handle error
            pass
```

## Limit Enforcement

The main loop checks limits before each iteration:

```python
def should_continue(config: ContinuousClaudeConfig, state: IterationState) -> bool:
    # Check completion signal threshold
    if state.completion_signal_count >= config.completion_threshold:
        return False

    # Check max runs
    if config.max_runs and state.successful_iterations >= config.max_runs:
        return False

    # Check max cost
    if config.max_cost_usd and state.total_cost >= config.max_cost_usd:
        return False

    # Check max duration
    if config.max_duration_seconds and state.start_time:
        elapsed = time.time() - state.start_time
        if elapsed >= config.max_duration_seconds:
            return False

    return True
```

## Error Handling Strategy

| Error Type | Handling |
|------------|----------|
| Claude error (rate limit, auth) | Increment error count, retry |
| 3 consecutive errors | Fatal exit |
| Single error | Add extra iteration, continue |
| Cost/duration exceeded | Graceful stop |

```python
if success:
    state.successful_iterations += 1
    state.error_count = 0  # Reset on success
else:
    state.error_count += 1
    state.extra_iterations += 1

    if state.error_count >= 3:
        print("Fatal: 3 consecutive errors. Exiting.")
        sys.exit(1)
```

## SDK Features Leveraged

### 1. Native Async Iteration

```python
# SDK handles subprocess management internally
async for message in query(prompt=prompt, options=options):
    # Process typed messages
    pass
```

### 2. Built-in Cost Tracking

```python
elif isinstance(message, ResultMessage):
    state.total_cost += message.total_cost_usd or 0.0
```

### 3. Session Resume (for future enhancement)

```python
# Resume previous session
options = ClaudeAgentOptions(
    resume=state.last_session_id,
    # ... other options
)
```

### 4. Permission Modes

```python
options = ClaudeAgentOptions(
    permission_mode="acceptEdits",  # Auto-approve file edits
    # Or "bypassPermissions" for full automation
)
```

## Git Integration (Optional)

When `enable_commits=True`:

1. **Branch Creation** - Create `continuous-claude/iteration-N/YYYY-MM-DD-hash`
2. **Commit** - Use Claude to write commit message and commit
3. **PR Creation** - Create PR via `gh` CLI
4. **Wait for Checks** - Poll for CI/review status
5. **Merge** - Merge with configured strategy
6. **Cleanup** - Delete branch, pull latest

This mirrors the bash script's behavior using `subprocess` calls to `git` and `gh`.

## ContinuousSandboxWorker (Main Implementation)

The `ContinuousSandboxWorker` extends the existing `SandboxWorker` to add iteration loop logic. It reuses the message processing, event reporting, and hooks infrastructure.

```python
class ContinuousSandboxWorker(SandboxWorker):
    """Extended worker for continuous/iterative Claude execution.

    Inherits from SandboxWorker:
    - EventReporter for HTTP callbacks
    - MessagePoller for injected messages
    - FileChangeTracker for diffs
    - Pre/Post tool hooks
    - Session transcript export/import

    Adds:
    - Iteration loop with configurable limits
    - Completion signal detection
    - Cross-iteration context via notes file
    - Per-iteration event reporting
    """

    def __init__(self, config: ContinuousWorkerConfig):
        super().__init__(config)
        self.continuous_config = config
        self.iteration_state = IterationState()

    async def run_continuous(self):
        """Main continuous execution loop."""
        self._setup_signal_handlers()
        self.running = True
        self.iteration_state.start_time = time.time()

        # Validate continuous configuration
        errors = self.continuous_config.validate_continuous()
        if errors:
            logger.error("Configuration errors", extra={"errors": errors})
            return 1

        async with EventReporter(self.continuous_config) as reporter:
            self.reporter = reporter

            # Report continuous session start
            await reporter.report(
                "continuous.started",
                {
                    "goal": self.continuous_config.initial_prompt,
                    "limits": {
                        "max_runs": self.continuous_config.max_runs,
                        "max_cost_usd": self.continuous_config.max_cost_usd,
                        "max_duration_seconds": self.continuous_config.max_duration_seconds,
                    },
                    "completion_signal": self.continuous_config.completion_signal,
                    "completion_threshold": self.continuous_config.completion_threshold,
                },
                source="worker",
            )

            # Main iteration loop
            while self._should_continue():
                self.iteration_state.iteration_num += 1
                success = await self._run_single_iteration()

                if success:
                    self.iteration_state.successful_iterations += 1
                    self.iteration_state.error_count = 0
                else:
                    self.iteration_state.error_count += 1
                    self.iteration_state.extra_iterations += 1

                    if self.iteration_state.error_count >= 3:
                        await reporter.report(
                            "continuous.completed",
                            {
                                "stop_reason": "consecutive_errors",
                                **self.iteration_state.to_event_data(),
                            },
                        )
                        return 1

            # Report completion
            stop_reason = self._get_stop_reason()
            await reporter.report(
                "continuous.completed",
                {
                    "stop_reason": stop_reason,
                    **self.iteration_state.to_event_data(),
                },
            )

        return 0

    def _should_continue(self) -> bool:
        """Check if iteration should continue."""
        state = self.iteration_state
        config = self.continuous_config

        # Check completion signal threshold
        if state.completion_signal_count >= config.completion_threshold:
            return False

        # Check max runs
        if config.max_runs and state.successful_iterations >= config.max_runs:
            return False

        # Check max cost
        if config.max_cost_usd and state.total_cost >= config.max_cost_usd:
            return False

        # Check max duration
        if config.max_duration_seconds and state.start_time:
            elapsed = time.time() - state.start_time
            if elapsed >= config.max_duration_seconds:
                return False

        # Check shutdown signal
        if self._should_stop:
            return False

        return True

    def _get_stop_reason(self) -> str:
        """Determine why the loop stopped."""
        state = self.iteration_state
        config = self.continuous_config

        if state.completion_signal_count >= config.completion_threshold:
            return "completion_signal"
        if config.max_runs and state.successful_iterations >= config.max_runs:
            return "max_runs_reached"
        if config.max_cost_usd and state.total_cost >= config.max_cost_usd:
            return "max_cost_reached"
        if config.max_duration_seconds and state.start_time:
            elapsed = time.time() - state.start_time
            if elapsed >= config.max_duration_seconds:
                return "max_duration_reached"
        if self._should_stop:
            return "shutdown_signal"
        return "unknown"

    async def _run_single_iteration(self) -> bool:
        """Execute a single iteration.

        Returns True on success, False on error.
        """
        state = self.iteration_state
        config = self.continuous_config

        # Build enhanced prompt with context
        enhanced_prompt = self._build_iteration_prompt()

        # Report iteration start
        await self.reporter.report(
            "iteration.started",
            {
                "iteration_num": state.iteration_num,
                "prompt_preview": enhanced_prompt[:500],
                **state.to_event_data(),
            },
        )

        try:
            # Create SDK options with hooks (reuses parent's method)
            pre_hook = await self._create_pre_tool_hook()
            post_hook = await self._create_post_tool_hook()
            sdk_options = config.to_sdk_options(
                pre_tool_hook=pre_hook,
                post_tool_hook=post_hook,
            )

            # Execute iteration
            async with ClaudeSDKClient(options=sdk_options) as client:
                await client.query(enhanced_prompt)
                result, output = await self._process_messages(client)

                if result:
                    # Track cost and session
                    iteration_cost = getattr(result, "total_cost_usd", 0.0) or 0.0
                    state.total_cost += iteration_cost
                    state.last_session_id = getattr(result, "session_id", None)

                    # Export transcript for cross-sandbox resumption
                    if state.last_session_id:
                        state.last_transcript_b64 = config.export_session_transcript(
                            state.last_session_id
                        )

                    # Check for completion signal
                    output_text = "\n".join(output) if output else ""
                    if config.completion_signal in output_text:
                        state.completion_signal_count += 1
                        await self.reporter.report(
                            "iteration.completion_signal",
                            {
                                "iteration_num": state.iteration_num,
                                "signal_count": state.completion_signal_count,
                                "threshold": config.completion_threshold,
                            },
                        )
                    else:
                        state.completion_signal_count = 0  # Reset on non-signal

                    # Report iteration completion
                    await self.reporter.report(
                        "iteration.completed",
                        {
                            "iteration_num": state.iteration_num,
                            "cost_usd": iteration_cost,
                            "session_id": state.last_session_id,
                            "transcript_b64": state.last_transcript_b64,
                            "output_preview": output_text[:1000] if output_text else None,
                            **state.to_event_data(),
                        },
                    )

                    return True

                else:
                    # Iteration failed (no ResultMessage)
                    await self.reporter.report(
                        "iteration.failed",
                        {
                            "iteration_num": state.iteration_num,
                            "error": "No result message received",
                            "error_type": "no_result",
                            "retry_allowed": state.error_count < 2,
                        },
                    )
                    return False

        except Exception as e:
            await self.reporter.report(
                "iteration.failed",
                {
                    "iteration_num": state.iteration_num,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "retry_allowed": state.error_count < 2,
                },
            )
            return False

    def _build_iteration_prompt(self) -> str:
        """Build enhanced prompt with iteration context."""
        config = self.continuous_config
        state = self.iteration_state

        # Read notes file if exists
        notes_content = ""
        notes_path = Path(config.cwd) / config.notes_file
        if notes_path.exists():
            try:
                notes_content = notes_path.read_text()
            except Exception:
                pass

        # Build enhanced prompt
        prompt_parts = [
            f"## CONTINUOUS WORKFLOW CONTEXT",
            f"",
            f"This is iteration {state.iteration_num} of a continuous development loop.",
            f"Work incrementally across iterations. Update the notes file to preserve context.",
            f"",
            f"**Limits**: max_runs={config.max_runs}, max_cost=${config.max_cost_usd}, ",
            f"max_duration={config.max_duration_seconds}s",
            f"**Progress**: {state.successful_iterations} successful iterations, ",
            f"${state.total_cost:.2f} spent",
            f"",
            f"**Project Completion Signal**: If you determine the ENTIRE project goal is ",
            f"fully complete, include the exact phrase \"{config.completion_signal}\" in your ",
            f"response. This must appear {config.completion_threshold} consecutive times to ",
            f"stop the loop.",
            f"",
            f"## PRIMARY GOAL",
            f"",
            config.initial_prompt or config.ticket_description or "No goal specified",
        ]

        if notes_content:
            prompt_parts.extend([
                f"",
                f"## PREVIOUS ITERATION NOTES",
                f"",
                notes_content,
            ])

        prompt_parts.extend([
            f"",
            f"## NOTES UPDATE INSTRUCTIONS",
            f"",
            f"Update `{config.notes_file}` with:",
            f"- What you accomplished this iteration",
            f"- What remains to be done",
            f"- Any blockers or issues",
            f"- Important context for the next iteration",
        ])

        return "\n".join(prompt_parts)
```

**Key Integration Points:**

1. **Inherits `SandboxWorker`** - Reuses `_process_messages()`, hooks, file tracking
2. **Uses `EventReporter`** - Reports iteration events via HTTP callbacks
3. **Session Portability** - Uses `export_session_transcript()` for cross-sandbox resumption
4. **Notes File** - Provides cross-iteration context similar to bash script
5. **Configurable via Environment** - All settings from environment variables

## CLI Interface

```bash
# Install
pip install claude-agent-sdk

# Run with max iterations
python continuous_claude.py -p "Add unit tests" -m 10

# Run with cost limit
python continuous_claude.py -p "Fix bugs" --max-cost 5.00

# Run with time limit
python continuous_claude.py -p "Refactor" --max-duration 2h

# Combine limits (first reached stops)
python continuous_claude.py -p "Feature work" -m 20 --max-cost 10.00 --max-duration 4h

# Without git integration
python continuous_claude.py -p "Experiment" -m 5 --disable-commits
```

## Comparison: Bash vs Python SDK vs OmoiOS Integration

| Aspect | Bash Script | Python SDK (Standalone) | OmoiOS Integration |
|--------|------------|------------------------|-------------------|
| Subprocess management | Manual | SDK handles internally | SDK handles internally |
| JSON parsing | `jq` dependency | Native Python | Native Python |
| Type safety | None | Full typing with dataclasses | Full typing + Pydantic |
| Async handling | Background processes | Native async/await | Native async/await |
| Cost tracking | Parse JSON output | `ResultMessage.total_cost_usd` | Events to server DB |
| Session management | External tracking | Built-in `resume` option | Cross-sandbox via HTTP |
| Error handling | Exit codes | Exceptions with context | Events + retries |
| Integration | Standalone script | Importable module | Full OmoiOS ecosystem |
| Event reporting | None | Manual implementation | `EventReporter` (HTTP) |
| Message injection | None | Manual implementation | `MessagePoller` |
| File diff tracking | None | Manual implementation | `FileChangeTracker` |
| Dashboard visibility | None | None | Real-time UI updates |

**Key OmoiOS Advantages:**

1. **Real-time Monitoring** - Iteration progress visible in OmoiOS dashboard
2. **Event Persistence** - All iteration events stored in database
3. **Cross-Sandbox Resumption** - Session transcripts portable via HTTP
4. **Human-in-the-Loop** - Inject messages during iterations via `MessagePoller`
5. **File Diffs** - Track changes with `FileChangeTracker` for code review
6. **Existing Infrastructure** - Reuses proven `EventReporter`, hooks, MCP tools

## Future Enhancements

1. **Parallel Execution** - Run multiple Claude instances on different tasks
2. **Worktree Support** - Use git worktrees for parallel git operations
3. **Webhook Notifications** - Send status updates to external services
4. **Structured Outputs** - Use JSON schema for iteration reports
5. **Custom Hooks** - Add pre/post iteration hooks for custom logic
6. **Database Persistence** - Track iteration history in SQLite/PostgreSQL

## Implementation File Location

The implementation should extend the existing `claude_sandbox_worker.py` to maintain code reuse and consistency with the OmoiOS infrastructure.

**Option A: Extend Existing Worker (Recommended)**

Add continuous mode directly to the existing worker:

```
backend/omoi_os/workers/
├── claude_sandbox_worker.py           # Existing worker (add ContinuousWorkerConfig)
├── continuous_sandbox_worker.py       # NEW: ContinuousSandboxWorker class
└── __init__.py                        # Export both workers
```

The worker can be invoked with `CONTINUOUS_MODE=true` to enable iteration:

```bash
# Standard mode (existing behavior)
SANDBOX_ID=xxx CALLBACK_URL=http://... python claude_sandbox_worker.py

# Continuous mode (new behavior)
CONTINUOUS_MODE=true \
CONTINUOUS_MAX_RUNS=10 \
CONTINUOUS_MAX_COST_USD=5.00 \
SANDBOX_ID=xxx \
CALLBACK_URL=http://... \
python continuous_sandbox_worker.py
```

**Option B: Standalone Script**

If standalone usage is needed (without OmoiOS backend):

```
scripts/continuous_claude/
├── __init__.py
├── continuous_claude.py      # Standalone implementation (copies EventReporter)
├── config.py                 # Standalone configuration
└── README.md                 # Usage documentation
```

**Recommended Approach**: Option A - extend existing worker to maximize code reuse.

## Server-Side Integration

The OmoiOS main server needs endpoints to receive iteration events:

```python
# Already exists in api/v1/sandboxes.py
POST /api/v1/sandboxes/{sandbox_id}/events

# Event types to handle:
# - continuous.started
# - continuous.completed
# - continuous.limit_reached
# - iteration.started
# - iteration.completed
# - iteration.failed
# - iteration.completion_signal
```

**Database Schema Extension (Optional):**

If tracking iteration history is desired:

```sql
CREATE TABLE continuous_iterations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id UUID REFERENCES sandboxes(id),
    iteration_num INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'completed', 'failed'
    cost_usd DECIMAL(10, 4),
    session_id VARCHAR(255),
    transcript_b64 TEXT,  -- For cross-sandbox resumption
    output_preview TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_continuous_iterations_sandbox ON continuous_iterations(sandbox_id);
```

## References

- [Claude Agent SDK Python](https://github.com/anthropics/claude-agent-sdk-python)
- [Original continuous-claude bash script](https://github.com/AnandChowdhary/continuous-claude)
- [SDK Documentation](https://deepwiki.com/anthropics/claude-agent-sdk-python)
- [Existing Worker Implementation](../backend/omoi_os/workers/claude_sandbox_worker.py)
