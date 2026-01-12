# Spec-Driven Development Documentation

This directory contains documentation for the spec-driven development workflow system.

## Overview

Spec-driven development allows users to go from **idea → spec → automated execution** without creating tickets that clutter the kanban board.

## Documents

| Document | Description |
|----------|-------------|
| [architecture.md](./architecture.md) | Complete system architecture and flow tracing |
| [implementation-gaps.md](./implementation-gaps.md) | Current gaps and what needs to be built |
| [activation-guide.md](./activation-guide.md) | How to activate each workflow path |
| [command-page-integration.md](./command-page-integration.md) | **Priority**: Google-like entry point from command page |
| [sandbox-execution.md](./sandbox-execution.md) | **CRITICAL**: Sandbox vs API process execution issue |

## Quick Summary

### Two Existing Paths (as of 2025-01)

1. **Prompt Injection Path**: Agent gets `spec_driven_dev_prompt` telling it to manually create specs
2. **SpecStateMachine Path**: Programmatic multi-phase execution (requires pre-existing spec_id)

### The Gap

There's no direct path from "user idea" → "create spec" → "run state machine" without going through tickets.

### Desired Flow (Command Page)

```
Command Page (type idea, select "Spec-Driven", hit Enter)
    ↓
POST /api/v1/specs/launch (creates spec + starts execution)
    ↓
Redirect to Spec Detail Page
    ↓
SpecStateMachine runs phases:
    EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE
    ↓
User watches progress, reviews artifacts
```

**Key insight**: Command page is like Google - simple, type and go. No tickets needed.

## Related Code

- `omoi_os/workers/spec_state_machine.py` - Multi-phase state machine
- `omoi_os/workers/claude_sandbox_worker.py` - Sandbox worker with state machine integration
- `omoi_os/services/daytona_spawner.py` - Sandbox spawning (including `spawn_for_phase`)
- `omoi_os/api/routes/specs.py` - Spec CRUD and execution endpoints
- `omoi_os/sandbox_skills/spec-driven-dev/SKILL.md` - Agent prompt for spec-driven work
