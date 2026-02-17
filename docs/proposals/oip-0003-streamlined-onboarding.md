```
OIP: 0003
Title: Streamlined Onboarding with Deferred GitHub
Description: Reduce onboarding from 6 steps to 2 by deferring GitHub OAuth and plan selection to point-of-need
Author: Kevin Hill
Status: Draft
Type: Standards Track
Created: 2026-02-17
```

## Abstract

Restructure the onboarding wizard from 6 mandatory steps (welcome, GitHub, repo, first-spec, plan, complete) to 2 steps (welcome, first-spec). GitHub OAuth, repository selection, and plan selection are deferred to the moments they are actually needed — GitHub at PR creation time (~30-60 minutes into usage), plan selection at the free tier limit. This reduces time-to-first-value from 8-15 minutes to approximately 2-3 minutes.

## Motivation

The current onboarding flow is defined in `frontend/hooks/useOnboarding.ts` at line 92:

```typescript
const STEPS_ORDER: OnboardingStep[] = [
  "welcome",    // Role selection
  "github",     // GitHub OAuth connection
  "repo",       // Repository selection
  "first-spec", // Write first feature spec
  "plan",       // Choose pricing plan
  "complete",   // Success screen
]
```

Each step is rendered by the `OnboardingWizard` (`frontend/components/onboarding/OnboardingWizard.tsx`) which maps steps to components:

```typescript
const STEP_COMPONENTS: Record<OnboardingStep, React.ComponentType> = {
  welcome: WelcomeStep,
  github: GitHubStep,
  repo: RepoSelectStep,
  "first-spec": FirstSpecStep,
  plan: PlanSelectStep,
  complete: CompleteStep,
}
```

**The fundamental problem**: Steps 2-3 (GitHub + repo) and step 5 (plan) create blocking gates that provide zero product value. They exist for operational reasons (we need a repo to push code to, we need a plan for billing) but are asked at the wrong time.

### Analysis of Each Step

| Step | Value to User | When Actually Needed | Current Timing |
|------|--------------|---------------------|----------------|
| Welcome | Sets context | Immediately | Correct |
| GitHub OAuth | None (setup) | When creating a PR (~30-60 min in) | Too early |
| Repo Selection | None (setup) | When creating a PR (~30-60 min in) | Too early |
| First Spec | High (core product) | Immediately | Correct |
| Plan Selection | None (billing) | When free tier limit reached | Too early |
| Complete | Low (confirmation) | After first spec launched | Remove entirely |

**Key insight from `useOnboarding.ts`**: The `submitFirstSpec` function (line ~180) auto-creates an organization and project if none exist. The org slug comes from the user's email prefix. This means the system already handles the case where a user hasn't set up GitHub — it creates infrastructure automatically.

**GitHub is only needed at PR creation time**. The spec pipeline (EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC) runs entirely within OmoiOS sandboxes. GitHub is only touched at the very end when the agent creates a PR. A user can experience the entire spec workflow — watching agents analyze requirements, design architecture, break down tasks, and write code — without ever connecting GitHub.

### Conversion Funnel Impact

Current funnel (estimated drop-off at each gate):
```
Landing Page → Register (10% convert)
  → Welcome step (95% continue)
    → GitHub OAuth (60% continue — 40% drop off at OAuth permission screen)
      → Repo Selection (85% continue)
        → First Spec (70% continue — some don't know what to write)
          → Plan Selection (80% continue — payment anxiety)
            → Complete (95% continue)
              → Actually see product value

Effective conversion: 10% * 95% * 60% * 85% * 70% * 80% * 95% = ~2.7% of landing visitors
```

Proposed funnel:
```
Landing Page → Register (10% convert)
  → Welcome step (95% continue)
    → First Spec (85% continue — suggestion chips help)
      → See product value immediately

Effective conversion to value: 10% * 95% * 85% = ~8.1% of landing visitors (3x improvement)
```

## Specification

### 1. Reduced STEPS_ORDER

**Modified file**: `frontend/hooks/useOnboarding.ts`

```typescript
const STEPS_ORDER: OnboardingStep[] = [
  "welcome",
  "first-spec",
]
```

