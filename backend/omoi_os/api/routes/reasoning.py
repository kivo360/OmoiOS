"""
Reasoning Chain API Routes

Tracks agent decisions, discoveries, and reasoning events for entities.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, ConfigDict

from omoi_os.api.dependencies import get_db_service
from omoi_os.models.reasoning import ReasoningEvent as ReasoningEventModel
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now

router = APIRouter(prefix="/reasoning", tags=["reasoning"])


# ============================================================================
# Pydantic Models
# ============================================================================


class Evidence(BaseModel):
    type: str  # error, log, code, doc, requirement, test, coverage, stats
    content: str
    link: Optional[str] = None


class Alternative(BaseModel):
    option: str
    rejected: str


class Decision(BaseModel):
    type: str  # proceed, block, complete, implement, investigate
    action: str
    reasoning: str


class EventDetails(BaseModel):
    # Common fields
    context: Optional[str] = None
    reasoning: Optional[str] = None

    # Task-related
    source_spec: Optional[str] = None
    source_requirement: Optional[str] = None
    created_by: Optional[str] = None
    tasks_created: Optional[int] = None
    tasks: Optional[list[str]] = None

    # Discovery-related
    discovery_type: Optional[str] = None
    evidence: Optional[str] = None
    action: Optional[str] = None
    impact: Optional[str] = None

    # Decision-related
    alternatives: Optional[list[Alternative]] = None
    confidence: Optional[float] = None

    # Blocking-related
    blocked_ticket: Optional[str] = None
    blocked_title: Optional[str] = None
    reason: Optional[str] = None

    # Code change-related
    task: Optional[str] = None
    lines_added: Optional[int] = None
    lines_removed: Optional[int] = None
    files_changed: Optional[int] = None
    tests_passing: Optional[int] = None
    tests_total: Optional[int] = None
    commit: Optional[str] = None

    # Error-related
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None


class ReasoningEvent(BaseModel):
    id: str
    timestamp: datetime
    type: str  # ticket_created, task_spawned, discovery, agent_decision, blocking_added, code_change, error
    title: str
    description: str
    agent: Optional[str] = None
    details: Optional[EventDetails] = None
    evidence: list[Evidence] = []
    decision: Optional[Decision] = None

    model_config = ConfigDict(from_attributes=True)


class ReasoningEventCreate(BaseModel):
    type: str
    title: str
    description: str
    agent: Optional[str] = None
    details: Optional[dict] = None
    evidence: list[Evidence] = []
    decision: Optional[Decision] = None


class ReasoningChainResponse(BaseModel):
    entity_type: str
    entity_id: str
    events: list[ReasoningEvent]
    total_count: int
    stats: dict


# ============================================================================
# Helper Functions
# ============================================================================


def _model_to_response(model: ReasoningEventModel) -> ReasoningEvent:
    """Convert database model to response."""
    details = None
    if model.details:
        details = EventDetails(**model.details)

    evidence = []
    if model.evidence:
        evidence = [Evidence(**e) for e in model.evidence]

    decision = None
    if model.decision:
        decision = Decision(**model.decision)

    return ReasoningEvent(
        id=model.id,
        timestamp=model.timestamp,
        type=model.event_type,
        title=model.title,
        description=model.description,
        agent=model.agent,
        details=details,
        evidence=evidence,
        decision=decision,
    )


def _seed_demo_events(
    session, entity_type: str, entity_id: str
) -> list[ReasoningEventModel]:
    """Seed demo events for a new entity."""
    now = utc_now()
    from datetime import timedelta

    events_data = [
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_type": "ticket_created",
            "title": "Ticket Created",
            "description": f"Created {entity_type} {entity_id}",
            "agent": None,
            "details": {
                "context": "Entity initialized from spec requirement",
                "created_by": "system",
            },
            "evidence": [],
            "decision": None,
            "timestamp": now - timedelta(days=3),
        },
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_type": "task_spawned",
            "title": "Tasks Auto-Generated",
            "description": "Implementation tasks created from requirements",
            "agent": "orchestrator",
            "details": {
                "tasks_created": 3,
                "reasoning": "Decomposed into atomic implementation units",
                "tasks": [
                    "TASK-001: Setup",
                    "TASK-002: Implementation",
                    "TASK-003: Testing",
                ],
            },
            "evidence": [],
            "decision": None,
            "timestamp": now - timedelta(days=2, hours=12),
        },
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_type": "agent_decision",
            "title": "Implementation Strategy",
            "description": "Decided on implementation approach",
            "agent": "worker-1",
            "details": {
                "context": "Evaluating implementation options",
                "reasoning": "Selected approach based on existing patterns in codebase",
                "confidence": 0.85,
                "alternatives": [
                    {"option": "Full rewrite", "rejected": "Too risky for timeline"},
                    {
                        "option": "Minimal changes",
                        "rejected": "Insufficient for requirements",
                    },
                ],
            },
            "evidence": [
                {"type": "doc", "content": "Architecture documentation reviewed"},
                {"type": "code", "content": "Existing patterns analyzed"},
            ],
            "decision": {
                "type": "proceed",
                "action": "Implement with incremental approach",
                "reasoning": "Best balance of risk and completeness",
            },
            "timestamp": now - timedelta(days=2),
        },
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_type": "code_change",
            "title": "Initial Implementation",
            "description": "Core functionality implemented",
            "agent": "worker-1",
            "details": {
                "task": "TASK-002",
                "lines_added": 250,
                "lines_removed": 15,
                "files_changed": 4,
                "tests_passing": 8,
                "tests_total": 10,
                "commit": "abc123d",
            },
            "evidence": [
                {"type": "test", "content": "8/10 tests passing"},
                {"type": "coverage", "content": "72% code coverage"},
            ],
            "decision": {
                "type": "implement",
                "action": "Continue with remaining tests",
                "reasoning": "Core functionality working, edge cases need coverage",
            },
            "timestamp": now - timedelta(days=1),
        },
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_type": "discovery",
            "title": "Edge Case Discovery",
            "description": "Found edge case requiring additional handling",
            "agent": "worker-1",
            "details": {
                "discovery_type": "edge_case",
                "context": "During testing, discovered unhandled scenario",
                "evidence": "Input validation fails for empty strings",
                "impact": "Minor - affects specific use case",
                "action": "Added validation logic",
            },
            "evidence": [
                {
                    "type": "error",
                    "content": "ValidationError: empty string not allowed",
                },
                {"type": "test", "content": "test_empty_input FAILED"},
            ],
            "decision": {
                "type": "implement",
                "action": "Add input validation",
                "reasoning": "Quick fix, improves robustness",
            },
            "timestamp": now - timedelta(hours=6),
        },
    ]

    created_events = []
    for data in events_data:
        event = ReasoningEventModel(**data)
        session.add(event)
        created_events.append(event)

    session.commit()
    for event in created_events:
        session.refresh(event)

    return created_events


# ============================================================================
# API Routes
# ============================================================================


@router.get("/{entity_type}/{entity_id}", response_model=ReasoningChainResponse)
async def get_reasoning_chain(
    entity_type: str,
    entity_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=500),
    db: DatabaseService = Depends(get_db_service),
):
    """Get reasoning chain for an entity."""
    with db.get_session() as session:
        # Check if any events exist for this entity
        count = (
            session.query(ReasoningEventModel)
            .filter(
                ReasoningEventModel.entity_type == entity_type,
                ReasoningEventModel.entity_id == entity_id,
            )
            .count()
        )

        # Seed demo data if no events exist
        if count == 0:
            _seed_demo_events(session, entity_type, entity_id)

        # Build query
        query = session.query(ReasoningEventModel).filter(
            ReasoningEventModel.entity_type == entity_type,
            ReasoningEventModel.entity_id == entity_id,
        )

        # Filter by event type if specified
        if event_type and event_type != "all":
            query = query.filter(ReasoningEventModel.event_type == event_type)

        # Get total count for this filter
        total_count = query.count()

        # Get events sorted by timestamp (newest first)
        events = query.order_by(ReasoningEventModel.timestamp.desc()).limit(limit).all()

        # Calculate stats from all events (not filtered)
        all_events = (
            session.query(ReasoningEventModel)
            .filter(
                ReasoningEventModel.entity_type == entity_type,
                ReasoningEventModel.entity_id == entity_id,
            )
            .all()
        )

        by_type: dict[str, int] = {}
        decisions_count = 0
        for e in all_events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
            if e.decision:
                decisions_count += 1

        stats = {
            "total": len(all_events),
            "decisions": decisions_count,
            "discoveries": by_type.get("discovery", 0),
            "errors": by_type.get("error", 0),
            "by_type": by_type,
        }

        return ReasoningChainResponse(
            entity_type=entity_type,
            entity_id=entity_id,
            events=[_model_to_response(e) for e in events],
            total_count=total_count,
            stats=stats,
        )


@router.post("/{entity_type}/{entity_id}/events", response_model=ReasoningEvent)
async def add_reasoning_event(
    entity_type: str,
    entity_id: str,
    event: ReasoningEventCreate,
    db: DatabaseService = Depends(get_db_service),
):
    """Add a reasoning event to an entity's chain."""
    with db.get_session() as session:
        new_event = ReasoningEventModel(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event.type,
            title=event.title,
            description=event.description,
            agent=event.agent,
            details=event.details,
            evidence=[e.model_dump() for e in event.evidence],
            decision=event.decision.model_dump() if event.decision else None,
        )

        session.add(new_event)
        session.commit()
        session.refresh(new_event)

        return _model_to_response(new_event)


