# Plan: Add Dependencies to Spec-Driven-Dev Skill

**Created**: 2025-12-29
**Status**: Draft
**Purpose**: Add ticket/task dependency support to the spec-driven-dev skill and create programmatic scanning utilities for direct API access

---

## Executive Summary

This plan addresses two requirements:
1. **Add dependency support** to the spec-driven-dev skill's ticket and task templates
2. **Create programmatic scanning utilities** to scan tickets/tasks and call the API directly (bypassing MCP server)

---

## Part 1: Add Ticket and Task Dependencies

### Current State Analysis

The existing templates already have dependency sections, but they are:
- **Ticket template** (`references/ticket_template.md`): Has "Blocks", "Blocked By", and "Related" sections - but these are freeform text
- **Task template** (`references/task_template.md`): Has "Requires" and "Provides" sections - also freeform text

The **backend database models** already support dependencies:
- `Task.dependencies`: JSONB field with structure `{"depends_on": ["task_id_1", "task_id_2"]}`
- `Task.parent_task_id`: FK to parent task for hierarchy
- `Ticket` model: Currently has no explicit dependency fields (uses blocking overlay mechanism instead)

### Proposed Changes

#### 1.1 Update Ticket Template with Structured Dependencies

**File**: `.claude/skills/spec-driven-dev/references/ticket_template.md`

Add structured dependency format:

```markdown
## Dependencies

### Blocks (other tickets waiting on this)
<!-- Format: TKT-XXX: Brief reason -->
- TKT-003: Cannot start auth until user model exists

### Blocked By (tickets that must complete first)
<!-- Format: TKT-XXX: Brief reason -->
- TKT-001: Requires database schema from infrastructure ticket

### Related (informational, not blocking)
<!-- Format: TKT-XXX: Relationship -->
- TKT-005: Same feature area, may share components
```

Add machine-readable frontmatter:

```yaml
---
id: TKT-001
title: Implement User Authentication
status: backlog
priority: HIGH
estimate: L
created: 2025-12-29
dependencies:
  blocks: [TKT-003, TKT-004]
  blocked_by: [TKT-001]
  related: [TKT-005]
---
```

#### 1.2 Update Task Template with Structured Dependencies

**File**: `.claude/skills/spec-driven-dev/references/task_template.md`

Add structured dependency format that matches the backend JSONB schema:

```yaml
---
id: TSK-001
title: Implement CRDT Data Types
status: pending
parent_ticket: TKT-001
estimate: M
assignee: null
dependencies:
  depends_on: [TSK-002, TSK-003]  # Must complete first
  blocks: [TSK-005, TSK-006]       # Cannot start until this completes
---
```

#### 1.3 Update SKILL.md Documentation

Add section explaining dependency management:

```markdown
## Dependency Management

### Ticket Dependencies
Tickets can have three types of relationships:
- **blocked_by**: Tickets that must complete before this can start
- **blocks**: Tickets waiting on this one
- **related**: Informational links (non-blocking)

### Task Dependencies
Tasks use the same schema as the backend:
- **depends_on**: Array of task IDs that must complete first
- **blocks**: Array of task IDs waiting on this one

### Best Practices
1. Keep dependency chains short (max 3-4 levels)
2. Avoid circular dependencies
3. Mark infrastructure tasks as blockers for feature tasks
4. Use `related` for informational links, not blocking
```

---

## Part 2: Programmatic Ticket/Task Scanning

### Goal

Create Python utilities that:
1. Scan `.omoi_os/` directory for tickets and tasks
2. Parse frontmatter and content
3. Provide structured data for API calls
4. Optionally sync to backend API directly

### Proposed Implementation

#### 2.1 Create Parser Module

**File**: `.claude/skills/spec-driven-dev/scripts/parse_specs.py`

