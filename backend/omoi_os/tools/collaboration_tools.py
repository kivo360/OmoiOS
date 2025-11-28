"""OmoiOS Collaboration Tools for OpenHands agents.

These tools allow agents to communicate with each other,
request handoffs, and share context.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional, List, TYPE_CHECKING

from pydantic import Field
from rich.text import Text

from openhands.sdk import Action, Observation, TextContent
from openhands.sdk.tool import ToolDefinition, ToolAnnotations, ToolExecutor, register_tool

from omoi_os.tools.protocols import CollaborationServiceProtocol

if TYPE_CHECKING:
    from openhands.sdk.conversation import LocalConversation
    from openhands.sdk.conversation.state import ConversationState


# ---------- Module-level service instance ----------

_collab_service: Optional[CollaborationServiceProtocol] = None


def initialize_collaboration_tool_services(
    collab_service: CollaborationServiceProtocol,
) -> None:
    """Initialize the module-level service instance for collaboration tools."""
    global _collab_service
    _collab_service = collab_service


# ---------- Actions ----------


class BroadcastMessageAction(Action):
    """Broadcast a message to all agents."""

    message: str = Field(min_length=1, description="Message to broadcast")
    message_type: str = Field(
        default="info",
        pattern="^(info|warning|alert|discovery)$",
        description="Type of message",
    )
    context: dict = Field(
        default_factory=dict,
        description="Additional context data",
    )


class SendMessageAction(Action):
    """Send a message to a specific agent."""

    target_agent_id: str = Field(description="ID of agent to send message to")
    message: str = Field(min_length=1, description="Message content")
    message_type: str = Field(
        default="info",
        pattern="^(info|request|response|handoff)$",
        description="Type of message",
    )
    context: dict = Field(
        default_factory=dict,
        description="Additional context data",
    )


class GetMessagesAction(Action):
    """Get messages for an agent."""

    agent_id: str = Field(description="Agent ID to get messages for")
    unread_only: bool = Field(
        default=True,
        description="Only return unread messages",
    )
    limit: int = Field(default=20, ge=1, le=100, description="Maximum messages to return")


class RequestHandoffAction(Action):
    """Request a handoff to another agent or phase."""

    task_id: str = Field(description="Current task ID")
    target_phase_id: Optional[str] = Field(
        default=None,
        description="Target phase for handoff (e.g., PHASE_IMPLEMENTATION)",
    )
    target_agent_type: Optional[str] = Field(
        default=None,
        description="Type of agent to hand off to (e.g., 'specialist', 'reviewer')",
    )
    reason: str = Field(
        min_length=10,
        description="Reason for requesting handoff",
    )
    context_summary: str = Field(
        min_length=10,
        description="Summary of context to pass to receiving agent",
    )


class MarkMessageReadAction(Action):
    """Mark a message as read."""

    message_id: str = Field(description="Message ID to mark as read")


# ---------- Observations ----------


class CollaborationObservation(Observation):
    """Observation returned by collaboration operations."""

    success: bool = Field(default=True)
    message: str = Field(default="")
    payload: dict = Field(default_factory=dict)

    @classmethod
    def ok(cls, message: str, payload: dict = None) -> "CollaborationObservation":
        return cls(
            content=[TextContent(type="text", text=message)],
            success=True,
            message=message,
            payload=payload or {},
        )

    @classmethod
    def error(cls, message: str, payload: dict = None) -> "CollaborationObservation":
        return cls(
            content=[TextContent(type="text", text=f"Error: {message}")],
            success=False,
            message=message,
            is_error=True,
            payload=payload or {},
        )

    @property
    def visualize(self) -> Text:
        text = Text()
        if self.success:
            text.append("✅ ", style="green")
            text.append(self.message, style="white")
        else:
            text.append("❌ ", style="red")
            text.append(self.message, style="red")
        return text


# ---------- Executors (ToolExecutor subclasses) ----------


class BroadcastMessageExecutor(ToolExecutor[BroadcastMessageAction, CollaborationObservation]):
    """Executor for broadcasting messages."""

    def __call__(
        self,
        action: BroadcastMessageAction,
        conversation: "LocalConversation | None" = None,
    ) -> CollaborationObservation:
        if _collab_service is None:
            return CollaborationObservation.error("Collaboration service not initialized.")

        try:
            _collab_service.broadcast_message(
                message=action.message,
                message_type=action.message_type,
                context=action.context,
            )
            return CollaborationObservation.ok(
                message=f"Broadcast {action.message_type} message sent",
                payload={"message_type": action.message_type, "message": action.message},
            )
        except Exception as e:
            return CollaborationObservation.error(f"Failed to broadcast: {str(e)}")


class SendMessageExecutor(ToolExecutor[SendMessageAction, CollaborationObservation]):
    """Executor for sending messages to specific agents."""

    def __call__(
        self,
        action: SendMessageAction,
        conversation: "LocalConversation | None" = None,
    ) -> CollaborationObservation:
        if _collab_service is None:
            return CollaborationObservation.error("Collaboration service not initialized.")

        try:
            _collab_service.send_message(
                target_agent_id=action.target_agent_id,
                message=action.message,
                message_type=action.message_type,
                context=action.context,
            )
            return CollaborationObservation.ok(
                message=f"Message sent to agent {action.target_agent_id}",
                payload={
                    "target_agent_id": action.target_agent_id,
                    "message_type": action.message_type,
                },
            )
        except Exception as e:
            return CollaborationObservation.error(f"Failed to send message: {str(e)}")


class GetMessagesExecutor(ToolExecutor[GetMessagesAction, CollaborationObservation]):
    """Executor for getting messages."""

    def __call__(
        self,
        action: GetMessagesAction,
        conversation: "LocalConversation | None" = None,
    ) -> CollaborationObservation:
        if _collab_service is None:
            return CollaborationObservation.error("Collaboration service not initialized.")

        try:
            messages = _collab_service.get_messages(
                agent_id=action.agent_id,
                unread_only=action.unread_only,
                limit=action.limit,
            )
            return CollaborationObservation.ok(
                message=f"Retrieved {len(messages)} messages",
                payload={"messages": messages, "count": len(messages)},
            )
        except Exception as e:
            return CollaborationObservation.error(f"Failed to get messages: {str(e)}")


class RequestHandoffExecutor(ToolExecutor[RequestHandoffAction, CollaborationObservation]):
    """Executor for requesting handoffs."""

    def __call__(
        self,
        action: RequestHandoffAction,
        conversation: "LocalConversation | None" = None,
    ) -> CollaborationObservation:
        if _collab_service is None:
            return CollaborationObservation.error("Collaboration service not initialized.")

        try:
            handoff_id = _collab_service.request_handoff(
                task_id=action.task_id,
                target_phase_id=action.target_phase_id,
                target_agent_type=action.target_agent_type,
                reason=action.reason,
                context_summary=action.context_summary,
            )
            return CollaborationObservation.ok(
                message=f"Handoff requested: {handoff_id}",
                payload={
                    "handoff_id": handoff_id,
                    "task_id": action.task_id,
                    "target_phase_id": action.target_phase_id,
                },
            )
        except Exception as e:
            return CollaborationObservation.error(f"Failed to request handoff: {str(e)}")


class MarkMessageReadExecutor(ToolExecutor[MarkMessageReadAction, CollaborationObservation]):
    """Executor for marking messages as read."""

    def __call__(
        self,
        action: MarkMessageReadAction,
        conversation: "LocalConversation | None" = None,
    ) -> CollaborationObservation:
        if _collab_service is None:
            return CollaborationObservation.error("Collaboration service not initialized.")

        try:
            _collab_service.mark_message_read(action.message_id)
            return CollaborationObservation.ok(
                message=f"Message {action.message_id} marked as read",
                payload={"message_id": action.message_id},
            )
        except Exception as e:
            return CollaborationObservation.error(f"Failed to mark message read: {str(e)}")


# ---------- Tool Definitions ----------


class BroadcastMessageTool(ToolDefinition[BroadcastMessageAction, CollaborationObservation]):
    """Tool for broadcasting messages to all agents."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["BroadcastMessageTool"]:
        return [
            cls(
                description=(
                    "Broadcast a message to all agents. Use for announcements, "
                    "discoveries that affect multiple agents, or system-wide alerts."
                ),
                action_type=BroadcastMessageAction,
                observation_type=CollaborationObservation,
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=True,
                ),
                executor=BroadcastMessageExecutor(),
            )
        ]


