# OmoiOS Implementation Roadmap

**Document Purpose**: High-level plan for implementing the multi-agent orchestration system, starting from the current MVP foundation and growing incrementally with working code at every step.

**Created**: 2025-11-16  
**Status**: Active Planning  
**Related Documents**:
- [Foundation & Smallest Runnable](./foundation_and_smallest_runnable.md)
- [OpenHands Insights & Prioritization](./openhands_insights_and_prioritization.md)
- [Implementation Questions](./implementation_questions.md)

---

## Current State (✅ Completed)

### Foundation Layer - MVP Complete
- ✅ **Database Models**: Ticket, Task, Agent, Event models with SQLAlchemy
- ✅ **Core Services**: DatabaseService, TaskQueueService, EventBusService
- ✅ **Agent Executor**: OpenHands SDK wrapper for task execution
- ✅ **API Server**: FastAPI with ticket/task CRUD endpoints
- ✅ **Worker Service**: Background worker that polls queue and executes tasks
- ✅ **Orchestrator Loop**: Basic task assignment logic in API server
- ✅ **Tests**: 27 passing tests covering database, queue, event bus, agent executor, E2E flows
- ✅ **Infrastructure**: Docker Compose with PostgreSQL, Redis, API, Worker services
- ✅ **Datetime Handling**: Migrated to `whenever` library for timezone-aware timestamps

**What Works Now**:
- Create ticket → System enqueues initial task
- Worker polls queue → Assigns task to available agent
- Agent executes task using OpenHands SDK
- Task status updates → Events published to Redis
- Basic end-to-end flow functional

**What's Missing**:
- Multi-phase workflow (only single phase)
- Task dependencies and blocking
- Agent health monitoring
- Phase transitions and validation
- Multi-agent coordination
- Error recovery and retries

---

## Implementation Phases

### Phase 1: Core Workflow Enhancement (Weeks 1-2)
**Goal**: Make the basic workflow robust and production-ready

#### Milestone 1.1: Task Dependencies & Blocking (Week 1)
**Deliverables**:
- Add `dependencies` JSONB field to Task model
- Implement dependency resolution in TaskQueueService
- Add `blocked_by` and `blocks` relationships
- Update `get_next_task()` to respect dependencies
- Tests: Task dependency resolution, blocking detection

**Success Criteria**:
- ✅ Can create tasks with dependencies
- ✅ Tasks only assigned when dependencies complete
- ✅ Circular dependency detection
- ✅ All tests pass

#### Milestone 1.2: Error Handling & Retries (Week 1)
**Deliverables**:
- Add `retry_count` and `max_retries` to Task model
- Implement retry logic in worker
- Add exponential backoff for retries
- Task failure handling with error categorization
- Tests: Retry logic, failure handling, backoff

**Success Criteria**:
- ✅ Failed tasks automatically retry up to max_retries
- ✅ Permanent failures marked appropriately
- ✅ Error messages stored and queryable
- ✅ All tests pass

#### Milestone 1.3: Agent Health & Heartbeat (Week 2)
**Deliverables**:
- Implement heartbeat mechanism in worker
- Add agent health status tracking
- Create agent health check endpoint
- Implement agent timeout detection
- Tests: Heartbeat emission, health checks, timeout detection

**Success Criteria**:
- ✅ Agents emit heartbeats every 30 seconds
- ✅ Stale agents detected and marked as failed
- ✅ Health endpoint shows agent status
- ✅ All tests pass

#### Milestone 1.4: Task Timeout & Cancellation (Week 2)
**Deliverables**:
- Add `timeout_seconds` to Task model
- Implement timeout detection in orchestrator
- Add task cancellation API endpoint
- Handle timeout in worker (kill conversation)
- Tests: Timeout detection, cancellation, cleanup

**Success Criteria**:
- ✅ Long-running tasks timeout after threshold
- ✅ Tasks can be cancelled via API
- ✅ Resources cleaned up on timeout/cancel
- ✅ All tests pass

