"""
Reasoning Chain API Routes

Tracks agent decisions, discoveries, and reasoning events for entities.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from omoi_os.api.dependencies import get_db_service


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
# In-Memory Storage
# ============================================================================

# Store events by entity key (e.g., "ticket:TICKET-001")
_reasoning_store: dict[str, list[dict]] = {}


def _get_entity_key(entity_type: str, entity_id: str) -> str:
    return f"{entity_type}:{entity_id}"


def _seed_demo_events(entity_type: str, entity_id: str) -> list[dict]:
    """Generate demo events for a new entity."""
    now = datetime.utcnow()
    base_time = now.timestamp()

    events = [
        {
            "id": f"evt-{uuid4().hex[:8]}",
            "timestamp": datetime.fromtimestamp(base_time - 3 * 24 * 60 * 60),
            "type": "ticket_created",
            "title": "Ticket Created",
            "description": f"Created {entity_type} {entity_id}",
            "agent": None,
            "details": {
                "context": "Entity initialized from spec requirement",
                "created_by": "system",
            },
            "evidence": [],
            "decision": None,
        },
        {
            "id": f"evt-{uuid4().hex[:8]}",
            "timestamp": datetime.fromtimestamp(base_time - 2.5 * 24 * 60 * 60),
            "type": "task_spawned",
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
        },
        {
            "id": f"evt-{uuid4().hex[:8]}",
            "timestamp": datetime.fromtimestamp(base_time - 2 * 24 * 60 * 60),
            "type": "agent_decision",
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
        },
        {
            "id": f"evt-{uuid4().hex[:8]}",
            "timestamp": datetime.fromtimestamp(base_time - 1 * 24 * 60 * 60),
            "type": "code_change",
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
        },
        {
            "id": f"evt-{uuid4().hex[:8]}",
            "timestamp": datetime.fromtimestamp(base_time - 6 * 60 * 60),
            "type": "discovery",
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
        },
    ]

    return events


# ============================================================================
# API Routes
# ============================================================================


@router.get("/{entity_type}/{entity_id}", response_model=ReasoningChainResponse)
async def get_reasoning_chain(
    entity_type: str,
    entity_id: str,
    event_type: Optional[str] = None,
    limit: int = 100,
    db=Depends(get_db_service),
):
    """Get reasoning chain for an entity."""
    key = _get_entity_key(entity_type, entity_id)

    # Initialize with demo data if not exists
    if key not in _reasoning_store:
        _reasoning_store[key] = _seed_demo_events(entity_type, entity_id)

    events = _reasoning_store[key]

    # Filter by type if specified
    if event_type and event_type != "all":
        events = [e for e in events if e["type"] == event_type]

    # Sort by timestamp descending (most recent first)
    events = sorted(events, key=lambda x: x["timestamp"], reverse=True)

    # Apply limit
    events = events[:limit]

    # Calculate stats
    all_events = _reasoning_store[key]
    by_type: dict[str, int] = {}
    for e in all_events:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1

    stats = {
        "total": len(all_events),
        "decisions": sum(1 for e in all_events if e.get("decision")),
        "discoveries": by_type.get("discovery", 0),
        "errors": by_type.get("error", 0),
        "by_type": by_type,
    }

    return ReasoningChainResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        events=[ReasoningEvent(**e) for e in events],
        total_count=len(all_events),
        stats=stats,
    )


@router.post("/{entity_type}/{entity_id}/events", response_model=ReasoningEvent)
async def add_reasoning_event(
    entity_type: str,
    entity_id: str,
    event: ReasoningEventCreate,
    db=Depends(get_db_service),
):
    """Add a reasoning event to an entity's chain."""
    key = _get_entity_key(entity_type, entity_id)

    if key not in _reasoning_store:
        _reasoning_store[key] = []

    event_id = f"evt-{uuid4().hex[:8]}"
    now = datetime.utcnow()

    new_event = {
        "id": event_id,
        "timestamp": now,
        "type": event.type,
        "title": event.title,
        "description": event.description,
        "agent": event.agent,
        "details": event.details,
        "evidence": [e.model_dump() for e in event.evidence],
        "decision": event.decision.model_dump() if event.decision else None,
    }

    _reasoning_store[key].append(new_event)

    return ReasoningEvent(**new_event)


@router.get(
    "/{entity_type}/{entity_id}/events/{event_id}", response_model=ReasoningEvent
)
async def get_reasoning_event(
    entity_type: str,
    entity_id: str,
    event_id: str,
    db=Depends(get_db_service),
):
    """Get a specific reasoning event."""
    key = _get_entity_key(entity_type, entity_id)

    if key not in _reasoning_store:
        raise HTTPException(status_code=404, detail="Entity not found")

    for event in _reasoning_store[key]:
        if event["id"] == event_id:
            return ReasoningEvent(**event)

    raise HTTPException(status_code=404, detail="Event not found")


@router.delete("/{entity_type}/{entity_id}/events/{event_id}")
async def delete_reasoning_event(
    entity_type: str,
    entity_id: str,
    event_id: str,
    db=Depends(get_db_service),
):
    """Delete a reasoning event."""
    key = _get_entity_key(entity_type, entity_id)

    if key not in _reasoning_store:
        raise HTTPException(status_code=404, detail="Entity not found")

    original_len = len(_reasoning_store[key])
    _reasoning_store[key] = [e for e in _reasoning_store[key] if e["id"] != event_id]

    if len(_reasoning_store[key]) == original_len:
        raise HTTPException(status_code=404, detail="Event not found")

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
