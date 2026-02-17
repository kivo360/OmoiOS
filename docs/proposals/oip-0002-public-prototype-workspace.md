```
OIP: 0002
Title: Try-Before-Register Public Prototype Workspace
Description: Expose an unauthenticated /try route with rate-limited prototype sandbox for instant interaction
Author: Kevin Hill
Status: Draft
Type: Standards Track
Created: 2026-02-17
```

## Abstract

Create a public `/try` route that exposes the existing prototype workspace to unauthenticated visitors. Users type a prompt, select a framework, and see a live preview — all within 60 seconds and without creating an account. Sessions are rate-limited by IP and fingerprint, with a clear upgrade path to full registration.

## Motivation

The existing prototype workspace (`frontend/components/prototype/PrototypeWorkspace.tsx`) provides a split-view layout with prompt input, history sidebar, and a live preview panel via `PreviewPanel` (`frontend/components/preview/PreviewPanel.tsx`). The backend `PrototypeManager` (`backend/omoi_os/services/prototype_manager.py`) manages ephemeral in-memory sessions with Daytona sandboxes.

However, this entire feature is behind authentication. A visitor must complete the full onboarding flow (8-15 minutes) before they can use it. By that point, most visitors have already left.

**Critical gap identified**: The current `apply_prompt()` method in `PrototypeManager` calls the LLM to generate a text response but does not actually edit files in the sandbox. The live preview shows the static framework template, not dynamically modified code. This proposal addresses both the access problem (authentication required) and the functionality gap (prompts don't modify code).

**User psychology**: "Show me, don't tell me." A visitor who types "Add a dark mode toggle" and sees a working toggle appear in a live preview within 30 seconds has experienced the product's value proposition firsthand. No amount of marketing copy achieves this.

## Specification

### 1. Public Route

**New file**: `frontend/app/try/page.tsx`

A public page (outside the `(app)` route group, no auth middleware) that renders a simplified version of `PrototypeWorkspace`. This page:
- Does not require authentication
- Shows a framework selector (React Vite, Next.js, Vue Vite)
- Provides a prompt input with suggestion chips ("Add a dark mode toggle", "Create a todo list", "Build a pricing page")
- Displays a live preview iframe via `PreviewPanel`
- Shows a prompt history sidebar (session-scoped, not persisted)
- Limits to 3 prompts per session with a "Sign up for unlimited" CTA after the limit

```
/try                          # Public prototype workspace
/try?framework=react-vite     # Pre-selected framework
/try?prompt=Add+a+counter     # Pre-filled prompt (from landing page CTA)
```

### 2. Anonymous Session Backend

**Modified file**: `backend/omoi_os/services/prototype_manager.py`

Add an `AnonymousPrototypeSession` variant:

```python
@dataclass
class AnonymousPrototypeSession(PrototypeSession):
    """Rate-limited session for unauthenticated visitors."""
    ip_address: str
    fingerprint: Optional[str] = None
    prompts_remaining: int = 3
    created_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None  # 15 min TTL
```

New methods on `PrototypeManager`:

```python
async def start_anonymous_session(
    self, ip_address: str, framework: str, fingerprint: Optional[str] = None
) -> AnonymousPrototypeSession:
    """Start a rate-limited anonymous session."""
    # Check IP rate limit (max 3 sessions per IP per hour)
    # Check global anonymous session cap
    # Create Daytona sandbox with reduced resource limits
    # Return session with 15-min TTL

async def apply_anonymous_prompt(
    self, session_id: str, prompt: str
) -> PromptResult:
    """Apply a prompt to an anonymous session with rate limiting."""
    # Decrement prompts_remaining
    # Apply prompt with code generation (see section 3)
    # Return result with prompts_remaining count
```

### 3. Prompt-to-Code Pipeline (Fix Existing Gap)

The current `apply_prompt()` method generates an LLM text response but does not modify sandbox files. This must be fixed for both authenticated and anonymous sessions.

**Modified file**: `backend/omoi_os/services/prototype_manager.py`

Extend `apply_prompt()` to:

1. Send the prompt + current file tree to the LLM with a code-generation system prompt
2. Receive structured output with file modifications (using `llm_service.structured_output()`)
3. Write the modified files to the Daytona sandbox via the existing sandbox API
4. Trigger a dev server restart if needed
5. Return the result with a summary of changes

```python
class PromptCodeChanges(BaseModel):
    """Structured output from LLM for prototype prompt application."""
    files_modified: list[FileModification]
    summary: str
    needs_restart: bool = False

class FileModification(BaseModel):
    path: str
    action: Literal["create", "modify", "delete"]
    content: Optional[str] = None  # Full file content for create/modify
```

### 4. Public Prototype API Endpoints

**New/modified file**: `backend/omoi_os/api/routes/prototype.py`

Add public endpoints (no auth middleware):

```
POST /api/v1/prototype/public/sessions     # Start anonymous session
POST /api/v1/prototype/public/prompt       # Apply prompt (rate-limited)
GET  /api/v1/prototype/public/preview/{id} # Get preview URL
DELETE /api/v1/prototype/public/sessions/{id}  # End session
```

All public endpoints require:
- IP-based rate limiting (3 sessions/hour, 3 prompts/session)
- Browser fingerprint header (optional, for enhanced rate limiting)
- CAPTCHA verification on session creation (hCaptcha or Turnstile)

### 5. Landing Page Integration

**Modified file**: `frontend/components/marketing/sections/HeroSection.tsx`

Add a secondary CTA below the primary "Get Started" button:

```tsx
<Button variant="outline" asChild>
  <Link href="/try">Try it now — no signup required</Link>
</Button>
```

**Modified file**: `frontend/components/marketing/sections/ProductShowcaseSection.tsx`

Add an inline "Try it yourself" prompt input that redirects to `/try?prompt={input}&framework=react-vite` on submit.

### 6. Conversion Funnel

After 3 prompts, the workspace shows a conversion overlay:

```
You've used 3/3 free prompts.
Sign up to get:
- Unlimited prototyping
- Full spec-driven workflows
- GitHub integration & PR creation
- Team collaboration

[Sign up free] [Continue browsing]
```

Clicking "Sign up free" preserves the session ID in a cookie. After registration, the anonymous session can be "adopted" — its sandbox and history transfer to the new user account.

## Rationale

### Why a separate /try route instead of embedding in the landing page?

- The prototype workspace requires significant screen real estate (split-view with preview). Embedding it in the landing page would make the page extremely long and slow.
- A dedicated route allows deep-linking from marketing campaigns (`omoios.dev/try?prompt=Build+a+dashboard`).
- Separation keeps the landing page focused on explaining value, while `/try` lets visitors experience it.

### Why 3 prompts per session?

- Enough to demonstrate the core loop (prompt → see changes → iterate) but scarce enough to create desire for more.
- Each prompt costs LLM tokens and sandbox compute. 3 prompts limits cost per anonymous visitor to approximately $0.05-0.15.
- A/B testable — can adjust to 2 or 5 based on conversion data.

### Why fix apply_prompt() as part of this OIP?

- The public prototype is useless without working code generation. The current implementation would show a static template regardless of what the visitor types.
- This fix benefits authenticated users too — the prototype workspace becomes genuinely functional for both audiences.

### Why not use a simulated/fake preview?

- Fake previews break trust the moment a user signs up and sees the real product differs. Authenticity is the core value of this approach.
- Real sandboxes also handle edge cases (framework-specific build systems, dependency installation) that a simulation would need to replicate.

## Backwards Compatibility

No backwards compatibility concerns for existing users. The prototype workspace for authenticated users gains improved `apply_prompt()` functionality (prompts now actually modify code), which is a pure improvement.

## Security Considerations

### Rate Limiting (Critical)
- **IP-based**: Max 3 anonymous sessions per IP per hour. Uses Redis with sliding window.
- **Fingerprint-enhanced**: Optional browser fingerprint (via FingerprintJS or similar) to catch VPN/proxy abuse.
- **Global cap**: Maximum 50 concurrent anonymous sessions system-wide. Returns "Demo busy, try again in a few minutes" when exceeded.
- **CAPTCHA**: Required on session creation to prevent automated abuse.

### Sandbox Isolation
- Anonymous sandboxes run with reduced resource limits (512MB RAM, 1 CPU core, 5-minute idle timeout).
- No network egress from anonymous sandboxes (prevent use as proxy/crypto miner).
- Sandboxes auto-terminate after 15 minutes regardless of activity.

### Prompt Injection
- Anonymous prompts are filtered through a content moderation layer before reaching the LLM.
- System prompt for anonymous sessions restricts output to frontend code only (no backend, no system commands).
- File writes are limited to the project directory (no escaping the sandbox root).

### Cost Control
- Each anonymous session costs approximately $0.02 (sandbox) + $0.01-0.05/prompt (LLM). At 3 prompts max, worst case is ~$0.17/visitor.
- Global session cap prevents runaway costs. At 50 concurrent sessions with 15-min TTL, maximum throughput is 200 sessions/hour = ~$34/hour worst case.
- Daily cost cap can be implemented: disable anonymous sessions after $X/day spend.

## Impact Assessment

**Effort**: Medium. Requires frontend route + component (~300 lines), backend anonymous session logic (~200 lines), prompt-to-code pipeline fix (~150 lines), rate limiting infrastructure (~100 lines), and landing page CTA additions.

**Infrastructure cost**: Variable. $0.05-0.17 per visitor session. With 100 daily visitors using `/try`, approximately $5-17/day. Capped by global session limits.

**Expected impact**: Visitors who interact with a working prototype are significantly more likely to register. This targets the "show me" audience that bounces from static landing pages.

**Success metrics**:
- `/try` page visits and completion rate (visitor reaches 3rd prompt)
- Conversion rate from `/try` to registration
- Time from landing to first interaction on `/try`
- Session adoption rate (anonymous sessions converted to registered accounts)

## Open Issues

1. Should anonymous sandboxes support all 3 frameworks or just React Vite (simplest, most familiar)?
2. What CAPTCHA provider? hCaptcha (privacy-focused) vs Cloudflare Turnstile (invisible, better UX)?
3. Should the 3-prompt limit be per-session or per-IP-per-day?
4. How to handle the prompt-to-code pipeline for the MVP — full file rewrites or incremental diffs?
5. Should we pre-warm anonymous sandbox pools (faster start, higher cost) or provision on-demand (slower start, lower cost)?
