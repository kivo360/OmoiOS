# OmoiOS Product Vision

**Created**: 2025-01-XX  
**Status**: Product Vision Document  
**Purpose**: Single source of truth for OmoiOS product vision, target audience, and core value proposition

---

## Product Concept Statement

**OmoiOS is an autonomous engineering execution dashboard that turns feature requests into real shipped code.** Engineering teams connect a GitHub repository, describe what they want built, and OmoiOS automatically plans the work using a spec-driven approach (Requirements → Design → Tasks → Execution), discovers tasks as it progresses, builds features, tests them, and creates PRs—all while teams monitor progress in real time. Users approve phase transitions and PRs at strategic points, while Guardian agents automatically detect and fix stuck workflows.

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
4. **Self-Healing System**: Guardian agents detect and fix stuck workflows automatically
5. **Real-Time Visibility**: Complete transparency into agent activity and progress
6. **Adaptive Monitoring**: Monitoring loop learns how things work and adapts without explicit instructions
7. **Mutual Agent Monitoring**: Agents verify each other's work and ensure alignment with desired goals

---

## Core Workflow: Spec-Driven Autonomous Engineering

### Workflow Phases

1. **Requirements Phase**: Structured requirements (EARS-style format with WHEN/THE SYSTEM SHALL patterns) capturing user stories and acceptance criteria
2. **Design Phase**: Architecture diagrams, sequence diagrams, data models, error handling, and implementation considerations
3. **Planning Phase**: Discrete, trackable tasks with dependencies and clear outcomes
4. **Execution Phase**: Code generation, self-correction, property-based validation, integration tests, PR generation

### Autonomous Agent Capabilities

**Discovery**: Agents discover new requirements, dependencies, optimizations, and issues as they work, expanding the original plan dynamically.

**Verification**: Agents verify each other's work through property-based testing, spec compliance checking, and quality gates—ensuring implementation matches intent.

**Mutual Monitoring**: Agents monitor each other to ensure they're helping reach desired goals. Guardian agents provide trajectory analysis, Conductor service ensures system-wide coherence, and agents self-correct when they drift.

**Adaptive Learning**: The monitoring loop learns patterns from successful and failed workflows, discovering how things work and adapting strategies without explicit programming for every scenario.

### User Journey

```
1. User connects GitHub repo (or creates new one)
2. User types: "Add payment processing with Stripe"
3. System analyzes codebase → Creates workflow → Generates spec
4. User reviews spec (Requirements → Design → Tasks) → Approves plan
5. System executes autonomously within phases
6. Real-time dashboard shows: agent status, workflow progress, tasks queue, Git activity
7. User receives notifications for approval gates (phase transitions, PR reviews)
8. User approves/rejects → Workflow continues autonomously
9. Feature completed, verified, and merged
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

8. **Autonomous Task Discovery Engine**: System expands the feature spec as it learns context from the codebase

9. **Agent Discovery, Verification, and Mutual Monitoring**:
   - **Discovery Agents**: Agents discover new requirements, dependencies, optimizations, and issues as they work
   - **Verification Agents**: Agents verify each other's work, run property-based tests, validate implementation against specs
   - **Mutual Monitoring**: Agents monitor each other to ensure they're helping reach desired goals, not working against each other
   - **Adaptive Monitoring Loop**: Continuous monitoring that learns patterns, discovers how workflows succeed/fail, and adapts without explicit instructions

10. **Execution Pipeline with Phase Gates**: Flow through Planning → Implementation → Integration → Testing → PR Review → Merge with approval gates

11. **Live Execution Dashboard**: Visual timeline + task list + logs + reasoning summaries with drill-down transparency

12. **Adaptive Monitoring Loop**: 
    - Learns patterns from successful and failed workflows
    - Discovers how agents work together effectively
    - Adapts monitoring strategies without explicit programming
    - Builds understanding of codebase patterns and development norms
    - Identifies when agents need help or redirection
    - Prevents the need to program every specific scenario

11. **Full Autonomous Feature Build Within Phases**: AI writes code, tests, self-corrects, retries, and runs integration tests

12. **PR Generation and Review Assistant**: Creates PRs, summarizes changes, prepares test coverage reports

13. **Command Palette**: Linear-style command palette (Cmd+K) for quick navigation across specs, tasks, workflows, and logs

14. **Workflow Intervention Tools**: Pause/resume, "Add constraint", "Fix this path", "Regenerate this task"

15. **Agent Status Monitoring**: Live agent status (active, idle, stuck, failed), heartbeat indicators, Guardian intervention alerts

16. **Git Activity Integration**: Real-time commit feed, PR status and diff viewer, branch visualization, merge approval interface

17. **Discovery Events Visualization**: Why workflows branch, new task discoveries, context and reasoning for each discovery

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
- **Guardian Agents**: Monitor individual agent trajectories, analyze alignment with goals, provide interventions when agents drift
- **Conductor Service**: Performs system-wide coherence analysis, detects duplicate work, ensures agents aren't working against each other
- **Verification Agents**: Cross-verify agent work, run property-based tests, validate implementation against specs, ensure quality gates
- **Discovery Agents**: Identify new requirements, dependencies, optimizations, and issues as work progresses, expanding plans dynamically

#### 4. Learning Feedback Loop
- **Successful interventions** → Store pattern in memory → Reuse similar strategies in future workflows
- **Failed interventions** → Learn what doesn't work → Avoid similar mistakes and adjust approaches
- **Agent discoveries** → Store in semantic memory → Reference in future workflows when similar contexts arise
- **Pattern evolution** → Update strategies as system learns → Continuously improve monitoring effectiveness
- **Cross-project learning** → Share patterns across projects → Build organizational knowledge base

### Key Implementation Files

**Core Services** (Already Exist):
- `omoi_os/services/monitoring_loop.py` - Orchestrates monitoring cycles, coordinates Guardian and Conductor
- `omoi_os/services/intelligent_guardian.py` - LLM-powered trajectory analysis with alignment scoring
- `omoi_os/services/conductor.py` - System-wide coherence analysis and duplicate detection
- `omoi_os/services/discovery.py` - Task discovery and workflow branching
- `omoi_os/services/memory.py` - Semantic memory for pattern storage and retrieval
- `omoi_os/services/agent_output_collector.py` - Collects agent outputs for trajectory analysis

### Next Steps for Implementation

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

6. **Improve ConductorService** with learned patterns
   - Better detect duplicate work using learned patterns
   - Optimize agent coordination based on successful team dynamics
   - Learn system-wide patterns that lead to success

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

