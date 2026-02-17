```
OIP: 0001
Title: Interactive Landing Page Demo Replay
Description: Replace static marketing animations with real sandbox event replays on the landing page
Author: Kevin Hill
Status: Draft
Type: Standards Track
Created: 2026-02-17
```

## Abstract

Replace the static `TicketJourney` animation on the landing page with a replay of real, pre-recorded sandbox events. Visitors see actual agent work (file edits, bash commands, test runs, PR creation) playing back in real-time, providing authentic product value within 30 seconds of landing — before any registration or interaction.

## Motivation

The current landing page at `omoios.dev` is entirely static marketing. The `TicketJourney` component (`frontend/components/landing/TicketJourney.tsx`) shows a scripted 4-phase animation with hardcoded phase data. The `NightShiftSection` has a `NightShiftLog` simulating agent activity. Neither uses real product data.

**Problem**: A visitor has zero evidence that OmoiOS actually works until they complete 8-15 minutes of onboarding (email verification, GitHub OAuth, repo selection, plan selection, first spec submission, and waiting for agent execution). Most visitors will leave before reaching that point.

**Data point**: The `ProductShowcaseSection` (`frontend/components/marketing/sections/ProductShowcaseSection.tsx`) shows 4 static screenshots in a carousel — the most concrete product evidence available pre-registration. Static screenshots cannot convey the experience of watching an autonomous agent build software.

**Opportunity**: The sandbox detail page (`frontend/app/(app)/sandbox/[sandboxId]/page.tsx`) already has a complete `EventRenderer` component that renders real agent events (file edits with syntax highlighting, bash commands with output, status changes, PR links). This component is production-tested but only accessible to authenticated users viewing their own sandboxes.

By recording a curated sandbox session and replaying it on the landing page, we can show real product value at zero infrastructure cost — the data is pre-recorded JSON, not a live sandbox.

## Specification

### 1. Event Recording Pipeline

Create a one-time script to capture a curated sandbox session:

**New file**: `scripts/capture_demo_events.py`

```python
"""Capture sandbox events from a real session for landing page replay."""
# Connect to production/staging DB
# Query events for a specific sandbox_id
# Filter to the most impressive ~60 events (file creates, test passes, PR)
# Export as JSON array to frontend/public/demo/events.json
```

**Output format** (`frontend/public/demo/events.json`):
```json
[
  {
    "type": "file_edit",
    "timestamp_offset_ms": 0,
    "data": {
      "path": "src/components/Dashboard.tsx",
      "language": "typescript",
      "diff": "..."
    }
  },
  {
    "type": "bash_command",
    "timestamp_offset_ms": 4200,
    "data": {
      "command": "pnpm test --run",
      "output": "Tests: 12 passed, 12 total",
      "exit_code": 0
    }
  }
]
```

Events use relative `timestamp_offset_ms` (milliseconds from session start) so the replay controls playback speed independent of original recording timing.

### 2. DemoReplayPlayer Component

**New file**: `frontend/components/landing/DemoReplayPlayer.tsx`

A self-contained component that:
- Loads `events.json` from `/demo/events.json` (static asset, no API call)
- Plays events sequentially with configurable speed (1x, 2x, 4x)
- Renders each event using the existing `EventRenderer` from `frontend/components/sandbox/`
- Auto-scrolls to the latest event
- Shows a progress bar and event counter
- Auto-starts on viewport intersection (IntersectionObserver)
- Pauses when the tab is not visible (Page Visibility API)

```typescript
interface DemoReplayPlayerProps {
  eventsUrl?: string        // Default: "/demo/events.json"
  speed?: 1 | 2 | 4        // Playback speed multiplier
  autoPlay?: boolean        // Start on viewport intersection
  maxVisibleEvents?: number // Limit rendered events for performance
}
```

### 3. Landing Page Integration

**Modified file**: `frontend/components/marketing/sections/HeroSection.tsx`

Add the `DemoReplayPlayer` below the existing hero CTA. The player sits in the "demo" section (anchor `#demo`) currently occupied by the `TicketJourney` component.

**Modified file**: `frontend/components/marketing/sections/ProductShowcaseSection.tsx`

Replace the static screenshot carousel with `DemoReplayPlayer` as the primary product evidence. Keep screenshots as a fallback for users with JavaScript disabled (rendered via `<noscript>`).

### 4. Event Data Curation

The demo recording should showcase a complete mini-workflow:
1. Agent reads a spec and plans implementation (~5 events)
2. Agent creates/edits 3-4 files with real TypeScript code (~15 events)
3. Agent runs tests, one fails, agent self-corrects (~10 events)
4. Agent runs tests again, all pass (~3 events)
5. Agent creates a PR with a summary (~2 events)

Total: ~35 events, replaying in ~45 seconds at 1x speed. The self-correction sequence is critical — it demonstrates autonomous problem-solving, not just code generation.

## Rationale

### Why pre-recorded replay over live sandbox?

- **Zero infrastructure cost**: No Daytona sandboxes, no LLM calls, no backend changes required.
- **Curated quality**: We control exactly which events are shown. No risk of an LLM producing embarrassing output on the landing page.
- **Instant load**: Static JSON asset loads with the page. No waiting for sandbox provisioning.
- **Deterministic**: Same experience every time. No flaky demos.

### Why reuse EventRenderer instead of a custom animation?

- **Authenticity**: Using the same renderer that authenticated users see proves the demo is real, not a mockup.
- **Maintenance**: One rendering path to maintain. When EventRenderer gets improvements, the landing page benefits automatically.
- **Trust signal**: Visitors who later sign up see the exact same event format, reinforcing that the demo was genuine.

### Why not just embed a video?

- Videos are passive and non-interactive. A live-feeling replay with speed controls and progress indicators feels more like the product itself. Videos also add significant page weight and can't be themed to match the landing page's dark mode.

## Backwards Compatibility

No backwards compatibility concerns. This adds a new component and modifies the landing page layout. No existing user-facing features are changed. The `TicketJourney` component remains in the codebase and can be restored if needed.

## Security Considerations

- **Data exposure**: The demo events JSON must be scrubbed of any real user data, API keys, internal URLs, or sensitive file paths before publishing. Use a dedicated demo project with synthetic content.
- **No new attack surface**: The replay is a static asset. No API calls, no user input processing, no authentication required.
- **Content injection**: Events are rendered through `EventRenderer` which already sanitizes output. No raw `dangerouslySetInnerHTML`.

## Impact Assessment

**Effort**: Small. Requires one new component (~200 lines), one script to capture events, and modifications to 2 existing landing page sections.

**Infrastructure cost**: Zero. Static JSON file served from Vercel CDN.

**Expected impact**: Visitors see real product evidence within 30 seconds. This should reduce bounce rate from the landing page and increase registration conversion by providing concrete proof that OmoiOS works before asking for any commitment.

**Success metrics**:
- Landing page bounce rate (decrease expected)
- Time on landing page (increase expected — visitors watching the replay)
- Registration conversion rate from landing page
- Scroll depth past the demo section

## Open Issues

1. How many events should the demo include? 35 events at ~45s feels right, but may need A/B testing.
2. Should the replay loop, or stop with a CTA ("See what OmoiOS can build for you — sign up free")?
3. Should we show a "This is a real recording" badge to emphasize authenticity?
4. Which framework should the demo project use — React (most familiar to target audience) or Next.js (matches OmoiOS's own stack)?
