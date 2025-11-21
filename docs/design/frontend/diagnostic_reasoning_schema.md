# Diagnostic Reasoning Schema Changes

**Created**: 2025-01-30
**Status**: Schema Proposal
**Purpose**: Add reasoning fields to track WHY tickets are connected and WHY tasks are linked
**Related**: [Diagnostic Reasoning View](./diagnostic_reasoning_view.md), [Hephaestus Patterns](../implementation/workflows/hephaestus_workflow_enhancements.md)

---

## Overview

This document proposes database schema changes to add reasoning fields for:
1. **Ticket Blocking Relationships** - WHY tickets are connected
2. **Task-Ticket Links** - WHY tasks are linked to tickets
3. **Task Dependencies** - WHY tasks depend on each other

These changes enable the unified diagnostic reasoning view and align with Hephaestus patterns of tracking WHY workflows branch.

---

## Schema Changes

### 1. Enhanced Ticket Blocking Relationships

**Current Schema** (`omoi_os/ticketing/models.py`):
```python
blocked_by_ticket_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
# Current structure: {"ids": ["ticket-1", "ticket-2"]}
```

**Proposed Schema**:
```python
blocked_by_ticket_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
# New structure:
# {
#   "ids": ["ticket-1", "ticket-2"],
#   "relationships": [
#     {
#       "blocking_ticket_id": "ticket-1",
#       "reason": "Auth system requires Redis cache to be operational",
#       "created_by_agent_id": "agent-123",
#       "created_at": "2025-10-30T10:28:00Z",
#       "dependency_type": "infrastructure",  # infrastructure | component | data | api
#       "required_for": ["session_storage", "token_validation"],
#       "agent_reasoning": "Cannot proceed with auth until cache is ready",
#       "evidence": ["src/auth/cache.py imports redis", "Design doc mentions Redis requirement"]
#     }
#   ]
# }
```

**Migration**:
```sql
-- Migration: 032_add_ticket_blocking_reasoning.sql

-- Update existing blocked_by_ticket_ids to new structure
UPDATE tickets
SET blocked_by_ticket_ids = jsonb_build_object(
  'ids', COALESCE(blocked_by_ticket_ids->'ids', '[]'::jsonb),
  'relationships', '[]'::jsonb
)
WHERE blocked_by_ticket_ids IS NOT NULL
  AND blocked_by_ticket_ids ? 'ids'
  AND NOT (blocked_by_ticket_ids ? 'relationships');

-- Add index for querying blocking relationships
CREATE INDEX idx_tickets_blocking_reasoning 
ON tickets USING GIN ((blocked_by_ticket_ids->'relationships'));
```

**New Model Helper**:
```python
# omoi_os/ticketing/models.py

class Ticket(Base):
    # ... existing fields ...
    
    def add_blocking_relationship(
        self,
        blocking_ticket_id: str,
        reason: str,
        agent_id: str,
        dependency_type: str = "component",
        required_for: Optional[List[str]] = None,
        agent_reasoning: Optional[str] = None,
        evidence: Optional[List[str]] = None,
    ) -> None:
        """Add a blocking relationship with reasoning."""
        if not self.blocked_by_ticket_ids:
            self.blocked_by_ticket_ids = {"ids": [], "relationships": []}
        
        # Add to IDs list if not present
        if blocking_ticket_id not in self.blocked_by_ticket_ids.get("ids", []):
            self.blocked_by_ticket_ids["ids"].append(blocking_ticket_id)
        
        # Add relationship record
        relationship = {
            "blocking_ticket_id": blocking_ticket_id,
            "reason": reason,
            "created_by_agent_id": agent_id,
            "created_at": utc_now().isoformat(),
            "dependency_type": dependency_type,
            "required_for": required_for or [],
            "agent_reasoning": agent_reasoning,
            "evidence": evidence or [],
        }
        
        relationships = self.blocked_by_ticket_ids.get("relationships", [])
        # Remove existing relationship for this blocking ticket if present
        relationships = [r for r in relationships if r["blocking_ticket_id"] != blocking_ticket_id]
        relationships.append(relationship)
        
        self.blocked_by_ticket_ids["relationships"] = relationships
    
    def get_blocking_reason(self, blocking_ticket_id: str) -> Optional[dict]:
        """Get reasoning for a specific blocking relationship."""
        if not self.blocked_by_ticket_ids:
            return None
        
        relationships = self.blocked_by_ticket_ids.get("relationships", [])
        for rel in relationships:
            if rel["blocking_ticket_id"] == blocking_ticket_id:
                return rel
        return None
```

