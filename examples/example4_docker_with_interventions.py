"""Example: Run agent in Docker with intervention support.

This example demonstrates how to run an agent in a Docker workspace and
send intervention messages while the agent is actively working.

Key features:
- Runs conversation in background thread to allow interventions
- Provides intervention function to send messages mid-execution
- Monitors conversation state and allows real-time steering
"""

import asyncio
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional, List, Dict, Any, AsyncIterator

from openhands.sdk import Conversation, get_logger
import uuid

# Import OOP workspace managers
from examples.workspace_managers import (
    LocalWorkspaceManager,
    DockerWorkspaceManager,
    ConversationRunner,
    build_llm,
    build_agent,
    detect_platform,
    find_available_port,
)

# DockerWorkspace import is lazy - only imported when use_docker=True
# This avoids requiring OpenHands SDK root when using local workspaces

logger = get_logger(__name__)


class InterventionType(Enum):
    """Types of structured interventions."""

    PRIORITIZE = "prioritize"
    STOP = "stop"
    REFOCUS = "refocus"
    ADD_CONSTRAINT = "add_constraint"
    INJECT_TOOL_CALL = "inject_tool_call"
    CUSTOM = "custom"


@dataclass
class InterventionRecord:
    """Record of an intervention sent to the conversation."""

    intervention_id: str
    timestamp: datetime
    type: InterventionType
    message: str
    structured_data: Optional[Dict[str, Any]] = None
    acknowledged: bool = False
    acknowledgment_timestamp: Optional[datetime] = None
    acknowledgment_message: Optional[str] = None
    effectiveness_score: Optional[float] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterventionResult:
    """Result of sending an intervention."""

    success: bool
    intervention_id: str
    message: str
    timestamp: datetime
    error: Optional[str] = None


@dataclass
class ConversationEvent:
    """Event from the conversation stream."""

    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    intervention_id: Optional[str] = None  # Link to intervention if relevant


# build_llm, build_agent, detect_platform, find_available_port are now imported from workspace_managers


