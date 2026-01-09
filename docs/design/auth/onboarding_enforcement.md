# Onboarding Enforcement System

**Created**: 2025-01-09
**Status**: Draft
**Purpose**: Design for enforcing onboarding completion with database persistence, localStorage sync, and debugging tools

---

## Overview

Users who haven't completed onboarding should be automatically redirected to `/onboarding`. The system needs to:

1. **Persist** onboarding state in the database (source of truth)
2. **Cache** state in localStorage for fast client-side checks
3. **Sync** between database and localStorage
4. **Auto-detect** inconsistencies and self-heal
5. **Provide** debugging tools to reset/bypass onboarding

---

## Data Model

### Database Schema (Backend)

Add to the `users` table or create a separate `user_onboarding` table:

```sql
-- Option A: Add columns to users table
ALTER TABLE users ADD COLUMN onboarding_completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN onboarding_step VARCHAR(50) DEFAULT 'welcome';
ALTER TABLE users ADD COLUMN onboarding_data JSONB DEFAULT '{}';

-- Option B: Separate table (preferred for cleaner separation)
CREATE TABLE user_onboarding (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_step VARCHAR(50) NOT NULL DEFAULT 'welcome',
    completed_steps TEXT[] DEFAULT '{}',
    completed_at TIMESTAMP WITH TIME ZONE,
    data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_user_onboarding UNIQUE (user_id)
);

CREATE INDEX idx_user_onboarding_user_id ON user_onboarding(user_id);
CREATE INDEX idx_user_onboarding_completed ON user_onboarding(completed_at) WHERE completed_at IS NOT NULL;
```

### SQLAlchemy Model

```python
# backend/omoi_os/models/user_onboarding.py
from sqlalchemy import Column, String, DateTime, ForeignKey, ARRAY, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now
import uuid

class UserOnboarding(Base):
    __tablename__ = "user_onboarding"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    current_step = Column(String(50), nullable=False, default="welcome")
    completed_steps = Column(ARRAY(String), default=[])
    completed_at = Column(DateTime(timezone=True), nullable=True)
    data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationship
    user = relationship("User", back_populates="onboarding")

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    __table_args__ = (
        Index("idx_user_onboarding_completed", "completed_at", postgresql_where=completed_at.isnot(None)),
    )
```

### LocalStorage Schema (Frontend)

```typescript
// Key: omoios_onboarding_state
interface OnboardingLocalState {
  currentStep: OnboardingStep
  completedSteps: OnboardingStep[]
  completedAt: string | null  // ISO timestamp
  data: {
    githubConnected: boolean
    githubUsername?: string
    selectedRepo?: { owner: string; name: string; fullName: string }
    projectId?: string
    organizationId?: string
    selectedPlan?: string
  }
  // Sync metadata
  lastSyncedAt: string  // ISO timestamp
  syncVersion: number   // Incremented on each sync
}
```

---

## API Endpoints

### Backend Routes

```python
# backend/omoi_os/api/routes/onboarding.py

@router.get("/onboarding/status")
async def get_onboarding_status(current_user: User = Depends(get_current_user)):
    """
    Get user's onboarding status.
    Returns current step, completion status, and data.
    Used by frontend to sync state.
    """

@router.post("/onboarding/step")
async def update_onboarding_step(
    step: str,
    data: dict = {},
    current_user: User = Depends(get_current_user)
):
    """
    Update user's current onboarding step.
    Called when user progresses through onboarding.
    """

@router.post("/onboarding/complete")
async def complete_onboarding(
    data: dict = {},
    current_user: User = Depends(get_current_user)
):
    """
    Mark onboarding as complete.
    Sets completed_at timestamp.
    """

@router.post("/onboarding/reset")
async def reset_onboarding(
    current_user: User = Depends(get_current_user),
    admin_override: bool = Query(False)
):
    """
    Reset onboarding to beginning.
    Requires admin role OR debug mode enabled.
    """
```

### Response Schema

```python
class OnboardingStatusResponse(BaseModel):
    is_completed: bool
    current_step: str
    completed_steps: list[str]
    completed_at: datetime | None
    data: dict
    sync_version: int
```

---

## Enforcement Logic

### Proxy/Middleware (Edge)

