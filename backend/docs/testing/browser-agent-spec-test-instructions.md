# Browser Agent Test: Spec-Driven Development Workflow

## Objective

Test the spec-driven-dev workflow end-to-end by creating a new feature spec through the OmoiOS dashboard. This validates that:
1. The `REQUIRE_SPEC_SKILL` flag is properly enforced
2. Agents follow the complete workflow (not stopping after confirming CLI works)
3. Specs are created with proper YAML frontmatter
4. Specs are synced to the API
5. Tickets and tasks appear in the system

---

## Test Feature: Supervisor Agent

**Feature Description**: A supervisor agent that monitors other agents' progress, detects when they're stuck or drifting from goals, and can intervene with guidance or escalate to humans.

Use this feature idea when creating the ticket in the dashboard.

---

## Pre-Test Setup

### 1. Verify Backend is Running

Before starting, confirm the backend API is accessible:
- Production: `https://api.omoios.dev`
- Check health endpoint: `https://api.omoios.dev/health`

### 2. Have Login Credentials Ready

You'll need valid OmoiOS credentials to log into the dashboard.

---

## Test Instructions

### Step 1: Navigate to Dashboard

1. Go to `https://omoios.dev` (or your local frontend URL)
2. Log in with valid credentials
3. Navigate to the **Projects** section
4. Select an existing project OR create a new test project

### Step 2: Create a New Ticket with Spec-Driven Mode

1. Click **"New Ticket"** or **"Create Ticket"** button
2. Fill in the ticket details:
   - **Title**: `Implement Supervisor Agent for Multi-Agent Monitoring`
   - **Description**:
     ```
     Create a supervisor agent that monitors other agents in the system. The supervisor should:

     1. Track agent heartbeats and detect stale/stuck agents
     2. Analyze agent trajectories to detect goal drift
     3. Provide intervention guidance when agents need help
     4. Escalate to humans when automated intervention fails
     5. Integrate with the existing Guardian and Conductor services

     The supervisor should be lightweight and not interfere with agent autonomy unless necessary.
     ```
   - **Type**: Feature
   - **Priority**: High

3. **CRITICAL**: Select **"Spec-Driven"** workflow mode (NOT "Quick")
   - This should be a dropdown or toggle labeled "Workflow Mode" or similar
   - The spec-driven option triggers `REQUIRE_SPEC_SKILL=true`

4. Click **Submit** or **Create**

### Step 3: Monitor the Sandbox Execution

After creating the ticket, a sandbox should be spawned. Monitor its progress:

1. Navigate to the ticket detail page
2. Look for **Agent Activity**, **Logs**, or **Sandbox Status** section
3. Watch for these key events (in order):

#### Expected Event Sequence:

| Order | Event | What to Look For |
|-------|-------|------------------|
| 1 | Sandbox Created | `sandbox_id` assigned, `REQUIRE_SPEC_SKILL: true` in env |
| 2 | Skill Loaded | Agent reads `/root/.claude/skills/spec-driven-dev/SKILL.md` |
| 3 | Discovery Questions | Agent asks 5-15 clarifying questions about the feature |
| 4 | Spec Files Created | Files appear in `.omoi_os/` directory |
| 5 | Validation Run | `spec_cli.py validate` executed and passes |
| 6 | API Sync | `spec_cli.py sync push` executed |
| 7 | Git Commit | Changes committed and pushed |
| 8 | Task Complete | Sandbox reports success |

### Step 4: Verify Spec Output

After the sandbox completes, verify the specs were created:

1. **Check the repository** for new files in `.omoi_os/`:
   ```
   .omoi_os/
   ├── docs/prd-supervisor-agent.md
   ├── requirements/supervisor-agent.md
   ├── designs/supervisor-agent.md
   ├── tickets/TKT-001.md (or similar)
   └── tasks/TSK-001.md, TSK-002.md, etc.
   ```

2. **Verify YAML frontmatter** in each file:
   - Open any created file
   - Confirm it starts with `---` and has required fields
   - Example for a ticket:
     ```yaml
     ---
     id: TKT-001
     title: Supervisor Agent Core Infrastructure
     status: backlog
     priority: HIGH
     ---
     ```

3. **Check the dashboard** for synced items:
   - Navigate to the project's Tickets list
   - Verify new tickets appear
   - Navigate to Tasks list
   - Verify new tasks appear linked to tickets

### Step 5: Verify API Trace

If the dashboard has an API trace or traceability view:

1. Look for a **Traceability** or **Spec Overview** section
2. Verify the chain: Requirements → Designs → Tickets → Tasks
3. Confirm all items are linked with proper references

---

## Success Criteria Checklist

Use this checklist to evaluate the test:

