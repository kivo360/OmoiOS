# Ticket Analysis Guide

## Overview

This guide provides a framework for analyzing tickets in the OmoiOS system. Ticket analysis ensures that implementation work is well-understood, properly scoped, and aligned with requirements and design specifications.

## Purpose of Ticket Analysis

Ticket analysis serves multiple purposes:
1. **Validation**: Ensure the ticket is complete, actionable, and properly linked to requirements
2. **Planning**: Identify dependencies, risks, and implementation approach
3. **Estimation**: Assess complexity and effort required
4. **Communication**: Provide clarity for implementers and stakeholders

## Ticket Analysis Framework

### 1. Basic Information Review

**Check:**
- [ ] Ticket ID is unique and follows naming convention (TKT-XXX)
- [ ] Title is clear and describes the work
- [ ] Status is appropriate (backlog, ready, in_progress, blocked, completed)
- [ ] Priority is set (HIGH, MEDIUM, LOW)
- [ ] Estimate is provided (S, M, L, XL)
- [ ] Created/updated timestamps are present

### 2. Requirement Linkage

**Verify:**
- [ ] All referenced requirements exist in `/workspace/.omoi_os/requirements/`
- [ ] Requirements are in approved state
- [ ] Ticket scope fully covers the requirements (no gaps)
- [ ] No unnecessary work beyond requirements (no scope creep)

### 3. Design Reference

**Check:**
- [ ] Design document exists and is referenced
- [ ] Design document is approved
- [ ] Technical approach is clearly documented
- [ ] Architecture decisions are explained

### 4. Task Breakdown

**Analyze:**
- [ ] Tasks are granular and actionable
- [ ] Task order is logical
- [ ] Each task has clear completion criteria
- [ ] Task estimates sum to ticket estimate

### 5. Dependencies

**Identify:**
- **Blocked By**: What must be completed before this ticket?
- **Blocks**: What is waiting on this ticket?
- **Related**: What other tickets are relevant?

### 6. Acceptance Criteria

**Validate:**
- [ ] Criteria are specific and testable
- [ ] Criteria cover functional requirements
- [ ] Criteria cover non-functional requirements (performance, security)
- [ ] Success conditions are clear

### 7. Implementation Approach

**Review:**
- [ ] Key files to modify are identified
- [ ] API changes are documented
- [ ] Database changes are documented
- [ ] Migration strategy is defined

### 8. Testing Strategy

**Ensure:**
- [ ] Unit test scope is defined
- [ ] Integration test scope is defined
- [ ] Manual testing steps are provided
- [ ] Edge cases are considered

### 9. Risk Assessment

**Evaluate:**
- **Technical Risks**: New technologies, complex logic, performance concerns
- **Dependency Risks**: External services, blocking tickets
- **Scope Risks**: Ambiguous requirements, scope creep
- **Timeline Risks**: Estimation accuracy, resource availability

### 10. Rollback Plan

**Verify:**
- [ ] Rollback steps are documented
- [ ] Database migration rollback is safe
- [ ] No data loss in rollback

## Example: Ticket Analysis for TKT-001

### Ticket: TKT-001 - Implement Webhook Notifications

**Analysis Date**: 2026-01-18
**Analyst**: System

---

#### 1. Basic Information ✅

- **ID**: TKT-001
- **Title**: Implement Webhook Notifications
- **Status**: backlog
- **Priority**: HIGH (appropriate - enables critical monitoring)
- **Estimate**: L (Large - multi-service implementation)
- **Created**: 2025-12-29
- **Feature**: webhook-notifications

**Assessment**: All basic metadata present and properly formatted.

---

#### 2. Requirement Linkage ✅

**Referenced Requirements**:
- REQ-WEBHOOK-CONFIG-001 (Project-level webhook configuration)
- REQ-WEBHOOK-CONFIG-002 (Ticket-level webhook configuration)
- REQ-WEBHOOK-EVENT-001 (Task completion events)
- REQ-WEBHOOK-EVENT-002 (Task failure events)
- REQ-WEBHOOK-EVENT-003 (Agent stuck events)

**Assessment**: All requirements follow EARS format (WHEN/THE SYSTEM SHALL). Comprehensive coverage of webhook functionality.

---

#### 3. Design Reference ✅

