---
description: Review code for security, quality, and maintainability with structured feedback
globs: ["**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"]
---

# Code Review

Perform thorough code reviews using this structured approach.

## Review Checklist

### 1. Security (CRITICAL)
- [ ] **Injection vulnerabilities**: SQL, command, XSS, template injection
- [ ] **Authentication**: Proper auth checks, secure session handling
- [ ] **Authorization**: Access control on all sensitive operations
- [ ] **Secrets**: No hardcoded credentials, API keys, tokens
- [ ] **Input validation**: All user input validated and sanitized
- [ ] **Output encoding**: Proper encoding for context (HTML, URL, JS)

### 2. Logic & Correctness
- [ ] **Requirements met**: Code implements what was specified
- [ ] **Edge cases**: Null/empty/boundary conditions handled
- [ ] **Error handling**: Exceptions caught and handled appropriately
- [ ] **Race conditions**: Concurrent access handled correctly
- [ ] **State management**: State transitions are valid

### 3. Performance
- [ ] **N+1 queries**: Database queries in loops
- [ ] **Memory leaks**: Unclosed resources, retained references
- [ ] **Unnecessary computation**: Repeated calculations, missing caching
- [ ] **Blocking operations**: Async operations not blocking main thread
- [ ] **Large payloads**: Response sizes reasonable

### 4. Maintainability
- [ ] **Single responsibility**: Each function/class has one purpose
- [ ] **DRY**: No duplicated code
- [ ] **Naming**: Clear, descriptive names for variables/functions
- [ ] **Comments**: Complex logic explained, not obvious code
- [ ] **Type hints**: Types annotated (Python/TypeScript)

### 5. Testing
- [ ] **Test coverage**: New code has tests
- [ ] **Test quality**: Tests verify behavior, not implementation
- [ ] **Edge case tests**: Boundary conditions tested
- [ ] **Integration tests**: System interactions tested

## Review Output Format

```markdown
## Code Review: {file/component}

### Summary
{1-2 sentence overall assessment}

### 🔴 Critical Issues
{Must fix before merge}

#### Issue 1: {Title}
- **Location**: `file.py:42`
- **Problem**: {Description}
- **Impact**: {Security/correctness impact}
- **Fix**: {Suggested solution}

### 🟡 Suggestions
{Should consider fixing}

#### Suggestion 1: {Title}
- **Location**: `file.py:88`
- **Current**: {What it does now}
- **Suggested**: {Better approach}
- **Reason**: {Why this is better}

### 🟢 Positive Notes
{Good patterns to highlight}

- Good use of {pattern} at `file.py:100`
- Clear error handling in {function}

### Verdict
- [ ] ✅ Approve
- [ ] 🔄 Request Changes
- [ ] 💬 Needs Discussion
```

## Security Patterns to Flag

### Python
```python
# 🔴 SQL Injection
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")  # BAD
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))  # GOOD

# 🔴 Command Injection
os.system(f"ls {user_input}")  # BAD
subprocess.run(["ls", user_input], check=True)  # GOOD

# 🔴 Path Traversal
open(f"/data/{user_filename}")  # BAD
safe_path = Path("/data") / user_filename
if safe_path.resolve().is_relative_to(Path("/data")):  # GOOD
    open(safe_path)
```

### TypeScript/JavaScript
```typescript
// 🔴 XSS
element.innerHTML = userInput;  // BAD
element.textContent = userInput;  // GOOD

// 🔴 Prototype Pollution
Object.assign(target, JSON.parse(userInput));  // BAD
// Validate shape before merging

// 🔴 SSRF
fetch(userProvidedUrl);  // BAD
// Validate URL against allowlist
```

## Performance Patterns to Flag

```python
# 🔴 N+1 Query
for user in users:
    orders = db.query(Order).filter(Order.user_id == user.id).all()  # BAD

# ✅ Eager Loading
users = db.query(User).options(joinedload(User.orders)).all()  # GOOD

# 🔴 Repeated Computation
for item in items:
    expensive = calculate_expensive_thing()  # BAD (repeated)
    process(item, expensive)

# ✅ Cache Result
expensive = calculate_expensive_thing()  # GOOD (once)
for item in items:
    process(item, expensive)
```

## Review Commands

```bash
# View changes in a PR
git diff main...HEAD

# Check specific file
git diff main -- path/to/file.py

# View commit history
git log --oneline main..HEAD

# Check for secrets (use git-secrets or similar)
git secrets --scan
```
