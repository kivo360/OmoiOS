# OmoiOS Landing Page Enhancement Guide

**Created**: 2025-12-22
**Status**: Design Document
**Purpose**: Transform the landing page from a minimal SaaS template into a high-conversion, technically credible autonomous engineering platform showcase

---

## Executive Summary

The current OmoiOS landing page is a clean "Minimalist SaaS" start, but lacks the **technical weight** and **visual proof** needed to convince engineers that this is a heavy-duty autonomous platform rather than just a wrapper.

This document provides a comprehensive implementation guide with:
- Component specifications
- Copy requirements
- Design system updates
- Visual mockup descriptions

---

## 1. Hero Section: "Show, Don't Tell"

### Current State
Static headline with generic CTA buttons. No visual proof of autonomy.

### Enhanced Design

#### 1.1 Dynamic Headline Options

Replace the current headline with outcome-focused copy:

**Option A (Recommended):**
```
Ship features while you sleep
From PRD to Pull Request—no babysitting required.
```

**Option B:**
```
From PRD to Pull Request in one command
Autonomous agents that plan, code, test, and ship.
```

**Option C:**
```
Unsupervised Engineering at Scale
Stop prompting. Start shipping.
```

#### 1.2 Agent Terminal Component

Add a secondary visual next to/below the headline—a faux-terminal or code editor window showing an agent "thinking," "browsing," and "committing code" in real-time.

**Component: `AgentTerminal`**

```tsx
// frontend/components/landing/AgentTerminal.tsx

interface TerminalEntry {
  timestamp: string;     // e.g., "02:47 AM"
  agentId: string;       // e.g., "Agent-Architect"
  action: string;        // e.g., "Analyzing requirements..."
  status: "thinking" | "coding" | "testing" | "committing";
}
```

**Animation Sequence** (loops every 15-20 seconds):
1. `[02:47:12]` Agent-Architect: "Analyzing user story → Breaking into 5 tasks..."
2. `[02:47:45]` Agent-Developer-1: "Implementing auth middleware..."
3. `[02:48:22]` Agent-Developer-2: "Writing unit tests for /api/login..."
4. `[02:49:01]` Agent-Developer-1: "✓ Tests passing (12/12)"
5. `[02:49:33]` Agent-Orchestrator: "Opening PR #147: 'Add JWT authentication'"

**Visual Style:**
- Dark terminal background (`#0D0D0D`)
- Terminal green accent (`#00FF41`) for success states
- JetBrains Mono font
- Subtle typing animation with cursor
- Status indicators (pulsing dots for active agents)

#### 1.3 Secondary CTA

Add a "Watch it build" button that opens a 30-second high-speed demo modal/video.

```tsx
<Button variant="outline" size="lg">
  <PlayIcon className="mr-2 h-4 w-4" />
  Watch it build (30s)
</Button>
```

---

## 2. Ticket Lifecycle Journey (Hero Visual)

**This is the centerpiece visualization** — showing a single ticket traveling through the OmoiOS pipeline step-by-step, proving the end-to-end autonomous workflow with **phase-specific instructions** injected at each stage.

### 2.1 Concept: The Ticket's Journey with Phase Instructions

A horizontal "journey rail" showing a ticket card moving through your actual phases. The key differentiator: **when a ticket enters a phase, we visualize the phase instructions being "downloaded" into the agent**.

**Component: `TicketJourney`**

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                     │
│   "Add user authentication"                                                         │
│                                                                                     │
│   ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────┐ │
│   │🔍 ANALYZE│ ───▶ │🔨 BUILD  │ ───▶ │🧪 TEST   │ ───▶ │🚀 DEPLOY │ ───▶ │✅DONE│ │
│   │          │      │          │      │          │      │          │      │      │ │
│   │ Extract  │      │ 3 Agents │      │ Validate │      │ Ship it  │      │ Live │ │
│   │ + Spawn  │      │ Parallel │      │ + Loop   │      │          │      │      │ │
│   └──────────┘      └──────────┘      └──────────┘      └──────────┘      └──────┘ │
│        │                 │                 │                                        │
│        │                 │    ┌────────────┘  Feedback Loop                        │
│        │                 │◀───┤ Bug found? Spawn fix task                          │
│        │◀────────────────┼────┘ back to BUILD phase                                │
│        │ Clarification   │                                                          │
│        │ needed?         │                                                          │
│                                                                                     │
│   [0:00:00]         [0:02:30]         [0:06:45]         [0:08:12]         [0:08:33]│
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 The Five Actual Phases (From Your Codebase)

| Phase ID | Board Column | What Happens | Agent Role |
|----------|--------------|--------------|------------|
| `PHASE_REQUIREMENTS` | 🔍 Analyzing | Extract requirements from PRD, spawn implementation tasks | Architect |
| `PHASE_IMPLEMENTATION` | 🔨 Building | Build component, write 3+ tests, spawn validation task | Developer |
| `PHASE_TESTING` | 🧪 Testing | Run integration tests, validate or spawn fix tasks | QA Engineer |
| `PHASE_DEPLOYMENT` | 🚀 Deploying | Deploy to production, enable monitoring | DevOps |
| `PHASE_DONE` | ✅ Done | Terminal state - component complete | — |