---

### 2. Task-Ticket Link Reasoning

**Current Schema** (`omoi_os/models/task.py`):
```python
ticket_id: Mapped[str] = mapped_column(
    String, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
)
# Only foreign key, no reasoning
```

**Proposed Schema**:
```python
ticket_id: Mapped[str] = mapped_column(
    String, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
)
link_reason: Mapped[Optional[str]] = mapped_column(
    Text, nullable=True,
    comment="Reason why this task is linked to this ticket"
)
link_metadata: Mapped[Optional[dict]] = mapped_column(
    JSONB, nullable=True,
    comment="Additional metadata about the link (agent_reasoning, discovery_id, automatic, evidence)"
)
linked_by_agent_id: Mapped[Optional[str]] = mapped_column(
    String, nullable=True, index=True,
    comment="Agent that linked this task to the ticket"
)
linked_at: Mapped[Optional[datetime]] = mapped_column(
    DateTime(timezone=True), nullable=True,
    comment="When the task was linked to the ticket"
)
```

**Migration**:
```sql
-- Migration: 032_add_task_ticket_link_reasoning.sql

ALTER TABLE tasks ADD COLUMN link_reason TEXT;
ALTER TABLE tasks ADD COLUMN link_metadata JSONB;
ALTER TABLE tasks ADD COLUMN linked_by_agent_id VARCHAR;
ALTER TABLE tasks ADD COLUMN linked_at TIMESTAMP WITH TIME ZONE;

-- Set linked_at to created_at for existing tasks
UPDATE tasks
SET linked_at = created_at
WHERE linked_at IS NULL;

-- Add indexes
CREATE INDEX idx_tasks_link_reason ON tasks(link_reason) WHERE link_reason IS NOT NULL;
CREATE INDEX idx_tasks_linked_by_agent ON tasks(linked_by_agent_id) WHERE linked_by_agent_id IS NOT NULL;
CREATE INDEX idx_tasks_link_metadata ON tasks USING GIN(link_metadata) WHERE link_metadata IS NOT NULL;
```

**Link Metadata Structure**:
```json
{
  "agent_reasoning": "This task implements the Redis cache setup needed by auth",
  "discovery_id": "discovery-001",
  "automatic": true,
  "evidence": ["Task description matches ticket requirement"],
  "link_method": "discovery_based"  // discovery_based | manual | automatic
}
```

---

### 3. Task Dependency Reasoning

**Current Schema** (`omoi_os/models/task.py`):
```python
dependencies: Mapped[Optional[dict]] = mapped_column(
    JSONB, nullable=True
)
# Current structure: {"depends_on": ["task_id_1", "task_id_2"]}
```

**Proposed Schema**:
```python
dependencies: Mapped[Optional[dict]] = mapped_column(
    JSONB, nullable=True
)
# New structure:
# {
#   "depends_on": ["task_id_1", "task_id_2"],
#   "relationships": [
#     {
#       "depends_on_task_id": "task_id_1",
#       "reason": "Task requires database schema to be created first",
#       "dependency_type": "data",  # data | component | api | infrastructure
#       "created_by_agent_id": "agent-123",
#       "created_at": "2025-10-30T10:15:00Z",
#       "agent_reasoning": "Cannot create API endpoints without database tables",
#       "evidence": ["Task creates User model", "API needs User table"]
#     }
#   ]
# }
```

**Migration**:
```sql
-- Migration: 032_add_task_dependency_reasoning.sql

-- Update existing dependencies to new structure
UPDATE tasks
SET dependencies = jsonb_build_object(
  'depends_on', COALESCE(dependencies->'depends_on', '[]'::jsonb),
  'relationships', '[]'::jsonb
)
WHERE dependencies IS NOT NULL
  AND dependencies ? 'depends_on'
  AND NOT (dependencies ? 'relationships');

-- Add index for querying dependency relationships
CREATE INDEX idx_tasks_dependency_reasoning 
ON tasks USING GIN ((dependencies->'relationships'));
```