class InterventionHandler:
    """Enhanced handler for sending interventions with event streaming and history."""

    def __init__(self, conversation: Conversation):
        """Initialize intervention handler with a conversation."""
        self.conversation = conversation
        self.conversation_id = conversation.state.id
        self.persistence_dir = conversation.state.persistence_dir
        self.intervention_history: List[InterventionRecord] = []
        self.event_queue: List[ConversationEvent] = []
        self.event_listeners: List[Callable[[ConversationEvent], None]] = []
        self._event_monitoring = False
        self._event_thread: Optional[threading.Thread] = None
        logger.info(
            f"Intervention handler ready for conversation {self.conversation_id}"
        )

    def send_intervention(
        self,
        message: str,
        prefix: str = "[INTERVENTION]",
        intervention_type: InterventionType = InterventionType.CUSTOM,
        structured_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> InterventionResult:
        """
        Send intervention message to running conversation with retry logic.

        This works even while the conversation is actively running - OpenHands
        will queue the message and process it asynchronously.

        Args:
            message: Intervention message to send
            prefix: Optional prefix for the message (default: "[INTERVENTION]")
            intervention_type: Type of intervention (default: CUSTOM)
            structured_data: Optional structured data for the intervention
            max_retries: Maximum number of retry attempts if sending fails (default: 3)
            retry_delay: Delay between retries in seconds (default: 2.0)

        Returns:
            InterventionResult with success status and intervention ID
        """
        intervention_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        last_error = None

        # Retry logic for sending interventions
        for attempt in range(max_retries):
            try:
                # Format message based on intervention type
                if intervention_type == InterventionType.PRIORITIZE:
                    formatted_message = f"{prefix} PRIORITY: {message}"
                elif intervention_type == InterventionType.STOP:
                    formatted_message = f"{prefix} STOP: {message}"
                elif intervention_type == InterventionType.REFOCUS:
                    formatted_message = f"{prefix} REFOCUS: {message}"
                else:
                    formatted_message = f"{prefix} {message}"

                logger.info(
                    f"Sending intervention [{intervention_type.value}]: {formatted_message}"
                )
                self.conversation.send_message(formatted_message)

                # Record intervention in history (only on first attempt)
                if attempt == 0:
                    record = InterventionRecord(
                        intervention_id=intervention_id,
                        timestamp=timestamp,
                        type=intervention_type,
                        message=message,
                        structured_data=structured_data,
                        retry_count=attempt,
                    )
                    self.intervention_history.append(record)
                else:
                    # Update retry count for existing record
                    record = next(
                        (
                            r
                            for r in self.intervention_history
                            if r.intervention_id == intervention_id
                        ),
                        None,
                    )
                    if record:
                        record.retry_count = attempt
                        record.last_error = str(last_error) if last_error else None

                # Check if we need to trigger processing
                # Note: RemoteState may not have agent_status, so we handle gracefully
                try:
                    state = self.conversation.state
                    if hasattr(state, "agent_status"):
                        status = state.agent_status
                        status_str = (
                            status.value if hasattr(status, "value") else str(status)
                        )

                        if status_str.lower() == "idle":
                            thread = threading.Thread(
                                target=self.conversation.run, daemon=True
                            )
                            thread.start()
                            logger.info(
                                "Started conversation processing after intervention"
                            )
                        else:
                            logger.info(
                                f"Intervention queued (agent status: {status_str}). "
                                "Message will be processed asynchronously."
                            )
                    else:
                        # RemoteState doesn't expose agent_status directly
                        # Message will be queued and processed automatically
                        logger.info(
                            "Intervention sent. Message will be processed asynchronously."
                        )
                except Exception as e:
                    logger.info(
                        f"Intervention sent (could not check status: {e}). "
                        "Message will be processed asynchronously."
                    )

                # Success - return immediately
                return InterventionResult(
                    success=True,
                    intervention_id=intervention_id,
                    message=message,
                    timestamp=timestamp,
                )
            except Exception as e:
                last_error = e
                error_msg = str(e)
                logger.warning(
                    f"Failed to send intervention (attempt {attempt + 1}/{max_retries}): {error_msg}"
                )

                # If this is the last attempt, record the failure
                if attempt == max_retries - 1:
                    # Update record with final error
                    record = next(
                        (
                            r
                            for r in self.intervention_history
                            if r.intervention_id == intervention_id
                        ),
                        None,
                    )
                    if record:
                        record.last_error = error_msg

                    return InterventionResult(
                        success=False,
                        intervention_id=intervention_id,
                        message=message,
                        timestamp=timestamp,
                        error=error_msg,
                    )

                # Wait before retrying (exponential backoff)
                time.sleep(retry_delay * (2**attempt))

        # Should not reach here, but just in case
        return InterventionResult(
            success=False,
            intervention_id=intervention_id,
            message=message,
            timestamp=timestamp,
            error="Max retries exceeded",
        )

    def send_structured_intervention(
        self,
        intervention_type: InterventionType,
        message: str,
        **kwargs: Any,
    ) -> InterventionResult:
        """
        Send a structured intervention with type-specific formatting.

        Args:
            intervention_type: Type of intervention
            message: Intervention message
            **kwargs: Additional structured data (e.g., target, urgency, reason)

        Returns:
            InterventionResult with success status
        """
        structured_data = kwargs.copy()
        return self.send_intervention(
            message=message,
            intervention_type=intervention_type,
            structured_data=structured_data,
        )

    def get_status(self) -> dict:
        """Get current conversation status."""
        state = self.conversation.state
        status = {
            "conversation_id": str(self.conversation_id),
            "execution_status": state.execution_status.value
            if hasattr(state.execution_status, "value")
            else str(state.execution_status),
            "persistence_dir": state.persistence_dir,
            "intervention_count": len(self.intervention_history),
            "event_count": len(self.event_queue),
        }
        # RemoteState may not have agent_status
        if hasattr(state, "agent_status"):
            status["agent_status"] = (
                state.agent_status.value
                if hasattr(state.agent_status, "value")
                else str(state.agent_status)
            )
        else:
            status["agent_status"] = "unknown"
        return status

    def get_intervention_history(self) -> List[InterventionRecord]:
        """Get history of all interventions sent."""
        return self.intervention_history.copy()

    def get_pending_interventions(self) -> List[InterventionRecord]:
        """Get list of interventions that haven't been acknowledged yet."""
        return [r for r in self.intervention_history if not r.acknowledged]

    def calculate_intervention_effectiveness(
        self, intervention_id: str, desired_outcome: Optional[str] = None
    ) -> Optional[float]:
        """
        Calculate effectiveness score for an intervention.

        Args:
            intervention_id: ID of the intervention to evaluate
            desired_outcome: Optional description of desired outcome

        Returns:
            Effectiveness score (0.0-1.0) or None if cannot be calculated
        """
        record = next(
            (
                r
                for r in self.intervention_history
                if r.intervention_id == intervention_id
            ),
            None,
        )
        if not record:
            return None

        score = 0.0

        # Base score for acknowledgment (50%)
        if record.acknowledged:
            score += 0.5

        # Check if intervention led to desired behavior changes
        # This is a simple heuristic - can be enhanced with LLM analysis
        if record.acknowledgment_message:
            # Check if acknowledgment shows understanding
            ack_lower = record.acknowledgment_message.lower()
            understanding_keywords = [
                "understood",
                "will",
                "focusing",
                "prioritizing",
                "switching",
            ]
            if any(keyword in ack_lower for keyword in understanding_keywords):
                score += 0.3

        # Time-based effectiveness (faster acknowledgment = better)
        if record.acknowledged and record.acknowledgment_timestamp:
            time_to_ack = (
                record.acknowledgment_timestamp - record.timestamp
            ).total_seconds()
            # Acknowledgment within 30 seconds is considered good
            if time_to_ack < 30:
                score += 0.2
            elif time_to_ack < 60:
                score += 0.1

        record.effectiveness_score = min(score, 1.0)
        return record.effectiveness_score

    def start_event_monitoring(self):
        """Start monitoring conversation events in background."""
        if self._event_monitoring:
            logger.warning("Event monitoring already started")
            return

        self._event_monitoring = True

        def monitor_events():
            """Background thread to monitor conversation events."""
            last_event_count = 0
            last_message_count = 0
            while self._event_monitoring:
                try:
                    state = self.conversation.state
                    # Check for new events
                    if hasattr(state, "events") and state.events:
                        current_count = len(state.events)
                        if current_count > last_event_count:
                            # New events detected
                            new_events = state.events[last_event_count:]
                            for event in new_events:
                                event_type_name = type(event).__name__
                                event_data = ConversationEvent(
                                    event_type=event_type_name,
                                    timestamp=datetime.utcnow(),
                                    data={"event": str(event), "raw_event": event},
                                )

                                # Try to extract message content for acknowledgment detection
                                if hasattr(event, "message") or hasattr(
                                    event, "content"
                                ):
                                    try:
                                        # Check if this is a message event that might acknowledge an intervention
                                        message_content = None
                                        if hasattr(event, "message"):
                                            msg = event.message
                                            if hasattr(msg, "content"):
                                                if isinstance(msg.content, list):
                                                    message_content = " ".join(
                                                        str(c)
                                                        for c in msg.content
                                                        if hasattr(c, "text")
                                                    )
                                                else:
                                                    message_content = str(msg.content)
                                        elif hasattr(event, "content"):
                                            message_content = str(event.content)

                                        if message_content:
                                            event_data.data["message_content"] = (
                                                message_content
                                            )
                                            # Check for intervention acknowledgments
                                            self._check_intervention_acknowledgment(
                                                message_content, event_data
                                            )
                                    except Exception as e:
                                        logger.debug(
                                            f"Could not extract message content: {e}"
                                        )

                                self.event_queue.append(event_data)
                                # Notify listeners
                                for listener in self.event_listeners:
                                    try:
                                        listener(event_data)
                                    except Exception as e:
                                        logger.error(f"Event listener error: {e}")
                            last_event_count = current_count

                    # Also check messages for acknowledgments
                    if hasattr(state, "messages") and state.messages:
                        current_msg_count = len(state.messages)
                        if current_msg_count > last_message_count:
                            new_messages = state.messages[last_message_count:]
                            for msg in new_messages:
                                if hasattr(msg, "role") and hasattr(msg, "content"):
                                    role = getattr(msg, "role", None)
                                    if (
                                        role == "assistant"
                                    ):  # Only check assistant messages
                                        content = getattr(msg, "content", "")
                                        if content:
                                            self._check_intervention_acknowledgment(
                                                str(content), None
                                            )
                            last_message_count = current_msg_count

                except Exception as e:
                    logger.error(f"Error monitoring events: {e}")

                time.sleep(0.5)  # Poll every 500ms

        self._event_thread = threading.Thread(target=monitor_events, daemon=True)
        self._event_thread.start()
        logger.info("Started event monitoring")

    def _check_intervention_acknowledgment(
        self, message_content: str, event: Optional[ConversationEvent]
    ):
        """Check if a message acknowledges any pending interventions."""
        message_lower = message_content.lower()

        # Look for acknowledgment patterns
        acknowledgment_keywords = [
            "understood",
            "got it",
            "will do",
            "noted",
            "acknowledged",
            "i'll",
            "i will",
            "focusing on",
            "prioritizing",
            "switching to",
        ]

        # Check each pending intervention
        for record in self.intervention_history:
            if not record.acknowledged:
                # Check if message mentions intervention keywords or content
                intervention_mentioned = any(
                    keyword in message_lower for keyword in acknowledgment_keywords
                )

                # Check if message references the intervention topic
                intervention_topic_mentioned = False
                if record.message:
                    # Extract key words from intervention message
                    intervention_words = [
                        word.lower()
                        for word in record.message.split()
                        if len(word) > 4  # Only meaningful words
                    ]
                    if any(word in message_lower for word in intervention_words[:3]):
                        intervention_topic_mentioned = True

                if intervention_mentioned or intervention_topic_mentioned:
                    record.acknowledged = True
                    record.acknowledgment_timestamp = datetime.utcnow()
                    record.acknowledgment_message = message_content[
                        :200
                    ]  # First 200 chars
                    if event:
                        event.intervention_id = record.intervention_id
                    logger.info(
                        f"Intervention {record.intervention_id} acknowledged: "
                        f"{message_content[:100]}"
                    )

    def stop_event_monitoring(self):
        """Stop monitoring conversation events."""
        self._event_monitoring = False
        if self._event_thread:
            self._event_thread.join(timeout=2)
        logger.info("Stopped event monitoring")

    def add_event_listener(self, callback: Callable[[ConversationEvent], None]):
        """Add a callback to be called when events occur."""
        self.event_listeners.append(callback)

    async def stream_events(
        self, event_types: Optional[List[str]] = None
    ) -> AsyncIterator[ConversationEvent]:
        """
        Stream conversation events asynchronously.

        Args:
            event_types: Optional list of event types to filter (e.g., ["ToolCallEvent", "MessageEvent"])

        Yields:
            ConversationEvent objects as they occur
        """
        if not self._event_monitoring:
            self.start_event_monitoring()

        last_index = 0
        while True:
            # Check for new events
            if len(self.event_queue) > last_index:
                new_events = self.event_queue[last_index:]
                for event in new_events:
                    if event_types is None or event.event_type in event_types:
                        yield event
                last_index = len(self.event_queue)

            await asyncio.sleep(0.1)  # Poll every 100ms


async def run_ticket_with_interventions(
    ticket_id: str,
    title: str,
    description: str,
    repo_url: str,
    branch: str = "main",
    use_docker: bool = False,
    local_workspace_dir: Optional[str] = None,
    host_port: int = 8020,
    intervention_callback: Optional[Callable[[InterventionHandler], None]] = None,
    wait_for_completion: bool = True,
) -> InterventionHandler:
    """
    Run ticket agent with intervention support (Docker or local workspace).

    Args:
        ticket_id: Unique identifier for the ticket
        title: Ticket title
        description: Detailed ticket description
        repo_url: Git repository URL to clone
        branch: Git branch to checkout (default: "main")
        use_docker: If True, use DockerWorkspace. If False, use local directory.
        local_workspace_dir: Local directory path (only used if use_docker=False).
                           Defaults to examples/workspaces/{ticket_id}
        host_port: Host port to expose from container (only used if use_docker=True)
        intervention_callback: Optional callback that receives InterventionHandler
                               when conversation starts
        wait_for_completion: If True, wait for conversation to complete before returning

    Returns:
        InterventionHandler instance for sending interventions
    """
    if use_docker:
        return await run_ticket_in_docker_with_interventions(
            ticket_id=ticket_id,
            title=title,
            description=description,
            repo_url=repo_url,
            branch=branch,
            host_port=host_port,
            intervention_callback=intervention_callback,
            wait_for_completion=wait_for_completion,
        )
    else:
        return await run_ticket_local_with_interventions(
            ticket_id=ticket_id,
            title=title,
            description=description,
            repo_url=repo_url,
            branch=branch,
            workspace_dir=local_workspace_dir,
            intervention_callback=intervention_callback,
            wait_for_completion=wait_for_completion,
        )


async def run_ticket_local_with_interventions(
    ticket_id: str,
    title: str,
    description: str,
    repo_url: str,
    branch: str = "main",
    workspace_dir: Optional[str] = None,
    intervention_callback: Optional[Callable[[InterventionHandler], None]] = None,
    wait_for_completion: bool = True,
) -> InterventionHandler:
    """
    Run ticket agent in local workspace with intervention support.

    Uses a local directory instead of Docker - faster for prototyping but no isolation.

    Args:
        ticket_id: Unique identifier for the ticket
        title: Ticket title
        description: Detailed ticket description
        repo_url: Git repository URL to clone
        branch: Git branch to checkout (default: "main")
        workspace_dir: Local directory path. Defaults to examples/workspaces/{ticket_id}
        intervention_callback: Optional callback that receives InterventionHandler
                               when conversation starts
        wait_for_completion: If True, wait for conversation to complete before returning

    Returns:
        InterventionHandler instance for sending interventions
    """
    llm = build_llm()
    agent = build_agent(llm)

    # Use OOP workspace manager
    workspace_manager = LocalWorkspaceManager(ticket_id, workspace_dir)
    workspace_manager.prepare_workspace()

    # Setup repository using manager
    repo_dir = workspace_manager.setup_repository(repo_url, branch)
    repo_name = repo_dir.name

    # Use OOP conversation runner
    runner = ConversationRunner(
        agent=agent,
        workspace_path=repo_dir,
        ticket_id=ticket_id,
        title=title,
        description=description,
        intervention_callback=intervention_callback,
    )

    # Create conversation
    conversation = runner.create_conversation()

    # Create intervention handler
    intervention_handler = InterventionHandler(conversation)

    # Call intervention callback if provided
    if intervention_callback:
        intervention_callback(intervention_handler)

    # Build and send goal prompt
    goal_prompt = runner.build_goal_prompt(repo_name=repo_name)
    conversation.send_message(goal_prompt)

    logger.info(
        f"Conversation ready. Use InterventionHandler to send messages. "
        f"Conversation ID: {intervention_handler.conversation_id}"
    )
    logger.info("Starting conversation execution...")

    # Run conversation in background thread
    conversation_thread, conversation_error = runner.run_conversation_in_background(
        conversation, wait_for_completion=wait_for_completion
    )

    # If wait_for_completion is False, return immediately
    if not wait_for_completion:
        logger.warning(
            "Returning handler immediately with wait_for_completion=False. "
            "Conversation will continue running in background."
        )
        return intervention_handler

    # Wait for conversation to complete
    logger.info(
        "Waiting for conversation to complete. "
        "You can send interventions using the handler while waiting..."
    )

    max_wait_seconds = 600  # 10 minutes max
    poll_interval = 1.0
    start_time = time.time()

    while conversation_thread.is_alive():
        if time.time() - start_time > max_wait_seconds:
            logger.warning(f"Conversation timeout after {max_wait_seconds} seconds")
            break
        await asyncio.sleep(poll_interval)

    # Thread finished, wait a moment for cleanup
    conversation_thread.join(timeout=5)

    # Check final status
    if conversation_error[0]:
        logger.error(f"Conversation completed with error: {conversation_error[0]}")
    else:
        logger.info("Conversation completed successfully")

    return intervention_handler


async def run_ticket_in_docker_with_interventions(
    ticket_id: str,
    title: str,
    description: str,
    repo_url: str,
    branch: str = "main",
    host_port: int = 8020,
    intervention_callback: Optional[Callable[[InterventionHandler], None]] = None,
    wait_for_completion: bool = True,
) -> InterventionHandler:
    """
    Run ticket agent in Docker workspace with intervention support.

    Spins up a DockerWorkspace, clones the repo, and runs a conversation
    in a background thread. Returns an InterventionHandler that allows
    sending messages to the running conversation.

    Args:
        ticket_id: Unique identifier for the ticket
        title: Ticket title
        description: Detailed ticket description
        repo_url: Git repository URL to clone
        branch: Git branch to checkout (default: "main")
        host_port: Host port to expose from container (default: 8020)
        intervention_callback: Optional callback that receives InterventionHandler
                               when conversation starts (allows immediate setup)

    Returns:
        InterventionHandler instance for sending interventions
    """
    # Lazy import DockerWorkspace to avoid requiring OpenHands SDK root when not using Docker
    from openhands.workspace import DockerWorkspace

    llm = build_llm()
    agent = build_agent(llm)
    platform_str = detect_platform()

    # Docker image with Python + Node used in official examples
    base_image = "nikolaik/python-nodejs:python3.12-nodejs22"

    # Find an available port if the requested one is in use
    actual_port = find_available_port(host_port)
    if actual_port != host_port:
        logger.info("Port %d is in use, using port %d instead", host_port, actual_port)
        host_port = actual_port

    logger.info(
        "Starting DockerWorkspace (image=%s, port=%d)...", base_image, host_port
    )

    with DockerWorkspace(
        base_image=base_image,
        host_port=host_port,
        platform=platform_str,
        extra_ports=False,
    ) as workspace:
        # Use OOP workspace manager
        workspace_manager = DockerWorkspaceManager(ticket_id, workspace, host_port)
        workspace_manager.prepare_workspace()

        # Setup repository using manager
        repo_dir = workspace_manager.setup_repository(repo_url, branch)
        repo_name = repo_dir.name

        # Wait for Docker workspace agent server to be fully ready
        await asyncio.sleep(3)

        # Use OOP conversation runner
        runner = ConversationRunner(
            agent=agent,
            workspace_path=repo_dir,
            ticket_id=ticket_id,
            title=title,
            description=description,
            intervention_callback=intervention_callback,
        )

        # Create conversation with retry logic (handled by runner)
        # For Docker, pass workspace object directly (not path string)
        conversation = runner.create_conversation(
            retry_count=5, workspace_obj=workspace
        )

        # Create intervention handler
        intervention_handler = InterventionHandler(conversation)

        # Call intervention callback if provided
        if intervention_callback:
            intervention_callback(intervention_handler)

        # Build and send goal prompt with Docker-specific instructions
        goal_prompt = f"""
You are working on ticket {ticket_id}: {title}

Ticket description:
{description}

Instructions:
- Work inside the repository directory: {repo_name}
- The repository has been cloned into a subdirectory within the workspace.
- Use file editor + terminal tools to implement the change.
- IMPORTANT: Do NOT start or modify the OpenHands agent server running on port 8000.
  That is container infrastructure, not part of the repository you're working on.
- If you need to test a server, use port {host_port} (exposed to host) or any port other than 8000.
- Run tests before finishing.
- When done, summarize the changes and what remains risky.
"""

        conversation.send_message(goal_prompt)

        # For RemoteConversation, we need to run in the main thread but allow interventions
        # We'll use a different approach: run the conversation with a timeout/check mechanism
        # that allows us to check for completion while still being able to send interventions

        # Store the conversation in the handler for later access
        # The conversation will be run, but we'll monitor it and allow interventions

        logger.info(
            f"Conversation ready. Use InterventionHandler to send messages. "
            f"Conversation ID: {intervention_handler.conversation_id}"
        )
        logger.info("Starting conversation execution...")

        # For RemoteConversation with DockerWorkspace, we need to be careful about
        # when we run the conversation. The server connection needs to be stable.
        # We'll run it in a background thread but wait a bit longer for the server to be ready.

        # Additional wait to ensure the agent server is fully ready
        logger.info("Waiting additional time for agent server to stabilize...")
        await asyncio.sleep(5)  # Give more time for server to be ready

        # Run conversation in background thread using runner
        conversation_thread, conversation_error = runner.run_conversation_in_background(
            conversation, wait_for_completion=wait_for_completion
        )

        # If wait_for_completion is False, return immediately (caller manages workspace lifecycle)
        # If True, we'll wait for completion before returning (workspace stays alive)
        if not wait_for_completion:
            logger.warning(
                "Returning handler immediately with wait_for_completion=False. "
                "WARNING: DockerWorkspace will close when function returns, "
                "which may terminate the conversation. Interventions may not work."
            )
            return intervention_handler

        # Wait for conversation to complete (keeps workspace alive)
        # This allows interventions to be sent while waiting
        # We'll poll the thread instead of blocking join() so we can check status
        logger.info(
            "Waiting for conversation to complete (workspace will stay alive). "
            "You can send interventions using the handler while waiting..."
        )

        # Poll thread status instead of blocking join, so we can still send interventions
        max_wait_seconds = 600  # 10 minutes max
        poll_interval = 1.0  # Check every second
        start_time = time.time()

        while conversation_thread.is_alive():
            if time.time() - start_time > max_wait_seconds:
                logger.warning(f"Conversation timeout after {max_wait_seconds} seconds")
                break
            await asyncio.sleep(poll_interval)

        # Thread finished, wait a moment for cleanup
        conversation_thread.join(timeout=5)

        # Check final status
        if conversation_error[0]:
            logger.error(f"Conversation completed with error: {conversation_error[0]}")
        else:
            logger.info("Conversation completed successfully")

        # Return handler (workspace will close when we exit the with block)
        return intervention_handler


# Example: Interactive intervention session
async def interactive_intervention_example():
    """
    Interactive example where you can send interventions via command line.

    Usage:
        # Start the conversation
        handler = await run_ticket_in_docker_with_interventions(...)

        # In another thread or async task, send interventions:
        handler.send_intervention("Please focus on testing first")
        handler.send_intervention("Make sure the endpoint returns proper JSON")
        status = handler.get_status()  # Check current status
    """
    ticket_id = "T-789"
    title = "Implement comprehensive API with authentication and testing"
    description = (
        "Create a complete REST API with the following requirements:\n"
        "1. Add user authentication endpoints (/auth/login, /auth/register)\n"
        "2. Implement JWT token generation and validation\n"
        "3. Create a user management system with CRUD operations\n"
        "4. Add comprehensive unit tests for all endpoints\n"
        "5. Add integration tests\n"
        "6. Create API documentation (OpenAPI/Swagger)\n"
        "7. Add request validation and error handling\n"
        "8. Implement rate limiting\n"
        "\n"
        "This is a complex task that should take significant time. Work methodically "
        "and test each component as you build it. Use port 8999 or any port other than 8000."
    )

    repo_url = os.getenv(
        "REPO_URL", "git@github.com:hesreallyhim/awesome-claude-code.git"
    )

    print("Starting conversation with intervention support...")

    def setup_interventions(handler: InterventionHandler):
        """Setup function called when conversation starts."""
        print(f"\n[Setup] Intervention handler ready: {handler.conversation_id}")
        # You could send an initial intervention here if needed
        # handler.send_intervention("Please focus on clean, testable code")

    # Use local workspace for faster prototyping (set use_docker=True for Docker)
    handler = await run_ticket_with_interventions(
        ticket_id=ticket_id,
        title=title,
        description=description,
        repo_url=repo_url,
        branch="main",
        use_docker=False,  # Set to True for Docker, False for local workspace
        intervention_callback=setup_interventions,
        wait_for_completion=True,  # Keep workspace alive so interventions work
    )

    print("\n" + "=" * 70)
    print("CONVERSATION RUNNING - ENHANCED INTERVENTION HANDLER READY")
    print("=" * 70)
    print(f"\nConversation ID: {handler.conversation_id}")
    print("\nAvailable intervention methods:")
    print("  handler.send_intervention('message')  # Basic intervention")
    print(
        "  handler.send_structured_intervention(InterventionType.PRIORITIZE, 'message')"
    )
    print("  handler.get_status()  # Check status")
    print("  handler.get_intervention_history()  # View all interventions")
    print("  handler.get_pending_interventions()  # Get unacknowledged interventions")
    print(
        "  handler.calculate_intervention_effectiveness(id)  # Get effectiveness score"
    )
    print("  handler.start_event_monitoring()  # Start event streaming")
    print("  async for event in handler.stream_events(): ...  # Stream events")
    print("\nExample interventions:")
    print("  handler.send_structured_intervention(")
    print("      InterventionType.PRIORITIZE,")
    print("      'Focus on writing tests first',")
    print("      target='test_coverage', urgency='high'")
    print("  )")
    print("  handler.send_intervention('Make sure to use port 8020')")
    print("\n" + "=" * 70 + "\n")

    # Start event monitoring
    handler.start_event_monitoring()

    # Add event listener for real-time updates
    def on_event(event: ConversationEvent):
        """Handle conversation events."""
        print(f"[EVENT] {event.event_type}: {event.data.get('event', '')[:100]}")

    handler.add_event_listener(on_event)

    # Example: Send some interventions after a delay
    async def send_delayed_interventions():
        """Example of sending interventions after some time."""
        import sys

        print(
            "\n🔔 Intervention sender task started - will send interventions in 2s and 10s",
            flush=True,
        )
        sys.stdout.flush()
        # Send first intervention after a short delay
        await asyncio.sleep(2)  # Wait 2 seconds to let conversation start
        import sys

        print("\n" + "=" * 70, flush=True)
        print("[Example] Sending structured intervention: PRIORITIZE tests", flush=True)
        print("=" * 70, flush=True)
        sys.stdout.flush()
        try:
            result = handler.send_structured_intervention(
                InterventionType.PRIORITIZE,
                "Please make sure tests pass",
                target="test_coverage",
                urgency="high",
            )
            print(f"  ✅ Intervention sent! ID: {result.intervention_id}")
            print(f"  Success: {result.success}")
            if not result.success:
                print(
                    f"  ❌ Error: {result.error if hasattr(result, 'error') else 'Unknown error'}"
                )
            else:
                print("  📝 Message: 'Please make sure tests pass'")
                print(f"  📊 Type: {InterventionType.PRIORITIZE.value}")
        except Exception as e:
            print(f"  ❌ Exception sending intervention: {e}")
            import traceback

            traceback.print_exc()

        await asyncio.sleep(8)  # Wait another 8 seconds
        print("\n" + "=" * 70)
        print("[Example] Sending intervention: 'Focus on clean code structure'")
        print("=" * 70)
        try:
            result = handler.send_intervention("Focus on clean code structure")
            print(f"  ✅ Intervention sent! ID: {result.intervention_id}")
            print(f"  Success: {result.success}")
            if not result.success:
                print(
                    f"  ❌ Error: {result.error if hasattr(result, 'error') else 'Unknown error'}"
                )
            else:
                print("  📝 Message: 'Focus on clean code structure'")
        except Exception as e:
            print(f"  ❌ Exception sending intervention: {e}")
            import traceback

            traceback.print_exc()

    # Start intervention task
    intervention_task = asyncio.create_task(send_delayed_interventions())

    # Monitor conversation with progress updates
    max_wait_time = 120  # Reduced to 2 minutes for faster testing
    start_time = time.time()
    check_interval = 3  # Check more frequently

    print("\n📊 Monitoring conversation progress...")
    print("   (Press Ctrl+C to stop early and see current state)\n")

    while True:
        status = handler.get_status()
        execution_status = status["execution_status"]
        agent_status = status["agent_status"]

        # Show pending interventions count
        pending = handler.get_pending_interventions()
        pending_count = len(pending)

        elapsed = int(time.time() - start_time)
        status_line = (
            f"[{elapsed:3d}s] Execution: {execution_status:12s} | "
            f"Agent: {agent_status:12s} | "
            f"Interventions: {len(handler.intervention_history)} sent, {pending_count} pending"
        )
        print(status_line)

        if execution_status in ["finished", "failed", "cancelled"]:
            break

        if time.time() - start_time > max_wait_time:
            logger.warning(
                f"Conversation timeout after {max_wait_time}s - stopping early"
            )
            print("\n⏱️  Timeout reached. Stopping early to show current state...")
            break

        await asyncio.sleep(check_interval)

    # Cancel intervention task if still running
    if not intervention_task.done():
        intervention_task.cancel()

    # Get final state
    state = handler.conversation.state
    execution_status = state.execution_status

    last_text = ""
    try:
        if hasattr(state, "messages") and state.messages:
            last_msg = state.messages[-1]
            last_text = getattr(last_msg, "content", "")
        elif hasattr(state, "events") and state.events:
            from openhands.sdk.event import MessageEvent

            for event in reversed(state.events):
                if isinstance(event, MessageEvent):
                    msg = event.to_llm_message()
                    if msg.role == "assistant":
                        last_text = msg.content
                        break
        if not last_text:
            last_text = "Execution completed. Check conversation logs for details."
    except Exception as e:
        logger.warning(f"Could not retrieve final message: {e}")
        last_text = "Execution completed. Check conversation logs for details."

    print(f"\n=== Ticket {ticket_id} finished ===")
    print(f"Execution status: {execution_status}")
    print("\n--- Final assistant message ---\n")
    print(last_text)

    # Stop event monitoring
    handler.stop_event_monitoring()

    # Show intervention history with effectiveness scores
    print("\n" + "=" * 70)
    print("INTERVENTION HISTORY")
    print("=" * 70)
    history = handler.get_intervention_history()
    if history:
        for record in history:
            print(f"\n[{record.timestamp}] {record.type.value.upper()}")
            print(f"  Message: {record.message}")
            if record.structured_data:
                print(f"  Data: {record.structured_data}")
            print(f"  Acknowledged: {record.acknowledged}")
            if record.acknowledged:
                print(f"  Acknowledged at: {record.acknowledgment_timestamp}")
                if record.acknowledgment_message:
                    print(f"  Response: {record.acknowledgment_message[:100]}...")
                # Calculate and show effectiveness
                effectiveness = handler.calculate_intervention_effectiveness(
                    record.intervention_id
                )
                if effectiveness is not None:
                    print(f"  Effectiveness Score: {effectiveness:.2f}/1.0")
            if record.retry_count > 0:
                print(f"  Retries: {record.retry_count}")
            if record.last_error:
                print(f"  Last Error: {record.last_error[:100]}")
    else:
        print("No interventions were sent.")

    # Show pending interventions
    pending = handler.get_pending_interventions()
    if pending:
        print(f"\n⚠️  {len(pending)} intervention(s) still pending acknowledgment")
    else:
        print("\n✅ All interventions have been acknowledged!")

    print("=" * 70)


if __name__ == "__main__":
    # Run interactive example
    asyncio.run(interactive_intervention_example())