### 2.3 Interactive Animation Sequence

The visualization animates through the journey in a loop (25-30 seconds total):

**Stage 1: REQUIREMENTS / 🔍 Analyzing (0:00 - 0:05)**
- Ticket card appears with title "Add user authentication"
- **Phase Instructions Panel slides in** with key bullets:
  - "Read the PRD carefully"
  - "Extract functional requirements"
  - "Create Phase 2 task for each component"
- **Done Criteria Checklist** appears, items tick off:
  - ✓ Requirements extracted
  - ✓ Components identified
  - ✓ Phase 2 tasks created
- Task cards "spawn" below: 5 small cards fan out with labels

**Stage 2: IMPLEMENTATION / 🔨 Building (0:05 - 0:15)**
- Ticket slides to Building column
- **New Phase Instructions load** (visual "download" effect):
  - "Move ticket to 'building' status"
  - "Implement core logic"
  - "Write 3+ test cases"
  - "If bugs found → spawn fix task"
- 3 agent avatars appear with pulsing status dots
- Progress bars animate on task cards
- **Done Criteria** ticks off as agent works:
  - ✓ Ticket status updated
  - ✓ Code files created
  - ✓ 3+ tests written
  - ◻ Tests passing...

**Stage 3: TESTING / 🧪 Testing (0:15 - 0:22)**
- Ticket moves to Testing column
- **QA Phase Instructions load**:
  - "Run integration tests"
  - "If PASS → create deployment task"
  - "If FAIL → spawn fix task to BUILD"
- **Feedback Loop Visualization**:
  - First run: Tests fail on 2 cases
  - Arrow animates back to BUILD phase
  - "Spawning fix task..." message
  - Fix completes, arrow returns to TESTING
  - Second run: All tests pass ✓

**Stage 4: DEPLOYMENT / 🚀 Deploying (0:22 - 0:26)**
- Ticket moves to Deploying column
- **DevOps Instructions load**:
  - "Deploy to production"
  - "Verify deployment health"
  - "Enable monitoring"
- Deployment animation (progress bar)

**Stage 5: DONE / ✅ Complete (0:26 - 0:30)**
- Ticket slides to Done column
- **Stats overlay** fades in:
  - "8 min 33 sec total"
  - "5 tasks completed"
  - "1 bug caught & fixed"
  - "847 lines • 24 tests"
- Subtle celebration effect (glow, not confetti)
- Loop resets

### 2.4 Component Interface

```tsx
// frontend/components/landing/TicketJourney.tsx

interface TicketJourneyProps {
  autoPlay?: boolean;
  speed?: "slow" | "normal" | "fast";
  showPhaseInstructions?: boolean;   // Show the instruction panel
  showDoneCriteria?: boolean;        // Show the checklist
  showFeedbackLoops?: boolean;       // Animate the loop-back arrows
  interactive?: boolean;
}

interface JourneyStage {
  id: "requirements" | "implementation" | "testing" | "deployment" | "done";
  phaseId: string;                   // e.g., "PHASE_REQUIREMENTS"
  boardColumn: string;               // e.g., "🔍 Analyzing"
  icon: ReactNode;
  duration: number;

  // Phase-specific content (from your YAML config)
  phaseInstructions: string[];       // Key bullets from phase_prompt
  doneCriteria: DoneCriterion[];     // From done_definitions
  canLoopBackTo?: string[];          // Feedback loop targets

  artifacts: Artifact[];
  agentRole: string;                 // "Architect", "Developer", "QA", "DevOps"
}

interface DoneCriterion {
  label: string;
  completed: boolean;
  animationDelay: number;            // When to tick this off
}

interface Artifact {
  type: "task" | "agent" | "pr" | "test" | "fix";
  label: string;
  status: "pending" | "active" | "complete" | "failed";
}
```

### 2.5 Phase Instructions Panel Design

When a ticket enters a phase, display the instructions the agent receives:

```
┌─────────────────────────────────────────────────────────┐
│  📜 PHASE INSTRUCTIONS                                  │
│  ───────────────────────────────────────────────────────│
│                                                         │
│  🔨 IMPLEMENTATION PHASE                                │
│                                                         │
│  Agent receives:                                        │
│  ┌─────────────────────────────────────────────────────┐│
│  │ • Move ticket to 'building' status                  ││
│  │ • Implement the core component logic                ││
│  │ • Write minimum 3 test cases                        ││
│  │ • If bugs discovered → spawn fix task               ││
│  │ • Create Phase 3 validation task when done          ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  Done when:                                             │
│  ✓ Ticket status = 'building'                          │
│  ✓ Code files created in src/                          │
│  ✓ 3+ tests written                                    │
│  ◻ Tests passing locally                               │
│  ◻ Validation task created                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.6 Feedback Loop Visualization

Show that the system self-corrects:

```
                    ┌─────────────────────────────────┐
                    │                                 │
                    ▼                                 │
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────┴─────┐
│ 🔍       │───▶│ 🔨       │───▶│ 🧪       │───▶│ 🚀       │
│ ANALYZE  │    │ BUILD    │◀───│ TEST     │    │ DEPLOY   │
└──────────┘    └────▲─────┘    └──────────┘    └──────────┘
     │               │                │
     │               │                │
     │   ┌───────────┴────────────────┘
     │   │  "Tests failed on 2 cases"
     │   │  "Spawning fix task..."
     │   │
     └───┤  "Requirements unclear"
         │  "Spawning clarification task..."
         │
    FEEDBACK LOOPS
    System self-corrects without human intervention