**New Model Helper**:
```python
# omoi_os/models/task.py

class Task(Base):
    # ... existing fields ...
    
    def add_dependency(
        self,
        depends_on_task_id: str,
        reason: str,
        agent_id: str,
        dependency_type: str = "component",
        agent_reasoning: Optional[str] = None,
        evidence: Optional[List[str]] = None,
    ) -> None:
        """Add a dependency relationship with reasoning."""
        if not self.dependencies:
            self.dependencies = {"depends_on": [], "relationships": []}
        
        # Add to depends_on list if not present
        if depends_on_task_id not in self.dependencies.get("depends_on", []):
            self.dependencies["depends_on"].append(depends_on_task_id)
        
        # Add relationship record
        relationship = {
            "depends_on_task_id": depends_on_task_id,
            "reason": reason,
            "dependency_type": dependency_type,
            "created_by_agent_id": agent_id,
            "created_at": utc_now().isoformat(),
            "agent_reasoning": agent_reasoning,
            "evidence": evidence or [],
        }
        
        relationships = self.dependencies.get("relationships", [])
        # Remove existing relationship for this dependency if present
        relationships = [r for r in relationships if r["depends_on_task_id"] != depends_on_task_id]
        relationships.append(relationship)
        
        self.dependencies["relationships"] = relationships
    
    def get_dependency_reason(self, depends_on_task_id: str) -> Optional[dict]:
        """Get reasoning for a specific dependency."""
        if not self.dependencies:
            return None
        
        relationships = self.dependencies.get("relationships", [])
        for rel in relationships:
            if rel["depends_on_task_id"] == depends_on_task_id:
                return rel
        return None
```

---

## Service Layer Changes

### Ticket Service Updates

**File**: `omoi_os/ticketing/services/ticket_service.py`

```python
def add_blocking_relationship(
    self,
    session: Session,
    ticket_id: str,
    blocking_ticket_id: str,
    reason: str,
    agent_id: str,
    dependency_type: str = "component",
    required_for: Optional[List[str]] = None,
    agent_reasoning: Optional[str] = None,
    evidence: Optional[List[str]] = None,
) -> Ticket:
    """Add a blocking relationship with reasoning."""
    ticket = session.query(Ticket).filter(Ticket.id == ticket_id).one()
    
    ticket.add_blocking_relationship(
        blocking_ticket_id=blocking_ticket_id,
        reason=reason,
        agent_id=agent_id,
        dependency_type=dependency_type,
        required_for=required_for,
        agent_reasoning=agent_reasoning,
        evidence=evidence,
    )
    
    # Record in history
    history = TicketHistory(
        ticket_id=ticket_id,
        agent_id=agent_id,
        change_type="blocking_added",
        change_description=f"Added blocking relationship to {blocking_ticket_id}",
        change_metadata={
            "blocking_ticket_id": blocking_ticket_id,
            "reason": reason,
            "dependency_type": dependency_type,
        },
    )
    session.add(history)
    
    return ticket
```

### Task Queue Service Updates

**File**: `omoi_os/services/task_queue.py`

```python
def enqueue_task(
    self,
    ticket_id: str,
    phase_id: str,
    task_type: str,
    description: str,
    priority: str,
    link_reason: Optional[str] = None,
    link_metadata: Optional[dict] = None,
    linked_by_agent_id: Optional[str] = None,
    session: Optional[Session] = None,
) -> Task:
    """Enqueue a task with optional link reasoning."""
    # ... existing task creation code ...
    
    task.link_reason = link_reason
    task.link_metadata = link_metadata
    task.linked_by_agent_id = linked_by_agent_id
    task.linked_at = utc_now()
    
    # ... rest of task creation ...
```

---

## MCP Tool Updates

### Update `create_ticket` Tool

**File**: `omoi_os/mcp/fastmcp_server.py`

