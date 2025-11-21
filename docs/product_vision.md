# OmoiOS Product Vision

**Created**: 2025-01-XX  
**Status**: Product Vision Document  
**Purpose**: Single source of truth for OmoiOS product vision, target audience, and core value proposition

---

## Product Concept Statement

**OmoiOS is an autonomous engineering execution dashboard that turns feature requests into real shipped code.** Engineering teams connect a GitHub repository, describe what they want built, and OmoiOS automatically plans the work using a spec-driven approach (Requirements → Design → Tasks → Execution), discovers tasks as it progresses, builds features, tests them, and creates PRs—all while teams monitor progress in real time. Workflows branch and adapt based on agent discoveries through interconnected problem-solving flows. Users approve phase transitions and PRs at strategic points, while Guardian agents automatically detect and fix stuck workflows.

---

## Target Audience

### Primary Users
- **Engineering Managers & CTOs** at mid-size SaaS companies (10–100 engineers) needing consistent output without scaling headcount
- **Senior IC engineers** who want to offload repetitive planning and boilerplate implementation

### Secondary Users
- **Solo developers & startups** (2–5 people) needing to move fast with limited resources
- **Technical product managers** who need features built quickly

### User Characteristics
- **Technical background**: Comfortable with Git, GitHub, and development concepts
- **Role**: Engineering managers, senior ICs, or CTOs (not junior developers)
- **Expectation**: Monitor and approve at strategic points, not micromanage every step
- **Technical knowledge**: Don't need deep AI/ML knowledge; expect to use the system as a tool

---

## Core Value Proposition

### The Problem We Solve

**Primary pain point**: Coordination and planning burden—not having to think through every step.

The AI handles nuances, corrects itself, verifies work, and discovers new tasks as it goes. Users only watch at **specific points** (phase gates, PR reviews), not every step.

### Key Value Drivers

1. **Spec-Driven Development**: Structured approach with Requirements → Design → Tasks → Execution
2. **Autonomous Execution**: AI discovers work, corrects itself, verifies completion
3. **Strategic Oversight**: Users monitor at approval gates, not micromanage
4. **Self-Healing System**: Guardian agents monitor agent trajectories every 60 seconds, analyze alignment with goals using accumulated context, detect when agents drift, get stuck, violate constraints, miss mandatory steps, or become idle, and provide targeted steering interventions to keep workflows on track automatically. **Future enhancements**: Explicit constraint persistence validation, mandatory step validation, and specific steering type categorization will make interventions even more effective.
5. **Real-Time Visibility**: Complete transparency into agent activity and progress
6. **Adaptive Monitoring**: Monitoring loop learns how things work and adapts without explicit instructions
7. **Mutual Agent Monitoring**: Agents verify each other's work and ensure alignment with desired goals
8. **Interconnected Workflows**: Workflows branch and adapt based on agent discoveries—tickets thread context through phases, feedback loops ensure quality, and structure emerges from the problem

---

## Core Workflow: Spec-Driven Autonomous Engineering

### Workflow Phases

1. **Requirements Phase**: Structured requirements (EARS-style format with WHEN/THE SYSTEM SHALL patterns) capturing user stories and acceptance criteria
2. **Design Phase**: Architecture diagrams, sequence diagrams, data models, error handling, and implementation considerations
3. **Planning Phase**: Discrete, trackable tasks with dependencies and clear outcomes
4. **Execution Phase**: Code generation, self-correction, property-based validation, integration tests, PR generation

### Interconnected Problem-Solving Flows

OmoiOS workflows are **interconnected problem-solving graphs**, not linear pipelines. The workflow structure emerges from what agents discover as they work.

**Core Principle**: Phases are logical stages of problem-solving that communicate, branch, and loop based on discoveries. Agents spawn new work in any phase based on what they find, creating adaptive workflows that build themselves.

#### Interconnection Patterns

**1. Ticket Threading Through Phases**
- Tickets move through Kanban columns as work progresses through phases
- Phase 1 creates ticket → Passes to Phase 2 → Phase 2 moves to 'building' → Passes to Phase 3
- Tickets maintain context (comments, commits, decisions) across all phases
- All work for a component tracked on one ticket through its lifecycle

**2. Discovery Branching**
- Agents discover optimizations, bugs, missing requirements during execution
- Discovery spawns new investigation/implementation tasks in appropriate phases
- Original work continues in parallel—agents don't stop when they discover something
- Workflow branches dynamically: Phase 3 discovers optimization → Spawns Phase 1 investigation → Spawns Phase 2 implementation → New feature branch emerges