```

**Animation:** When the loop-back happens:
1. Red "X" appears on failing test
2. Dotted arrow animates backward to BUILD phase
3. "Spawning fix task..." label appears
4. Small fix-task card appears in BUILD
5. Arrow animates forward again
6. Green "✓" appears - tests now pass

### 2.7 Data Structure (Using Real Phase Data)

```tsx
const journeyData: JourneyStage[] = [
  {
    id: "requirements",
    phaseId: "PHASE_REQUIREMENTS",
    boardColumn: "🔍 Analyzing",
    icon: <SearchIcon />,
    duration: 5,
    agentRole: "Architect",
    phaseInstructions: [
      "Read the PRD carefully",
      "Extract functional and non-functional requirements",
      "Identify system components (auth, API, frontend, etc.)",
      "Create Phase 2 implementation task for each component",
    ],
    doneCriteria: [
      { label: "Requirements extracted", completed: false, animationDelay: 1000 },
      { label: "Components identified", completed: false, animationDelay: 2000 },
      { label: "Phase 2 tasks created", completed: false, animationDelay: 4000 },
    ],
    artifacts: [
      { type: "task", label: "JWT middleware", status: "pending" },
      { type: "task", label: "Login endpoint", status: "pending" },
      { type: "task", label: "Signup endpoint", status: "pending" },
    ],
  },
  {
    id: "implementation",
    phaseId: "PHASE_IMPLEMENTATION",
    boardColumn: "🔨 Building",
    icon: <HammerIcon />,
    duration: 10,
    agentRole: "Developer",
    phaseInstructions: [
      "Move ticket to 'building' status",
      "Implement the core component logic",
      "Write minimum 3 test cases",
      "If bugs found → spawn fix task (don't stop)",
      "Create Phase 3 validation task when done",
    ],
    doneCriteria: [
      { label: "Ticket status = 'building'", completed: false, animationDelay: 500 },
      { label: "Code files created", completed: false, animationDelay: 3000 },
      { label: "3+ tests written", completed: false, animationDelay: 6000 },
      { label: "Tests passing", completed: false, animationDelay: 8000 },
      { label: "Validation task created", completed: false, animationDelay: 9500 },
    ],
    canLoopBackTo: ["requirements"],  // Can spawn clarification tasks
    artifacts: [
      { type: "agent", label: "Agent-Dev-1", status: "active" },
      { type: "agent", label: "Agent-Dev-2", status: "active" },
    ],
  },
  {
    id: "testing",
    phaseId: "PHASE_TESTING",
    boardColumn: "🧪 Testing",
    icon: <FlaskIcon />,
    duration: 7,
    agentRole: "QA Engineer",
    phaseInstructions: [
      "Run integration tests",
      "Validate against requirements",
      "If PASS → create deployment task",
      "If FAIL → spawn fix task back to BUILD",
    ],
    doneCriteria: [
      { label: "Integration tests executed", completed: false, animationDelay: 2000 },
      { label: "Requirements validated", completed: false, animationDelay: 4000 },
      { label: "All tests passing", completed: false, animationDelay: 6000 },
    ],
    canLoopBackTo: ["implementation"],  // Feedback loop for bug fixes
    artifacts: [
      { type: "test", label: "24/24 passing", status: "complete" },
    ],
  },
  {
    id: "deployment",
    phaseId: "PHASE_DEPLOYMENT",
    boardColumn: "🚀 Deploying",
    icon: <RocketIcon />,
    duration: 4,
    agentRole: "DevOps",
    phaseInstructions: [
      "Verify all tests passing",
      "Deploy to production",
      "Verify deployment health",
      "Enable monitoring",
    ],
    doneCriteria: [
      { label: "Deployed successfully", completed: false, animationDelay: 2000 },
      { label: "Health check passed", completed: false, animationDelay: 3000 },
      { label: "Monitoring enabled", completed: false, animationDelay: 3500 },
    ],
    artifacts: [
      { type: "pr", label: "PR #147 merged", status: "complete" },
    ],
  },
  {
    id: "done",
    phaseId: "PHASE_DONE",
    boardColumn: "✅ Done",
    icon: <CheckCircleIcon />,
    duration: 3,
    agentRole: "—",
    phaseInstructions: ["Component successfully completed."],
    doneCriteria: [
      { label: "Component in production", completed: true, animationDelay: 0 },
    ],
    artifacts: [],
  },
];
```

### 2.8 Copy for Each Stage (Using Real Phase Language)

**🔍 Requirements / Analyzing:**
> "Architect Agent reads your PRD, extracts requirements, and spawns implementation tasks for each component discovered."

**🔨 Implementation / Building:**
> "Developer Agents build in parallel. Each writes code, tests, and spawns validation tasks. Bugs discovered? Fix tasks spawn automatically."

**🧪 Testing / Validation:**
> "QA Agent runs integration tests. If tests fail, fix tasks loop back to Build. No bugs slip through—the system self-corrects."

**🚀 Deployment:**
> "DevOps Agent deploys to production, verifies health, enables monitoring. Your code is live."

**✅ Done:**
> "Component complete. 8 minutes from PRD to production. You reviewed one PR."

---

## 2.9 Visual Effects & Animations

### 2.9.1 "Instruction Download" Effect

When a ticket enters a new phase, visualize the phase instructions being "injected" into the agent:

**Effect: Matrix-Style Code Rain (Subtle)**
- Terminal-green characters (`#00FF41`) rain down briefly
- Characters resolve into the instruction bullet points
- Duration: 0.8 seconds
- Inspiration: The Matrix code rain, but refined and brief