```python
@tool()
def create_ticket(
    ctx: Context,
    workflow_id: str,
    agent_id: str,
    title: str,
    description: str,
    ticket_type: str = "component",
    priority: str = "medium",
    blocked_by_ticket_ids: List[str] = Field(default_factory=list),
    blocking_reasons: Optional[Dict[str, str]] = Field(
        default=None,
        description="Map of blocking_ticket_id -> reason for blocking relationship"
    ),
    blocking_metadata: Optional[Dict[str, dict]] = Field(
        default=None,
        description="Map of blocking_ticket_id -> metadata (dependency_type, agent_reasoning, etc.)"
    ),
) -> Dict[str, Any]:
    """Create ticket with optional blocking relationship reasoning."""
    # ... existing ticket creation ...
    
    # Add blocking relationships with reasoning
    if blocked_by_ticket_ids and blocking_reasons:
        for blocking_id in blocked_by_ticket_ids:
            reason = blocking_reasons.get(blocking_id, "Dependency relationship")
            metadata = blocking_metadata.get(blocking_id, {}) if blocking_metadata else {}
            
            ticket.add_blocking_relationship(
                blocking_ticket_id=blocking_id,
                reason=reason,
                agent_id=agent_id,
                dependency_type=metadata.get("dependency_type", "component"),
                required_for=metadata.get("required_for"),
                agent_reasoning=metadata.get("agent_reasoning"),
                evidence=metadata.get("evidence"),
            )
```

### Update Task Creation

**File**: `omoi_os/mcp/fastmcp_server.py`

```python
@tool()
def create_task(
    ctx: Context,
    workflow_id: str,
    agent_id: str,
    description: str,
    phase_id: str,
    ticket_id: Optional[str] = None,
    link_reason: Optional[str] = Field(
        default=None,
        description="Reason why this task is linked to the ticket"
    ),
    link_metadata: Optional[dict] = Field(
        default=None,
        description="Additional link metadata (agent_reasoning, discovery_id, etc.)"
    ),
    depends_on_task_ids: List[str] = Field(default_factory=list),
    dependency_reasons: Optional[Dict[str, str]] = Field(
        default=None,
        description="Map of depends_on_task_id -> reason for dependency"
    ),
) -> Dict[str, Any]:
    """Create task with optional link and dependency reasoning."""
    # ... existing task creation ...
    
    if ticket_id and link_reason:
        task.link_reason = link_reason
        task.link_metadata = link_metadata or {}
        task.linked_by_agent_id = agent_id
        task.linked_at = utc_now()
    
    # Add dependencies with reasoning
    if depends_on_task_ids and dependency_reasons:
        for dep_id in depends_on_task_ids:
            reason = dependency_reasons.get(dep_id, "Task dependency")
            task.add_dependency(
                depends_on_task_id=dep_id,
                reason=reason,
                agent_id=agent_id,
                agent_reasoning=link_metadata.get("agent_reasoning") if link_metadata else None,
            )
```

---

## Hephaestus Alignment

### How Hephaestus Handles This

**Hephaestus Pattern**: "Track WHY workflows branch, not just WHAT happened"

**Key Principles**:
1. **Discovery Context**: Every discovery includes context and evidence
2. **Agent Reasoning**: Agents provide reasoning when creating relationships
3. **Memory Integration**: Decisions stored in memory system for future reference
4. **Graph Visualization**: Shows reasoning chain, not just connections

**OmoiOS Implementation**:
- ✅ TaskDiscovery tracks WHY tasks spawned (already implemented)
- ✅ Memory system stores agent decisions (already implemented)
- ⚠️ **Adding**: Reasoning fields for ticket blocking relationships
- ⚠️ **Adding**: Reasoning fields for task-ticket links
- ⚠️ **Adding**: Reasoning fields for task dependencies

---

## Migration Strategy

### Phase 1: Add New Fields (Backward Compatible)
1. Add new columns/fields to existing tables
2. Migrate existing data to new structure
3. Update service layer to populate new fields

### Phase 2: Update MCP Tools
1. Update `create_ticket` to accept blocking_reasons
2. Update `create_task` to accept link_reason and dependency_reasons
3. Update agents to provide reasoning when creating relationships

### Phase 3: Build Diagnostic View
1. Create diagnostic API endpoints
2. Build diagnostic UI components
3. Integrate with existing views (Kanban, Graph)

---

## Related Documents

- [Diagnostic Reasoning View](./diagnostic_reasoning_view.md) - UI design
- [Hephaestus Workflow Enhancements](../implementation/workflows/hephaestus_workflow_enhancements.md) - Discovery tracking
- [Task Discovery Model](../../omoi_os/models/task_discovery.py) - Model definition

