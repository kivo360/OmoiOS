---
id: PRD-SUPERVISOR-001
title: Supervisor Agent PRD
feature: supervisor-agent
created: 2025-01-08
updated: 2025-01-08
status: draft
author: Claude
---

# Supervisor Agent

## Executive Summary

The Supervisor Agent is a higher-level orchestration service that provides centralized oversight, coordination, and policy enforcement for the multi-agent monitoring system. Unlike existing services (MonitoringLoop, IntelligentGuardian, Conductor) that operate independently, the Supervisor Agent unifies their capabilities, implements cross-service policies, enables intelligent resource allocation, and provides a single entry point for agent team management.

The Supervisor Agent addresses the gap between individual agent monitoring and system-wide coordination by implementing hierarchical supervision, adaptive autonomy based on learned patterns, and automated remediation within policy boundaries.

## Problem Statement

### Current State

OmoiOS has several monitoring services that operate largely independently:
- **IntelligentGuardian** monitors individual agent trajectories and provides steering interventions
- **ConductorService** analyzes system coherence and detects duplicate work
- **MonitoringLoop** orchestrates Guardian and Conductor analyses
- **GuardianService** provides emergency intervention capabilities

However, these services lack:
1. **Unified coordination** - No central authority to orchestrate responses across services
2. **Team-based management** - Agents are monitored individually, not as coordinated teams
3. **Adaptive policy enforcement** - Static policies without learning from intervention outcomes
4. **Hierarchical supervision** - No way to supervise groups of agents or nested supervisor hierarchies
5. **Proactive resource management** - Reactive rather than predictive resource allocation

### Desired State

A Supervisor Agent that:
1. **Orchestrates all monitoring services** under a unified decision-making framework
2. **Manages agent teams** with role-based coordination and shared objectives
3. **Learns optimal policies** from intervention outcomes and adapts autonomy levels
4. **Supports hierarchical supervision** for managing large-scale agent deployments
5. **Proactively prevents issues** through predictive analysis and preventive actions

### Impact of Not Building

Without the Supervisor Agent:
- Monitoring services remain fragmented, requiring manual coordination
- Team-based workflows require custom orchestration code for each project
- Intervention policies cannot adapt based on learned effectiveness
- Large-scale deployments (50+ agents) lack scalable supervision structure
- Human operators must manually interpret and act on alerts from multiple services

## Goals & Success Metrics

### Primary Goals

1. **Unified Monitoring Orchestration**: Single service that coordinates Guardian, Conductor, and MonitoringLoop with coherent decision-making
2. **Team-Based Agent Management**: Enable grouping agents into teams with shared objectives and coordinated actions
3. **Adaptive Policy Enforcement**: Learn from intervention outcomes to automatically adjust policy thresholds and autonomy levels
4. **Hierarchical Supervision**: Support nested supervisor hierarchies for scalable management of large agent fleets
5. **Proactive Issue Prevention**: Predict and prevent issues before they become critical through trend analysis

### Success Metrics

| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| Mean Time to Resolution (MTTR) | ~10 minutes (manual) | <2 minutes (automated) | Track time from anomaly detection to resolution |
| Intervention Success Rate | ~70% (static policies) | >90% (adaptive policies) | Track outcome of each automated intervention |
| Agent Team Coordination Overhead | ~30% (manual) | <5% (automated) | Measure time spent coordinating team actions |
| Supervisor Coverage | N/A | 100% of agents supervised | Database query for agent-to-supervisor mapping |
| False Positive Intervention Rate | ~15% | <5% | Track interventions that didn't improve outcomes |

## User Stories

### Primary User: System Operator (DevOps/SRE)

1. **Supervisor Dashboard Visibility**
   As a system operator, I want a unified dashboard showing all supervisors, their teams, and current health status so that I can quickly assess system-wide agent health.

   Acceptance Criteria:
   - [ ] Dashboard displays hierarchical supervisor/agent relationship
   - [ ] Real-time health status for each supervisor and team
   - [ ] Drill-down capability to view individual agents within teams
   - [ ] Alert summary grouped by supervisor

2. **Policy Configuration**
   As a system operator, I want to configure intervention policies per supervisor so that I can enforce organization-specific rules for different agent teams.

   Acceptance Criteria:
   - [ ] CRUD API for supervisor policies
   - [ ] Policy templates for common scenarios (restart, quarantine, reallocate)
   - [ ] Policy validation before activation
   - [ ] Policy versioning and rollback

3. **Intervention Review and Approval**
   As a system operator, I want to review and approve high-impact interventions so that I maintain control over critical system changes.

   Acceptance Criteria:
   - [ ] Approval queue for interventions above configured threshold
   - [ ] Intervention details include rationale, expected impact, and rollback plan
   - [ ] One-click approve/reject interface
   - [ ] Audit log of all approval decisions

