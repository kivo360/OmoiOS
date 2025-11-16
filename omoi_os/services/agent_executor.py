"""Agent executor service wrapping OpenHands SDK for task execution."""

import os
from typing import Dict, Any

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

    def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a task using OpenHands agent.

        Args:
            task_description: Description of the task to execute

        Returns:
            Dictionary with execution results:
            - status: Execution status
            - event_count: Number of events generated
            - cost: LLM API cost
        """
        # Create conversation (one per task)
        conversation = Conversation(
            agent=self.agent,
            workspace=self.workspace_dir,
        )

        # Send task message
        conversation.send_message(task_description)

        # Run agent
        conversation.run()

        # Extract result
        result = {
            "status": conversation.state.execution_status,
            "event_count": len(conversation.state.events),
            "cost": conversation.conversation_stats.get_combined_metrics().accumulated_cost,
        }

        conversation.close()
        return result