---

### Phase 2: Multi-Phase Workflow (Weeks 3-4)
**Goal**: Implement complete workflow with phase transitions

#### Milestone 2.1: Phase Definitions & State Machine (Week 3)
**Deliverables**:
- Define phase constants (REQUIREMENTS, DESIGN, IMPLEMENTATION, TESTING, DEPLOYMENT)
- Implement ticket phase state machine
- Add phase transition validation
- Create phase transition API endpoint
- Tests: Phase transitions, validation, state machine

**Success Criteria**:
- ✅ Tickets can transition between phases
- ✅ Invalid transitions rejected
- ✅ Phase history tracked
- ✅ All tests pass

#### Milestone 2.2: Phase-Specific Task Generation (Week 3)
**Deliverables**:
- Create task generation service per phase
- Implement ticket decomposition logic
- Add phase-specific task templates
- Create task generation API endpoint
- Tests: Task generation per phase, templates

**Success Criteria**:
- ✅ Tickets generate appropriate tasks per phase
- ✅ Task templates configurable
- ✅ Tasks linked to correct phase
- ✅ All tests pass

#### Milestone 2.3: Phase Gates & Validation (Week 4)
**Deliverables**:
- Implement phase gate validation service
- Add artifact requirements per phase
- Create validation agent (separate from worker)
- Add phase gate API endpoints
- Tests: Gate validation, artifact checking, validation agent

**Success Criteria**:
- ✅ Phase gates check required artifacts
- ✅ Validation agent reviews phase completion
- ✅ Gates can block or allow transitions
- ✅ All tests pass

#### Milestone 2.4: Cross-Phase Context Passing (Week 4)
**Deliverables**:
- Implement context aggregation service
- Add context storage to Ticket model
- Create context summarization logic
- Pass context between phases
- Tests: Context aggregation, summarization, passing

**Success Criteria**:
- ✅ Context from previous phases available
- ✅ Context summarized to reduce token usage
- ✅ Context passed to next phase tasks
- ✅ All tests pass

---

### Phase 3: Multi-Agent Coordination (Weeks 5-6)
**Goal**: Enable multiple agents working on related tasks

#### Phase 3 Planning & Parallelization Overview
- **Readiness Checks**: confirm Phase 2 state machine, context passing, and validation services are merged; ensure heartbeat + retry telemetry from Phase 1 is flowing so coordination metrics have source data.
- **Agent Workstreams**:
  - *Registry Squad* (SchemaAgent + APIAgent) owns Milestone 3.1 by extending the Agent model, migrations, and `/agents/search` API.
  - *Collaboration Squad* (EventBusAgent + ConversationAgent) tackles Milestone 3.2 by defining event schemas and messaging patterns; starts once registry read models are seeded but iterates in parallel with 3.1 after day 1.
  - *Parallel Execution Squad* (SchedulerAgent + LockManagerAgent) delivers Milestone 3.3 by shipping the DAG resolver, lock manager, and worker concurrency envelope.
  - *Coordination Patterns Squad* (TemplateAgent + PlaybookAgent) focuses on Milestone 3.4, templating sync/join primitives that plug into the new scheduler.
- **Parallel Execution Timeline**:
  - *Week 5 / Days 1-2*: Registry Squad leads; Collaboration Squad develops event schemas simultaneously using stub capability data shared via Redis streams.
  - *Week 5 / Days 3-5*: Collaboration Squad finalizes messaging + handoff flows while Parallel Execution Squad prototypes DAG evaluation using fixture tickets.
  - *Week 6 / Days 1-2*: Parallel Execution Squad productionizes locks and conflict detection; Coordination Patterns Squad begins codifying templates leveraging the new DAG API.
  - *Week 6 / Days 3-5*: Coordination Patterns Squad and Collaboration Squad run joint simulations to prove multi-agent splits/joins while Registry Squad hardens search indexes.
