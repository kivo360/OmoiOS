---
title: "Use Case Posts"
category: use-cases
tags: [use-cases, examples, implementation, proof, practical]
description: "Specific implementation examples that demonstrate practical value"
post_count: 12
last_updated: 2026-01-13
# Scheduling constraints
scheduling:
  best_days: [wednesday]
  best_times: ["12:00"]
  min_gap_hours: 48
  max_per_day: 1
  max_per_week: 2
  time_sensitive: false
  engagement_level: medium
  notes: "Practical examples. Pairs with vision content."
---

# Use Case Posts

Specific implementation examples that prove the concept. Grounds the vision in reality.

---

### Use Case: Webhook Implementation

```
use case: webhook system

spec-driven approach:
1. requirements: delivery guarantees, retry logic, signing
2. design: service architecture, data model
3. tasks: 8 discrete work units
4. execution: agents implement each task
5. review: verify against spec

result: webhook system that actually meets requirements

vs vibe coding: "build me webhooks" → hope for the best
```

---

### Use Case: API Endpoint

```
spec-driven api development:

requirement: "POST /api/tasks creates task, returns 201, validates input"

agent gets:
- exact endpoint path
- expected status code
- input validation rules
- response schema

vs vibe: "make an endpoint for tasks"

one is testable
one is vibes
```

---

### Use Case: Database Migration

```
spec-driven migrations:

1. design specifies exact schema
2. task: "create migration for users table with fields X, Y, Z"
3. agent implements migration
4. validation: compare output to design spec

vs vibe: "add users to the database"

which one would you trust in production?
```

---

### Use Case: Phase Gate Example

```
phase gate in action:

phase 1: requirements doc approved ✓
phase 2: design doc approved ✓
phase 3: tasks breakdown approved ✓
phase 4: agents execute autonomously
phase 5: PR ready for review

human involved at decision points
ai handles execution between

control + speed
```

---

### Use Case: Bug Fix Workflow

```
bug fix with spec-driven approach:

1. spec: describe expected behavior vs actual behavior
2. design: identify root cause, propose fix approach
3. task: implement fix + add regression test
4. verify: test passes, expected behavior restored

vs vibe: "fix the login bug"
→ agent guesses what's wrong
→ "fix" breaks something else
→ repeat
```

---

### Use Case: Feature Addition

```
adding pagination to an api:

spec:
- page_size parameter (default 20, max 100)
- page_token for cursor-based pagination
- returns next_page_token if more results

design:
- modify query layer
- update response schema
- add validation

tasks:
1. add pagination parameters to schema
2. implement cursor logic
3. update response format
4. add tests

vs: "add pagination"
```

---

### Use Case: Multi-Agent Feature

```
multi-agent feature build:

feature: user notifications

agent 1: database schema
agent 2: api endpoints
agent 3: notification service
agent 4: frontend components

coordination:
- agents 2,3,4 blocked until agent 1 completes
- agent 3 blocked until agent 2 completes
- all use shared design spec

result: components that actually fit together
```

---

### Use Case: Stuck Recovery

```
stuck detection in action:

agent: trying same fix for 5 minutes
guardian: detects repetition pattern
intervention: "approach X isn't working, try Y"
agent: pivots to new approach
result: unstuck, continues progress

vs: agent loops until you notice
→ 2 hours of wasted tokens
→ you close the tab
```

---

### Use Case: Code Review Prep

```
pre-review checklist (spec-driven):

✓ implementation matches requirement spec
✓ tests cover acceptance criteria
✓ code follows design patterns from design doc
✓ no unrelated changes (spec prevents drift)

vs vibe-coded PR:
- matches... something?
- tests cover... some things?
- follows... some pattern?
- might have extra "improvements"
```

---

### Use Case: Refactoring

```
spec-driven refactoring:

spec: "extract authentication logic to shared middleware"

design:
- identify all auth patterns in codebase
- design unified middleware interface
- define migration path

tasks:
1. create middleware skeleton
2. migrate endpoint A
3. migrate endpoint B
4. remove duplicated code
5. verify all endpoints still work

vs: "clean up the auth code"
→ agent "improves" random things
→ breaks 3 unrelated features
```

---

### Use Case: Testing Strategy

```
spec-driven testing:

requirements spec defines:
- acceptance criteria for each feature
- edge cases to handle
- error scenarios

test generation:
- each acceptance criterion → test case
- each edge case → test case
- each error scenario → test case

result: tests that verify what matters

vs: "write tests"
→ agent writes tests for random things
→ 80% coverage of 20% that matters
```

---

### Use Case: Documentation

```
spec-driven documentation:

source of truth: requirements + design docs

documentation task:
- extract API interface from design
- generate endpoint documentation
- include examples from acceptance criteria

result: docs that match implementation

vs: "document the api"
→ docs that might match
→ drift immediately
→ nobody trusts them
```