**3. Feedback Loops**
- Validation fails → Spawns fix task → Spawns revalidation → Loops until success
- Phase 3 validation discovers bugs → Spawns Phase 2 fix → Fix spawns Phase 3 revalidation
- Quality gates ensure iteration until requirements met
- Retry loops tracked in discovery system

**4. Phase Jumping**
- Implementation discovers missing requirements → Spawns Phase 1 clarification task
- Current task marked as blocked until clarification received
- Workflow adapts to reality—agents don't guess when requirements unclear
- Phase jumps tracked in discovery system for visibility

**5. Parallel Branching**
- Phase 1 identifies multiple components → Spawns multiple Phase 2 tasks in parallel
- All components built simultaneously by different agents
- Each component flows through phases independently
- Parallel execution maximizes throughput

**6. Done Definitions with Interconnection**
- Done definitions specify what connections to create:
  - "Phase 3 validation task created with ticket link"
  - "Ticket moved to 'building-done' status"
  - "If discovered issues: investigation tasks created"
- Agents can't complete phase without creating next phase's work
- Interconnection enforced through completion criteria

### Autonomous Agent Capabilities

**Discovery**: Agents discover new requirements, dependencies, optimizations, and issues as they work, expanding the original plan dynamically. Discoveries spawn new work in any phase based on what's needed.

**Verification**: Agents verify each other's work through property-based testing, spec compliance checking, and quality gates—ensuring implementation matches intent. Failed verification spawns fix tasks, creating feedback loops.

**Mutual Monitoring**: Agents monitor each other to ensure they're helping reach desired goals. Guardian agents provide trajectory analysis, Conductor service ensures system-wide coherence, and agents self-correct when they drift.

**Adaptive Learning**: The monitoring loop learns patterns from successful and failed workflows, discovering how things work and adapting strategies without explicit programming for every scenario. Interconnection patterns improve over time based on what works.

### User Journey

```
1. User connects GitHub repo (or creates new one)
2. User types: "Add payment processing with Stripe"
3. System analyzes codebase → Creates workflow → Generates spec
4. User reviews spec (Requirements → Design → Tasks) → Approves plan
5. System executes autonomously within phases
   - Agents work on tasks, discover optimizations/bugs/missing requirements
   - Discoveries spawn new tasks in appropriate phases
   - Workflow branches and adapts based on discoveries
   - Tickets thread through phases maintaining context
   - Feedback loops ensure quality (validation → fix → revalidate)
6. Real-time dashboard shows: agent status, workflow progress, tasks queue, Git activity, discovery events, workflow branching
7. User receives notifications for approval gates (phase transitions, PR reviews)
8. User approves/rejects → Workflow continues autonomously
9. Feature completed, verified, and merged
```

**Workflow Adaptation Example:**
```
Phase 2 agent implementing payment API discovers caching opportunity
  ↓
Spawns Phase 1 investigation task (continues original work)
  ↓
Investigation determines 40% performance improvement possible
  ↓
Spawns Phase 2 caching implementation task
  ↓
New feature branch emerges: Original payment API + Caching optimization
  ↓
Both branches execute in parallel
  ↓
Workflow structure emerged from discovery, not predefined plan
```

---

## Key Features

### Core MVP Features

1. **Repository Integration**: Connect GitHub/GitLab repos with OAuth, read/write access, PR creation

2. **Natural Language Feature Requests**: Users describe what they want; OmoiOS generates a multi-phase spec-driven implementation plan

3. **Spec-Driven Workflow**: 
   - Requirements Phase (EARS-style structured requirements)
   - Design Phase (architecture diagrams, sequence diagrams, data models)
   - Planning Phase (task breakdown with dependencies)
   - Execution Phase (autonomous code generation and validation)

4. **Spec Workspace**: Multi-tab workspace (Requirements | Design | Tasks | Execution) with spec switcher to switch between specs within each tab

5. **Kanban Board**: Visual workflow management with tickets/tasks organized by phase, real-time updates, drag-and-drop prioritization

6. **Dependency Graph**: Interactive visualization of task/ticket relationships with blocking indicators, animated as dependencies resolve

7. **Activity Timeline/Feed**: Chronological feed showing when specs/tasks/tickets are created, discovery events, phase transitions, agent interventions, approvals