```typescript
// frontend/proxy.ts

const ONBOARDING_EXEMPT_ROUTES = [
  "/onboarding",
  "/callback",
  "/logout",
  "/api",
]

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Check auth
  const authCookie = request.cookies.get(AUTH_COOKIE_NAME)
  const isAuthenticated = authCookie?.value === "true"

  // Check onboarding completion (cookie set by client after sync)
  const onboardingCookie = request.cookies.get("omoios_onboarding_completed")
  const onboardingCompleted = onboardingCookie?.value === "true"

  // Skip enforcement for exempt routes
  const isExempt = ONBOARDING_EXEMPT_ROUTES.some(r => pathname.startsWith(r))

  // If authenticated but onboarding not completed -> redirect to onboarding
  if (isAuthenticated && !onboardingCompleted && !isExempt) {
    return NextResponse.redirect(new URL("/onboarding", request.url))
  }

  // ... rest of existing logic
}
```

### AuthProvider (Client-Side Fallback)

```typescript
// frontend/providers/AuthProvider.tsx

// After successful auth validation, check onboarding
useEffect(() => {
  if (!isAuthenticated || isLoading) return

  const checkOnboarding = async () => {
    try {
      const status = await api.get<OnboardingStatus>("/api/v1/onboarding/status")

      // Sync to localStorage
      syncOnboardingState(status)

      // Set cookie for middleware
      setOnboardingCookie(status.is_completed)

      // Redirect if not completed
      if (!status.is_completed && !isOnboardingRoute(pathname)) {
        router.replace("/onboarding")
      }
    } catch (err) {
      // If endpoint fails, check localStorage as fallback
      const localState = getLocalOnboardingState()
      if (!localState?.completedAt && !isOnboardingRoute(pathname)) {
        router.replace("/onboarding")
      }
    }
  }

  checkOnboarding()
}, [isAuthenticated, isLoading, pathname])
```

---

## Sync Strategy

### On Login/Auth Restore

```
1. User authenticates
2. Frontend calls GET /onboarding/status
3. Response contains server state + sync_version
4. Frontend compares sync_version with localStorage
   - If server > local: Update localStorage from server
   - If local > server: Push local changes to server (edge case)
   - If equal: No action needed
5. Set omoios_onboarding_completed cookie
```

### On Step Completion

```
1. User completes step in UI
2. Update localStorage immediately (optimistic)
3. POST /onboarding/step with new step
4. Server updates DB, returns new sync_version
5. Update localStorage sync_version
```

### On Onboarding Complete

```
1. User finishes last step
2. POST /onboarding/complete
3. Server sets completed_at, returns confirmation
4. Update localStorage with completedAt
5. Set omoios_onboarding_completed=true cookie
6. Redirect to /command or project board
```

---

## Auto-Detection of Completed Steps

### Step Completion Detection

When a user hits onboarding (new or returning), automatically detect what they've already done and pre-fill/skip those steps. Users can still change settings, but see their current state.

```typescript
// frontend/lib/onboarding/auto-detect.ts

interface DetectedState {
  github: {
    completed: boolean
    username?: string
    connectedAt?: string
  }
  repo: {
    completed: boolean
    selectedRepo?: { owner: string; name: string; fullName: string }
    availableRepos?: Array<{ owner: string; name: string }>
  }
  organization: {
    completed: boolean
    organizationId?: string
    organizationName?: string
  }
  project: {
    completed: boolean
    projectId?: string
    projectName?: string
  }
  plan: {
    completed: boolean
    currentPlan?: "free" | "pro" | "team" | "lifetime"
    subscriptionStatus?: "active" | "trialing" | "canceled"
  }
}

async function detectCompletedSteps(): Promise<DetectedState> {
  const [
    githubStatus,
    organizations,
    projects,
    subscription
  ] = await Promise.all([
    api.get("/api/v1/github/connection-status").catch(() => null),
    api.get("/api/v1/organizations").catch(() => []),
    api.get("/api/v1/projects").catch(() => []),
    api.get("/api/v1/billing/subscription").catch(() => null),
  ])

  return {
    github: {
      completed: githubStatus?.connected ?? false,
      username: githubStatus?.username,
      connectedAt: githubStatus?.connected_at,
    },
    repo: {
      completed: projects.length > 0 && projects[0]?.github_repo,
      selectedRepo: projects[0] ? {
        owner: projects[0].github_owner,
        name: projects[0].github_repo,
        fullName: `${projects[0].github_owner}/${projects[0].github_repo}`
      } : undefined,
    },
    organization: {
      completed: organizations.length > 0,
      organizationId: organizations[0]?.id,
      organizationName: organizations[0]?.name,
    },
    project: {
      completed: projects.length > 0,
      projectId: projects[0]?.id,
      projectName: projects[0]?.name,
    },
    plan: {
      completed: subscription?.status === "active" || subscription?.plan !== "free",
      currentPlan: subscription?.plan,
      subscriptionStatus: subscription?.status,
    },
  }
}
```

