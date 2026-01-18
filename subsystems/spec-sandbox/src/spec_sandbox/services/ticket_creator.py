"""Ticket creation service for spec-sandbox.

Creates tickets and tasks in the OmoiOS backend from spec phase outputs.
Supports both HTTP API calls and event-based notification.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from spec_sandbox.reporters.base import Reporter
from spec_sandbox.schemas.events import Event, EventTypes


@dataclass
class TicketCreatorConfig:
    """Configuration for ticket creation."""

    api_url: str
    project_id: str
    api_key: Optional[str] = None
    user_id: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3


@dataclass
class TicketResult:
    """Result of creating a single ticket."""

    local_id: str
    api_id: Optional[str] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class TaskResult:
    """Result of creating a single task."""

    local_id: str
    api_id: Optional[str] = None
    ticket_api_id: Optional[str] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class TicketCreationSummary:
    """Summary of ticket creation operation."""

    tickets_created: int = 0
    tickets_failed: int = 0
    tasks_created: int = 0
    tasks_failed: int = 0
    ticket_results: List[TicketResult] = field(default_factory=list)
    task_results: List[TaskResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for event payload."""
        return {
            "tickets_created": self.tickets_created,
            "tickets_failed": self.tickets_failed,
            "tasks_created": self.tasks_created,
            "tasks_failed": self.tasks_failed,
            "errors": self.errors,
            "ticket_ids": [r.api_id for r in self.ticket_results if r.success],
            "task_ids": [r.api_id for r in self.task_results if r.success],
        }


