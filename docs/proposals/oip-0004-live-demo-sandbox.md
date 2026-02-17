```
OIP: 0004
Title: One-Click Live Demo with Pre-Warmed Sandboxes
Description: Maintain a pool of pre-warmed sandboxes for instant live demos on the landing page
Author: Kevin Hill
Status: Draft
Type: Standards Track
Created: 2026-02-17
```

## Abstract

Maintain a pool of pre-warmed Daytona sandboxes that are ready to accept prompts instantly. Landing page visitors click "Try Live Demo" and are dropped into a working sandbox with a live preview in under 15 seconds — no registration, no waiting for provisioning. The sandbox pool is managed by a background service that keeps a configurable number of warm sandboxes available at all times.

## Motivation

Both OIP-0001 (pre-recorded replay) and OIP-0002 (public prototype workspace) address time-to-value, but with trade-offs:

- **OIP-0001** is passive — the visitor watches, but doesn't interact. Effective for proof but doesn't create the "I built this" feeling.
- **OIP-0002** requires on-demand sandbox provisioning, which adds 15-30 seconds of wait time after the visitor submits their first prompt. That's 15-30 seconds of a loading spinner where the visitor might leave.

This proposal eliminates the provisioning wait entirely. When a visitor clicks "Try Live Demo", a pre-warmed sandbox is immediately assigned. The dev server is already running. The framework template is already loaded. The first prompt response appears within seconds.

**The "15-second rule"**: Studies on web application abandonment show that users who don't see meaningful content within 10-15 seconds are likely to leave. By pre-warming sandboxes, we compress the time from click to live preview to under 15 seconds, including LLM response time.

### Competitive advantage

Most developer tool landing pages offer:
- Static screenshots (common)
- Embedded videos (common)
- Interactive playground with simulated output (rare)
- Live sandbox with real execution (extremely rare)

A live sandbox demo on the landing page would be a significant differentiator.

## Specification

### 1. Sandbox Pool Manager

**New file**: `backend/omoi_os/services/sandbox_pool_manager.py`

A background service that maintains a pool of ready-to-use sandboxes:

```python
class SandboxPoolManager:
    """Manages a pool of pre-warmed sandboxes for instant demos."""

    def __init__(
        self,
        pool_size: int = 5,          # Target number of warm sandboxes
        framework: str = "react-vite", # Default framework
        max_session_duration: int = 300, # 5 min max per demo session
        idle_timeout: int = 900,       # 15 min before recycling unused warm sandbox
        replenish_interval: int = 30,  # Check pool every 30s
    ):
        self._warm_pool: list[WarmSandbox] = []
        self._active_sessions: dict[str, DemoSession] = {}

    async def claim_sandbox(self, visitor_id: str) -> DemoSession:
        """Claim a pre-warmed sandbox for a demo session.

        Returns immediately if pool has available sandboxes.
        Falls back to on-demand provisioning if pool is empty.
        """

    async def release_sandbox(self, session_id: str) -> None:
        """Release a demo session's sandbox back for recycling."""

    async def _replenish_loop(self) -> None:
        """Background loop that maintains pool_size warm sandboxes."""

    async def _warm_sandbox(self) -> WarmSandbox:
        """Create and warm a sandbox:
        1. Provision Daytona sandbox
        2. Install framework template
        3. Start dev server
        4. Wait for dev server to be healthy
        5. Return with preview URL ready
        """
```

```python
@dataclass
class WarmSandbox:
    """A sandbox ready for immediate use."""
    sandbox_id: str
    preview_url: str
    framework: str
    created_at: datetime
    dev_server_healthy: bool = True

@dataclass
class DemoSession:
    """An active demo session using a claimed sandbox."""
    session_id: str
    visitor_id: str  # IP-based or fingerprint
    sandbox: WarmSandbox
    claimed_at: datetime
    prompts_used: int = 0
    max_prompts: int = 3
    expires_at: datetime  # claimed_at + max_session_duration
```

### 2. Pool Configuration

**Modified file**: `backend/config/base.yaml`

