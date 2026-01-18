"""Markdown sync service for syncing generated files to backend API.

The sync service:
1. Reads markdown files with frontmatter from a directory
2. Validates frontmatter against Pydantic schemas
3. Converts frontmatter + body to API payloads
4. Creates tickets/tasks via the backend API
5. Emits events for progress tracking
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from spec_sandbox.parsers.markdown import (
    MarkdownParseError,
    parse_markdown_with_frontmatter,
    parse_task_markdown,
    parse_ticket_markdown,
)
from spec_sandbox.reporters.base import Reporter
from spec_sandbox.schemas.events import Event, EventTypes
from spec_sandbox.schemas.frontmatter import TaskFrontmatter, TicketFrontmatter


@dataclass
class SyncConfig:
    """Configuration for markdown sync service."""

    api_url: str
    project_id: str
    spec_id: str
    api_key: Optional[str] = None
    user_id: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    dry_run: bool = False


@dataclass
class SyncResult:
    """Result of syncing a single item."""

    local_id: str
    api_id: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    file_path: Optional[Path] = None


@dataclass
class SyncSummary:
    """Summary of sync operation."""

    tickets_synced: int = 0
    tickets_failed: int = 0
    tasks_synced: int = 0
    tasks_failed: int = 0
    ticket_results: List[SyncResult] = field(default_factory=list)
    task_results: List[SyncResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    ticket_id_map: Dict[str, str] = field(default_factory=dict)
    task_id_map: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "tickets_synced": self.tickets_synced,
            "tickets_failed": self.tickets_failed,
            "tasks_synced": self.tasks_synced,
            "tasks_failed": self.tasks_failed,
            "errors": self.errors,
            "ticket_ids": list(self.ticket_id_map.values()),
            "task_ids": list(self.task_id_map.values()),
        }


class MarkdownSyncService:
    """Syncs markdown files to backend API.

    The service reads markdown files from a directory structure:
    ```
    output_dir/
    ├── tickets/
    │   ├── TKT-001.md
    │   └── TKT-002.md
    └── tasks/
        ├── TSK-001.md
        └── TSK-002.md
    ```

    Each file is parsed for YAML frontmatter (structured data) and
    markdown body (description). The frontmatter is validated against
    Pydantic models and converted to API payloads.

    Usage:
        service = MarkdownSyncService(config, reporter)
        summary = await service.sync_directory(Path("./output"))
    """

    def __init__(
        self,
        config: SyncConfig,
        reporter: Optional[Reporter] = None,
    ) -> None:
        self.config = config
        self.reporter = reporter
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {}
            if self.config.api_key:
                # Use Bearer token authentication (standard for JWT)
                headers["Authorization"] = f"Bearer {self.config.api_key}"

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
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an event through the reporter."""
        if self.reporter is None:
            return

        event = Event(
            event_type=event_type,
            spec_id=self.config.spec_id,
            data=data,
        )
        await self.reporter.report(event)

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
    ) -> tuple[int, Optional[Dict[str, Any]]]:
        """Make HTTP request to API."""
        if self.config.dry_run:
            # Simulate successful creation in dry-run mode
            return 201, {"id": f"dry-run-{endpoint.split('/')[-1]}"}

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
                    import asyncio

                    await asyncio.sleep(0.5 * (2**attempt))
                else:
                    return 0, {"error": str(e)}

        return 0, {"error": "Unknown error"}

    async def sync_directory(self, output_dir: Path) -> SyncSummary:
        """Sync all markdown files from a directory.

        Args:
            output_dir: Directory containing tickets/ and tasks/ subdirectories

        Returns:
            SyncSummary with results
        """
        summary = SyncSummary()

        tickets_dir = output_dir / "tickets"
        tasks_dir = output_dir / "tasks"

        # Count files to sync
        ticket_files = list(tickets_dir.glob("TKT-*.md")) if tickets_dir.exists() else []
        task_files = list(tasks_dir.glob("TSK-*.md")) if tasks_dir.exists() else []

        await self._emit(
            EventTypes.SYNC_STARTED,
            data={
                "ticket_count": len(ticket_files),
                "task_count": len(task_files),
                "dry_run": self.config.dry_run,
            },
        )

        # Sync tickets first (tasks depend on ticket IDs)
        if tickets_dir.exists():
            await self._sync_tickets(tickets_dir, summary)

        # Sync tasks (using ticket ID map for parent resolution)
        if tasks_dir.exists():
            await self._sync_tasks(tasks_dir, summary)

        await self._emit(
            EventTypes.SYNC_COMPLETED,
            data=summary.to_dict(),
        )

        return summary

    async def _sync_tickets(self, tickets_dir: Path, summary: SyncSummary) -> None:
        """Sync all ticket markdown files."""
        for ticket_file in sorted(tickets_dir.glob("TKT-*.md")):
            result = await self._sync_ticket_file(ticket_file)
            summary.ticket_results.append(result)

            if result.success and result.api_id:
                summary.tickets_synced += 1
                summary.ticket_id_map[result.local_id] = result.api_id
            else:
                summary.tickets_failed += 1
                if result.error:
                    summary.errors.append(f"Ticket {result.local_id}: {result.error}")

    async def _sync_ticket_file(self, file_path: Path) -> SyncResult:
        """Sync a single ticket markdown file."""
        try:
            ticket, body = parse_ticket_markdown(file_path)
        except MarkdownParseError as e:
            return SyncResult(
                local_id=file_path.stem,
                success=False,
                error=str(e),
                file_path=file_path,
            )

        # Convert to API payload
        payload = ticket.to_api_payload(
            project_id=self.config.project_id,
            spec_id=self.config.spec_id,
        )
        payload["description"] = body  # Markdown body becomes description

        # Add user_id if configured
        if self.config.user_id:
            payload["user_id"] = self.config.user_id

        status, data = await self._request("POST", "/api/v1/tickets", json=payload)

        if status in (200, 201) and data:
            api_id = data.get("id")
            await self._emit(
                EventTypes.TICKET_CREATED,
                data={
                    "local_id": ticket.id,
                    "api_id": api_id,
                    "title": ticket.title,
                },
            )
            return SyncResult(
                local_id=ticket.id,
                api_id=api_id,
                success=True,
                file_path=file_path,
            )
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return SyncResult(
                local_id=ticket.id,
                success=False,
                error=error,
                file_path=file_path,
            )

    async def _sync_tasks(self, tasks_dir: Path, summary: SyncSummary) -> None:
        """Sync all task markdown files."""
        for task_file in sorted(tasks_dir.glob("TSK-*.md")):
            result = await self._sync_task_file(task_file, summary.ticket_id_map)
            summary.task_results.append(result)

            if result.success and result.api_id:
                summary.tasks_synced += 1
                summary.task_id_map[result.local_id] = result.api_id
            else:
                summary.tasks_failed += 1
                if result.error:
                    summary.errors.append(f"Task {result.local_id}: {result.error}")

    async def _sync_task_file(
        self,
        file_path: Path,
        ticket_id_map: Dict[str, str],
    ) -> SyncResult:
        """Sync a single task markdown file."""
        try:
            task, body = parse_task_markdown(file_path)
        except MarkdownParseError as e:
            return SyncResult(
                local_id=file_path.stem,
                success=False,
                error=str(e),
                file_path=file_path,
            )

        # Resolve parent ticket to API ID
        ticket_api_id = ticket_id_map.get(task.parent_ticket)
        if not ticket_api_id:
            return SyncResult(
                local_id=task.id,
                success=False,
                error=f"Parent ticket {task.parent_ticket} not found in sync",
                file_path=file_path,
            )

        # Convert to API payload
        payload = task.to_api_payload(ticket_api_id=ticket_api_id)
        payload["description"] = body  # Markdown body becomes description

        status, data = await self._request("POST", "/api/v1/tasks", json=payload)

        if status in (200, 201) and data:
            api_id = data.get("id")
            await self._emit(
                EventTypes.TASK_CREATED,
                data={
                    "local_id": task.id,
                    "api_id": api_id,
                    "ticket_api_id": ticket_api_id,
                    "title": task.title,
                },
            )
            return SyncResult(
                local_id=task.id,
                api_id=api_id,
                success=True,
                file_path=file_path,
            )
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return SyncResult(
                local_id=task.id,
                success=False,
                error=error,
                file_path=file_path,
            )

    async def sync_from_phase_output(
        self,
        tasks_output: Dict[str, Any],
    ) -> SyncSummary:
        """Sync directly from TASKS phase output (without markdown files).

        This is an alternative to sync_directory when you have the
        phase output in memory and don't need to read from files.

        Args:
            tasks_output: Output from TASKS phase with tickets and tasks

        Returns:
            SyncSummary with results
        """
        summary = SyncSummary()

        tickets = tasks_output.get("tickets", [])
        tasks = tasks_output.get("tasks", [])

        await self._emit(
            EventTypes.SYNC_STARTED,
            data={
                "ticket_count": len(tickets),
                "task_count": len(tasks),
                "dry_run": self.config.dry_run,
            },
        )

        # Create tickets
        for ticket_data in tickets:
            result = await self._sync_ticket_dict(ticket_data)
            summary.ticket_results.append(result)

            if result.success and result.api_id:
                summary.tickets_synced += 1
                summary.ticket_id_map[result.local_id] = result.api_id
            else:
                summary.tickets_failed += 1
                if result.error:
                    summary.errors.append(f"Ticket {result.local_id}: {result.error}")

        # Create tasks
        for task_data in tasks:
            result = await self._sync_task_dict(task_data, summary.ticket_id_map)
            summary.task_results.append(result)

            if result.success and result.api_id:
                summary.tasks_synced += 1
                summary.task_id_map[result.local_id] = result.api_id
            else:
                summary.tasks_failed += 1
                if result.error:
                    summary.errors.append(f"Task {result.local_id}: {result.error}")

        await self._emit(
            EventTypes.SYNC_COMPLETED,
            data=summary.to_dict(),
        )

        return summary

    async def _sync_ticket_dict(self, ticket_data: Dict[str, Any]) -> SyncResult:
        """Sync a ticket from dict data."""
        local_id = ticket_data.get("id", "unknown")
        title = ticket_data.get("title", local_id)
        description = ticket_data.get("description", "")
        priority = ticket_data.get("priority", "MEDIUM")

        payload = {
            "title": title,
            "description": description,
            "priority": priority,
            "project_id": self.config.project_id,
            "context": {
                "local_id": local_id,
                "spec_id": self.config.spec_id,
                "source": "spec_sandbox",
            },
        }

        if self.config.user_id:
            payload["user_id"] = self.config.user_id

        status, data = await self._request("POST", "/api/v1/tickets", json=payload)

        if status in (200, 201) and data:
            api_id = data.get("id")
            await self._emit(
                EventTypes.TICKET_CREATED,
                data={"local_id": local_id, "api_id": api_id, "title": title},
            )
            return SyncResult(local_id=local_id, api_id=api_id, success=True)
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return SyncResult(local_id=local_id, success=False, error=error)

    async def _sync_task_dict(
        self,
        task_data: Dict[str, Any],
        ticket_id_map: Dict[str, str],
    ) -> SyncResult:
        """Sync a task from dict data."""
        local_id = task_data.get("id", "unknown")
        title = task_data.get("title", local_id)
        description = task_data.get("description", task_data.get("objective", ""))
        parent_ticket = task_data.get("parent_ticket", "")
        task_type = task_data.get("type", "implementation")
        priority = task_data.get("priority", "MEDIUM")

        ticket_api_id = ticket_id_map.get(parent_ticket)
        if not ticket_api_id:
            return SyncResult(
                local_id=local_id,
                success=False,
                error=f"Parent ticket {parent_ticket} not found",
            )

        payload = {
            "ticket_id": ticket_api_id,
            "title": title,
            "description": description,
            "task_type": task_type,
            "priority": priority,
        }

        status, data = await self._request("POST", "/api/v1/tasks", json=payload)

        if status in (200, 201) and data:
            api_id = data.get("id")
            await self._emit(
                EventTypes.TASK_CREATED,
                data={
                    "local_id": local_id,
                    "api_id": api_id,
                    "ticket_api_id": ticket_api_id,
                    "title": title,
                },
            )
            return SyncResult(local_id=local_id, api_id=api_id, success=True)
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return SyncResult(local_id=local_id, success=False, error=error)