class TicketCreator:
    """Creates tickets and tasks from spec phase outputs.

    This service bridges the spec-sandbox (local spec generation) with
    the OmoiOS backend (ticket/task management). It:

    1. Takes the TASKS phase output containing tickets and tasks
    2. Creates tickets in the backend API with proper user_id assignment
    3. Creates tasks linked to tickets
    4. Emits events for progress tracking

    Usage:
        creator = TicketCreator(
            config=TicketCreatorConfig(
                api_url="https://api.omoios.dev",
                project_id="proj-123",
                api_key="sk-...",
                user_id="user-456",
            ),
            reporter=reporter,
            spec_id="spec-789",
        )

        summary = await creator.create_from_phase_output(tasks_output)
    """

    def __init__(
        self,
        config: TicketCreatorConfig,
        reporter: Reporter,
        spec_id: str,
    ) -> None:
        self.config = config
        self.reporter = reporter
        self.spec_id = spec_id
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {}
            if self.config.api_key:
                headers["X-API-Key"] = self.config.api_key

            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers=headers,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _emit(
        self,
        event_type: str,
        data: Optional[dict] = None,
    ) -> None:
        """Emit an event through the reporter."""
        event = Event(
            event_type=event_type,
            spec_id=self.spec_id,
            data=data,
        )
        await self.reporter.report(event)

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[dict] = None,
    ) -> tuple[int, Optional[dict]]:
        """Make HTTP request to API with retry logic."""
        client = await self._get_client()
        url = f"{self.config.api_url.rstrip('/')}{endpoint}"

        for attempt in range(self.config.max_retries):
            try:
                response = await client.request(method, url, json=json)
                try:
                    data = response.json()
                except Exception:
                    data = None
                return response.status_code, data
            except httpx.RequestError as e:
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(0.5 * (2**attempt))
                else:
                    return 0, {"error": str(e)}

        return 0, {"error": "Unknown error"}

    async def create_ticket(
        self,
        title: str,
        description: str,
        priority: str = "MEDIUM",
        phase_id: str = "PHASE_IMPLEMENTATION",
        context: Optional[Dict[str, Any]] = None,
    ) -> TicketResult:
        """Create a single ticket in the backend.

        Args:
            title: Ticket title
            description: Ticket description (full body for AI context)
            priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)
            phase_id: Kanban phase (PHASE_INITIAL, PHASE_IMPLEMENTATION, etc.)
            context: Additional context data (spec_id, requirements, etc.)

        Returns:
            TicketResult with success status and API ID if created
        """
        payload = {
            "title": title,
            "description": description,
            "priority": priority,
            "phase_id": phase_id,
            "project_id": self.config.project_id,
        }

        # Add user_id if available (critical for visibility on board)
        if self.config.user_id:
            payload["user_id"] = self.config.user_id

        # Add context with spec reference
        ticket_context = {"spec_id": self.spec_id, "source": "spec_sandbox"}
        if context:
            ticket_context.update(context)
        payload["context"] = ticket_context

        status, data = await self._request("POST", "/api/v1/tickets", json=payload)

        if status in (200, 201) and data:
            api_id = data.get("id")
            return TicketResult(
                local_id=title,  # Use title as local identifier
                api_id=api_id,
                success=True,
            )
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return TicketResult(
                local_id=title,
                success=False,
                error=f"Failed to create ticket: {error}",
            )

    async def create_task(
        self,
        ticket_api_id: str,
        title: str,
        description: str,
        task_type: str = "implementation",
        priority: str = "MEDIUM",
        phase_id: str = "PHASE_IMPLEMENTATION",
        dependencies: Optional[List[str]] = None,
    ) -> TaskResult:
        """Create a single task linked to a ticket.

        Args:
            ticket_api_id: Parent ticket's API ID
            title: Task title
            description: Task description (full body for AI context)
            task_type: Type of task (implementation, test, research, etc.)
            priority: Priority level
            phase_id: Kanban phase
            dependencies: List of task IDs this depends on

        Returns:
            TaskResult with success status and API ID if created
        """
        payload = {
            "ticket_id": ticket_api_id,
            "title": title,
            "description": description,
            "task_type": task_type,
            "priority": priority,
            "phase_id": phase_id,
        }

        if dependencies:
            payload["dependencies"] = {"depends_on": dependencies}

        status, data = await self._request("POST", "/api/v1/tasks", json=payload)

        if status in (200, 201) and data:
            api_id = data.get("id")
            return TaskResult(
                local_id=title,
                api_id=api_id,
                ticket_api_id=ticket_api_id,
                success=True,
            )
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return TaskResult(
                local_id=title,
                ticket_api_id=ticket_api_id,
                success=False,
                error=f"Failed to create task: {error}",
            )

    async def create_from_phase_output(
        self,
        tasks_output: Dict[str, Any],
    ) -> TicketCreationSummary:
        """Create tickets and tasks from TASKS phase output.

        Expects the TASKS phase output format:
        {
            "tickets": [
                {
                    "id": "TKT-001",
                    "title": "...",
                    "description": "...",
                    "priority": "HIGH",
                    "tasks": ["TSK-001", "TSK-002"]
                }
            ],
            "tasks": [
                {
                    "id": "TSK-001",
                    "title": "...",
                    "description": "...",
                    "parent_ticket": "TKT-001",
                    "type": "implementation",
                    "dependencies": {"depends_on": []}
                }
            ]
        }

        Returns:
            TicketCreationSummary with results
        """
        summary = TicketCreationSummary()

        tickets = tasks_output.get("tickets", [])
        tasks = tasks_output.get("tasks", [])

        if not tickets and not tasks:
            summary.errors.append("No tickets or tasks found in phase output")
            return summary

        await self._emit(
            EventTypes.TICKETS_CREATION_STARTED,
            data={
                "ticket_count": len(tickets),
                "task_count": len(tasks),
            },
        )

        # Track local ID -> API ID mapping for tasks
        ticket_id_map: Dict[str, str] = {}

        # Create tickets first
        for ticket_data in tickets:
            local_id = ticket_data.get("id", ticket_data.get("title", "unknown"))
            title = ticket_data.get("title", local_id)
            description = ticket_data.get("description", "")
            priority = ticket_data.get("priority", "MEDIUM").upper()

            # Build context with requirements reference
            context = {}
            if "requirements" in ticket_data:
                context["requirements"] = ticket_data["requirements"]

            result = await self.create_ticket(
                title=title,
                description=description,
                priority=priority,
                context=context,
            )

            summary.ticket_results.append(result)

            if result.success:
                summary.tickets_created += 1
                ticket_id_map[local_id] = result.api_id
                await self._emit(
                    EventTypes.TICKET_CREATED,
                    data={
                        "local_id": local_id,
                        "api_id": result.api_id,
                        "title": title,
                    },
                )
            else:
                summary.tickets_failed += 1
                summary.errors.append(result.error or f"Failed to create ticket {local_id}")

        # Create tasks linked to tickets
        task_id_map: Dict[str, str] = {}  # For dependency resolution

        for task_data in tasks:
            local_id = task_data.get("id", task_data.get("title", "unknown"))
            title = task_data.get("title", local_id)
            description = task_data.get("description", task_data.get("objective", ""))
            parent_ticket = task_data.get("parent_ticket", "")
            task_type = task_data.get("type", "implementation")
            priority = task_data.get("priority", "MEDIUM").upper()

            # Get parent ticket API ID
            ticket_api_id = ticket_id_map.get(parent_ticket)
            if not ticket_api_id:
                summary.tasks_failed += 1
                summary.errors.append(
                    f"Task {local_id}: Parent ticket {parent_ticket} not found"
                )
                continue

            # Resolve dependencies to API IDs
            deps = task_data.get("dependencies", {})
            depends_on = deps.get("depends_on", []) if isinstance(deps, dict) else []
            resolved_deps = [task_id_map[d] for d in depends_on if d in task_id_map]

            result = await self.create_task(
                ticket_api_id=ticket_api_id,
                title=title,
                description=description,
                task_type=task_type,
                priority=priority,
                dependencies=resolved_deps if resolved_deps else None,
            )

            summary.task_results.append(result)

            if result.success:
                summary.tasks_created += 1
                task_id_map[local_id] = result.api_id
                await self._emit(
                    EventTypes.TASK_CREATED,
                    data={
                        "local_id": local_id,
                        "api_id": result.api_id,
                        "ticket_api_id": ticket_api_id,
                        "title": title,
                    },
                )
            else:
                summary.tasks_failed += 1
                summary.errors.append(result.error or f"Failed to create task {local_id}")

        await self._emit(
            EventTypes.TICKETS_CREATION_COMPLETED,
            data=summary.to_dict(),
        )

        return summary
