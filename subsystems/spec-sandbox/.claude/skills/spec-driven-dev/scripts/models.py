"""
Data models for parsed spec files.

These dataclasses represent the structured data extracted from
.omoi_os/ markdown files with YAML frontmatter.

Supports:
- Requirements (.omoi_os/requirements/*.md)
- Designs (.omoi_os/designs/*.md)
- Tickets (.omoi_os/tickets/*.md)
- Tasks (.omoi_os/tasks/*.md)
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


# ============================================================================
# Requirement Models
# ============================================================================


@dataclass
class AcceptanceCriterion:
    """Single acceptance criterion for a requirement."""

    text: str
    completed: bool = False


@dataclass
class ParsedRequirement:
    """Parsed requirement from .omoi_os/requirements/*.md

    Uses EARS format (Easy Approach to Requirements Syntax):
    - condition: The "WHEN" clause (triggering condition)
    - action: The "THE SYSTEM SHALL" clause (expected behavior)
    """

    id: str  # REQ-XXX-YYY-NNN format
    title: str
    status: str  # draft, review, approved
    created: date
    updated: date
    category: str = ""  # functional, non-functional, constraint
    priority: str = "MEDIUM"
    condition: str = ""  # EARS "WHEN" clause
    action: str = ""  # EARS "THE SYSTEM SHALL" clause
    rationale: str = ""  # Why this requirement exists
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    linked_tickets: list[str] = field(default_factory=list)  # TKT-XXX references
    linked_design: Optional[str] = None  # Design section reference
    file_path: str = ""

    def __str__(self) -> str:
        return f"{self.id}: {self.title}"


# ============================================================================
# Design Models
# ============================================================================


@dataclass
class ApiEndpoint:
    """API endpoint specification.

    Enhanced to support richer API documentation including:
    - Request/response schemas
    - Authentication requirements
    - Path parameters
    - Query parameters
    - Error responses
    """

    method: str  # GET, POST, PUT, DELETE, PATCH
    path: str  # /api/v1/resource
    description: str = ""
    request_body: Optional[str] = None  # JSON schema or description
    response: Optional[str] = None  # JSON schema or description
    auth_required: bool = True  # Whether authentication is required
    path_params: list[str] = field(default_factory=list)  # e.g., ["id", "project_id"]
    query_params: dict[str, str] = field(default_factory=dict)  # param_name -> description
    error_responses: dict[str, str] = field(default_factory=dict)  # status_code -> description

    def to_api_dict(self) -> dict:
        """Convert to API sync format."""
        return {
            "method": self.method,
            "endpoint": self.path,
            "description": self.description,
            "request_body": self.request_body,
            "response": self.response,
            "auth_required": self.auth_required,
            "path_params": self.path_params,
            "query_params": self.query_params,
            "error_responses": self.error_responses,
        }


@dataclass
class DataModelField:
    """A single field in a data model."""

    name: str
    type: str  # e.g., "string", "uuid", "timestamp", "int", "boolean", "jsonb"
    description: str = ""
    nullable: bool = False
    default: Optional[str] = None
    constraints: list[str] = field(default_factory=list)  # e.g., ["unique", "indexed"]


@dataclass
class DataModel:
    """Data model/entity specification.

    Enhanced to support richer data model documentation including:
    - Typed fields with constraints
    - Table names
    - Relationships with cardinality
    """

    name: str
    description: str = ""
    fields: dict[str, str] = field(default_factory=dict)  # Legacy: field_name -> type/description
    typed_fields: list[DataModelField] = field(default_factory=list)  # Enhanced field specs
    relationships: list[str] = field(default_factory=list)
    table_name: Optional[str] = None  # Database table name if different from model name

    def to_markdown(self) -> str:
        """Convert to markdown representation for data_model sync."""
        parts = [f"### {self.name}"]
        if self.description:
            parts.append(self.description)
        parts.append("")

        # Use typed_fields if available, otherwise fall back to legacy fields
        if self.typed_fields:
            parts.append("**Fields:**")
            for f in self.typed_fields:
                nullable_str = " (nullable)" if f.nullable else ""
                default_str = f" = {f.default}" if f.default else ""
                constraints_str = f" [{', '.join(f.constraints)}]" if f.constraints else ""
                desc_str = f" - {f.description}" if f.description else ""
                parts.append(f"- `{f.name}`: {f.type}{nullable_str}{default_str}{constraints_str}{desc_str}")
        elif self.fields:
            parts.append("**Fields:**")
            for field_name, field_type in self.fields.items():
                parts.append(f"- `{field_name}`: {field_type}")

        if self.relationships:
            parts.append("")
            parts.append("**Relationships:**")
            for rel in self.relationships:
                parts.append(f"- {rel}")

        return "\n".join(parts)


@dataclass
class ParsedDesign:
    """Parsed design from .omoi_os/designs/*.md"""

    id: str  # Design identifier
    title: str
    status: str  # draft, review, approved
    created: date
    updated: date
    feature: str = ""  # Feature this design covers
    requirements: list[str] = field(default_factory=list)  # REQ-XXX references
    architecture: str = ""  # Architecture description/diagram
    data_models: list[DataModel] = field(default_factory=list)
    api_endpoints: list[ApiEndpoint] = field(default_factory=list)
    components: list[str] = field(default_factory=list)  # Key components
    error_handling: str = ""
    security_considerations: str = ""
    implementation_notes: str = ""
    file_path: str = ""

    def __str__(self) -> str:
        return f"{self.id}: {self.title}"


# ============================================================================
# Ticket/Task Dependency Models
# ============================================================================


@dataclass
class TicketDependencies:
    """Dependencies for a ticket."""

    blocked_by: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)


@dataclass
class TaskDependencies:
    """Dependencies for a task."""

    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)


@dataclass
class ParsedTicket:
    """Parsed ticket from .omoi_os/tickets/*.md"""

    id: str
    title: str
    status: str
    priority: str
    estimate: str
    created: date
    updated: date
    feature: Optional[str] = None
    requirements: list[str] = field(default_factory=list)
    design_ref: Optional[str] = None
    tasks: list[str] = field(default_factory=list)
    dependencies: TicketDependencies = field(default_factory=TicketDependencies)
    description: str = ""  # Short summary/description
    full_body: str = ""    # Full markdown body with all sections (for AI context)
    file_path: str = ""

    def is_blocked(self) -> bool:
        """Check if this ticket is blocked by other tickets."""
        return len(self.dependencies.blocked_by) > 0

    def __str__(self) -> str:
        return f"{self.id}: {self.title}"


@dataclass
class ParsedTask:
    """Parsed task from .omoi_os/tasks/*.md"""

    id: str
    title: str
    status: str
    parent_ticket: str
    estimate: str
    created: date
    assignee: Optional[str] = None
    dependencies: TaskDependencies = field(default_factory=TaskDependencies)
    objective: str = ""    # Short objective/description
    full_body: str = ""    # Full markdown body with all sections (for AI context)
    file_path: str = ""

    def is_blocked(self, completed_tasks: set[str]) -> bool:
        """Check if this task is blocked by incomplete tasks."""
        for dep in self.dependencies.depends_on:
            if dep not in completed_tasks:
                return True
        return False

    def is_ready(self, completed_tasks: set[str]) -> bool:
        """Check if this task is ready to work on."""
        return self.status == "pending" and not self.is_blocked(completed_tasks)

    def __str__(self) -> str:
        return f"{self.id}: {self.title}"


@dataclass
class ValidationError:
    """Validation error found in specs."""

    error_type: str  # circular_dependency, missing_reference, etc.
    message: str
    source_id: str
    target_id: Optional[str] = None

    def __str__(self) -> str:
        if self.target_id:
            return f"[{self.error_type}] {self.source_id} -> {self.target_id}: {self.message}"
        return f"[{self.error_type}] {self.source_id}: {self.message}"


@dataclass
class ParseResult:
    """Result of parsing all spec files."""

    requirements: list[ParsedRequirement] = field(default_factory=list)
    designs: list[ParsedDesign] = field(default_factory=list)
    tickets: list[ParsedTicket] = field(default_factory=list)
    tasks: list[ParsedTask] = field(default_factory=list)
    errors: list[ValidationError] = field(default_factory=list)

    # ========================================================================
    # Requirement Methods
    # ========================================================================

    def get_requirement(self, req_id: str) -> Optional[ParsedRequirement]:
        """Get requirement by ID."""
        for req in self.requirements:
            if req.id == req_id:
                return req
        return None

    def get_requirements_by_category(self, category: str) -> list[ParsedRequirement]:
        """Get all requirements in a category."""
        return [r for r in self.requirements if r.category == category]

    def get_requirements_by_status(self, status: str) -> list[ParsedRequirement]:
        """Get all requirements with a given status."""
        return [r for r in self.requirements if r.status == status]

    # ========================================================================
    # Design Methods
    # ========================================================================

    def get_design(self, design_id: str) -> Optional[ParsedDesign]:
        """Get design by ID."""
        for design in self.designs:
            if design.id == design_id:
                return design
        return None

    def get_design_for_feature(self, feature: str) -> Optional[ParsedDesign]:
        """Get design for a feature."""
        for design in self.designs:
            if design.feature == feature:
                return design
        return None

    # ========================================================================
    # Ticket Methods
    # ========================================================================

    def get_ticket(self, ticket_id: str) -> Optional[ParsedTicket]:
        """Get ticket by ID."""
        for ticket in self.tickets:
            if ticket.id == ticket_id:
                return ticket
        return None

    def get_task(self, task_id: str) -> Optional[ParsedTask]:
        """Get task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_tasks_for_ticket(self, ticket_id: str) -> list[ParsedTask]:
        """Get all tasks belonging to a ticket."""
        return [t for t in self.tasks if t.parent_ticket == ticket_id]

    def get_completed_tasks(self) -> set[str]:
        """Get set of completed task IDs."""
        return {t.id for t in self.tasks if t.status == "done"}

    def get_completed_tickets(self) -> set[str]:
        """Get set of ticket IDs where all tasks are complete."""
        completed_tickets = set()
        for ticket in self.tickets:
            tasks = self.get_tasks_for_ticket(ticket.id)
            if tasks and all(t.status == "done" for t in tasks):
                completed_tickets.add(ticket.id)
            elif not tasks and ticket.status == "done":
                # Ticket with no tasks is complete if status is done
                completed_tickets.add(ticket.id)
        return completed_tickets

    def get_blocking_tickets(self, ticket_id: str) -> list[str]:
        """Get list of ticket IDs that block a given ticket (transitively).

        Uses BFS to find all tickets that must complete before this ticket.
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return []

        blocking = []
        visited = set()
        queue = list(ticket.dependencies.blocked_by)

        while queue:
            blocker_id = queue.pop(0)
            if blocker_id in visited:
                continue
            visited.add(blocker_id)
            blocking.append(blocker_id)

            # Check transitive dependencies
            blocker = self.get_ticket(blocker_id)
            if blocker:
                for transitive in blocker.dependencies.blocked_by:
                    if transitive not in visited:
                        queue.append(transitive)

        return blocking

    def is_task_blocked_by_tickets(self, task: ParsedTask) -> tuple[bool, list[str]]:
        """Check if a task is blocked by incomplete tickets its parent depends on.

        Returns:
            Tuple of (is_blocked, list of blocking ticket IDs)
        """
        parent_ticket = self.get_ticket(task.parent_ticket)
        if not parent_ticket:
            return False, []

        blocking_tickets = self.get_blocking_tickets(task.parent_ticket)
        if not blocking_tickets:
            return False, []

        completed_tickets = self.get_completed_tickets()
        incomplete_blockers = [t for t in blocking_tickets if t not in completed_tickets]

        return len(incomplete_blockers) > 0, incomplete_blockers

    def is_task_blocked(self, task: ParsedTask, completed_tasks: Optional[set[str]] = None) -> tuple[bool, str]:
        """Check if a task is blocked, considering both task and ticket dependencies.

        Returns:
            Tuple of (is_blocked, reason)
        """
        if completed_tasks is None:
            completed_tasks = self.get_completed_tasks()

        # Check direct task dependencies first
        for dep in task.dependencies.depends_on:
            if dep not in completed_tasks:
                return True, f"blocked by task {dep}"

        # Check cross-ticket dependencies
        is_blocked, blocking_tickets = self.is_task_blocked_by_tickets(task)
        if is_blocked:
            return True, f"blocked by ticket(s): {', '.join(blocking_tickets)}"

        return False, ""

    def get_ready_tasks(self) -> list[ParsedTask]:
        """Get tasks that are ready to work on (no blocking dependencies).

        Considers both:
        - Direct task dependencies (depends_on)
        - Cross-ticket dependencies (parent ticket blocked_by)
        """
        completed = self.get_completed_tasks()
        ready = []

        for task in self.tasks:
            if task.status != "pending":
                continue

            is_blocked, _ = self.is_task_blocked(task, completed)
            if not is_blocked:
                ready.append(task)

        return ready

    def get_cross_ticket_dependency_graph(self) -> dict[str, list[str]]:
        """Build a graph of ticket dependencies.

        Returns:
            Dict mapping ticket_id -> list of ticket_ids it blocks
        """
        graph = {t.id: [] for t in self.tickets}

        for ticket in self.tickets:
            for blocker_id in ticket.dependencies.blocked_by:
                if blocker_id in graph:
                    graph[blocker_id].append(ticket.id)

        return graph

    def is_valid(self) -> bool:
        """Check if there are no validation errors."""
        return len(self.errors) == 0

    # ========================================================================
    # Traceability Methods
    # ========================================================================

    def get_tickets_for_requirement(self, req_id: str) -> list[ParsedTicket]:
        """Get all tickets implementing a requirement."""
        return [t for t in self.tickets if req_id in t.requirements]

    def get_design_for_ticket(self, ticket_id: str) -> Optional[ParsedDesign]:
        """Get the design document for a ticket."""
        ticket = self.get_ticket(ticket_id)
        if not ticket or not ticket.design_ref:
            return None
        # design_ref is like "designs/feature-name.md"
        # Find design by matching feature
        for design in self.designs:
            if ticket.design_ref.endswith(f"{design.feature}.md"):
                return design
            if design.id == ticket.design_ref:
                return design
        return None

    def get_requirements_for_ticket(self, ticket_id: str) -> list[ParsedRequirement]:
        """Get all requirements a ticket implements."""
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return []
        return [r for r in self.requirements if r.id in ticket.requirements]

    def get_full_traceability(self) -> dict:
        """Build complete traceability matrix.

        Returns dict with:
        - requirements: REQ-ID -> {requirement, designs, tickets, tasks}
        - designs: DESIGN-ID -> {design, requirements, tickets}
        - tickets: TKT-ID -> {ticket, requirements, design, tasks}
        - orphans: items without proper links
        """
        trace = {
            "requirements": {},
            "designs": {},
            "tickets": {},
            "orphans": {
                "requirements": [],  # Requirements not linked to any ticket
                "designs": [],  # Designs not linked to any ticket
                "tickets": [],  # Tickets not linked to requirements
            },
        }

        # Build requirement traceability
        for req in self.requirements:
            tickets = self.get_tickets_for_requirement(req.id)
            tasks = []
            for ticket in tickets:
                tasks.extend(self.get_tasks_for_ticket(ticket.id))

            trace["requirements"][req.id] = {
                "requirement": req,
                "linked_design": req.linked_design,
                "tickets": [t.id for t in tickets],
                "tasks": [t.id for t in tasks],
            }

            if not tickets:
                trace["orphans"]["requirements"].append(req.id)

        # Build design traceability
        for design in self.designs:
            linked_tickets = [
                t for t in self.tickets
                if t.design_ref and (
                    t.design_ref.endswith(f"{design.feature}.md")
                    or t.design_ref == design.id
                )
            ]

            trace["designs"][design.id] = {
                "design": design,
                "requirements": design.requirements,
                "tickets": [t.id for t in linked_tickets],
            }

            if not linked_tickets:
                trace["orphans"]["designs"].append(design.id)

        # Build ticket traceability
        for ticket in self.tickets:
            reqs = self.get_requirements_for_ticket(ticket.id)
            design = self.get_design_for_ticket(ticket.id)
            tasks = self.get_tasks_for_ticket(ticket.id)

            trace["tickets"][ticket.id] = {
                "ticket": ticket,
                "requirements": [r.id for r in reqs],
                "design": design.id if design else None,
                "tasks": [t.id for t in tasks],
                "blocking_tickets": self.get_blocking_tickets(ticket.id),
            }

            if not reqs:
                trace["orphans"]["tickets"].append(ticket.id)

        return trace

    def get_traceability_stats(self) -> dict:
        """Get summary statistics for traceability.

        Returns coverage metrics showing how well-linked the specs are.
        """
        trace = self.get_full_traceability()

        total_reqs = len(self.requirements)
        linked_reqs = total_reqs - len(trace["orphans"]["requirements"])

        total_designs = len(self.designs)
        linked_designs = total_designs - len(trace["orphans"]["designs"])

        total_tickets = len(self.tickets)
        linked_tickets = total_tickets - len(trace["orphans"]["tickets"])

        return {
            "requirements": {
                "total": total_reqs,
                "linked": linked_reqs,
                "coverage": (linked_reqs / total_reqs * 100) if total_reqs > 0 else 100,
            },
            "designs": {
                "total": total_designs,
                "linked": linked_designs,
                "coverage": (linked_designs / total_designs * 100) if total_designs > 0 else 100,
            },
            "tickets": {
                "total": total_tickets,
                "linked": linked_tickets,
                "coverage": (linked_tickets / total_tickets * 100) if total_tickets > 0 else 100,
            },
            "tasks": {
                "total": len(self.tasks),
                "done": len([t for t in self.tasks if t.status == "done"]),
                "in_progress": len([t for t in self.tasks if t.status == "in_progress"]),
                "pending": len([t for t in self.tasks if t.status == "pending"]),
            },
            "orphans": trace["orphans"],
        }