8. **Autonomous Task Discovery Engine**: System expands the feature spec as it learns context from the codebase. Agents spawn new work in any phase based on discoveries, creating adaptive workflows that build themselves.

9. **Interconnected Workflow Patterns**:
   - **Ticket Threading**: Tickets move through phases maintaining context—Phase 1 creates ticket → Phase 2 builds → Phase 3 validates → All context preserved
   - **Discovery Branching**: Agents discover optimizations/bugs/missing requirements → Spawn investigation/implementation tasks → Workflow branches dynamically
   - **Feedback Loops**: Validation fails → Spawns fix task → Spawns revalidation → Loops until success
   - **Phase Jumping**: Implementation discovers missing requirements → Spawns Phase 1 clarification → Workflow adapts to reality
   - **Parallel Branching**: Phase 1 identifies multiple components → Spawns multiple Phase 2 tasks → All execute in parallel
   - **Structure Emerges**: Workflow structure emerges from discoveries, not predefined plans

10. **Agent Discovery, Verification, and Mutual Monitoring**:
    - **Discovery Agents**: Agents discover new requirements, dependencies, optimizations, and issues as they work. Discoveries spawn new work in appropriate phases while original work continues.
    - **Verification Agents**: Agents verify each other's work, run property-based tests, validate implementation against specs. Failed verification spawns fix tasks, creating feedback loops.
    - **Mutual Monitoring**: Agents monitor each other to ensure they're helping reach desired goals, not working against each other
    - **Adaptive Monitoring Loop**: Continuous monitoring that learns patterns, discovers how workflows succeed/fail, and adapts without explicit instructions. Learns effective interconnection patterns over time.

11. **Execution Pipeline with Phase Gates**: Flow through Planning → Implementation → Integration → Testing → PR Review → Merge with approval gates. Workflows branch and adapt within phases based on discoveries.

12. **Live Execution Dashboard**: Visual timeline + task list + logs + reasoning summaries with drill-down transparency. Shows workflow branching, discovery events, and interconnection patterns in real-time.

13. **Adaptive Monitoring Loop**: 
    - Learns patterns from successful and failed workflows
    - Discovers how agents work together effectively
    - Adapts monitoring strategies without explicit programming
    - Builds understanding of codebase patterns and development norms
    - Identifies when agents need help or redirection
    - Prevents the need to program every specific scenario

14. **Full Autonomous Feature Build Within Phases**: AI writes code, tests, self-corrects, retries, and runs integration tests. Workflows branch and adapt as agents discover new requirements, optimizations, and issues.

15. **PR Generation and Review Assistant**: Creates PRs, summarizes changes, prepares test coverage reports

16. **Command Palette**: Linear-style command palette (Cmd+K) for quick navigation across specs, tasks, workflows, and logs

17. **Workflow Intervention Tools**: Pause/resume, "Add constraint", "Fix this path", "Regenerate this task"

18. **Agent Status Monitoring**: Live agent status (active, idle, stuck, failed), heartbeat indicators, Guardian intervention alerts with trajectory analysis showing alignment scores over time, constraint violations, and steering interventions

19. **Git Activity Integration**: Real-time commit feed, PR status and diff viewer, branch visualization, merge approval interface

20. **Discovery Events Visualization**: Why workflows branch, new task discoveries, context and reasoning for each discovery. Shows interconnection patterns: ticket threading, feedback loops, phase jumping, parallel branching

---

## Business Model

### SaaS Platform
- **Multi-tenant SaaS**: Organizations/teams have separate workspaces
- **Role-based access**: Admin (full control), Manager (approve/intervene), Viewer (monitor only)
- **Pricing**: Per organization/workspace (team-based) or per active workflow/agent runtime
- **Onboarding**: Self-serve for SaaS scalability

---

## Visual Design Direction

**Option A with elements of B: Linear/Arc style with Notion/Obsidian hybrid elements**

### Visual Foundation
- **Clean, minimal, white-space-heavy** (Linear/Arc aesthetic)
- **Structured block-based content** for specs (Notion-style blocks for requirements/design/tasks)
- **Collapsible sidebar** for spec navigation (Obsidian-style)
- **Modern SaaS look** that's professional and approachable
- **Light theme default** with smooth animations
- **Gentle shadows and subtle gradients** for depth

