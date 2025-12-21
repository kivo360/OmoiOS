---
description: Git branching, commits, and PR workflow following GitFlow conventions
globs: [".git/**", "**/.gitignore"]
---

# Git Workflow

Follow these conventions for all git operations.

## Branch Naming

```
{type}/{ticket-id}-{short-description}
```

| Type | Purpose | Example |
|------|---------|---------|
| `feature/` | New features | `feature/TKT-123-user-auth` |
| `fix/` | Bug fixes | `fix/TKT-456-login-error` |
| `hotfix/` | Production fixes | `hotfix/TKT-789-security-patch` |
| `refactor/` | Code refactoring | `refactor/TKT-101-cleanup-api` |
| `docs/` | Documentation | `docs/TKT-102-api-docs` |
| `test/` | Test additions | `test/TKT-103-unit-tests` |

## Commit Messages

Use conventional commits format:

```
{type}({scope}): {description}

{body - optional}

{footer - optional}
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring (no functional change)
- `test`: Adding or updating tests
- `docs`: Documentation only
- `chore`: Maintenance tasks
- `style`: Formatting, whitespace (no code change)
- `perf`: Performance improvement

### Examples

```bash
# Simple commit
git commit -m "feat(auth): add JWT token validation"

# With body
git commit -m "fix(api): handle null user in response

The API was returning 500 when user was not found.
Now returns 404 with proper error message.

Fixes TKT-456"

# Breaking change
git commit -m "feat(api)!: change response format to JSON:API

BREAKING CHANGE: Response format changed from custom to JSON:API spec.
Migration guide: docs/migration/v2-response-format.md"
```

## Workflow Commands

### Starting Work
```bash
# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/TKT-123-feature-name

# Or from develop for GitFlow
git checkout develop
git pull origin develop
git checkout -b feature/TKT-123-feature-name
```

### During Development
```bash
# Stage and commit changes
git add -A
git commit -m "feat(scope): description"

# Keep branch updated
git fetch origin
git rebase origin/main  # or origin/develop
```

### Before PR
```bash
# Ensure clean history
git rebase -i HEAD~{n}  # Squash if needed

# Push to remote
git push -u origin feature/TKT-123-feature-name
```

## Pull Request Guidelines

### PR Title
```
{type}({scope}): {description} [TKT-{num}]
```

Example: `feat(auth): implement OAuth2 login [TKT-123]`

### PR Description Template
```markdown
## Summary
{1-2 sentence description of changes}

## Changes
- {Change 1}
- {Change 2}

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Ticket
Closes TKT-{num}

## Screenshots (if UI changes)
{Add screenshots}
```

## Common Operations

### Amend Last Commit
```bash
git add -A
git commit --amend --no-edit
git push --force-with-lease
```

### Undo Last Commit (keep changes)
```bash
git reset --soft HEAD~1
```

### Cherry-pick to Another Branch
```bash
git checkout target-branch
git cherry-pick {commit-hash}
```

### Clean Up Merged Branches
```bash
git fetch -p
git branch --merged | grep -v main | xargs git branch -d
```

## Pushing Code

### Push to Remote
```bash
# First push (set upstream)
git push -u origin feature/TKT-123-feature-name

# Subsequent pushes
git push

# Force push (only on your own branches, never main!)
git push --force-with-lease
```

### After Making Changes
```bash
# Stage, commit, push in one flow
git add -A
git commit -m "feat(scope): description"
git push
```

## Creating Pull Requests

### Using GitHub CLI (Recommended)
```bash
# Create PR with title and body
gh pr create --title "feat(auth): add login feature [TKT-123]" --body "## Summary
Implements user login with JWT authentication.

## Changes
- Add login endpoint
- Add JWT token generation
- Add auth middleware

## Testing
- [x] Unit tests pass
- [x] Integration tests pass

Closes TKT-123"

# Create PR interactively
gh pr create

# Create draft PR
gh pr create --draft

# Create PR with reviewers
gh pr create --reviewer @username1,@username2
```

## Merging Pull Requests

### Check PR Status First
```bash
# View PR status and checks
gh pr status
gh pr checks

# View specific PR
gh pr view 123
```

### Merge Methods
```bash
# Squash merge (recommended - clean history)
gh pr merge --squash

# Regular merge
gh pr merge --merge

# Rebase merge
gh pr merge --rebase

# Merge specific PR number
gh pr merge 123 --squash

# Merge with custom commit message
gh pr merge --squash --subject "feat(auth): implement login [TKT-123]"

# Auto-merge when checks pass
gh pr merge --auto --squash
```

### Merge to Main (When Task is 100% Complete)
```bash
# 1. Ensure all tests pass
gh pr checks

# 2. Ensure PR is approved (if required)
gh pr view --json reviews

# 3. Merge the PR
gh pr merge --squash --delete-branch

# The --delete-branch flag cleans up the feature branch after merge
```

### After Merge
```bash
# Switch back to main and pull latest
git checkout main
git pull origin main

# Clean up local branches
git fetch -p
git branch --merged | grep -v main | xargs git branch -d
```

## Handling Merge Conflicts

```bash
# Update your branch with main
git fetch origin
git rebase origin/main

# If conflicts occur:
# 1. Fix conflicts in files
# 2. Stage resolved files
git add <resolved-files>
# 3. Continue rebase
git rebase --continue
# 4. Force push (safe on feature branches)
git push --force-with-lease
```

## Safety Rules

1. **Never force push to main/develop** - Shared branches are protected
2. **Always use `--force-with-lease`** - Safer than `--force`
3. **Rebase, don't merge** - Keep history clean
4. **One concern per commit** - Atomic changes
5. **Test before push** - Run tests locally first
6. **Only merge when 100% complete** - All tests passing, code reviewed
7. **Use --delete-branch on merge** - Keep repo clean