```python
"""
Parse .omoi_os/ ticket and task files into structured data.

Usage:
    python parse_specs.py --list-tickets
    python parse_specs.py --list-tasks
    python parse_specs.py --get-ticket TKT-001
    python parse_specs.py --get-dependencies TKT-001
    python parse_specs.py --export-json
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml
import re

@dataclass
class TicketDependencies:
    blocks: list[str]
    blocked_by: list[str]
    related: list[str]

@dataclass
class ParsedTicket:
    id: str
    title: str
    status: str
    priority: str
    estimate: str
    description: str
    acceptance_criteria: list[str]
    tasks: list[str]
    dependencies: TicketDependencies
    raw_content: str

@dataclass
class TaskDependencies:
    depends_on: list[str]
    blocks: list[str]

@dataclass
class ParsedTask:
    id: str
    title: str
    status: str
    parent_ticket: str
    estimate: str
    assignee: Optional[str]
    objective: str
    deliverables: list[str]
    acceptance_criteria: list[str]
    dependencies: TaskDependencies
    raw_content: str

class SpecParser:
    """Parse spec files from .omoi_os/ directory."""

    def __init__(self, root_dir: Path = None):
        self.root = root_dir or self._find_project_root()
        self.omoi_dir = self.root / ".omoi_os"

    def list_tickets(self) -> list[ParsedTicket]: ...
    def list_tasks(self) -> list[ParsedTask]: ...
    def get_ticket(self, ticket_id: str) -> ParsedTicket: ...
    def get_task(self, task_id: str) -> ParsedTask: ...
    def get_ticket_dependencies(self, ticket_id: str) -> dict: ...
    def get_task_dependencies(self, task_id: str) -> dict: ...
    def get_ready_tasks(self) -> list[ParsedTask]:
        """Return tasks with all dependencies satisfied."""
    def get_dependency_graph(self) -> dict:
        """Return full dependency graph for visualization."""
    def export_json(self) -> dict:
        """Export all specs as JSON for API calls."""
```

#### 2.2 Create API Client Module

**File**: `.claude/skills/spec-driven-dev/scripts/api_client.py`

```python
"""
Direct API client for OmoiOS backend (bypasses MCP server).

Usage:
    python api_client.py --sync-tickets    # Push local tickets to API
    python api_client.py --sync-tasks      # Push local tasks to API
    python api_client.py --list-remote     # List tickets/tasks from API
    python api_client.py --diff            # Show diff between local and remote
"""

import httpx
from parse_specs import SpecParser, ParsedTicket, ParsedTask

class OmoiOSClient:
    """Direct HTTP client for OmoiOS API."""

    def __init__(self, base_url: str = "http://localhost:18000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    # Ticket operations
    async def create_ticket(self, ticket: ParsedTicket) -> dict: ...
    async def update_ticket(self, ticket_id: str, data: dict) -> dict: ...
    async def get_ticket(self, ticket_id: str) -> dict: ...
    async def list_tickets(self, project_id: str = None) -> list[dict]: ...
    async def delete_ticket(self, ticket_id: str) -> bool: ...

    # Task operations
    async def create_task(self, task: ParsedTask) -> dict: ...
    async def update_task(self, task_id: str, data: dict) -> dict: ...
    async def get_task(self, task_id: str) -> dict: ...
    async def list_tasks(self, ticket_id: str = None) -> list[dict]: ...
    async def delete_task(self, task_id: str) -> bool: ...

    # Sync operations
    async def sync_from_local(self, parser: SpecParser) -> dict:
        """Push local .omoi_os/ files to API."""

    async def sync_to_local(self, output_dir: Path) -> dict:
        """Pull from API and write to local files."""

    async def diff(self, parser: SpecParser) -> dict:
        """Compare local files with remote API state."""
```

#### 2.3 Create CLI Tool

**File**: `.claude/skills/spec-driven-dev/scripts/spec_cli.py`

Unified CLI that combines parsing and API operations:

```bash
# List all tickets/tasks
uv run python spec_cli.py list tickets
uv run python spec_cli.py list tasks

# Get specific item
uv run python spec_cli.py get ticket TKT-001
uv run python spec_cli.py get task TSK-001

# Dependency operations
uv run python spec_cli.py deps TKT-001         # Show dependency tree
uv run python spec_cli.py ready                 # Show tasks ready to work on
uv run python spec_cli.py graph                 # Export dependency graph as DOT

# API operations (when backend is running)
uv run python spec_cli.py sync push             # Push local to API
uv run python spec_cli.py sync pull             # Pull from API to local
uv run python spec_cli.py sync diff             # Show differences

# Export operations
uv run python spec_cli.py export json > specs.json
uv run python spec_cli.py export yaml > specs.yaml
```