### Workflow Execution
- [ ] Sandbox was created with `REQUIRE_SPEC_SKILL=true`
- [ ] Agent loaded the spec-driven-dev skill
- [ ] Agent asked discovery questions (5-15 questions)
- [ ] Agent created files in `.omoi_os/` directory
- [ ] Agent ran `spec_cli.py validate` successfully
- [ ] Agent ran `spec_cli.py sync push` successfully
- [ ] Agent committed and pushed to git

### Spec Quality
- [ ] PRD document exists with proper frontmatter
- [ ] Requirements document exists with EARS-format requirements
- [ ] Design document exists with architecture/data models
- [ ] At least 2 tickets were created
- [ ] At least 4 tasks were created
- [ ] All files have valid YAML frontmatter

### API Sync
- [ ] Tickets appear in the dashboard
- [ ] Tasks appear linked to tickets
- [ ] Requirements/designs are visible (if supported)

### Common Failure Modes to Watch For
- [ ] ❌ Agent stopped after confirming `spec_cli.py` works (DID NOT create specs)
- [ ] ❌ Agent created plain markdown without YAML frontmatter
- [ ] ❌ Agent skipped the sync step (files exist locally but not in API)
- [ ] ❌ Agent wrote implementation code instead of specs
- [ ] ❌ Agent skipped discovery questions

---

## Failure Investigation

If the test fails, collect this information:

### 1. Sandbox Logs
- Copy the full sandbox execution log
- Note the sandbox ID: `omoios-XXXXXXXX-XXXXXX`
- Look for error messages or unexpected behavior

### 2. Environment Variables
Verify these were set in the sandbox:
```
REQUIRE_SPEC_SKILL=true
OMOIOS_PROJECT_ID=<uuid>
OMOIOS_API_URL=https://api.omoios.dev
EXECUTION_MODE=exploration
```

### 3. File System State
If possible, check what files exist in the sandbox:
```bash
ls -la .omoi_os/
ls -la .omoi_os/tickets/
ls -la .omoi_os/tasks/
```

### 4. CLI Output
Check if spec_cli.py was run and what it returned:
- Look for `spec_cli.py validate` output
- Look for `spec_cli.py sync push` output
- Look for any error messages

---

## Report Template

After completing the test, fill out this report:

```markdown
# Spec-Driven Dev Test Report

**Date**: YYYY-MM-DD
**Tester**: Browser Agent
**Sandbox ID**: omoios-XXXXXXXX-XXXXXX

## Test Summary
- [ ] PASSED
- [ ] FAILED
- [ ] PARTIAL

## Execution Timeline

| Step | Status | Notes |
|------|--------|-------|
| Sandbox Created | ✅/❌ | |
| Skill Loaded | ✅/❌ | |
| Discovery Questions | ✅/❌ | Count: X questions |
| Spec Files Created | ✅/❌ | Count: X files |
| Validation Passed | ✅/❌ | |
| API Sync Completed | ✅/❌ | |
| Git Commit/Push | ✅/❌ | |

## Files Created

List all files found in `.omoi_os/`:
- [ ] docs/prd-*.md
- [ ] requirements/*.md
- [ ] designs/*.md
- [ ] tickets/TKT-*.md (count: X)
- [ ] tasks/TSK-*.md (count: X)

## Frontmatter Validation

| File | Has Frontmatter | Required Fields Present |
|------|-----------------|------------------------|
| | ✅/❌ | ✅/❌ |

## API Sync Verification

| Item Type | Synced to API | Count |
|-----------|---------------|-------|
| Specs | ✅/❌ | |
| Tickets | ✅/❌ | |
| Tasks | ✅/❌ | |

## Issues Found

1. [Describe any issues]
2. [Describe any issues]

## Recommendations

1. [Suggested fixes]
2. [Suggested fixes]

## Raw Logs

<details>
<summary>Sandbox Execution Logs</summary>

```
[Paste relevant logs here]
```

</details>
```

---

## Alternative Test Features

If you want to run additional tests with different features, use these ideas:

### Option 2: Redis-Based Scalable WebSockets
```
Title: Implement Scalable WebSocket System with Redis Pub/Sub
Description: Create a WebSocket infrastructure that scales horizontally using Redis as a message broker. Support team-based and user-based channels with presence tracking.
```

### Option 3: Continuous Execution Improvements
```
Title: Enhance Continuous Agent Execution Capabilities
Description: Improve the iteration state system to support longer-running agents with better checkpointing, resumption from failures, and progress persistence across sandbox restarts.
```

### Option 4: HMR-Style Hot Refresh for Sandboxes
```
Title: Implement Hot Module Refresh for Daytona Sandboxes
Description: Create an HMR-like system where code changes in a sandbox are immediately reflected without full restart. Include a web view system for real-time preview of changes.
```

---

## Notes for Browser Agent

1. **Take screenshots** at key moments (ticket creation, sandbox status, final results)
2. **Wait for sandbox completion** - this may take 5-15 minutes
3. **Check both the UI and the git repository** for created files
4. **Document exact error messages** if anything fails
5. **Compare against success criteria** before marking complete