### Key Visual Requirements
- Kanban board and dependency graph: Clean, minimal style (Option A)
- Spec workspace: Structured blocks for requirements/design/tasks (Option B)
- Collapsible sidebar: Spec navigation within tabs (Option B)
- Activity timeline: Clean and scannable (Option A)
- Overall: Modern, polished SaaS feel that supports structured spec-driven workflows

---

## Technical Architecture (High-Level)

### Backend
- **FastAPI** REST API with MCP (Model Context Protocol) integration
- **PostgreSQL 18+** with vector extensions for semantic memory
- **Redis** pub/sub for real-time event broadcasting
- **OpenHands SDK** for agent execution in isolated workspaces
- **Multi-agent orchestration** with Guardian/Diagnostic agents

### Frontend
- **Next.js 15+** (React 18+) with App Router
- **ShadCN UI** (Radix UI + Tailwind CSS) for components
- **React Query** for server state with WebSocket integration
- **React Flow** for dependency graph visualization
- **Command palette** for quick navigation

### Spec Storage
- **OmoiOS database/storage** (not in repo files)
- Optional export to markdown/YAML for version control integration
- PDF export for compliance/documentation

---

## Adaptive Monitoring Loop Architecture

### Core Vision

The adaptive monitoring loop addresses the "agent SOFAR" problem—where systems require explicit programming for every scenario—by learning patterns and adapting strategies autonomously. Instead of programming every specific scenario, the system discovers how things work and adapts based on what it learns.

**Interconnection Philosophy**: Workflows are interconnected problem-solving graphs, not linear pipelines. Phases communicate, branch, and loop based on discoveries. The workflow structure emerges from the problem itself, not a predefined plan. Agents spawn new work in any phase based on what they discover, creating adaptive workflows that build themselves.

### Architecture Components

#### 1. Pattern Discovery Layer
- **Analyzes successful workflows** to extract reusable patterns and strategies
- **Identifies failure patterns** from stuck/failed workflows to learn what doesn't work
- **Uses semantic memory (RAG)** to find similar past experiences and reference successful strategies
- **Builds knowledge base** of effective patterns, intervention strategies, and coordination approaches
- **Learns codebase-specific norms** and development patterns unique to each project

#### 2. Adaptive Strategy Engine
- **Adjusts monitoring thresholds** based on learned patterns from similar workflows
- **Adapts intervention strategies** based on what worked before in similar situations
- **Modifies agent coordination patterns** based on discoveries about effective team dynamics
- **Evolves monitoring cadence** based on system behavior and workload patterns
- **Customizes quality gates** based on learned success criteria for different types of features

#### 3. Mutual Monitoring Framework
- **Guardian Agents**: Monitor individual agent trajectories every 60 seconds, analyze alignment with goals using accumulated context from entire conversation history, provide targeted interventions when agents drift, get stuck, violate constraints, miss mandatory steps, or become idle. Guardian builds trajectory summaries over time, tracks persistent constraints throughout the session (even if mentioned 20 minutes ago), validates phase instructions compliance including mandatory steps, and sends specific steering messages categorized by root cause (stuck, drifting, violating constraints, idle, missed steps) to keep agents on track. **Enhancement opportunities**: Explicit constraint persistence validation with specific violation messages, mandatory step validation from phase instructions, and idle detection when agents finish but don't update status.
- **Conductor Service**: Performs system-wide coherence analysis, detects duplicate work, ensures agents aren't working against each other
- **Verification Agents**: Cross-verify agent work, run property-based tests, validate implementation against specs, ensure quality gates
- **Discovery Agents**: Identify new requirements, dependencies, optimizations, and issues as work progresses, expanding plans dynamically

#### 4. Learning Feedback Loop
- **Successful interventions** → Store pattern in memory → Reuse similar strategies in future workflows
- **Failed interventions** → Learn what doesn't work → Avoid similar mistakes and adjust approaches
- **Agent discoveries** → Store in semantic memory → Reference in future workflows when similar contexts arise
- **Interconnection patterns** → Learn effective branching, feedback loops, phase jumping patterns → Improve workflow adaptation
- **Pattern evolution** → Update strategies as system learns → Continuously improve monitoring effectiveness
- **Cross-project learning** → Share patterns across projects → Build organizational knowledge base

### Key Implementation Files