---

## Part 3: File Changes Summary

### Files to Modify

| File | Change |
|------|--------|
| `references/ticket_template.md` | Add YAML frontmatter with structured dependencies |
| `references/task_template.md` | Add YAML frontmatter with structured dependencies |
| `SKILL.md` | Add dependency management documentation section |

### Files to Create

| File | Purpose |
|------|---------|
| `scripts/parse_specs.py` | Parse .omoi_os/ files into structured data |
| `scripts/api_client.py` | Direct HTTP client for OmoiOS API |
| `scripts/spec_cli.py` | Unified CLI combining parsing + API operations |
| `scripts/models.py` | Shared dataclasses/Pydantic models |

### Existing Files to Update

| File | Change |
|------|--------|
| `scripts/generate_ids.py` | Add dependency-aware ID generation |
| `scripts/validate_specs.py` | Add dependency validation (circular detection) |

---

## Part 4: Implementation Steps

### Phase 1: Template Updates (30 min)
1. Update `ticket_template.md` with YAML frontmatter
2. Update `task_template.md` with YAML frontmatter
3. Update `SKILL.md` with dependency documentation
4. Update existing `.omoi_os/` files to use new format

### Phase 2: Parser Module (1-2 hours)
1. Create `scripts/models.py` with dataclasses
2. Create `scripts/parse_specs.py` with parser logic
3. Add YAML frontmatter parsing
4. Add markdown content extraction
5. Add dependency graph building
6. Add "ready tasks" logic

### Phase 3: API Client (1-2 hours)
1. Create `scripts/api_client.py` with HTTP client
2. Add ticket CRUD operations
3. Add task CRUD operations
4. Add sync operations (push/pull/diff)
5. Add error handling and retries

### Phase 4: CLI Tool (30 min)
1. Create `scripts/spec_cli.py` with argparse
2. Wire up all commands
3. Add output formatting (table, json, yaml)
4. Add dependency graph DOT export

### Phase 5: Validation Updates (30 min)
1. Update `validate_specs.py` with:
   - Circular dependency detection
   - Missing dependency validation
   - Orphaned task detection

---

## Part 5: Usage Examples

### After Implementation

```bash
# Parse local specs
uv run python .claude/skills/spec-driven-dev/scripts/spec_cli.py list tickets

# Output:
# ID        | Title                      | Status  | Blocked By | Blocks
# TKT-001   | Implement Auth             | backlog | -          | TKT-002, TKT-003
# TKT-002   | User Profile Page          | backlog | TKT-001    | -
# TKT-003   | Dashboard                  | backlog | TKT-001    | -

# Get ready tasks (all dependencies satisfied)
uv run python .claude/skills/spec-driven-dev/scripts/spec_cli.py ready

# Output:
# Ready tasks (no pending dependencies):
# - TSK-001: Add webhook_url to Project and Ticket Models
# - TSK-002: Create database migration

# Sync to backend API
uv run python .claude/skills/spec-driven-dev/scripts/spec_cli.py sync push

# Output:
# Syncing 1 tickets and 6 tasks to http://localhost:18000...
# Created TKT-001-webhook-notifications
# Created TSK-001, TSK-002, TSK-003, TSK-004, TSK-005, TSK-006
# Sync complete!
```

---

## Design Decisions (Confirmed)

1. **Frontmatter format**: YAML frontmatter with `---` delimiters
2. **No legacy support**: Files MUST have frontmatter (no inference from content)
3. **Sync behavior**: Create-only, but update descriptions if they differ from existing
4. **Validation strictness**: Strict - error on circular dependencies (blocks sync)
5. **Workflow**: **Markdown first** - write specs in markdown, use Python to parse/validate/visualize, then optionally sync to API

---

## Core Workflow: Markdown First

The key insight is that **markdown files are the source of truth**. The Python tools exist to:

