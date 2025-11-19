"""Agent executor service wrapping OpenHands SDK for task execution."""

import asyncio
import os
from typing import Dict, Any

# Ensure an event loop exists for libraries that expect one at import time
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from openhands.sdk import Conversation, LLM
from openhands.tools.preset.default import get_default_agent


class AgentExecutor:
    """Wraps OpenHands Agent for task execution."""

    def __init__(self, phase_id: str, workspace_dir: str):
        """
        Initialize agent executor.

        Args:
            phase_id: Phase identifier (e.g., "PHASE_IMPLEMENTATION")
            workspace_dir: Directory path for workspace operations
        """
        self.phase_id = phase_id
        self.workspace_dir = workspace_dir

        # Create OpenHands LLM and Agent
        self.llm = LLM(
            model="openhands/claude-sonnet-4-5-20250929",
            api_key=os.getenv("LLM_API_KEY"),
        )
        self.agent = get_default_agent(llm=self.llm, cli_mode=True)

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
            # Send task message
            conversation.send_message(task_description)

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
