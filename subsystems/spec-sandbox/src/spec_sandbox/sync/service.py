"""Markdown sync service for syncing generated files to backend API.

The sync service:
1. Reads markdown files with frontmatter from a directory
2. Validates frontmatter against Pydantic schemas
3. Converts frontmatter + body to API payloads
4. Creates or updates tickets/tasks via the backend API
5. Emits events for progress tracking

Sync Behavior:
- CREATE: New tickets/tasks are created if they don't exist
- UPDATE: If item exists but description differs, update it
- SKIP: If item exists with same description, skip
- FAILED: If sync operation fails
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


# =============================================================================
# Helper Functions for Data Transformation
# =============================================================================


def parse_ears_text(text: str) -> Tuple[str, str]:
    """Parse EARS-format text into condition and action.

    EARS format: "WHEN [condition], THE SYSTEM SHALL [action]"
    Also handles variations like "WHEN ... THE SYSTEM SHALL ..." without comma.

    Args:
        text: EARS-formatted requirement text

    Returns:
        Tuple of (condition, action). Returns original text as action if parsing fails.
    """
    if not text:
        return "", ""

    # Try pattern: WHEN ... , THE SYSTEM SHALL ...
    pattern1 = r"^WHEN\s+(.+?),?\s+THE SYSTEM SHALL\s+(.+?)\.?$"
    match = re.match(pattern1, text.strip(), re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # Try pattern: WHEN ... THE SYSTEM SHALL ... (no comma)
    pattern2 = r"^WHEN\s+(.+?)\s+THE SYSTEM SHALL\s+(.+?)\.?$"
    match = re.match(pattern2, text.strip(), re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # Fallback: return empty condition, text as action
    return "", text.strip()


def convert_data_models_to_markdown(data_models: List[Dict[str, Any]]) -> str:
    """Convert data models list to markdown string for backend storage.

    Args:
        data_models: List of data model dicts with name, table_name, fields, etc.

    Returns:
        Markdown string representing the data models.
    """
    if not data_models:
        return ""

    lines = []
    for model in data_models:
        name = model.get("name", "Unknown")
        table_name = model.get("table_name", "")
        description = model.get("description", "")

        lines.append(f"### {name}")
        if table_name:
            lines.append(f"**Table:** `{table_name}`")
        if description:
            lines.append(f"\n{description}\n")

        fields = model.get("fields", [])
        if fields:
            lines.append("\n| Field | Type | Description |")
            lines.append("|-------|------|-------------|")
            for field_data in fields:
                fname = field_data.get("name", "")
                ftype = field_data.get("type", "")
                fdesc = field_data.get("description", "")
                lines.append(f"| {fname} | {ftype} | {fdesc} |")

        relationships = model.get("relationships", [])
        if relationships:
            lines.append("\n**Relationships:**")
            for rel in relationships:
                if isinstance(rel, dict):
                    lines.append(f"- {rel.get('description', str(rel))}")
                else:
                    lines.append(f"- {rel}")

        lines.append("")

    return "\n".join(lines)


def convert_api_endpoints_to_spec(api_endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert api_endpoints to api_spec format expected by backend.

    Args:
        api_endpoints: List from design phase output

    Returns:
        List in api_spec format: [{method, path, description, ...}]
    """
    api_spec = []
    for ep in api_endpoints:
        spec_entry = {
            "method": ep.get("method", "GET"),
            "endpoint": ep.get("path", ep.get("endpoint", "")),
            "description": ep.get("description", ""),
        }
        # Include optional fields if present
        if ep.get("auth_required") is not None:
            spec_entry["auth_required"] = ep.get("auth_required")
        if ep.get("request_schema"):
            spec_entry["request_body"] = ep.get("request_schema")
        if ep.get("response_schema"):
            spec_entry["response"] = ep.get("response_schema")
        api_spec.append(spec_entry)
    return api_spec


class SyncAction(Enum):
    """Action taken during sync."""

    CREATED = "created"
    UPDATED = "updated"
    SKIPPED = "skipped"
    FAILED = "failed"


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
    action: SyncAction = SyncAction.FAILED
    api_id: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    message: str = ""
    file_path: Optional[Path] = None


