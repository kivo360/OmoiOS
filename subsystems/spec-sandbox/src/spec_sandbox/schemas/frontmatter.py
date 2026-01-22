"""Frontmatter schemas for markdown files.

These Pydantic models define the structure of YAML frontmatter
in generated markdown files. They enable validation and provide
a clear contract for the sync-to-API workflow.
"""

from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Priority(str, Enum):
    """Priority levels for tickets and tasks."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Status(str, Enum):
    """Status values for artifacts."""

    # Document statuses
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"

    # Work item statuses
    BACKLOG = "backlog"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class Estimate(str, Enum):
    """T-shirt size estimates."""

    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"


class TaskType(str, Enum):
    """Types of tasks."""

    IMPLEMENTATION = "implementation"
    TEST = "test"
    RESEARCH = "research"
    DOCUMENTATION = "documentation"
    INFRASTRUCTURE = "infrastructure"
    REFACTOR = "refactor"


class Dependencies(BaseModel):
    """Dependency tracking for tickets and tasks."""

    blocked_by: List[str] = Field(default_factory=list)
    blocks: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)


class TicketFrontmatter(BaseModel):
    """Frontmatter schema for ticket markdown files.

    Example:
        ---
        id: TKT-001
        title: Implement user authentication
        created: 2025-01-16
        status: backlog
        priority: HIGH
        estimate: M
        requirements:
          - REQ-AUTH-001
        ---
    """

    id: str = Field(..., pattern=r"^TKT-\d{3}$", description="Ticket ID (TKT-NNN format)")
    title: str = Field(..., min_length=1, max_length=200)
    created: date
    updated: Optional[date] = None
    status: Status = Status.BACKLOG
    priority: Priority = Priority.MEDIUM
    estimate: Estimate = Estimate.M
    assignee: Optional[str] = None
    design_ref: Optional[str] = Field(
        default=None,
        description="Reference to design document (e.g., designs/auth.md)",
    )
    requirements: List[str] = Field(
        default_factory=list,
        description="List of requirement IDs this ticket addresses",
    )
    dependencies: Dependencies = Field(default_factory=Dependencies)
    labels: List[str] = Field(default_factory=list)

    def to_api_payload(
        self,
        project_id: str,
        spec_id: Optional[str] = None,
        phase_id: str = "PHASE_IMPLEMENTATION",
        status: str = "building",
    ) -> Dict[str, Any]:
        """Convert frontmatter to API payload for ticket creation.

        Args:
            project_id: The project ID to create the ticket in
            spec_id: Optional spec ID for context
            phase_id: Phase ID for the ticket (default: PHASE_IMPLEMENTATION)
                     Using PHASE_IMPLEMENTATION ensures:
                     1. Tasks run in continuous mode (auto-enabled)
                     2. Tasks run to completion with PR creation
                     3. Tickets appear in "doing" category for immediate work
            status: Ticket status (default: "building")
                   Using "building" puts tickets in the active work queue

        Returns:
            Dict ready for POST /api/v1/tickets
        """
        payload = {
            "title": self.title,
            "priority": self.priority.value,
            "project_id": project_id,
            "phase_id": phase_id,  # Set to IMPLEMENTATION for continuous mode
            "status": status,       # Set to building for immediate execution
            "context": {
                "local_id": self.id,
                "requirements": self.requirements,
                "source": "spec_sandbox",
            },
        }

        if spec_id:
            payload["context"]["spec_id"] = spec_id

        if self.design_ref:
            payload["context"]["design_ref"] = self.design_ref

        return payload


class TaskFrontmatter(BaseModel):
    """Frontmatter schema for task markdown files.

    Example:
        ---
        id: TSK-001
        title: Create database schema
        created: 2025-01-16
        status: pending
        parent_ticket: TKT-001
        type: implementation
        estimate: S
        ---
    """

    id: str = Field(..., pattern=r"^TSK-\d{3}$", description="Task ID (TSK-NNN format)")
    title: str = Field(..., min_length=1, max_length=200)
    created: date
    updated: Optional[date] = None
    status: Status = Status.PENDING
    priority: Priority = Priority.MEDIUM
    estimate: Estimate = Estimate.S
    assignee: Optional[str] = None
    parent_ticket: str = Field(
        ...,
        pattern=r"^TKT-\d{3}$",
        description="Parent ticket ID (TKT-NNN format)",
    )
    type: TaskType = TaskType.IMPLEMENTATION
    files_to_modify: List[str] = Field(
        default_factory=list,
        description="List of file paths this task will modify",
    )
    dependencies: Dependencies = Field(default_factory=Dependencies)

    def to_api_payload(
        self,
        ticket_api_id: str,
        description: str = "",
        phase_id: str = "PHASE_IMPLEMENTATION",
    ) -> Dict[str, Any]:
        """Convert frontmatter to API payload for task creation.

        Args:
            ticket_api_id: The API ID of the parent ticket
            description: Task description (body content from markdown)
            phase_id: Phase ID for the task (default: PHASE_IMPLEMENTATION)
                     Using PHASE_IMPLEMENTATION ensures:
                     1. Tasks run in continuous mode (auto-enabled)
                     2. Tasks run to completion with PR creation
                     3. Tasks get execution_mode="implementation"

        Returns:
            Dict ready for POST /api/v1/tasks
        """
        # Map TaskType to task_type that ensures implementation mode
        # Using "implement_feature" ensures the task is analyzed as implementation mode
        # and gets continuous mode enabled
        task_type_map = {
            TaskType.IMPLEMENTATION: "implement_feature",
            TaskType.TEST: "write_tests",
            TaskType.RESEARCH: "implement_feature",  # Changed from analyze_requirements
            TaskType.DOCUMENTATION: "implement_feature",  # Changed from analyze_requirements
            TaskType.INFRASTRUCTURE: "implement_feature",
            TaskType.REFACTOR: "implement_feature",
        }
        task_type = task_type_map.get(self.type, "implement_feature")

        payload = {
            "ticket_id": ticket_api_id,
            "title": self.title,
            "description": description,
            "task_type": task_type,
            "priority": self.priority.value,
            "phase_id": phase_id,
        }

        if self.dependencies.depends_on:
            payload["dependencies"] = {"depends_on": self.dependencies.depends_on}

        return payload


class RequirementFrontmatter(BaseModel):
    """Frontmatter schema for requirement markdown files.

    Example:
        ---
        id: REQ-AUTH-001
        title: User login with email
        created: 2025-01-16
        status: approved
        priority: HIGH
        category: functional
        ---
    """

    id: str = Field(
        ...,
        pattern=r"^REQ-[A-Z]+-\d{3}$",
        description="Requirement ID (REQ-FEATURE-NNN format)",
    )
    title: str = Field(..., min_length=1, max_length=200)
    created: date
    updated: Optional[date] = None
    status: Status = Status.DRAFT
    priority: Priority = Priority.MEDIUM
    category: str = Field(
        default="functional",
        description="Category: functional, non-functional, constraint",
    )
    prd_ref: Optional[str] = Field(
        default=None,
        description="Reference to PRD document",
    )
    stakeholder: Optional[str] = None
    verification_method: str = Field(
        default="test",
        description="How to verify: test, inspection, demonstration, analysis",
    )
    acceptance_criteria: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: Dependencies = Field(default_factory=Dependencies)


class DesignFrontmatter(BaseModel):
    """Frontmatter schema for design markdown files.

    Example:
        ---
        id: DES-AUTH-001
        title: Authentication System Design
        created: 2025-01-16
        status: review
        type: architecture
        requirements:
          - REQ-AUTH-001
        ---
    """

    id: str = Field(
        ...,
        pattern=r"^DES-[A-Z]+-\d{3}$",
        description="Design ID (DES-FEATURE-NNN format)",
    )
    title: str = Field(..., min_length=1, max_length=200)
    created: date
    updated: Optional[date] = None
    status: Status = Status.DRAFT
    type: str = Field(
        default="architecture",
        description="Type: architecture, data_model, api, sequence, component",
    )
    requirements: List[str] = Field(
        default_factory=list,
        description="List of requirement IDs this design addresses",
    )
    components: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of components with name and type",
    )
    technologies: List[str] = Field(default_factory=list)
    risks: List[Dict[str, str]] = Field(default_factory=list)
