---
description: Create well-structured pull requests with proper descriptions and labels
globs: [".github/**", "**/*.md"]
---

# PR Creator

Create well-structured pull requests that are easy to review.

## PR Title Format

```
{type}({scope}): {description} [TKT-{num}]
```

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code refactoring |
| `test` | Test additions |
| `docs` | Documentation |
| `chore` | Maintenance |
| `perf` | Performance |

Examples:
- `feat(auth): implement OAuth2 login [TKT-123]`
- `fix(api): handle null response in user endpoint [TKT-456]`
- `refactor(db): optimize query performance [TKT-789]`

## PR Description Template

```markdown
## Summary
{1-2 sentence high-level description of what this PR does}

## Changes
{Bullet list of specific changes}

- Add {component/feature} for {purpose}
- Update {file} to {change}
- Remove {deprecated thing}

## Implementation Details
{Technical details for reviewers}

### Key Decisions
- **{Decision 1}**: Chose {approach} because {reason}
- **{Decision 2}**: Used {pattern} for {benefit}

### Notable Files
- `path/to/main/file.py` - Core implementation
- `path/to/tests.py` - Test coverage

## Testing

### Automated Tests
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] E2E tests pass (if applicable)

### Manual Testing
{Steps to manually verify}

1. {Step 1}
2. {Step 2}
3. Expected: {outcome}

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings/errors
- [ ] Tests cover new functionality

## Related
- Closes TKT-{num}
- Relates to #{other-pr}
- Depends on #{blocking-pr}

## Screenshots
{For UI changes, add before/after screenshots}

| Before | After |
|--------|-------|
| {img}  | {img} |
```

## Creating PR via CLI

```bash
# Using GitHub CLI (gh)
gh pr create \
  --title "feat(auth): implement OAuth2 login [TKT-123]" \
  --body "$(cat <<'EOF'
## Summary
Implements OAuth2 login flow with Google and GitHub providers.

## Changes
- Add OAuth2 provider configuration
- Implement callback handling
- Add session management for OAuth users

## Testing
- [ ] Unit tests for OAuth flow
- [ ] Manual testing with Google/GitHub

Closes TKT-123
EOF
)" \
  --base main \
  --label "feature" \
  --label "auth"
```

## Labels to Apply

| Label | When to Use |
|-------|-------------|
| `feature` | New functionality |
| `bugfix` | Bug fixes |
| `breaking` | Breaking changes |
| `security` | Security-related |
| `performance` | Performance improvements |
| `documentation` | Doc changes only |
| `needs-review` | Ready for review |
| `work-in-progress` | Not ready yet |

## Size Guidelines

| Size | Lines Changed | Review Time |
|------|---------------|-------------|
| XS | < 50 | < 15 min |
| S | 50-200 | 15-30 min |
| M | 200-500 | 30-60 min |
| L | 500-1000 | 1-2 hours |
| XL | > 1000 | Consider splitting |

## Best Practices

1. **Keep PRs small** - Easier to review, fewer conflicts
2. **One concern per PR** - Don't mix features with refactors
3. **Include tests** - Every feature/fix should have tests
4. **Update docs** - Keep documentation in sync
5. **Add context** - Help reviewers understand decisions
6. **Link issues** - Use "Closes #123" to auto-close
7. **Request specific reviewers** - Tag domain experts
8. **Respond to feedback** - Address all comments

## Draft PRs

Use draft PRs for:
- Work in progress that needs early feedback
- Large changes that will take multiple commits
- Exploring approaches before finalizing

```bash
gh pr create --draft --title "WIP: feat(auth): OAuth2 exploration"
```

## Merge Strategy

| Strategy | When to Use |
|----------|-------------|
| **Squash** | Default - clean history, one commit per PR |
| **Merge** | When preserving commit history matters |
| **Rebase** | When linear history is required |

```bash
# Squash merge (recommended)
gh pr merge --squash

# With custom commit message
gh pr merge --squash --subject "feat(auth): OAuth2 login"
```
