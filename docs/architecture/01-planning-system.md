# Part 1: The Planning System

> Extracted from [ARCHITECTURE.md](../../ARCHITECTURE.md) — see hub doc for full system overview.

## Purpose

Convert a high-level feature idea into structured, executable work units.

## Location

```md
subsystems/spec-sandbox/src/spec_sandbox/
├── worker/state_machine.py      # Main orchestrator
├── prompts/phases.py            # Phase-specific prompts
├── evaluators/phases.py         # Quality gate evaluators
├── reporters/http.py            # Event streaming to backend
└── sync/service.py              # Sync artifacts to API
```

## Phase Flow

```md
EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE
   │        │         │           │        │       │
   ▼        ▼         ▼           ▼        ▼       ▼
 Codebase  Product   EARS      Architecture  TKT/TSK  Validation
 Analysis  Reqs Doc  Format    + API Specs   IDs      + Sync
```

## Phase Details

| Phase | Purpose | Output |
|-------|---------|--------|
| **EXPLORE** | Analyze codebase + gather discovery questions | `codebase_summary`, `tech_stack`, `discovery_questions`, `feature_summary` |
| **PRD** | Product Requirements Document | `goals`, `user_stories`, `scope`, `risks`, `success_metrics` |
| **REQUIREMENTS** | EARS-format formal requirements | `requirements[]` with `WHEN [trigger], THE SYSTEM SHALL [action]` |
| **DESIGN** | Architecture, API specs, data models | `components[]`, `data_models[]`, `api_endpoints[]`, `architecture_diagram` |
| **TASKS** | Tickets (TKT-NNN) and Tasks (TSK-NNN) | `tickets[]`, `tasks[]` with dependencies and estimates |
| **SYNC** | Validate traceability and sync to API | `coverage_matrix`, `traceability_stats`, `ready_for_execution` |

## Phase Evaluators (Quality Gates)

Each phase has an evaluator that scores the output (0.0 - 1.0). If score < threshold (0.7), the phase retries with feedback.

**Example: RequirementsEvaluator scoring:**

- `structure`: 20% - Required fields present
- `normative_language`: 20% - Uses SHALL/SHOULD/MAY
- `ears_format`: 15% - WHEN/SHALL patterns
- `acceptance_criteria`: 20% - 2+ criteria per requirement
- `id_format`: 5% - REQ-FEATURE-CATEGORY-NNN format

## Incremental Work Pattern (Critical)

All phases follow incremental writing to prevent data loss:

```python
# WRONG - One massive write at the end
[... do all analysis ...]
Write(entire_file)  # If this fails, everything is lost!

# CORRECT - Incremental writes
[... analyze first area ...]
Write(file, first_5_requirements)
[... analyze second area ...]
Edit(file, append next_5_requirements)  # Progress preserved
```

## Key Files

| File | Purpose |
|------|---------|
| `subsystems/spec-sandbox/src/spec_sandbox/worker/state_machine.py` | Main spec orchestrator |
| `subsystems/spec-sandbox/src/spec_sandbox/prompts/phases.py` | Phase prompts (1500 lines) |
| `subsystems/spec-sandbox/src/spec_sandbox/evaluators/phases.py` | Quality gates |

## Related Documentation

- [Spec-Sandbox Subsystem Strategy](spec_sandbox_subsystem_strategy.md) — extraction strategy for independent subsystem