**Implementation:**
```tsx
// Animated text that "types in" each instruction
<motion.div
  initial={{ opacity: 0, y: -10 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.3, staggerChildren: 0.1 }}
>
  {instructions.map((instruction, i) => (
    <TypewriterText key={i} text={instruction} delay={i * 200} />
  ))}
</motion.div>
```

### 2.9.2 "Particle Flow" Between Phases

Show data/work flowing between phases as animated particles:

**Effect: Flowing Particles Along Rail**
- Small glowing dots flow along the connection lines
- Speed increases when ticket is actively moving
- Color: Terminal green (`#00FF41`) or phase-specific colors
- Particles accumulate at the active phase node

**Implementation (Framer Motion + Canvas):**
```tsx
<svg className="particle-rail">
  <motion.circle
    cx={particleX}
    cy={particleY}
    r={3}
    fill="#00FF41"
    animate={{
      cx: [startX, endX],
      opacity: [0, 1, 1, 0],
    }}
    transition={{
      duration: 2,
      repeat: Infinity,
      ease: "linear",
    }}
  />
</svg>
```

### 2.9.3 "Pulse Ring" on Active Phase

The currently active phase node pulses to show activity:

**Effect: Concentric Pulse Rings**
- 2-3 rings expand outward from the active phase node
- Rings fade as they expand
- Continuous pulse while phase is active
- Color: Phase-specific accent color

**CSS:**
```css
@keyframes pulse-ring {
  0% {
    transform: scale(1);
    opacity: 0.8;
  }
  100% {
    transform: scale(2.5);
    opacity: 0;
  }
}

.phase-node.active::before,
.phase-node.active::after {
  content: '';
  position: absolute;
  border: 2px solid var(--terminal-green);
  border-radius: 50%;
  animation: pulse-ring 2s ease-out infinite;
}

.phase-node.active::after {
  animation-delay: 0.5s;
}
```

### 2.9.4 "Task Spawn" Explosion Effect

When tasks are created (in Requirements phase), show them "exploding" outward:

**Effect: Card Burst**
- Task cards start stacked at center
- Cards burst outward in a fan pattern
- Each card has slight rotation and bounce
- Staggered timing for organic feel

**Implementation:**
```tsx
<motion.div
  variants={{
    hidden: { scale: 0, rotate: -10, opacity: 0 },
    visible: (i: number) => ({
      scale: 1,
      rotate: 0,
      opacity: 1,
      x: (i - 2) * 120,  // Fan out horizontally
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 20,
        delay: i * 0.1,
      },
    }),
  }}
  custom={index}
  initial="hidden"
  animate="visible"
>
  <TaskCard />
</motion.div>
```

### 2.9.5 "Feedback Loop" Arrow Animation

When tests fail and a fix task spawns back to BUILD:

**Effect: Animated Dashed Arrow**
- Dashed line draws itself backward (SVG stroke-dashoffset)
- Small "error" icon travels along the path
- "Spawning fix..." label fades in
- Arrow pulses red briefly, then resolves to green when fixed

**Implementation:**
```tsx
<motion.path
  d="M 400,200 C 350,250 250,250 200,200"  // Curved path back
  stroke="#FF4444"
  strokeWidth={2}
  strokeDasharray="8 4"
  initial={{ pathLength: 0 }}
  animate={{ pathLength: 1 }}
  transition={{ duration: 1, ease: "easeInOut" }}
/>

<motion.div
  className="error-icon"
  animate={{
    offsetDistance: ["0%", "100%"],
  }}
  transition={{ duration: 1.5, ease: "easeInOut" }}
  style={{ offsetPath: `path("M 400,200 C 350,250 250,250 200,200")` }}
>
  🔴
</motion.div>
```

### 2.9.6 "Done Criteria" Checkbox Animation

Checkboxes tick off with satisfying micro-interactions:

**Effect: Checkbox Draw + Bounce**
- Empty checkbox → checkmark draws itself (SVG path animation)
- Slight scale bounce on completion
- Green glow pulse
- Sound effect option (subtle "tick")

**Implementation:**
```tsx
<motion.svg viewBox="0 0 24 24">
  <motion.path
    d="M5 13l4 4L19 7"
    stroke="#00FF41"
    strokeWidth={3}
    fill="none"
    initial={{ pathLength: 0 }}
    animate={{ pathLength: 1 }}
    transition={{ duration: 0.3, ease: "easeOut" }}
  />
</motion.svg>

<motion.div
  animate={{ scale: [1, 1.2, 1] }}
  transition={{ duration: 0.3 }}
>
  ✓
</motion.div>
```