@router.get(
    "/{entity_type}/{entity_id}/events/{event_id}", response_model=ReasoningEvent
)
async def get_reasoning_event(
    entity_type: str,
    entity_id: str,
    event_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Get a specific reasoning event."""
    with db.get_session() as session:
        event = (
            session.query(ReasoningEventModel)
            .filter(
                ReasoningEventModel.id == event_id,
                ReasoningEventModel.entity_type == entity_type,
                ReasoningEventModel.entity_id == entity_id,
            )
            .first()
        )

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return _model_to_response(event)


@router.delete("/{entity_type}/{entity_id}/events/{event_id}")
async def delete_reasoning_event(
    entity_type: str,
    entity_id: str,
    event_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Delete a reasoning event."""
    with db.get_session() as session:
        event = (
            session.query(ReasoningEventModel)
            .filter(
                ReasoningEventModel.id == event_id,
                ReasoningEventModel.entity_type == entity_type,
                ReasoningEventModel.entity_id == entity_id,
            )
            .first()
        )

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        session.delete(event)
        session.commit()

        return {"message": "Event deleted successfully"}


@router.get("/types")
async def get_event_types():
    """Get available event types and their configurations."""
    return {
        "event_types": [
            {"id": "ticket_created", "label": "Ticket Created", "icon": "plus"},
            {"id": "task_spawned", "label": "Tasks Spawned", "icon": "zap"},
            {"id": "discovery", "label": "Discovery", "icon": "lightbulb"},
            {"id": "agent_decision", "label": "Agent Decision", "icon": "brain"},
            {
                "id": "blocking_added",
                "label": "Blocking Added",
                "icon": "alert-triangle",
            },
            {"id": "code_change", "label": "Code Change", "icon": "git-branch"},
            {"id": "error", "label": "Error", "icon": "alert-circle"},
        ],
        "evidence_types": [
            {"id": "error", "label": "Error"},
            {"id": "log", "label": "Log"},
            {"id": "code", "label": "Code"},
            {"id": "doc", "label": "Documentation"},
            {"id": "requirement", "label": "Requirement"},
            {"id": "test", "label": "Test"},
            {"id": "coverage", "label": "Coverage"},
            {"id": "stats", "label": "Statistics"},
        ],
        "decision_types": [
            {"id": "proceed", "label": "Proceed"},
            {"id": "block", "label": "Block"},
            {"id": "complete", "label": "Complete"},
            {"id": "implement", "label": "Implement"},
            {"id": "investigate", "label": "Investigate"},
        ],
    }