class SendMessageTool(ToolDefinition[SendMessageAction, CollaborationObservation]):
    """Tool for sending messages to specific agents."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["SendMessageTool"]:
        return [
            cls(
                description=(
                    "Send a message to a specific agent. Use for direct communication, "
                    "questions, or sharing specific context with another agent."
                ),
                action_type=SendMessageAction,
                observation_type=CollaborationObservation,
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=True,
                ),
                executor=SendMessageExecutor(),
            )
        ]


class GetMessagesTool(ToolDefinition[GetMessagesAction, CollaborationObservation]):
    """Tool for getting messages for an agent."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["GetMessagesTool"]:
        return [
            cls(
                description="Get messages for an agent. Use to check for communications from other agents.",
                action_type=GetMessagesAction,
                observation_type=CollaborationObservation,
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=GetMessagesExecutor(),
            )
        ]


class RequestHandoffTool(ToolDefinition[RequestHandoffAction, CollaborationObservation]):
    """Tool for requesting handoffs to other agents."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["RequestHandoffTool"]:
        return [
            cls(
                description=(
                    "Request a handoff to another agent or phase. Use when work needs "
                    "to transition to a different specialist or development phase."
                ),
                action_type=RequestHandoffAction,
                observation_type=CollaborationObservation,
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=True,
                ),
                executor=RequestHandoffExecutor(),
            )
        ]


class MarkMessageReadTool(ToolDefinition[MarkMessageReadAction, CollaborationObservation]):
    """Tool for marking messages as read."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["MarkMessageReadTool"]:
        return [
            cls(
                description="Mark a message as read after processing it.",
                action_type=MarkMessageReadAction,
                observation_type=CollaborationObservation,
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=MarkMessageReadExecutor(),
            )
        ]


# ---------- Tool Registration ----------


def register_omoi_collaboration_tools() -> None:
    """Register OmoiOS collaboration tools with OpenHands."""
    register_tool(BroadcastMessageTool.name, BroadcastMessageTool)
    register_tool(SendMessageTool.name, SendMessageTool)
    register_tool(GetMessagesTool.name, GetMessagesTool)
    register_tool(RequestHandoffTool.name, RequestHandoffTool)
    register_tool(MarkMessageReadTool.name, MarkMessageReadTool)
