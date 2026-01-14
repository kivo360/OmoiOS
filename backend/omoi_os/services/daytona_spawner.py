"""Daytona Spawner Service for OmoiOS.

This service manages the lifecycle of Daytona sandboxes for agent execution.
It's the bridge between the orchestrator and isolated agent execution.

The spawner:
1. Creates Daytona sandboxes with proper environment variables
2. Tracks active sandboxes and their associated tasks
3. Cleans up sandboxes when tasks complete
4. Provides health monitoring for running sandboxes
"""

import asyncio
import shlex
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from omoi_os.config import load_daytona_settings, get_app_settings
from omoi_os.logging import get_logger
from omoi_os.sandbox_skills import get_skills_for_upload
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

# TYPE_CHECKING import for TaskRequirements to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omoi_os.services.task_requirements_analyzer import TaskRequirements

logger = get_logger(__name__)


@dataclass
class SandboxInfo:
    """Information about a spawned sandbox."""

    sandbox_id: str
    agent_id: str
    task_id: str
    phase_id: str
    status: str = "creating"  # creating, running, completed, failed, terminated
    created_at: datetime = field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)


class DaytonaSpawnerService:
    """Service for spawning and managing Daytona sandboxes.

    This service creates isolated execution environments for agents,
    passing the necessary configuration via environment variables.

    Usage:
        spawner = DaytonaSpawnerService(db, event_bus, mcp_server_url="http://localhost:18000/mcp")

        # Spawn a sandbox for a task
        sandbox_id = await spawner.spawn_for_task(
            task_id="task-123",
            agent_id="agent-456",
            phase_id="PHASE_IMPLEMENTATION"
        )

        # Check sandbox status
        info = spawner.get_sandbox_info(sandbox_id)

        # Terminate when done
        await spawner.terminate_sandbox(sandbox_id)
    """

    def __init__(
        self,
        db: Optional[DatabaseService] = None,
        event_bus: Optional[EventBusService] = None,
        mcp_server_url: str = "http://localhost:18000/mcp/",
        daytona_api_key: Optional[str] = None,
        daytona_api_url: str = "https://app.daytona.io/api",
        sandbox_image: Optional[str] = "nikolaik/python-nodejs:python3.12-nodejs22",
        sandbox_snapshot: Optional[str] = None,
        auto_cleanup: bool = True,
        sandbox_memory_gb: int = 4,
        sandbox_cpu: int = 2,
        sandbox_disk_gb: int = 8,
    ):
        """Initialize the spawner service.

        Args:
            db: Database service for persisting sandbox info
            event_bus: Event bus for publishing sandbox events
            mcp_server_url: URL of the MCP server sandboxes connect to
            daytona_api_key: Daytona API key (or from settings)
            daytona_api_url: Daytona API URL
            sandbox_image: Docker image for sandboxes (used if sandbox_snapshot is None)
            sandbox_snapshot: Snapshot name to create sandbox from (takes precedence over image)
            auto_cleanup: Automatically cleanup sandboxes on completion
            sandbox_memory_gb: Memory allocation in GiB (default: 4, max: 8)
            sandbox_cpu: CPU cores (default: 2, max: 4)
            sandbox_disk_gb: Disk space in GiB (default: 8, max: 10)
        """
        self.db = db
        self.event_bus = event_bus
        self.mcp_server_url = mcp_server_url
        self.sandbox_image = sandbox_image
        self.sandbox_snapshot = sandbox_snapshot
        self.auto_cleanup = auto_cleanup
        # Load Daytona settings for defaults
        daytona_settings = load_daytona_settings()
        self.daytona_api_key = daytona_api_key or daytona_settings.api_key
        self.daytona_api_url = daytona_api_url or daytona_settings.api_url

        # Use config file values if not explicitly provided
        if self.sandbox_snapshot is None:
            self.sandbox_snapshot = daytona_settings.snapshot
        if self.sandbox_image is None:
            self.sandbox_image = (
                daytona_settings.image or "nikolaik/python-nodejs:python3.12-nodejs22"
            )

        # Override resource limits from config file (config takes precedence over parameter defaults)
        # This allows YAML config to override the default parameter values
        self.sandbox_memory_gb = min(daytona_settings.sandbox_memory_gb, 8)
        self.sandbox_cpu = min(daytona_settings.sandbox_cpu, 4)
        self.sandbox_disk_gb = min(daytona_settings.sandbox_disk_gb, 10)

        # In-memory tracking of active sandboxes
        self._sandboxes: Dict[str, SandboxInfo] = {}
        self._task_to_sandbox: Dict[str, str] = {}  # task_id -> sandbox_id

    async def spawn_for_task(
        self,
        task_id: str,
        agent_id: str,
        phase_id: str,
        agent_type: Optional[str] = None,
        extra_env: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        runtime: str = "openhands",  # "openhands" or "claude"
        execution_mode: str = "implementation",  # "exploration", "implementation", "validation"
        continuous_mode: Optional[
            bool
        ] = None,  # None = auto-enable for implementation/validation
        task_requirements: Optional[
            "TaskRequirements"
        ] = None,  # LLM-analyzed requirements
        require_spec_skill: bool = False,  # Force spec-driven-dev skill usage
        project_id: Optional[str] = None,  # Project ID for spec CLI
        omoios_api_key: Optional[str] = None,  # API key for spec CLI authentication
    ) -> str:
        """Spawn a Daytona sandbox for executing a task.

        Args:
            task_id: ID of the task to execute
            agent_id: ID of the agent executing
            phase_id: Current phase ID
            agent_type: Optional agent type override
            extra_env: Additional environment variables
            labels: Labels for the sandbox
            runtime: Agent runtime to use - "openhands" (default) or "claude"
            execution_mode: Skill loading mode - determines which skills are loaded
                - "exploration": For feature definition (creates specs/tickets/tasks)
                - "implementation": For task execution (writes code, default)
                - "validation": For verifying implementation
            continuous_mode: Enable continuous iteration until task is complete
                (code pushed, PR created) or limits are reached. Only works with
                runtime="claude".
                - None (default): Auto-enable for implementation/validation modes
                - True: Force enable
                - False: Force disable
            task_requirements: Optional LLM-analyzed TaskRequirements object.
                When provided, these settings override execution_mode-based defaults
                for git validation requirements (commit, push, PR).
            require_spec_skill: When True, enforces spec-driven-dev skill usage:
                - Injects skill content directly into system prompt
                - Validates spec output format before task completion
                - Fails task if .omoi_os/ files lack proper frontmatter
            project_id: Project ID for spec CLI to sync specs/tickets. Required for
                spec-driven-dev skill to function properly.
            omoios_api_key: API key for authenticating with OmoiOS API. If not provided,
                falls back to LLM_API_KEY from settings.

        Returns:
            Sandbox ID

        Raises:
            RuntimeError: If sandbox creation fails
        """
        # Log ALL incoming parameters at the start for full traceability
        logger.info(
            "[SPAWNER] spawn_for_task called",
            extra={
                "task_id": task_id,
                "agent_id": agent_id,
                "phase_id": phase_id,
                "agent_type": agent_type,
                "runtime": runtime,
                "execution_mode": execution_mode,
                "continuous_mode": continuous_mode,
                "require_spec_skill": require_spec_skill,
                "project_id": project_id,
                "has_omoios_api_key": omoios_api_key is not None,
                "has_extra_env": extra_env is not None,
                "has_labels": labels is not None,
                "has_task_requirements": task_requirements is not None,
            },
        )

        if not self.daytona_api_key:
            raise RuntimeError("Daytona API key not configured")

        # Check if task already has a sandbox
        if task_id in self._task_to_sandbox:
            existing_id = self._task_to_sandbox[task_id]
            existing = self._sandboxes.get(existing_id)
            if existing and existing.status in ("creating", "running"):
                logger.warning(
                    f"Task {task_id} already has active sandbox {existing_id}"
                )
                return existing_id

        # Generate sandbox ID
        sandbox_id = f"omoios-{task_id[:8]}-{uuid4().hex[:6]}"

        # Build environment variables
        # Derive base URL from MCP server URL (remove /mcp suffix if present)
        base_url = self.mcp_server_url.replace("/mcp", "").rstrip("/")

        env_vars = {
            "AGENT_ID": agent_id,
            "TASK_ID": task_id,
            "EXECUTION_MODE": execution_mode,  # Controls prompt and skill behavior
            "MCP_SERVER_URL": self.mcp_server_url,
            "CALLBACK_URL": base_url,  # For EventReporter to use correct API URL
            "PHASE_ID": phase_id,
            "SANDBOX_ID": sandbox_id,
            # IS_SANDBOX=1 tells Claude Code it's running in a secure sandbox,
            # allowing --dangerously-skip-permissions to work even as root
            "IS_SANDBOX": "1",
            # Spec CLI env vars - API URL for syncing specs/tickets/tasks
            "OMOIOS_API_URL": base_url,
        }

        # Add spec skill enforcement if requested (from frontend dropdown)
        # This is the critical path for spec-driven development mode
        if require_spec_skill:
            env_vars["REQUIRE_SPEC_SKILL"] = "true"
            logger.info(
                "[SPEC-SKILL] ✅ Spec skill enforcement ENABLED for sandbox",
                extra={
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "execution_mode": execution_mode,
                    "sandbox_id": sandbox_id,
                    "project_id": project_id,
                },
            )
        else:
            logger.info(
                "[SPEC-SKILL] ❌ Spec skill enforcement DISABLED (require_spec_skill=False)",
                extra={
                    "task_id": task_id,
                    "execution_mode": execution_mode,
                },
            )

        # Add spec CLI env vars for syncing specs/tickets/tasks
        # These are needed for the spec-driven-dev skill to work properly
        if project_id:
            env_vars["OMOIOS_PROJECT_ID"] = project_id
            logger.info(
                "[SPEC-SKILL] Project ID set for spec CLI",
                extra={"project_id": project_id, "task_id": task_id},
            )
        elif require_spec_skill:
            # Warn if spec skill is enabled but no project_id
            logger.warning(
                "[SPEC-SKILL] ⚠️ require_spec_skill=true but NO project_id provided! "
                "Spec sync will fail without project_id.",
                extra={"task_id": task_id},
            )

        # Get API key from parameter or fall back to LLM settings
        api_key_source = None
        if omoios_api_key:
            env_vars["OMOIOS_API_KEY"] = omoios_api_key
            api_key_source = "parameter"
        else:
            # Fall back to LLM API key from settings
            from omoi_os.config import get_app_settings

            app_settings = get_app_settings()
            if app_settings.llm.api_key:
                env_vars["OMOIOS_API_KEY"] = app_settings.llm.api_key
                api_key_source = "llm_settings"

        if require_spec_skill:
            logger.info(
                "[SPEC-SKILL] API key configured for spec CLI",
                extra={
                    "api_key_source": api_key_source or "NOT_SET",
                    "has_api_key": api_key_source is not None,
                    "task_id": task_id,
                },
            )

        # Determine continuous mode:
        # - None (default): Auto-enable for implementation/validation modes with Claude runtime
        # - True: Force enable
        # - False: Force disable
        effective_continuous_mode = continuous_mode
        logger.info(
            "SPAWNER: Continuous mode decision",
            extra={
                "continuous_mode_param": continuous_mode,
                "runtime": runtime,
                "execution_mode": execution_mode,
                "task_id": task_id,
            },
        )
        if continuous_mode is None and runtime == "claude":
            # Auto-enable for implementation and validation modes
            # These modes need to ensure tasks complete fully (code pushed, PR created)
            effective_continuous_mode = execution_mode in (
                "implementation",
                "validation",
            )
            logger.info(
                "SPAWNER: Auto-determined continuous mode",
                extra={
                    "effective_continuous_mode": effective_continuous_mode,
                    "execution_mode": execution_mode,
                    "is_implementation_or_validation": execution_mode
                    in ("implementation", "validation"),
                },
            )

        # Add continuous mode settings if enabled
        if effective_continuous_mode and runtime == "claude":
            env_vars["CONTINUOUS_MODE"] = "true"
            # Default limits for continuous mode (can be overridden via extra_env)
            env_vars.setdefault("MAX_ITERATIONS", "10")
            env_vars.setdefault("MAX_TOTAL_COST_USD", "20.0")
            env_vars.setdefault("MAX_DURATION_SECONDS", "3600")  # 1 hour
            logger.info(
                "SPAWNER: Continuous mode ENABLED",
                extra={
                    "max_iterations": env_vars.get("MAX_ITERATIONS"),
                    "max_cost_usd": env_vars.get("MAX_TOTAL_COST_USD"),
                    "max_duration_seconds": env_vars.get("MAX_DURATION_SECONDS"),
                },
            )
        else:
            logger.info(
                "SPAWNER: Continuous mode DISABLED",
                extra={
                    "effective_continuous_mode": effective_continuous_mode,
                    "runtime": runtime,
                    "reason": "not claude runtime"
                    if runtime != "claude"
                    else "continuous_mode=False",
                },
            )

        # Set validation requirements based on task_requirements (LLM-analyzed) or execution_mode
        # task_requirements takes precedence when provided, as it's based on intelligent analysis
        if runtime == "claude":
            if task_requirements is not None:
                # Use LLM-analyzed requirements for fine-grained control
                env_vars.setdefault(
                    "REQUIRE_CLEAN_GIT",
                    "true" if task_requirements.requires_git_commit else "false",
                )
                env_vars.setdefault(
                    "REQUIRE_CODE_PUSHED",
                    "true" if task_requirements.requires_git_push else "false",
                )
                env_vars.setdefault(
                    "REQUIRE_PR_CREATED",
                    "true" if task_requirements.requires_pull_request else "false",
                )
                env_vars.setdefault(
                    "REQUIRE_TESTS",
                    "true" if task_requirements.requires_tests else "false",
                )
                # Also pass output type for context
                env_vars.setdefault(
                    "TASK_OUTPUT_TYPE", task_requirements.output_type.value
                )
                logger.info(
                    "Using LLM-analyzed task requirements",
                    extra={
                        "execution_mode": task_requirements.execution_mode.value,
                        "output_type": task_requirements.output_type.value,
                        "requires_code": task_requirements.requires_code_changes,
                        "requires_commit": task_requirements.requires_git_commit,
                        "requires_push": task_requirements.requires_git_push,
                        "requires_pr": task_requirements.requires_pull_request,
                        "requires_tests": task_requirements.requires_tests,
                        "reasoning": task_requirements.reasoning[:100],
                    },
                )
            elif execution_mode == "exploration":
                # Fallback: Research/analysis tasks don't need git validation
                env_vars.setdefault("REQUIRE_CLEAN_GIT", "false")
                env_vars.setdefault("REQUIRE_CODE_PUSHED", "false")
                env_vars.setdefault("REQUIRE_PR_CREATED", "false")
                logger.info(
                    "Exploration mode: Git validation requirements disabled "
                    "(research/analysis task)"
                )
            else:
                # Fallback: Implementation and validation modes require full git workflow
                env_vars.setdefault("REQUIRE_CLEAN_GIT", "true")
                env_vars.setdefault("REQUIRE_CODE_PUSHED", "true")
                env_vars.setdefault("REQUIRE_PR_CREATED", "true")

        # Add agent type if specified
        if agent_type:
            env_vars["AGENT_TYPE"] = agent_type

        # Add LLM configuration from settings (for OpenHands SDK compatibility)
        # Note: Claude Agent SDK uses ANTHROPIC_* env vars and CLAUDE_CODE_OAUTH_TOKEN
        app_settings = get_app_settings()
        if hasattr(app_settings, "llm") and app_settings.llm:
            if app_settings.llm.api_key:
                env_vars["LLM_API_KEY"] = app_settings.llm.api_key
            if app_settings.llm.model:
                env_vars["LLM_MODEL"] = app_settings.llm.model

        # Anthropic / Z.AI API Configuration
        # Supports per-user credentials with fallback to global config
        from omoi_os.services.credentials import CredentialsService

        # Get user_id from extra_env if provided
        user_id = None
        if extra_env and extra_env.get("USER_ID"):
            try:
                from uuid import UUID

                user_id = UUID(extra_env["USER_ID"])
            except (ValueError, TypeError):
                pass

        # Get credentials (user-specific or global fallback)
        cred_service = CredentialsService(self.db) if self.db else None
        if cred_service:
            creds = cred_service.get_anthropic_credentials(user_id=user_id)
        else:
            # No DB available, use config directly
            from omoi_os.config import load_anthropic_settings

            settings = load_anthropic_settings()
            from omoi_os.services.credentials import AnthropicCredentials

            creds = AnthropicCredentials(
                api_key=settings.get_api_key() or "",
                oauth_token=settings.get_oauth_token(),  # Include OAuth token!
                base_url=settings.base_url,
                model=settings.model,
                default_model=settings.default_model,
                default_haiku_model=settings.default_haiku_model,
                default_sonnet_model=settings.default_sonnet_model,
                default_opus_model=settings.default_opus_model,
                source="config",
            )

        # Prefer OAuth token for Claude Agent SDK, fallback to API key
        if creds.oauth_token:
            env_vars["CLAUDE_CODE_OAUTH_TOKEN"] = creds.oauth_token
            logger.info(
                f"Using OAuth token for Claude Agent SDK (prefix: {creds.oauth_token[:15]}...)"
            )
        elif creds.api_key:
            env_vars["ANTHROPIC_API_KEY"] = creds.api_key
            logger.debug("Using API key for authentication (OAuth token not available)")

        # Only set ANTHROPIC_BASE_URL if a custom endpoint is specified
        # If base_url is None or empty, use default Anthropic API (no env var needed)
        if creds.base_url:
            env_vars["ANTHROPIC_BASE_URL"] = creds.base_url
            logger.info(f"Using custom API endpoint: {creds.base_url}")
        else:
            logger.info("Using default Anthropic API (no custom base_url)")

        # Set model for both MODEL and ANTHROPIC_MODEL
        # Worker reads MODEL first, falls back to ANTHROPIC_MODEL
        if creds.model:
            env_vars["MODEL"] = creds.model  # Primary env var for worker
            env_vars["ANTHROPIC_MODEL"] = creds.model  # Fallback / compatibility
        # Model aliases for Claude SDK compatibility
        if creds.default_model:
            env_vars["ANTHROPIC_DEFAULT_MODEL"] = creds.default_model
        if creds.default_haiku_model:
            env_vars["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = creds.default_haiku_model
        if creds.default_sonnet_model:
            env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] = creds.default_sonnet_model
        if creds.default_opus_model:
            env_vars["ANTHROPIC_DEFAULT_OPUS_MODEL"] = creds.default_opus_model

        logger.debug(f"Using {creds.source} credentials for sandbox")

        # Create GitHub branch BEFORE sandbox creation (if we have ticket/repo info)
        # This ensures the branch exists before we clone the repo in the sandbox
        branch_name = None
        if extra_env and self.db:
            github_repo = extra_env.get("GITHUB_REPO")
            ticket_id = extra_env.get("TICKET_ID")
            user_id = extra_env.get("USER_ID")
            ticket_title = extra_env.get("TICKET_TITLE", "")
            ticket_type = extra_env.get("TICKET_TYPE", "feature")

            # If we have all required info, create branch via BranchWorkflowService
            if github_repo and ticket_id and user_id:
                try:
                    from omoi_os.services.branch_workflow import BranchWorkflowService
                    from omoi_os.services.github_api import GitHubAPIService

                    # Parse owner/repo
                    parts = github_repo.split("/")
                    if len(parts) == 2:
                        repo_owner, repo_name = parts

                        # Initialize services
                        github_service = GitHubAPIService(self.db)
                        branch_workflow = BranchWorkflowService(github_service)

                        # Create branch using user's GitHub token (from user.attributes)
                        result = await branch_workflow.start_work_on_ticket(
                            ticket_id=ticket_id,
                            ticket_title=ticket_title,
                            repo_owner=repo_owner,
                            repo_name=repo_name,
                            user_id=user_id,
                            ticket_type=ticket_type,
                        )

                        if result.get("success"):
                            branch_name = result.get("branch_name")
                            logger.info(
                                f"✅ Created branch '{branch_name}' for ticket {ticket_id} "
                                f"before sandbox creation"
                            )
                            # Add branch name to extra_env so it gets passed to sandbox
                            if extra_env:
                                extra_env["BRANCH_NAME"] = branch_name
                        else:
                            error = result.get("error", "Unknown error")
                            logger.warning(
                                f"⚠️  Failed to create branch for ticket {ticket_id}: {error}"
                            )
                except Exception as e:
                    logger.warning(
                        f"Exception creating branch before sandbox spawn: {e}",
                        exc_info=True,
                    )

        # Handle session resumption for Claude runtime
        if runtime == "claude" and self.db:
            resume_session_id = None
            resume_from_task = extra_env.get("RESUME_FROM_TASK") if extra_env else None

            if extra_env and extra_env.get("RESUME_SESSION_ID"):
                resume_session_id = extra_env["RESUME_SESSION_ID"]
            elif extra_env and extra_env.get("resume_session_id"):
                resume_session_id = extra_env["resume_session_id"]

            # Option 1: Resume by session_id
            if resume_session_id:
                # Retrieve session transcript from database
                from omoi_os.api.routes.sandbox import get_session_transcript

                transcript_b64 = get_session_transcript(self.db, resume_session_id)
                if transcript_b64:
                    env_vars["RESUME_SESSION_ID"] = resume_session_id
                    env_vars["SESSION_TRANSCRIPT_B64"] = transcript_b64
                    logger.info(
                        f"Retrieved session transcript for resumption: {resume_session_id[:8]}..."
                    )
                else:
                    logger.warning(
                        f"Session transcript not found for {resume_session_id}, starting fresh session"
                    )

            # Option 2: Resume by task_id (looks up session from the task's previous runs)
            elif resume_from_task:
                from omoi_os.api.routes.sandbox import get_session_transcript_for_task

                session_id, transcript_b64 = get_session_transcript_for_task(
                    self.db, resume_from_task
                )
                if session_id and transcript_b64:
                    env_vars["RESUME_SESSION_ID"] = session_id
                    env_vars["SESSION_TRANSCRIPT_B64"] = transcript_b64
                    logger.info(
                        f"Retrieved session transcript for task {resume_from_task[:8]}... (session: {session_id[:8]}...)"
                    )
                else:
                    logger.debug(
                        f"No session transcript found for task {resume_from_task}, starting fresh session"
                    )

        # Add extra env vars (can override transcript if explicitly provided)
        if extra_env:
            env_vars.update(extra_env)

            # Set branch name if we created one
            if branch_name:
                env_vars["BRANCH_NAME"] = branch_name
                logger.debug(f"Set BRANCH_NAME={branch_name} for sandbox")

            # If TASK_DATA_BASE64 is provided, decode it and extract ticket info
            # This ensures TICKET_DESCRIPTION and TICKET_TITLE are set for the worker
            if extra_env.get("TASK_DATA_BASE64"):
                try:
                    import json
                    import base64

                    task_json = base64.b64decode(extra_env["TASK_DATA_BASE64"]).decode()
                    task_data = json.loads(task_json)

                    # Set ticket info as direct env vars for WorkerConfig
                    if task_data.get("ticket_title"):
                        env_vars["TICKET_TITLE"] = task_data["ticket_title"]
                    if task_data.get("ticket_description"):
                        env_vars["TICKET_DESCRIPTION"] = task_data["ticket_description"]
                    if task_data.get("ticket_id"):
                        env_vars["TICKET_ID"] = task_data["ticket_id"]
                    if task_data.get("ticket_type"):
                        env_vars["TICKET_TYPE"] = task_data["ticket_type"]

                    logger.debug(
                        f"Extracted ticket info from TASK_DATA_BASE64: title={task_data.get('ticket_title')[:50] if task_data.get('ticket_title') else None}..."
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to decode TASK_DATA_BASE64 for ticket info: {e}"
                    )

        # Build labels
        sandbox_labels = {
            "project": "omoios",
            "task_id": task_id,
            "agent_id": agent_id,
            "phase_id": phase_id,
        }
        if labels:
            sandbox_labels.update(labels)

        # Create sandbox info
        info = SandboxInfo(
            sandbox_id=sandbox_id,
            agent_id=agent_id,
            task_id=task_id,
            phase_id=phase_id,
            status="creating",
        )
        self._sandboxes[sandbox_id] = info
        self._task_to_sandbox[task_id] = sandbox_id

        try:
            # Create Daytona sandbox
            logger.info(
                f"Creating Daytona sandbox {sandbox_id} for task {task_id} (runtime: {runtime})"
            )

            # Store runtime type before creation
            info.extra_data["runtime"] = runtime

            await self._create_daytona_sandbox(
                sandbox_id=sandbox_id,
                env_vars=env_vars,
                labels=sandbox_labels,
                runtime=runtime,
                execution_mode=execution_mode,
                continuous_mode=effective_continuous_mode,
            )

            # Update status
            info.status = "running"
            info.started_at = utc_now()

            # Publish event (include sandbox_id in payload for frontend compatibility)
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="sandbox.spawned",
                        entity_type="sandbox",
                        entity_id=sandbox_id,
                        payload={
                            "sandbox_id": sandbox_id,  # Also in payload for easier access
                            "task_id": task_id,
                            "agent_id": agent_id,
                            "phase_id": phase_id,
                        },
                    )
                )

            # Log comprehensive sandbox creation summary with ALL spec-skill related variables
            logger.info(
                f"Sandbox {sandbox_id} created and running",
                extra={
                    "sandbox_id": sandbox_id,
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "phase_id": phase_id,
                    "runtime": runtime,
                    "execution_mode": execution_mode,
                    "continuous_mode": effective_continuous_mode,
                    # Spec-skill specific variables
                    "require_spec_skill": require_spec_skill,
                    "project_id": project_id,
                    "has_omoios_api_key": "OMOIOS_API_KEY" in env_vars,
                    "omoios_api_url": env_vars.get("OMOIOS_API_URL"),
                    # Key env vars being passed
                    "env_vars_summary": {
                        "REQUIRE_SPEC_SKILL": env_vars.get(
                            "REQUIRE_SPEC_SKILL", "not_set"
                        ),
                        "OMOIOS_PROJECT_ID": env_vars.get(
                            "OMOIOS_PROJECT_ID", "not_set"
                        ),
                        "EXECUTION_MODE": env_vars.get("EXECUTION_MODE"),
                        "CONTINUOUS_MODE": env_vars.get("CONTINUOUS_MODE", "not_set"),
                    },
                },
            )
            return sandbox_id

        except Exception as e:
            logger.error(f"Failed to create sandbox {sandbox_id}: {e}")
            info.status = "failed"
            info.error = str(e)

            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="sandbox.failed",
                        entity_type="sandbox",
                        entity_id=sandbox_id,
                        payload={"error": str(e)},
                    )
                )

            raise RuntimeError(f"Failed to spawn sandbox: {e}") from e

    async def spawn_for_phase(
        self,
        spec_id: str,
        phase: str,
        project_id: str,
        phase_context: Optional[Dict[str, Any]] = None,
        resume_transcript: Optional[str] = None,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> str:
        """Spawn a Daytona sandbox for executing a spec phase.

        This is optimized for the spec-driven state machine workflow, where
        each phase (explore, requirements, design, tasks, sync) runs in
        focused short sessions with checkpointing.

        Args:
            spec_id: ID of the spec being processed
            phase: Current phase (explore, requirements, design, tasks, sync)
            project_id: Project ID for the spec
            phase_context: Accumulated context from previous phases (phase_data JSONB)
            resume_transcript: Base64-encoded session transcript for resumption
            extra_env: Additional environment variables

        Returns:
            Sandbox ID

        Raises:
            RuntimeError: If sandbox creation fails
        """
        import base64
        import json

        logger.info(
            "[SPAWNER] spawn_for_phase called",
            extra={
                "spec_id": spec_id,
                "phase": phase,
                "project_id": project_id,
                "has_phase_context": phase_context is not None,
                "has_resume_transcript": resume_transcript is not None,
            },
        )

        if not self.daytona_api_key:
            raise RuntimeError("Daytona API key not configured")

        # Generate unique sandbox ID for this phase execution
        sandbox_id = f"spec-{spec_id[:8]}-{phase[:4]}-{uuid4().hex[:6]}"

        # Map phase to execution mode
        phase_to_mode = {
            "explore": "exploration",
            "requirements": "exploration",
            "design": "exploration",
            "tasks": "exploration",
            "sync": "implementation",
        }
        execution_mode = phase_to_mode.get(phase, "exploration")

        # Build base environment variables
        base_url = self.mcp_server_url.replace("/mcp", "").rstrip("/")

        env_vars = {
            "SPEC_ID": spec_id,
            "SPEC_PHASE": phase,
            "PROJECT_ID": project_id,
            "EXECUTION_MODE": execution_mode,
            "MCP_SERVER_URL": self.mcp_server_url,
            "CALLBACK_URL": base_url,
            "SANDBOX_ID": sandbox_id,
            "IS_SANDBOX": "1",
            "OMOIOS_API_URL": base_url,
            "OMOIOS_PROJECT_ID": project_id,
            # Enable spec skill for state machine phases
            "REQUIRE_SPEC_SKILL": "true",
        }

        # Add API key for spec sync
        from omoi_os.config import get_app_settings
        app_settings = get_app_settings()
        if app_settings.llm.api_key:
            env_vars["OMOIOS_API_KEY"] = app_settings.llm.api_key

        # ==== GitHub Integration: Fetch credentials and repo info ====
        # This enables sandboxes to clone repos and create PRs
        if self.db:
            from omoi_os.services.credentials import CredentialsService
            from omoi_os.models.spec import Spec
            from omoi_os.models.project import Project

            cred_service = CredentialsService(self.db)

            # Get spec to find user_id
            user_id = None
            with self.db.get_session() as session:
                spec = session.get(Spec, spec_id)
                if spec and spec.user_id:
                    user_id = spec.user_id
                    env_vars["USER_ID"] = str(user_id)

                # Get project for GitHub repo info
                project = session.get(Project, project_id)
                if project and project.github_owner and project.github_repo:
                    env_vars["GITHUB_REPO"] = f"{project.github_owner}/{project.github_repo}"
                    env_vars["GITHUB_REPO_OWNER"] = project.github_owner
                    env_vars["GITHUB_REPO_NAME"] = project.github_repo
                    logger.info(
                        f"[SPAWNER] GitHub repo configured: {project.github_owner}/{project.github_repo}"
                    )
                else:
                    logger.info(
                        f"[SPAWNER] No GitHub repo configured for project {project_id}"
                    )

            # Get GitHub credentials for the user
            if user_id:
                github_creds = cred_service.get_github_credentials(user_id=user_id)
                if github_creds.access_token:
                    env_vars["GITHUB_TOKEN"] = github_creds.access_token
                    if github_creds.username:
                        env_vars["GITHUB_USERNAME"] = github_creds.username
                    logger.info(
                        f"[SPAWNER] GitHub token configured from {github_creds.source}"
                    )
                else:
                    logger.warning(
                        f"[SPAWNER] No GitHub token available for user {user_id} - "
                        "sandbox will not be able to clone private repos or create PRs"
                    )

                # Get Anthropic credentials for the user
                anthropic_creds = cred_service.get_anthropic_credentials(user_id=user_id)
                if anthropic_creds.oauth_token:
                    env_vars["CLAUDE_CODE_OAUTH_TOKEN"] = anthropic_creds.oauth_token
                    logger.info("[SPAWNER] Using OAuth token for Claude Agent SDK")
                elif anthropic_creds.api_key:
                    env_vars["ANTHROPIC_API_KEY"] = anthropic_creds.api_key
                    logger.info("[SPAWNER] Using API key for authentication")
                if anthropic_creds.base_url:
                    env_vars["ANTHROPIC_BASE_URL"] = anthropic_creds.base_url
                if anthropic_creds.model:
                    env_vars["MODEL"] = anthropic_creds.model
                    env_vars["ANTHROPIC_MODEL"] = anthropic_creds.model
        # ==== End GitHub Integration ====

        # Add phase context as base64-encoded JSON
        if phase_context:
            context_json = json.dumps(phase_context)
            env_vars["PHASE_CONTEXT_B64"] = base64.b64encode(
                context_json.encode()
            ).decode()
            logger.debug(
                f"Encoded phase context ({len(context_json)} bytes) for phase {phase}"
            )

        # Add session transcript for resumption if provided
        if resume_transcript:
            env_vars["SESSION_TRANSCRIPT_B64"] = resume_transcript
            logger.info(
                f"Phase {phase} will resume from previous session transcript"
            )

        # Add extra env vars (can override defaults)
        if extra_env:
            env_vars.update(extra_env)

        # Build labels
        sandbox_labels = {
            "project": "omoios",
            "type": "spec_phase",
            "spec_id": spec_id,
            "phase": phase,
            "project_id": project_id,
        }

        # Create sandbox info - use spec_id as task_id equivalent
        info = SandboxInfo(
            sandbox_id=sandbox_id,
            agent_id=f"spec-{phase}",  # Virtual agent ID for phase
            task_id=f"{spec_id}-{phase}",  # Composite task ID
            phase_id=phase,
            status="creating",
        )
        info.extra_data["spec_id"] = spec_id
        info.extra_data["spec_phase"] = phase
        info.extra_data["runtime"] = "claude"

        self._sandboxes[sandbox_id] = info
        self._task_to_sandbox[f"{spec_id}-{phase}"] = sandbox_id

        try:
            logger.info(
                f"Creating Daytona sandbox {sandbox_id} for spec phase {phase}"
            )

            await self._create_daytona_sandbox(
                sandbox_id=sandbox_id,
                env_vars=env_vars,
                labels=sandbox_labels,
                runtime="claude",  # Always use Claude for spec phases
                execution_mode=execution_mode,
                continuous_mode=False,  # State machine handles iteration
            )

            info.status = "running"
            info.started_at = utc_now()

            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="sandbox.spawned",
                        entity_type="sandbox",
                        entity_id=sandbox_id,
                        payload={
                            "sandbox_id": sandbox_id,
                            "spec_id": spec_id,
                            "phase": phase,
                            "project_id": project_id,
                            "type": "spec_phase",
                        },
                    )
                )

            logger.info(
                f"Sandbox {sandbox_id} created for spec phase {phase}",
                extra={
                    "sandbox_id": sandbox_id,
                    "spec_id": spec_id,
                    "phase": phase,
                    "execution_mode": execution_mode,
                },
            )

            return sandbox_id

        except Exception as e:
            logger.error(f"Failed to create sandbox for spec phase: {e}")
            info.status = "failed"
            info.error = str(e)

            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="sandbox.failed",
                        entity_type="sandbox",
                        entity_id=sandbox_id,
                        payload={
                            "error": str(e),
                            "spec_id": spec_id,
                            "phase": phase,
                        },
                    )
                )

            raise RuntimeError(f"Failed to spawn sandbox for phase {phase}: {e}") from e

    async def _create_daytona_sandbox(
        self,
        sandbox_id: str,
        env_vars: Dict[str, str],
        labels: Dict[str, str],
        runtime: str = "openhands",
        execution_mode: str = "implementation",
        continuous_mode: bool = False,
    ) -> None:
        """Create a Daytona sandbox via their API.

        This is the actual Daytona SDK integration point.

        Args:
            sandbox_id: Unique sandbox identifier
            env_vars: Environment variables to set in sandbox
            labels: Labels for sandbox organization
            runtime: Agent runtime - "openhands" or "claude"
            execution_mode: Skill loading mode - determines which skills are loaded
            continuous_mode: Whether continuous iteration mode is enabled
        """
        try:
            from daytona import (
                Daytona,
                DaytonaConfig,
                CreateSandboxFromImageParams,
                CreateSandboxFromSnapshotParams,
                Resources,
            )

            daytona_config = DaytonaConfig(
                api_key=self.daytona_api_key,
                api_url=self.daytona_api_url,
                target="us",
            )
            daytona = Daytona(daytona_config)

            # Configure resources for sandbox (memory, CPU, disk)
            # Higher memory helps prevent OOM kills (exit code -9)
            resources = Resources(
                cpu=self.sandbox_cpu,
                memory=self.sandbox_memory_gb,
                disk=self.sandbox_disk_gb,
            )

            # Create sandbox from snapshot if provided, otherwise use image
            if self.sandbox_snapshot:
                logger.info(
                    f"Creating sandbox from snapshot: {self.sandbox_snapshot} "
                    f"with resources: {self.sandbox_cpu} CPU, "
                    f"{self.sandbox_memory_gb} GiB RAM, {self.sandbox_disk_gb} GiB disk"
                )
                params = CreateSandboxFromSnapshotParams(
                    snapshot=self.sandbox_snapshot,
                    labels=labels or None,
                    ephemeral=True,  # Auto-delete when stopped
                    public=False,
                    resources=resources,
                )
            else:
                logger.info(
                    f"Creating sandbox from image: {self.sandbox_image} "
                    f"with resources: {self.sandbox_cpu} CPU, "
                    f"{self.sandbox_memory_gb} GiB RAM, {self.sandbox_disk_gb} GiB disk"
                )
                params = CreateSandboxFromImageParams(
                    image=self.sandbox_image,
                    labels=labels or None,
                    ephemeral=True,  # Auto-delete when stopped
                    public=False,
                    resources=resources,
                )

            sandbox = daytona.create(params=params, timeout=120)
            logger.info(f"Daytona sandbox {sandbox.id} created for {sandbox_id}")

            # Store sandbox reference
            info = self._sandboxes.get(sandbox_id)
            if info:
                info.extra_data["daytona_sandbox"] = sandbox
                info.extra_data["daytona_sandbox_id"] = sandbox.id

        except ImportError as e:
            # Daytona SDK not available - use mock for local testing
            logger.warning(f"Daytona SDK import failed: {e}, using mock sandbox")
            await self._create_mock_sandbox(sandbox_id, env_vars)
            return  # Don't try to start worker in mock sandbox here
        except Exception as e:
            logger.error(f"Failed to create Daytona sandbox: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            await self._create_mock_sandbox(sandbox_id, env_vars)
            return  # Don't try to start worker in mock sandbox here

        # Start worker OUTSIDE the try/except so errors are not silently swallowed
        # This ensures we see exactly what fails during worker startup
        try:
            # Pass continuous_mode from spawn_for_task to control worker logging
            await self._start_worker_in_sandbox(
                sandbox,
                env_vars,
                runtime,
                execution_mode,
                continuous_mode=continuous_mode,
            )
            logger.info(f"Worker started successfully in sandbox {sandbox.id}")
        except Exception as e:
            # Log worker startup errors clearly - don't fall back to mock!
            # The sandbox exists, we just failed to start the worker
            logger.error(f"Failed to start worker in sandbox {sandbox.id}: {e}")
            import traceback

            logger.error(f"Worker startup traceback: {traceback.format_exc()}")
            # Re-raise so the caller knows something went wrong
            raise RuntimeError(
                f"Worker startup failed in sandbox {sandbox.id}: {e}"
            ) from e

    async def _start_worker_in_sandbox(
        self,
        sandbox: Any,
        env_vars: Dict[str, str],
        runtime: str = "openhands",
        execution_mode: str = "implementation",
        continuous_mode: bool = False,
    ) -> None:
        """Start the sandbox worker inside the Daytona sandbox.

        Args:
            sandbox: Daytona sandbox instance
            env_vars: Environment variables for the worker
            runtime: Agent runtime - "openhands" or "claude"
            execution_mode: Skill loading mode - determines which skills are loaded
            continuous_mode: Whether continuous iteration mode is enabled
        """
        # Extract git clone parameters (don't pass token to env vars for security)
        github_repo = env_vars.pop("GITHUB_REPO", None)
        github_token = env_vars.pop("GITHUB_TOKEN", None)
        github_owner = env_vars.pop("GITHUB_REPO_OWNER", None)
        github_repo_name = env_vars.pop("GITHUB_REPO_NAME", None)
        # Extract branch name but keep it in env_vars for the worker
        branch_name = env_vars.get("BRANCH_NAME")

        # Helper function to escape environment variable values for shell export
        def escape_env_value(v: str) -> str:
            """Escape environment variable value for shell export."""
            # Use shlex.quote to properly escape shell values
            return shlex.quote(str(v))

        # NOTE: We delay writing env file and bashrc until AFTER all env vars are set
        # (including GITHUB_TOKEN which gets added after git clone).
        # See the "Persist final environment" section below.

        # Install required packages based on runtime
        # Use uv for faster installation if available, fallback to pip
        logger.info(f"Installing {runtime} dependencies in sandbox...")
        if runtime == "claude":
            # Claude Agent SDK - per docs/libraries/claude-agent-sdk-python-clean.md
            # Include pydantic for model serialization (model_dump support)
            install_cmd = "uv pip install claude-agent-sdk httpx pydantic 2>/dev/null || pip install claude-agent-sdk httpx pydantic"
        else:  # openhands (default)
            # OpenHands Software Agent SDK - per docs/libraries/software-agent-sdk-clean.md
            # openhands-sdk: Core SDK (openhands.sdk)
            # openhands-tools: Built-in tools (openhands.tools)
            install_cmd = "uv pip install openhands-sdk openhands-tools httpx 2>/dev/null || pip install openhands-sdk openhands-tools httpx"
        sandbox.process.exec(install_cmd, timeout=180)

        # Install GitHub CLI (gh) for PR creation, merging, and GitHub API access
        # This enables agents to create PRs, merge branches, and interact with GitHub
        logger.info("Installing GitHub CLI...")
        try:
            # Try to install gh CLI - different methods for different base images
            gh_install_cmd = """
            if command -v gh &> /dev/null; then
                echo "gh already installed"
            elif command -v apt-get &> /dev/null; then
                # Debian/Ubuntu
                curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
                chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
                echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
                apt-get update -qq && apt-get install gh -y -qq
            elif command -v apk &> /dev/null; then
                # Alpine
                apk add --no-cache github-cli
            elif command -v dnf &> /dev/null; then
                # Fedora/RHEL
                dnf install -y gh
            else
                echo "Could not install gh - unknown package manager"
            fi
            """
            sandbox.process.exec(gh_install_cmd, timeout=120)
            logger.info("GitHub CLI installed successfully")
        except Exception as e:
            logger.warning(f"Failed to install GitHub CLI: {e}")
            # Continue without gh - agent can still use git commands directly

        # Upload Claude skills to sandbox (Claude runtime only)
        if runtime == "claude":
            logger.info(f"Uploading Claude skills for '{execution_mode}' mode...")
            try:
                # Create skills directory
                sandbox.process.exec("mkdir -p /root/.claude/skills")

                # Create minimal settings.local.json
                # With IS_SANDBOX=1 and bypassPermissions, the allow list is not needed
                # The SDK will skip all permission prompts automatically
                settings_content = """{
  "permissions": {
    "allow": [],
    "deny": []
  }
}"""
                sandbox.fs.upload_file(
                    settings_content.encode("utf-8"),
                    "/root/.claude/settings.local.json",
                )
                logger.info(
                    "Uploaded Claude settings.local.json (bypassPermissions mode)"
                )

                # Get skills based on execution mode
                # - exploration: spec-driven-dev (for creating specs/tickets/tasks)
                # - implementation: git-workflow, code-review, etc. (for executing tasks)
                # - validation: code-review, test-writer (for validating implementation)
                skills = get_skills_for_upload(mode=execution_mode)
                for skill_path, content in skills.items():
                    # Create parent directory for skill
                    parent_dir = "/".join(skill_path.rsplit("/", 1)[:-1])
                    sandbox.process.exec(f"mkdir -p {parent_dir}")
                    # Upload skill file
                    sandbox.fs.upload_file(content.encode("utf-8"), skill_path)
                    logger.debug(f"Uploaded skill: {skill_path}")

                logger.info(
                    f"Uploaded {len(skills)} Claude skills for '{execution_mode}' mode"
                )
            except Exception as e:
                logger.warning(f"Failed to upload Claude skills: {e}")
                # Continue without skills - agent can still function

        # Clone GitHub repository using Daytona SDK (if configured)
        # This uses sandbox.git.clone() directly instead of shell commands
        # Token is passed via SDK, never exposed in environment variables
        logger.info(
            f"Git clone check: github_repo={github_repo}, "
            f"has_token={bool(github_token)}, "
            f"token_prefix={github_token[:10] + '...' if github_token and len(github_token) > 10 else 'N/A'}"
        )

        if github_repo and github_token:
            logger.info(
                f"Cloning repository {github_repo} via Daytona SDK... "
                f"(branch: {branch_name or 'default'})"
            )

            # Validate token before attempting clone
            repo_url = f"https://github.com/{github_repo}.git"
            workspace_path = "/workspace"

            # Pre-clone validation: check if we can access the repo with this token
            logger.info(f"Validating GitHub token can access {github_repo}...")
            try:
                import httpx

                headers = {
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }
                validation_url = f"https://api.github.com/repos/{github_repo}"
                with httpx.Client(timeout=10) as client:
                    resp = client.get(validation_url, headers=headers)
                    if resp.status_code == 200:
                        repo_info = resp.json()
                        logger.info(
                            f"GitHub token validated: can access {github_repo} "
                            f"(private={repo_info.get('private')}, "
                            f"default_branch={repo_info.get('default_branch')})"
                        )
                    elif resp.status_code == 401:
                        logger.error(
                            f"GitHub token is invalid or expired (401). "
                            f"User needs to re-authenticate with GitHub."
                        )
                    elif resp.status_code == 403:
                        logger.error(
                            f"GitHub token lacks permission to access {github_repo} (403). "
                            f"Token may need 'repo' scope."
                        )
                    elif resp.status_code == 404:
                        logger.error(
                            f"Repository {github_repo} not found or token lacks access (404)."
                        )
                    else:
                        logger.warning(
                            f"GitHub API returned {resp.status_code} for {github_repo}: {resp.text[:200]}"
                        )
            except Exception as e:
                logger.warning(f"Failed to validate GitHub token (non-fatal): {e}")

            try:
                # Use Daytona SDK's native git.clone() with authentication
                # username="x-access-token" is GitHub's convention for token auth
                # Pass branch parameter to clone the feature branch directly
                clone_kwargs = {
                    "url": repo_url,
                    "path": workspace_path,
                    "username": "x-access-token",
                    "password": github_token,
                }
                if branch_name:
                    clone_kwargs["branch"] = branch_name
                    logger.info(f"Cloning branch '{branch_name}' from {github_repo}")

                sandbox.git.clone(**clone_kwargs)

                logger.info(
                    f"Repository cloned successfully to {workspace_path} "
                    f"(branch: {branch_name or 'default'})"
                )

                # Verify clone worked and check which branch we're on
                try:
                    result = sandbox.process.exec(f"ls -la {workspace_path}")
                    logger.info(
                        f"Workspace contents after clone:\n{result.stdout[:500] if hasattr(result, 'stdout') else result}"
                    )

                    # Check current branch
                    branch_check = sandbox.process.exec(
                        f"cd {workspace_path} && git branch --show-current"
                    )
                    current_branch = (
                        branch_check.stdout.strip()
                        if hasattr(branch_check, "stdout")
                        else str(branch_check).strip()
                    )
                    logger.info(f"Current git branch after clone: '{current_branch}'")

                    # ALWAYS checkout the target branch if specified
                    # Don't rely on SDK's branch parameter - explicitly switch to ensure we're on the right branch
                    if branch_name:
                        if current_branch != branch_name:
                            logger.info(
                                f"Switching from '{current_branch}' to feature branch '{branch_name}'..."
                            )
                        else:
                            logger.info(
                                f"Already on branch '{branch_name}', confirming checkout..."
                            )

                        # Fetch all remote branches first to ensure we have the branch ref
                        sandbox.process.exec(f"cd {workspace_path} && git fetch origin")

                        # Checkout the feature branch (this works whether we're already on it or not)
                        checkout_result = sandbox.process.exec(
                            f"cd {workspace_path} && git checkout {branch_name}"
                        )
                        checkout_output = (
                            checkout_result.stdout
                            if hasattr(checkout_result, "stdout")
                            else str(checkout_result)
                        )
                        logger.info(f"Checkout result: {checkout_output}")

                        # Verify we're now on the correct branch
                        final_branch_check = sandbox.process.exec(
                            f"cd {workspace_path} && git branch --show-current"
                        )
                        final_branch = (
                            final_branch_check.stdout.strip()
                            if hasattr(final_branch_check, "stdout")
                            else str(final_branch_check).strip()
                        )

                        if final_branch == branch_name:
                            logger.info(
                                f"✅ Successfully on feature branch '{branch_name}'"
                            )
                        else:
                            logger.error(
                                f"❌ Failed to checkout branch '{branch_name}', still on '{final_branch}'"
                            )
                except Exception as e:
                    logger.warning(f"Could not verify/switch branch after clone: {e}")

                # Set WORKSPACE_PATH env var so worker knows where code is
                env_vars["WORKSPACE_PATH"] = workspace_path
                env_vars["GITHUB_REPO"] = (
                    github_repo  # Re-add repo info (not the token)
                )
                if github_owner:
                    env_vars["GITHUB_REPO_OWNER"] = github_owner
                if github_repo_name:
                    env_vars["GITHUB_REPO_NAME"] = github_repo_name

                # Configure git for pushing
                # 1. Set up git credential helper to use the token
                # Store credentials in memory for the session (more secure than file)
                sandbox.process.exec(
                    "git config --global credential.helper 'cache --timeout=86400'"
                )

                # 2. Configure the remote URL with token for push access
                # This embeds the token in the remote URL (standard GitHub approach)
                authenticated_url = f"https://x-access-token:{github_token}@github.com/{github_repo}.git"
                sandbox.process.exec(
                    f"cd {workspace_path} && git remote set-url origin {shlex.quote(authenticated_url)}"
                )

                # 3. Configure git user for commits (use GitHub Actions bot identity)
                sandbox.process.exec(
                    'git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"'
                )
                sandbox.process.exec(
                    'git config --global user.name "github-actions[bot]"'
                )

                # 4. Set default branch behavior for push
                sandbox.process.exec("git config --global push.default current")

                # 5. Pass GITHUB_TOKEN to environment for gh CLI and API access
                # This allows the agent to use `gh` commands for PRs, merges, etc.
                env_vars["GITHUB_TOKEN"] = github_token
                env_vars["GH_TOKEN"] = github_token  # gh CLI uses this

                logger.info("Git configured for push access with GitHub token")

                # NOTE: WORKSPACE_PATH, GITHUB_TOKEN, GH_TOKEN are now in env_vars
                # and will be persisted to /tmp/.sandbox_env and ~/.bashrc in the
                # "Persist final environment" section below.

            except Exception as e:
                logger.warning(f"Failed to clone repository via SDK: {e}")
                # Continue without repo - worker can still run
        elif github_repo:
            logger.info(
                f"GITHUB_REPO set ({github_repo}) but no GITHUB_TOKEN - skipping clone"
            )
        else:
            logger.debug("No GITHUB_REPO configured - skipping repository clone")

        # Upload the appropriate worker script
        # Note: Claude worker has continuous mode built-in, controlled by CONTINUOUS_MODE env var
        if runtime == "claude":
            worker_script = self._get_claude_worker_script()
            if continuous_mode:
                logger.info(
                    "Using Claude worker with continuous mode enabled via environment"
                )
        else:
            worker_script = self._get_worker_script()
        sandbox.fs.upload_file(worker_script.encode("utf-8"), "/tmp/sandbox_worker.py")

        # Rebuild env_exports with any new variables (like WORKSPACE_PATH, GITHUB_TOKEN)
        # Use the same escape function defined above
        env_exports = " ".join(
            [f"export {k}={escape_env_value(v)}" for k, v in env_vars.items()]
        )

        # =========================================================================
        # Persist final environment (AFTER all env vars including GITHUB_TOKEN are set)
        # This ensures the token is available for:
        # - Subprocesses spawned by the worker
        # - Continuous mode iterations that may source bashrc
        # - gh CLI commands that read GH_TOKEN from environment
        # =========================================================================

        # Write env vars to a file for persistence and debugging
        # For the file, we can use simpler escaping since it's not in a shell command
        env_file_content = "\n".join(
            [
                f'{k}="{v.replace(chr(34), chr(92) + chr(34))}"'
                for k, v in env_vars.items()
            ]
        )
        sandbox.process.exec(
            f"cat > /tmp/.sandbox_env << 'ENVEOF'\n{env_file_content}\nENVEOF"
        )

        # Export to current shell profile for all future commands
        # This ensures env vars persist across shell sessions and subprocesses
        sandbox.process.exec(f"cat >> /root/.bashrc << 'ENVEOF'\n{env_exports}\nENVEOF")

        # Also source the env file in bashrc for belt-and-suspenders persistence
        sandbox.process.exec(
            'echo "source /tmp/.sandbox_env 2>/dev/null || true" >> /root/.bashrc'
        )

        logger.info(
            f"Persisted {len(env_vars)} environment variables (including GitHub tokens)"
        )

        # Create workspace directory (even if no repo cloned)
        sandbox.process.exec("mkdir -p /workspace")

        # Start the worker
        logger.info("Starting sandbox worker...")
        # Use proper escaping for the bash -c command
        # Since env_exports is already properly escaped, we can use it directly
        # Add PYTHONUNBUFFERED=1 to ensure output is not buffered
        start_cmd = (
            f"{env_exports} && cd /tmp && PYTHONUNBUFFERED=1 python sandbox_worker.py"
        )

        # Run in background and capture output
        # Escape the command properly for bash -c
        escaped_cmd = shlex.quote(start_cmd)
        sandbox.process.exec(f"nohup bash -c {escaped_cmd} > /tmp/worker.log 2>&1 &")
        logger.info("Sandbox worker started, check /tmp/worker.log for output")

    def _get_worker_script(self) -> str:
        """Get the standalone sandbox worker script content.

        SDK Reference: docs/libraries/software-agent-sdk-clean.md
        GitHub: https://github.com/OpenHands/software-agent-sdk

        Phase 3 Updates:
        - Uses /api/v1/sandboxes/{id}/events for event callbacks
        - Polls /api/v1/sandboxes/{id}/messages for message injection
        - Enhanced callback checks for pending messages
        - Handles interrupt messages to stop execution

        Phase 3.5 Updates:
        - Clones GitHub repository on startup if credentials provided
        - Checks out feature branch if BRANCH_NAME specified
        - Configures git user for commits
        """
        return '''#!/usr/bin/env python3
"""Standalone sandbox worker - runs OpenHands agent for a task.

SDK Reference: https://github.com/OpenHands/software-agent-sdk
Local Docs: docs/libraries/software-agent-sdk-clean.md

Phase 3: HTTP Callbacks and Message Injection
- Reports events via POST /api/v1/sandboxes/{sandbox_id}/events
- Polls GET /api/v1/sandboxes/{sandbox_id}/messages for injected messages
- Event callback checks for pending messages

Phase 3.5: GitHub Clone Integration
- Clones repository on startup if GITHUB_TOKEN provided
- Checks out feature branch if BRANCH_NAME specified
"""

import asyncio
import os
import logging
import subprocess
import httpx
from typing import List, Optional

# OpenHands SDK imports - using actual package structure
from openhands.sdk import LLM, Conversation
from openhands.tools.preset.default import get_default_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
TASK_ID = os.environ.get("TASK_ID")
AGENT_ID = os.environ.get("AGENT_ID")
SANDBOX_ID = os.environ.get("SANDBOX_ID", "")
# Base URL without /mcp suffix for API calls
BASE_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:18000").replace("/mcp", "").rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")

# GitHub configuration (Phase 3.5)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # format: owner/repo
BRANCH_NAME = os.environ.get("BRANCH_NAME")

# Phase 5: Additional environment variables for branch workflow
TICKET_ID = os.environ.get("TICKET_ID")  # For GitFlow branch naming
TICKET_TITLE = os.environ.get("TICKET_TITLE", "")
TICKET_TYPE = os.environ.get("TICKET_TYPE", "feature")
USER_ID = os.environ.get("USER_ID", "")

# Phase 6: Injected task data from orchestrator (eliminates need for API fetch)
# Task data is base64-encoded to avoid shell escaping issues
TASK_DATA_BASE64 = os.environ.get("TASK_DATA_BASE64")
WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", "/workspace")

# Global state for message injection
_should_stop: bool = False
_conversation: Optional[Conversation] = None


# ============================================================================
# GITHUB CLONE SETUP (Phase 3.5 + Phase 5 Integration)
# ============================================================================

async def create_branch_via_api():
    """Call BranchWorkflowService API to create properly named branch.
    
    Phase 5: Uses BranchWorkflowService for GitFlow-compliant branch naming.
    Returns the branch name if successful, None otherwise.
    """
    if not GITHUB_REPO or not TICKET_ID or not USER_ID:
        logger.info("Missing GITHUB_REPO, TICKET_ID, or USER_ID - skipping API branch creation")
        return None
    
    # Parse owner/repo
    parts = GITHUB_REPO.split("/")
    if len(parts) != 2:
        logger.error(f"Invalid GITHUB_REPO format: {GITHUB_REPO}")
        return None
    owner, repo = parts
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/branch-workflow/start",
                json={
                    "ticket_id": TICKET_ID,
                    "ticket_title": TICKET_TITLE or f"Task {TICKET_ID}",
                    "repo_owner": owner,
                    "repo_name": repo,
                    "user_id": USER_ID,
                    "ticket_type": TICKET_TYPE,
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    branch_name = data.get("branch_name")
                    logger.info(f"Branch created via API: {branch_name}")
                    return branch_name
                else:
                    logger.warning(f"Branch creation failed: {data.get('error')}")
            else:
                logger.warning(f"Branch API returned {resp.status_code}")
    except Exception as e:
        logger.warning(f"Failed to create branch via API: {e}")
    
    return None


def clone_repo(branch_name: str | None = None):
    """Clone GitHub repo and checkout branch. Called on startup.

    Phase 3.5: Clones repository if GITHUB_TOKEN and GITHUB_REPO are set.
    Phase 5: Uses branch_name from BranchWorkflowService if provided,
             otherwise falls back to BRANCH_NAME env var.
    Phase 6: Skips clone if WORKSPACE_PATH already contains a git repo
             (spawner uses sandbox.git.clone() directly).
    """
    # Phase 6: Check if workspace was already cloned by spawner
    if os.path.exists(os.path.join(WORKSPACE_PATH, ".git")):
        logger.info(f"Workspace {WORKSPACE_PATH} already has a git repo - skipping clone")
        return True
    
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logger.info("No GitHub credentials, skipping repo clone")
        return False

    # Use provided branch_name or fall back to env var
    target_branch = branch_name or BRANCH_NAME

    # Configure git user for commits
    subprocess.run(["git", "config", "--global", "user.email", "agent@omoios.ai"], check=False)
    subprocess.run(["git", "config", "--global", "user.name", "OmoiOS Agent"], check=False)
    
    # Build authenticated clone URL
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
    
    logger.info(f"Cloning {GITHUB_REPO}...")
    result = subprocess.run(
        ["git", "clone", clone_url, "/workspace"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.error(f"Clone failed: {result.stderr}")
        return False
    
    os.chdir("/workspace")
    
    # Checkout branch if specified
    if target_branch:
        logger.info(f"Checking out branch: {target_branch}")
        # Try to checkout existing branch (created via API)
        result = subprocess.run(
            ["git", "checkout", target_branch],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            # Branch doesn't exist remotely, create it locally
            logger.info(f"Creating new branch locally: {target_branch}")
            subprocess.run(["git", "checkout", "-b", target_branch], check=False)
    
    logger.info("Repository ready at /workspace")
    return True


async def setup_github_workspace():
    """Setup GitHub workspace with proper branch naming.
    
    Phase 5 Integration: 
    1. Calls BranchWorkflowService API to create properly named branch
    2. Clones repo and checks out the branch
    """
    # Try to create branch via API (Phase 5)
    branch_name = await create_branch_via_api()
    
    # Clone repo (will use API branch name or fall back to BRANCH_NAME env var)
    return clone_repo(branch_name)


# ============================================================================
# HTTP CALLBACK FUNCTIONS (Phase 3)
# ============================================================================

async def fetch_task():
    """Fetch task details - uses injected data first, falls back to API.
    
    Phase 6: The orchestrator injects TASK_DATA_BASE64 with full task context,
    eliminating the need for an API call. This enables local development
    and ensures task data is always available regardless of API connectivity.
    """
    import json
    import base64
    
    # First: Check for injected task data (Phase 6 - base64 encoded)
    if TASK_DATA_BASE64:
        try:
            task_json = base64.b64decode(TASK_DATA_BASE64).decode()
            task_data = json.loads(task_json)
            logger.info("Using injected task data from orchestrator")
            # Map to expected format
            return {
                "id": task_data.get("task_id"),
                "description": task_data.get("task_description") or task_data.get("ticket_description") or task_data.get("ticket_title"),
                "task_type": task_data.get("task_type"),
                "priority": task_data.get("task_priority"),
                "phase_id": task_data.get("phase_id"),
                "ticket_id": task_data.get("ticket_id"),
                "ticket_title": task_data.get("ticket_title"),
                "ticket_description": task_data.get("ticket_description"),
                "ticket_context": task_data.get("ticket_context", {}),
            }
        except Exception as e:
            logger.warning(f"Failed to decode TASK_DATA_BASE64: {e}, falling back to API")
    
    # Fallback: Fetch from API (original behavior)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BASE_URL}/api/v1/tasks/{TASK_ID}")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch task: {e}")
    return None


async def report_event(event_type: str, event_data: dict, source: str = "agent"):
    """Report an agent event via sandbox callback endpoint.
    
    Phase 3: Uses POST /api/v1/sandboxes/{sandbox_id}/events
    """
    if not SANDBOX_ID:
        logger.debug("No SANDBOX_ID, skipping event report")
        return
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BASE_URL}/api/v1/sandboxes/{SANDBOX_ID}/events",
                json={
                    "event_type": event_type,
                    "event_data": {
                        **event_data,
                        "task_id": TASK_ID,
                        "agent_id": AGENT_ID,
                    },
                    "source": source,
                },
            )
    except Exception as e:
        logger.debug(f"Failed to report event: {e}")


async def poll_messages() -> List[dict]:
    """Poll for pending messages from the message queue.
    
    Phase 3: Uses GET /api/v1/sandboxes/{sandbox_id}/messages
    Messages are consumed (cleared) after retrieval.
    """
    if not SANDBOX_ID:
        return []
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BASE_URL}/api/v1/sandboxes/{SANDBOX_ID}/messages")
            if resp.status_code == 200:
                messages = resp.json()
                if messages:
                    logger.info(f"Received {len(messages)} injected message(s)")
                return messages
    except Exception as e:
        logger.debug(f"Failed to poll messages: {e}")
    return []


def process_messages(messages: List[dict]) -> Optional[str]:
    """Process injected messages and return context to inject.
    
    Handles message types:
    - user_message: Guidance from user
    - guardian_nudge: Suggestion from Guardian
    - interrupt: Stop current work immediately
    - system: System notification
    """
    global _should_stop
    
    context_parts = []
    
    for msg in messages:
        msg_type = msg.get("message_type", "user_message")
        content = msg.get("content", "")
        
        if msg_type == "interrupt":
            logger.warning(f"INTERRUPT received: {content}")
            _should_stop = True
            return f"INTERRUPT: {content}. Stop current work immediately."
        
        elif msg_type == "guardian_nudge":
            context_parts.append(f"Guardian suggests: {content}")
        
        elif msg_type == "user_message":
            context_parts.append(f"User message: {content}")
        
        elif msg_type == "system":
            context_parts.append(f"System: {content}")
    
    if context_parts:
        return "\\n".join(context_parts)
    return None


async def register_conversation(conversation_id: str):
    """Register conversation ID with server for Guardian observation."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BASE_URL}/api/v1/tasks/{TASK_ID}/register-conversation",
                json={
                    "conversation_id": conversation_id,
                    "sandbox_id": SANDBOX_ID,
                },
            )
            logger.info(f"Registered conversation {conversation_id}")
    except Exception as e:
        logger.warning(f"Failed to register conversation: {e}")


async def update_task_status(status: str, result: str = None):
    """Update task status in the server."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.patch(
                f"{BASE_URL}/api/v1/tasks/{TASK_ID}",
                json={"status": status, "result": result},
            )
    except Exception as e:
        logger.warning(f"Failed to update task status: {e}")


# ============================================================================
# AGENT EXECUTION WITH MESSAGE INJECTION
# ============================================================================

def create_event_callback():
    """Create event callback with message injection support."""
    global _should_stop, _conversation
    
    async def check_and_report(event):
        """Event callback that checks for messages and reports events."""
        global _should_stop
        
        # Report the event
        event_type = type(event).__name__
        event_data = {"message": str(event)[:300]}
        await report_event(f"agent.{event_type}", event_data)
        
        # Check for pending messages (message injection)
        messages = await poll_messages()
        if messages:
            injected_context = process_messages(messages)
            
            if _should_stop:
                # Interrupt received - this will be handled in main loop
                await report_event("agent.interrupted", {"reason": "interrupt_message"})
                logger.warning("Interrupt flag set - agent should stop")
            
            elif injected_context and _conversation:
                # Inject the message into the conversation
                await report_event("agent.message_injected", {"message_count": len(messages)})
                # Send injected context as a new message
                _conversation.send_message(f"[INJECTED GUIDANCE]\\n{injected_context}")
    
    def sync_callback(event):
        """Synchronous wrapper for async callback."""
        asyncio.create_task(check_and_report(event))
    
    return sync_callback


async def main():
    global _conversation, _should_stop

    logger.info(f"OpenHands Worker starting for task {TASK_ID}")
    logger.info(f"Sandbox ID: {SANDBOX_ID}")
    logger.info(f"Backend URL: {BASE_URL}")
    
    if not TASK_ID or not AGENT_ID:
        logger.error("TASK_ID and AGENT_ID required")
        return
    
    if not LLM_API_KEY:
        logger.error("LLM_API_KEY required")
        await update_task_status("failed", "Missing LLM_API_KEY")
        return
    
    # Phase 3.5 + Phase 5: Setup GitHub workspace with proper branch naming
    await setup_github_workspace()

    # Fetch task
    task = await fetch_task()
    if not task:
        logger.error(f"Could not fetch task {TASK_ID}")
        await update_task_status("failed", "Could not fetch task")
        return
    
    task_desc = task.get("description", "No description")
    logger.info(f"Task: {task_desc}")
    
    await update_task_status("in_progress")
    await report_event("agent.started", {"task": task_desc[:200]})
    
    # Create LLM instance
    llm = LLM(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
    )
    
    # Create agent with default tools using pre-configured helper
    # cli_mode=True disables browser tools for CLI/sandbox usage
    agent = get_default_agent(llm=llm, cli_mode=True)
    
    # Create conversation with message injection callback
    _conversation = Conversation(
        agent=agent,
        workspace="/workspace",
        callbacks=[create_event_callback()],
    )
    
    # Register with server for Guardian observation
    await register_conversation(str(_conversation.state.id))
    
    # Send task and run
    logger.info("Sending task to agent...")
    _conversation.send_message(task_desc)
    
    try:
        _conversation.run()
        
        if _should_stop:
            logger.warning("Agent stopped due to interrupt")
            await update_task_status("completed", "Stopped by interrupt")
            await report_event("agent.completed", {"success": True, "interrupted": True})
        else:
            logger.info("Agent completed successfully")
            await update_task_status("completed", "Task completed successfully")
            await report_event("agent.completed", {"success": True})
            
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        await update_task_status("failed", str(e))
        await report_event("agent.failed", {"error": str(e)})


if __name__ == "__main__":
    asyncio.run(main())
'''

    def _get_claude_worker_script(self) -> str:
        """Get the Claude Agent SDK worker script content.

        Reads from backend/omoi_os/workers/claude_sandbox_worker.py
        This makes the script easier to edit and test independently.

        Features:
        - Comprehensive event tracking (full content, no truncation)
        - Subagent support (code-reviewer, test-runner, architect, debugger)
        - Skills support (loads from .claude/skills/)
        - GitHub repo cloning
        - Message injection and intervention handling
        - Custom model/API support (Z.AI GLM, etc.)
        """
        # Try to read from file first (development mode)
        worker_file = (
            Path(__file__).parent.parent / "workers" / "claude_sandbox_worker.py"
        )
        if worker_file.exists():
            logger.info(f"Loading Claude worker script from {worker_file}")
            return worker_file.read_text()

        # Fallback to inline script if file not found (should not happen in normal operation)
        logger.warning("Claude worker file not found, using minimal fallback")
        return '''#!/usr/bin/env python3
"""Standalone sandbox worker - runs Claude Agent SDK for a task.

SDK Reference: https://github.com/anthropics/claude-agent-sdk-python
Local Docs: docs/libraries/claude-agent-sdk-python-clean.md

Phase 3: HTTP Callbacks and Message Injection
- Reports events via POST /api/v1/sandboxes/{sandbox_id}/events
- Polls GET /api/v1/sandboxes/{sandbox_id}/messages for injected messages
- PreToolUse hook checks for pending messages (sub-second intervention)

Phase 3.5: GitHub Clone Integration
- Clones repository on startup if GITHUB_TOKEN provided
- Checks out feature branch if BRANCH_NAME specified
"""

import asyncio
import os
import logging
import subprocess
from pathlib import Path
from typing import Any, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
TASK_ID = os.environ.get("TASK_ID")
AGENT_ID = os.environ.get("AGENT_ID")
SANDBOX_ID = os.environ.get("SANDBOX_ID", "")
# Base URL without /mcp suffix for API calls
BASE_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:18000").replace("/mcp", "").rstrip("/")

# Anthropic / Z.AI API configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", os.environ.get("LLM_API_KEY", ""))
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "")  # Custom API endpoint (e.g., Z.AI)
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", "claude-sonnet-4-5-20250929"))

# GitHub configuration (Phase 3.5)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # format: owner/repo
BRANCH_NAME = os.environ.get("BRANCH_NAME")

# Phase 5: Additional environment variables for branch workflow
TICKET_ID = os.environ.get("TICKET_ID")  # For GitFlow branch naming
TICKET_TITLE = os.environ.get("TICKET_TITLE", "")
TICKET_TYPE = os.environ.get("TICKET_TYPE", "feature")
USER_ID = os.environ.get("USER_ID", "")

# Phase 6: Injected task data from orchestrator (eliminates need for API fetch)
# Task data is base64-encoded to avoid shell escaping issues
TASK_DATA_BASE64 = os.environ.get("TASK_DATA_BASE64")
WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", "/workspace")

# Global state for message injection
_pending_messages: List[dict] = []
_should_stop: bool = False


# ============================================================================
# GITHUB CLONE SETUP (Phase 3.5 + Phase 5 Integration)
# ============================================================================

async def create_branch_via_api():
    """Call BranchWorkflowService API to create properly named branch.
    
    Phase 5: Uses BranchWorkflowService for GitFlow-compliant branch naming.
    Returns the branch name if successful, None otherwise.
    """
    import httpx
    
    if not GITHUB_REPO or not TICKET_ID or not USER_ID:
        logger.info("Missing GITHUB_REPO, TICKET_ID, or USER_ID - skipping API branch creation")
        return None
    
    # Parse owner/repo
    parts = GITHUB_REPO.split("/")
    if len(parts) != 2:
        logger.error(f"Invalid GITHUB_REPO format: {GITHUB_REPO}")
        return None
    owner, repo = parts
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/branch-workflow/start",
                json={
                    "ticket_id": TICKET_ID,
                    "ticket_title": TICKET_TITLE or f"Task {TICKET_ID}",
                    "repo_owner": owner,
                    "repo_name": repo,
                    "user_id": USER_ID,
                    "ticket_type": TICKET_TYPE,
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    branch_name = data.get("branch_name")
                    logger.info(f"Branch created via API: {branch_name}")
                    return branch_name
                else:
                    logger.warning(f"Branch creation failed: {data.get('error')}")
            else:
                logger.warning(f"Branch API returned {resp.status_code}")
    except Exception as e:
        logger.warning(f"Failed to create branch via API: {e}")
    
    return None


def clone_repo(branch_name: str | None = None):
    """Clone GitHub repo and checkout branch. Called on startup.

    Phase 3.5: Clones repository if GITHUB_TOKEN and GITHUB_REPO are set.
    Phase 5: Uses branch_name from BranchWorkflowService if provided,
             otherwise falls back to BRANCH_NAME env var.
    Phase 6: Skips clone if WORKSPACE_PATH already contains a git repo
             (spawner uses sandbox.git.clone() directly).
    """
    # Phase 6: Check if workspace was already cloned by spawner
    if os.path.exists(os.path.join(WORKSPACE_PATH, ".git")):
        logger.info(f"Workspace {WORKSPACE_PATH} already has a git repo - skipping clone")
        return True
    
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logger.info("No GitHub credentials, skipping repo clone")
        return False

    # Use provided branch_name or fall back to env var
    target_branch = branch_name or BRANCH_NAME

    # Configure git user for commits
    subprocess.run(["git", "config", "--global", "user.email", "agent@omoios.ai"], check=False)
    subprocess.run(["git", "config", "--global", "user.name", "OmoiOS Agent"], check=False)
    
    # Build authenticated clone URL
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
    
    logger.info(f"Cloning {GITHUB_REPO}...")
    result = subprocess.run(
        ["git", "clone", clone_url, "/workspace"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.error(f"Clone failed: {result.stderr}")
        return False
    
    os.chdir("/workspace")
    
    # Checkout branch if specified
    if target_branch:
        logger.info(f"Checking out branch: {target_branch}")
        # Try to checkout existing branch (created via API)
        result = subprocess.run(
            ["git", "checkout", target_branch],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            # Branch doesn't exist remotely, create it locally
            logger.info(f"Creating new branch locally: {target_branch}")
            subprocess.run(["git", "checkout", "-b", target_branch], check=False)
    
    logger.info("Repository ready at /workspace")
    return True


async def setup_github_workspace():
    """Setup GitHub workspace with proper branch naming.
    
    Phase 5 Integration: 
    1. Calls BranchWorkflowService API to create properly named branch
    2. Clones repo and checks out the branch
    """
    # Try to create branch via API (Phase 5)
    branch_name = await create_branch_via_api()
    
    # Clone repo (will use API branch name or fall back to BRANCH_NAME env var)
    return clone_repo(branch_name)


# ============================================================================
# HTTP CALLBACK FUNCTIONS (Phase 3)
# ============================================================================

async def fetch_task():
    """Fetch task details - uses injected data first, falls back to API.
    
    Phase 6: The orchestrator injects TASK_DATA_BASE64 with full task context,
    eliminating the need for an API call.
    """
    import json
    import base64
    import httpx
    
    # First: Check for injected task data (Phase 6 - base64 encoded)
    if TASK_DATA_BASE64:
        try:
            task_json = base64.b64decode(TASK_DATA_BASE64).decode()
            task_data = json.loads(task_json)
            logger.info("Using injected task data from orchestrator")
            return {
                "id": task_data.get("task_id"),
                "description": task_data.get("task_description") or task_data.get("ticket_description") or task_data.get("ticket_title"),
                "task_type": task_data.get("task_type"),
                "priority": task_data.get("task_priority"),
                "phase_id": task_data.get("phase_id"),
                "ticket_id": task_data.get("ticket_id"),
                "ticket_title": task_data.get("ticket_title"),
                "ticket_description": task_data.get("ticket_description"),
                "ticket_context": task_data.get("ticket_context", {}),
            }
        except Exception as e:
            logger.warning(f"Failed to decode TASK_DATA_BASE64: {e}, falling back to API")
    
    # Fallback: Fetch from API
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BASE_URL}/api/v1/tasks/{TASK_ID}")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch task: {e}")
    return None


async def report_status(status: str, result: str = None):
    """Report task status back to orchestrator."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.patch(
                f"{BASE_URL}/api/v1/tasks/{TASK_ID}",
                json={"status": status, "result": result},
            )
    except Exception as e:
        logger.debug(f"Failed to report status: {e}")


async def report_event(event_type: str, event_data: dict, source: str = "agent"):
    """Report an agent event via sandbox callback endpoint.
    
    Phase 3: Uses POST /api/v1/sandboxes/{sandbox_id}/events
    """
    import httpx
    if not SANDBOX_ID:
        logger.debug("No SANDBOX_ID, skipping event report")
        return
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BASE_URL}/api/v1/sandboxes/{SANDBOX_ID}/events",
                json={
                    "event_type": event_type,
                    "event_data": {
                        **event_data,
                        "task_id": TASK_ID,
                        "agent_id": AGENT_ID,
                    },
                    "source": source,
                },
            )
    except Exception as e:
        logger.debug(f"Failed to report event: {e}")


async def poll_messages() -> List[dict]:
    """Poll for pending messages from the message queue.
    
    Phase 3: Uses GET /api/v1/sandboxes/{sandbox_id}/messages
    Messages are consumed (cleared) after retrieval.
    
    Returns:
        List of message dicts with content, message_type, timestamp
    """
    import httpx
    if not SANDBOX_ID:
        return []
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BASE_URL}/api/v1/sandboxes/{SANDBOX_ID}/messages")
            if resp.status_code == 200:
                messages = resp.json()
                if messages:
                    logger.info(f"Received {len(messages)} injected message(s)")
                return messages
    except Exception as e:
        logger.debug(f"Failed to poll messages: {e}")
    return []


def process_messages(messages: List[dict]) -> Optional[str]:
    """Process injected messages and return context to inject.
    
    Handles message types:
    - user_message: Guidance from user
    - guardian_nudge: Suggestion from Guardian
    - interrupt: Stop current work immediately
    - system: System notification
    
    Returns:
        Context string to inject, or None
    """
    global _should_stop
    
    context_parts = []
    
    for msg in messages:
        msg_type = msg.get("message_type", "user_message")
        content = msg.get("content", "")
        
        if msg_type == "interrupt":
            logger.warning(f"INTERRUPT received: {content}")
            _should_stop = True
            return f"⚠️ INTERRUPT: {content}. Stop current work immediately."
        
        elif msg_type == "guardian_nudge":
            context_parts.append(f"💡 Guardian suggests: {content}")
        
        elif msg_type == "user_message":
            context_parts.append(f"📝 User message: {content}")
        
        elif msg_type == "system":
            context_parts.append(f"🔔 System: {content}")
    
    if context_parts:
        return "\\n".join(context_parts)
    return None


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

def create_tools():
    """Create custom tools for the Claude agent."""
    from claude_agent_sdk import tool, create_sdk_mcp_server
    
    @tool("read_file", "Read contents of a file", {"file_path": str})
    async def read_file(args: dict[str, Any]) -> dict[str, Any]:
        file_path = Path(args["file_path"])
        try:
            content = file_path.read_text()
            return {"content": [{"type": "text", "text": content}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}
    
    @tool("write_file", "Write contents to a file", {"file_path": str, "content": str})
    async def write_file(args: dict[str, Any]) -> dict[str, Any]:
        file_path = Path(args["file_path"])
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(args["content"])
            asyncio.create_task(report_event("agent.file_written", {"path": str(file_path)}))
            return {"content": [{"type": "text", "text": f"Wrote to {file_path}"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}
    
    @tool("run_command", "Execute a shell command", {"command": str})
    async def run_command(args: dict[str, Any]) -> dict[str, Any]:
        command = args["command"]
        try:
            asyncio.create_task(report_event("agent.command_started", {"command": command}))
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300, cwd="/workspace")
            asyncio.create_task(report_event("agent.command_completed", {"command": command, "exit_code": result.returncode}))
            return {"content": [{"type": "text", "text": f"Exit: {result.returncode}\\nStdout: {result.stdout}\\nStderr: {result.stderr}"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}
    
    @tool("list_files", "List files in a directory", {"directory": str})
    async def list_files(args: dict[str, Any]) -> dict[str, Any]:
        directory = Path(args["directory"])
        try:
            files = ["[DIR] " + item.name if item.is_dir() else "[FILE] " + item.name for item in directory.iterdir()]
            return {"content": [{"type": "text", "text": "\\n".join(files) or "(empty)"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}
    
    server = create_sdk_mcp_server("workspace", tools=[read_file, write_file, run_command, list_files])
    return server, ["mcp__workspace__read_file", "mcp__workspace__write_file", "mcp__workspace__run_command", "mcp__workspace__list_files"]


# ============================================================================
# AGENT EXECUTION WITH MULTI-TURN MESSAGE INJECTION (Fixed Pattern)
# ============================================================================

async def run_agent(task_description: str):
    """Run the Claude Agent SDK with proper multi-turn message injection.
    
    FIXED: Uses receive_messages() for indefinite streaming and client.query()
    for real message injection (matching Claude Code web behavior).
    """
    from claude_agent_sdk import (
        ClaudeAgentOptions, 
        ClaudeSDKClient, 
        HookMatcher,
        # Message types
        AssistantMessage,
        UserMessage,
        SystemMessage,
        ResultMessage,
        # Content blocks
        TextBlock,
        ThinkingBlock,
        ToolUseBlock,
        ToolResultBlock,
    )
    
    tools_server, tool_names = create_tools()
    global _should_stop
    
    # PostToolUse hook: Report tool usage for Guardian observation
    async def track_tool_use(input_data, tool_use_id, context):
        """PostToolUse hook for comprehensive event reporting."""
        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", "")

        # Serialize tool_response properly
        # Claude SDK tool results (like CLIResult) are objects with stdout/stderr fields
        # We need to extract just the stdout content for display
        serialized_response = None
        if tool_response:
            if hasattr(tool_response, "stdout"):
                # CLIResult-like object from Bash tool
                serialized_response = tool_response.stdout or ""
                if hasattr(tool_response, "stderr") and tool_response.stderr:
                    serialized_response += f"\n[stderr]: {tool_response.stderr}"
            elif hasattr(tool_response, "__dict__"):
                # Generic object - try to serialize nicely
                import json
                try:
                    serialized_response = json.dumps(tool_response.__dict__, default=str)
                except (TypeError, ValueError):
                    serialized_response = str(tool_response)
            else:
                serialized_response = str(tool_response)

        # Comprehensive tool tracking with full details
        event_data = {
            "tool": tool_name,
            "tool_input": tool_input,  # Full input, no truncation
            "tool_response": serialized_response,  # Properly serialized response
        }
        
        # Special tracking for subagents
        if tool_name == "Task":
            event_data["subagent_type"] = tool_input.get("subagent_type")
            event_data["description"] = tool_input.get("description")
            event_data["prompt"] = tool_input.get("prompt")
            await report_event("agent.subagent_completed", event_data)
        # Special tracking for skills
        elif tool_name == "Skill":
            event_data["skill_name"] = tool_input.get("name") or tool_input.get("skill_name")
            await report_event("agent.skill_completed", event_data)
        else:
            await report_event("agent.tool_completed", event_data)
        
        return {}
    
    # Define custom subagents for specialized tasks
    custom_agents = {
        "code-reviewer": {
            "description": "Expert code review specialist. Use for security, quality, and maintainability reviews.",
            "prompt": """You are a code review specialist with expertise in security, performance, and best practices.
When reviewing code:
- Identify security vulnerabilities and injection risks
- Check for performance issues and memory leaks
- Verify adherence to coding standards
- Suggest specific, actionable improvements
Be thorough but concise in your feedback.""",
            "tools": ["Read", "Grep", "Glob"],
            "model": "sonnet"
        },
        "test-runner": {
            "description": "Runs and analyzes test suites. Use for test execution and coverage analysis.",
            "prompt": """You are a test execution specialist. Run tests and provide clear analysis of results.
Focus on:
- Running test commands (pytest, npm test, etc.)
- Analyzing test output and identifying patterns
- Identifying failing tests and their root causes
- Suggesting fixes for test failures""",
            "tools": ["Bash", "Read", "Grep"],
        },
        "architect": {
            "description": "Software architecture specialist. Use for design decisions and codebase structure.",
            "prompt": """You are a software architecture specialist.
Analyze code structure, identify patterns, suggest architectural improvements.
Focus on:
- Module organization and dependencies
- Design patterns and anti-patterns
- Scalability and maintainability concerns
- API design and contracts""",
            "tools": ["Read", "Grep", "Glob"],
        },
        "debugger": {
            "description": "Debugging specialist. Use for investigating bugs and unexpected behavior.",
            "prompt": """You are a debugging specialist.
Systematically investigate issues:
- Reproduce the problem
- Add logging/tracing to narrow down the cause
- Identify root causes
- Propose and test fixes""",
            "tools": ["Read", "Bash", "Edit", "Grep"],
        }
    }
    
    options = ClaudeAgentOptions(
        # Core tools + Subagents + Skills
        allowed_tools=tool_names + [
            "Read", "Write", "Bash", "Edit", "Glob", "Grep",  # Standard tools
            "Task",  # Subagent dispatch
            "Skill",  # Skill invocation
        ],
        permission_mode="bypassPermissions",
        system_prompt=f"""You are an AI coding agent. Your workspace is /workspace. Be thorough and test your changes.

You have access to specialized subagents:
- code-reviewer: For security and quality code reviews
- test-runner: For running and analyzing tests
- architect: For design decisions and structure analysis
- debugger: For investigating bugs

You also have access to Skills loaded from .claude/skills/ directories.
Use subagents and skills when they can help accomplish the task more effectively.""",
        cwd=Path("/workspace"),
        max_turns=50,
        max_budget_usd=10.0,
        model=ANTHROPIC_MODEL,
        mcp_servers={"workspace": tools_server},
        # Enable skills loading
        setting_sources=["user", "project"],
        # Custom subagents
        agents=custom_agents,
        hooks={
            "PostToolUse": [HookMatcher(matcher=None, hooks=[track_tool_use])],
        },
    )
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            # Start with initial task
            await client.query(task_description)
            await report_event("agent.started", {
                "task": task_description,  # Full task description
                "model": ANTHROPIC_MODEL,
                "sandbox_id": SANDBOX_ID,
                "agent_id": AGENT_ID,
                "task_id": TASK_ID,
            })
            
            # Message queue for streaming
            message_queue = asyncio.Queue()
            agent_done = asyncio.Event()
            final_output = []
            turn_count = 0
            
            async def message_stream():
                """Stream messages from Claude and map to our event types with full details."""
                nonlocal turn_count
                try:
                    async for msg in client.receive_messages():  # Indefinite streaming
                        # Map SDK messages to our event types
                        if isinstance(msg, AssistantMessage):
                            turn_count += 1
                            # Report full assistant message metadata
                            await report_event("agent.assistant_message", {
                                "turn": turn_count,
                                "model": getattr(msg, "model", ANTHROPIC_MODEL),
                                "stop_reason": getattr(msg, "stop_reason", None),
                                "block_count": len(msg.content),
                            })
                            
                            for block in msg.content:
                                if isinstance(block, ThinkingBlock):
                                    # Full thinking content
                                    await report_event("agent.thinking", {
                                        "turn": turn_count,
                                        "content": block.text,  # Full content, no truncation
                                        "thinking_type": "extended_thinking",
                                    })
                                    
                                elif isinstance(block, ToolUseBlock):
                                    # Comprehensive tool use tracking
                                    tool_event = {
                                        "turn": turn_count,
                                        "tool": block.name,
                                        "tool_use_id": block.id,
                                        "input": block.input,  # Full input dict, no truncation
                                    }
                                    
                                    # Special handling for subagent dispatch
                                    if block.name == "Task":
                                        tool_event["event_subtype"] = "subagent_invoked"
                                        tool_event["subagent_type"] = block.input.get("subagent_type")
                                        tool_event["subagent_description"] = block.input.get("description")
                                        tool_event["subagent_prompt"] = block.input.get("prompt")
                                        await report_event("agent.subagent_invoked", tool_event)
                                    
                                    # Special handling for skill invocation
                                    elif block.name == "Skill":
                                        tool_event["event_subtype"] = "skill_invoked"
                                        tool_event["skill_name"] = block.input.get("name") or block.input.get("skill_name")
                                        await report_event("agent.skill_invoked", tool_event)
                                    
                                    # Standard tool use
                                    else:
                                        tool_event["event_subtype"] = "tool_use"
                                        await report_event("agent.tool_use", tool_event)
                                
                                elif isinstance(block, ToolResultBlock):
                                    # Full tool result with reasonable limit for very large outputs
                                    result_content = str(block.content)
                                    await report_event("agent.tool_result", {
                                        "turn": turn_count,
                                        "tool_use_id": block.tool_use_id,
                                        "result": result_content[:5000] if len(result_content) > 5000 else result_content,
                                        "result_truncated": len(result_content) > 5000,
                                        "result_full_length": len(result_content),
                                        "is_error": getattr(block, "is_error", False),
                                    })
                                
                                elif isinstance(block, TextBlock):
                                    # Full text content
                                    await report_event("agent.message", {
                                        "turn": turn_count,
                                        "content": block.text,  # Full content, no truncation
                                        "content_length": len(block.text),
                                    })
                                    final_output.append(block.text)
                        
                        elif isinstance(msg, UserMessage):
                            # Track user messages (tool results, injected messages)
                            for block in msg.content:
                                if isinstance(block, TextBlock):
                                    await report_event("agent.user_message", {
                                        "turn": turn_count,
                                        "content": block.text,
                                        "content_length": len(block.text),
                                    })
                                elif isinstance(block, ToolResultBlock):
                                    result_content = str(block.content)
                                    await report_event("agent.user_tool_result", {
                                        "turn": turn_count,
                                        "tool_use_id": block.tool_use_id,
                                        "result": result_content[:5000] if len(result_content) > 5000 else result_content,
                                        "result_truncated": len(result_content) > 5000,
                                    })
                        
                        elif isinstance(msg, SystemMessage):
                            # Track system messages
                            await report_event("agent.system_message", {
                                "turn": turn_count,
                                "metadata": getattr(msg, "metadata", {}),
                            })
                        
                        elif isinstance(msg, ResultMessage):
                            # Comprehensive completion event
                            usage = getattr(msg, "usage", None)
                            await report_event("agent.completed", {
                                "success": True,
                                "turns": msg.num_turns,
                                "cost_usd": msg.total_cost_usd,
                                "session_id": msg.session_id,
                                "stop_reason": getattr(msg, "stop_reason", None),
                                "input_tokens": usage.input_tokens if usage else None,
                                "output_tokens": usage.output_tokens if usage else None,
                                "cache_read_tokens": getattr(usage, "cache_read_input_tokens", None) if usage else None,
                                "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", None) if usage else None,
                                "task_id": TASK_ID,
                                "agent_id": AGENT_ID,
                            })
                            final_output.append(f"Completed: {msg.num_turns} turns, ${msg.total_cost_usd:.4f}")
                            agent_done.set()
                            break
                        
                        await message_queue.put(msg)
                except Exception as e:
                    logger.error(f"Message stream error: {e}")
                    await report_event("agent.stream_error", {
                        "error": str(e),
                        "turn": turn_count,
                        "task_id": TASK_ID,
                    })
                    agent_done.set()
            
            async def intervention_handler():
                """Poll for interventions and inject as new user messages."""
                global _should_stop
                poll_interval = 0.5  # Poll every 500ms
                intervention_count = 0
                
                while not agent_done.is_set():
                    try:
                        # Check for interrupt first
                        if _should_stop:
                            logger.warning("Interrupt received, stopping agent")
                            await client.interrupt()
                            await report_event("agent.interrupted", {
                                "reason": "user_interrupt",
                                "turn": turn_count,
                                "task_id": TASK_ID,
                                "agent_id": AGENT_ID,
                            })
                            agent_done.set()
                            break
                        
                        # Poll for new messages
                        messages = await poll_messages()
                        if messages:
                            for msg in messages:
                                intervention_count += 1
                                msg_type = msg.get("message_type", "user_message")
                                content = msg.get("content", "")
                                sender_id = msg.get("sender_id")
                                message_id = msg.get("message_id")
                                
                                if msg_type == "interrupt":
                                    logger.warning(f"INTERRUPT: {content}")
                                    _should_stop = True
                                    await client.interrupt()
                                    await report_event("agent.interrupted", {
                                        "reason": content,
                                        "sender_id": sender_id,
                                        "turn": turn_count,
                                        "task_id": TASK_ID,
                                        "agent_id": AGENT_ID,
                                    })
                                    agent_done.set()
                                    break
                                
                                elif msg_type in ["user_message", "guardian_nudge"]:
                                    # Inject as NEW USER MESSAGE (like Claude Code web)
                                    logger.info(f"Injecting message: {content[:100]}")
                                    await report_event("agent.message_injected", {
                                        "message_type": msg_type,
                                        "content": content,  # Full content, no truncation
                                        "content_length": len(content),
                                        "sender_id": sender_id,
                                        "message_id": message_id,
                                        "intervention_number": intervention_count,
                                        "turn": turn_count,
                                        "task_id": TASK_ID,
                                        "agent_id": AGENT_ID,
                                    })
                                    await client.query(content)  # ← Real message injection
                        
                        await asyncio.sleep(poll_interval)
                    except Exception as e:
                        logger.error(f"Intervention handler error: {e}")
                        await asyncio.sleep(poll_interval)
            
            # Run message streaming and intervention handling concurrently
            await asyncio.gather(
                message_stream(),
                intervention_handler(),
                return_exceptions=True
            )
            
            # Wait a bit for final messages
            try:
                await asyncio.wait_for(agent_done.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
            
            result_text = "\\n".join(final_output[-10:]) if final_output else "No output"
            return True, result_text
            
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        await report_event("agent.error", {"error": str(e)})
        return False, str(e)


async def main():
    logger.info(f"Claude Agent Worker starting for task {TASK_ID}")
    logger.info(f"Sandbox ID: {SANDBOX_ID}")
    logger.info(f"Backend URL: {BASE_URL}")
    logger.info(f"Anthropic Base URL: {ANTHROPIC_BASE_URL or 'default'}")
    logger.info(f"Model: {ANTHROPIC_MODEL}")
    
    if not TASK_ID or not AGENT_ID:
        logger.error("TASK_ID and AGENT_ID required")
        return
    
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY required")
        await report_status("failed", "Missing ANTHROPIC_API_KEY")
        return
    
    # Phase 3.5 + Phase 5: Setup GitHub workspace with proper branch naming
    await setup_github_workspace()

    # Set Anthropic/Z.AI environment variables
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    if ANTHROPIC_BASE_URL:
        os.environ["ANTHROPIC_BASE_URL"] = ANTHROPIC_BASE_URL
        logger.info(f"Using custom Anthropic API: {ANTHROPIC_BASE_URL}")
    logger.info(f"Using model: {ANTHROPIC_MODEL}")
    
    task = await fetch_task()
    if not task:
        await report_status("failed", "Could not fetch task")
        return
    
    task_desc = task.get("description", "No description")
    logger.info(f"Task: {task_desc}")
    
    await report_status("in_progress")
    await report_event("agent.started", {"task": task_desc[:200]})
    
    success, result = await run_agent(task_desc)
    
    if success:
        await report_status("completed", result)
        await report_event("agent.completed", {"success": True})
    else:
        await report_status("failed", result)
        await report_event("agent.failed", {"error": result})


if __name__ == "__main__":
    asyncio.run(main())
'''

    async def _create_mock_sandbox(
        self,
        sandbox_id: str,
        env_vars: Dict[str, str],
    ) -> None:
        """Create a mock sandbox for local testing without Daytona."""

        logger.info(f"Creating mock sandbox {sandbox_id}")

        # In mock mode, we could:
        # 1. Run the worker locally in a subprocess
        # 2. Just log and pretend (for unit tests)
        # 3. Use Docker directly

        # For now, just log - the sandbox_worker can be run manually
        logger.info("Mock sandbox created. To run manually:")
        logger.info(f"  AGENT_ID={env_vars.get('AGENT_ID')} \\")
        logger.info(f"  TASK_ID={env_vars.get('TASK_ID')} \\")
        logger.info(f"  MCP_SERVER_URL={env_vars.get('MCP_SERVER_URL')} \\")
        logger.info("  python -m omoi_os.sandbox_worker")

    async def terminate_sandbox(self, sandbox_id: str) -> bool:
        """Terminate a running sandbox.

        Args:
            sandbox_id: Sandbox to terminate

        Returns:
            True if terminated successfully
        """
        info = self._sandboxes.get(sandbox_id)
        task_id = None

        # Case 1: Sandbox is in memory - use cached info
        if info:
            if info.status in ("completed", "failed", "terminated"):
                logger.info(f"Sandbox {sandbox_id} already stopped")
                return True

            task_id = info.task_id

            try:
                # Get Daytona sandbox reference from cache
                daytona_sandbox = info.extra_data.get("daytona_sandbox")

                if daytona_sandbox:
                    # Terminate via cached Daytona object
                    daytona_sandbox.stop()
                    logger.info(
                        f"Daytona sandbox {sandbox_id} terminated via cached reference"
                    )

                info.status = "terminated"
                info.completed_at = utc_now()

                if self.event_bus:
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="sandbox.terminated",
                            entity_type="sandbox",
                            entity_id=sandbox_id,
                            payload={"task_id": task_id},
                        )
                    )

                return True

            except Exception as e:
                logger.error(f"Failed to terminate sandbox {sandbox_id} via cache: {e}")
                # Fall through to direct API termination below

        # Case 2: Sandbox NOT in memory (e.g., after worker restart)
        # or Case 1 failed - use Daytona API directly
        logger.info(f"Attempting direct Daytona API termination for {sandbox_id}")

        try:
            from daytona import Daytona, DaytonaConfig

            daytona_settings = load_daytona_settings()
            config = DaytonaConfig(
                api_key=self.daytona_api_key or daytona_settings.api_key,
                api_url=self.daytona_api_url or daytona_settings.api_url,
                target="us",
            )

            daytona = Daytona(config)

            try:
                sandbox = daytona.get(sandbox_id)
                sandbox.stop()
                logger.info(f"Daytona sandbox {sandbox_id} terminated via direct API")

                # Update in-memory cache if it exists
                if info:
                    info.status = "terminated"
                    info.completed_at = utc_now()

                if self.event_bus:
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="sandbox.terminated",
                            entity_type="sandbox",
                            entity_id=sandbox_id,
                            payload={"task_id": task_id},
                        )
                    )

                return True

            except Exception as get_err:
                # Sandbox doesn't exist in Daytona - might already be terminated
                error_str = str(get_err).lower()
                if "not found" in error_str or "404" in error_str:
                    logger.info(
                        f"Sandbox {sandbox_id} not found in Daytona (already terminated?)"
                    )
                    # Update in-memory cache if it exists
                    if info:
                        info.status = "terminated"
                        info.completed_at = utc_now()
                    return True
                else:
                    raise

        except Exception as e:
            logger.error(
                f"Failed to terminate sandbox {sandbox_id} via direct API: {e}"
            )
            return False

    def _get_continuous_worker_script(self) -> str:
        """Get the Continuous Sandbox Worker script content.

        DEPRECATED: Use _get_claude_worker_script() instead.
        Continuous mode is now integrated into the base claude_sandbox_worker.py
        and is controlled via the CONTINUOUS_MODE environment variable.

        This method now just returns the base Claude worker script.
        """
        logger.info(
            "Note: Continuous mode is now integrated into base Claude worker. "
            "Using claude_sandbox_worker.py with CONTINUOUS_MODE env var."
        )
        return self._get_claude_worker_script()

    def mark_completed(self, sandbox_id: str, result: Optional[Dict] = None) -> None:
        """Mark a sandbox as completed (called when task finishes)."""
        info = self._sandboxes.get(sandbox_id)
        if info:
            info.status = "completed"
            info.completed_at = utc_now()
            if result:
                info.extra_data["result"] = result

            if self.auto_cleanup:
                asyncio.create_task(self.terminate_sandbox(sandbox_id))

    def mark_failed(self, sandbox_id: str, error: str) -> None:
        """Mark a sandbox as failed."""
        info = self._sandboxes.get(sandbox_id)
        if info:
            info.status = "failed"
            info.completed_at = utc_now()
            info.error = error

            if self.auto_cleanup:
                asyncio.create_task(self.terminate_sandbox(sandbox_id))

    def get_sandbox_info(self, sandbox_id: str) -> Optional[SandboxInfo]:
        """Get information about a sandbox."""
        return self._sandboxes.get(sandbox_id)

    def get_sandbox_for_task(self, task_id: str) -> Optional[SandboxInfo]:
        """Get sandbox info for a task."""
        sandbox_id = self._task_to_sandbox.get(task_id)
        if sandbox_id:
            return self._sandboxes.get(sandbox_id)
        return None

    async def get_sandbox_logs(
        self, sandbox_id: str, lines: int = 100, follow: bool = False
    ) -> Optional[str]:
        """Get logs from a Daytona sandbox.

        Args:
            sandbox_id: Sandbox ID to get logs from
            lines: Number of recent lines to retrieve (default: 100)
            follow: If True, continuously stream logs (not implemented yet)

        Returns:
            Log content as string, or None if sandbox not found or error
        """
        info = self._sandboxes.get(sandbox_id)
        if not info:
            logger.warning(f"Sandbox {sandbox_id} not found in tracked sandboxes")
            return None

        try:
            from daytona import Daytona, DaytonaConfig

            daytona_settings = load_daytona_settings()
            config = DaytonaConfig(
                api_key=self.daytona_api_key or daytona_settings.api_key,
                api_url=self.daytona_api_url or daytona_settings.api_url,
                target="us",
            )

            daytona = Daytona(config)
            sandbox = daytona.get(sandbox_id)

            # Get recent log lines
            result = sandbox.process.exec(
                f"tail -n {lines} /tmp/worker.log 2>/dev/null || echo '[Log file not found or empty]'"
            )
            output = result.result if hasattr(result, "result") else str(result)
            return output if output.strip() != "[Log file not found or empty]" else None

        except Exception as e:
            logger.error(f"Failed to get logs for sandbox {sandbox_id}: {e}")
            return None

    async def get_full_sandbox_logs(self, sandbox_id: str) -> Optional[str]:
        """Get full logs from a Daytona sandbox.

        Args:
            sandbox_id: Sandbox ID to get logs from

        Returns:
            Full log content as string, or None if sandbox not found or error
        """
        info = self._sandboxes.get(sandbox_id)
        if not info:
            logger.warning(f"Sandbox {sandbox_id} not found in tracked sandboxes")
            return None

        try:
            from daytona import Daytona, DaytonaConfig

            daytona_settings = load_daytona_settings()
            config = DaytonaConfig(
                api_key=self.daytona_api_key or daytona_settings.api_key,
                api_url=self.daytona_api_url or daytona_settings.api_url,
                target="us",
            )

            daytona = Daytona(config)
            sandbox = daytona.get(sandbox_id)

            # Get full log file
            result = sandbox.process.exec(
                "cat /tmp/worker.log 2>/dev/null || echo '[Log file not found]'"
            )
            output = result.result if hasattr(result, "result") else str(result)
            return output if output.strip() != "[Log file not found]" else None

        except Exception as e:
            logger.error(f"Failed to get full logs for sandbox {sandbox_id}: {e}")
            return None

    async def extract_session_transcript(
        self, sandbox_id: str, session_id: Optional[str] = None
    ) -> Optional[str]:
        """Extract the session transcript from a sandbox before termination.

        Searches for JSONL transcript files in the Claude sessions directory
        and returns the most recent one as base64-encoded content.

        Args:
            sandbox_id: Sandbox ID to extract transcript from
            session_id: Optional specific session ID to extract. If not provided,
                       extracts the most recent session transcript.

        Returns:
            Base64-encoded transcript content, or None if not found/error
        """
        info = self._sandboxes.get(sandbox_id)
        if not info:
            logger.warning(f"Sandbox {sandbox_id} not found for transcript extraction")
            return None

        try:
            daytona_sandbox = info.extra_data.get("daytona_sandbox")
            if not daytona_sandbox:
                logger.warning(f"No Daytona sandbox reference for {sandbox_id}")
                return None

            import base64

            # Claude Code stores sessions in ~/.claude/projects/<project_key>/<session_id>.jsonl
            # We need to find the .jsonl file in the sessions directory
            claude_dir = "/root/.claude/projects"

            try:
                # List project directories
                projects = daytona_sandbox.fs.list_files(claude_dir)
                if not projects:
                    logger.debug(f"No Claude projects found in sandbox {sandbox_id}")
                    return None

                # For each project directory, find .jsonl files
                transcript_files = []
                for project in projects:
                    if hasattr(project, "is_dir") and project.is_dir:
                        project_path = f"{claude_dir}/{project.name}"
                        try:
                            files = daytona_sandbox.fs.list_files(project_path)
                            for f in files:
                                if hasattr(f, "name") and f.name.endswith(".jsonl"):
                                    transcript_files.append(f"{project_path}/{f.name}")
                        except Exception:
                            continue

                if not transcript_files:
                    logger.debug(f"No transcript files found in sandbox {sandbox_id}")
                    return None

                # If a specific session_id is requested, find that file
                if session_id:
                    target_file = None
                    for f in transcript_files:
                        if session_id in f:
                            target_file = f
                            break
                    if not target_file:
                        logger.debug(
                            f"Session {session_id} not found in sandbox {sandbox_id}"
                        )
                        return None
                    transcript_path = target_file
                else:
                    # Get the most recent transcript (last in list typically, or we could check mtime)
                    transcript_path = transcript_files[-1]

                # Download the transcript file
                logger.info(
                    f"Extracting transcript from {transcript_path} in sandbox {sandbox_id}"
                )
                content = daytona_sandbox.fs.download_file(transcript_path)

                if content:
                    # Encode to base64
                    if isinstance(content, bytes):
                        transcript_b64 = base64.b64encode(content).decode("utf-8")
                    else:
                        transcript_b64 = base64.b64encode(
                            content.encode("utf-8")
                        ).decode("utf-8")

                    logger.info(
                        f"Extracted transcript ({len(transcript_b64)} bytes base64) "
                        f"from sandbox {sandbox_id}"
                    )
                    return transcript_b64

            except Exception as e:
                logger.warning(
                    f"Failed to list/download transcripts from sandbox {sandbox_id}: {e}"
                )
                return None

        except Exception as e:
            logger.error(f"Failed to extract transcript from sandbox {sandbox_id}: {e}")
            return None

        return None

    def list_active_sandboxes(self) -> List[SandboxInfo]:
        """List all active (creating or running) sandboxes."""
        return [
            info
            for info in self._sandboxes.values()
            if info.status in ("creating", "running")
        ]

    def list_all_sandboxes(self) -> List[SandboxInfo]:
        """List all tracked sandboxes."""
        return list(self._sandboxes.values())

    async def cleanup_stale_sandboxes(self, max_age_hours: int = 24) -> int:
        """Cleanup sandboxes older than max_age_hours.

        Returns:
            Number of sandboxes cleaned up
        """
        from datetime import timedelta

        now = utc_now()
        cutoff = now - timedelta(hours=max_age_hours)
        cleaned = 0

        for sandbox_id, info in list(self._sandboxes.items()):
            if info.created_at < cutoff and info.status in ("creating", "running"):
                logger.warning(f"Cleaning up stale sandbox {sandbox_id}")
                await self.terminate_sandbox(sandbox_id)
                cleaned += 1

        return cleaned