### Backend Detection Endpoint

```python
# backend/omoi_os/api/routes/onboarding.py

@router.get("/onboarding/detect")
async def detect_onboarding_state(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Auto-detect user's current state for onboarding steps.
    Returns what the user has already completed with their current values.
    """
    # Check GitHub connection
    github_connected = bool(
        current_user.attributes and
        current_user.attributes.get("github_access_token")
    )
    github_username = (
        current_user.attributes.get("github_username")
        if current_user.attributes else None
    )

    # Check organizations
    orgs = db.query(Organization).filter(
        Organization.members.any(user_id=current_user.id)
    ).all()

    # Check projects
    projects = db.query(Project).filter(
        Project.organization_id.in_([o.id for o in orgs])
    ).all() if orgs else []

    # Check subscription
    subscription = db.query(Subscription).filter(
        Subscription.organization_id.in_([o.id for o in orgs]),
        Subscription.status.in_(["active", "trialing"])
    ).first() if orgs else None

    return {
        "github": {
            "completed": github_connected,
            "username": github_username,
            "can_change": True,  # User can reconnect different account
        },
        "organization": {
            "completed": len(orgs) > 0,
            "current": {
                "id": orgs[0].id,
                "name": orgs[0].name,
            } if orgs else None,
            "can_change": True,  # User can create new org
        },
        "repo": {
            "completed": any(p.github_repo for p in projects),
            "current": {
                "owner": projects[0].github_owner,
                "name": projects[0].github_repo,
                "project_id": projects[0].id,
            } if projects and projects[0].github_repo else None,
            "can_change": True,  # User can select different repo
        },
        "plan": {
            "completed": subscription is not None,
            "current": {
                "plan": subscription.plan_id,
                "status": subscription.status,
            } if subscription else None,
            "can_change": True,  # User can upgrade/change plan
        },
        # Suggest which step to start at
        "suggested_step": _determine_start_step(
            github_connected, orgs, projects, subscription
        ),
    }


def _determine_start_step(github, orgs, projects, subscription) -> str:
    """Determine which onboarding step user should start at."""
    if not github:
        return "github"
    if not orgs:
        return "organization"  # If we add this step
    if not any(p.github_repo for p in projects):
        return "repo"
    if not subscription:
        return "plan"
    return "complete"
```

### UI Behavior for Pre-filled Steps

```typescript
// frontend/components/onboarding/steps/GitHubStep.tsx

function GitHubStep({ detectedState }: { detectedState: DetectedState }) {
  const { github } = detectedState

  if (github.completed) {
    // Show current connection with option to change
    return (
      <div>
        <div className="flex items-center gap-3 p-4 bg-green-500/10 rounded-lg">
          <CheckCircle className="text-green-500" />
          <div>
            <p className="font-medium">GitHub Connected</p>
            <p className="text-sm text-muted-foreground">
              Connected as @{github.username}
            </p>
          </div>
        </div>

        <Button variant="outline" onClick={reconnectGitHub}>
          Connect Different Account
        </Button>

        <Button onClick={nextStep}>
          Continue with @{github.username}
        </Button>
      </div>
    )
  }

  // Show normal connection flow
  return <GitHubConnectFlow />
}
```

```typescript
// frontend/components/onboarding/steps/RepoSelectStep.tsx

function RepoSelectStep({ detectedState }: { detectedState: DetectedState }) {
  const { repo } = detectedState
  const [selectedRepo, setSelectedRepo] = useState(repo.current)

  return (
    <div>
      {repo.completed && (
        <div className="mb-4 p-4 bg-blue-500/10 rounded-lg">
          <p className="text-sm text-muted-foreground">
            You previously selected:
          </p>
          <p className="font-medium">{repo.current?.fullName}</p>
        </div>
      )}

      <RepoSelector
        value={selectedRepo}
        onChange={setSelectedRepo}
        defaultValue={repo.current}
      />

      <Button onClick={() => confirmRepo(selectedRepo)}>
        {repo.completed ? "Continue with this repo" : "Select Repository"}
      </Button>
    </div>
  )
}
```

```typescript
// frontend/components/onboarding/steps/PlanSelectStep.tsx

function PlanSelectStep({ detectedState }: { detectedState: DetectedState }) {
  const { plan } = detectedState

  if (plan.completed && plan.current?.status === "active") {
    // User already has active subscription
    return (
      <div>
        <div className="p-4 bg-green-500/10 rounded-lg mb-4">
          <p className="font-medium">You're on the {plan.current.plan} plan</p>
          <p className="text-sm text-muted-foreground">
            Your subscription is active
          </p>
        </div>

        <Button variant="outline" onClick={goToBilling}>
          Manage Subscription
        </Button>

        <Button onClick={completeOnboarding}>
          Continue to Dashboard
        </Button>
      </div>
    )
  }

  // Show plan selection
  return <PlanSelector currentPlan={plan.current?.plan} />
}
```

