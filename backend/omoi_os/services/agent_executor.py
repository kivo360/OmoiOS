"""Agent executor service wrapping OpenHands SDK for task execution."""

import asyncio
import os
from typing import Dict, Any, Optional

# Ensure an event loop exists for libraries that expect one at import time
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from openhands.sdk import Conversation, LLM, AgentContext
from openhands.tools.preset.default import get_default_agent

from omoi_os.config import get_app_settings, load_llm_settings
from omoi_os.models.phase import PhaseModel
from omoi_os.services.database import DatabaseService


class AgentExecutor:
    """Wraps OpenHands Agent for task execution."""

    def __init__(
        self,
        phase_id: str,
        workspace_dir: str,
        db: Optional[DatabaseService] = None,
    ):
        """
        Initialize agent executor.

        Args:
            phase_id: Phase identifier (e.g., "PHASE_IMPLEMENTATION")
            workspace_dir: Directory path for workspace operations
            db: Optional database service for loading phase context
        """
        self.phase_id = phase_id
        self.workspace_dir = workspace_dir
        self.db = db

        # Load phase context for instructions
        phase_context = self._load_phase_context()
        phase_instructions = self._build_phase_instructions(phase_context)

        llm_settings = load_llm_settings()
        if not llm_settings.api_key:
            raise ValueError("LLM_API_KEY (or equivalent) must be configured")

        # Create OpenHands LLM and Agent
        self.llm = LLM(
            model=llm_settings.model,
            api_key=llm_settings.api_key,
        )

        # Create agent with phase instructions in system message suffix
        agent_context = None
        if phase_instructions:
            agent_context = AgentContext(system_message_suffix=phase_instructions)

        # Configure MCP connection to FastMCP server (if enabled)
        mcp_config = None
        integrations = get_app_settings().integrations
        mcp_server_url = integrations.mcp_server_url
        if integrations.enable_mcp_tools:
            # Use mcp-remote to connect to HTTP FastMCP server
            mcp_config = {
                "mcpServers": {
                    "omoi-os": {
                        "command": "npx",
                        "args": [
                            "-y",
                            "mcp-remote",
                            mcp_server_url
                        ]
                    }
                }
            }

        self.agent = get_default_agent(
            llm=self.llm,
            cli_mode=True,
            agent_context=agent_context,
            mcp_config=mcp_config,
        )
        self.phase_instructions = phase_instructions

    def prepare_conversation(self, task_id: str | None = None) -> Dict[str, str]:
        """
        Prepare conversation with persistence and return metadata.

        This allows storing conversation_id and persistence_dir in the database
        before execution starts, enabling Guardian to send interventions during execution.

        Args:
            task_id: Optional task ID to use as conversation_id for persistence

        Returns:
            Dictionary with:
            - conversation_id: OpenHands conversation ID
            - persistence_dir: Conversation persistence directory
        """
        import os

        # Set up persistence directory for conversation resumption
        persistence_dir = os.path.join(self.workspace_dir, "conversation")
        os.makedirs(persistence_dir, exist_ok=True)

        # Use task_id as conversation_id if provided, otherwise let OpenHands generate one
        conversation_id = str(task_id) if task_id else None

        # Create conversation with persistence enabled
        conversation = Conversation(
            agent=self.agent,
            workspace=self.workspace_dir,
            persistence_dir=persistence_dir,
            conversation_id=conversation_id,
        )

        return {
            "conversation_id": conversation.state.id,
            "persistence_dir": persistence_dir,
            "_conversation": conversation,  # Internal: store for execute_task
        }

    def execute_task(
        self,
        task_description: str,
        task_id: str | None = None,
        conversation_metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Execute a task using OpenHands agent.

        Args:
            task_description: Description of the task to execute
            task_id: Optional task ID to use as conversation_id for persistence
            conversation_metadata: Optional pre-prepared conversation metadata from prepare_conversation()

        Returns:
            Dictionary with execution results:
            - status: Execution status
            - event_count: Number of events generated
            - cost: LLM API cost
            - conversation_id: OpenHands conversation ID
            - persistence_dir: Conversation persistence directory
        """
        import os

        # Use pre-prepared conversation if provided, otherwise create new one
        if conversation_metadata and "_conversation" in conversation_metadata:
            conversation = conversation_metadata["_conversation"]
            conversation_id = conversation_metadata["conversation_id"]
            persistence_dir = conversation_metadata["persistence_dir"]
        else:
            # Set up persistence directory for conversation resumption
            persistence_dir = os.path.join(self.workspace_dir, "conversation")
            os.makedirs(persistence_dir, exist_ok=True)

            # Use task_id as conversation_id if provided, otherwise let OpenHands generate one
            conversation_id = str(task_id) if task_id else None

            # Create conversation with persistence enabled
            conversation = Conversation(
                agent=self.agent,
                workspace=self.workspace_dir,
                persistence_dir=persistence_dir,
                conversation_id=conversation_id,
            )

        try:
            # Build task message with phase instructions if not already in system prompt
            # (If agent_context was used, instructions are already in system prompt)
            task_message = task_description
            if self.phase_instructions and not hasattr(
                self.agent, "_phase_instructions_in_system"
            ):
                # Prepend phase instructions to task message if not in system prompt
                task_message = f"{self.phase_instructions}\n\n---\n\n{task_description}"

            # Send task message
            conversation.send_message(task_message)

            # Run agent
            conversation.run()

            # Extract result with conversation metadata
            result = {
                "status": conversation.state.execution_status,
                "event_count": len(conversation.state.events),
                "cost": conversation.conversation_stats.get_combined_metrics().accumulated_cost,
                "conversation_id": conversation.state.id,
                "persistence_dir": persistence_dir,
            }

            return result
        finally:
            # Always close conversation, even on error
            conversation.close()

    def _load_phase_context(self) -> Optional[Dict[str, Any]]:
        """Load phase context from database.

        Returns:
            Phase context dictionary or None if phase not found
        """
        if not self.db or not self.phase_id:
            return None

        try:
            with self.db.get_session() as session:
                phase = session.query(PhaseModel).filter_by(id=self.phase_id).first()
                if phase:
                    return phase.to_dict()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load phase context for {self.phase_id}: {e}")

        return None

    def _build_phase_instructions(
        self, phase_context: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Build phase instructions string from phase context.

        Args:
            phase_context: Phase context dictionary from database

        Returns:
            Formatted phase instructions string or None
        """
        if not phase_context:
            return None

        instructions_parts = []

        # Add phase name and description
        phase_name = phase_context.get("name", self.phase_id)
        phase_desc = phase_context.get("description")
        if phase_desc:
            instructions_parts.append(f"# Phase: {phase_name}\n{phase_desc}\n")
        else:
            instructions_parts.append(f"# Phase: {phase_name}\n")

        # Add phase prompt (main instructions)
        phase_prompt = phase_context.get("phase_prompt")
        if phase_prompt:
            instructions_parts.append(f"## Phase Instructions\n{phase_prompt}\n")

        # Add done definitions (completion criteria)
        done_definitions = phase_context.get("done_definitions")
        if done_definitions:
            instructions_parts.append("## Completion Criteria\n")
            instructions_parts.append(
                "You must complete ALL of the following before marking this task as done:\n"
            )
            for i, criterion in enumerate(done_definitions, 1):
                instructions_parts.append(f"{i}. {criterion}\n")
            instructions_parts.append(
                "\n⚠️ IMPORTANT: Do not claim the task is done until ALL criteria above are met.\n"
            )

        # Add expected outputs
        expected_outputs = phase_context.get("expected_outputs")
        if expected_outputs:
            instructions_parts.append("## Expected Outputs\n")
            for output in expected_outputs:
                output_type = output.get("type", "unknown")
                pattern = output.get("pattern") or output.get("name", "N/A")
                required = output.get("required", False)
                required_str = " (REQUIRED)" if required else " (optional)"
                instructions_parts.append(f"- {output_type}: {pattern}{required_str}\n")
            instructions_parts.append("\n")

        if not instructions_parts:
            return None

        return "\n".join(instructions_parts).strip()
