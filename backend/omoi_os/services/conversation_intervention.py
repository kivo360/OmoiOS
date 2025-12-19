"""Service for sending Guardian interventions to active OpenHands conversations."""

from typing import Optional

from openhands.sdk import Conversation, Agent
from openhands.tools.preset.default import get_default_agent
from openhands.sdk import LLM

from omoi_os.config import load_llm_settings
from omoi_os.logging import get_logger

logger = get_logger(__name__)


class ConversationInterventionService:
    """Service for sending Guardian interventions to active OpenHands conversations."""

    def __init__(self):
        """Initialize the conversation intervention service."""
        # Create LLM and agent for conversation resumption
        # Note: Agent must have same tools as original for reconciliation
        llm_settings = load_llm_settings()
        if not llm_settings.api_key:
            raise ValueError("LLM_API_KEY must be configured for interventions")
        self.llm = LLM(
            model=llm_settings.model,
            api_key=llm_settings.api_key,
        )
        self.agent = get_default_agent(llm=self.llm, cli_mode=True)

    def send_intervention(
        self,
        conversation_id: str,
        persistence_dir: str,
        workspace_dir: str,
        message: str,
        agent: Optional[Agent] = None,
    ) -> bool:
        """
        Send intervention message to active OpenHands conversation.

        This method resumes a conversation and sends a Guardian intervention message.
        The message can be sent even while the agent is running - OpenHands will
        process it asynchronously.

        Args:
            conversation_id: OpenHands conversation ID
            persistence_dir: Conversation persistence directory
            workspace_dir: Workspace directory for the conversation
            message: Intervention message to send
            agent: Optional agent instance (must match original agent tools for reconciliation).
                   If None, uses default agent.

        Returns:
            True if intervention was sent successfully, False otherwise
        """
        try:
            # Use provided agent or default (must match original tools for reconciliation)
            intervention_agent = agent if agent else self.agent

            # Resume conversation with same ID and persistence directory
            # Workspace can be different instance, but persistence_dir must match
            conversation = Conversation(
                conversation_id=conversation_id,
                persistence_dir=persistence_dir,
                agent=intervention_agent,
                workspace=workspace_dir,
            )

            # Format intervention message with Guardian prefix (Recommendation 4)
            # Truncate agent ID to 8 characters for readability
            intervention_message = f"[GUARDIAN INTERVENTION]: {message}"

            # Send intervention message (works even if agent is running)
            conversation.send_message(intervention_message)

            # If agent is idle, trigger processing
            # If agent is running, message will be queued and processed automatically
            from openhands.sdk.conversation.state import AgentExecutionStatus
            if conversation.state.agent_status == AgentExecutionStatus.IDLE:
                # Start processing in background thread to avoid blocking
                import threading
                thread = threading.Thread(target=conversation.run, daemon=True)
                thread.start()
                logger.info(
                    f"Sent intervention to conversation {conversation_id} and started processing"
                )
            else:
                logger.info(
                    f"Sent intervention to running conversation {conversation_id} "
                    f"(status: {conversation.state.agent_status})"
                )

            return True

        except Exception as e:
            logger.error(
                f"Failed to send intervention to conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return False