### 2.9.7 "Agent Avatar" Activity Indicators

Show agents actively working:

**Effect: Orbiting Activity Dots**
- Small dots orbit around agent avatars
- Speed varies based on activity level
- Multiple agents = multiple orbit systems
- Color indicates status (green=working, yellow=waiting, red=error)

**Implementation:**
```tsx
<div className="agent-avatar">
  <img src={agentIcon} />
  <motion.div
    className="orbit-dot"
    animate={{
      rotate: 360,
    }}
    transition={{
      duration: 2,
      repeat: Infinity,
      ease: "linear",
    }}
    style={{
      position: "absolute",
      width: 8,
      height: 8,
      borderRadius: "50%",
      backgroundColor: "#00FF41",
      transformOrigin: "20px 20px",  // Orbit radius
    }}
  />
</div>
```

### 2.9.8 "Completion" Celebration Effect

When the journey completes:

**Effect: Subtle Glow Expansion (Not Confetti)**
- The DONE node emits a soft expanding glow
- Stats card fades in with slight upward motion
- Connection rail briefly glows green end-to-end
- Optional: Very subtle particle burst (5-10 particles, not confetti)

**CSS:**
```css
@keyframes completion-glow {
  0% {
    box-shadow: 0 0 0 0 rgba(0, 255, 65, 0.7);
  }
  70% {
    box-shadow: 0 0 0 20px rgba(0, 255, 65, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(0, 255, 65, 0);
  }
}

.phase-node.done.celebrating {
  animation: completion-glow 1s ease-out;
}
```

### 2.9.9 Interactive Hover States

When users hover over elements:

**Phase Node Hover:**
- Node scales up slightly (1.1x)
- Tooltip appears with phase description
- Connection lines to this node highlight

**Task Card Hover:**
- Card lifts (subtle shadow increase)
- Task details expand inline
- Agent working on this task highlights

**Instruction Panel Hover:**
- Individual instructions highlight on hover
- "Learn more" link appears for each

---

## 2.10 Technical Implementation Notes

### Animation Library: Framer Motion
Primary choice for React animations. Handles:
- Layout animations
- Gesture interactions
- SVG path animations
- Stagger effects

### Canvas for Particles
Use HTML Canvas or Three.js for:
- Particle flow effects
- Background ambient animations
- Performance-critical animations

### Responsive Animation Scaling
- Desktop: Full animations, all effects
- Tablet: Reduced particle count, simpler effects
- Mobile: Minimal animations, focus on clarity
- Respect `prefers-reduced-motion` media query

### Performance Budget
- Target: 60fps on mid-range devices
- Lazy load heavy animation components
- Use `will-change` sparingly
- Prefer CSS animations over JS where possible

---

## 3. Architecture of Autonomy Section

Engineers are skeptical of "AI agents." Show the logic behind the OmoiOS orchestrator.

### 3.1 Phase-Based Workflow Diagram

**Component: `WorkflowDiagram`**

Visual showing how a **Requirement** (input) moves through the agent chain:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   INPUT     │    │  ARCHITECT  │    │  DEVELOPER  │    │   RELEASE   │
│ "Add auth"  │───▶│   Agent     │───▶│   Agents    │───▶│   Agent     │
│             │    │             │    │  (Parallel) │    │             │
└─────────────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
                          │                   │                   │
                    Requirements         Sandbox            Git PR
                    + Tickets            Builds            Created
                          │                   │                   │
                          ▼                   ▼                   ▼
                   ┌──────────────────────────────────────────────┐
                   │          HUMAN-IN-THE-LOOP                   │
                   │   Final PR Review & Approval Point           │
                   └──────────────────────────────────────────────┘
```

**Agent Personas** (for copy and diagram labels):

1. **Architect Agent**: Analyzes requirements, chooses tech stack, creates tickets
2. **Project Lead Agent**: Decomposes work into tasks, manages dependencies
3. **Developer Agents**: Execute tasks in sandboxed environments (parallel execution)
4. **Release Agent**: Manages Git workflows, opens PRs, attaches test results

**Key Callouts:**
- "Human-in-the-loop: Only at final review"
- "Parallel execution: 10 agents, 10 tickets, simultaneously"
- "Sandboxed: Every task runs in an isolated container"

### 3.2 Dynamic Discovery Visualization

**Component: `DiscoveryBacklog`**

A UI that looks like a simplified Linear/Jira board where new task cards "pop" into existence:

```tsx
// Card appears with ✨ icon
<TaskCard
  icon={<SparklesIcon />}
  label="Discovered by Agent"
  title="Add database index for user_id"
  source="Task-A discovered this dependency"