### Onboarding Flow with Auto-Detection

```typescript
// frontend/app/(auth)/onboarding/page.tsx

export default function OnboardingPage() {
  const [detectedState, setDetectedState] = useState<DetectedState | null>(null)
  const [isDetecting, setIsDetecting] = useState(true)

  useEffect(() => {
    async function detect() {
      try {
        const state = await api.get("/api/v1/onboarding/detect")
        setDetectedState(state)

        // Auto-advance to suggested step
        if (state.suggested_step !== "welcome") {
          goToStep(state.suggested_step)
        }
      } catch (err) {
        // Fallback to fresh onboarding
        console.error("Failed to detect state:", err)
      } finally {
        setIsDetecting(false)
      }
    }
    detect()
  }, [])

  if (isDetecting) {
    return <OnboardingLoader message="Checking your account..." />
  }

  return (
    <OnboardingWizard
      detectedState={detectedState}
      initialStep={detectedState?.suggested_step || "welcome"}
    />
  )
}
```

---

## Auto-Detection & Self-Healing

### Inconsistency Detection

```typescript
// frontend/lib/onboarding/sync.ts

interface SyncResult {
  status: "synced" | "healed" | "conflict"
  action?: string
}

async function detectAndHealInconsistencies(): Promise<SyncResult> {
  const localState = getLocalOnboardingState()
  const serverState = await api.get<OnboardingStatus>("/api/v1/onboarding/status")

  // Case 1: Server says complete, local says incomplete
  if (serverState.is_completed && !localState?.completedAt) {
    syncLocalFromServer(serverState)
    setOnboardingCookie(true)
    return { status: "healed", action: "local_updated_from_server" }
  }

  // Case 2: Local says complete, server says incomplete
  // Trust server (source of truth), reset local
  if (!serverState.is_completed && localState?.completedAt) {
    syncLocalFromServer(serverState)
    setOnboardingCookie(false)
    return { status: "healed", action: "local_reset_from_server" }
  }

  // Case 3: Steps mismatch
  if (serverState.current_step !== localState?.currentStep) {
    // Server wins
    syncLocalFromServer(serverState)
    return { status: "healed", action: "step_synced" }
  }

  // Case 4: Cookie missing but should be set
  const cookie = getCookie("omoios_onboarding_completed")
  if (serverState.is_completed && cookie !== "true") {
    setOnboardingCookie(true)
    return { status: "healed", action: "cookie_restored" }
  }

  return { status: "synced" }
}
```

### Periodic Sync

```typescript
// Run on:
// 1. App mount
// 2. Window focus (user returns to tab)
// 3. Every 5 minutes while app is active

useEffect(() => {
  const sync = () => detectAndHealInconsistencies()

  sync() // Initial

  window.addEventListener("focus", sync)
  const interval = setInterval(sync, 5 * 60 * 1000)

  return () => {
    window.removeEventListener("focus", sync)
    clearInterval(interval)
  }
}, [])
```

---

## Debugging Tools

### Browser Console Commands

```typescript
// Expose on window object in development/staging
declare global {
  interface Window {
    omoiosDebug: {
      onboarding: {
        getState: () => OnboardingLocalState | null
        getServerState: () => Promise<OnboardingStatus>
        reset: () => Promise<void>
        complete: () => Promise<void>
        skipToStep: (step: string) => void
        clearLocal: () => void
        sync: () => Promise<SyncResult>
      }
    }
  }
}

// Usage in browser console:
// omoiosDebug.onboarding.getState()        - View localStorage state
// omoiosDebug.onboarding.getServerState()  - Fetch server state
// omoiosDebug.onboarding.reset()           - Reset onboarding (calls API)
// omoiosDebug.onboarding.complete()        - Force complete (calls API)
// omoiosDebug.onboarding.skipToStep("plan") - Jump to specific step
// omoiosDebug.onboarding.clearLocal()      - Clear localStorage only
// omoiosDebug.onboarding.sync()            - Force sync with server
```

### Implementation

