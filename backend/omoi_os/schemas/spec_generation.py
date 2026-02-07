"""
Pydantic schemas for spec-driven development state machine.

These schemas support the multi-phase spec generation workflow:
EXPLORE -> REQUIREMENTS -> DESIGN -> TASKS -> SYNC -> COMPLETE

Each phase produces structured output that:
1. Can be serialized to YAML frontmatter + markdown
2. Can be validated before proceeding to next phase
3. Can be synced to the database
4. Supports resumption from checkpoints

The schemas align with the existing .omoi_os/ file structure and
SKILL.md frontmatter conventions.
"""

from datetime import date
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

# =============================================================================
# Enums
# =============================================================================


class SpecPhase(str, Enum):
    """State machine phases for spec generation."""

    EXPLORE = "explore"
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    TASKS = "tasks"
    SYNC = "sync"
    COMPLETE = "complete"


class SpecStatus(str, Enum):
    """Status of a spec or its components."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"


class RequirementCategory(str, Enum):
    """Category of a requirement."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"


class Priority(str, Enum):
    """Priority levels for requirements, tickets, and tasks."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TicketStatus(str, Enum):
    """Status of a ticket."""

    BACKLOG = "backlog"
    ANALYZING = "analyzing"
    BUILDING = "building"
    TESTING = "testing"
    DONE = "done"
    BLOCKED = "blocked"


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class TaskType(str, Enum):
    """Type of task."""

    IMPLEMENTATION = "implementation"
    REFACTOR = "refactor"
    TEST = "test"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    BUGFIX = "bugfix"


class Estimate(str, Enum):
    """Size estimate for tickets and tasks."""

    S = "S"  # < 2 hours
    M = "M"  # 2-4 hours
    L = "L"  # 4-8 hours
    XL = "XL"  # 8+ hours (tickets only)


# =============================================================================
# Phase 1: Exploration Context
# =============================================================================


class CodebasePattern(BaseModel):
    """A pattern discovered during codebase exploration."""

    name: str = Field(
        ..., description="Name of the pattern (e.g., 'Repository Pattern')"
    )
    location: str = Field(..., description="File or directory where pattern is found")
    description: str = Field(
        ..., description="How this pattern is used in the codebase"
    )
    relevance: str = Field(
        ..., description="How this pattern relates to the new feature"
    )


class ExistingComponent(BaseModel):
    """An existing component that the new feature should integrate with."""

    name: str = Field(..., description="Component name")
    file_path: str = Field(..., description="Path to the component")
    interface: str = Field(..., description="Key methods/interfaces to use")
    integration_notes: str = Field(
        ..., description="How to integrate with this component"
    )


class DatabaseSchema(BaseModel):
    """Relevant database schema information."""

    table_name: str = Field(..., description="Name of the database table")
    columns: list[str] = Field(
        default_factory=list, description="Key columns relevant to the feature"
    )
    relationships: list[str] = Field(
        default_factory=list, description="Relationships to other tables"
    )


class ExplorationContext(BaseModel):
    """
    Output of the EXPLORE phase.

    Captures codebase context needed for generating accurate specs.
    This ensures the Agent SDK has explored relevant code before
    generating requirements.
    """

    feature_name: str = Field(..., description="Kebab-case feature name")
    explored_files: list[str] = Field(
        default_factory=list,
        description="Files that were read during exploration",
    )
    patterns: list[CodebasePattern] = Field(
        default_factory=list,
        description="Architectural patterns discovered",
    )
    existing_components: list[ExistingComponent] = Field(
        default_factory=list,
        description="Components to integrate with",
    )
    database_schemas: list[DatabaseSchema] = Field(
        default_factory=list,
        description="Relevant database tables",
    )
    conventions: list[str] = Field(
        default_factory=list,
        description="Coding conventions observed (e.g., 'async/await for I/O')",
    )
    technology_stack: list[str] = Field(
        default_factory=list,
        description="Technologies in use (e.g., 'FastAPI', 'SQLAlchemy')",
    )
    exploration_summary: str = Field(
        ..., description="Summary of what was learned during exploration"
    )


# =============================================================================
# Phase 2: Requirements
# =============================================================================


class AcceptanceCriterion(BaseModel):
    """A single acceptance criterion for a requirement."""

    text: str = Field(..., description="The acceptance criterion text")
    completed: bool = Field(default=False, description="Whether criterion is met")


class Requirement(BaseModel):
    """
    A single requirement in EARS format.

    EARS (Easy Approach to Requirements Syntax):
    WHEN [condition], THE SYSTEM SHALL [action].
    """

    id: str = Field(
        ...,
        pattern=r"^REQ-[A-Z0-9]+-[A-Z]+-\d{3}$",
        description="Requirement ID (e.g., REQ-WEBHOOK-FUNC-001)",
    )
    title: str = Field(..., description="Short title for the requirement")
    category: RequirementCategory = Field(
        default=RequirementCategory.FUNCTIONAL,
        description="Requirement category",
    )
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority level")
    condition: str = Field(..., description="The WHEN clause (trigger condition)")
    action: str = Field(
        ..., description="The THE SYSTEM SHALL clause (expected behavior)"
    )
    rationale: str = Field(default="", description="Why this requirement exists")
    acceptance_criteria: list[AcceptanceCriterion] = Field(
        default_factory=list,
        description="Testable acceptance criteria",
    )
    linked_design: Optional[str] = Field(
        default=None, description="Reference to design section"
    )

    def to_ears_statement(self) -> str:
        """Format as EARS statement."""
        return f"WHEN {self.condition}, THE SYSTEM SHALL {self.action}."


class RequirementsOutput(BaseModel):
    """
    Output of the REQUIREMENTS phase.

    Contains all requirements for a feature, ready for frontmatter serialization.
    """

    # Frontmatter fields (match SKILL.md template)
    id: str = Field(
        ...,
        pattern=r"^REQ-[A-Z0-9]+-\d{3}$",
        description="Requirements document ID (e.g., REQ-WEBHOOK-001)",
    )
    title: str = Field(..., description="Requirements document title")
    feature: str = Field(..., description="Feature name (kebab-case)")
    created: date = Field(default_factory=date.today)
    updated: date = Field(default_factory=date.today)
    status: SpecStatus = Field(default=SpecStatus.DRAFT)
    category: RequirementCategory = Field(default=RequirementCategory.FUNCTIONAL)
    priority: Priority = Field(default=Priority.HIGH)
    prd_ref: Optional[str] = Field(default=None, description="Reference to PRD file")
    design_ref: Optional[str] = Field(
        default=None, description="Reference to design file"
    )

    # Content
    overview: str = Field(..., description="Brief overview of requirements")
    requirements: list[Requirement] = Field(
        default_factory=list, description="List of requirements"
    )

    # Context from exploration (passed through)
    exploration_context: Optional[ExplorationContext] = Field(
        default=None, description="Context from exploration phase"
    )


# =============================================================================
# Phase 3: Design
# =============================================================================


class ApiEndpoint(BaseModel):
    """An API endpoint specification.

    Enhanced to support richer API documentation including:
    - Request/response schemas
    - Authentication requirements
    - Path and query parameters
    - Error responses
    """

    method: str = Field(..., description="HTTP method (GET, POST, PUT, DELETE, PATCH)")
    path: str = Field(..., description="Endpoint path (e.g., /api/v1/webhooks)")
    description: str = Field(..., description="What this endpoint does")
    request_body: Optional[str] = Field(
        default=None, description="Request body schema/description"
    )
    response: Optional[str] = Field(
        default=None, description="Response schema/description"
    )
    auth_required: bool = Field(default=True, description="Requires authentication")
    path_params: list[str] = Field(
        default_factory=list, description="Path parameters (e.g., ['id', 'project_id'])"
    )
    query_params: dict[str, str] = Field(
        default_factory=dict, description="Query parameters with descriptions"
    )
    error_responses: dict[str, str] = Field(
        default_factory=dict, description="Error status codes with descriptions"
    )


class DataModelField(BaseModel):
    """A field in a data model.

    Enhanced to support richer data model documentation including:
    - Type information
    - Nullable flags
    - Default values
    - Constraints (primary_key, unique, indexed, etc.)
    """

    name: str = Field(..., description="Field name")
    type: str = Field(
        ...,
        description="Field type (e.g., 'uuid', 'string', 'int', 'timestamp', 'jsonb')",
    )
    description: str = Field(default="", description="Field description")
    nullable: bool = Field(default=False)
    default: Optional[str] = Field(default=None, description="Default value if any")
    constraints: list[str] = Field(
        default_factory=list,
        description="Constraints (e.g., ['primary_key', 'unique', 'indexed'])",
    )


class DataModel(BaseModel):
    """A data model/entity specification."""

    name: str = Field(..., description="Model name (e.g., WebhookSubscription)")
    description: str = Field(..., description="What this model represents")
    fields: list[DataModelField] = Field(
        default_factory=list, description="Model fields"
    )
    relationships: list[str] = Field(
        default_factory=list, description="Relationships to other models"
    )
    table_name: Optional[str] = Field(
        default=None, description="Database table name if different"
    )


class DesignOutput(BaseModel):
    """
    Output of the DESIGN phase.

    Contains architecture, data models, and API specs ready for
    frontmatter serialization.
    """

    # Frontmatter fields
    id: str = Field(
        ...,
        pattern=r"^DESIGN-[A-Z0-9]+-\d{3}$",
        description="Design document ID (e.g., DESIGN-WEBHOOK-001)",
    )
    title: str = Field(..., description="Design document title")
    feature: str = Field(..., description="Feature name (kebab-case)")
    created: date = Field(default_factory=date.today)
    updated: date = Field(default_factory=date.today)
    status: SpecStatus = Field(default=SpecStatus.DRAFT)
    requirements: list[str] = Field(
        default_factory=list,
        description="Requirement IDs this design addresses",
    )

    # Architecture
    architecture_overview: str = Field(
        ..., description="High-level architecture description"
    )
    architecture_diagram: Optional[str] = Field(
        default=None, description="Mermaid diagram of architecture"
    )
    components: list[str] = Field(default_factory=list, description="Key components")

    # Data Model
    data_models: list[DataModel] = Field(
        default_factory=list, description="Data models for this feature"
    )
    database_migrations: Optional[str] = Field(
        default=None, description="SQL migration description"
    )

    # API Specification
    api_endpoints: list[ApiEndpoint] = Field(
        default_factory=list, description="API endpoints"
    )

    # Implementation Details
    error_handling: str = Field(default="", description="Error handling strategy")
    security_considerations: str = Field(
        default="", description="Security considerations"
    )
    performance_considerations: str = Field(
        default="", description="Performance considerations"
    )
    testing_strategy: str = Field(default="", description="Testing approach")

    # Context from previous phases
    exploration_context: Optional[ExplorationContext] = Field(default=None)
    requirements_output: Optional[RequirementsOutput] = Field(default=None)


# =============================================================================
# Phase 4: Tickets and Tasks
# =============================================================================


class TicketDependencies(BaseModel):
    """Dependencies for a ticket."""

    blocked_by: list[str] = Field(
        default_factory=list, description="Ticket IDs that block this one"
    )
    blocks: list[str] = Field(
        default_factory=list, description="Ticket IDs that this blocks"
    )


class TaskDependencies(BaseModel):
    """Dependencies for a task."""

    depends_on: list[str] = Field(
        default_factory=list, description="Task IDs this depends on"
    )
    blocks: list[str] = Field(
        default_factory=list, description="Task IDs that this blocks"
    )


class Task(BaseModel):
    """
    A single atomic task.

    Tasks should be completable in 1-4 hours by an AI agent.
    """

    # Frontmatter fields
    id: str = Field(
        ...,
        pattern=r"^TSK-\d{3}$",
        description="Task ID (e.g., TSK-001)",
    )
    title: str = Field(..., description="Short task title")
    created: date = Field(default_factory=date.today)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    parent_ticket: str = Field(..., description="Parent ticket ID (e.g., TKT-001)")
    estimate: Estimate = Field(default=Estimate.M, description="Size estimate")
    task_type: TaskType = Field(
        default=TaskType.IMPLEMENTATION, description="Type of task"
    )
    priority: Priority = Field(default=Priority.MEDIUM)
    dependencies: TaskDependencies = Field(default_factory=TaskDependencies)

    # Content
    objective: str = Field(..., description="One-sentence objective")
    context: str = Field(default="", description="Background context")
    deliverables: list[str] = Field(
        default_factory=list,
        description="Specific files/outputs to produce",
    )
    implementation_notes: str = Field(
        default="", description="Guidance for implementation"
    )
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Criteria for task completion",
    )
    verification_command: Optional[str] = Field(
        default=None,
        description="Command to verify task completion (e.g., pytest test_file.py)",
    )


class Ticket(BaseModel):
    """
    A ticket grouping related tasks.

    One ticket typically maps to one major component from the design.
    """

    # Frontmatter fields
    id: str = Field(
        ...,
        pattern=r"^TKT-\d{3}$",
        description="Ticket ID (e.g., TKT-001)",
    )
    title: str = Field(..., description="Ticket title")
    created: date = Field(default_factory=date.today)
    updated: date = Field(default_factory=date.today)
    status: TicketStatus = Field(default=TicketStatus.BACKLOG)
    priority: Priority = Field(default=Priority.HIGH)
    estimate: Estimate = Field(default=Estimate.M)
    feature: Optional[str] = Field(default=None, description="Feature name")
    design_ref: Optional[str] = Field(
        default=None, description="Reference to design file"
    )
    requirements: list[str] = Field(
        default_factory=list, description="Requirement IDs this implements"
    )
    dependencies: TicketDependencies = Field(default_factory=TicketDependencies)

    # Content
    description: str = Field(..., description="Ticket description")
    scope_in: list[str] = Field(default_factory=list, description="What's in scope")
    scope_out: list[str] = Field(
        default_factory=list, description="What's out of scope"
    )
    acceptance_criteria: list[str] = Field(
        default_factory=list, description="Ticket acceptance criteria"
    )
    technical_notes: str = Field(default="", description="Technical context")

    # Tasks belonging to this ticket
    tasks: list[Task] = Field(default_factory=list, description="Tasks for this ticket")


class TasksOutput(BaseModel):
    """
    Output of the TASKS phase.

    Contains all tickets and tasks for a feature.
    """

    feature: str = Field(..., description="Feature name (kebab-case)")
    tickets: list[Ticket] = Field(default_factory=list, description="All tickets")

    # Context from previous phases
    exploration_context: Optional[ExplorationContext] = Field(default=None)
    requirements_output: Optional[RequirementsOutput] = Field(default=None)
    design_output: Optional[DesignOutput] = Field(default=None)

    def get_all_tasks(self) -> list[Task]:
        """Get all tasks across all tickets."""
        tasks = []
        for ticket in self.tickets:
            tasks.extend(ticket.tasks)
        return tasks

    def get_ready_tasks(self) -> list[Task]:
        """Get tasks that have no pending dependencies."""
        completed = {t.id for t in self.get_all_tasks() if t.status == TaskStatus.DONE}
        ready = []
        for task in self.get_all_tasks():
            if task.status != TaskStatus.PENDING:
                continue
            if all(dep in completed for dep in task.dependencies.depends_on):
                ready.append(task)
        return ready


# =============================================================================
# State Machine State
# =============================================================================


class PhaseResult(BaseModel):
    """Result of executing a phase."""

    phase: SpecPhase = Field(..., description="Phase that was executed")
    success: bool = Field(..., description="Whether phase succeeded")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retries attempted")
    validation_errors: list[str] = Field(
        default_factory=list, description="Validation errors if any"
    )


class SpecGenerationState(BaseModel):
    """
    Complete state of the spec generation state machine.

    This is persisted to the database after each phase, enabling:
    - Resumption from any checkpoint
    - Retry with feedback on validation failure
    - Progress tracking
    """

    # Identification
    spec_id: UUID = Field(..., description="Unique ID for this spec generation run")
    project_id: UUID = Field(..., description="Project this spec belongs to")
    feature_name: str = Field(..., description="Feature being specified")

    # State Machine
    current_phase: SpecPhase = Field(
        default=SpecPhase.EXPLORE, description="Current phase"
    )
    phase_history: list[PhaseResult] = Field(
        default_factory=list, description="Results of completed phases"
    )

    # Phase Outputs (populated as phases complete)
    exploration_context: Optional[ExplorationContext] = Field(default=None)
    requirements_output: Optional[RequirementsOutput] = Field(default=None)
    design_output: Optional[DesignOutput] = Field(default=None)
    tasks_output: Optional[TasksOutput] = Field(default=None)

    # Metadata
    created_at: date = Field(default_factory=date.today)
    updated_at: date = Field(default_factory=date.today)
    retry_count: int = Field(default=0, description="Total retries across all phases")
    max_retries: int = Field(default=3, description="Max retries per phase")

    def can_proceed(self) -> bool:
        """Check if we can proceed to next phase."""
        if not self.phase_history:
            return True
        last_result = self.phase_history[-1]
        return last_result.success

    def get_next_phase(self) -> Optional[SpecPhase]:
        """Get the next phase to execute."""
        phase_order = [
            SpecPhase.EXPLORE,
            SpecPhase.REQUIREMENTS,
            SpecPhase.DESIGN,
            SpecPhase.TASKS,
            SpecPhase.SYNC,
            SpecPhase.COMPLETE,
        ]
        try:
            current_idx = phase_order.index(self.current_phase)
            if current_idx < len(phase_order) - 1:
                return phase_order[current_idx + 1]
        except ValueError:
            pass
        return None

    def advance_phase(self, result: PhaseResult) -> None:
        """Record phase result and advance to next phase."""
        self.phase_history.append(result)
        if result.success:
            next_phase = self.get_next_phase()
            if next_phase:
                self.current_phase = next_phase
        self.updated_at = date.today()


# =============================================================================
# Evaluator Outputs
# =============================================================================


class EvaluationResult(BaseModel):
    """Result of evaluating phase output."""

    valid: bool = Field(..., description="Whether output passed validation")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Quality score 0-1")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(
        default_factory=list, description="Non-blocking warnings"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Improvement suggestions"
    )
    feedback_for_retry: Optional[str] = Field(
        default=None,
        description="Specific feedback to include if retrying",
    )
