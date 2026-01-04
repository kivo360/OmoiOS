#!/usr/bin/env python3
"""
Continuous Sandbox Worker - Iterative Claude execution until task completion.

This worker extends the base SandboxWorker to run Claude Code in a continuous
loop until the task is truly complete (code pushed, PR created) or limits are hit.

The iteration loop:
1. Executes the task with enhanced prompt including context
2. Checks for completion signal in output
3. Validates work is done (tests pass, code pushed, PR exists)
4. If not complete, continues with updated context
5. Stops when: completion signal threshold reached, limits hit, or validation passes

Environment Variables (extends base worker):
    CONTINUOUS_MODE         - Set to "true" to enable continuous iteration
    CONTINUOUS_MAX_RUNS     - Maximum successful iterations (default: 10)
    CONTINUOUS_MAX_COST_USD - Maximum total cost in USD (default: 20.0)
    CONTINUOUS_MAX_DURATION - Maximum duration in seconds (default: 3600)
    CONTINUOUS_COMPLETION_SIGNAL - Phrase to detect completion (default: TASK_COMPLETE)
    CONTINUOUS_COMPLETION_THRESHOLD - Consecutive signals to stop (default: 2)
    CONTINUOUS_NOTES_FILE   - Notes file for context sharing (default: ITERATION_NOTES.md)
    CONTINUOUS_AUTO_VALIDATE - Auto-validate git status after completion signal (default: true)

See docs/design/continuous_claude_sdk.md for full design documentation.
"""

import asyncio
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from omoi_os.workers.claude_sandbox_worker import (
    SandboxWorker,
    WorkerConfig,
    EventReporter,
    MessagePoller,
    ClaudeSDKClient,
    SDK_AVAILABLE,
    logger,
)


# =============================================================================
# Continuous Worker Configuration
# =============================================================================


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

        # Enable continuous mode flag
        self.continuous_mode = os.environ.get("CONTINUOUS_MODE", "false").lower() == "true"

        # Iteration limits (at least one should be set for safety)
        self.max_runs: Optional[int] = self._get_int_env("CONTINUOUS_MAX_RUNS", 10)
        self.max_cost_usd: Optional[float] = self._get_float_env("CONTINUOUS_MAX_COST_USD", 20.0)
        self.max_duration_seconds: Optional[int] = self._get_int_env("CONTINUOUS_MAX_DURATION", 3600)

        # Completion detection
        self.completion_signal = os.environ.get(
            "CONTINUOUS_COMPLETION_SIGNAL",
            "TASK_COMPLETE"
        )
        self.completion_threshold = int(os.environ.get("CONTINUOUS_COMPLETION_THRESHOLD", "2"))

        # Notes file for cross-iteration context
        self.notes_file = os.environ.get("CONTINUOUS_NOTES_FILE", "ITERATION_NOTES.md")

        # Auto-validate git status after completion signal
        self.auto_validate = os.environ.get("CONTINUOUS_AUTO_VALIDATE", "true").lower() == "true"

        # Git validation requirements
        self.require_clean_git = os.environ.get("CONTINUOUS_REQUIRE_CLEAN_GIT", "true").lower() == "true"
        self.require_pushed = os.environ.get("CONTINUOUS_REQUIRE_PUSHED", "true").lower() == "true"
        self.require_pr = os.environ.get("CONTINUOUS_REQUIRE_PR", "true").lower() == "true"

    def _get_int_env(self, key: str, default: Optional[int] = None) -> Optional[int]:
        val = os.environ.get(key)
        if val:
            return int(val)
        return default

    def _get_float_env(self, key: str, default: Optional[float] = None) -> Optional[float]:
        val = os.environ.get(key)
        if val:
            return float(val)
        return default

    def validate_continuous(self) -> list[str]:
        """Validate continuous-specific configuration."""
        errors = super().validate()

        # At least one limit must be set for safety
        if not any([self.max_runs, self.max_cost_usd, self.max_duration_seconds]):
            errors.append(
                "At least one limit required: CONTINUOUS_MAX_RUNS, "
                "CONTINUOUS_MAX_COST_USD, or CONTINUOUS_MAX_DURATION"
            )

        return errors

    def to_dict(self) -> dict:
        """Return config as dict including continuous settings."""
        base = super().to_dict()
        base.update({
            "continuous_mode": self.continuous_mode,
            "max_runs": self.max_runs,
            "max_cost_usd": self.max_cost_usd,
            "max_duration_seconds": self.max_duration_seconds,
            "completion_signal": self.completion_signal,
            "completion_threshold": self.completion_threshold,
            "notes_file": self.notes_file,
            "auto_validate": self.auto_validate,
            "require_clean_git": self.require_clean_git,
            "require_pushed": self.require_pushed,
            "require_pr": self.require_pr,
        })
        return base


