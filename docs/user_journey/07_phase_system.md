# 7 Phase System

**Part of**: [User Journey Documentation](./README.md)

---
## Phase System Overview

### Default Phases

OmoiOS comes with **8 default phases** ready to use:

1. **PHASE_BACKLOG** - Initial ticket triage and prioritization
2. **PHASE_REQUIREMENTS** - Gather and analyze requirements
3. **PHASE_DESIGN** - Create technical design and architecture
4. **PHASE_IMPLEMENTATION** - Develop and implement features
5. **PHASE_TESTING** - Test and validate implementation
6. **PHASE_DEPLOYMENT** - Deploy to production
7. **PHASE_DONE** - Ticket completed (terminal)
8. **PHASE_BLOCKED** - Ticket blocked by external dependencies (terminal)

### Custom Phases

Users can create **custom phases** for specialized workflows:

**Example: Research Workflow**
- `PHASE_RESEARCH` - Investigate topic and identify approaches
- `PHASE_EVALUATION` - Evaluate approaches and document findings
- `PHASE_DOCUMENTATION` - Document research results

**Custom Phase Creation**:
1. Navigate to Project Settings → Phases Tab
2. Click "Create Custom Phase"
3. Define phase properties:
   - Phase ID (must start with `PHASE_`)
   - Name and description
   - Sequence order
   - Done definitions (completion criteria)
   - Phase prompt (agent instructions)
   - Expected outputs (artifact patterns)
   - Allowed transitions
4. Save phase (stored in database, reusable across projects)

### Phase Features

**Each Phase Includes**:
- **Done Definitions**: Concrete, verifiable completion criteria
  - Example: "Component code files created", "Minimum 3 test cases written"
- **Phase Prompt**: System instructions for agents
  - Loaded automatically into agent system messages
  - Guides agent behavior and decision-making
- **Expected Outputs**: Required artifacts
  - Example: `{"type": "file", "pattern": "src/**/*.py", "required": true}`
- **Allowed Transitions**: Structured phase flow
  - Controls normal workflow progression
  - Discovery-based spawning bypasses restrictions
- **Configuration**: Phase-specific settings
  - Timeouts, retry limits, WIP limits

### Discovery-Based Branching

**Adaptive Workflows**:
- Agents can spawn tasks in **ANY phase** via `DiscoveryService`
- Bypasses `allowed_transitions` restriction
- Enables Hephaestus-style free-form branching

**Example Flow**:
```
Phase 3 agent (testing API) discovers caching optimization
  ↓
Spawns Phase 1 investigation task (bypasses restrictions)
  ↓
Phase 1 agent investigates caching pattern
  ↓
Spawns Phase 2 implementation task
  ↓
New feature branch emerges (parallel to original work)
```

**Discovery Types**:
- `bug_found` → Spawn Phase 2 fix task
- `optimization_opportunity` → Spawn Phase 1 investigation → Phase 2 implementation
- `clarification_needed` → Spawn Phase 1 clarification task
- `security_issue` → Spawn Phase 1 analysis → Phase 2 fix
- `new_component` → Spawn Phase 2 implementation task

### Phase Overview Dashboard

**View**: `/projects/:projectId/phases`

**Features**:
- Phase cards showing:
  - Task counts (Total, Done, Active)
  - Active agents per phase
  - Discovery indicators (new branches spawned)
  - Phase status (active, completed, idle)
- "View Tasks" button → See phase-specific tasks
- "View Discoveries" button → See discovery events
- Real-time updates via WebSocket

### Phase Metrics

**Statistics Dashboard → Phases Tab**:
- Phase performance overview (tasks, completion rates)
- Phase efficiency metrics (average time, success rate)
- Phase bottlenecks (queue depth, WIP violations)
- Phase cost breakdown (LLM costs per phase)
- Discovery activity by phase (discoveries, branches spawned)

---


---

**Next**: See [README.md](./README.md) for complete documentation index.