/>
```

**Animation:** Cards slide in from the right with a subtle glow effect.

---

## 3. Deep-Dive Feature Bento Grid

Replace the four simple cards with a high-density "Bento Grid" (6-8 items).

### 3.1 Grid Layout

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  Agent Memory    │  │  Sandbox Safety  │  │  Git Native  │ │
│  │  (Large Card)    │  │  (Large Card)    │  │  (Small)     │ │
│  │                  │  │                  │  ├──────────────┤ │
│  │                  │  │                  │  │  Parallel    │ │
│  │                  │  │                  │  │  Execution   │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
│                                                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  Audit Trail     │  │  Discovery Loop  │  │  HITL        │ │
│  │  (Medium)        │  │  (Medium)        │  │  Approvals   │ │
│  │                  │  │                  │  │  (Small)     │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Feature Card Content

#### Card 1: Agent Memory (RAG-Based Context)
**Icon:** Brain/Memory icon
**Headline:** "Codebase-Aware Intelligence"
**Copy:**
> Agents remember context across files, PRs, and sessions. RAG-powered semantic memory means no hallucinated function calls—ever.

**Visual:** Mini code snippet showing `find_memory("PostgreSQL connection error")` returning past solutions.

#### Card 2: Sandbox Safety
**Icon:** Shield/Container icon
**Headline:** "Zero-Risk Execution"
**Copy:**
> Every task runs in an ephemeral Docker container. Tests pass before any code touches your branch. Preview URLs for every PR.

**Visual:** Build status badge mockup: `✓ Build Passed • 12/12 Tests • Preview Ready`

#### Card 3: Git Native
**Icon:** GitBranch icon
**Headline:** "Seamless Version Control"
**Copy:**
> Agents understand Git. They create branches, write meaningful commits, and open PRs with full context. No copy-paste required.

**Visual:** Mock GitHub PR comment from "OmoiOS Bot" explaining changes.

#### Card 4: Parallel Execution
**Icon:** Layers/Parallel icon
**Headline:** "10x Developer Output"
**Copy:**
> Atomic task decomposition enables true parallelism. 10 agents working 10 tickets simultaneously—ship features while you sleep.

**Visual:** Mini progress bars showing 5 agents working in parallel.

#### Card 5: Audit Trail / Transparency
**Icon:** FileSearch icon
**Headline:** "No Black Box"
**Copy:**
> Every agent decision is logged with full reasoning. See exactly why Library X was chosen over Library Y.

**Visual:** Reasoning log snippet:
```
Reasoning: Selected Tailwind CSS over styled-components because:
- Project already uses utility-first patterns
- Bundle size reduction: 15KB
- Team familiarity (detected in existing code)
```

#### Card 6: Dynamic Discovery
**Icon:** Sparkles/Magic icon
**Headline:** "Beyond Pre-Defined Workflows"
**Copy:**
> Unlike static DAGs, OmoiOS uses emergent discovery. Agents identify dependencies and create new tasks on-the-fly as they explore your codebase.

**Visual:** Task tree animation showing new nodes appearing.

#### Card 7: Human-in-the-Loop
**Icon:** UserCheck icon
**Headline:** "You Stay in Control"
**Copy:**
> One approval point: the final PR review. Guardian agents monitor for drift and surface anomalies before they become problems.

---

## 4. "Time-Lapse" Autonomy Dashboard Component

Prove the "ship while you sleep" value proposition.

### 4.1 Night Shift Log

**Component: `NightShiftLog`**

A vertical timeline with timestamps showing agents working through the night:

```tsx
interface LogEntry {
  timestamp: string;      // "02:47 AM"
  agentId: string;        // "Agent-Dev-3"
  ticketId: string;       // "FEAT-147"
  action: string;         // "Completed"
  sandboxUrl?: string;    // Link to sandbox build
  prUrl?: string;         // Link to PR
}
```

**Sample Entries:**
```
02:47 AM  Agent-Architect   FEAT-147  Decomposed into 5 tasks
03:12 AM  Agent-Dev-1       TASK-301  ✓ Completed • Tests: 8/8
03:34 AM  Agent-Dev-2       TASK-302  ✓ Completed • Tests: 12/12
04:01 AM  Agent-Dev-3       TASK-303  🔄 In Progress...
04:22 AM  Agent-Dev-1       TASK-304  ✓ Completed • Tests: 6/6
05:15 AM  Agent-Orchestrator FEAT-147  📬 PR #147 Opened
```

### 4.2 Day/Night Mode Toggle

A UI switch that toggles the site visualization:
- **Day Mode**: "Manual Oversight" — Shows traditional workflow
- **Night Mode**: "Full Autonomy" — Shows completed PRs and passed tests

---

## 5. "How it Works" Section

### 5.1 Four-Phase Loop

**Phase 1: The Blueprint (Input & Injection)**
> You provide a high-level objective. OmoiOS injects Phase Instructions—architectural constraints that ensure every agent follows your coding standards from the start.

**Phase 2: Dynamic Task Discovery**
> Unlike static tools, OmoiOS doesn't need a full map. As agents process requirements, they discover sub-tasks ("Wait, this needs a new schema") and autonomously add them to the backlog.

**Phase 3: Parallel Execution Engine**
> Tickets decompose into atomic tasks—work completable in a single session. OmoiOS spins up multiple agents in parallel, drastically reducing time-to-PR.

**Phase 4: Autonomous Verification**
> Every task executes in a sandbox. Agents manage Git workflows, run tests, and ensure code is ship-ready without human intervention.

### 5.2 Visual: Atomic Decomposition Tree

**Component: `DecompositionTree`**

```
                    ┌─────────────────────┐
                    │   "Add Stripe       │
                    │   Checkout Flow"    │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
     ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
     │ REQ: Payment│    │ REQ: Webhook│    │ REQ: Testing│
     │ Integration │    │ Handling    │    │ Suite       │
     └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
            │                  │                  │
      ┌─────┼─────┐      ┌─────┼─────┐      ┌─────┼─────┐
      ▼     ▼     ▼      ▼     ▼     ▼      ▼     ▼     ▼
   [T-1] [T-2] [T-3]  [T-4] [T-5] [T-6]  [T-7] [T-8] [T-9]

   Status Indicators:
   ● Pending  ◐ Coding  ◑ Testing  ✓ Committed