```typescript
// frontend/lib/debug/onboarding.ts

export function initOnboardingDebug() {
  if (typeof window === "undefined") return

  // Only enable in development or with debug flag
  const isDebugEnabled =
    process.env.NODE_ENV === "development" ||
    localStorage.getItem("omoios_debug") === "true"

  if (!isDebugEnabled) return

  window.omoiosDebug = window.omoiosDebug || {}
  window.omoiosDebug.onboarding = {
    getState: () => {
      const raw = localStorage.getItem("omoios_onboarding_state")
      return raw ? JSON.parse(raw) : null
    },

    getServerState: async () => {
      return api.get("/api/v1/onboarding/status")
    },

    reset: async () => {
      await api.post("/api/v1/onboarding/reset")
      localStorage.removeItem("omoios_onboarding_state")
      document.cookie = "omoios_onboarding_completed=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
      console.log("Onboarding reset. Refresh the page.")
    },

    complete: async () => {
      await api.post("/api/v1/onboarding/complete", {})
      const state = window.omoiosDebug.onboarding.getState() || {}
      state.completedAt = new Date().toISOString()
      localStorage.setItem("omoios_onboarding_state", JSON.stringify(state))
      document.cookie = "omoios_onboarding_completed=true; path=/; max-age=31536000"
      console.log("Onboarding marked complete. Refresh the page.")
    },

    skipToStep: (step: string) => {
      const state = window.omoiosDebug.onboarding.getState() || {
        currentStep: "welcome",
        completedSteps: [],
        completedAt: null,
        data: { githubConnected: false },
        lastSyncedAt: new Date().toISOString(),
        syncVersion: 0
      }
      state.currentStep = step
      localStorage.setItem("omoios_onboarding_state", JSON.stringify(state))
      console.log(`Skipped to step: ${step}. Refresh the page.`)
    },

    clearLocal: () => {
      localStorage.removeItem("omoios_onboarding_state")
      document.cookie = "omoios_onboarding_completed=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
      console.log("Local onboarding state cleared. Refresh the page.")
    },

    sync: async () => {
      const result = await detectAndHealInconsistencies()
      console.log("Sync result:", result)
      return result
    }
  }

  console.log("🔧 Onboarding debug tools enabled. Use: omoiosDebug.onboarding")
}
```

### Admin API Endpoint

```python
# For support team to reset user onboarding

@router.post("/admin/users/{user_id}/onboarding/reset")
async def admin_reset_onboarding(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to reset a user's onboarding.
    Requires admin role.
    """
    # Reset onboarding record
    # Log action for audit trail
    pass
```

---

## Environment-Specific Behavior

| Environment | Onboarding Enforcement | Debug Tools | Reset API |
|-------------|------------------------|-------------|-----------|
| Development | Optional (can bypass)  | Enabled     | Open      |
| Staging     | Enforced               | Enabled     | Admin only|
| Production  | Enforced               | Disabled*   | Admin only|

*Debug tools can be enabled in production by setting `localStorage.setItem("omoios_debug", "true")` - useful for support.

---

## Implementation Checklist

### Backend
- [ ] Create `user_onboarding` table migration
- [ ] Add `UserOnboarding` SQLAlchemy model
- [ ] Create `GET /api/v1/onboarding/status` endpoint
- [ ] Create `POST /api/v1/onboarding/step` endpoint
- [ ] Create `POST /api/v1/onboarding/complete` endpoint
- [ ] Create `POST /api/v1/onboarding/reset` endpoint
- [ ] Add admin reset endpoint
- [ ] Auto-create onboarding record on user creation

### Frontend
- [ ] Update `proxy.ts` to check onboarding cookie
- [ ] Add onboarding sync service (`lib/onboarding/sync.ts`)
- [ ] Update `AuthProvider` to trigger onboarding check
- [ ] Add `omoios_onboarding_completed` cookie management
- [ ] Implement debug tools (`lib/debug/onboarding.ts`)
- [ ] Initialize debug tools in app layout
- [ ] Update `useOnboarding` hook to sync with server

### Testing
- [ ] Test new user -> onboarding flow
- [ ] Test returning user with incomplete onboarding
- [ ] Test completed user bypasses onboarding
- [ ] Test sync after localStorage cleared
- [ ] Test debug reset functionality
- [ ] Test cross-device state consistency

---

## Migration Strategy

For existing users who never went through formal onboarding:

```python
# One-time migration script
async def backfill_onboarding_status():
    """
    For existing users, check if they have:
    - At least one project -> mark onboarding complete
    - GitHub connected -> mark github step complete
    - Active subscription -> mark plan step complete

    Otherwise, leave as incomplete (they'll see onboarding on next login)
    """
    pass
```

---

## See Also

- `frontend/hooks/useOnboarding.ts` - Current client-side implementation
- `frontend/proxy.ts` - Edge middleware
- `frontend/providers/AuthProvider.tsx` - Auth state management
