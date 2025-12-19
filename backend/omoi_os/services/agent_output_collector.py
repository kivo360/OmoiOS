"""Agent output collection service for OpenHands-based agents.

This service provides a unified interface to collect agent output from
various sources since we're not using tmux sessions:
- OpenHands Conversation events
- Agent workspace files
- EventBusService system events
- Agent registry status updates
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from omoi_os.models.agent import Agent
from omoi_os.models.agent_log import AgentLog
from omoi_os.models.sandbox_event import SandboxEvent
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class AgentOutputCollector:
    """Collects agent output from OpenHands conversations and other sources.

    This service replaces tmux-based output collection with a more robust
    system that works with OpenHands SDK conversations, workspace files,
    and event-driven communication.
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
    ):
        """Initialize output collector.

        Args:
            db: Database service for persistence
            event_bus: Optional event bus for real-time updates
        """
        self.db = db
        self.event_bus = event_bus

    def get_agent_output(
        self,
        agent_id: str,
        lines: int = 200,
        workspace_dir: Optional[str] = None,
    ) -> str:
        """
        Get the most recent output from an agent.

        Args:
            agent_id: Agent ID to get output from
            lines: Number of recent lines to return (deprecated, kept for compatibility)
            workspace_dir: Optional workspace directory for file-based output

        Returns:
            Combined output from various sources
        """
        output_sections = []

        # Method 1: Get recent logs from database
        logs_output = self._get_recent_logs(agent_id, limit=50)
        if logs_output:
            output_sections.append("=== Recent Logs ===")
            output_sections.append(logs_output)

        # Method 2: Scan workspace files if available
        if workspace_dir:
            workspace_output = self._get_workspace_output(agent_id, workspace_dir)
            if workspace_output:
                output_sections.append("=== Workspace Files ===")
                output_sections.append(workspace_output)

        # Method 3: Get conversation summary if available
        conversation_output = self._get_conversation_summary(agent_id)
        if conversation_output:
            output_sections.append("=== Conversation Status ===")
            output_sections.append(conversation_output)

        # Combine all output sources
        if output_sections:
            return "\n\n".join(output_sections)
        else:
            return "No agent output available"

    def _get_recent_logs(self, agent_id: str, limit: int = 50) -> str:
        """Get recent log entries for an agent."""
        try:
            with self.db.get_session() as session:
                logs = (
                    session.query(AgentLog)
                    .filter_by(agent_id=agent_id)
                    .filter(
                        AgentLog.log_type.in_([
                            "output", "message", "input", "intervention", "steering"
                        ])
                    )
                    .order_by(AgentLog.created_at.desc())
                    .limit(limit)
                    .all()
                )

                if not logs:
                    return "No recent logs found"

                # Format logs for display
                formatted_logs = []
                for log in logs:
                    timestamp = log.created_at.strftime("%H:%M:%S")
                    log_type = log.log_type.upper()
                    content = log.message[:200] + ("..." if len(log.message) > 200 else "")
                    formatted_logs.append(f"[{timestamp}] {log_type}: {content}")

                return "\n".join(formatted_logs)

        except Exception as e:
            logger.error(f"Failed to get recent logs for agent {agent_id}: {e}")
            return f"Error retrieving logs: {str(e)}"

    def _get_workspace_output(self, agent_id: str, workspace_dir: str) -> str:
        """Scan workspace directory for recent activity."""
        try:
            workspace_path = Path(workspace_dir)
            if not workspace_path.exists():
                return f"Workspace directory does not exist: {workspace_dir}"

            output_sections = []

            # Look for common output files
            output_files = [
                "output.log",
                "agent.log",
                "conversation.log",
                "stderr.log",
                "stdout.log"
            ]

            for filename in output_files:
                file_path = workspace_path / filename
                if file_path.exists():
                    try:
                        # Get last 20 lines
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            if lines:
                                recent_lines = lines[-20:]
                                file_output = f"{filename} (last 20 lines):\n"
                                file_output += "".join(recent_lines)
                                output_sections.append(file_output)
                    except (IOError, UnicodeDecodeError) as e:
                        logger.warning(f"Could not read {filename}: {e}")

            # Look for recently modified files (last 5 minutes)
            try:
                recent_files = []
                current_time = datetime.utcnow()
                for file_path in workspace_path.rglob("*"):
                    if file_path.is_file():
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if (current_time - mtime) < timedelta(minutes=5):
                            relative_path = file_path.relative_to(workspace_path)
                            file_size = file_path.stat().st_size
                            recent_files.append(
                                f"{relative_path} ({file_size} bytes, modified {mtime.strftime('%H:%M:%S')})"
                            )

                if recent_files:
                    output_sections.append("Recently Modified Files:")
                    output_sections.extend(recent_files)

            except Exception as e:
                logger.warning(f"Error scanning workspace: {e}")

            return "\n".join(output_sections) if output_sections else "No workspace output files found"

        except Exception as e:
            logger.error(f"Failed to get workspace output for agent {agent_id}: {e}")
            return f"Error scanning workspace: {str(e)}"

    def _get_conversation_summary(self, agent_id: str) -> str:
        """Get conversation summary from agent status."""
        try:
            with self.db.get_session() as session:
                agent = session.query(Agent).filter_by(id=agent_id).first()
                if not agent:
                    return "Agent not found"

                summary_parts = [
                    f"Agent Type: {agent.agent_type}",
                    f"Status: {agent.status}",
                    f"Phase: {agent.phase_id or 'None'}",
                ]

                # Get current task assigned to this agent
                from omoi_os.models.task import Task
                current_task = session.query(Task).filter_by(
                    assigned_agent_id=str(agent.id),
                    status="running"
                ).first()
                if current_task:
                    summary_parts.append(f"Current Task: {current_task.id}")

                if agent.last_heartbeat:
                    time_since = (utc_now() - agent.last_heartbeat).total_seconds()
                    summary_parts.append(f"Last Heartbeat: {time_since:.0f}s ago")

                # Note: Agent model doesn't have health_check_failures attribute
                # Health status is tracked via health_status field instead

                return " | ".join(summary_parts)

        except Exception as e:
            logger.error(f"Failed to get conversation summary for agent {agent_id}: {e}")
            return f"Error getting agent status: {str(e)}"

    def log_agent_event(
        self,
        agent_id: str,
        event_type: str,
        content: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an agent event for trajectory analysis.

        This method replaces tmux output logging with a structured
        event system that can be consumed by trajectory analysis.

        Args:
            agent_id: Agent ID
            event_type: Type of event (input, output, intervention, etc.)
            content: Event content
            details: Optional structured details
        """
        try:
            with self.db.get_session() as session:
                log_entry = AgentLog(
                    agent_id=agent_id,
                    log_type=event_type,
                    message=content,
                    details=details or {},
                )
                session.add(log_entry)
                session.commit()

                # Publish event for real-time monitoring
                if self.event_bus:
                    event = SystemEvent(
                        event_type="agent.event",
                        entity_type="agent",
                        entity_id=agent_id,
                        payload={
                            "event_type": event_type,
                            "content": content,
                            "details": details,
                        },
                    )
                    self.event_bus.publish(event)

        except Exception as e:
            logger.error(f"Failed to log agent event for {agent_id}: {e}")

    def get_active_agents(self) -> List[Agent]:
        """Get list of active agents.

        Replaces tmux session enumeration with database-based
        agent status tracking.
        
        Active agents are those with IDLE or RUNNING status per AgentStatus enum.
        """
        try:
            with self.db.get_session() as session:
                # Define active statuses using AgentStatus enum values
                # Active = can receive tasks (IDLE or RUNNING)
                from omoi_os.models.agent_status import AgentStatus
                
                active_statuses = [AgentStatus.IDLE.value, AgentStatus.RUNNING.value]

                agents = (
                    session.query(Agent)
                    .filter(Agent.status.in_(active_statuses))
                    .all()
                )

                # Expunge for use outside session
                for agent in agents:
                    session.expunge(agent)

                return agents

        except Exception as e:
            logger.error(f"Failed to get active agents: {e}")
            return []

    def check_agent_responsiveness(self, agent_id: str) -> bool:
        """Check if an agent is responsive.

        Uses multiple indicators since we don't have tmux session checks.
        """
        try:
            with self.db.get_session() as session:
                agent = session.query(Agent).filter_by(id=agent_id).first()
                if not agent:
                    return False

                # Check 1: Recent heartbeat
                if agent.last_heartbeat:
                    time_since = (utc_now() - agent.last_heartbeat).total_seconds()
                    if time_since > 120:  # 2 minutes
                        return False

                # Check 2: Recent log activity
                recent_log = (
                    session.query(AgentLog)
                    .filter_by(agent_id=agent_id)
                    .filter(AgentLog.created_at > utc_now() - timedelta(minutes=5))
                    .first()
                )

                return recent_log is not None

        except Exception as e:
            logger.error(f"Failed to check agent responsiveness for {agent_id}: {e}")
            return False

    def extract_error_context(self, agent_id: str) -> str:
        """Extract error context from agent output.

        Helps Guardian provide targeted assistance for stuck agents.
        """
        try:
            with self.db.get_session() as session:
                # Look for error logs in the last hour
                error_logs = (
                    session.query(AgentLog)
                    .filter_by(agent_id=agent_id)
                    .filter(
                        AgentLog.log_type.in_(["error", "exception", "failure"])
                    )
                    .filter(AgentLog.created_at > utc_now() - timedelta(hours=1))
                    .order_by(AgentLog.created_at.desc())
                    .limit(5)
                    .all()
                )

                if error_logs:
                    error_contexts = []
                    for log in error_logs:
                        timestamp = log.created_at.strftime("%H:%M:%S")
                        error_contexts.append(f"[{timestamp}] {log.message}")

                    return "\n".join(error_contexts)

                # Look for error indicators in recent output
                recent_logs = (
                    session.query(AgentLog)
                    .filter_by(agent_id=agent_id)
                    .filter(AgentLog.created_at > utc_now() - timedelta(minutes=10))
                    .order_by(AgentLog.created_at.desc())
                    .limit(20)
                    .all()
                )

                for log in recent_logs:
                    content_lower = log.message.lower()
                    error_indicators = [
                        "error", "exception", "traceback", "failed",
                        "cannot", "unable", "permission denied"
                    ]

                    if any(indicator in content_lower for indicator in error_indicators):
                        return f"Potential error detected: {log.message}"

        except Exception as e:
            logger.error(f"Failed to extract error context for {agent_id}: {e}")

        return "No specific errors detected"

    # -------------------------------------------------------------------------
    # Sandbox-Aware Methods (Phase 6)
    # -------------------------------------------------------------------------

    def get_sandbox_id_for_agent(self, agent_id: str) -> Optional[str]:
        """Get sandbox_id for an agent if running in sandbox.

        Args:
            agent_id: Agent ID to look up

        Returns:
            sandbox_id if agent is in sandbox, None otherwise
        """
        try:
            with self.db.get_session() as session:
                task = (
                    session.query(Task)
                    .filter(
                        Task.assigned_agent_id == agent_id,
                        Task.sandbox_id.isnot(None),
                        Task.status.in_(["running", "assigned"]),
                    )
                    .first()
                )
                return task.sandbox_id if task else None
        except Exception as e:
            logger.error(f"Failed to get sandbox_id for agent {agent_id}: {e}")
            return None

    def is_sandbox_agent(self, agent_id: str) -> bool:
        """Check if agent is running in a sandbox."""
        return self.get_sandbox_id_for_agent(agent_id) is not None

    def get_sandbox_output(
        self, sandbox_id: str, lines: int = 50
    ) -> str:
        """Get recent output from sandbox events.

        Args:
            sandbox_id: Sandbox ID to query
            lines: Number of recent events to include

        Returns:
            Formatted output string from sandbox events
        """
        try:
            with self.db.get_session() as session:
                events = (
                    session.query(SandboxEvent)
                    .filter(SandboxEvent.sandbox_id == sandbox_id)
                    .filter(
                        SandboxEvent.event_type.in_([
                            "agent.assistant_message",
                            "agent.tool_use",
                            "agent.tool_result",
                            "agent.file_edited",
                            "agent.error",
                            "agent.completed",
                            "agent.message_injected",
                        ])
                    )
                    .order_by(SandboxEvent.created_at.desc())
                    .limit(lines)
                    .all()
                )

                if not events:
                    return "No sandbox output available"

                # Format events for display (reverse to chronological order)
                formatted_events = []
                for event in reversed(events):
                    timestamp = event.created_at.strftime("%H:%M:%S")
                    event_type = event.event_type.replace("agent.", "").upper()
                    event_data = event.event_data or {}

                    # Extract content based on event type
                    content = self._format_sandbox_event(event.event_type, event_data)
                    formatted_events.append(f"[{timestamp}] {event_type}: {content}")

                return "\n".join(formatted_events)

        except Exception as e:
            logger.error(f"Failed to get sandbox output for {sandbox_id}: {e}")
            return f"Error retrieving sandbox output: {str(e)}"

    def _format_sandbox_event(self, event_type: str, event_data: dict) -> str:
        """Format a sandbox event for display.

        Args:
            event_type: Type of event
            event_data: Event payload

        Returns:
            Formatted content string
        """
        content = event_data.get("content", "")
        tool_name = event_data.get("tool_name", "")
        file_path = event_data.get("file_path", "")
        error = event_data.get("error", "")
        message = event_data.get("message", "")

        if event_type == "agent.assistant_message":
            return content[:200] + ("..." if len(content) > 200 else "")
        elif event_type == "agent.tool_use":
            return f"Tool: {tool_name}"
        elif event_type == "agent.tool_result":
            return content[:150] + ("..." if len(content) > 150 else "")
        elif event_type == "agent.file_edited":
            return f"File: {file_path}"
        elif event_type == "agent.error":
            return error[:200] if error else "Error occurred"
        elif event_type == "agent.completed":
            return message or "Task completed"
        elif event_type == "agent.message_injected":
            msg_type = event_data.get("message_type", "user")
            return f"[{msg_type}] {content[:100]}"
        else:
            return message or content or event_type

    def get_agent_output_auto(
        self,
        agent_id: str,
        lines: int = 200,
        workspace_dir: Optional[str] = None,
    ) -> str:
        """Automatically detect agent type and get appropriate output.

        Routes to sandbox or legacy output collection based on agent type.

        Args:
            agent_id: Agent ID
            lines: Number of lines/events to return
            workspace_dir: Optional workspace directory for legacy agents

        Returns:
            Formatted output string
        """
        # Check if sandbox agent
        sandbox_id = self.get_sandbox_id_for_agent(agent_id)

        if sandbox_id:
            logger.debug(f"Agent {agent_id} is sandbox agent, using sandbox events")
            return self._get_sandbox_agent_output(agent_id, sandbox_id, lines)
        else:
            logger.debug(f"Agent {agent_id} is legacy agent, using agent logs")
            return self.get_agent_output(agent_id, lines, workspace_dir)

    def _get_sandbox_agent_output(
        self, agent_id: str, sandbox_id: str, lines: int = 50
    ) -> str:
        """Get output for a sandbox agent.

        Args:
            agent_id: Agent ID
            sandbox_id: Sandbox ID
            lines: Number of events to include

        Returns:
            Formatted output combining sandbox events and agent status
        """
        output_sections = []

        # Get sandbox events
        sandbox_output = self.get_sandbox_output(sandbox_id, lines)
        if sandbox_output:
            output_sections.append("=== Sandbox Events ===")
            output_sections.append(sandbox_output)

        # Get agent/task status
        status_output = self._get_sandbox_status(agent_id, sandbox_id)
        if status_output:
            output_sections.append("=== Sandbox Status ===")
            output_sections.append(status_output)

        if output_sections:
            return "\n\n".join(output_sections)
        else:
            return "No sandbox agent output available"

    def _get_sandbox_status(self, agent_id: str, sandbox_id: str) -> str:
        """Get status summary for a sandbox agent.

        Args:
            agent_id: Agent ID
            sandbox_id: Sandbox ID

        Returns:
            Status summary string
        """
        try:
            with self.db.get_session() as session:
                agent = session.query(Agent).filter_by(id=agent_id).first()
                task = session.query(Task).filter_by(sandbox_id=sandbox_id).first()

                summary_parts = []

                if agent:
                    summary_parts.extend([
                        f"Agent Type: {agent.agent_type}",
                        f"Status: {agent.status}",
                    ])
                    if agent.last_heartbeat:
                        time_since = (utc_now() - agent.last_heartbeat).total_seconds()
                        summary_parts.append(f"Last Heartbeat: {time_since:.0f}s ago")

                if task:
                    summary_parts.extend([
                        f"Task: {task.id}",
                        f"Task Status: {task.status}",
                        f"Phase: {task.phase_id or 'None'}",
                    ])

                summary_parts.append(f"Sandbox: {sandbox_id}")

                return " | ".join(summary_parts)

        except Exception as e:
            logger.error(f"Failed to get sandbox status: {e}")
            return f"Error getting status: {str(e)}"

    def extract_sandbox_error_context(self, sandbox_id: str) -> str:
        """Extract error context from sandbox events.

        Args:
            sandbox_id: Sandbox ID to check

        Returns:
            Error context string
        """
        try:
            with self.db.get_session() as session:
                # Look for error events
                error_events = (
                    session.query(SandboxEvent)
                    .filter(
                        SandboxEvent.sandbox_id == sandbox_id,
                        SandboxEvent.event_type == "agent.error",
                    )
                    .order_by(SandboxEvent.created_at.desc())
                    .limit(5)
                    .all()
                )

                if error_events:
                    error_contexts = []
                    for event in error_events:
                        timestamp = event.created_at.strftime("%H:%M:%S")
                        event_data = event.event_data or {}
                        error_msg = event_data.get("error", "Unknown error")
                        error_contexts.append(f"[{timestamp}] {error_msg}")
                    return "\n".join(error_contexts)

                # Check for error indicators in recent events
                recent_events = (
                    session.query(SandboxEvent)
                    .filter(
                        SandboxEvent.sandbox_id == sandbox_id,
                        SandboxEvent.created_at > utc_now() - timedelta(minutes=10),
                    )
                    .order_by(SandboxEvent.created_at.desc())
                    .limit(20)
                    .all()
                )

                for event in recent_events:
                    event_data = event.event_data or {}
                    content = str(event_data.get("content", "")).lower()
                    error = str(event_data.get("error", "")).lower()

                    error_indicators = [
                        "error", "exception", "traceback", "failed",
                        "cannot", "unable", "permission denied"
                    ]

                    combined = content + error
                    if any(indicator in combined for indicator in error_indicators):
                        return f"Potential error in {event.event_type}: {event_data}"

        except Exception as e:
            logger.error(f"Failed to extract error context for sandbox {sandbox_id}: {e}")

        return "No specific errors detected"

    def extract_error_context_auto(self, agent_id: str) -> str:
        """Automatically extract error context from appropriate source.

        Args:
            agent_id: Agent ID

        Returns:
            Error context string
        """
        sandbox_id = self.get_sandbox_id_for_agent(agent_id)

        if sandbox_id:
            return self.extract_sandbox_error_context(sandbox_id)
        else:
            return self.extract_error_context(agent_id)