```

---

## 6. Social Proof & Performance Metrics

### 6.1 Efficiency Stats

Display prominent metrics (hypothetical but realistic):

| Metric | Value | Context |
|--------|-------|---------|
| **70%** | Reduction in boilerplate time | Scaffolding, setup, config |
| **Zero-config** | For Next.js, Python, TypeScript | Out-of-the-box support |
| **10x** | Parallel task throughput | vs. single-agent tools |
| **100%** | Sandbox isolation | No production risk |

### 6.2 Integration Cloud

Grayscale logo cloud of supported tech stack:
- **Platforms**: AWS, Vercel, Railway, Docker, Kubernetes
- **Tools**: GitHub, Linear, Jira, Notion
- **Languages**: TypeScript, Python, Rust, Go

---

## 7. Developer Experience (DX) Section

### 7.1 CLI Reveal

**Component: `CLIDemo`**

Show the `omi` command-line tool:

```bash
$ omi task "Add Stripe checkout to the billing page"

✓ Analyzing requirements...
✓ Created Ticket FEAT-201
✓ Decomposed into 4 tasks
✓ Spawning 4 agents...

Agent-1: Implementing StripeCheckoutButton component
Agent-2: Adding /api/checkout/session endpoint
Agent-3: Writing integration tests
Agent-4: Updating billing page layout

[████████████████████░░░░] 78% complete
```

### 7.2 Comparison Table: Manual vs. Autonomous

| Traditional AI Coding | OmoiOS |
|----------------------|--------|
| Copy-paste from chat | Goal-based entry |
| Manual debugging | Auto-verification in sandbox |
| Constant prompting | Background execution |
| "It works on my machine" | Verified, tested PRs |
| One task at a time | 10 agents in parallel |

---

## 8. Design System Updates

### 8.1 Dark Mode Enhancement (Engineers' Preference)

Update `globals.css` to support a "Terminal Dark" theme for landing page:

```css
/* Terminal-style dark theme for landing page */
.terminal-dark {
  --background: 0 0% 5%;          /* #0D0D0D Near-black */
  --foreground: 0 0% 90%;         /* #E5E5E5 Light gray */
  --accent: 145 100% 50%;         /* #00FF41 Terminal green */
  --accent-secondary: 212 97% 43%; /* #0366D6 Link blue */
}
```

### 8.2 Typography Updates

Add to `tailwind.config.ts`:

```ts
fontFamily: {
  sans: ['var(--font-inter)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
  mono: ['var(--font-jetbrains-mono)', 'ui-monospace', 'monospace'],
  display: ['var(--font-inter)', 'ui-sans-serif'],  // For hero headlines
},
```

**Usage:**
- Headlines: Inter (display weight)
- Body: Inter
- Code/Technical: JetBrains Mono

### 8.3 New Color Tokens

```css
/* Add to globals.css */
:root {
  /* Terminal colors for landing components */
  --terminal-bg: 0 0% 5%;
  --terminal-text: 0 0% 90%;
  --terminal-green: 145 100% 50%;
  --terminal-yellow: 45 100% 50%;
  --terminal-red: 0 100% 50%;
  --terminal-blue: 212 100% 60%;

  /* Gradient for hero */
  --gradient-start: 145 100% 50%;  /* Terminal green */
  --gradient-end: 212 97% 43%;     /* Info blue */
}
```

---

## 9. New Components Required

### 9.1 Component Checklist

| Component | Location | Priority | Description |
|-----------|----------|----------|-------------|
| `TicketJourney` | `components/landing/TicketJourney.tsx` | **P0** | **Hero centerpiece** - Animated ticket moving through phases with instruction injection |
| `PhaseInstructionsPanel` | `components/landing/PhaseInstructionsPanel.tsx` | **P0** | Shows phase_prompt bullets + done_definitions checklist |
| `FeedbackLoopArrow` | `components/landing/FeedbackLoopArrow.tsx` | **P0** | Animated SVG arrow for TEST→BUILD loop-back |
| `AgentTerminal` | `components/landing/AgentTerminal.tsx` | P0 | Faux terminal showing agent activity |
| `WorkflowDiagram` | `components/landing/WorkflowDiagram.tsx` | P0 | Agent handoff architecture diagram |
| `ParticleRail` | `components/landing/ParticleRail.tsx` | P1 | Flowing particles along phase connection lines |
| `TaskSpawnBurst` | `components/landing/TaskSpawnBurst.tsx` | P1 | Cards exploding outward when tasks spawn |
| `AgentAvatar` | `components/landing/AgentAvatar.tsx` | P1 | Agent icon with orbiting activity indicator |
| `AnimatedCheckbox` | `components/landing/AnimatedCheckbox.tsx` | P1 | SVG checkmark draw animation |
| `BentoGrid` | `components/landing/BentoGrid.tsx` | P1 | Feature grid container |
| `FeatureCard` | `components/landing/FeatureCard.tsx` | P1 | Individual feature cards |
| `NightShiftLog` | `components/landing/NightShiftLog.tsx` | P1 | Timestamped agent activity log |
| `TypewriterText` | `components/landing/TypewriterText.tsx` | P1 | Text that types in character by character |
| `DecompositionTree` | `components/landing/DecompositionTree.tsx` | P2 | Task breakdown visualization |
| `CLIDemo` | `components/landing/CLIDemo.tsx` | P2 | CLI command showcase |
| `IntegrationCloud` | `components/landing/IntegrationCloud.tsx` | P2 | Logo cloud of integrations |
| `ComparisonTable` | `components/landing/ComparisonTable.tsx` | P2 | Manual vs Autonomous comparison |
| `VideoModal` | `components/landing/VideoModal.tsx` | P2 | Demo video modal |

### 9.2 Shared Animation Utilities

Create `lib/animations.ts`:

```ts
export const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 }
};