```yaml
sandbox_pool:
  enabled: false           # Off by default, enable in production
  pool_size: 5             # Number of warm sandboxes to maintain
  framework: "react-vite"  # Framework for demo sandboxes
  max_session_duration: 300 # 5 minutes per demo
  idle_timeout: 900         # 15 min before recycling warm sandbox
  replenish_interval: 30    # Check every 30s
  max_concurrent_demos: 10  # Hard cap on active demos
  daily_cost_cap: 50.0      # Stop warming after $X/day
```

### 3. Demo API Endpoints

**New file**: `backend/omoi_os/api/routes/demo.py`

```
POST /api/v1/demo/claim           # Claim a warm sandbox
POST /api/v1/demo/{session}/prompt # Apply prompt to demo session
GET  /api/v1/demo/{session}/status # Check demo session status
DELETE /api/v1/demo/{session}      # Release demo session
GET  /api/v1/demo/availability     # Check if demos are available
```

The `/availability` endpoint is called by the landing page to determine whether to show the "Try Live Demo" button. If the pool is empty and provisioning would take too long, the button degrades to the OIP-0001 replay or OIP-0002 on-demand experience.

### 4. Landing Page Integration

**Modified file**: `frontend/components/marketing/sections/HeroSection.tsx`

Add a prominent "Try Live Demo" button in the hero section:

```tsx
function HeroDemoButton() {
  const { available, claiming, claimDemo } = useDemoAvailability()

  if (!available) {
    // Fallback to OIP-0001 replay or OIP-0002 /try link
    return <Link href="/try">Try it — no signup required</Link>
  }

  return (
    <Button
      size="lg"
      onClick={claimDemo}
      disabled={claiming}
    >
      {claiming ? "Starting demo..." : "Try Live Demo — 15 seconds"}
    </Button>
  )
}
```

**New file**: `frontend/components/demo/LiveDemoOverlay.tsx`

When the visitor clicks "Try Live Demo", an overlay slides up from the bottom of the landing page showing:
- A split view: prompt input on the left, live preview iframe on the right
- A countdown timer showing session time remaining (5 minutes)
- Suggestion chips for first prompt
- A "Sign up to keep building" CTA
- A close button to dismiss and return to the landing page

The overlay approach keeps the visitor on the landing page (maintaining context) while providing a full interactive experience.

### 5. Frontend Hook

**New file**: `frontend/hooks/useLiveDemo.ts`

```typescript
interface UseLiveDemoReturn {
  available: boolean
  session: DemoSession | null
  claiming: boolean
  claimDemo: () => Promise<void>
  applyPrompt: (prompt: string) => Promise<PromptResult>
  releaseDemo: () => Promise<void>
  previewUrl: string | null
  promptsRemaining: number
  timeRemaining: number // seconds
}

function useLiveDemo(): UseLiveDemoReturn {
  // Polls /api/v1/demo/availability on mount
  // Claims sandbox on claimDemo()
  // Manages session lifecycle with auto-release on unmount
  // Countdown timer for session expiration
}
```

### 6. Graceful Degradation

The system degrades gracefully based on pool availability:

| Pool State | User Experience |
|------------|----------------|
| Warm sandboxes available | "Try Live Demo" — instant (< 15s) |
| Pool empty, provisioning possible | "Try it — starts in ~30s" (falls back to OIP-0002 flow) |
| Pool empty, at capacity | "Watch Demo" (falls back to OIP-0001 replay) |
| Pool disabled / error | Standard landing page (no demo button) |

### 7. Cost Management

The pool manager tracks costs:

```python
async def _check_cost_budget(self) -> bool:
    """Check if daily cost cap has been reached."""
    today_cost = await self._get_today_cost()
    if today_cost >= self.settings.daily_cost_cap:
        logger.warning(f"Daily demo cost cap reached: ${today_cost:.2f}")
        return False
    return True
```

Cost components per warm sandbox:
- Daytona sandbox: ~$0.01/minute while running
- Pool of 5 sandboxes running 24h: ~$72/day
- With 15-min idle timeout and demand-based scaling: ~$15-30/day estimated

Cost components per demo session:
- LLM prompts (3 max): ~$0.05-0.15
- Sandbox compute (5 min max): ~$0.05

## Rationale

### Why pre-warm instead of on-demand provisioning?

