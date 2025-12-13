# Sandbox Agents System

Documentation for running AI agents in isolated sandbox environments (Daytona) with full Git integration.

**Last Validated**: 2025-12-12 ✅

---

## 🚀 Getting Started

**New to this project?** Start here:

1. **[Development Workflow Guide](./10_development_workflow.md)** — Step-by-step instructions for using these docs to build features
2. **[Implementation Checklist](./06_implementation_checklist.md)** — Copy-pasteable test code and implementation for each phase

The workflow guide explains *how* to use these documents practically. The checklist contains the actual code to copy.

---

## 🎯 Two-Track Implementation Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MVP → FULL INTEGRATION ROADMAP                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MVP TRACK (Start Here!)             FULL INTEGRATION (Build On MVP)       │
│  ────────────────────────            ────────────────────────────────       │
│  Phases 0-3.5                        Phases 4-7                             │
│  ~14-17 hours (~2 days)              +20-30 hours (~3-5 days)              │
│                                                                             │
│  ✅ Event streaming to frontend      ✅ Database persistence                │
│  ✅ Message injection works          ✅ Branch workflow automation          │
│  ✅ Basic Guardian intervention      ✅ Full Guardian integration           │
│  ✅ Task timeout handling            ✅ Heartbeat-based health              │
│  ✅ GitHub repo clone on startup     ✅ Fault tolerance integration         │
│                                      ✅ RestartOrchestrator integration     │
│                                                                             │
│  WHY MVP FIRST:                                                             │
│  • Validates core assumptions quickly                                      │
│  • Creates extension points for Full Integration                           │
│  • NOT a parallel system - Full Integration builds on MVP code             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Documents

| # | Document | Description | Track | Status |
|---|----------|-------------|-------|--------|
| 01 | [Architecture](./01_architecture.md) | System design for real-time agent communication | Both | 📋 Design |
| 02 | [Gap Analysis](./02_gap_analysis.md) | What we have vs. what we need | Both | ✅ Validated |
| 03 | [Git Branch Workflow](./03_git_branch_workflow.md) | Branch management, PR workflow (Musubi) | Full | 📋 Design |
| 04 | [Communication Patterns](./04_communication_patterns.md) | HTTP patterns, **security, rate limiting** | Both | 📋 Design |
| 05 | [HTTP API Migration](./05_http_api_migration.md) | MCP→HTTP mapping, new routes | Both | 📋 Design |
| 06 | [Implementation Checklist](./06_implementation_checklist.md) | ⭐ **Test-driven implementation plan** | Both | 🆕 NEW |
| 07 | [Existing Systems Integration](./07_existing_systems_integration.md) | Guardian, Registry, Fault Tolerance | Full | 🆕 NEW |
| 08 | [Frontend Integration](./08_frontend_integration.md) | UI components, WebSocket hooks, **+ Rich Activity Feed spec** | Full | 🆕 NEW |
| 09 | [Rich Activity Feed Architecture](./09_rich_activity_feed_architecture.md) | ⭐ **Future**: Tool events, diffs, streaming | Future | 🔮 POST-MVP |
| 10 | [Development Workflow Guide](./10_development_workflow.md) | 🚀 **Start Here**: How to use these docs | Both | 🆕 NEW |

### Status Legend
- 📋 Design - Design document, not yet validated
- ✅ Validated - Cross-referenced against codebase
- 🆕 NEW - Recently added
- ⏳ In Progress - Implementation underway
- 🔮 POST-MVP - Future enhancement (implement after MVP validated)

---

## Reading Order

### For MVP (Quick Start)
1. **Development Workflow Guide** - 🚀 **Start here** - How to use these docs
2. **Gap Analysis** - See what's already built (85% exists!) ✅
3. **Implementation Checklist** - ⭐ Phases 0-3.5 test code & implementation
4. **Architecture** - Reference as needed

### For Full Integration
5. **Existing Systems Integration** - Understand Guardian, Fault Tolerance
6. **Implementation Checklist** - Phases 4-7
7. **Git Workflow** - Branch/PR automation details
8. **Frontend Integration** - UI components and WebSocket hooks (Optional)

### For Future Enhancements (Post-MVP)
9. **Rich Activity Feed Architecture** - Tool events, file diffs, streaming (Optional)

---

## Quick Start for Implementation

> 📖 **For detailed instructions, see [Development Workflow Guide](./10_development_workflow.md)**