export const staggerChildren = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

export const typewriter = {
  // For AgentTerminal typing effect
  hidden: { opacity: 0, x: -20 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.05 }
  })
};
```

---

## 10. Implementation Phases

### Phase 1: Foundation (P0)
1. Create `components/landing/` directory structure
2. **Implement `TicketJourney` component** - The hero centerpiece showing ticket lifecycle
3. Implement `AgentTerminal` with basic typing animation
4. Update hero section with new copy
5. Add "Watch it build" CTA (placeholder modal)

### Phase 2: Trust Signals (P1)
1. Implement `BentoGrid` layout
2. Create all 6-7 `FeatureCard` components
3. Add `NightShiftLog` component
4. Implement `WorkflowDiagram`

### Phase 3: Polish (P2)
1. Add `CLIDemo` with animated output
2. Create `IntegrationCloud` with logos
3. Build `ComparisonTable` component
4. Implement `DecompositionTree` with React Flow
5. Add video modal integration

### Phase 4: Optimization
1. Dark mode toggle for landing
2. Performance optimization (lazy loading, code splitting)
3. Analytics integration (conversion tracking)
4. A/B testing infrastructure for headlines

---

## 11. Copy Bank

### Headlines

**Hero Options:**
- "Ship features while you sleep"
- "From PRD to Pull Request in one command"
- "Unsupervised Engineering at Scale"
- "Stop prompting. Start shipping."
- "Your autonomous engineering department"

**Subheadlines:**
- "OmoiOS orchestrates multiple AI agents through adaptive, phase-based workflows to build software from requirements to deployment."
- "From natural language to verified pull requests—no babysitting required."
- "Autonomous agents that plan, code, test, and ship. You review the final PR."

### Feature Taglines

- Agent Memory: "Never explain your codebase twice"
- Sandbox Safety: "Risk-free execution, every time"
- Git Native: "Agents that speak Git fluently"
- Parallel Execution: "10 agents. 10 tickets. Simultaneously."
- Audit Trail: "See the reasoning, not just the code"
- Discovery Loop: "Agents that find what you missed"

---

## 12. Appendix: Prompt-Ready Instructions for AI

### For Copywriting

> "Write three versions of a hero section headline for OmoiOS. Focus: 'Unsupervised Engineering.' Keywords: Autonomous, Ship while you sleep, No babysitting, Planning to PR, Decomposed tasks. Tone: technical, authoritative, minimalist."

### For Agent Persona Definitions

> "Define four distinct AI Agent personas for a software engineering platform:
> 1. **Architect** (Requirements & Tech Stack)
> 2. **Project Lead** (Decomposing code into tickets)
> 3. **Developer** (Executing tasks in sandbox)
> 4. **Release Bot** (Git workflows & PR management)
> Describe their specific responsibilities and how they communicate autonomously."

### For Feature Descriptions

> "Write 6 high-intent feature descriptions for an AI software agent platform, focusing on: RAG-based context, multi-repo support, automated testing, sandbox isolation, audit trails, and emergent task discovery."

### For Reasoning Log Example

> "Create a 'Reasoning Log' example for an AI agent refactoring a React component to use Tailwind CSS, including its rationale for specific architectural decisions."

### For UI Component Specs

> "Create a UI specification for a 'Night Shift' log. Each entry should include: timestamp, Agent ID (e.g., 'Agent-Decomposer'), the specific ticket it finished, and a link to the Sandbox build URL."

---

## Related Documents

- [Project Management Dashboard](./project_management_dashboard.md) - Internal dashboard design
- [Frontend Architecture](./frontend_architecture_shadcn_nextjs.md) - Technical stack reference
- [Component Scaffold Guide](./component_scaffold_guide.md) - How to create new components