@dataclass
class SyncSummary:
    """Summary of sync operation."""

    tickets_created: int = 0
    tickets_updated: int = 0
    tickets_skipped: int = 0
    tickets_failed: int = 0
    tasks_created: int = 0
    tasks_updated: int = 0
    tasks_skipped: int = 0
    tasks_failed: int = 0
    requirements_created: int = 0
    requirements_updated: int = 0
    requirements_skipped: int = 0
    requirements_failed: int = 0
    design_updated: bool = False
    design_skipped: bool = False
    design_failed: bool = False
    ticket_results: List[SyncResult] = field(default_factory=list)
    task_results: List[SyncResult] = field(default_factory=list)
    requirement_results: List[SyncResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    ticket_id_map: Dict[str, str] = field(default_factory=dict)
    task_id_map: Dict[str, str] = field(default_factory=dict)
    requirement_id_map: Dict[str, str] = field(default_factory=dict)

    # Backwards compatibility properties
    @property
    def tickets_synced(self) -> int:
        """Total tickets successfully synced (created + updated)."""
        return self.tickets_created + self.tickets_updated

    @property
    def tasks_synced(self) -> int:
        """Total tasks successfully synced (created + updated)."""
        return self.tasks_created + self.tasks_updated

    @property
    def requirements_synced(self) -> int:
        """Total requirements successfully synced (created + updated)."""
        return self.requirements_created + self.requirements_updated

    def add_ticket_result(self, result: SyncResult) -> None:
        """Add a ticket result and update counters."""
        self.ticket_results.append(result)
        if result.action == SyncAction.CREATED:
            self.tickets_created += 1
        elif result.action == SyncAction.UPDATED:
            self.tickets_updated += 1
        elif result.action == SyncAction.SKIPPED:
            self.tickets_skipped += 1
        elif result.action == SyncAction.FAILED:
            self.tickets_failed += 1
            if result.error:
                self.errors.append(f"Ticket {result.local_id}: {result.error}")
        if result.api_id:
            self.ticket_id_map[result.local_id] = result.api_id

    def add_task_result(self, result: SyncResult) -> None:
        """Add a task result and update counters."""
        self.task_results.append(result)
        if result.action == SyncAction.CREATED:
            self.tasks_created += 1
        elif result.action == SyncAction.UPDATED:
            self.tasks_updated += 1
        elif result.action == SyncAction.SKIPPED:
            self.tasks_skipped += 1
        elif result.action == SyncAction.FAILED:
            self.tasks_failed += 1
            if result.error:
                self.errors.append(f"Task {result.local_id}: {result.error}")
        if result.api_id:
            self.task_id_map[result.local_id] = result.api_id

    def add_requirement_result(self, result: SyncResult) -> None:
        """Add a requirement result and update counters."""
        self.requirement_results.append(result)
        if result.action == SyncAction.CREATED:
            self.requirements_created += 1
        elif result.action == SyncAction.UPDATED:
            self.requirements_updated += 1
        elif result.action == SyncAction.SKIPPED:
            self.requirements_skipped += 1
        elif result.action == SyncAction.FAILED:
            self.requirements_failed += 1
            if result.error:
                self.errors.append(f"Requirement {result.local_id}: {result.error}")
        if result.api_id:
            self.requirement_id_map[result.local_id] = result.api_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "tickets_created": self.tickets_created,
            "tickets_updated": self.tickets_updated,
            "tickets_skipped": self.tickets_skipped,
            "tickets_failed": self.tickets_failed,
            "tickets_synced": self.tickets_synced,
            "tasks_created": self.tasks_created,
            "tasks_updated": self.tasks_updated,
            "tasks_skipped": self.tasks_skipped,
            "tasks_failed": self.tasks_failed,
            "tasks_synced": self.tasks_synced,
            "requirements_created": self.requirements_created,
            "requirements_updated": self.requirements_updated,
            "requirements_skipped": self.requirements_skipped,
            "requirements_failed": self.requirements_failed,
            "requirements_synced": self.requirements_synced,
            "design_updated": self.design_updated,
            "design_skipped": self.design_skipped,
            "design_failed": self.design_failed,
            "errors": self.errors,
            "ticket_ids": list(self.ticket_id_map.values()),
            "task_ids": list(self.task_id_map.values()),
            "requirement_ids": list(self.requirement_id_map.values()),
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
        if self.config.dry_run and method != "GET":
            # Simulate successful creation/update in dry-run mode (but allow GET)
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

    async def _list_tickets(self) -> List[Dict[str, Any]]:
        """Fetch existing tickets from API for the project."""
        status, data = await self._request(
            "GET", f"/api/v1/tickets?project_id={self.config.project_id}"
        )
        if status == 200 and isinstance(data, list):
            return data
        elif status == 200 and isinstance(data, dict):
            # Handle paginated response
            return data.get("items", data.get("tickets", []))
        return []

    async def _list_tasks(self) -> List[Dict[str, Any]]:
        """Fetch existing tasks from API."""
        status, data = await self._request("GET", "/api/v1/tasks")
        if status == 200 and isinstance(data, list):
            return data
        elif status == 200 and isinstance(data, dict):
            return data.get("items", data.get("tasks", []))
        return []

    async def _update_ticket(
        self, ticket_id: str, payload: Dict[str, Any]
    ) -> tuple[int, Optional[Dict[str, Any]]]:
        """Update an existing ticket."""
        return await self._request("PATCH", f"/api/v1/tickets/{ticket_id}", json=payload)

    async def _update_task(
        self, task_id: str, payload: Dict[str, Any]
    ) -> tuple[int, Optional[Dict[str, Any]]]:
        """Update an existing task."""
        return await self._request("PATCH", f"/api/v1/tasks/{task_id}", json=payload)

    # =========================================================================
    # Spec Requirements and Design API Methods
    # =========================================================================

    async def _get_spec(self) -> Optional[Dict[str, Any]]:
        """Fetch the spec with requirements and design."""
        status, data = await self._request(
            "GET", f"/api/v1/specs/{self.config.spec_id}"
        )
        if status == 200 and isinstance(data, dict):
            return data
        return None

    async def _list_spec_requirements(self) -> List[Dict[str, Any]]:
        """Fetch existing requirements for the spec."""
        spec = await self._get_spec()
        if spec:
            return spec.get("requirements", [])
        return []

    async def _get_spec_design(self) -> Optional[Dict[str, Any]]:
        """Fetch existing design for the spec."""
        spec = await self._get_spec()
        if spec:
            return spec.get("design")
        return None

    async def _create_requirement(
        self, payload: Dict[str, Any]
    ) -> tuple[int, Optional[Dict[str, Any]]]:
        """Create a new requirement for the spec."""
        return await self._request(
            "POST", f"/api/v1/specs/{self.config.spec_id}/requirements", json=payload
        )

    async def _update_requirement(
        self, req_id: str, payload: Dict[str, Any]
    ) -> tuple[int, Optional[Dict[str, Any]]]:
        """Update an existing requirement."""
        return await self._request(
            "PATCH", f"/api/v1/specs/{self.config.spec_id}/requirements/{req_id}",
            json=payload
        )

    async def _update_design(
        self, design: Dict[str, Any]
    ) -> tuple[int, Optional[Dict[str, Any]]]:
        """Update the spec design."""
        return await self._request(
            "PUT", f"/api/v1/specs/{self.config.spec_id}/design", json=design
        )

    async def sync_directory(self, output_dir: Path) -> SyncSummary:
        """Sync all markdown files from a directory.

        Behavior:
        - CREATE: If ticket/task doesn't exist (by title match)
        - UPDATE: If exists but description differs
        - SKIP: If exists with same description

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

        # Fetch existing items for comparison (create/update/skip logic)
        existing_tickets = await self._list_tickets()
        existing_tasks = await self._list_tasks()

        # Build lookup by title for comparison
        ticket_by_title = {t.get("title", ""): t for t in existing_tickets}
        task_by_title = {t.get("title", ""): t for t in existing_tasks}

        # Sync tickets first (tasks depend on ticket IDs)
        if tickets_dir.exists():
            await self._sync_tickets(tickets_dir, summary, ticket_by_title)

        # Sync tasks (using ticket ID map for parent resolution)
        if tasks_dir.exists():
            await self._sync_tasks(tasks_dir, summary, task_by_title)

        await self._emit(
            EventTypes.SYNC_COMPLETED,
            data=summary.to_dict(),
        )

        return summary

    async def _sync_tickets(
        self,
        tickets_dir: Path,
        summary: SyncSummary,
        existing_tickets: Dict[str, Dict[str, Any]],
    ) -> None:
        """Sync all ticket markdown files with create/update/skip logic."""
        for ticket_file in sorted(tickets_dir.glob("TKT-*.md")):
            result = await self._sync_ticket_file(ticket_file, existing_tickets)
            summary.add_ticket_result(result)

    async def _sync_ticket_file(
        self,
        file_path: Path,
        existing_tickets: Dict[str, Dict[str, Any]],
    ) -> SyncResult:
        """Sync a single ticket markdown file with create/update/skip logic."""
        try:
            ticket, body = parse_ticket_markdown(file_path)
        except MarkdownParseError as e:
            return SyncResult(
                local_id=file_path.stem,
                action=SyncAction.FAILED,
                success=False,
                error=str(e),
                file_path=file_path,
            )

        # Check if ticket already exists by title
        existing = existing_tickets.get(ticket.title)

        if existing:
            # Ticket exists - check if we need to update description
            existing_desc = (existing.get("description") or "").strip()
            new_desc = body.strip()

            if existing_desc == new_desc:
                # Same description - skip
                return SyncResult(
                    local_id=ticket.id,
                    action=SyncAction.SKIPPED,
                    api_id=existing.get("id"),
                    success=True,
                    message="Already exists with same description",
                    file_path=file_path,
                )
            else:
                # Different description - update
                if self.config.dry_run:
                    return SyncResult(
                        local_id=ticket.id,
                        action=SyncAction.UPDATED,
                        api_id=existing.get("id"),
                        success=True,
                        message="Would update description (dry run)",
                        file_path=file_path,
                    )

                status, data = await self._update_ticket(
                    existing["id"], {"description": body}
                )
                if status in (200, 201) and data:
                    api_id = data.get("id", existing.get("id"))
                    await self._emit(
                        EventTypes.TICKET_UPDATED,
                        data={
                            "local_id": ticket.id,
                            "api_id": api_id,
                            "title": ticket.title,
                        },
                    )
                    return SyncResult(
                        local_id=ticket.id,
                        action=SyncAction.UPDATED,
                        api_id=api_id,
                        success=True,
                        message="Updated description",
                        file_path=file_path,
                    )
                else:
                    error = data.get("detail", str(data)) if data else f"HTTP {status}"
                    return SyncResult(
                        local_id=ticket.id,
                        action=SyncAction.FAILED,
                        success=False,
                        error=error,
                        file_path=file_path,
                    )

        # Ticket doesn't exist - create new
        payload = ticket.to_api_payload(
            project_id=self.config.project_id,
            spec_id=self.config.spec_id,
        )
        payload["description"] = body

        if self.config.user_id:
            payload["user_id"] = self.config.user_id

        if self.config.dry_run:
            return SyncResult(
                local_id=ticket.id,
                action=SyncAction.CREATED,
                api_id=f"dry-run-{ticket.id}",
                success=True,
                message="Would create (dry run)",
                file_path=file_path,
            )

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
                action=SyncAction.CREATED,
                api_id=api_id,
                success=True,
                message="Created",
                file_path=file_path,
            )
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return SyncResult(
                local_id=ticket.id,
                action=SyncAction.FAILED,
                success=False,
                error=error,
                file_path=file_path,
            )

    async def _sync_tasks(
        self,
        tasks_dir: Path,
        summary: SyncSummary,
        existing_tasks: Dict[str, Dict[str, Any]],
    ) -> None:
        """Sync all task markdown files with create/update/skip logic."""
        for task_file in sorted(tasks_dir.glob("TSK-*.md")):
            result = await self._sync_task_file(
                task_file, summary.ticket_id_map, existing_tasks
            )
            summary.add_task_result(result)

    async def _sync_task_file(
        self,
        file_path: Path,
        ticket_id_map: Dict[str, str],
        existing_tasks: Dict[str, Dict[str, Any]],
    ) -> SyncResult:
        """Sync a single task markdown file with create/update/skip logic."""
        try:
            task, body = parse_task_markdown(file_path)
        except MarkdownParseError as e:
            return SyncResult(
                local_id=file_path.stem,
                action=SyncAction.FAILED,
                success=False,
                error=str(e),
                file_path=file_path,
            )

        # Resolve parent ticket to API ID
        ticket_api_id = ticket_id_map.get(task.parent_ticket)
        if not ticket_api_id:
            return SyncResult(
                local_id=task.id,
                action=SyncAction.FAILED,
                success=False,
                error=f"Parent ticket {task.parent_ticket} not found in sync",
                file_path=file_path,
            )

        # Check if task already exists by title
        existing = existing_tasks.get(task.title)

        if existing:
            # Task exists - check if we need to update description
            existing_desc = (existing.get("description") or "").strip()
            new_desc = body.strip()

            if existing_desc == new_desc:
                # Same description - skip
                return SyncResult(
                    local_id=task.id,
                    action=SyncAction.SKIPPED,
                    api_id=existing.get("id"),
                    success=True,
                    message="Already exists with same description",
                    file_path=file_path,
                )
            else:
                # Different description - update
                if self.config.dry_run:
                    return SyncResult(
                        local_id=task.id,
                        action=SyncAction.UPDATED,
                        api_id=existing.get("id"),
                        success=True,
                        message="Would update description (dry run)",
                        file_path=file_path,
                    )

                status, data = await self._update_task(
                    existing["id"], {"description": body}
                )
                if status in (200, 201) and data:
                    api_id = data.get("id", existing.get("id"))
                    await self._emit(
                        EventTypes.TASK_UPDATED,
                        data={
                            "local_id": task.id,
                            "api_id": api_id,
                            "ticket_api_id": ticket_api_id,
                            "title": task.title,
                        },
                    )
                    return SyncResult(
                        local_id=task.id,
                        action=SyncAction.UPDATED,
                        api_id=api_id,
                        success=True,
                        message="Updated description",
                        file_path=file_path,
                    )
                else:
                    error = data.get("detail", str(data)) if data else f"HTTP {status}"
                    return SyncResult(
                        local_id=task.id,
                        action=SyncAction.FAILED,
                        success=False,
                        error=error,
                        file_path=file_path,
                    )

        # Task doesn't exist - create new
        # Pass description and ensure phase_id=PHASE_IMPLEMENTATION for continuous mode
        payload = task.to_api_payload(
            ticket_api_id=ticket_api_id,
            description=body,
            phase_id="PHASE_IMPLEMENTATION",
        )

        if self.config.dry_run:
            return SyncResult(
                local_id=task.id,
                action=SyncAction.CREATED,
                api_id=f"dry-run-{task.id}",
                success=True,
                message="Would create (dry run)",
                file_path=file_path,
            )

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
                action=SyncAction.CREATED,
                api_id=api_id,
                success=True,
                message="Created",
                file_path=file_path,
            )
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return SyncResult(
                local_id=task.id,
                action=SyncAction.FAILED,
                success=False,
                error=error,
                file_path=file_path,
            )

    async def sync_from_phase_output(
        self,
        tasks_output: Dict[str, Any],
    ) -> SyncSummary:
        """Sync directly from TASKS phase output (without markdown files).

        Behavior:
        - CREATE: If ticket/task doesn't exist (by title match)
        - UPDATE: If exists but description differs
        - SKIP: If exists with same description

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

        # Fetch existing items for comparison (create/update/skip logic)
        existing_tickets = await self._list_tickets()
        existing_tasks = await self._list_tasks()

        # Build lookup by title for comparison
        ticket_by_title = {t.get("title", ""): t for t in existing_tickets}
        task_by_title = {t.get("title", ""): t for t in existing_tasks}

        # Sync tickets
        for ticket_data in tickets:
            result = await self._sync_ticket_dict(ticket_data, ticket_by_title)
            summary.add_ticket_result(result)

        # Sync tasks
        for task_data in tasks:
            result = await self._sync_task_dict(
                task_data, summary.ticket_id_map, task_by_title
            )
            summary.add_task_result(result)

        await self._emit(
            EventTypes.SYNC_COMPLETED,
            data=summary.to_dict(),
        )

        return summary

    async def _sync_ticket_dict(
        self,
        ticket_data: Dict[str, Any],
        existing_tickets: Dict[str, Dict[str, Any]],
    ) -> SyncResult:
        """Sync a ticket from dict data with create/update/skip logic."""
        local_id = ticket_data.get("id", "unknown")
        title = ticket_data.get("title", local_id)
        description = ticket_data.get("description", "")
        priority = ticket_data.get("priority", "MEDIUM")

        # Check if ticket already exists by title
        existing = existing_tickets.get(title)

        if existing:
            # Ticket exists - check if we need to update description
            existing_desc = (existing.get("description") or "").strip()
            new_desc = description.strip()

            if existing_desc == new_desc:
                # Same description - skip
                return SyncResult(
                    local_id=local_id,
                    action=SyncAction.SKIPPED,
                    api_id=existing.get("id"),
                    success=True,
                    message="Already exists with same description",
                )
            else:
                # Different description - update
                if self.config.dry_run:
                    return SyncResult(
                        local_id=local_id,
                        action=SyncAction.UPDATED,
                        api_id=existing.get("id"),
                        success=True,
                        message="Would update description (dry run)",
                    )

                status, data = await self._update_ticket(
                    existing["id"], {"description": description}
                )
                if status in (200, 201) and data:
                    api_id = data.get("id", existing.get("id"))
                    await self._emit(
                        EventTypes.TICKET_UPDATED,
                        data={"local_id": local_id, "api_id": api_id, "title": title},
                    )
                    return SyncResult(
                        local_id=local_id,
                        action=SyncAction.UPDATED,
                        api_id=api_id,
                        success=True,
                        message="Updated description",
                    )
                else:
                    error = data.get("detail", str(data)) if data else f"HTTP {status}"
                    return SyncResult(
                        local_id=local_id,
                        action=SyncAction.FAILED,
                        success=False,
                        error=error,
                    )

        # Ticket doesn't exist - create new
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

        if self.config.dry_run:
            return SyncResult(
                local_id=local_id,
                action=SyncAction.CREATED,
                api_id=f"dry-run-{local_id}",
                success=True,
                message="Would create (dry run)",
            )

        status, data = await self._request("POST", "/api/v1/tickets", json=payload)

        if status in (200, 201) and data:
            api_id = data.get("id")
            await self._emit(
                EventTypes.TICKET_CREATED,
                data={"local_id": local_id, "api_id": api_id, "title": title},
            )
            return SyncResult(
                local_id=local_id,
                action=SyncAction.CREATED,
                api_id=api_id,
                success=True,
                message="Created",
            )
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return SyncResult(
                local_id=local_id,
                action=SyncAction.FAILED,
                success=False,
                error=error,
            )

    async def _sync_task_dict(
        self,
        task_data: Dict[str, Any],
        ticket_id_map: Dict[str, str],
        existing_tasks: Dict[str, Dict[str, Any]],
    ) -> SyncResult:
        """Sync a task from dict data with create/update/skip logic."""
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
                action=SyncAction.FAILED,
                success=False,
                error=f"Parent ticket {parent_ticket} not found",
            )

        # Check if task already exists by title
        existing = existing_tasks.get(title)

        if existing:
            # Task exists - check if we need to update description
            existing_desc = (existing.get("description") or "").strip()
            new_desc = description.strip()

            if existing_desc == new_desc:
                # Same description - skip
                return SyncResult(
                    local_id=local_id,
                    action=SyncAction.SKIPPED,
                    api_id=existing.get("id"),
                    success=True,
                    message="Already exists with same description",
                )
            else:
                # Different description - update
                if self.config.dry_run:
                    return SyncResult(
                        local_id=local_id,
                        action=SyncAction.UPDATED,
                        api_id=existing.get("id"),
                        success=True,
                        message="Would update description (dry run)",
                    )

                status, data = await self._update_task(
                    existing["id"], {"description": description}
                )
                if status in (200, 201) and data:
                    api_id = data.get("id", existing.get("id"))
                    await self._emit(
                        EventTypes.TASK_UPDATED,
                        data={
                            "local_id": local_id,
                            "api_id": api_id,
                            "ticket_api_id": ticket_api_id,
                            "title": title,
                        },
                    )
                    return SyncResult(
                        local_id=local_id,
                        action=SyncAction.UPDATED,
                        api_id=api_id,
                        success=True,
                        message="Updated description",
                    )
                else:
                    error = data.get("detail", str(data)) if data else f"HTTP {status}"
                    return SyncResult(
                        local_id=local_id,
                        action=SyncAction.FAILED,
                        success=False,
                        error=error,
                    )

        # Task doesn't exist - create new
        payload = {
            "ticket_id": ticket_api_id,
            "title": title,
            "description": description,
            "task_type": task_type,
            "priority": priority,
        }

        if self.config.dry_run:
            return SyncResult(
                local_id=local_id,
                action=SyncAction.CREATED,
                api_id=f"dry-run-{local_id}",
                success=True,
                message="Would create (dry run)",
            )

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
            return SyncResult(
                local_id=local_id,
                action=SyncAction.CREATED,
                api_id=api_id,
                success=True,
                message="Created",
            )
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return SyncResult(
                local_id=local_id,
                action=SyncAction.FAILED,
                success=False,
                error=error,
            )

    # =========================================================================
    # Requirements and Design Sync Methods
    # =========================================================================

    async def sync_requirements_to_spec(
        self,
        requirements: List[Dict[str, Any]],
        summary: Optional[SyncSummary] = None,
    ) -> SyncSummary:
        """Sync requirements to the spec document.

        Args:
            requirements: List of requirement dicts with title, condition, action
            summary: Optional existing summary to add to

        Returns:
            SyncSummary with results
        """
        if summary is None:
            summary = SyncSummary()

        await self._emit(
            EventTypes.REQUIREMENTS_SYNC_STARTED,
            data={"requirement_count": len(requirements)},
        )

        # Fetch existing requirements for comparison
        existing_reqs = await self._list_spec_requirements()
        req_by_title = {r.get("title", ""): r for r in existing_reqs}

        for req_data in requirements:
            result = await self._sync_requirement(req_data, req_by_title)
            summary.add_requirement_result(result)

        await self._emit(
            EventTypes.REQUIREMENTS_SYNC_COMPLETED,
            data={
                "requirements_created": summary.requirements_created,
                "requirements_updated": summary.requirements_updated,
                "requirements_skipped": summary.requirements_skipped,
                "requirements_failed": summary.requirements_failed,
            },
        )

        return summary

    async def _sync_requirement(
        self,
        req_data: Dict[str, Any],
        existing_reqs: Dict[str, Dict[str, Any]],
    ) -> SyncResult:
        """Sync a single requirement with create/update/skip logic.

        Handles both formats:
        - Direct condition/action fields
        - EARS 'text' field that needs parsing
        """
        local_id = req_data.get("id", "unknown")
        title = req_data.get("title", local_id)

        # Get condition/action - either directly or parse from 'text' field
        condition = req_data.get("condition", "")
        action = req_data.get("action", "")

        # If condition/action are empty, try to parse from 'text' field (EARS format)
        if not condition and not action:
            text = req_data.get("text", "")
            if text:
                condition, action = parse_ears_text(text)

        linked_design = req_data.get("linked_design")

        # Get acceptance criteria (list of strings or dicts)
        acceptance_criteria = req_data.get("acceptance_criteria", [])
        # Normalize to list of strings
        criteria_list = []
        for crit in acceptance_criteria:
            if isinstance(crit, dict):
                criteria_list.append(crit.get("text", str(crit)))
            else:
                criteria_list.append(str(crit))

        # Check if requirement already exists by title
        existing = existing_reqs.get(title)

        if existing:
            # Requirement exists - check if we need to update
            existing_condition = existing.get("condition", "").strip()
            existing_action = existing.get("action", "").strip()

            if existing_condition == condition.strip() and existing_action == action.strip():
                # Same content - skip
                return SyncResult(
                    local_id=local_id,
                    action=SyncAction.SKIPPED,
                    api_id=existing.get("id"),
                    success=True,
                    message="Already exists with same content",
                )
            else:
                # Different content - update
                if self.config.dry_run:
                    return SyncResult(
                        local_id=local_id,
                        action=SyncAction.UPDATED,
                        api_id=existing.get("id"),
                        success=True,
                        message="Would update (dry run)",
                    )

                payload = {"condition": condition, "action": action}
                if linked_design:
                    payload["linked_design"] = linked_design
                if criteria_list:
                    payload["acceptance_criteria"] = criteria_list

                status, data = await self._update_requirement(existing["id"], payload)
                if status in (200, 201) and data:
                    api_id = data.get("id", existing.get("id"))
                    await self._emit(
                        EventTypes.REQUIREMENT_UPDATED,
                        data={"local_id": local_id, "api_id": api_id, "title": title},
                    )
                    return SyncResult(
                        local_id=local_id,
                        action=SyncAction.UPDATED,
                        api_id=api_id,
                        success=True,
                        message="Updated",
                    )
                else:
                    error = data.get("detail", str(data)) if data else f"HTTP {status}"
                    return SyncResult(
                        local_id=local_id,
                        action=SyncAction.FAILED,
                        success=False,
                        error=error,
                    )

        # Requirement doesn't exist - create new
        payload = {
            "title": title,
            "condition": condition,
            "action": action,
        }
        if linked_design:
            payload["linked_design"] = linked_design
        if criteria_list:
            payload["acceptance_criteria"] = criteria_list

        if self.config.dry_run:
            return SyncResult(
                local_id=local_id,
                action=SyncAction.CREATED,
                api_id=f"dry-run-{local_id}",
                success=True,
                message="Would create (dry run)",
            )

        status, data = await self._create_requirement(payload)

        if status in (200, 201) and data:
            api_id = data.get("id")
            await self._emit(
                EventTypes.REQUIREMENT_CREATED,
                data={"local_id": local_id, "api_id": api_id, "title": title},
            )
            return SyncResult(
                local_id=local_id,
                action=SyncAction.CREATED,
                api_id=api_id,
                success=True,
                message="Created",
            )
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return SyncResult(
                local_id=local_id,
                action=SyncAction.FAILED,
                success=False,
                error=error,
            )

    async def sync_design_to_spec(
        self,
        design: Dict[str, Any],
        summary: Optional[SyncSummary] = None,
    ) -> SyncSummary:
        """Sync design to the spec document.

        Args:
            design: Design dict with architecture, data_model, api_spec
            summary: Optional existing summary to add to

        Returns:
            SyncSummary with results
        """
        if summary is None:
            summary = SyncSummary()

        await self._emit(
            EventTypes.DESIGN_SYNC_STARTED,
            data={"has_architecture": bool(design.get("architecture"))},
        )

        # Fetch existing design for comparison
        existing_design = await self._get_spec_design()

        # Compare designs (simple check - could be more sophisticated)
        if existing_design and self._designs_equal(existing_design, design):
            summary.design_skipped = True
            await self._emit(
                EventTypes.DESIGN_SYNC_COMPLETED,
                data={"design_skipped": True, "reason": "No changes"},
            )
            return summary

        # Update design
        if self.config.dry_run:
            summary.design_updated = True
            await self._emit(
                EventTypes.DESIGN_SYNC_COMPLETED,
                data={"design_updated": True, "dry_run": True},
            )
            return summary

        status, data = await self._update_design(design)

        if status in (200, 201):
            summary.design_updated = True
            await self._emit(
                EventTypes.DESIGN_UPDATED,
                data={"spec_id": self.config.spec_id},
            )
            await self._emit(
                EventTypes.DESIGN_SYNC_COMPLETED,
                data={"design_updated": True},
            )
        else:
            summary.design_failed = True
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            summary.errors.append(f"Design sync failed: {error}")
            await self._emit(
                EventTypes.DESIGN_SYNC_COMPLETED,
                data={"design_failed": True, "error": error},
            )

        return summary

    def _designs_equal(
        self, existing: Dict[str, Any], new: Dict[str, Any]
    ) -> bool:
        """Compare two designs for equality."""
        import json

        # Compare architecture
        if existing.get("architecture") != new.get("architecture"):
            return False

        # Compare data_model
        if existing.get("data_model") != new.get("data_model"):
            return False

        # Compare api_spec (normalize to compare)
        existing_api = existing.get("api_spec", [])
        new_api = new.get("api_spec", [])
        if len(existing_api) != len(new_api):
            return False

        # Simple comparison - could be more sophisticated
        return json.dumps(existing_api, sort_keys=True) == json.dumps(new_api, sort_keys=True)

    async def sync_phase_outputs_to_spec(
        self,
        requirements_output: Optional[Dict[str, Any]] = None,
        design_output: Optional[Dict[str, Any]] = None,
    ) -> SyncSummary:
        """Sync requirements and design phase outputs to the spec document.

        This is the main method to sync the outputs of REQUIREMENTS and DESIGN
        phases to the spec document API. It handles both requirements and design
        in a single call for convenience.

        Args:
            requirements_output: Output from REQUIREMENTS phase
            design_output: Output from DESIGN phase

        Returns:
            SyncSummary with combined results
        """
        summary = SyncSummary()

        # Sync requirements if provided
        if requirements_output:
            requirements = requirements_output.get("requirements", [])
            if requirements:
                await self.sync_requirements_to_spec(requirements, summary)

        # Sync design if provided
        if design_output:
            # Map from generated output field names to backend expected field names:
            # - architecture_diagram (or architecture_overview) -> architecture
            # - data_models (list of dicts) -> data_model (markdown string)
            # - api_endpoints -> api_spec
            architecture = design_output.get("architecture_diagram") or design_output.get("architecture_overview") or design_output.get("architecture", "")

            # Convert data_models list to markdown string
            data_models = design_output.get("data_models", [])
            if isinstance(data_models, list) and data_models:
                data_model = convert_data_models_to_markdown(data_models)
            else:
                data_model = design_output.get("data_model", "")

            # Convert api_endpoints to api_spec format
            api_endpoints = design_output.get("api_endpoints", [])
            if api_endpoints:
                api_spec = convert_api_endpoints_to_spec(api_endpoints)
            else:
                api_spec = design_output.get("api_spec", [])

            design = {
                "architecture": architecture,
                "data_model": data_model,
                "api_spec": api_spec,
            }
            # Only sync if there's actual design content
            if any(design.values()):
                await self.sync_design_to_spec(design, summary)

        return summary
