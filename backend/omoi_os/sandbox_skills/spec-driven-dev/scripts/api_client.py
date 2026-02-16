#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.25",
#     "pyyaml>=6.0",
# ]
# ///
"""
Direct API client for OmoiOS backend (bypasses MCP server).

This module provides the OmoiOSClient class for syncing local specs
to the OmoiOS backend API.

Sync Behavior:
- CREATE: New tickets/tasks are created
- UPDATE DESCRIPTION: If item exists but description differs, update it
- SKIP: If item exists with same description, skip

Usage:
    from api_client import OmoiOSClient
    from parse_specs import SpecParser

    client = OmoiOSClient()
    parser = SpecParser()
    result = parser.parse_all()

    await client.sync(result)
"""

import asyncio
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import httpx

# Default API URL - can be overridden via environment variable
DEFAULT_API_URL = "http://localhost:18000"

from models import (
    ParseResult,
    ParsedDesign,
    ParsedRequirement,
    ParsedTask,
    ParsedTicket,
)


class SyncAction(Enum):
    """Action taken during sync."""

    CREATED = "created"
    UPDATED = "updated"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class SyncResult:
    """Result of syncing a single item."""

    item_id: str
    item_type: str  # "ticket" or "task"
    action: SyncAction
    message: str = ""


@dataclass
class SyncSummary:
    """Summary of sync operation."""

    results: list[SyncResult]
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0

    def add(self, result: SyncResult):
        self.results.append(result)
        if result.action == SyncAction.CREATED:
            self.created += 1
        elif result.action == SyncAction.UPDATED:
            self.updated += 1
        elif result.action == SyncAction.SKIPPED:
            self.skipped += 1
        elif result.action == SyncAction.FAILED:
            self.failed += 1