### Secondary User: Developer (Agent Configuration)

4. **Team Configuration**
   As a developer, I want to define agent teams with shared objectives so that agents can coordinate automatically on multi-step tasks.

   Acceptance Criteria:
   - [ ] Define teams with agent types and counts
   - [ ] Specify team objectives and success criteria
   - [ ] Configure team-level communication patterns
   - [ ] Validate team configuration before deployment

5. **Supervisor Hierarchy Design**
   As a developer, I want to design hierarchical supervision structures so that large-scale deployments remain manageable.

   Acceptance Criteria:
   - [ ] Define parent-child supervisor relationships
   - [ ] Configure escalation paths between supervisor levels
   - [ ] Set policy inheritance rules
   - [ ] Visual hierarchy validation tool

## Scope

### In Scope

- **Supervisor Core Service**
  - Supervisor lifecycle management (spawn, configure, monitor, terminate)
  - Policy engine with adaptive learning
  - Intervention orchestration across Guardian, Conductor, and custom actions
  - Team management and coordination
  - Hierarchical supervision support

- **Policy Framework**
  - Policy definition language (YAML/JSON)
  - Policy validation and simulation
  - Policy versioning and rollback
  - Adaptive learning from intervention outcomes
  - Multi-level policy inheritance

- **Integration Layer**
  - Orchestrate existing MonitoringLoop, Guardian, Conductor services
  - Direct integration with TaskQueueService for task reassignment
  - Integration with AgentRegistry for agent lifecycle
  - Alert aggregation and correlation from all services

- **Observability**
  - Supervisor health metrics and status
  - Intervention tracking and outcomes
  - Policy effectiveness analytics
  - Team performance metrics

### Out of Scope

- **Individual agent monitoring** (handled by IntelligentGuardian)
- **System coherence analysis** (handled by ConductorService)
- **Emergency intervention primitives** (handled by GuardianService)
- **Frontend dashboard implementation** (separate frontend project)
- **Agent implementation details** (supervisor manages existing agents)

### Future Considerations

- **Multi-region supervision**: Supervisors spanning geographic regions
- **Cross-organization supervision**: Supervisors managing agents across org boundaries
- **A/B testing for policies**: Compare policy effectiveness experimentally
- **Natural language policy interface**: Define policies using natural language
- **Integration with external monitoring**: Prometheus, Datadog, etc.

## Constraints

### Technical Constraints

- **Existing Service Integration**: Must work with current MonitoringLoop, Guardian, Conductor without breaking changes
- **Database Schema**: Requires new tables but must maintain compatibility with existing 23 tables
- **API Compatibility**: New supervisor APIs must follow existing FastAPI patterns
- **Performance**: Supervisor orchestration overhead must be <100ms per action
- **Scalability**: Must support 100+ agents per supervisor, 10+ supervisor levels in hierarchy

### Business Constraints

- **No breaking changes**: Existing agent workflows must continue unchanged
- **Backward compatibility**: Current monitoring features must remain functional
- **Deployment timeline**: Initial release within 4-6 weeks
- **Resource limits**: Supervisor overhead must be minimal (<5% CPU, <1GB memory per supervisor)

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Policy misconfiguration causes widespread agent failures | Medium | High | Policy validation sandbox, dry-run mode, staged rollout with canary testing |
| Supervisor becomes single point of failure | Low | Critical | Run supervisors as stateless services, support supervisor failover, store state in database |
| Hierarchical supervision complexity leads to unmanageable systems | Medium | Medium | Limit hierarchy depth to 5 levels, provide visualization tools, enforce complexity limits |
| Adaptive learning produces unexpected policies | Low | High | Policy change rate limiting, human approval for significant policy shifts, explicit policy bounds |
| Performance degradation at scale | Medium | Medium | Async supervisor operations, batch processing for large teams, caching for frequent decisions |

## Dependencies

- **MonitoringLoop**: Must be running and accessible for coordinated analysis cycles
- **IntelligentGuardian**: Required for individual agent trajectory analysis
- **ConductorService**: Required for system coherence analysis
- **GuardianService**: Required for emergency intervention primitives
- **TaskQueueService**: Required for task reassignment and priority changes
- **AgentRegistry**: Required for agent lifecycle management
- **EventBusService**: Required for publishing supervisor events

## Open Questions

- [ ] Should supervisors support multi-tenancy (multiple orgs sharing supervisor infrastructure)?
- [ ] What is the maximum reasonable hierarchy depth for supervision?
- [ ] Should policy learning be per-supervisor or shared across supervisors?
- [ ] How should supervisors handle conflicting recommendations from Guardian and Conductor?
- [ ] Should there be a "supervisor of supervisors" at the top of every hierarchy?
