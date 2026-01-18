# Markdown Generation & Sync Architecture Plan

**Created**: 2025-01-16
**Status**: Draft
**Purpose**: Define standardized frontmatter schemas, markdown generation patterns, and sync-to-API workflows for spec-sandbox

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Core Philosophy](#core-philosophy)
3. [Frontmatter Schema Specifications](#frontmatter-schema-specifications)
4. [Markdown Generation Architecture](#markdown-generation-architecture)
5. [Sync-to-API Workflow](#sync-to-api-workflow)
6. [Evaluation Gates Integration](#evaluation-gates-integration)
7. [Implementation Plan](#implementation-plan)
8. [File Structure](#file-structure)

---

## Executive Summary

The spec-sandbox generates markdown files with YAML frontmatter as **verification artifacts**. These files serve dual purposes:

1. **Human Verification**: Easy to inspect if output is correct before pushing to backend
2. **API Sync Source**: Frontmatter provides structured data, markdown body provides descriptions

**Key Principle**: Frontmatter = Structured JSON-like data → API fields; Body = Rich description content

---

## Core Philosophy

### Markdown as Verification Artifacts

```
┌─────────────────────────────────────────────────────────────┐
│                    SPEC EXECUTION                           │
│                                                             │
│  EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC            │
│                                                             │
│  Each phase generates:                                      │
│  ├── Markdown files with frontmatter (verification)        │
│  └── Structured data for API sync                          │
│                                                             │
│  After verification:                                        │
│  └── Sandbox can be deleted (artifacts are ephemeral)      │
└─────────────────────────────────────────────────────────────┘
```

### The Frontmatter Pattern

Every generated file follows this pattern:

```markdown
---
# YAML frontmatter = structured data for API
id: TKT-001
title: Feature Title
status: backlog
priority: HIGH
# ... more fields
---

# Markdown body = description content
This becomes the `description` field in the API.

Rich markdown formatting is preserved:
- Lists
- Code blocks
- Tables
```

---

## Frontmatter Schema Specifications

### 1. PRD (Product Requirements Document)

**File**: `prd.md`

```yaml
---
id: PRD-{feature-name}
title: "{Feature Name} Product Requirements"
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: draft | review | approved
version: "1.0"
stakeholders:
  - role: Product Owner
    name: "{Name}"
  - role: Tech Lead
    name: "{Name}"
tags:
  - {tag1}
  - {tag2}
related_specs:
  - REQ-{FEATURE}-001
  - DES-{FEATURE}-001
---

# {Feature Name}

## Problem Statement
{Description of the problem being solved}

## Goals
- Goal 1
- Goal 2

## Non-Goals
- Non-goal 1

## Success Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| {metric} | {target} | {how measured} |
```

### 2. Requirements

**File**: `requirements/{feature-name}.md`

```yaml
---
id: REQ-{FEATURE}-{NNN}
title: "{Requirement Title}"
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: draft | review | approved
priority: CRITICAL | HIGH | MEDIUM | LOW
category: functional | non-functional | constraint
prd_ref: PRD-{feature-name}
stakeholder: "{Role/Name}"
verification_method: test | inspection | demonstration | analysis
acceptance_criteria:
  - criterion: "{Criterion 1}"
    testable: true
  - criterion: "{Criterion 2}"
    testable: true
dependencies:
  depends_on: []
  blocks: []
---

# {Requirement Title}

## Description
WHEN {trigger condition}
THE SYSTEM SHALL {required behavior}
SO THAT {business value}

## Rationale
{Why this requirement exists}

## Acceptance Criteria
1. Given {precondition}, when {action}, then {expected result}
2. Given {precondition}, when {action}, then {expected result}

## Notes
{Additional context or constraints}
```

### 3. Design Documents

**File**: `designs/{feature-name}.md`

```yaml
---
id: DES-{FEATURE}-{NNN}
title: "{Design Title}"
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: draft | review | approved
type: architecture | data_model | api | sequence | component
requirements:
  - REQ-{FEATURE}-001
  - REQ-{FEATURE}-002
components:
  - name: "{Component Name}"
    type: service | model | api | ui
  - name: "{Component Name}"
    type: service | model | api | ui
technologies:
  - "{Technology 1}"
  - "{Technology 2}"
risks:
  - risk: "{Risk description}"
    mitigation: "{Mitigation strategy}"
    severity: high | medium | low
---

# {Design Title}

## Overview
{High-level description of the design}

## Architecture
{Architecture description with diagrams if applicable}

## Data Model
{Data structures and relationships}

## API Design
{Endpoints, request/response formats}

## Error Handling
{Error scenarios and handling strategies}

## Security Considerations
{Security measures and considerations}
```

### 4. Tickets

**File**: `tickets/TKT-{NNN}.md`

```yaml
---
id: TKT-{NNN}
title: "{Ticket Title}"
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: backlog | in_progress | review | done
priority: CRITICAL | HIGH | MEDIUM | LOW
estimate: XS | S | M | L | XL
assignee: null
design_ref: designs/{feature-name}.md
requirements:
  - REQ-{FEATURE}-FUNC-001
  - REQ-{FEATURE}-FUNC-002
dependencies:
  blocked_by: []
  blocks: []
labels:
  - feature
  - backend
---

# {Ticket Title}

## Objective
{Clear statement of what this ticket accomplishes}

## Background
{Context and motivation}

## Scope
### In Scope
- Item 1
- Item 2

### Out of Scope
- Item 1

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes
{Implementation hints, gotchas, or considerations}

## Tasks
- TSK-{NNN}: {Task title}
- TSK-{NNN}: {Task title}
```

### 5. Tasks

**File**: `tasks/TSK-{NNN}.md`

```yaml
---
id: TSK-{NNN}
title: "{Task Title}"
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: pending | in_progress | review | done | blocked
priority: CRITICAL | HIGH | MEDIUM | LOW
estimate: XS | S | M | L | XL
assignee: null
parent_ticket: TKT-{NNN}
type: implementation | test | research | documentation | infrastructure
files_to_modify:
  - path/to/file1.py
  - path/to/file2.ts
dependencies:
  depends_on: []
  blocks: []
---

# {Task Title}

## Objective
{Clear, single-sentence objective}

## Description
{Detailed description of what needs to be done}

## Implementation Steps
1. Step 1
2. Step 2
3. Step 3

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Testing Requirements
- Unit tests for {component}
- Integration test for {workflow}

## Notes
{Additional context, gotchas, or references}
```

### 6. Summary

**File**: `summary.md`

```yaml
---
spec_id: "{UUID}"
title: "{Spec Title}"
created: {YYYY-MM-DD}
completed: {YYYY-MM-DD}
status: completed | failed | partial
phases_completed:
  - explore
  - requirements
  - design
  - tasks
  - sync
total_duration_seconds: {number}
artifacts:
  requirements_count: {number}
  designs_count: {number}
  tickets_count: {number}
  tasks_count: {number}
---

# Spec Execution Summary

## Overview
{Brief description of what was accomplished}

## Phase Results

### EXPLORE
- Duration: {seconds}s
- Key Findings: {summary}

### REQUIREMENTS
- Duration: {seconds}s
- Requirements Generated: {count}
- Evaluation Score: {score}

### DESIGN
- Duration: {seconds}s
- Components Designed: {count}
- Evaluation Score: {score}

### TASKS
- Duration: {seconds}s
- Tickets Created: {count}
- Tasks Created: {count}
- Evaluation Score: {score}

### SYNC
- Duration: {seconds}s
- Items Synced: {count}

## Artifacts Generated
- Requirements: {list}
- Designs: {list}
- Tickets: {list}
- Tasks: {list}
```

---

## Markdown Generation Architecture

### Generator Interface

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List

class MarkdownGenerator(ABC):
    """Base interface for markdown generators."""

    @abstractmethod
    async def generate_requirements(
        self,
        spec_context: Dict[str, Any],
        output_dir: Path,
    ) -> List[Path]:
        """Generate requirements markdown files."""
        pass

    @abstractmethod
    async def generate_design(
        self,
        requirements: Dict[str, Any],
        output_dir: Path,
    ) -> List[Path]:
        """Generate design markdown files."""
        pass

    @abstractmethod
    async def generate_tickets(
        self,
        design: Dict[str, Any],
        output_dir: Path,
    ) -> List[Path]:
        """Generate ticket markdown files."""
        pass

    @abstractmethod
    async def generate_tasks(
        self,
        tickets: Dict[str, Any],
        output_dir: Path,
    ) -> List[Path]:
        """Generate task markdown files."""
        pass
```

### Implementation Modes

#### 1. Claude Generator (Production)

Uses Claude SDK for intelligent content generation:

```python
class ClaudeMarkdownGenerator(MarkdownGenerator):
    """Uses Claude SDK for intelligent markdown generation."""

    def __init__(self, client: Anthropic):
        self.client = client

    async def generate_requirements(self, spec_context, output_dir):
        # Use Claude to generate rich requirements
        # Returns markdown files with proper frontmatter
        pass
```

#### 2. Mock Generator (Testing/Fallback)

Generates deterministic output for testing when SDK unavailable:

```python
class MockMarkdownGenerator(MarkdownGenerator):
    """Deterministic generator for testing without Claude SDK."""

    async def generate_requirements(self, spec_context, output_dir):
        # Generate template-based markdown
        # Useful for testing the pipeline without API calls
        pass
```

### Generator Factory

```python
def get_markdown_generator() -> MarkdownGenerator:
    """Get appropriate generator based on environment."""
    try:
        from anthropic import Anthropic
        client = Anthropic()
        return ClaudeMarkdownGenerator(client)
    except (ImportError, Exception):
        logger.warning("Claude SDK unavailable, using mock generator")
        return MockMarkdownGenerator()
```

### Output Directory Structure

```
{sandbox_output}/
├── prd.md                      # Product requirements document
├── summary.md                  # Execution summary
├── requirements/
│   ├── REQ-FEATURE-001.md
│   ├── REQ-FEATURE-002.md
│   └── index.md               # Requirements index
├── designs/
│   ├── architecture.md
│   ├── data_model.md
│   └── index.md               # Designs index
├── tickets/
│   ├── TKT-001.md
│   ├── TKT-002.md
│   └── index.md               # Tickets index
└── tasks/
    ├── TSK-001.md
    ├── TSK-002.md
    └── index.md               # Tasks index
```

---

## Sync-to-API Workflow

### Core Concept

The sync phase reads markdown files, parses frontmatter for structured data, and uses the markdown body as the description field.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Markdown File  │ ──► │  Parser Service  │ ──► │  Backend API    │
│                 │     │                  │     │                 │
│  ---            │     │  frontmatter →   │     │  POST /tickets  │
│  id: TKT-001    │     │    API fields    │     │  POST /tasks    │
│  title: ...     │     │                  │     │                 │
│  priority: HIGH │     │  body →          │     │                 │
│  ---            │     │    description   │     │                 │
│                 │     │                  │     │                 │
│  # Description  │     │                  │     │                 │
│  Rich content   │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Markdown Parser

```python
import yaml
from pathlib import Path
from typing import Tuple, Dict, Any

def parse_markdown_with_frontmatter(file_path: Path) -> Tuple[Dict[str, Any], str]:
    """Parse markdown file, extracting frontmatter and body.

    Args:
        file_path: Path to markdown file

    Returns:
        Tuple of (frontmatter_dict, markdown_body)
    """
    content = file_path.read_text()

    if not content.startswith('---'):
        return {}, content

    # Find end of frontmatter
    end_idx = content.find('---', 3)
    if end_idx == -1:
        return {}, content

    frontmatter_str = content[3:end_idx].strip()
    body = content[end_idx + 3:].strip()

    frontmatter = yaml.safe_load(frontmatter_str) or {}

    return frontmatter, body
```

### Sync Service

```python
class MarkdownSyncService:
    """Syncs markdown files to backend API."""

    def __init__(
        self,
        api_url: str,
        project_id: str,
        reporter: Reporter,
    ):
        self.api_url = api_url
        self.project_id = project_id
        self.reporter = reporter

    async def sync_tickets(self, tickets_dir: Path) -> SyncSummary:
        """Sync all ticket markdown files to backend."""
        summary = SyncSummary()

        for ticket_file in tickets_dir.glob("TKT-*.md"):
            frontmatter, body = parse_markdown_with_frontmatter(ticket_file)

            # Map frontmatter to API payload
            payload = {
                "title": frontmatter["title"],
                "description": body,  # Markdown body becomes description
                "priority": frontmatter.get("priority", "MEDIUM"),
                "project_id": self.project_id,
                "context": {
                    "spec_id": frontmatter.get("spec_id"),
                    "requirements": frontmatter.get("requirements", []),
                    "design_ref": frontmatter.get("design_ref"),
                },
            }

            result = await self._create_ticket(payload)
            summary.add_result(result)

        return summary

    async def sync_tasks(
        self,
        tasks_dir: Path,
        ticket_id_map: Dict[str, str],
    ) -> SyncSummary:
        """Sync all task markdown files to backend."""
        summary = SyncSummary()

        for task_file in tasks_dir.glob("TSK-*.md"):
            frontmatter, body = parse_markdown_with_frontmatter(task_file)

            # Resolve parent ticket to API ID
            parent_local_id = frontmatter.get("parent_ticket")
            parent_api_id = ticket_id_map.get(parent_local_id)

            if not parent_api_id:
                summary.add_error(f"Parent ticket {parent_local_id} not found")
                continue

            payload = {
                "ticket_id": parent_api_id,
                "title": frontmatter["title"],
                "description": body,  # Markdown body becomes description
                "task_type": frontmatter.get("type", "implementation"),
                "priority": frontmatter.get("priority", "MEDIUM"),
            }

            result = await self._create_task(payload)
            summary.add_result(result)

        return summary
```

### CLI Command

```bash
# Sync markdown files to backend API
spec-sandbox sync-markdown \
    --input-dir ./sandbox_output \
    --api-url https://api.omoios.dev \
    --project-id proj-123 \
    --api-key sk-...

# Dry-run mode (validate without creating)
spec-sandbox sync-markdown \
    --input-dir ./sandbox_output \
    --dry-run
```

---

## Evaluation Gates Integration

### Phase Evaluation Flow

Each phase must pass evaluation before proceeding:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   PHASE     │ ──► │  EVALUATE   │ ──► │   NEXT      │
│   OUTPUT    │     │   GATE      │     │   PHASE     │
│             │     │             │     │             │
│  Markdown   │     │  Score ≥    │     │  or RETRY   │
│  Files      │     │  Threshold  │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   EVENTS    │
                    │             │
                    │ phase_      │
                    │ completed   │
                    │ or          │
                    │ phase_      │
                    │ failed      │
                    └─────────────┘
```

### Evaluator for Markdown Output

```python
class MarkdownOutputEvaluator:
    """Evaluates generated markdown files for quality and completeness."""

    def evaluate_requirements(self, requirements_dir: Path) -> EvalResult:
        """Evaluate requirements markdown files."""
        files = list(requirements_dir.glob("REQ-*.md"))

        checks = []

        # Check: At least one requirement generated
        checks.append(EvalCheck(
            name="requirements_exist",
            passed=len(files) > 0,
            message=f"Found {len(files)} requirement files",
        ))

        # Check: All files have valid frontmatter
        for f in files:
            frontmatter, body = parse_markdown_with_frontmatter(f)
            checks.append(EvalCheck(
                name=f"frontmatter_valid_{f.stem}",
                passed=self._validate_requirement_frontmatter(frontmatter),
                message=f"Frontmatter validation for {f.name}",
            ))

            # Check: Body has meaningful content
            checks.append(EvalCheck(
                name=f"body_content_{f.stem}",
                passed=len(body) > 100,  # Minimum content length
                message=f"Body content check for {f.name}",
            ))

        passed_count = sum(1 for c in checks if c.passed)
        score = passed_count / len(checks) if checks else 0.0

        return EvalResult(
            score=score,
            passed=score >= 0.8,
            checks=checks,
        )

    def _validate_requirement_frontmatter(self, fm: dict) -> bool:
        """Validate requirement frontmatter has required fields."""
        required = ["id", "title", "status", "priority", "category"]
        return all(field in fm for field in required)
```

### Event Emission During Sync

```python
async def sync_with_events(
    self,
    output_dir: Path,
    reporter: Reporter,
) -> SyncSummary:
    """Sync markdown files with event emission."""

    await reporter.report(Event(
        event_type=EventTypes.SYNC_STARTED,
        spec_id=self.spec_id,
        data={"items_to_sync": self._count_files(output_dir)},
    ))

    # Sync tickets
    ticket_summary = await self.sync_tickets(output_dir / "tickets")

    for result in ticket_summary.results:
        await reporter.report(Event(
            event_type=EventTypes.TICKET_CREATED,
            spec_id=self.spec_id,
            data={
                "local_id": result.local_id,
                "api_id": result.api_id,
                "title": result.title,
            },
        ))

    # Sync tasks
    task_summary = await self.sync_tasks(
        output_dir / "tasks",
        ticket_summary.id_map,
    )

    for result in task_summary.results:
        await reporter.report(Event(
            event_type=EventTypes.TASK_CREATED,
            spec_id=self.spec_id,
            data={
                "local_id": result.local_id,
                "api_id": result.api_id,
                "ticket_api_id": result.ticket_api_id,
                "title": result.title,
            },
        ))

    await reporter.report(Event(
        event_type=EventTypes.SYNC_COMPLETED,
        spec_id=self.spec_id,
        data={
            "tickets_synced": ticket_summary.success_count,
            "tasks_synced": task_summary.success_count,
        },
    ))

    return SyncSummary.merge(ticket_summary, task_summary)
```

---

## Implementation Plan

### Phase 1: Schema Standardization (Current)

- [x] Define frontmatter schemas for all artifact types
- [x] Document field mappings to API
- [x] Create validation rules

### Phase 2: Generator Refactoring

- [ ] Create `MarkdownGenerator` interface
- [ ] Implement `ClaudeMarkdownGenerator` with schema compliance
- [ ] Implement `MockMarkdownGenerator` for testing
- [ ] Add generator factory with fallback logic

### Phase 3: Parser & Sync Service

- [ ] Implement `parse_markdown_with_frontmatter()`
- [ ] Create `MarkdownSyncService` class
- [ ] Add `sync-markdown` CLI command
- [ ] Implement dry-run mode for validation

### Phase 4: Evaluator Integration

- [ ] Create `MarkdownOutputEvaluator`
- [ ] Add frontmatter validation checks
- [ ] Add content quality checks
- [ ] Integrate with phase evaluation gates

### Phase 5: Event System Updates

- [ ] Ensure all sync operations emit events
- [ ] Update UI to display sync progress
- [ ] Add event filtering for sync-specific events

### Phase 6: Testing & Documentation

- [ ] Unit tests for parser
- [ ] Integration tests for sync workflow
- [ ] E2E test for full spec execution
- [ ] Update user documentation

---

## File Structure

### Proposed Module Organization

```
src/spec_sandbox/
├── generators/
│   ├── __init__.py
│   ├── base.py              # MarkdownGenerator interface
│   ├── claude_generator.py  # Claude SDK implementation
│   ├── mock_generator.py    # Testing fallback
│   └── factory.py           # Generator factory
├── parsers/
│   ├── __init__.py
│   └── markdown.py          # Frontmatter parser
├── sync/
│   ├── __init__.py
│   ├── service.py           # MarkdownSyncService
│   └── cli.py               # sync-markdown command
├── evaluators/
│   ├── __init__.py
│   ├── base.py              # Evaluator interface
│   ├── phases.py            # Phase evaluators
│   └── markdown.py          # Markdown output evaluator
└── schemas/
    ├── __init__.py
    ├── events.py            # Event types
    └── frontmatter.py       # Frontmatter Pydantic models
```

### Frontmatter Pydantic Models

```python
# schemas/frontmatter.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from enum import Enum

class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class Status(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class TicketFrontmatter(BaseModel):
    """Frontmatter schema for ticket markdown files."""
    id: str = Field(..., pattern=r"^TKT-\d{3}$")
    title: str
    created: date
    updated: date
    status: Status = Status.BACKLOG
    priority: Priority = Priority.MEDIUM
    estimate: str = Field(..., pattern=r"^(XS|S|M|L|XL)$")
    assignee: Optional[str] = None
    design_ref: Optional[str] = None
    requirements: List[str] = Field(default_factory=list)
    dependencies: dict = Field(default_factory=lambda: {
        "blocked_by": [],
        "blocks": [],
    })
    labels: List[str] = Field(default_factory=list)

class TaskFrontmatter(BaseModel):
    """Frontmatter schema for task markdown files."""
    id: str = Field(..., pattern=r"^TSK-\d{3}$")
    title: str
    created: date
    updated: date
    status: Status = Status.BACKLOG
    priority: Priority = Priority.MEDIUM
    estimate: str = Field(..., pattern=r"^(XS|S|M|L|XL)$")
    assignee: Optional[str] = None
    parent_ticket: str = Field(..., pattern=r"^TKT-\d{3}$")
    type: str = "implementation"
    files_to_modify: List[str] = Field(default_factory=list)
    dependencies: dict = Field(default_factory=lambda: {
        "depends_on": [],
        "blocks": [],
    })
```

---

## Summary

This document establishes:

1. **Standardized Frontmatter Schemas** - Consistent YAML structure across all artifact types
2. **Dual-Purpose Markdown** - Human-readable verification + machine-parseable sync source
3. **Generator Abstraction** - Claude SDK for production, mock for testing
4. **Sync-to-API Flow** - Frontmatter → API fields, Body → description
5. **Evaluation Gates** - Quality checks before proceeding to next phase
6. **Event Integration** - Real-time progress tracking during sync

The markdown files are ephemeral verification artifacts. The source of truth is the backend API. Markdown serves as an intermediate format that's easy to inspect, validate, and delete when done.
