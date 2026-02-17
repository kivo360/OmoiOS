---
name: oip-proposal
description: |
  Create OmoiOS Improvement Proposals (OIPs) through an interactive workflow. Gathers context
  from the user via clarifying questions, researches relevant codebase files, then writes a
  complete proposal following the OIP template.

  Use when requesting "create a proposal", "write an OIP", "new proposal", "propose a feature",
  "OIP", "improvement proposal", or when the user wants to formally propose a product, architecture,
  or process change for OmoiOS.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, WebFetch, WebSearch
---

# OIP Proposal Skill

Create OmoiOS Improvement Proposals (OIPs) through an interactive, question-driven workflow. This skill gathers context from the user, researches the codebase for accurate file references, and writes a complete proposal following the project's OIP template.

## Workflow

Follow these three phases in order. **Do not skip the clarification phase** — proposals written without understanding the user's intent produce vague specifications that require rewrites.

---

## Phase 1: Clarify the Proposal

**Goal:** Understand what the user wants to propose and why, before writing anything.

### Step 1: Determine the next OIP number

Read `docs/proposals/README.md` and check which OIP numbers are taken:

```
ls docs/proposals/oip-*.md
```

The next number is one above the highest existing number, zero-padded to 4 digits.

### Step 2: Ask clarifying questions

Use the `AskUserQuestion` tool to gather essential context. Ask questions based on what the user has provided so far. Not all questions will be needed for every proposal — use judgment.

**Always ask:**
- What problem does this solve? (The "motivation" — should be concrete, not vague)
- Who benefits? (Users, developers, ops, everyone?)
- What's the proposed solution at a high level?

**Ask if unclear:**
- What type of proposal is this? (Standards Track for product/code changes, Informational for guidelines, Process for workflow changes)
- Are there constraints or non-goals? (Things this proposal deliberately does NOT do)
- Are there alternatives you considered and rejected?
- Does this depend on or conflict with other OIPs?
- What's the security surface? (New endpoints, auth changes, public-facing features)
- What infrastructure is needed? (New services, databases, external APIs)

**Ask if the proposal involves frontend work:**
- Which routes or pages are affected?
- Are new components needed, or can existing ones be reused?
- How does this interact with the navigation/sidebar?

**Ask if the proposal involves backend work:**
- Which services are affected?
- Are database migrations needed?
- Does this require new API endpoints?

### Step 3: Confirm understanding

Summarize what you've gathered in 3-4 sentences and ask the user to confirm before proceeding. Use `AskUserQuestion` with options like "Yes, that's right" / "Close but let me clarify" / "No, let me re-explain".

---

## Phase 2: Research the Codebase

**Goal:** Find the real files, components, and patterns that the proposal will reference. Proposals that reference actual codebase paths are far more useful than ones that speak abstractly.

### What to research

Based on the proposal's scope, read the relevant files:

- **Frontend changes**: Check `frontend/app/` for route structure, `frontend/components/` for existing components, `frontend/hooks/` for data patterns, `frontend/lib/api/` for API client functions
- **Backend changes**: Check `backend/omoi_os/api/routes/` for existing endpoints, `backend/omoi_os/services/` for business logic, `backend/omoi_os/models/` for database schema
- **Configuration**: Check `backend/config/base.yaml` for settings patterns
- **Existing proposals**: Read related OIPs in `docs/proposals/` to avoid conflicts or duplication

### Key reference documents

| Document | When to read |
|----------|-------------|
| `ARCHITECTURE.md` | Any backend or system-wide proposal |
| `UI.md` | Any frontend proposal |
| `docs/proposals/README.md` | Always — check status table for conflicts |
| `backend/CLAUDE.md` | Backend conventions (structured_output, datetime, reserved words) |

### Record your findings

Note the exact file paths (relative from repo root) for every component, service, hook, or route you'll reference. The Specification section must use real paths, not hypothetical ones.

---

## Phase 3: Write the Proposal

**Goal:** Write the complete OIP file following the template exactly.

### File location

```
docs/proposals/oip-{NNNN}-{short-title}.md
```

Where `{NNNN}` is the zero-padded number and `{short-title}` is a kebab-case slug (2-4 words).

### Required structure

Every OIP must contain these sections in this order:

````markdown
```
OIP: {NNNN}
Title: {Descriptive Title}
Description: {One-line summary, max 140 characters}
Author: {Name or handle}
Status: Draft
Type: {Standards Track | Informational | Process}
Created: {YYYY-MM-DD}
Requires: (optional, other OIP numbers)
Replaces: (optional)
Superseded-By: (optional)
```

## Abstract

2-3 sentences. A reader should understand the proposal in 30 seconds.

## Motivation

Why this change is needed. Include data, user research, or metrics.
Reference the problem concretely — link to specific code that demonstrates the issue.

## Specification

Concrete technical details. This is the longest section.

For each change, specify:
- **Modified file**: `path/to/file.ts` — what changes and why
- **New file**: `path/to/new/file.ts` — what it does, key interfaces/types

Include code snippets for interfaces, types, API endpoints, config changes.
Be specific enough that another engineer could implement without asking questions.

## Rationale

Why this approach over alternatives. Name the alternatives explicitly
and explain why they were not chosen. Discuss trade-offs.

## Backwards Compatibility

How existing users and behavior are affected.
If none: "No backwards compatibility concerns."

## Security Considerations

Authentication, rate limiting, abuse vectors, data exposure.
Every proposal MUST address this, even if the answer is "no new attack surface."

## Impact Assessment

Effort estimate (small/medium/large), infrastructure costs, expected user impact.
Include metrics for measuring success.

## Open Issues

Unresolved questions. Number them for easy reference in discussions.
````

### Writing guidelines

- **Reference real files**: Use `path/to/file.ts` format for every file mentioned. Readers should be able to `cat` the file and see what you're talking about.
- **Show interfaces**: For new components, APIs, or data structures, include the TypeScript interface or Python class definition.
- **Be opinionated**: State the recommended approach clearly. Don't present 3 options without recommending one.
- **Quantify where possible**: "~200 lines of new code", "$0.05 per session", "reduces onboarding from 6 steps to 2".
- **Address security proactively**: Don't wait to be asked. If the feature has a public surface, discuss rate limiting, auth, and abuse vectors.

### After writing

1. Update `docs/proposals/README.md` — add the new OIP to the status table
2. Show the user the completed file path and a brief summary
3. Ask if they want to adjust anything before committing

---

## Example Trigger Conversations

**User**: "I want to propose adding WebSocket support to the sandbox page"
**Action**: Ask clarifying questions about scope (which events? replace polling? backwards compatible?), research `frontend/app/(app)/sandbox/[sandboxId]/page.tsx` and `frontend/hooks/useSandbox.ts`, then write the OIP.

**User**: "Write an OIP for rate limiting the public API"
**Action**: Ask about which endpoints, what limits, whether it's IP-based or token-based, research `backend/omoi_os/api/main.py` and existing auth middleware, then write the OIP.

**User**: "New proposal"
**Action**: Ask what they want to propose — don't assume. Start with "What problem are you looking to solve?"

---

## Related Resources

- [OIP README](docs/proposals/README.md) — Status table, lifecycle, types
- [OIP Template](docs/proposals/TEMPLATE.md) — Raw template structure
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design reference
- [UI.md](UI.md) — Frontend architecture reference