**Core Services** (Already Exist):
- `omoi_os/services/monitoring_loop.py` - Orchestrates monitoring cycles every 60 seconds, coordinates Guardian and Conductor
- `omoi_os/services/intelligent_guardian.py` - LLM-powered trajectory analysis with alignment scoring (0.0-1.0), accumulated context building from entire conversation history, past summaries timeline, phase context integration, and steering intervention decisions
- `omoi_os/services/trajectory_context.py` - Builds accumulated understanding from conversation history, extracts persistent constraints, standing instructions, and journey tracking
- `omoi_os/services/conductor.py` - System-wide coherence analysis and duplicate detection
- `omoi_os/services/discovery.py` - Task discovery and workflow branching
- `omoi_os/services/memory.py` - Semantic memory for pattern storage and retrieval with hybrid search (semantic + keyword using RRF), automatic pattern extraction, memory type taxonomy (error_fix, discovery, decision, learning, warning, codebase_knowledge), and similarity search. **Enhancement opportunities**: Agent-accessible MCP tools (save_memory, find_memory), pre-loaded context at agent spawn, deduplication system, and enhanced metadata (tags, related_files, agent_id).
- `omoi_os/services/agent_output_collector.py` - Collects agent outputs for trajectory analysis
- `omoi_os/services/conversation_intervention.py` - Sends steering interventions to OpenHands conversations
- `omoi_os/services/embedding.py` - Embedding generation using OpenAI text-embedding-3-small (1536-dim) or local multilingual-e5-large (padded to 1536-dim)

### Next Steps for Implementation

#### Phase 0: Guardian Enhancement Opportunities (Immediate Improvements)

These enhancements will make OmoiOS's Guardian system even more effective at keeping agents on track, aligning with Hephaestus Guardian best practices:

1. **Explicit Constraint Persistence Validation**
   - Enhance Guardian analysis to explicitly validate that constraints persist throughout the entire session
   - Provide specific violation messages with context: "You're installing 'jsonwebtoken' package, but the constraint from Phase 1 says 'no external auth libraries'. Use Node.js built-in crypto module instead."
   - Update `guardian_analysis.md.j2` template to check constraint violations as a primary validation point

2. **Explicit Mandatory Step Validation**
   - Add explicit validation for mandatory steps from phase instructions
   - Parse phase instructions for `⚠️ MANDATORY:` markers or similar patterns
   - Detect when agents skip mandatory steps and provide specific guidance: "Phase instructions require: search_tickets() before creating new tickets. You created a ticket without searching."

3. **Specific Steering Type Categorization**
   - Enhance steering type system to explicitly categorize interventions by root cause:
     - **Stuck** - Same error appearing 5+ times
     - **Drifting** - Working on unrelated areas
     - **Violating Constraints** - Breaking rules from earlier conversation
     - **Idle** - Agent finished but hasn't updated status
     - **Missed Steps** - Agent skipped mandatory phase instructions
   - Provide more specific, actionable intervention messages based on steering type

4. **Enhanced Constraint Violation Detection**
   - Detect constraint violations with full context (constraint source, when it was set, what action violates it)
   - Generate Hephaestus-style specific violation messages that include alternatives
   - Track constraint violations as a primary steering trigger, not just in analysis details

5. **Explicit Idle Detection**
   - Detect when agents appear to have completed work but haven't called `update_task_status(status='done')`
   - Provide specific reminders: "You've completed JWT implementation and tests are passing. Please update task status to 'done' with update_task_status tool."
   - Categorize idle detection as a distinct steering type

**Benefits**: These enhancements will make Guardian interventions more specific, actionable, and effective at preventing common agent drift patterns, improving the self-healing capabilities of the system.

#### Phase 0.5: Memory System Enhancement Opportunities

These enhancements will enable true collective intelligence where agents learn from each other in real-time:

1. **Agent-Accessible MCP Tools**
   - Create `save_memory` MCP tool for agents to save discoveries during execution
     - Parameters: `content`, `agent_id`, `memory_type`, optional `tags`, `related_files`
     - Stores memory using existing `MemoryService.store_execution()`
     - Enables agents to share knowledge in real-time
   - Create `find_memory` MCP tool for agents to search memories semantically during execution
     - Parameters: `query`, `limit` (default 5), optional `memory_types` filter
     - Uses existing `MemoryService.search_similar()` with hybrid search
     - Returns top matching memories with similarity scores
   - Enable agents to learn from each other's discoveries in real-time
   - Example: Agent encounters error → calls `find_memory("PostgreSQL timeout")` → finds solution → calls `save_memory()` to share fix for future agents