- **Dependencies & Integration Hooks**:
  - Registry service publishes capability deltas to EventBus so Collaboration Squad consumes real data.
  - Scheduler exposes gRPC/REST surface for Coordination Patterns Squad, enabling agents to configure sync points without direct DB writes.
  - Shared `agent_orchestration` library captures DTOs so each squad iterates independently yet stays type-safe.

#### Milestone 3.1: Agent Registry & Discovery (Week 5)
**Deliverables**:
- Enhance agent registry with capabilities
- Add agent discovery API
- Implement agent capability matching
- Create agent assignment algorithm
- Tests: Registry, discovery, matching, assignment

**Success Criteria**:
- ✅ Agents register with capabilities
- ✅ System can find agents by capability
- ✅ Tasks assigned to best-fit agents
- ✅ All tests pass

#### Milestone 3.2: Agent Communication Protocol (Week 5)
**Deliverables**:
- Define agent-to-agent event types
- Implement agent messaging via event bus
- Add agent collaboration patterns
- Create agent handoff mechanism
- Tests: Agent messaging, collaboration, handoff

**Success Criteria**:
- ✅ Agents can send messages to each other
- ✅ Collaboration events published
- ✅ Tasks can be handed off between agents
- ✅ All tests pass

#### Milestone 3.3: Parallel Task Execution (Week 6)
**Deliverables**:
- Implement dependency graph resolution
- Add parallel execution support
- Create task conflict detection
- Implement resource locking
- Tests: Parallel execution, conflicts, locking

**Success Criteria**:
- ✅ Independent tasks execute in parallel
- ✅ Conflicts detected and resolved
- ✅ Resources locked appropriately
- ✅ All tests pass

#### Milestone 3.4: Task Coordination Patterns (Week 6)
**Deliverables**:
- Implement task coordination primitives
- Add task synchronization points
- Create task merge/join logic
- Implement task splitting
- Tests: Coordination patterns, sync points, merge/join

**Success Criteria**:
- ✅ Tasks can coordinate via sync points
- ✅ Tasks can merge results
- ✅ Large tasks can be split
- ✅ All tests pass

---

### Phase 4: Monitoring & Observability (Weeks 7-8)
**Goal**: Add comprehensive monitoring and health management

#### Phase 4 Planning & Parallelization Overview
- **Readiness Checks**: verify Phase 3 emits capability metrics, DAG events, and lock telemetry; ensure OpenTelemetry collectors are provisioned via infrastructure code.
- **Agent Workstreams**:
  - *Monitor Squad* (MetricsAgent + DashboardAgent) handles Milestone 4.1, building the monitor service and baseline anomaly detection.
  - *Alerting Squad* (SignalAgent + RouterAgent) addresses Milestone 4.2 by layering alert logic on top of monitor metrics and wiring outbound channels.
  - *Watchdog Squad* (GuardianPrepAgent + AutoRecoveryAgent) executes Milestone 4.3, consuming heartbeats plus alert streams to trigger remediation.
  - *Observability Squad* (TracingAgent + LoggingAgent) owns Milestone 4.4, instrumenting services and integrating distributed tracing/log aggregation.
- **Parallel Execution Timeline**:
  - *Week 7 / Days 1-2*: Monitor Squad deploys collector + dashboard scaffolding while Observability Squad adds tracing hooks to shared libraries.
  - *Week 7 / Days 3-5*: Alerting Squad consumes Monitor metrics to implement rules; Watchdog Squad begins building restart policies using simulated alerts.
  - *Week 8 / Days 1-2*: Watchdog Squad integrates with Alerting + Monitor outputs; Observability Squad finishes log aggregation pipeline and profiling harness.
  - *Week 8 / Days 3-5*: All squads run joint game-day to validate anomaly detection → alerting → watchdog remediation, with Observability Squad capturing traces for regression baselines.