**Design Document**: `designs/webhook-notifications.md`

**Key Design Elements**:
- Uses existing EventBusService infrastructure
- Two-tier service architecture:
  - `WebhookDeliveryService`: HTTP delivery with retry logic
  - `WebhookNotificationService`: Event subscription and dispatch
- URL resolution: ticket-level overrides project-level

**Assessment**: Design leverages existing patterns, minimizes new dependencies.

---

#### 4. Task Breakdown ✅

**Tasks** (6 total):
1. TSK-001: Add model fields
2. TSK-002: Create database migration
3. TSK-003: Implement WebhookDeliveryService
4. TSK-004: Implement WebhookNotificationService
5. TSK-005: Update API routes
6. TSK-006: Add tests

**Assessment**: Logical order (models → migration → services → API → tests). Each task is atomic.

---

#### 5. Dependencies ✅

**Blocked By**: None (can start immediately)
**Blocks**: None (other features can proceed)
**Related**: TKT-002 (webhook integrations - future enhancement)

**Assessment**: No blocking dependencies. Clean execution path.

---

#### 6. Acceptance Criteria ✅

**Criteria** (8 items):
- Model changes (Project.webhook_url, Ticket.webhook_url)
- Database migration
- Service implementations
- API endpoint updates
- Performance (5-10 second delivery)
- Error handling (failed deliveries don't block tasks)

**Assessment**: Specific, measurable, testable. Covers functional and non-functional requirements.

---

#### 7. Implementation Approach ✅

**Key Files**:
- `backend/omoi_os/models/project.py` - Add webhook_url
- `backend/omoi_os/models/ticket.py` - Add webhook_url
- `backend/omoi_os/services/webhook_delivery.py` - New service
- `backend/omoi_os/services/webhook_notification.py` - New service

**API Changes**:
- PATCH /api/v1/projects/{id} - accepts webhook_url
- PATCH /api/v1/tickets/{id} - accepts webhook_url

**Database Schema**:
```sql
ALTER TABLE projects ADD COLUMN webhook_url VARCHAR(2048);
ALTER TABLE tickets ADD COLUMN webhook_url VARCHAR(2048);
```

**Assessment**: Clear file locations, API contracts, and schema changes.

---

#### 8. Testing Strategy ✅

**Unit Tests**:
- WebhookDeliveryService retry logic
- URL resolution precedence (ticket overrides project)

**Integration Tests**:
- Event triggers webhook delivery end-to-end
- API endpoints accept and store webhook URLs

**Manual Testing**:
- Configure webhook, trigger task completion, verify payload

**Assessment**: Comprehensive test coverage across layers.

---

#### 9. Risk Assessment ⚠️

**Technical Risks**:
- ✅ **LOW**: Uses existing EventBusService patterns
- ⚠️ **MEDIUM**: Retry logic complexity (exponential backoff, max attempts)
- ✅ **LOW**: HTTP client reliability (use httpx with timeouts)

**Dependency Risks**:
- ✅ **LOW**: No external service dependencies
- ✅ **LOW**: No blocking tickets

**Scope Risks**:
- ✅ **LOW**: Well-defined non-goals (no auth, no third-party integrations)
- ⚠️ **MEDIUM**: Payload schema not fully specified in ticket

**Timeline Risks**:
- ⚠️ **MEDIUM**: Large estimate (L) - ensure tasks are parallelizable
- ✅ **LOW**: No hard deadline mentioned

**Mitigation**:
1. Define webhook payload schema in design doc before implementation
2. Implement retry logic with configurable parameters
3. Use httpx with 10-second timeout for deliveries
4. Parallelize development: Models/migration can proceed while services are designed

---

#### 10. Rollback Plan ✅

**Rollback Steps**:
1. Run `alembic downgrade -1` to remove columns
2. Revert code changes via `git revert`

**Assessment**: Safe rollback. New nullable columns can be removed without data loss.

---

### Overall Assessment: READY FOR IMPLEMENTATION ✅

**Strengths**:
- Clear requirements linkage
- Well-defined acceptance criteria
- Logical task breakdown
- Safe rollback plan

**Recommendations**:
1. **Before Implementation**: Define exact webhook payload schema (JSON structure) in design doc
2. **During Implementation**: Add logging for webhook delivery failures (aid debugging)
3. **Testing**: Test with unreachable URLs to verify retry logic
4. **Documentation**: Document webhook payload format for consumers

**Estimated Complexity**: Large (L) ✅
- 2 models + migration
- 2 new services
- API endpoint updates
- Comprehensive testing

**Ready to Assign**: Yes, after payload schema is documented.

---

## Ticket Analysis Checklist

Use this checklist for quick ticket analysis:

```markdown
## Ticket Analysis: [TKT-ID] - [Title]

**Date**: YYYY-MM-DD
**Analyst**: [Name]

### Quick Assessment

- [ ] Basic metadata complete
- [ ] Requirements linked and approved
- [ ] Design document referenced
- [ ] Tasks are atomic and ordered
- [ ] Dependencies identified
- [ ] Acceptance criteria testable
- [ ] Implementation approach clear
- [ ] Testing strategy defined
- [ ] Risks assessed
- [ ] Rollback plan safe

### Decision

- [ ] ✅ READY FOR IMPLEMENTATION
- [ ] ⚠️ NEEDS CLARIFICATION (see notes)
- [ ] ❌ BLOCKED (see dependencies)

### Notes

[Additional context, recommendations, or concerns]
```

---

## Integration with OmoiOS Workflow

### When to Analyze Tickets

1. **Before Sprint Planning**: Analyze all tickets in the sprint backlog
2. **Before Assignment**: Analyze before assigning to an agent
3. **During Review**: Analyze if ticket is returned or blocked
4. **After Design Approval**: Analyze when design moves to implementation phase

### Who Analyzes Tickets

- **Product Owner**: Requirement linkage, acceptance criteria
- **Tech Lead**: Implementation approach, risk assessment
- **Agent**: Self-analysis before starting work
- **QA**: Testing strategy validation

### Analysis Output

Store analysis in:
- `/workspace/.omoi_os/analysis/TKT-XXX-analysis.md`
- Link from ticket: `analysis_ref: analysis/TKT-XXX-analysis.md`

---

## Common Anti-Patterns

### ❌ Insufficient Detail
**Problem**: "Implement feature X"
**Fix**: Break down into specific acceptance criteria and tasks

### ❌ Missing Requirements
**Problem**: Ticket has no requirement linkage
**Fix**: Create requirements first, then tickets

### ❌ Vague Acceptance Criteria
**Problem**: "Feature should work well"
**Fix**: Define measurable success criteria

### ❌ No Testing Strategy
**Problem**: No test scope defined
**Fix**: Specify unit, integration, and manual tests

### ❌ Unclear Dependencies
**Problem**: "May depend on other tickets"
**Fix**: Explicitly list blocking and blocked tickets

---

## Tools for Ticket Analysis

### CLI Commands

```bash
# Read ticket
cat /workspace/.omoi_os/tickets/TKT-001-webhook-notifications.md

# Find related requirements
grep -r "REQ-WEBHOOK-CONFIG-001" /workspace/.omoi_os/requirements/

# Check design document
cat /workspace/.omoi_os/designs/webhook-notifications.md

# Find related tasks
grep -r "TSK-001" /workspace/.omoi_os/tasks/
```

### Validation Script

```python
# Example: Validate ticket structure
import yaml
from pathlib import Path

def validate_ticket(ticket_path):
    content = Path(ticket_path).read_text()
    # Split frontmatter
    _, frontmatter, body = content.split('---', 2)
    ticket = yaml.safe_load(frontmatter)

    required_fields = ['id', 'title', 'status', 'priority', 'requirements']
    missing = [f for f in required_fields if f not in ticket]

    if missing:
        print(f"❌ Missing fields: {missing}")
    else:
        print(f"✅ Ticket {ticket['id']} is valid")

    return len(missing) == 0

# Usage
validate_ticket('/workspace/.omoi_os/tickets/TKT-001-webhook-notifications.md')
```

---

## Conclusion

Thorough ticket analysis is the foundation of successful implementation. By systematically reviewing requirements, design, tasks, dependencies, and risks, we ensure that work is well-understood and properly scoped before execution begins.

**Remember**: A ticket that passes analysis is ready for autonomous agent execution. A ticket that fails analysis needs human clarification.
