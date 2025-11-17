# Result Submission System

**Task-level and workflow-level result tracking with validation**

---

## Overview

The Result Submission System provides two types of result tracking:

1. **AgentResult** — Task-level achievements (multiple per task)
2. **WorkflowResult** — Workflow-level completion (marks workflow done)

### Purpose

- **Accountability:** Audit trail of agent work
- **Quality Assurance:** Evidence-based validation
- **Knowledge Preservation:** Document solutions for future reference
- **Trust Building:** Verification tracking

---

## Result Types

### Task-Level Results (AgentResult)

Agents submit results for individual tasks showing what they accomplished.

**Features:**
- Multiple results per task
- Six result types (implementation, analysis, fix, design, test, documentation)
- Verification status tracking
- Markdown content storage
- Immutable records

**Use when:**
- Documenting task completion
- Providing evidence of work
- Creating audit trail
- Supporting validation review

### Workflow-Level Results (WorkflowResult)

Agents submit final results marking entire workflow completion.

**Features:**
- One or more submissions per workflow
- Automatic validation trigger
- Configurable workflow termination  
- Evidence collection
- Status tracking (pending_validation, validated, rejected)

**Use when:**
- Workflow goal achieved
- Solution found
- Definitive deliverable complete
- Ready for final validation

---

## Quick Start

### Submit Task Result

```python
# Via API
POST /api/v1/report_results
Headers: X-Agent-ID: agent-123
{
  "task_id": "task-456",
  "markdown_file_path": "/path/to/results.md",
  "result_type": "implementation",
  "summary": "Implemented feature successfully"
}
```

### Submit Workflow Result

```python
# Via API
POST /api/v1/submit_result
Headers: X-Agent-ID: agent-123
{
  "workflow_id": "workflow-789",
  "markdown_file_path": "/path/to/solution.md",
  "explanation": "Found the solution",
  "evidence": ["Evidence 1", "Evidence 2"]
}
```

---

## File Validation Rules

All result submissions must follow:

1. **File exists** — Must be readable
2. **Markdown format** — .md extension required
3. **Size limit** — Maximum 100KB
4. **Path security** — No ".." directory traversal
5. **Task ownership** — Agent must own task (for AgentResult)

### Examples

```python
# ✅ Valid
/tmp/results.md
./output/analysis.md
/workspace/solution.md

# ❌ Invalid
/tmp/results.txt           # Not markdown
/tmp/large_file.md        # Over 100KB
../../../etc/passwd.md    # Path traversal
```

---

## Result Type Classifications

### AgentResult Types

| Type | Description | Use Case |
|------|-------------|----------|
| `implementation` | Code or feature implementation | New features, components |
| `analysis` | Research or analysis results | Investigation, research |
| `fix` | Bug fix or issue resolution | Bug fixes, patches |
| `design` | Design documents or architecture | System design, diagrams |
| `test` | Test implementation or results | Test suites, test results |
| `documentation` | Documentation creation | READMEs, guides, docs |

---

## Verification System

### Verification States (AgentResult)

| State | Description | When Applied |
|-------|-------------|--------------|
| `unverified` | Default state | On creation |
| `verified` | Claims validated | Validation passed |
| `disputed` | Claims questioned | Validation failed |

### How Verification Works

1. **Agent submits** task result → Status: unverified
2. **Validator reviews** task → Creates validation_review
3. **Verification links** result to review
4. **Status updates** to verified or disputed
5. **Timestamp recorded** in verified_at

**API:**
```python
# Validator marks result as verified
result_service.verify_task_result(
    result_id="result-123",
    validation_review_id="review-456",
    verified=True
)
```

---

## Workflow Result Lifecycle

```
Agent submits result
  ↓
WorkflowResult created (status: pending_validation)
  ↓
If has_result=true: Validator agent spawned
  ↓
Validator reviews against result_criteria
  ↓
Validator calls /submit_result_validation
  ↓
If PASS + on_result_found="stop_all":
  → Status: validated
  → Workflow terminated
  → Event: workflow.termination.requested
  
If PASS + on_result_found="do_nothing":
  → Status: validated
  → Workflow continues
  
If FAIL:
  → Status: rejected
  → Feedback provided
  → Agent can resubmit
```

---

## Markdown Template

### Required Sections

```markdown
# Task/Workflow Results: [Title]

## Summary
2-3 sentence overview of achievements

## Detailed Achievements
- Bullet list of completed items
- Technical implementation details

## Artifacts Created
| File Path | Type | Description |
|-----------|------|-------------|
| src/auth.py | Python | Authentication logic |
| tests/test_auth.py | Python | Unit tests |

## Validation Evidence
- Test results
- Manual verification steps
- Performance metrics

## Known Limitations
- Current limitations
- Workarounds available

## Recommended Next Steps
- Immediate actions needed
- Future enhancements
```

---

## Database Schema

### `agent_results` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (PK) | UUID |
| `agent_id` | String (FK) | Agent who submitted |
| `task_id` | String (FK) | Task being reported on |
| `markdown_content` | Text | Full markdown content |
| `markdown_file_path` | Text | Source file path |
| `result_type` | String | implementation, analysis, etc. |
| `summary` | Text | Brief summary |
| `verification_status` | String | unverified, verified, disputed |
| `verified_at` | Timestamp | When verified |
| `verified_by_validation_id` | String | Validation review link |
| `created_at` | Timestamp | Submission time |