- **Dependencies & Integration Hooks**:
  - Monitor Squad publishes metrics schemas early so Alerting Squad can stub data; Observability Squad reuses the same schema to avoid duplicate instrumentation.
  - Watchdog actions piggyback on agent registry APIs from Phase 3; define contract tests to lock interfaces.
  - Shared `telemetry-config` package centralizes exporter setup to keep squads unblocked while working in parallel.

#### Milestone 4.1: Monitor Agent Implementation (Week 7)
**Deliverables**:
- Create Monitor agent service
- Implement metrics collection
- Add anomaly detection basics
- Create monitoring dashboard API
- Tests: Monitor agent, metrics, anomaly detection

**Success Criteria**:
- ✅ Monitor agent collects system metrics
- ✅ Anomalies detected and reported
- ✅ Dashboard shows system health
- ✅ All tests pass

#### Milestone 4.2: Health Metrics & Alerting (Week 7)
**Deliverables**:
- Implement health metrics service
- Add alert generation logic
- Create alert routing (email, webhook, etc.)
- Add alert severity levels
- Tests: Metrics, alerts, routing, severity

**Success Criteria**:
- ✅ Health metrics collected continuously
- ✅ Alerts generated on thresholds
- ✅ Alerts routed to appropriate channels
- ✅ All tests pass

#### Milestone 4.3: Watchdog Agent (Week 8)
**Deliverables**:
- Create Watchdog agent service
- Implement agent health monitoring
- Add automatic agent restart logic
- Create watchdog escalation
- Tests: Watchdog, health monitoring, restart

**Success Criteria**:
- ✅ Watchdog monitors all agents
- ✅ Failed agents automatically restarted
- ✅ Escalation to Guardian when needed
- ✅ All tests pass

#### Milestone 4.4: Observability Integration (Week 8)
**Deliverables**:
- Add OpenTelemetry instrumentation
- Implement distributed tracing
- Create log aggregation
- Add performance profiling
- Tests: Tracing, logging, profiling

**Success Criteria**:
- ✅ Traces span across services
- ✅ Logs aggregated and searchable
- ✅ Performance bottlenecks identified
- ✅ All tests pass

---

### Phase 5: Advanced Features (Weeks 9-12)
**Goal**: Add production-ready features and optimizations

#### Milestone 5.1: Guardian Agent (Week 9)
**Deliverables**:
- Create Guardian agent service
- Implement emergency intervention
- Add resource reallocation
- Create guardian authority system
- Tests: Guardian, intervention, reallocation

**Success Criteria**:
- ✅ Guardian can override normal operations
- ✅ Resources reallocated in emergencies
- ✅ Authority system enforced
- ✅ All tests pass

#### Milestone 5.2: Memory & Learning System (Week 10)
**Deliverables**:
- Implement memory storage service
- Add pattern recognition
- Create learning from past tasks
- Add memory retrieval for similar tasks
- Tests: Memory storage, pattern recognition, learning

**Success Criteria**:
- ✅ System remembers past solutions
- ✅ Patterns recognized and reused
- ✅ Similar tasks benefit from memory
- ✅ All tests pass

#### Milestone 5.3: Discovery-Based Task Spawning (Week 11)
**Deliverables**:
- Implement task discovery service
- Add observation parsing
- Create dynamic task generation
- Add discovery validation
- Tests: Discovery, parsing, generation

**Success Criteria**:
- ✅ Agents can discover new tasks
- ✅ Discovered tasks validated
- ✅ Tasks generated from observations
- ✅ All tests pass

#### Milestone 5.4: Custom Tools & Integrations (Week 12)
**Deliverables**:
- Create tool development framework
- Implement GitHub integration tool
- Add Jira integration tool
- Create Supabase integration tool
- Tests: Tool framework, integrations

**Success Criteria**:
- ✅ Custom tools can be developed
- ✅ GitHub/Jira/Supabase integrated
- ✅ Tools work with OpenHands SDK
- ✅ All tests pass

