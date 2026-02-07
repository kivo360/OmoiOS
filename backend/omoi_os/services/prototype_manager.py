"""Prototype Manager service for fast prompt-to-preview iteration.

Phase 3: Prototyping Mode — enables rapid prototyping without the full
spec pipeline. Sessions are ephemeral (in-memory, not persisted to DB).

Usage:
    manager = PrototypeManager(db=db_service, event_bus=event_bus_service)

    session = await manager.start_session(user_id="u-1", framework="react-vite")
    result = await manager.apply_prompt(session.id, prompt="Add a counter")
    export = await manager.export_to_repo(session.id, repo_url="...", branch="prototype")
    await manager.end_session(session.id)
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from omoi_os.logging import get_logger
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.preview_manager import PreviewManager
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


class PrototypeStatus(str, Enum):
    """Lifecycle states for a prototype session."""

    CREATING = "creating"
    READY = "ready"
    PROMPTING = "prompting"
    EXPORTING = "exporting"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class PrototypeSession:
    """In-memory prototype session state."""

    id: str
    user_id: str
    framework: str  # "react-vite" | "next" | "vue-vite"
    sandbox_id: Optional[str] = None
    preview_id: Optional[str] = None
    status: PrototypeStatus = PrototypeStatus.CREATING
    preview_url: Optional[str] = None
    prompt_history: List[Dict] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: utc_now().isoformat())


class PrototypeManager:
    """Manages ephemeral prototype sessions with in-memory storage.

    Sessions are lost on server restart (acceptable for POC).
    """

    # Snapshot names for each framework template
    FRAMEWORK_SNAPSHOTS: Dict[str, str] = {
        "react-vite": "omoios-react-vite-snapshot",
        "next": "omoios-next-snapshot",
        "vue-vite": "omoios-vue-vite-snapshot",
    }

    # Dev server ports by framework
    FRAMEWORK_PORTS: Dict[str, int] = {
        "react-vite": 5173,
        "next": 3000,
        "vue-vite": 5173,
    }

    # Dev server start commands
    FRAMEWORK_START_COMMANDS: Dict[str, str] = {
        "react-vite": "cd /app && npm run dev -- --host 0.0.0.0",
        "next": "cd /app && npm run dev -- --hostname 0.0.0.0",
        "vue-vite": "cd /app && npm run dev -- --host 0.0.0.0",
    }

    def __init__(self, db: DatabaseService, event_bus: EventBusService):
        self.db = db
        self.event_bus = event_bus
        self.preview_manager = PreviewManager(db=db, event_bus=event_bus)
        self._sessions: Dict[str, PrototypeSession] = {}

    def get_session(self, session_id: str) -> Optional[PrototypeSession]:
        """Get a prototype session by ID."""
        return self._sessions.get(session_id)

    def get_user_sessions(self, user_id: str) -> List[PrototypeSession]:
        """Get all sessions for a user."""
        return [s for s in self._sessions.values() if s.user_id == user_id]

    async def start_session(self, user_id: str, framework: str) -> PrototypeSession:
        """Start a new prototype session.

        Creates a Daytona sandbox from a framework snapshot,
        starts the dev server, and sets up a preview session.

        Args:
            user_id: ID of the user starting the session
            framework: Framework template ("react-vite", "next", "vue-vite")

        Returns:
            Created PrototypeSession

        Raises:
            ValueError: If framework is not supported
        """
        if framework not in self.FRAMEWORK_SNAPSHOTS:
            raise ValueError(
                f"Unsupported framework: {framework}. "
                f"Supported: {list(self.FRAMEWORK_SNAPSHOTS.keys())}"
            )

        session_id = str(uuid.uuid4())
        session = PrototypeSession(
            id=session_id,
            user_id=user_id,
            framework=framework,
        )
        self._sessions[session_id] = session

        try:
            # Import Daytona SDK lazily
            from daytona import Daytona, DaytonaConfig

            from omoi_os.config import get_app_settings

            settings = get_app_settings()
            daytona_config = DaytonaConfig(
                api_key=settings.daytona.api_key,
                server_url=settings.daytona.api_url,
                target=settings.daytona.target,
            )
            daytona = Daytona(config=daytona_config)

            # Create sandbox from snapshot
            snapshot_name = self.FRAMEWORK_SNAPSHOTS[framework]
            sandbox = daytona.create(snapshot=snapshot_name)
            session.sandbox_id = sandbox.id

            # Start dev server in background
            start_cmd = self.FRAMEWORK_START_COMMANDS[framework]
            sandbox.process.exec(f"nohup {start_cmd} > /tmp/dev-server.log 2>&1 &")

            # Create preview session
            port = self.FRAMEWORK_PORTS[framework]
            preview = await self.preview_manager.create_preview(
                sandbox_id=sandbox.id,
                user_id=user_id,
                port=port,
                framework=framework,
            )
            session.preview_id = preview.id

            # Get preview URL
            preview_link = sandbox.get_preview_link(port)
            session.preview_url = preview_link.url

            # Mark preview as ready
            await self.preview_manager.mark_ready(
                preview_id=preview.id,
                preview_url=preview_link.url,
                preview_token=preview_link.token,
            )

            session.status = PrototypeStatus.READY

            # Publish event
            self.event_bus.publish(
                SystemEvent(
                    event_type="PROTOTYPE_SESSION_STARTED",
                    entity_type="prototype",
                    entity_id=session_id,
                    payload={
                        "user_id": user_id,
                        "framework": framework,
                        "sandbox_id": sandbox.id,
                        "preview_url": preview_link.url,
                    },
                )
            )

            logger.info(
                "Prototype session started",
                extra={
                    "session_id": session_id,
                    "framework": framework,
                    "sandbox_id": sandbox.id,
                    "preview_url": preview_link.url,
                },
            )

        except Exception as e:
            session.status = PrototypeStatus.FAILED
            session.error_message = str(e)
            logger.error(
                "Failed to start prototype session",
                extra={"session_id": session_id, "error": str(e)},
                exc_info=True,
            )

        return session

    async def apply_prompt(self, session_id: str, prompt: str) -> Dict:
        """Apply a prompt to generate/modify code in the sandbox.

        POC limitation: Uses llm_service.complete() which generates code
        suggestions but can't edit sandbox files. Production version needs
        Claude Code running inside the sandbox.

        Args:
            session_id: Session ID
            prompt: User prompt describing desired changes

        Returns:
            Dict with prompt, response_summary, and timestamp

        Raises:
            ValueError: If session not found or in wrong state
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if session.status not in (PrototypeStatus.READY, PrototypeStatus.PROMPTING):
            raise ValueError(
                f"Session {session_id} not in a promptable state: {session.status}"
            )

        session.status = PrototypeStatus.PROMPTING
        timestamp = utc_now().isoformat()

        try:
            from omoi_os.services.llm_service import get_llm_service

            llm = get_llm_service()
            system_prompt = (
                f"You are a frontend developer working on a {session.framework} project. "
                f"The user wants you to modify the code. Describe what changes you would make "
                f"and provide the code. Framework: {session.framework}."
            )
            response = await llm.complete(
                prompt=prompt,
                system_prompt=system_prompt,
            )

            result = {
                "prompt": prompt,
                "response_summary": response[:500] if response else "",
                "timestamp": timestamp,
            }
            session.prompt_history.append(result)
            session.status = PrototypeStatus.READY

            # Publish event
            self.event_bus.publish(
                SystemEvent(
                    event_type="PROTOTYPE_PROMPT_APPLIED",
                    entity_type="prototype",
                    entity_id=session_id,
                    payload={
                        "prompt": prompt,
                        "response_summary": result["response_summary"][:200],
                        "timestamp": timestamp,
                    },
                )
            )

            logger.info(
                "Prototype prompt applied",
                extra={
                    "session_id": session_id,
                    "prompt_length": len(prompt),
                },
            )
            return result

        except Exception as e:
            session.status = PrototypeStatus.READY  # Recover to ready state
            logger.error(
                "Failed to apply prompt",
                extra={"session_id": session_id, "error": str(e)},
                exc_info=True,
            )
            raise

    async def export_to_repo(
        self,
        session_id: str,
        repo_url: str,
        branch: str = "prototype",
        commit_message: str = "Export prototype",
    ) -> Dict:
        """Export the sandbox code to a git repository.

        Args:
            session_id: Session ID
            repo_url: Git repository URL to push to
            branch: Branch name (default: "prototype")
            commit_message: Commit message

        Returns:
            Dict with repo_url, branch, commit_message, and timestamp

        Raises:
            ValueError: If session not found or no sandbox
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if not session.sandbox_id:
            raise ValueError(f"Session {session_id} has no sandbox")

        session.status = PrototypeStatus.EXPORTING
        timestamp = utc_now().isoformat()

        try:
            from daytona import Daytona, DaytonaConfig

            from omoi_os.config import get_app_settings

            settings = get_app_settings()
            daytona_config = DaytonaConfig(
                api_key=settings.daytona.api_key,
                server_url=settings.daytona.api_url,
                target=settings.daytona.target,
            )
            daytona = Daytona(config=daytona_config)
            sandbox = daytona.get_current_sandbox(session.sandbox_id)

            # Initialize git and push
            git_commands = [
                "cd /app",
                "git init",
                "git add -A",
                f'git commit -m "{commit_message}"',
                f"git remote add origin {repo_url}",
                f"git checkout -b {branch}",
                f"git push -u origin {branch} --force",
            ]
            sandbox.process.exec(" && ".join(git_commands))

            result = {
                "repo_url": repo_url,
                "branch": branch,
                "commit_message": commit_message,
                "timestamp": timestamp,
            }

            session.status = PrototypeStatus.READY

            # Publish event
            self.event_bus.publish(
                SystemEvent(
                    event_type="PROTOTYPE_EXPORTED",
                    entity_type="prototype",
                    entity_id=session_id,
                    payload=result,
                )
            )

            logger.info(
                "Prototype exported",
                extra={
                    "session_id": session_id,
                    "repo_url": repo_url,
                    "branch": branch,
                },
            )
            return result

        except Exception as e:
            session.status = PrototypeStatus.READY
            logger.error(
                "Failed to export prototype",
                extra={"session_id": session_id, "error": str(e)},
                exc_info=True,
            )
            raise

    async def end_session(self, session_id: str) -> None:
        """End a prototype session and clean up resources.

        Args:
            session_id: Session ID

        Raises:
            ValueError: If session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Stop preview if active
        if session.preview_id:
            try:
                await self.preview_manager.mark_stopped(session.preview_id)
            except Exception as e:
                logger.warning(
                    "Failed to stop preview during session cleanup",
                    extra={"session_id": session_id, "error": str(e)},
                )

        # Delete Daytona sandbox
        if session.sandbox_id:
            try:
                from daytona import Daytona, DaytonaConfig

                from omoi_os.config import get_app_settings

                settings = get_app_settings()
                daytona_config = DaytonaConfig(
                    api_key=settings.daytona.api_key,
                    server_url=settings.daytona.api_url,
                    target=settings.daytona.target,
                )
                daytona = Daytona(config=daytona_config)
                sandbox = daytona.get_current_sandbox(session.sandbox_id)
                sandbox.delete()
            except Exception as e:
                logger.warning(
                    "Failed to delete sandbox during session cleanup",
                    extra={"session_id": session_id, "error": str(e)},
                )

        session.status = PrototypeStatus.STOPPED

        # Remove from memory
        self._sessions.pop(session_id, None)

        logger.info(
            "Prototype session ended",
            extra={"session_id": session_id},
        )