# =============================================================================
# Iteration State Tracking
# =============================================================================


@dataclass
class IterationState:
    """Tracks state across iterations."""

    iteration_num: int = 0                    # Current iteration
    successful_iterations: int = 0            # Completed successfully
    error_count: int = 0                      # Consecutive errors
    extra_iterations: int = 0                 # Added due to errors
    total_cost: float = 0.0                   # Accumulated cost
    completion_signal_count: int = 0          # Consecutive completion signals
    start_time: Optional[float] = None        # For duration tracking
    last_session_id: Optional[str] = None     # For potential resume
    last_transcript_b64: Optional[str] = None  # For cross-sandbox resumption
    validation_passed: bool = False           # Whether git validation passed
    validation_feedback: str = ""             # Feedback from validation

    # Track what's been accomplished
    tests_passed: bool = False
    code_committed: bool = False
    code_pushed: bool = False
    pr_created: bool = False

    # Additional PR/CI info for artifact generation
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    files_changed: int = 0
    ci_status: Optional[list] = None

    def to_event_data(self) -> dict:
        """Convert state to event payload for EventReporter."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            "iteration_num": self.iteration_num,
            "successful_iterations": self.successful_iterations,
            "error_count": self.error_count,
            "extra_iterations": self.extra_iterations,
            "total_cost_usd": self.total_cost,
            "completion_signal_count": self.completion_signal_count,
            "elapsed_seconds": elapsed,
            "last_session_id": self.last_session_id,
            "validation_passed": self.validation_passed,
            "tests_passed": self.tests_passed,
            "code_committed": self.code_committed,
            "code_pushed": self.code_pushed,
            "pr_created": self.pr_created,
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "files_changed": self.files_changed,
            "ci_status": self.ci_status,
        }


# =============================================================================
# Git Validation
# =============================================================================


def check_git_status(cwd: str) -> dict[str, Any]:
    """Check git status for validation.

    Returns dict with:
    - is_clean: No uncommitted changes
    - is_pushed: Not ahead of remote
    - has_pr: PR exists for current branch
    - branch_name: Current branch
    - status_output: Raw git status output
    - errors: List of validation errors
    - ci_status: CI check results (if PR exists)
    - tests_passed: Whether all CI checks passed
    - pr_url: URL of the PR (if exists)
    - pr_number: PR number (if exists)
    - files_changed: Number of files changed in PR
    """
    result = {
        "is_clean": False,
        "is_pushed": False,
        "has_pr": False,
        "branch_name": None,
        "status_output": "",
        "errors": [],
        "ci_status": None,
        "tests_passed": False,
        "pr_url": None,
        "pr_number": None,
        "files_changed": 0,
    }

    try:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if branch_result.returncode == 0:
            result["branch_name"] = branch_result.stdout.strip()

        # Check git status
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        result["status_output"] = status_result.stdout
        result["is_clean"] = status_result.returncode == 0 and not status_result.stdout.strip()

        if not result["is_clean"]:
            result["errors"].append("Uncommitted changes detected")

        # Check if ahead of remote
        status_verbose = subprocess.run(
            ["git", "status"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        status_text = status_verbose.stdout

        # Check for "Your branch is ahead" message
        if "Your branch is ahead" in status_text:
            result["is_pushed"] = False
            result["errors"].append("Code not pushed to remote")
        elif "Your branch is up to date" in status_text or "nothing to commit" in status_text:
            result["is_pushed"] = True
        else:
            # If we can't determine, assume it's pushed
            result["is_pushed"] = True

        # Check for PR using gh CLI
        try:
            pr_result = subprocess.run(
                ["gh", "pr", "view", "--json", "number,title,state,url,changedFiles"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if pr_result.returncode == 0 and pr_result.stdout.strip():
                result["has_pr"] = True
                # Parse PR info
                try:
                    import json
                    pr_data = json.loads(pr_result.stdout)
                    result["pr_number"] = pr_data.get("number")
                    result["pr_url"] = pr_data.get("url")
                    result["files_changed"] = pr_data.get("changedFiles", 0)
                except json.JSONDecodeError:
                    pass

                # Check CI status if PR exists
                ci_result = subprocess.run(
                    ["gh", "pr", "checks", "--json", "name,state,conclusion"],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if ci_result.returncode == 0 and ci_result.stdout.strip():
                    try:
                        ci_checks = json.loads(ci_result.stdout)
                        result["ci_status"] = ci_checks

                        # Determine if all checks passed
                        if ci_checks:
                            all_passed = all(
                                check.get("conclusion") == "success"
                                or check.get("state") == "pending"  # Allow pending
                                for check in ci_checks
                            )
                            # But require at least one completed success
                            has_success = any(
                                check.get("conclusion") == "success"
                                for check in ci_checks
                            )
                            result["tests_passed"] = all_passed and has_success
                        else:
                            # No CI checks configured - assume tests pass
                            # (project may not have CI)
                            result["tests_passed"] = True
                    except json.JSONDecodeError:
                        # Can't parse CI status, assume no CI configured
                        result["tests_passed"] = True
                else:
                    # gh pr checks failed - might be no checks configured
                    # This is okay, not all repos have CI
                    result["tests_passed"] = True
            else:
                result["has_pr"] = False
                result["errors"].append("No PR found for current branch")
        except FileNotFoundError:
            # gh CLI not installed
            result["errors"].append("GitHub CLI (gh) not available to check PR status")
        except subprocess.TimeoutExpired:
            result["errors"].append("Timeout checking PR status")

    except subprocess.TimeoutExpired:
        result["errors"].append("Timeout running git commands")
    except Exception as e:
        result["errors"].append(f"Git validation error: {str(e)}")

    return result


# =============================================================================
# Continuous Sandbox Worker
# =============================================================================


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
    - Git validation (tests pass, code pushed, PR exists)
    - Cross-iteration context via notes file
    - Per-iteration event reporting
    """

    def __init__(self, config: ContinuousWorkerConfig):
        super().__init__(config)
        self.continuous_config = config
        self.iteration_state = IterationState()

    async def run(self):
        """Main entry point - runs continuous or single mode based on config."""
        if self.continuous_config.continuous_mode:
            return await self.run_continuous()
        else:
            # Fall back to standard single-run mode
            return await super().run()

    async def run_continuous(self):
        """Main continuous execution loop."""
        self._setup_signal_handlers()
        self.running = True
        self.iteration_state.start_time = time.time()

        logger.info("=" * 60)
        logger.info("CONTINUOUS SANDBOX WORKER")
        logger.info("=" * 60)
        logger.info("Configuration: %s", self.continuous_config.to_dict())

        # Validate continuous configuration
        errors = self.continuous_config.validate_continuous()
        if errors:
            logger.error("Configuration errors", extra={"errors": errors})
            return 1

        if not SDK_AVAILABLE:
            logger.error("claude_agent_sdk package not installed - Run: pip install claude-agent-sdk")
            return 1

        # Setup workspace
        Path(self.continuous_config.cwd).mkdir(parents=True, exist_ok=True)

        async with EventReporter(self.continuous_config) as reporter:
            self.reporter = reporter

            # Report continuous session start
            await reporter.report(
                "continuous.started",
                {
                    "goal": self.continuous_config.task_description
                            or self.continuous_config.initial_prompt
                            or self.continuous_config.ticket_description,
                    "limits": {
                        "max_runs": self.continuous_config.max_runs,
                        "max_cost_usd": self.continuous_config.max_cost_usd,
                        "max_duration_seconds": self.continuous_config.max_duration_seconds,
                    },
                    "completion_signal": self.continuous_config.completion_signal,
                    "completion_threshold": self.continuous_config.completion_threshold,
                    "validation_requirements": {
                        "require_clean_git": self.continuous_config.require_clean_git,
                        "require_pushed": self.continuous_config.require_pushed,
                        "require_pr": self.continuous_config.require_pr,
                    },
                },
                source="worker",
            )

            async with MessagePoller(self.continuous_config) as poller:
                # Main iteration loop
                while self._should_continue():
                    self.iteration_state.iteration_num += 1

                    # Check for injected messages (user intervention)
                    messages = await poller.poll()
                    for msg in messages:
                        content = msg.get("content", "")
                        msg_type = msg.get("message_type", "user_message")

                        if msg_type == "interrupt":
                            logger.info("Received interrupt message")
                            self._should_stop = True
                            break
                        elif content:
                            # Store user message for next iteration
                            self._inject_user_context(content)

                    if self._should_stop:
                        break

                    success = await self._run_single_iteration()

                    if success:
                        self.iteration_state.successful_iterations += 1
                        self.iteration_state.error_count = 0

                        # If validation passed, we're truly done
                        if self.iteration_state.validation_passed:
                            logger.info("Validation passed - task complete!")
                            break
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

                logger.info(
                    "Continuous worker completed",
                    extra={
                        "stop_reason": stop_reason,
                        "iterations": self.iteration_state.iteration_num,
                        "successful": self.iteration_state.successful_iterations,
                        "total_cost": self.iteration_state.total_cost,
                    }
                )

        return 0

    def _should_continue(self) -> bool:
        """Check if iteration should continue."""
        state = self.iteration_state
        config = self.continuous_config

        # Check if validation already passed
        if state.validation_passed:
            return False

        # Check completion signal threshold
        if state.completion_signal_count >= config.completion_threshold:
            # If auto-validate is enabled, only stop if validation passed
            if config.auto_validate and not state.validation_passed:
                # Continue to allow agent to fix issues
                logger.info("Completion signal reached but validation not passed - continuing")
                state.completion_signal_count = 0  # Reset to allow more iterations
            else:
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

        if state.validation_passed:
            return "validation_passed"
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

    def _inject_user_context(self, content: str):
        """Store user message to include in next iteration prompt."""
        # Append to notes file for next iteration
        notes_path = Path(self.continuous_config.cwd) / self.continuous_config.notes_file
        try:
            existing = notes_path.read_text() if notes_path.exists() else ""
            timestamp = datetime.now(timezone.utc).isoformat()
            new_content = f"{existing}\n\n## User Message ({timestamp})\n\n{content}\n"
            notes_path.write_text(new_content)
        except Exception as e:
            logger.warning("Failed to inject user context", extra={"error": str(e)})

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
                        logger.info(
                            "Completion signal detected",
                            extra={
                                "count": state.completion_signal_count,
                                "threshold": config.completion_threshold,
                            }
                        )

                        await self.reporter.report(
                            "iteration.completion_signal",
                            {
                                "iteration_num": state.iteration_num,
                                "signal_count": state.completion_signal_count,
                                "threshold": config.completion_threshold,
                            },
                        )

                        # Run git validation if auto-validate enabled
                        if config.auto_validate:
                            await self._run_validation()
                    else:
                        state.completion_signal_count = 0  # Reset on non-signal

                    # Report iteration completion
                    await self.reporter.report(
                        "iteration.completed",
                        {
                            "iteration_num": state.iteration_num,
                            "cost_usd": iteration_cost,
                            "session_id": state.last_session_id,
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
            logger.error("Iteration failed", extra={"error": str(e)}, exc_info=True)
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

    async def _run_validation(self):
        """Run git validation to check if work is truly complete.

        Handles two scenarios:
        1. Implementation tasks: Require clean git, code pushed, and PR created
        2. Research/analysis tasks: No code changes, so skip git validation

        Detection of research tasks:
        - Working directory is clean (no changes made)
        - Not ahead of remote (nothing to push)
        - On main/master branch (no feature branch created)
        - OR execution_mode is "exploration"
        """
        state = self.iteration_state
        config = self.continuous_config

        logger.info("Running git validation...")

        git_status = check_git_status(config.cwd)

        # Update state with validation results
        state.code_committed = git_status["is_clean"]
        state.code_pushed = git_status["is_pushed"]
        state.pr_created = git_status["has_pr"]
        state.tests_passed = git_status["tests_passed"]

        # Store additional PR info for artifact generation
        state.pr_url = git_status.get("pr_url")
        state.pr_number = git_status.get("pr_number")
        state.files_changed = git_status.get("files_changed", 0)
        state.ci_status = git_status.get("ci_status")

        # CRITICAL: Detect research/analysis tasks that don't produce code changes
        # These tasks should pass validation without requiring a PR
        # A task is "research only" if:
        # 1. Working directory is clean (no uncommitted changes)
        # 2. Not ahead of remote (nothing to push)
        # 3. On main/master branch (no feature branch was created)
        # This applies to ALL modes - if no files were created, no git workflow needed
        is_research_task = (
            # Clean working directory (no uncommitted changes)
            git_status["is_clean"] and
            # Not ahead of remote (nothing to push)
            git_status["is_pushed"] and
            # On main/master branch (no feature branch was created)
            git_status.get("branch_name") in ("main", "master", None)
        )

        # NOTE: exploration mode NO LONGER auto-passes validation
        # If exploration creates files (specs, PRDs, docs), it must push them
        # Only pure analysis with no file output passes without git workflow

        if is_research_task:
            logger.info(
                "Detected research/analysis task - no code changes needed",
                extra={
                    "branch": git_status.get("branch_name"),
                    "is_clean": git_status["is_clean"],
                    "is_pushed": git_status["is_pushed"],
                }
            )
            state.validation_passed = True
            state.validation_feedback = "Research/analysis task completed - no code changes required"

            # Report validation result for research task
            await self.reporter.report(
                "iteration.validation",
                {
                    "iteration_num": state.iteration_num,
                    "passed": True,
                    "feedback": state.validation_feedback,
                    "task_type": "research",
                    "git_status": {
                        "is_clean": git_status["is_clean"],
                        "is_pushed": git_status["is_pushed"],
                        "has_pr": git_status["has_pr"],
                        "branch_name": git_status["branch_name"],
                    },
                    "errors": [],
                },
            )
            return

        # Standard validation for implementation tasks
        validation_errors = []

        if config.require_clean_git and not git_status["is_clean"]:
            validation_errors.append("Uncommitted changes exist")

        if config.require_pushed and not git_status["is_pushed"]:
            validation_errors.append("Code not pushed to remote")

        if config.require_pr and not git_status["has_pr"]:
            validation_errors.append("No PR created")

        if not validation_errors:
            state.validation_passed = True
            state.validation_feedback = "All validation checks passed"
            logger.info("Git validation PASSED")
        else:
            state.validation_passed = False
            state.validation_feedback = "; ".join(validation_errors)
            logger.info(
                "Git validation FAILED",
                extra={"errors": validation_errors}
            )

            # Update notes file with validation feedback for next iteration
            self._update_notes_with_validation(validation_errors, git_status)

        # Report validation result
        await self.reporter.report(
            "iteration.validation",
            {
                "iteration_num": state.iteration_num,
                "passed": state.validation_passed,
                "feedback": state.validation_feedback,
                "git_status": {
                    "is_clean": git_status["is_clean"],
                    "is_pushed": git_status["is_pushed"],
                    "has_pr": git_status["has_pr"],
                    "branch_name": git_status["branch_name"],
                },
                "errors": validation_errors,
            },
        )

    def _update_notes_with_validation(self, errors: list[str], git_status: dict):
        """Update notes file with validation feedback for next iteration."""
        config = self.continuous_config
        notes_path = Path(config.cwd) / config.notes_file

        try:
            existing = notes_path.read_text() if notes_path.exists() else ""

            feedback_section = f"""

## VALIDATION FAILED - Iteration {self.iteration_state.iteration_num}

The completion signal was detected, but validation checks failed.
**You must fix these issues before the task is truly complete:**

### Issues Found:
"""
            for error in errors:
                feedback_section += f"- ❌ {error}\n"

            feedback_section += f"""
### Git Status:
- Branch: {git_status.get('branch_name', 'unknown')}
- Clean working directory: {'✅ Yes' if git_status['is_clean'] else '❌ No'}
- Code pushed to remote: {'✅ Yes' if git_status['is_pushed'] else '❌ No'}
- PR exists: {'✅ Yes' if git_status['has_pr'] else '❌ No'}

### Required Actions:
"""
            if not git_status["is_clean"]:
                feedback_section += "1. Stage and commit all changes: `git add -A && git commit -m \"...\"`\n"
            if not git_status["is_pushed"]:
                feedback_section += "2. Push code to remote: `git push`\n"
            if not git_status["has_pr"]:
                feedback_section += "3. Create a pull request: `gh pr create --title \"...\" --body \"...\"`\n"

            feedback_section += f"""
**After fixing these issues, include `{config.completion_signal}` in your response again.**
"""

            notes_path.write_text(existing + feedback_section)

        except Exception as e:
            logger.warning("Failed to update notes with validation feedback", extra={"error": str(e)})

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

        # Get the primary goal
        primary_goal = (
            config.task_description
            or config.initial_prompt
            or config.ticket_description
            or "No goal specified"
        )

        # Calculate remaining budget
        remaining_cost = None
        if config.max_cost_usd:
            remaining_cost = config.max_cost_usd - state.total_cost

        remaining_runs = None
        if config.max_runs:
            remaining_runs = config.max_runs - state.successful_iterations

        # Build enhanced prompt
        prompt_parts = [
            "## CONTINUOUS WORKFLOW CONTEXT",
            "",
            f"This is **iteration {state.iteration_num}** of a continuous development loop.",
            "Work incrementally. The loop continues until all requirements are met.",
            "",
        ]

        # Add progress info
        prompt_parts.extend([
            "### Current Progress:",
            f"- Successful iterations: {state.successful_iterations}",
            f"- Cost spent: ${state.total_cost:.2f}",
        ])

        if remaining_cost is not None:
            prompt_parts.append(f"- Remaining budget: ${remaining_cost:.2f}")
        if remaining_runs is not None:
            prompt_parts.append(f"- Remaining runs: {remaining_runs}")

        prompt_parts.extend([
            "",
            "### Completion Requirements:",
            "For your work to be considered complete, you MUST:",
            "1. ✅ Implement the requested changes",
            "2. ✅ Run tests and ensure they pass",
            "3. ✅ Commit all changes (no uncommitted files)",
            "4. ✅ Push code to remote (`git push`)",
            "5. ✅ Create a Pull Request (`gh pr create ...`)",
            "",
            f"**Completion Signal**: When ALL requirements are met, include the exact phrase:",
            f"**`{config.completion_signal}`**",
            "",
            "The system will validate your work. If validation fails, you'll continue",
            "with specific feedback about what needs to be fixed.",
            "",
        ])

        # Add primary goal
        prompt_parts.extend([
            "## PRIMARY GOAL",
            "",
            primary_goal,
            "",
        ])

        # Add previous iteration notes if they exist
        if notes_content:
            prompt_parts.extend([
                "## PREVIOUS ITERATION NOTES",
                "",
                notes_content,
                "",
            ])

        # Add notes update instructions
        prompt_parts.extend([
            "## NOTES UPDATE INSTRUCTIONS",
            "",
            f"Update `{config.notes_file}` with:",
            "- What you accomplished this iteration",
            "- What remains to be done",
            "- Any blockers or issues",
            "- Important context for the next iteration",
            "",
        ])

        return "\n".join(prompt_parts)


# =============================================================================
# Entry Point
# =============================================================================


async def main():
    """Entry point for continuous sandbox worker."""
    config = ContinuousWorkerConfig()
    worker = ContinuousSandboxWorker(config)
    return await worker.run()


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