The `OnboardingStep` type retains all values for backwards compatibility (existing users may have partial onboarding state stored), but the wizard only navigates through the reduced set.

### 2. Modified submitFirstSpec

**Modified file**: `frontend/hooks/useOnboarding.ts`

The `submitFirstSpec` function currently requires `organizationId` and `projectId` to exist (created during GitHub/repo steps). With deferred GitHub:

```typescript
async function submitFirstSpec(specText: string) {
  // Auto-create organization from email (already supported)
  const org = await getOrCreateOrganization(user.email)

  // Auto-create a default project (no GitHub repo required)
  const project = await getOrCreateDefaultProject(org.id, {
    name: "My First Project",
    source: "onboarding",
    // No github_repo_url — will be set later when GitHub is connected
  })

  // Launch spec with auto_execute=true
  const spec = await launchSpec({
    projectId: project.id,
    text: specText,
    auto_execute: true,
  })

  // Navigate to sandbox view to watch the agent work
  router.push(`/sandbox/${spec.sandboxId}`)
}
```

### 3. Deferred GitHub Connection

**New component**: `frontend/components/github/GitHubConnectPrompt.tsx`

A contextual prompt that appears at the moment GitHub is needed:

```typescript
interface GitHubConnectPromptProps {
  trigger: "pr_ready" | "repo_needed" | "settings"
  specId?: string
  onConnected: () => void
  onSkip?: () => void
}
```

This component is shown:
- **At PR creation time**: When the agent finishes a spec and is ready to create a PR, the sandbox view shows: "Your code is ready! Connect GitHub to create a PR, or download as a zip."
- **In project settings**: Users can connect GitHub at any time from project settings.
- **On the /command page**: A subtle banner shows "Connect GitHub to enable PR creation" — dismissable, not blocking.

**Modified file**: `frontend/app/(app)/sandbox/[sandboxId]/page.tsx`

Add a `GitHubConnectPrompt` that appears when the sandbox reaches "completed" status and no GitHub repo is linked to the project:

```typescript
{sandbox.status === "completed" && !project.githubRepoUrl && (
  <GitHubConnectPrompt
    trigger="pr_ready"
    specId={sandbox.specId}
    onConnected={() => {
      // Re-trigger PR creation with the newly connected repo
      createPR(sandbox.specId, project.githubRepoUrl)
    }}
    onSkip={() => {
      // Offer zip download or clipboard copy
      showExportOptions()
    }}
  />
)}
```

### 4. Deferred Plan Selection

**Modified file**: `frontend/hooks/useOnboarding.ts`

Remove `PlanSelectStep` from the onboarding flow. Plan selection is triggered by usage limits:

**New component**: `frontend/components/billing/UsageLimitPrompt.tsx`

Appears when the user hits the free tier limit (5 workflows/month as shown in `FirstSpecStep`):

```typescript
interface UsageLimitPromptProps {
  currentUsage: number
  limit: number
  onUpgrade: () => void
  onDismiss: () => void
}
```

This prompt appears inline on the `/command` page when the user tries to launch a 6th spec:

```
You've used 5/5 free workflows this month.
Upgrade to Pro for unlimited workflows.
[Upgrade to Pro — $50/mo] [Remind me later]
```

### 5. Backend: Projects Without GitHub

**Modified file**: `backend/omoi_os/api/routes/projects.py` (or equivalent)

Ensure the project creation endpoint allows `github_repo_url` to be `null`. The spec execution pipeline must handle projects without a linked repository:

