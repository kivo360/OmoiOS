# OmoiOS Improvement Proposals (OIPs)

OIPs are the primary mechanism for proposing new features, collecting design input, and documenting architectural decisions for OmoiOS. They provide a structured, reviewable format for changes that affect the product, infrastructure, or development process.

## Current Proposals

| OIP | Title | Type | Status | Created |
|-----|-------|------|--------|---------|
| [0001](oip-0001-landing-demo-replay.md) | Interactive Landing Page Demo Replay | Standards Track | Draft | 2026-02-17 |
| [0002](oip-0002-public-prototype-workspace.md) | Try-Before-Register Public Prototype Workspace | Standards Track | Draft | 2026-02-17 |
| [0003](oip-0003-streamlined-onboarding.md) | Streamlined Onboarding with Deferred GitHub | Standards Track | Draft | 2026-02-17 |
| [0004](oip-0004-live-demo-sandbox.md) | One-Click Live Demo with Pre-Warmed Sandboxes | Standards Track | Draft | 2026-02-17 |
| [0005](oip-0005-bring-your-own-keys.md) | Bring Your Own API Keys | Standards Track | Draft | 2026-02-17 |

### Recommended Implementation Order

1. **OIP-0001** — Quick win, zero infrastructure cost. Adds passive value to the landing page by replaying real sandbox events.
2. **OIP-0003** — Structural improvement that compounds with everything else. Reduces onboarding from 6 steps to 2.
3. **OIP-0002** — High-impact interactive experience. Exposes the prototype workspace without requiring registration.
4. **OIP-0004** — Premium wow-moment with highest infrastructure cost. Pre-warmed sandboxes for instant live demos.

## OIP Types

- **Standards Track** — Changes to the product, APIs, infrastructure, or frontend that affect users or developers.
- **Informational** — Describes a design guideline, best practice, or general information. Does not propose a new feature.
- **Process** — Changes to development processes, tooling, or governance (including changes to the OIP process itself).

## Status Lifecycle

```
Draft → Review → Accepted → Implemented
                    ↓
               Deferred (parked for later)

Draft/Review → Rejected | Withdrawn
Implemented → Superseded (by a later OIP)
```

| Status | Meaning |
|--------|---------|
| **Draft** | Initial proposal, open for feedback and iteration |
| **Review** | Formally under review by maintainers |
| **Accepted** | Approved for implementation |
| **Implemented** | Fully shipped to production |
| **Deferred** | Accepted in principle but parked for later |
| **Rejected** | Reviewed and declined |
| **Withdrawn** | Pulled by the author |
| **Superseded** | Replaced by a newer OIP |

## How to Submit an OIP

1. Copy `TEMPLATE.md` to `oip-NNNN-short-title.md` using the next available number (4-digit, zero-padded).
2. Fill in all required sections. The Abstract should be understandable in 30 seconds.
3. Add your OIP to the status table in this README.
4. Submit for review via PR or direct discussion.

## Numbering

OIPs use 4-digit zero-padded numbers: `OIP-0001`, `OIP-0002`, etc. File names follow the pattern `oip-NNNN-short-title.md`.

## Required Sections

Every OIP must include:

- **Preamble** — Metadata header block
- **Abstract** — 2-3 sentence summary
- **Motivation** — Why this change is needed, with data where possible
- **Specification** — Concrete technical details, referencing real codebase files
- **Rationale** — Why this approach over alternatives
- **Backwards Compatibility** — Impact on existing behavior (if applicable)
- **Security Considerations** — Authentication, rate limiting, abuse vectors
- **Open Issues** — Unresolved questions for discussion
