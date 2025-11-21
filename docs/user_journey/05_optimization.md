# 5 Optimization

**Part of**: [User Journey Documentation](./README.md)

---
### Phase 5: Ongoing Monitoring & Optimization

#### 5.1 Statistics Dashboard

```
User navigates to Statistics dashboard:
   ↓
Views analytics:
- Ticket statistics: Completion rates, cycle times
- Agent performance: Tasks completed, code quality
- Code change statistics: Lines changed, files modified
- Project health: WIP violations, budget status
- Discovery analytics: Discovery rates by type
- Cost tracking: LLM costs per workflow
```

#### 5.2 Agents Overview Page

```
User navigates to /agents:
   ↓
Views Agents Overview Page:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Agents Overview                              [Spawn Agent] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent Metrics                                       │  │
│  │                                                      │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐          │  │
│  │  │  5   │  │  3   │  │  2   │  │  1   │          │  │
│  │  │Total │  │Active│  │Idle  │  │Stuck │          │  │
│  │  └──────┘  └──────┘  └──────┘  └──────┘          │  │
│  │                                                      │  │
│  │  Average Alignment: 78%                            │  │
│  │  Tasks Completed Today: 12                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent List                                          │  │
│  │                                                      │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │ Agent: worker-1                               │  │  │
│  │  │ Status: 🟢 Active                             │  │  │
│  │  │ Phase: PHASE_IMPLEMENTATION                    │  │  │
│  │  │ Tasks: 28 total, 22 done, 2 active          │  │  │
│  │  │ Agents: 2 active                             │  │  │
│  │  │ Discoveries: 3 new branches spawned         │  │  │
│  │  │ Current Task: "Implement JWT"                │  │  │
│  │  │ Alignment: 85%                                │  │  │
│  │  │ Tasks Completed: 8                            │  │  │
│  │  │ Commits: 15                                   │  │  │
│  │  │ Lines Changed: +2,450 -120                    │  │  │
│  │  │ [View Details] [Intervene]                    │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  │                                                      │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │ Agent: worker-2                               │  │  │
│  │  │ Status: 🟡 Idle                                │  │  │
│  │  │ Phase: PHASE_TESTING                          │  │  │
│  │  │ Tasks: 23 total, 22 done, 0 active          │  │  │
│  │  │ Agents: 0 active                             │  │  │
│  │  │ Current Task: None                            │  │  │
│  │  │ Alignment: N/A                                │  │  │
│  │  │ Tasks Completed: 5                            │  │  │
│  │  │ Commits: 8                                    │  │  │
│  │  │ Lines Changed: +890 -45                       │  │  │
│  │  │ [View Details] [Assign Task]                  │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Filters: [All ▼] [Active] [Idle] [Stuck] [By Phase ▼]     │
│  Search: [________________] [🔍]                            │
└─────────────────────────────────────────────────────────────┘
```

**Agent Metrics:**
- Total agents count
- Active agents (currently working)
- Idle agents (waiting for tasks)
- Stuck agents (needs intervention)
- Average alignment score across all agents
- Tasks completed today
- Total commits made
- Total lines changed

**Agent Card Details:**
- Agent ID and type
- Current status (Active, Idle, Stuck, Failed)
- Phase assignment (agents specialized per phase)
- Phase-specific metrics (cost, latency, error rate per phase)
- Phase bottlenecks (queue depth, WIP limits per phase)
- Current task (if active)
- Alignment score (if active)
- Performance metrics (tasks completed, commits, lines changed)
- Quick actions ([View Details] [Intervene] [Assign Task])

#### 5.3 Theme Settings

```
User navigates to Settings → Appearance:
   ↓
Views Theme Settings:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Theme Settings                                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Theme Mode:                                               │
│  ○ Light (default)                                         │
│  ● Dark                                                    │
│  ○ System (follows OS preference)                          │
│                                                              │
│  Accent Color:                                             │
│  [Select Color ▼]                                          │
│  • Blue (default)                                          │
│  • Green                                                   │
│  • Purple                                                  │
│  • Orange                                                  │
│                                                              │
│  Font Size:                                                │
│  [Small] [Medium] [Large]                                  │
│                                                              │
│  Reduced Motion:                                           │
│  ☐ Enable reduced motion animations                        │
│                                                              │
│  [Save Changes]                                            │
└─────────────────────────────────────────────────────────────┘
```

**Theme Options:**
- **Light Mode**: Default light theme
- **Dark Mode**: Dark theme for low-light environments
- **System**: Automatically follows OS theme preference
- **Accent Color**: Customize primary color scheme
- **Font Size**: Adjustable text size
- **Reduced Motion**: Disable animations for accessibility

#### 5.4 Search & Filtering

```
User uses Command Palette (Cmd+K) or Search bar:
   ↓
Search across:
- Tickets (by title, description, phase)
- Tasks (by description, status)
- Commits (by message, author, date)
- Agents (by status, capabilities)
- Code changes (by file, agent)
   ↓
Advanced filters:
- Date range
- Phase/status
- Agent
- Project
- Discovery type
```

#### 5.5 Audit Trails

```
User views audit trail for ticket:
   ↓
Sees complete history:
- When ticket created
- All phase transitions
- All agent assignments
- All code commits
- All discoveries made
- All interventions sent
- All approvals/rejections
   ↓
Can export audit trail:
- PDF report
- CSV export
- JSON export
```

---


---

**Next**: See [README.md](./README.md) for complete documentation index.