### `workflow_results` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (PK) | UUID |
| `workflow_id` | String (FK) | Workflow (ticket) |
| `agent_id` | String (FK) | Agent who submitted |
| `markdown_file_path` | Text | Result file path |
| `explanation` | Text | What was accomplished |
| `evidence` | JSONB | Evidence items array |
| `status` | String | pending_validation, validated, rejected |
| `validated_at` | Timestamp | When validated |
| `validation_feedback` | Text | Validator feedback |
| `created_at` | Timestamp | Submission time |

---

## API Reference

### Task-Level Results

**Submit Task Result:**
```http
POST /api/v1/report_results
Headers: X-Agent-ID: {agent-id}
Body: {
  "task_id": "task-uuid",
  "markdown_file_path": "/path/to/results.md",
  "result_type": "implementation",
  "summary": "Brief summary"
}
```

**Get Task Results:**
```http
GET /api/v1/tasks/{task_id}/results
```

### Workflow-Level Results

**Submit Workflow Result:**
```http
POST /api/v1/submit_result
Headers: X-Agent-ID: {agent-id}
Body: {
  "workflow_id": "workflow-uuid",
  "markdown_file_path": "/path/to/solution.md",
  "explanation": "Found solution",
  "evidence": ["Evidence 1", "Evidence 2"]
}
```

**Validate Workflow Result (validator-only):**
```http
POST /api/v1/submit_result_validation
Headers: X-Validator-ID: {validator-id}
Body: {
  "result_id": "result-uuid",
  "validation_passed": true,
  "feedback": "All criteria met",
  "evidence": [...]
}
```

**Get Workflow Results:**
```http
GET /api/v1/workflows/{workflow_id}/results
```

---

## Integration

### With Validation System

When task enters validation:
- Validator reviews task
- Can verify AgentResults via `verify_task_result()`
- Links verification to validation_review

### With Discovery System

Diagnostic recovery uses Discovery:
- Creates TaskDiscovery (type: diagnostic_no_result)
- Spawns recovery task
- Maintains branching audit trail

### With Phase System

Workflow results respect phases:
- Can be submitted from any phase
- Validation checks against result_criteria
- Termination respects phase boundaries

---

## Best Practices

### For Agents

1. **Submit comprehensive evidence** in markdown
2. **Test before submitting** workflow results
3. **Provide clear reproduction steps**
4. **Document methodology thoroughly**
5. **Be honest about confidence levels**

### For Workflow Configuration

1. **Write specific result_criteria** (not vague)
2. **Consider stop_all vs do_nothing** carefully
3. **Test criteria with example results**
4. **Provide detailed requirements**

### For Validators

1. **Read entire result file carefully**
2. **Check each criterion systematically**
3. **Provide specific feedback** on failures
4. **Include evidence** in validation decision

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| File not found | File doesn't exist | Verify file path |
| File too large | Over 100KB | Split into multiple results |
| Not markdown | Wrong file type | Use .md extension |
| Path traversal | Security violation | Remove ".." from path |
| Not assigned | Wrong agent | Check task assignment |
| Already validated | Immutability | Create new submission |

---

## Examples

### Example 1: Implementation Result

```markdown
# Task Results: User Authentication

## Summary
Implemented JWT-based authentication with refresh tokens,
achieving 100% test coverage.

## Detailed Achievements
- JWT token generation and validation
- Refresh token mechanism
- Token blacklisting on logout
- 15 unit tests passing
- Integration with existing user model

## Artifacts Created
| File | Description |
|------|-------------|
| src/auth/jwt.py | JWT logic |
| src/auth/refresh.py | Refresh tokens |
| tests/test_auth.py | 15 tests |

## Validation Evidence
```
pytest tests/test_auth.py
===== 15 passed in 0.5s =====
```

## Known Limitations
- Tokens expire after 1 hour
- No multi-device support yet

## Recommended Next Steps
- Add token refresh UI
- Implement multi-device management
```

### Example 2: Workflow Result

```markdown
# Solution: Password Cracking Challenge

## Solution Statement
Password is: `mysecretpassword123`

## Primary Evidence
Execution output:
```
./crackme
Enter password: mysecretpassword123
Access granted! Flag: CTF{success}
```

## Methodology
1. Analyzed binary with Ghidra
2. Found hardcoded password comparison
3. Extracted password from strings
4. Verified with execution

## Confidence Assessment
100% confident - verified with successful execution
```

---

## Support

**Documentation:**
- Diagnostic System: `docs/diagnostic/README.md`
- Validation System: `docs/validation/README.md`

**Database Queries:**
```sql
-- Check results for task
SELECT * FROM agent_results WHERE task_id = 'task-123';

-- Check workflow completion
SELECT * FROM workflow_results WHERE workflow_id = 'workflow-456';

-- Verification status breakdown
SELECT verification_status, COUNT(*)
FROM agent_results
GROUP BY verification_status;
```

---

**For issues:** Check diagnostic runs and validation reviews in database