2. **Pre-loaded Context at Agent Spawn**
   - Enhance agent spawn to pre-load top 20 most relevant memories based on task description
   - Embed memories in agent's initial system prompt
   - Cover 80% of agent needs upfront, reducing need for dynamic searches
   - Improve agent performance by starting with relevant context

3. **Deduplication System**
   - Add similarity threshold check (0.95) before storing new memories
   - Prevent redundant knowledge storage
   - Reduce storage costs and maintain uniqueness of insights
   - Store duplicates as metadata-only records

4. **Enhanced Metadata & Tags**
   - Add `tags` field (array of searchable tags) to TaskMemory model
   - Add `related_files` field (array of file paths) to TaskMemory model
   - Add `agent_id` field to track which agent created the memory
   - Improve searchability and context tracking

5. **Dual Storage Architecture (Optional)**
   - Consider separating metadata (PostgreSQL) from embeddings (dedicated vector DB)
   - Improve scalability for large memory sets
   - Note: Current PostgreSQL approach works well, this is optional optimization

**Benefits**: These enhancements will enable agents to share knowledge in real-time, reduce redundant work, and improve overall system intelligence through collective learning.

#### Phase 1: Pattern Storage and Retrieval
1. **Enhance MonitoringLoop** to store successful/failed patterns in MemoryService
   - Store intervention strategies that worked
   - Store patterns of successful agent coordination
   - Store failure patterns to avoid repeating mistakes

2. **Add pattern matching to IntelligentGuardian**
   - Find similar past trajectories using semantic search
   - Reference successful interventions for similar situations
   - Learn from past agent behavior patterns

#### Phase 2: Adaptive Strategy Learning
3. **Create adaptive strategy engine**
   - Adjust monitoring thresholds based on learned patterns
   - Adapt intervention types based on what worked before
   - Modify agent coordination patterns based on discoveries

4. **Implement feedback loop**
   - Track intervention success/failure rates
   - Update strategies based on outcomes
   - Learn codebase-specific norms and patterns

#### Phase 3: Cross-Agent Learning
5. **Enhance DiscoveryService** with pattern awareness
   - Learn what types of discoveries are common
   - Identify patterns in workflow branching
   - Adapt discovery strategies based on project type
   - Learn effective interconnection patterns (ticket threading, feedback loops, phase jumping)

6. **Improve ConductorService** with learned patterns
   - Better detect duplicate work using learned patterns
   - Optimize agent coordination based on successful team dynamics
   - Learn system-wide patterns that lead to success
   - Identify effective interconnection patterns across workflows

#### Phase 4: Advanced Adaptation
7. **Build organizational knowledge base**
   - Share patterns across projects within an organization
   - Learn organization-specific development norms
   - Build institutional memory of effective strategies

8. **Implement predictive monitoring**
   - Predict when agents might get stuck based on learned patterns
   - Proactively intervene before problems occur
   - Optimize workflow paths based on learned success patterns

### Benefits

- **Reduces programming burden**: System learns how to handle scenarios without explicit programming
- **Improves over time**: Gets better at monitoring and coordination as it learns patterns
- **Adapts to context**: Customizes strategies based on codebase, team, and project type
- **Prevents repeating mistakes**: Learns from failures and avoids similar issues
- **Scales knowledge**: Builds organizational memory that improves across all projects
- **Enables adaptive workflows**: Interconnection patterns allow workflows to build themselves based on discoveries
- **Maintains context**: Ticket threading preserves context through phases, enabling better decision-making

---

## Success Metrics

### User Experience
- Reduced time monitoring development (from hours to minutes)
- Faster delivery cycles (agents work 24/7 autonomously)
- Clear visibility into agent activity and progress
- Confidence that agents are working correctly and recovering from failures
- Ability to trust the system enough to approve PRs without manual review

### Business Metrics
- User adoption and retention
- Number of workflows completed successfully
- Average time from feature request to merged PR
- User satisfaction scores
- Cost per successful workflow completion

---

## Related Documents
- [Front-End Design](./design/frontend/project_management_dashboard.md) - Detailed UI/UX design
- [Architecture Overview](../CLAUDE.md#architecture-overview) - Technical architecture
- [Hephaestus-Inspired Workflow Enhancements](./implementation/workflows/hephaestus_workflow_enhancements.md) - Spec-driven workflow implementation