---

### Phase 6: Scale & Optimization (Weeks 13-16)
**Goal**: Optimize for scale and production workloads

#### Milestone 6.1: Performance Optimization (Week 13)
**Deliverables**:
- Database query optimization
- Add caching layer
- Implement connection pooling
- Optimize event bus performance
- Tests: Performance benchmarks, caching

**Success Criteria**:
- ✅ Query times < 100ms for common operations
- ✅ Cache hit rate > 80%
- ✅ Event bus handles 1000+ events/sec
- ✅ All tests pass

#### Milestone 6.2: Scalability Enhancements (Week 14)
**Deliverables**:
- Implement horizontal scaling
- Add load balancing
- Create service mesh integration
- Add auto-scaling logic
- Tests: Scaling, load balancing, auto-scale

**Success Criteria**:
- ✅ System scales horizontally
- ✅ Load distributed evenly
- ✅ Auto-scaling based on queue depth
- ✅ All tests pass

#### Milestone 6.3: High Availability (Week 15)
**Deliverables**:
- Implement database replication
- Add Redis clustering
- Create failover mechanisms
- Add data backup/restore
- Tests: Replication, clustering, failover

**Success Criteria**:
- ✅ System survives single node failure
- ✅ Data replicated across nodes
- ✅ Automatic failover works
- ✅ All tests pass

#### Milestone 6.4: Security Hardening (Week 16)
**Deliverables**:
- Implement authentication/authorization
- Add API rate limiting
- Create audit logging
- Add secret management
- Tests: Auth, rate limiting, audit, secrets

**Success Criteria**:
- ✅ All APIs require authentication
- ✅ Rate limits enforced
- ✅ All actions audited
- ✅ Secrets securely managed
- ✅ All tests pass

---

## Progress Tracking

### Phase Completion Criteria
Each phase is considered complete when:
1. ✅ All milestones in phase are done
2. ✅ All tests pass (unit + integration + E2E)
3. ✅ Documentation updated
4. ✅ Performance benchmarks met
5. ✅ Code review completed

### Milestone Completion Criteria
Each milestone is considered complete when:
1. ✅ All deliverables implemented
2. ✅ Success criteria met
3. ✅ Tests written and passing
4. ✅ Code reviewed and merged

### Weekly Checkpoints
- **Monday**: Review previous week progress, plan current week
- **Wednesday**: Mid-week status check, adjust if needed
- **Friday**: Week completion review, demo working features

---

## Risk Mitigation

### Technical Risks
- **OpenHands SDK Changes**: Monitor SDK updates, pin versions, test compatibility
- **Performance Bottlenecks**: Profile early, optimize incrementally
- **Database Scalability**: Use connection pooling, read replicas, sharding if needed
- **Event Bus Overload**: Implement backpressure, message batching, rate limiting

### Process Risks
- **Scope Creep**: Stick to milestone deliverables, defer nice-to-haves
- **Testing Debt**: Maintain >80% test coverage, write tests first
- **Documentation Lag**: Update docs with each milestone
- **Integration Issues**: Test integrations early, use mocks where possible

---

## Success Metrics

### Code Quality
- Test coverage: >80%
- Linter errors: 0
- Type coverage: >90%
- Documentation coverage: >70%

### Performance
- API response time: <200ms (p95)
- Task assignment latency: <1s
- Event bus throughput: >1000 events/sec
- Database query time: <100ms (p95)

### Reliability
- Uptime: >99.9%
- Task success rate: >95%
- Agent availability: >99%
- Data consistency: 100%

---

## Next Steps

1. **Review & Approve Plan**: Get stakeholder approval on roadmap
2. **Start Phase 1.1**: Begin task dependencies implementation
3. **Set Up Tracking**: Create project board, track milestones
4. **Weekly Sync**: Establish weekly progress review meetings

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Assistant | Initial roadmap based on foundation and prioritization documents |