class OmoiOSClient:
    """Direct HTTP client for OmoiOS API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        token: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 3,
    ):
        """Initialize client.

        Args:
            base_url: Base URL of OmoiOS API. If not provided, uses
                      OMOIOS_API_URL environment variable, or falls back
                      to DEFAULT_API_URL (http://localhost:18000)
            timeout: Request timeout in seconds
            token: JWT access token for authentication. If not provided,
                   uses OMOIOS_TOKEN environment variable.
            api_key: API key for authentication (alternative to JWT).
                     If not provided, uses OMOIOS_API_KEY environment variable.
            max_retries: Maximum number of retries for failed requests
        """
        # Resolve base URL: explicit > env var > default
        if base_url:
            self.base_url = base_url.rstrip("/")
        else:
            self.base_url = os.environ.get("OMOIOS_API_URL", DEFAULT_API_URL).rstrip(
                "/"
            )

        self.timeout = timeout
        self.max_retries = max_retries

        # Resolve auth: explicit > env var
        self.token = token or os.environ.get("OMOIOS_TOKEN")
        self.api_key = api_key or os.environ.get("OMOIOS_API_KEY")

        # Persistent client for connection pooling
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the persistent HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[dict] = None,
    ) -> tuple[int, Optional[dict]]:
        """Make HTTP request to API with retry logic.

        Returns:
            Tuple of (status_code, response_json or None)
        """
        url = f"{self.base_url}{endpoint}"
        headers = {}
        if self.api_key:
            # API key authentication takes precedence
            headers["X-API-Key"] = self.api_key
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        client = await self._get_client()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = await client.request(method, url, json=json, headers=headers)
                try:
                    data = response.json()
                except Exception:
                    data = None
                return response.status_code, data
            except httpx.RequestError as e:
                last_error = e
                # Wait before retry (exponential backoff)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (2**attempt))
                continue

        # All retries failed
        return 0, {"error": str(last_error) if last_error else "Unknown error"}

    # ========================================================================
    # Ticket Operations
    # ========================================================================

    async def get_ticket(self, ticket_id: str) -> Optional[dict]:
        """Get ticket by ID."""
        status, data = await self._request("GET", f"/api/v1/tickets/{ticket_id}")
        if status == 200:
            return data
        return None

    async def create_ticket(
        self, ticket: ParsedTicket, project_id: Optional[str] = None
    ) -> tuple[bool, str]:
        """Create a new ticket.

        Returns:
            Tuple of (success, message/error)
        """
        # Use full_body for rich AI context, fallback to description
        description_text = ticket.full_body if ticket.full_body else ticket.description
        payload = {
            "title": ticket.title,
            "description": description_text,
            "priority": ticket.priority,
            "phase_id": "PHASE_IMPLEMENTATION",  # Default phase
        }
        if project_id:
            payload["project_id"] = project_id

        status, data = await self._request("POST", "/api/v1/tickets", json=payload)

        if status in (200, 201):
            return True, f"Created with API ID: {data.get('id', 'unknown')}"
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return False, f"Failed to create: {error}"

    async def update_ticket_description(
        self, api_id: str, description: str
    ) -> tuple[bool, str]:
        """Update ticket description.

        Returns:
            Tuple of (success, message/error)
        """
        payload = {"description": description}
        status, data = await self._request(
            "PATCH", f"/api/v1/tickets/{api_id}", json=payload
        )

        if status == 200:
            return True, "Description updated"
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return False, f"Failed to update: {error}"

    async def list_tickets(self, project_id: Optional[str] = None) -> list[dict]:
        """List all tickets, optionally filtered by project."""
        endpoint = "/api/v1/tickets"
        if project_id:
            endpoint += f"?project_id={project_id}"

        status, data = await self._request("GET", endpoint)
        if status == 200 and isinstance(data, dict):
            return data.get("tickets", [])
        return []

    # ========================================================================
    # Task Operations
    # ========================================================================

    async def get_task(self, task_id: str) -> Optional[dict]:
        """Get task by ID."""
        status, data = await self._request("GET", f"/api/v1/tasks/{task_id}")
        if status == 200:
            return data
        return None

    async def create_task(
        self, task: ParsedTask, ticket_api_id: str
    ) -> tuple[bool, str]:
        """Create a new task.

        Returns:
            Tuple of (success, message/error)
        """
        # Convert dependencies to backend format
        dependencies = None
        if task.dependencies.depends_on:
            dependencies = {"depends_on": task.dependencies.depends_on}

        # Use full_body for rich AI context, fallback to objective
        description_text = task.full_body if task.full_body else task.objective
        payload = {
            "ticket_id": ticket_api_id,
            "title": task.title,
            "description": description_text,
            "task_type": "implementation",  # Default type
            "priority": "MEDIUM",  # Default priority
            "phase_id": "PHASE_IMPLEMENTATION",
        }
        if dependencies:
            payload["dependencies"] = dependencies

        status, data = await self._request("POST", "/api/v1/tasks", json=payload)

        if status in (200, 201):
            return True, f"Created with API ID: {data.get('id', 'unknown')}"
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return False, f"Failed to create: {error}"

    async def update_task_description(
        self, api_id: str, description: str
    ) -> tuple[bool, str]:
        """Update task description.

        Returns:
            Tuple of (success, message/error)
        """
        payload = {"description": description}
        status, data = await self._request(
            "PATCH", f"/api/v1/tasks/{api_id}", json=payload
        )

        if status == 200:
            return True, "Description updated"
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return False, f"Failed to update: {error}"

    async def list_tasks(self, ticket_id: Optional[str] = None) -> list[dict]:
        """List all tasks, optionally filtered by ticket."""
        endpoint = "/api/v1/tasks"
        # Note: The tasks endpoint doesn't have a ticket_id filter yet
        # We filter client-side for now
        status, data = await self._request("GET", endpoint)
        if status == 200 and isinstance(data, list):
            if ticket_id:
                return [t for t in data if t.get("ticket_id") == ticket_id]
            return data
        return []

    async def get_project_with_tickets(self, project_id: str) -> dict:
        """Get project details with all tickets and their tasks."""
        # Get project info
        status, project_data = await self._request(
            "GET", f"/api/v1/projects/{project_id}"
        )
        if status != 200:
            return {"error": f"Project not found: {project_id}"}

        # Get tickets for this project
        tickets = await self.list_tickets(project_id)

        # Get all tasks
        all_tasks = await self.list_tasks()

        # Group tasks by ticket
        tasks_by_ticket = {}
        for task in all_tasks:
            tid = task.get("ticket_id")
            if tid not in tasks_by_ticket:
                tasks_by_ticket[tid] = []
            tasks_by_ticket[tid].append(task)

        # Attach tasks to tickets
        for ticket in tickets:
            ticket["tasks"] = tasks_by_ticket.get(ticket["id"], [])

        return {
            "project": project_data,
            "tickets": tickets,
            "total_tickets": len(tickets),
            "total_tasks": len(all_tasks),
        }

    # ========================================================================
    # Project Operations
    # ========================================================================

    async def list_projects(self) -> list[dict]:
        """List all projects."""
        status, data = await self._request("GET", "/api/v1/projects")
        if status == 200 and isinstance(data, dict):
            return data.get("projects", [])
        return []

    # ========================================================================
    # Spec Operations
    # ========================================================================

    async def get_spec(self, spec_id: str) -> Optional[dict]:
        """Get spec by ID."""
        status, data = await self._request("GET", f"/api/v1/specs/{spec_id}")
        if status == 200:
            return data
        return None

    async def list_specs(self, project_id: str) -> list[dict]:
        """List all specs for a project."""
        status, data = await self._request("GET", f"/api/v1/specs/project/{project_id}")
        if status == 200 and isinstance(data, dict):
            return data.get("specs", [])
        return []

    async def create_spec(
        self,
        title: str,
        project_id: str,
        description: Optional[str] = None,
    ) -> tuple[bool, str, Optional[str]]:
        """Create a new spec.

        Returns:
            Tuple of (success, message/error, spec_id if created)
        """
        payload = {
            "title": title,
            "project_id": project_id,
        }
        if description:
            payload["description"] = description

        status, data = await self._request("POST", "/api/v1/specs", json=payload)

        if status in (200, 201) and data:
            spec_id = data.get("id")
            return True, f"Created spec with ID: {spec_id}", spec_id
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return False, f"Failed to create spec: {error}", None

    async def update_spec(
        self,
        spec_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Update a spec.

        Returns:
            Tuple of (success, message/error)
        """
        payload = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if status is not None:
            payload["status"] = status
        if phase is not None:
            payload["phase"] = phase

        resp_status, data = await self._request(
            "PATCH", f"/api/v1/specs/{spec_id}", json=payload
        )

        if resp_status == 200:
            return True, "Spec updated"
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {resp_status}"
            return False, f"Failed to update spec: {error}"

    # ========================================================================
    # Requirement Operations (EARS format)
    # ========================================================================

    async def add_requirement(
        self,
        spec_id: str,
        title: str,
        condition: str,
        action: str,
        linked_design: Optional[str] = None,
    ) -> tuple[bool, str, Optional[str]]:
        """Add a requirement to a spec using EARS format.

        EARS format:
        - condition: The "WHEN" clause (triggering condition)
        - action: The "THE SYSTEM SHALL" clause (expected behavior)

        Args:
            linked_design: Optional reference to a design section/ID

        Returns:
            Tuple of (success, message/error, requirement_id if created)
        """
        payload = {
            "title": title,
            "condition": condition,
            "action": action,
        }
        if linked_design:
            payload["linked_design"] = linked_design

        status, data = await self._request(
            "POST", f"/api/v1/specs/{spec_id}/requirements", json=payload
        )

        if status in (200, 201) and data:
            req_id = data.get("id")
            return True, f"Added requirement with ID: {req_id}", req_id
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return False, f"Failed to add requirement: {error}", None

    async def update_requirement(
        self,
        spec_id: str,
        req_id: str,
        title: Optional[str] = None,
        condition: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        linked_design: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Update a requirement.

        Args:
            linked_design: Optional reference to a design section/ID

        Returns:
            Tuple of (success, message/error)
        """
        payload = {}
        if title is not None:
            payload["title"] = title
        if condition is not None:
            payload["condition"] = condition
        if action is not None:
            payload["action"] = action
        if status is not None:
            payload["status"] = status
        if linked_design is not None:
            payload["linked_design"] = linked_design

        resp_status, data = await self._request(
            "PATCH", f"/api/v1/specs/{spec_id}/requirements/{req_id}", json=payload
        )

        if resp_status == 200:
            return True, "Requirement updated"
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {resp_status}"
            return False, f"Failed to update requirement: {error}"

    async def add_acceptance_criterion(
        self,
        spec_id: str,
        req_id: str,
        text: str,
    ) -> tuple[bool, str]:
        """Add an acceptance criterion to a requirement.

        Returns:
            Tuple of (success, message/error)
        """
        payload = {"text": text}

        status, data = await self._request(
            "POST",
            f"/api/v1/specs/{spec_id}/requirements/{req_id}/criteria",
            json=payload,
        )

        if status in (200, 201):
            return True, "Criterion added"
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return False, f"Failed to add criterion: {error}"

    # ========================================================================
    # Design Operations
    # ========================================================================

    async def update_design(
        self,
        spec_id: str,
        architecture: Optional[str] = None,
        data_model: Optional[str] = None,
        api_spec: Optional[list[dict]] = None,
    ) -> tuple[bool, str]:
        """Update a spec's design artifact.

        Args:
            spec_id: The spec ID
            architecture: Architecture description (markdown/mermaid)
            data_model: Data model description
            api_spec: List of API endpoints [{method, endpoint, description}]

        Returns:
            Tuple of (success, message/error)
        """
        payload = {}
        if architecture is not None:
            payload["architecture"] = architecture
        if data_model is not None:
            payload["data_model"] = data_model
        if api_spec is not None:
            payload["api_spec"] = api_spec

        status, data = await self._request(
            "PUT", f"/api/v1/specs/{spec_id}/design", json=payload
        )

        if status == 200:
            return True, "Design updated"
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return False, f"Failed to update design: {error}"

    # ========================================================================
    # Sync Specs from Local Files
    # ========================================================================

    async def sync_requirement_to_spec(
        self,
        spec_id: str,
        requirement: ParsedRequirement,
        existing_reqs: Optional[list[dict]] = None,
    ) -> SyncResult:
        """Sync a parsed requirement to an API spec.

        Args:
            spec_id: The spec ID to add/update requirement in
            requirement: Parsed requirement from local file
            existing_reqs: Optional list of existing requirements for comparison

        Returns:
            SyncResult indicating action taken
        """
        # Check if requirement already exists by title match
        existing = None
        if existing_reqs:
            for req in existing_reqs:
                if req.get("title") == requirement.title:
                    existing = req
                    break

        if existing:
            # Check if needs update (compare condition/action/linked_design)
            needs_update = (
                existing.get("condition", "").strip() != requirement.condition.strip()
                or existing.get("action", "").strip() != requirement.action.strip()
                or existing.get("linked_design") != requirement.linked_design
            )
            if needs_update:
                success, msg = await self.update_requirement(
                    spec_id,
                    existing["id"],
                    condition=requirement.condition,
                    action=requirement.action,
                    linked_design=requirement.linked_design,
                )
                return SyncResult(
                    item_id=requirement.id,
                    item_type="requirement",
                    action=SyncAction.UPDATED if success else SyncAction.FAILED,
                    message=msg,
                )
            else:
                return SyncResult(
                    item_id=requirement.id,
                    item_type="requirement",
                    action=SyncAction.SKIPPED,
                    message="Already exists with same content",
                )
        else:
            # Create new requirement
            success, msg, req_id = await self.add_requirement(
                spec_id,
                requirement.title,
                requirement.condition,
                requirement.action,
                requirement.linked_design,
            )

            result = SyncResult(
                item_id=requirement.id,
                item_type="requirement",
                action=SyncAction.CREATED if success else SyncAction.FAILED,
                message=msg,
            )

            # Add acceptance criteria if requirement was created
            if success and req_id and requirement.acceptance_criteria:
                for criterion in requirement.acceptance_criteria:
                    await self.add_acceptance_criterion(spec_id, req_id, criterion.text)

            return result

    async def sync_design_to_spec(
        self,
        spec_id: str,
        design: ParsedDesign,
        existing_design: Optional[dict] = None,
    ) -> SyncResult:
        """Sync a parsed design to an API spec.

        Args:
            spec_id: The spec ID to update design in
            design: Parsed design from local file
            existing_design: Optional existing design for comparison

        Returns:
            SyncResult indicating action taken
        """
        # Convert parsed API endpoints to API format (enhanced)
        api_spec = []
        for ep in design.api_endpoints:
            # Use to_api_dict() if available, otherwise build manually
            if hasattr(ep, "to_api_dict"):
                api_spec.append(ep.to_api_dict())
            else:
                api_spec.append(
                    {
                        "method": ep.method,
                        "endpoint": ep.path,
                        "description": ep.description,
                        "request_body": getattr(ep, "request_body", None),
                        "response": getattr(ep, "response", None),
                        "auth_required": getattr(ep, "auth_required", True),
                        "path_params": getattr(ep, "path_params", []),
                        "query_params": getattr(ep, "query_params", {}),
                        "error_responses": getattr(ep, "error_responses", {}),
                    }
                )

        # Build data model description from parsed data models (enhanced)
        data_model_parts = []
        for dm in design.data_models:
            # Use to_markdown() if available, otherwise build manually
            if hasattr(dm, "to_markdown"):
                data_model_parts.append(dm.to_markdown())
            else:
                model_desc = f"### {dm.name}\n{dm.description}\n\n"
                if dm.fields:
                    model_desc += "**Fields:**\n"
                    for field_name, field_type in dm.fields.items():
                        model_desc += f"- `{field_name}`: {field_type}\n"
                if dm.relationships:
                    model_desc += "\n**Relationships:**\n"
                    for rel in dm.relationships:
                        model_desc += f"- {rel}\n"
                data_model_parts.append(model_desc)

        data_model = "\n\n".join(data_model_parts) if data_model_parts else None

        # Check if needs update
        if existing_design:
            existing_arch = existing_design.get("architecture", "") or ""
            existing_dm = existing_design.get("data_model", "") or ""
            existing_api = existing_design.get("api_spec", []) or []
            new_arch = design.architecture or ""
            new_dm = data_model or ""

            # Compare architecture and data model text
            arch_same = existing_arch.strip() == new_arch.strip()
            dm_same = existing_dm.strip() == new_dm.strip()

            # Compare API spec (simplified comparison by length and methods)
            api_same = len(existing_api) == len(api_spec)
            if api_same and existing_api:
                existing_methods = {
                    (e.get("method"), e.get("endpoint")) for e in existing_api
                }
                new_methods = {(e.get("method"), e.get("endpoint")) for e in api_spec}
                api_same = existing_methods == new_methods

            if arch_same and dm_same and api_same:
                return SyncResult(
                    item_id=design.id,
                    item_type="design",
                    action=SyncAction.SKIPPED,
                    message="Already exists with same content",
                )

        # Update design
        success, msg = await self.update_design(
            spec_id,
            architecture=design.architecture,
            data_model=data_model,
            api_spec=api_spec if api_spec else None,
        )

        return SyncResult(
            item_id=design.id,
            item_type="design",
            action=SyncAction.UPDATED if success else SyncAction.FAILED,
            message=msg,
        )

    # ========================================================================
    # Auth Operations
    # ========================================================================

    async def login(self, email: str, password: str) -> tuple[bool, str]:
        """Login and store access token.

        Returns:
            Tuple of (success, message/error)
        """
        payload = {"email": email, "password": password}
        status, data = await self._request("POST", "/api/v1/auth/login", json=payload)

        if status == 200 and data:
            self.token = data.get("access_token")
            return True, "Login successful"
        else:
            error = data.get("detail", str(data)) if data else f"HTTP {status}"
            return False, f"Login failed: {error}"

    # ========================================================================
    # Sync Operations
    # ========================================================================

    async def check_connection(self) -> tuple[bool, str]:
        """Check if API is reachable.

        Returns:
            Tuple of (success, message)
        """
        try:
            status, _ = await self._request("GET", "/health")
            if status == 200:
                return True, "Connected"
            else:
                return False, f"API returned status {status}"
        except Exception as e:
            return False, str(e)

    async def sync(
        self,
        result: ParseResult,
        project_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> SyncSummary:
        """Sync local specs to API.

        Behavior:
        - CREATE: If ticket/task doesn't exist (by title match)
        - UPDATE: If exists but description differs
        - SKIP: If exists with same description

        Args:
            result: Parsed specs from SpecParser
            project_id: Optional project ID to associate tickets with
            dry_run: If True, don't actually make changes

        Returns:
            SyncSummary with results for each item
        """
        summary = SyncSummary(results=[])

        # Get existing items from API for comparison
        existing_tickets = await self.list_tickets(project_id)
        existing_tasks = await self.list_tasks()

        # Build lookup by title
        ticket_by_title = {t["title"]: t for t in existing_tickets}
        task_by_title = {t.get("title", ""): t for t in existing_tasks}

        # Track created ticket API IDs for task creation
        ticket_api_ids: dict[str, str] = {}

        # Sync tickets
        for ticket in result.tickets:
            existing = ticket_by_title.get(ticket.title)

            if existing:
                ticket_api_ids[ticket.id] = existing["id"]

                # Check if description needs update (use full_body for rich context)
                description_text = (
                    ticket.full_body if ticket.full_body else ticket.description
                )
                existing_desc = existing.get("description", "") or ""
                if existing_desc.strip() != description_text.strip():
                    if dry_run:
                        summary.add(
                            SyncResult(
                                item_id=ticket.id,
                                item_type="ticket",
                                action=SyncAction.UPDATED,
                                message="Would update description (dry run)",
                            )
                        )
                    else:
                        success, msg = await self.update_ticket_description(
                            existing["id"], description_text
                        )
                        summary.add(
                            SyncResult(
                                item_id=ticket.id,
                                item_type="ticket",
                                action=(
                                    SyncAction.UPDATED if success else SyncAction.FAILED
                                ),
                                message=msg,
                            )
                        )
                else:
                    summary.add(
                        SyncResult(
                            item_id=ticket.id,
                            item_type="ticket",
                            action=SyncAction.SKIPPED,
                            message="Already exists with same description",
                        )
                    )
            else:
                # Create new ticket
                if dry_run:
                    # Use placeholder ID for dry run so tasks can reference it
                    ticket_api_ids[ticket.id] = f"dry-run-{ticket.id}"
                    summary.add(
                        SyncResult(
                            item_id=ticket.id,
                            item_type="ticket",
                            action=SyncAction.CREATED,
                            message="Would create (dry run)",
                        )
                    )
                else:
                    success, msg = await self.create_ticket(ticket, project_id)
                    if success:
                        # Extract API ID from message
                        # Format: "Created with API ID: xxx"
                        match = re.search(r"API ID: (\S+)", msg)
                        if match:
                            ticket_api_ids[ticket.id] = match.group(1)
                    summary.add(
                        SyncResult(
                            item_id=ticket.id,
                            item_type="ticket",
                            action=SyncAction.CREATED if success else SyncAction.FAILED,
                            message=msg,
                        )
                    )

        # Sync tasks
        for task in result.tasks:
            existing = task_by_title.get(task.title)

            if existing:
                # Check if description needs update (use full_body for rich context)
                description_text = task.full_body if task.full_body else task.objective
                existing_desc = existing.get("description", "") or ""
                if existing_desc.strip() != description_text.strip():
                    if dry_run:
                        summary.add(
                            SyncResult(
                                item_id=task.id,
                                item_type="task",
                                action=SyncAction.UPDATED,
                                message="Would update description (dry run)",
                            )
                        )
                    else:
                        success, msg = await self.update_task_description(
                            existing["id"], description_text
                        )
                        summary.add(
                            SyncResult(
                                item_id=task.id,
                                item_type="task",
                                action=(
                                    SyncAction.UPDATED if success else SyncAction.FAILED
                                ),
                                message=msg,
                            )
                        )
                else:
                    summary.add(
                        SyncResult(
                            item_id=task.id,
                            item_type="task",
                            action=SyncAction.SKIPPED,
                            message="Already exists with same description",
                        )
                    )
            else:
                # Create new task - need parent ticket API ID
                ticket_api_id = ticket_api_ids.get(task.parent_ticket)
                if not ticket_api_id:
                    summary.add(
                        SyncResult(
                            item_id=task.id,
                            item_type="task",
                            action=SyncAction.FAILED,
                            message=f"Parent ticket {task.parent_ticket} not found in API",
                        )
                    )
                    continue

                if dry_run:
                    summary.add(
                        SyncResult(
                            item_id=task.id,
                            item_type="task",
                            action=SyncAction.CREATED,
                            message="Would create (dry run)",
                        )
                    )
                else:
                    success, msg = await self.create_task(task, ticket_api_id)
                    summary.add(
                        SyncResult(
                            item_id=task.id,
                            item_type="task",
                            action=SyncAction.CREATED if success else SyncAction.FAILED,
                            message=msg,
                        )
                    )

        return summary

    async def diff(
        self, result: ParseResult, project_id: Optional[str] = None
    ) -> SyncSummary:
        """Show what would change without making changes.

        This is equivalent to sync with dry_run=True.
        """
        return await self.sync(result, project_id, dry_run=True)

    async def sync_specs(
        self,
        result: ParseResult,
        project_id: str,
        spec_title: Optional[str] = None,
        dry_run: bool = False,
    ) -> SyncSummary:
        """Sync local requirements and designs to API specs.

        This creates/updates a spec document in the API with requirements
        and design artifacts parsed from local .omoi_os/ files.

        Workflow:
        1. Find or create spec by title (defaults to first design's title)
        2. Sync all requirements to the spec
        3. Sync all designs to the spec

        Args:
            result: Parsed specs from SpecParser
            project_id: Project ID to associate spec with
            spec_title: Optional spec title (defaults to design feature name)
            dry_run: If True, don't actually make changes

        Returns:
            SyncSummary with results for each item
        """
        summary = SyncSummary(results=[])

        # Determine spec title
        if not spec_title:
            if result.designs:
                spec_title = result.designs[0].title or result.designs[0].feature
            elif result.requirements:
                spec_title = f"Spec for {result.requirements[0].title}"
            else:
                summary.add(
                    SyncResult(
                        item_id="unknown",
                        item_type="spec",
                        action=SyncAction.FAILED,
                        message="No requirements or designs found to sync",
                    )
                )
                return summary

        # Get existing specs for this project
        existing_specs = await self.list_specs(project_id)
        spec_by_title = {s["title"]: s for s in existing_specs}

        # Find or create spec
        spec_id = None
        if spec_title in spec_by_title:
            spec_id = spec_by_title[spec_title]["id"]
            existing_spec = spec_by_title[spec_title]
            summary.add(
                SyncResult(
                    item_id=spec_id,
                    item_type="spec",
                    action=SyncAction.SKIPPED,
                    message=f"Using existing spec: {spec_title}",
                )
            )
        else:
            if dry_run:
                spec_id = f"dry-run-spec-{spec_title}"
                summary.add(
                    SyncResult(
                        item_id=spec_id,
                        item_type="spec",
                        action=SyncAction.CREATED,
                        message=f"Would create spec: {spec_title} (dry run)",
                    )
                )
                existing_spec = {"requirements": [], "design": None}
            else:
                # Build description from requirements
                description = ""
                if result.requirements:
                    description = f"Requirements ({len(result.requirements)}): "
                    description += ", ".join(r.title for r in result.requirements[:3])
                    if len(result.requirements) > 3:
                        description += f" and {len(result.requirements) - 3} more"

                success, msg, created_id = await self.create_spec(
                    title=spec_title,
                    project_id=project_id,
                    description=description,
                )
                if success and created_id:
                    spec_id = created_id
                    summary.add(
                        SyncResult(
                            item_id=spec_id,
                            item_type="spec",
                            action=SyncAction.CREATED,
                            message=msg,
                        )
                    )
                    existing_spec = {"requirements": [], "design": None}
                else:
                    summary.add(
                        SyncResult(
                            item_id="unknown",
                            item_type="spec",
                            action=SyncAction.FAILED,
                            message=msg,
                        )
                    )
                    return summary

        # Sync requirements
        if spec_id and not dry_run:
            existing_reqs = existing_spec.get("requirements", [])

            for requirement in result.requirements:
                req_result = await self.sync_requirement_to_spec(
                    spec_id,
                    requirement,
                    existing_reqs,
                )
                summary.add(req_result)
        elif dry_run:
            for requirement in result.requirements:
                summary.add(
                    SyncResult(
                        item_id=requirement.id,
                        item_type="requirement",
                        action=SyncAction.CREATED,
                        message=f"Would create requirement: {requirement.title} (dry run)",
                    )
                )

        # Sync designs
        if spec_id and not dry_run:
            existing_design = existing_spec.get("design")

            for design in result.designs:
                design_result = await self.sync_design_to_spec(
                    spec_id,
                    design,
                    existing_design,
                )
                summary.add(design_result)
        elif dry_run:
            for design in result.designs:
                summary.add(
                    SyncResult(
                        item_id=design.id,
                        item_type="design",
                        action=SyncAction.UPDATED,
                        message=f"Would update design: {design.title} (dry run)",
                    )
                )

        return summary

    async def diff_specs(
        self,
        result: ParseResult,
        project_id: str,
        spec_title: Optional[str] = None,
    ) -> SyncSummary:
        """Show what spec changes would happen without making changes.

        This is equivalent to sync_specs with dry_run=True.
        """
        return await self.sync_specs(result, project_id, spec_title, dry_run=True)

    async def get_full_traceability(
        self,
        project_id: str,
    ) -> dict:
        """Get full traceability from API: Specs → Requirements → Tickets → Tasks.

        Returns:
            Dict with:
            - specs: List of specs with requirements
            - tickets: List of tickets with tasks
            - traceability: Mapping of spec requirements to tickets
        """
        # Get all specs for the project
        specs = await self.list_specs(project_id)

        # Get all tickets for the project
        tickets = await self.list_tickets(project_id)

        # Get all tasks
        all_tasks = await self.list_tasks()

        # Group tasks by ticket
        tasks_by_ticket = {}
        for task in all_tasks:
            tid = task.get("ticket_id")
            if tid not in tasks_by_ticket:
                tasks_by_ticket[tid] = []
            tasks_by_ticket[tid].append(task)

        # Build traceability matrix
        traceability = {
            "specs": [],
            "tickets": [],
            "orphan_tickets": [],  # Tickets not linked to any spec requirement
        }

        # Process specs
        for spec in specs:
            spec_entry = {
                "id": spec["id"],
                "title": spec["title"],
                "status": spec["status"],
                "requirements": [],
                "linked_tickets": [],
            }

            for req in spec.get("requirements", []):
                req_entry = {
                    "id": req["id"],
                    "title": req["title"],
                    "condition": req.get("condition", ""),
                    "action": req.get("action", ""),
                    "status": req.get("status", "pending"),
                    "linked_tickets": [],
                }

                # Find tickets that might implement this requirement
                # (This would require ticket.requirements field - checking by title match for now)
                for ticket in tickets:
                    ticket_title_lower = ticket.get("title", "").lower()
                    req_title_lower = req["title"].lower()

                    # Simple heuristic: ticket title contains requirement keywords
                    if any(
                        word in ticket_title_lower for word in req_title_lower.split()
                    ):
                        req_entry["linked_tickets"].append(ticket["id"])
                        spec_entry["linked_tickets"].append(ticket["id"])

                spec_entry["requirements"].append(req_entry)

            traceability["specs"].append(spec_entry)

        # Process tickets
        linked_ticket_ids = set()
        for spec in traceability["specs"]:
            linked_ticket_ids.update(spec["linked_tickets"])

        for ticket in tickets:
            ticket_entry = {
                "id": ticket["id"],
                "title": ticket["title"],
                "status": ticket.get("status", "unknown"),
                "priority": ticket.get("priority", "MEDIUM"),
                "tasks": tasks_by_ticket.get(ticket["id"], []),
            }

            if ticket["id"] in linked_ticket_ids:
                traceability["tickets"].append(ticket_entry)
            else:
                traceability["orphan_tickets"].append(ticket_entry)

        return traceability


# ============================================================================
# CLI Integration
# ============================================================================


def print_sync_summary(summary: SyncSummary):
    """Print sync summary to console."""
    print("\nSync Results:")
    print("-" * 60)

    for result in summary.results:
        action_str = {
            SyncAction.CREATED: "[CREATE]",
            SyncAction.UPDATED: "[UPDATE]",
            SyncAction.SKIPPED: "[SKIP]  ",
            SyncAction.FAILED: "[FAILED]",
        }[result.action]

        print(f"{action_str} {result.item_type} {result.item_id}")
        if result.message:
            print(f"         {result.message}")

    print("-" * 60)
    print(
        f"Summary: {summary.created} created, {summary.updated} updated, "
        f"{summary.skipped} skipped, {summary.failed} failed"
    )


async def run_sync(
    api_url: str,
    action: str,
    project_id: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None,
    api_key: Optional[str] = None,
):
    """Run sync from CLI."""
    import os
    from parse_specs import SpecParser

    # Auth can come from: argument > env var
    auth_token = token or os.environ.get("OMOIOS_TOKEN")
    auth_api_key = api_key or os.environ.get("OMOIOS_API_KEY")

    client = OmoiOSClient(base_url=api_url, token=auth_token, api_key=auth_api_key)
    parser = SpecParser()

    # Check connection
    print(f"Connecting to {api_url}...")
    connected, msg = await client.check_connection()
    if not connected:
        print(f"Error: Cannot connect to API: {msg}")
        return False

    print("Connected!")

    # Handle authentication
    if client.api_key:
        print("Using API key authentication.\n")
    elif client.token:
        print("Using provided token.\n")
    else:
        # Try to login if credentials provided
        if email and password:
            print(f"Logging in as {email}...")
            success, msg = await client.login(email, password)
            if not success:
                print(f"Error: {msg}")
                return False
            print("Authenticated!\n")
        else:
            # Try env vars for credentials
            env_email = os.environ.get("OMOIOS_EMAIL")
            env_password = os.environ.get("OMOIOS_PASSWORD")
            if env_email and env_password:
                print(f"Logging in as {env_email}...")
                success, msg = await client.login(env_email, env_password)
                if not success:
                    print(f"Error: {msg}")
                    return False
                print("Authenticated!\n")
            else:
                print("Warning: No authentication provided. API calls may fail.")
                print(
                    "Set OMOIOS_API_KEY, OMOIOS_TOKEN, or OMOIOS_EMAIL/OMOIOS_PASSWORD env vars.\n"
                )

    # Parse specs
    result = parser.parse_all()
    print(f"Parsed {len(result.tickets)} tickets and {len(result.tasks)} tasks\n")

    # Run validation first
    from spec_cli import validate_specs

    errors = validate_specs(result)
    if errors:
        print("Validation failed! Fix these errors before syncing:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("Validation passed!\n")

    # Run sync
    try:
        if action == "diff":
            print("Checking what would change (dry run)...")
            summary = await client.diff(result, project_id)
        else:  # push
            print("Syncing to API...")
            summary = await client.sync(result, project_id)

        print_sync_summary(summary)
        return summary.failed == 0
    finally:
        # Clean up client connection
        await client.close()


if __name__ == "__main__":
    # Quick test
    async def test():
        client = OmoiOSClient()
        connected, msg = await client.check_connection()
        print(f"Connection test: {msg}")

    asyncio.run(test())
