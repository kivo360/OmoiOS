---
description: Debug errors, analyze logs, identify root causes, and suggest fixes
globs: ["**/*.log", "**/logs/**", "**/*.py", "**/*.ts"]
---

# Error Diagnosis

Systematic approach to debugging errors and identifying root causes.

## Diagnosis Workflow

```
1. Reproduce → 2. Isolate → 3. Identify → 4. Fix → 5. Verify
```

### 1. Reproduce the Error
- Get exact steps to reproduce
- Note environment (OS, versions, config)
- Check if error is consistent or intermittent
- Capture full error message and stack trace

### 2. Isolate the Problem
- Identify which component is failing
- Check recent changes (git log, deployments)
- Narrow down to smallest reproducible case
- Check if issue is in your code or dependencies

### 3. Identify Root Cause
- Read the actual error message carefully
- Follow the stack trace top-to-bottom
- Check logs at the time of failure
- Add temporary logging if needed

### 4. Fix the Issue
- Address the root cause, not symptoms
- Consider side effects of the fix
- Add tests to prevent regression

### 5. Verify the Fix
- Reproduce original steps - should work now
- Run full test suite
- Check for unintended side effects

## Common Error Patterns

### Python Exceptions

| Exception | Common Cause | Investigation |
|-----------|--------------|---------------|
| `KeyError` | Missing dict key | Check if key exists before access |
| `AttributeError` | None object access | Check for None before method call |
| `TypeError` | Wrong argument type | Check function signature and input |
| `ImportError` | Missing/circular import | Check import paths and dependencies |
| `ConnectionError` | Network/DB issues | Check connectivity and credentials |

### Stack Trace Analysis

```python
# Example stack trace:
# Traceback (most recent call last):
#   File "app.py", line 42, in handle_request    ← Entry point
#     result = process_data(data)
#   File "processor.py", line 15, in process_data ← Intermediate
#     return transform(data['key'])
#   File "processor.py", line 8, in transform      ← Root cause
#     return value.upper()
# AttributeError: 'NoneType' object has no attribute 'upper'

# The error is at line 8, but the fix might be:
# - Line 15: Check if 'key' exists in data
# - Line 8: Check if value is None before .upper()
# - Caller: Ensure data is properly validated
```

### Database Errors

| Error | Likely Cause | Fix |
|-------|--------------|-----|
| Connection refused | DB not running | Start DB, check port |
| Authentication failed | Bad credentials | Check env vars |
| Timeout | Long query or lock | Optimize query, check locks |
| Unique constraint | Duplicate data | Handle conflict or validate first |
| Foreign key violation | Invalid reference | Check referential integrity |

### API Errors

| Status | Meaning | Investigation |
|--------|---------|---------------|
| 400 | Bad request | Check request body/params |
| 401 | Unauthorized | Check auth token |
| 403 | Forbidden | Check permissions |
| 404 | Not found | Check URL path |
| 500 | Server error | Check server logs |
| 502/503 | Service unavailable | Check upstream services |

## Debugging Commands

### Python

```python
# Quick debugging
import pdb; pdb.set_trace()  # Breakpoint

# Better: ipdb or pudb
import ipdb; ipdb.set_trace()

# Inspect object
print(vars(obj))
print(dir(obj))

# Pretty print
from pprint import pprint
pprint(complex_dict)

# Get traceback
import traceback
traceback.print_exc()
```

### Logging Investigation

```bash
# Search logs for errors
grep -i "error\|exception\|traceback" app.log

# Get context around error
grep -B 5 -A 10 "ERROR" app.log

# Follow logs in real-time
tail -f app.log | grep --line-buffered "ERROR"

# Count error types
grep "ERROR" app.log | cut -d':' -f4 | sort | uniq -c | sort -rn
```

### Git Investigation

```bash
# What changed recently?
git log --oneline -20

# What changed in specific file?
git log --oneline -p -- path/to/file.py

# Who changed this line?
git blame path/to/file.py -L 42,42

# Find when bug was introduced
git bisect start
git bisect bad HEAD
git bisect good v1.0.0
# Test at each step until found
```

### Database Investigation

```sql
-- Check for locks (PostgreSQL)
SELECT * FROM pg_locks WHERE granted = false;

-- Active queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;

-- Kill stuck query
SELECT pg_cancel_backend(pid);
```

## Error Report Template

```markdown
## Error Report

### Summary
{One-line description of the error}

### Environment
- OS: {os}
- Version: {app version}
- Config: {relevant config}

### Steps to Reproduce
1. {Step 1}
2. {Step 2}
3. {Step 3}

### Expected Behavior
{What should happen}

### Actual Behavior
{What actually happens}

### Error Message
```
{Full error message and stack trace}
```

### Logs
```
{Relevant log entries}
```

### Root Cause Analysis
{What is causing this error}

### Proposed Fix
{How to fix it}

### Impact
- Severity: Critical/High/Medium/Low
- Affected users: {scope}
- Workaround: {if any}
```

## Debugging Mindset

1. **Read the error message** - It usually tells you what's wrong
2. **Check the obvious first** - Typos, missing config, wrong version
3. **Reproduce before fixing** - Don't guess at the problem
4. **One change at a time** - Isolate what fixes it
5. **Document the fix** - Help future you and others