```bash
# 1. Setup environment
cd backend && uv sync

# 2. Run existing infrastructure tests (Phase 0)
pytest tests/integration/ -v -k "websocket or event_bus"

# 3. If Phase 0 passes, proceed with Phase 1
# See 06_implementation_checklist.md for copy-pasteable code
```

---

## Implementation Summary

### MVP Track (Phases 0-3.5) - Get Working Fast

| Phase | Effort | Description | Gate |
|-------|--------|-------------|------|
| Phase 0 | 1-2h | Validate existing infrastructure | Tests pass |
| Phase 1 | 2-3h | Sandbox event callback endpoint | Tests pass |
| Phase 2 | 4-6h | Message injection endpoints | Tests pass |
| Phase 3 | 4h | Worker script updates | Tests pass |
| Phase 3.5 | 3-4h | **GitHub clone integration** | 🎉 **MVP Complete** |

**MVP Total**: 14-17 hours (~2 days)

### Full Integration Track (Phases 4-7) - Production Ready

| Phase | Effort | Description | Gate |
|-------|--------|-------------|------|
| Phase 4 | 4-6h | Database persistence | Tests pass |
| Phase 5 | 10-15h | Branch workflow service | Tests pass |
| Phase 6 | 6-8h | Guardian & systems integration | Tests pass |
| **Phase 7** | 8-12h | Fault tolerance integration | 🎉 **Full Integration** |

**Full Total**: 38-50 hours (~1 week)

---

## Key Concepts

- **Daytona**: Cloud sandbox technology for isolated agent execution
- **BranchWorkflowService**: Manages ticket → branch → PR → merge lifecycle
- **HTTP over MCP**: Use simple HTTP for task/status operations (more reliable)
- **MVP Extension Points**: MVP code creates hooks that Full Integration uses
- **Hook-Based Intervention**: PreToolUse hooks enable sub-second message injection (vs polling)

---

## Sandbox Lifecycle States

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SANDBOX LIFECYCLE STATE MACHINE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐     spawn()      ┌──────────┐    agent starts   ┌──────────┐ │
│  │ PENDING  │ ───────────────► │ CREATING │ ────────────────► │ RUNNING  │ │
│  └──────────┘                  └──────────┘                   └──────────┘ │
│       │                              │                              │       │
│       │                              │ creation fails               │       │
│       │                              ▼                              │       │
│       │                        ┌──────────┐                        │       │
│       │                        │  FAILED  │ ◄──────────────────────┤       │
│       │                        └──────────┘   agent crashes/       │       │
│       │                              ▲        timeout              │       │
│       │                              │                              │       │
│       │                              │                              ▼       │
│       │                              │                        ┌──────────┐ │
│       │                              │                        │COMPLETING│ │
│       │                              │                        └──────────┘ │
│       │                              │                              │       │
│       │                              │                              │       │
│       │                              │                              ▼       │
│       │                              │                        ┌──────────┐ │
│       └──────────────────────────────┴───────────────────────►│COMPLETED │ │
│              manual cancel                                     └──────────┘ │
│                                                                             │
│  STATE TRANSITIONS:                                                         │
│  ─────────────────                                                          │
│  PENDING → CREATING   : DaytonaSpawnerService.spawn_sandbox()               │
│  CREATING → RUNNING   : Worker script starts, first heartbeat               │
│  CREATING → FAILED    : Daytona API error, timeout                          │
│  RUNNING → COMPLETING : Task marked done, creating PR                       │
│  RUNNING → FAILED     : Agent crash, Guardian timeout                       │
│  COMPLETING → COMPLETED: PR created successfully                            │
│  COMPLETING → FAILED   : PR creation fails                                  │
│  * → COMPLETED        : Manual cancellation                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ Critical Issues Identified

| Issue | Status | Resolution |
|-------|--------|------------|
| Missing `sandbox_id` on Task model | 📋 Documented | See [Gap Analysis #4](./02_gap_analysis.md) - Fix in Phase 6 |
| Guardian can't intervene with sandbox agents | 📋 Documented | See [Gap Analysis #5](./02_gap_analysis.md) - Fix in Phase 6 |
| Fault tolerance not sandbox-aware | 📋 Documented | See [07_existing_systems_integration.md](./07_existing_systems_integration.md) - Phase 7 |
| Polling-based intervention latency | ✅ Resolved | Hook-based injection designed in [04_communication_patterns.md](./04_communication_patterns.md) |
| SDK API correctness | ✅ Resolved | Fixed in [02_gap_analysis.md](./02_gap_analysis.md) - Gap #8 |

See [02_gap_analysis.md](./02_gap_analysis.md) for full details and risk assessments.