1. **Parse** - Read all tickets/tasks from `.omoi_os/`
2. **Validate** - Check for circular dependencies, missing references
3. **Visualize** - Print dependency graph, show ready tasks
4. **Sync** - Push validated specs to backend API (create-only, update descriptions)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  1. Write       │────>│  2. Parse &      │────>│  3. Sync to     │
│  Markdown       │     │  Validate        │     │  Backend API    │
│  (.omoi_os/)    │     │  (Python CLI)    │     │  (optional)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                        │
        │                       ▼                        │
        │               ┌──────────────────┐             │
        │               │  Print Graph:    │             │
        │               │  - All tickets   │             │
        │               │  - All tasks     │             │
        │               │  - Dependencies  │             │
        │               │  - Ready tasks   │             │
        │               └──────────────────┘             │
        │                                                │
        └────────────────────────────────────────────────┘
                    Source of Truth
```

---

## Revised Implementation: Parse & Print First

### Primary Goal: Parse Markdown, Print Everything

Before any API integration, the core utility is:

```bash
# Parse all specs and print structured output
uv run python .claude/skills/spec-driven-dev/scripts/spec_cli.py show all

# Output:
# ══════════════════════════════════════════════════════════════
# TICKETS (3 total)
# ══════════════════════════════════════════════════════════════
#
# TKT-001: Implement Webhook Notifications
#   Status: backlog | Priority: HIGH | Estimate: L
#   Description: Implement webhook notifications for task lifecycle...
#   Tasks: TSK-001, TSK-002, TSK-003, TSK-004, TSK-005, TSK-006
#   Blocked By: (none)
#   Blocks: (none)
#
# ══════════════════════════════════════════════════════════════
# TASKS (6 total)
# ══════════════════════════════════════════════════════════════
#
# TSK-001: Add webhook_url to Project and Ticket Models
#   Parent: TKT-001 | Status: pending | Estimate: S
#   Description: Add webhook_url field to both Project and Ticket models.
#   Depends On: (none)
#   Blocks: TSK-002
#
# TSK-002: Create database migration
#   Parent: TKT-001 | Status: pending | Estimate: S
#   Description: Create Alembic migration for webhook_url fields.
#   Depends On: TSK-001
#   Blocks: TSK-003, TSK-004
#
# ... etc
#
# ══════════════════════════════════════════════════════════════
# DEPENDENCY GRAPH
# ══════════════════════════════════════════════════════════════
#
# TSK-001 (Add webhook_url...)
#   └─> TSK-002 (Create migration)
#       ├─> TSK-003 (WebhookDeliveryService)
#       │   └─> TSK-004 (WebhookNotificationService)
#       │       └─> TSK-006 (Tests)
#       └─> TSK-005 (Update API routes)
#           └─> TSK-006 (Tests)
#
# ══════════════════════════════════════════════════════════════
# READY TASKS (no pending dependencies)
# ══════════════════════════════════════════════════════════════
#
# - TSK-001: Add webhook_url to Project and Ticket Models
#
# ══════════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════════
#
# ✓ No circular dependencies detected
# ✓ All task references valid
# ✓ All ticket references valid
```

### Secondary Goal: API Sync (After Validation Passes)

```bash
# Only after parsing/validation succeeds, optionally sync
uv run python .claude/skills/spec-driven-dev/scripts/spec_cli.py sync push

# Output:
# Validating specs...
# ✓ 3 tickets, 6 tasks parsed
# ✓ No circular dependencies
#
# Syncing to http://localhost:18000...
# [CREATE] TKT-001: Implement Webhook Notifications
# [CREATE] TSK-001: Add webhook_url to Project and Ticket Models
# [CREATE] TSK-002: Create database migration
# [UPDATE DESC] TSK-003: WebhookDeliveryService (description changed)
# [SKIP] TSK-004: Already exists, description unchanged
# ...
#
# Sync complete: 5 created, 1 updated, 1 skipped
```

---

## Next Steps

1. ✅ Plan approved with design decisions
2. Begin Phase 1: Update templates with YAML frontmatter
3. Phase 2: Create parser that prints all tickets/tasks/dependencies
4. Phase 3: Add validation (circular dependency detection)
5. Phase 4: Add API sync (create-only, update descriptions)