On-demand provisioning (OIP-0002) takes 15-30 seconds for sandbox creation, framework installation, and dev server startup. Pre-warming moves this cost to a background process. The visitor experiences near-instant response.

The trade-off is idle cost — warm sandboxes consume resources even when no visitors are using them. This is mitigated by:
- Small pool size (5 sandboxes)
- Idle timeout recycling (15 minutes)
- Demand-based scaling (reduce pool during off-peak hours)
- Daily cost cap

### Why an overlay instead of a new route?

An overlay keeps the visitor on the landing page. If they dismiss the demo, they're back to the marketing content — not lost in navigation. This also means the landing page URL stays constant, which is better for analytics and sharing.

### Why React Vite as the default framework?

- React is the most widely known frontend framework (~40% market share among target audience).
- Vite provides the fastest dev server startup (~500ms vs ~3s for Next.js dev).
- The simpler Vite setup means fewer failure modes during demos.
- Users who prefer other frameworks can use the full `/try` route (OIP-0002).

### Why limit to 5 minutes per session?

- 5 minutes is enough for 3 prompts with iteration (observe results, refine prompt, observe again).
- Longer sessions increase cost without proportionally increasing conversion.
- Time pressure creates urgency — "I want to keep building, let me sign up."
- A/B testable — can adjust to 3 or 10 minutes based on data.

## Backwards Compatibility

No backwards compatibility concerns. This is an entirely new feature on the landing page. No existing user flows are modified.

## Security Considerations

### Sandbox Isolation
- Pre-warmed sandboxes are identical to production sandboxes in terms of isolation (Daytona containers).
- No network egress from demo sandboxes.
- File system is ephemeral and destroyed on session end.
- No access to production databases or services.

### Rate Limiting
- One demo session per visitor (IP + fingerprint) per hour.
- Max 3 prompts per session (enforced server-side).
- CAPTCHA not required (the "Try Live Demo" button is a single click, CAPTCHA would kill the instant experience). Instead, rely on IP rate limiting and pool size cap.
- Global concurrent session cap (10) prevents abuse at scale.

### Resource Exhaustion
- Pool size is capped (5 warm + 10 active = 15 max sandboxes).
- Daily cost cap automatically disables the pool when budget is exceeded.
- Individual sandbox resource limits (512MB RAM, 1 CPU, 5-min session).
- The replenish loop has backoff — if sandbox creation fails repeatedly, it stops trying and logs an alert.

### Prompt Security
- Same content moderation as OIP-0002 for anonymous prompts.
- System prompt restricts LLM output to frontend code modifications only.
- No shell access, no backend code generation, no file system escape.

## Impact Assessment

**Effort**: Large. Requires a new backend service (SandboxPoolManager ~400 lines), new API routes (~150 lines), new frontend components (overlay ~300 lines, hook ~150 lines), landing page modifications, and configuration infrastructure.

**Infrastructure cost**: $15-72/day for the warm pool depending on traffic patterns and configuration. Per-session cost of ~$0.10-0.20. With a $50/day cap, maximum monthly cost is ~$1,500.

**Expected impact**: The "instant live demo" is the most impressive possible pre-registration experience. A visitor goes from "what is this?" to "I just built something with AI" in 15 seconds. This is the strongest possible conversion signal.

**Success metrics**:
- Demo claim rate (% of landing page visitors who click "Try Live Demo")
- Demo completion rate (% who use all 3 prompts)
- Demo-to-registration conversion rate
- Time from demo claim to first prompt response (target: < 15 seconds)
- Pool utilization rate (claimed sandboxes / total warm sandboxes)
- Daily cost vs. daily registrations (cost per acquisition)

## Open Issues

1. Should the pool scale based on time of day (more sandboxes during US business hours, fewer at night)?
2. How to handle the transition when a demo visitor signs up — can we seamlessly transfer their demo sandbox to their new account?
3. Should the demo overlay be a modal, a slide-up panel, or a full-screen takeover?
4. Is 5 warm sandboxes the right starting pool size? Should we start with 2-3 and scale up based on demand data?
5. Should we track and display a "live users building right now" counter on the landing page for social proof?
6. How to handle the case where a warm sandbox's dev server crashes before being claimed — health check interval and auto-replacement strategy?