# Global singleton
_spawner_service: Optional[DaytonaSpawnerService] = None


def get_daytona_spawner(
    db: Optional[DatabaseService] = None,
    event_bus: Optional[EventBusService] = None,
    mcp_server_url: Optional[str] = None,
    sandbox_memory_gb: Optional[int] = None,
    sandbox_cpu: Optional[int] = None,
    sandbox_disk_gb: Optional[int] = None,
    sandbox_snapshot: Optional[str] = None,
    sandbox_image: Optional[str] = None,
) -> DaytonaSpawnerService:
    """Get or create the global Daytona spawner service.

    Args:
        db: Database service
        event_bus: Event bus service
        mcp_server_url: MCP server URL
        sandbox_memory_gb: Memory in GiB (default: 4, max: 8). Can also be set via SANDBOX_MEMORY_GB env var.
        sandbox_cpu: CPU cores (default: 2, max: 4). Can also be set via SANDBOX_CPU env var.
        sandbox_disk_gb: Disk space in GiB (default: 8, max: 10). Can also be set via SANDBOX_DISK_GB env var.
        sandbox_snapshot: Snapshot name to create sandbox from (takes precedence over image). Can also be set via SANDBOX_SNAPSHOT env var.
        sandbox_image: Docker image for sandboxes (used if snapshot is None). Can also be set via SANDBOX_IMAGE env var.
    """
    global _spawner_service

    if _spawner_service is None:
        settings = get_app_settings()
        url = mcp_server_url or settings.integrations.mcp_server_url

        # Load resource limits and source from config file, then environment variables, then defaults
        # Priority: explicit param > env var > config file > default
        import os

        daytona_settings = load_daytona_settings()

        # Memory: explicit param > env var > config file > default
        if sandbox_memory_gb is not None:
            memory = sandbox_memory_gb
        elif "SANDBOX_MEMORY_GB" in os.environ:
            memory = int(os.environ.get("SANDBOX_MEMORY_GB", "4"))
        else:
            memory = daytona_settings.sandbox_memory_gb

        # CPU: explicit param > env var > config file > default
        if sandbox_cpu is not None:
            cpu = sandbox_cpu
        elif "SANDBOX_CPU" in os.environ:
            cpu = int(os.environ.get("SANDBOX_CPU", "2"))
        else:
            cpu = daytona_settings.sandbox_cpu

        # Disk: explicit param > env var > config file > default
        if sandbox_disk_gb is not None:
            disk = sandbox_disk_gb
        elif "SANDBOX_DISK_GB" in os.environ:
            disk = int(os.environ.get("SANDBOX_DISK_GB", "8"))
        else:
            disk = daytona_settings.sandbox_disk_gb

        # Snapshot takes precedence over image
        # Priority: explicit param > env var > config file > None
        if sandbox_snapshot is not None:
            snapshot = sandbox_snapshot
        elif "SANDBOX_SNAPSHOT" in os.environ:
            snapshot = os.environ.get("SANDBOX_SNAPSHOT")
        else:
            snapshot = daytona_settings.snapshot

        # Image: explicit param > env var > config file > default
        if sandbox_image is not None:
            image = sandbox_image
        elif "SANDBOX_IMAGE" in os.environ:
            image = os.environ.get("SANDBOX_IMAGE")
        else:
            image = (
                daytona_settings.image or "nikolaik/python-nodejs:python3.12-nodejs22"
            )

        _spawner_service = DaytonaSpawnerService(
            db=db,
            event_bus=event_bus,
            mcp_server_url=url,
            sandbox_memory_gb=memory,
            sandbox_cpu=cpu,
            sandbox_disk_gb=disk,
            sandbox_snapshot=snapshot,
            sandbox_image=image,
        )

    return _spawner_service


# ============================================================================
# WORKER SCRIPT EXPORTS (for testing and inspection)
# ============================================================================

# These module-level constants allow tests to verify worker script contents.
# They are created once by instantiating a minimal service instance.


def _create_worker_script_exports():
    """Create worker script exports without full service initialization."""
    # Create minimal instance just to access script methods
    service = DaytonaSpawnerService.__new__(DaytonaSpawnerService)
    return (
        service._get_worker_script(),
        service._get_claude_worker_script(),
    )


# Export worker scripts as module-level constants
# These contain the full worker script content including guardian_nudge handling
OPENHANDS_WORKER_SCRIPT, CLAUDE_WORKER_SCRIPT = _create_worker_script_exports()