- Sandboxes run normally (Daytona doesn't need GitHub)
- The SYNC phase (PR creation) checks for a linked repo
- If no repo is linked, the SYNC phase is skipped and the spec completes with a "Ready for export" status
- The completed sandbox includes a "Connect GitHub to create PR" prompt and a "Download as zip" fallback

### 6. Migration for Existing Users

Users who already completed the full 6-step onboarding are unaffected. Their GitHub connections and repo selections remain intact.

New users who register after this change:
- Complete 2-step onboarding (welcome → first-spec)
- See agents work immediately
- Are prompted for GitHub when a PR is ready
- Are prompted for plan upgrade when free tier is exhausted

Users who abandoned the old 6-step flow mid-way:
- On next login, skip to the reduced flow (welcome → first-spec)
- Any partial onboarding state (e.g., GitHub connected but no spec) is preserved

## Rationale

### Why defer GitHub instead of making it optional?

Making GitHub "optional" in the existing flow still presents it as a step, creating decision fatigue. Deferring it entirely removes the cognitive load. The user doesn't even think about GitHub until they have working code they want to push.

### Why keep the welcome step?

The `WelcomeStep` collects the user's role (developer, PM, founder, etc.) which is used for analytics segmentation and spec suggestion personalization. It's a low-friction step (single click) with genuine product value.

### Why not defer everything and just show the command center?

The first-spec step during onboarding serves a critical purpose: it ensures the user's first experience includes watching an agent work. Without it, a new user lands on an empty `/command` page and has to figure out what to do. The guided first-spec step with suggestion chips ("Add user authentication", "Build a REST API", etc.) provides the push needed to start.

### Why not just add "Skip" buttons to existing steps?

The `GitHubStep` (`frontend/components/onboarding/steps/GitHubStep.tsx`) and `RepoSelectStep` already have skip buttons. But skip buttons still present the step — forcing the user to read, understand, and decide to skip. Each decision point is a potential abandonment. Removing the steps entirely eliminates these decision points.

## Backwards Compatibility

### Frontend State

The `useOnboarding` hook uses Zustand with `persist` middleware (stored in localStorage via `createSafeStorage`). Existing users may have serialized state referencing old steps. The migration path:

- `completedSteps` array may contain `"github"`, `"repo"`, `"plan"`, `"complete"` — these are ignored by the reduced `STEPS_ORDER` but don't cause errors.
- `currentStep` may be set to a removed step — the hook should fall back to `"first-spec"` if `currentStep` is not in `STEPS_ORDER`.
- `OnboardingData` fields (`githubConnected`, `selectedRepo`, `selectedPlan`) remain in the type definition for backwards compatibility but are no longer populated during onboarding.

### Backend API

No breaking API changes. The `onboarding_status` endpoint continues to accept all step names. The frontend simply stops sending updates for removed steps.

### Analytics

Onboarding funnel analytics will show a discontinuity at the deployment date. Document this in analytics annotations so the conversion rate change isn't misinterpreted as an anomaly.

## Security Considerations

- **GitHub OAuth deferral**: No security impact. OAuth is initiated by the user at a later time with the same scope and permissions.
- **Projects without repos**: Sandbox isolation is handled by Daytona regardless of GitHub connection status. No additional attack surface.
- **Plan deferral**: Free tier limits are still enforced server-side. Moving the plan selection UI doesn't change the enforcement mechanism.

## Impact Assessment

**Effort**: Medium. Primary changes are in `useOnboarding.ts` (reduce step array, modify submitFirstSpec), `OnboardingWizard.tsx` (remove step components from flow), and new contextual prompts for GitHub and plan selection. Backend changes are minimal — ensuring projects work without GitHub repos.

**Infrastructure cost**: None. This is purely a UX restructuring.

**Expected impact**: 3x improvement in conversion-to-value rate (from ~2.7% to ~8.1% of landing visitors). Users reach their first "wow moment" (watching an agent build software) in 2-3 minutes instead of 8-15 minutes.

**Success metrics**:
- Onboarding completion rate (expect significant increase)
- Time from registration to first spec launch (expect decrease from 8-15 min to 2-3 min)
- 7-day retention rate (expect increase — users who see value early are more likely to return)
- GitHub connection rate at PR-ready time (new metric — measures deferred conversion)
- Plan upgrade conversion rate at usage limit (new metric)

## Open Issues

1. Should the welcome step collect role, or should it be deferred to a profile settings page?
2. How should the `/command` page handle the case where no project exists yet? Currently it auto-creates one — should this happen silently or with a brief explanation?
3. Should there be a "Getting Started" checklist on the `/command` page that nudges users toward connecting GitHub and selecting a plan — without blocking them?
4. What's the zip export format for users who never connect GitHub? Raw source files, or a complete git repo with commit history?
