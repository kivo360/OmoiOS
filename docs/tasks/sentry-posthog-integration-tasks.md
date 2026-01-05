# Sentry & PostHog Integration Tasks for Claude Code Web

These tasks are designed to be completed by Claude Code web. Each task includes research/exploration, planning, implementation, and documentation phases. Tasks are scoped to be completable in a single session while being substantial enough for meaningful progress.

---

## Phase 1: Frontend Analytics Foundation (PostHog)

### Task 1.1: PostHog Frontend Setup with Session Recording

**Objective**: Set up PostHog in the Next.js 15 frontend with session recording, autocapture, and proper App Router integration. This enables watching full user sessions to understand how users navigate to payment.

**Research/Explore Phase**:
1. Read the existing `trackEvent` function in `frontend/hooks/useOnboarding.ts` (lines 407-415) - it's a placeholder
2. Check if there's a `package.json` in frontend for existing dependencies
3. Look at `frontend/providers/` directory for existing provider patterns
4. Review `frontend/app/layout.tsx` for how providers are wrapped
5. Search for any existing analytics setup: `grep -r "posthog\|analytics" frontend/`
6. List all pages in `frontend/app/` to understand the full application structure

**Planning Phase**:
1. Document which PostHog features we need (ALL of these are required):
   - **Session Recording** - Watch full user sessions, see exactly what users click
   - **Autocapture** - Automatically track all clicks, form submissions, page views
   - **Event tracking** - Custom events for business logic
   - **User identification** - Link sessions to users
   - **Feature flags** - For A/B testing pricing and features
   - **Heatmaps** - See where users click most (requires session recording)
2. Plan the provider architecture for Next.js App Router
3. Identify all files that need modification
4. Plan session recording privacy settings (mask sensitive inputs)

**Implementation Phase**:
1. Install PostHog: `pnpm add posthog-js`
2. Create `frontend/lib/analytics/posthog.ts` - PostHog client initialization with:
   ```typescript
   posthog.init(key, {
     api_host: 'https://app.posthog.com',
     autocapture: true,  // Capture all clicks automatically
     capture_pageview: true,  // Track all page views
     capture_pageleave: true,  // Track when users leave
     session_recording: {
       maskAllInputs: false,  // Show inputs (except passwords)
       maskInputOptions: { password: true },
     },
     enable_heatmaps: true,
   })
   ```
3. Create `frontend/providers/PostHogProvider.tsx` - React context provider with pageview tracking
4. Create `frontend/lib/analytics/events.ts` - Typed event definitions
5. Add environment variables to `.env.example`:
   - `NEXT_PUBLIC_POSTHOG_KEY`
   - `NEXT_PUBLIC_POSTHOG_HOST` (optional, defaults to PostHog cloud)
6. Update `frontend/app/layout.tsx` to include PostHogProvider
7. Add PostHog toolbar for development (opt-in feature flags testing)

**Documentation Phase**:
1. Create `frontend/docs/analytics-setup.md` documenting:
   - How to add new events
   - Session recording configuration
   - Privacy/masking settings
   - Environment variable requirements
   - How to watch session recordings in PostHog

**Acceptance Criteria**:
- [ ] PostHog initializes on app load
- [ ] Session recordings appear in PostHog dashboard
- [ ] Autocapture tracks clicks on buttons, links, forms
- [ ] Page views are automatically tracked
- [ ] No errors in browser console
- [ ] Provider wraps the entire app
- [ ] Sensitive inputs (passwords) are masked in recordings
- [ ] TypeScript types are properly defined

---

### Task 1.2: Implement Core Analytics Events

**Objective**: Replace placeholder `trackEvent` with real PostHog implementation and add core business events.

**Research/Explore Phase**:
1. Find all existing `trackEvent` calls: `grep -r "trackEvent" frontend/`
2. Review `frontend/hooks/useOnboarding.ts` for onboarding-specific events
3. Check `frontend/lib/api/billing.ts` for billing-related actions
4. Look at `frontend/components/onboarding/` for user flow touchpoints
5. Review Stripe integration in billing for checkout events

**Planning Phase**:
1. Create event taxonomy document listing all events:
   - Onboarding events (step viewed, completed, skipped)
   - Billing events (checkout started, completed, failed)
   - Feature usage events (spec created, project created)
   - Error events (API failures, validation errors)
2. Define event properties schema for each event type
3. Plan user identification strategy (when to call `posthog.identify`)

**Implementation Phase**:
1. Update `frontend/lib/analytics/events.ts` with typed event names:
   ```typescript
   export const ANALYTICS_EVENTS = {
     ONBOARDING_STEP_VIEWED: 'onboarding_step_viewed',
     CHECKOUT_STARTED: 'checkout_started',
     CHECKOUT_COMPLETED: 'checkout_completed',
     // ... etc
   } as const
   ```
2. Create `frontend/lib/analytics/track.ts` with the main tracking function
3. Update `frontend/hooks/useOnboarding.ts` to use real tracking
4. Add tracking to `frontend/hooks/useBilling.ts` for checkout events
5. Create `frontend/hooks/useAnalytics.ts` - React hook for easy tracking

**Documentation Phase**:
1. Update `frontend/docs/analytics-setup.md` with:
   - Complete event catalog
   - Event property schemas
   - Example usage patterns

**Acceptance Criteria**:
- [ ] All existing trackEvent calls use real PostHog
- [ ] Events appear in PostHog dashboard
- [ ] User identification works after login
- [ ] No PII is accidentally tracked

---

### Task 1.3: PostHog User Identification & Properties

**Objective**: Properly identify users and set user properties for segmentation.

**Research/Explore Phase**:
1. Review `frontend/providers/AuthProvider.tsx` for auth flow
2. Check `frontend/hooks/useAuth.ts` for user data structure
3. Look at user object returned from `/api/v1/auth/me`
4. Review when users are considered "logged in" vs "anonymous"

**Planning Phase**:
1. Define user properties to track:
   - `email` (hashed or excluded based on privacy needs)
   - `plan_type` (free, pro, lifetime)
   - `organization_id`
   - `github_connected` (boolean)
   - `created_at`
2. Plan identification timing (after login, on page load if logged in)
3. Determine how to handle anonymous → identified user merging

**Implementation Phase**:
1. Create `frontend/lib/analytics/identify.ts` - user identification logic
2. Update `frontend/providers/AuthProvider.tsx` to call identify on auth
3. Add `posthog.reset()` on logout
4. Set super properties for common attributes
5. Handle organization context for B2B tracking

**Documentation Phase**:
1. Document user identification flow
2. Add privacy considerations section
3. Document how to add new user properties

**Acceptance Criteria**:
- [ ] Users are identified after login
- [ ] User properties appear in PostHog
- [ ] Anonymous sessions merge correctly with identified users
- [ ] Logout properly resets PostHog state

---

## Phase 2: Frontend Error Tracking (Sentry)

### Task 2.1: Sentry Frontend Setup & Configuration

**Objective**: Set up Sentry error tracking for the Next.js frontend with proper source maps.

**Research/Explore Phase**:
1. Check Next.js version in `frontend/package.json`
2. Review `frontend/next.config.js` for existing config
3. Look for any existing error boundary components
4. Check if there's a global error handler in `frontend/app/error.tsx`
5. Review build process for source map generation

**Planning Phase**:
1. Document Sentry features needed:
   - Error tracking
   - Performance monitoring
   - Session replay (optional)
   - Source maps for stack traces
2. Plan Sentry configuration for Next.js App Router
3. Identify integration points (error boundaries, API calls)

**Implementation Phase**:
1. Install Sentry: `pnpm add @sentry/nextjs`
2. Run Sentry wizard or manual setup:
   - Create `frontend/sentry.client.config.ts`
   - Create `frontend/sentry.server.config.ts`
   - Create `frontend/sentry.edge.config.ts`
3. Update `frontend/next.config.js` with Sentry webpack plugin
4. Add environment variables to `.env.example`:
   - `NEXT_PUBLIC_SENTRY_DSN`
   - `SENTRY_AUTH_TOKEN` (for source maps)
   - `SENTRY_ORG`
   - `SENTRY_PROJECT`
5. Create custom error boundary component

**Documentation Phase**:
1. Create `frontend/docs/error-tracking.md` documenting:
   - How errors are captured
   - How to manually report errors
   - Source map upload process

**Acceptance Criteria**:
- [ ] Sentry initializes without errors
- [ ] Test error is captured in Sentry dashboard
- [ ] Source maps work (stack traces show original code)
- [ ] No performance impact on page load

---

### Task 2.2: Sentry Error Context & Breadcrumbs

**Objective**: Add rich context to Sentry errors for better debugging.

**Research/Explore Phase**:
1. Review API client in `frontend/lib/api/client.ts` for error handling
2. Check React Query error handling patterns
3. Look at form validation errors in components
4. Review authentication error flows

**Planning Phase**:
1. Define error context to capture:
   - User context (id, email hash, plan)
   - Request context (URL, method, status)
   - Application state (current route, feature flags)
2. Plan breadcrumb strategy:
   - Navigation breadcrumbs
   - API call breadcrumbs
   - User action breadcrumbs
3. Define error categories for filtering

**Implementation Phase**:
1. Create `frontend/lib/sentry/context.ts` - context management
2. Update API client to add Sentry breadcrumbs on requests
3. Add user context on authentication
4. Create error wrapper for React Query
5. Add custom tags for error categorization:
   - `error.category`: `api`, `validation`, `auth`, `network`
   - `error.severity`: `fatal`, `error`, `warning`

**Documentation Phase**:
1. Document error context fields
2. Add troubleshooting guide for common errors
3. Document how to add custom context

**Acceptance Criteria**:
- [ ] Errors include user context
- [ ] API errors show request details
- [ ] Breadcrumbs show user journey before error
- [ ] Errors are properly categorized

---

### Task 2.3: Sentry Performance Monitoring

**Objective**: Enable Sentry performance monitoring for frontend transactions.

**Research/Explore Phase**:
1. Review Next.js App Router data fetching patterns
2. Check for any existing performance monitoring
3. Look at critical user flows (onboarding, checkout)
4. Review API call patterns and timing

**Planning Phase**:
1. Define transactions to monitor:
   - Page loads (automatic with Next.js integration)
   - Onboarding flow (custom transaction)
   - Checkout flow (custom transaction)
   - API calls (as spans)
2. Set performance sampling rates
3. Identify slow operations to focus on

**Implementation Phase**:
1. Update Sentry config to enable performance monitoring
2. Create `frontend/lib/sentry/performance.ts` - custom transaction helpers
3. Add custom spans for:
   - API calls
   - State hydration
   - Heavy computations
4. Configure transaction sampling:
   - 100% for development
   - 10-20% for production
5. Add Web Vitals tracking

**Documentation Phase**:
1. Document performance monitoring setup
2. Add guide for creating custom transactions
3. Document performance budgets and alerts

**Acceptance Criteria**:
- [ ] Page load transactions appear in Sentry
- [ ] Custom transactions for critical flows
- [ ] Web Vitals are tracked
- [ ] No significant performance overhead

---

## Phase 3: Backend Analytics & Error Tracking

### Task 3.1: Sentry Backend Setup (FastAPI)

**Objective**: Set up Sentry for the FastAPI backend with proper async support.

**Research/Explore Phase**:
1. Check existing logging in `backend/omoi_os/logging.py`
2. Review `backend/omoi_os/api/main.py` for app initialization
3. Look at existing error handling middleware
4. Check for any observability setup in `backend/omoi_os/observability/`
5. Review async patterns used in the codebase

**Planning Phase**:
1. Document Sentry features for backend:
   - Exception tracking
   - Performance monitoring (traces)
   - Cron job monitoring
   - Queue job monitoring
2. Plan integration points:
   - FastAPI middleware
   - Background workers
   - Celery/Redis tasks (if applicable)
3. Define environment-specific settings

**Implementation Phase**:
1. Add Sentry to dependencies: `uv add sentry-sdk[fastapi]`
2. Create `backend/omoi_os/observability/sentry.py`:
   - Initialization function
   - Environment-based configuration
   - Custom before_send hook for PII filtering
3. Update `backend/omoi_os/api/main.py` to initialize Sentry
4. Add Sentry to worker processes
5. Configure async support properly

**Documentation Phase**:
1. Create `backend/docs/observability/sentry-setup.md`
2. Document error filtering rules
3. Add troubleshooting guide

**Acceptance Criteria**:
- [ ] Sentry captures backend exceptions
- [ ] Async errors are properly captured
- [ ] Worker errors are tracked
- [ ] PII is properly filtered

---

### Task 3.2: Backend Event Tracking (PostHog Server-Side)

**Objective**: Implement server-side PostHog tracking for billing and critical backend events.

**Research/Explore Phase**:
1. Review `backend/omoi_os/api/routes/billing.py` for webhook handlers
2. Check Stripe webhook events being processed
3. Look at `backend/omoi_os/services/billing_service.py`
4. Review user creation and authentication flows
5. Check for existing event publishing patterns

**Planning Phase**:
1. Define server-side events:
   - `checkout_session_completed` (Stripe webhook)
   - `subscription_created`
   - `subscription_cancelled`
   - `workflow_started`
   - `workflow_completed`
   - `workflow_failed`
2. Plan PostHog server-side integration
3. Define event properties and user identification

**Implementation Phase**:
1. Add PostHog Python SDK: `uv add posthog`
2. Create `backend/omoi_os/analytics/posthog.py`:
   - Client initialization
   - Event tracking function
   - User identification
3. Add tracking to Stripe webhook handlers:
   - `checkout.session.completed` → `checkout_completed`
   - `customer.subscription.created` → `subscription_created`
4. Add tracking to sandbox/workflow events
5. Ensure user_id consistency with frontend

**Documentation Phase**:
1. Create `backend/docs/analytics/server-side-tracking.md`
2. Document event schemas
3. Add guide for adding new events

**Acceptance Criteria**:
- [ ] Stripe webhook events tracked in PostHog
- [ ] User IDs match between frontend and backend
- [ ] Events include proper properties
- [ ] No duplicate events

---

### Task 3.3: Backend Performance Tracing

**Objective**: Implement distributed tracing for backend services.

**Research/Explore Phase**:
1. Review database operations in `backend/omoi_os/services/database.py`
2. Check async task patterns in workers
3. Look at external API calls (GitHub, Stripe, OpenAI)
4. Review critical API endpoints for performance

**Planning Phase**:
1. Define tracing strategy:
   - Database query tracing
   - External API call tracing
   - Background task tracing
2. Plan span naming conventions
3. Define custom tags and attributes

**Implementation Phase**:
1. Update Sentry config for tracing
2. Add SQLAlchemy instrumentation
3. Create `backend/omoi_os/observability/tracing.py`:
   - Custom span decorators
   - Context propagation helpers
4. Instrument critical paths:
   - Sandbox execution
   - GitHub API calls
   - Stripe API calls
5. Add request ID propagation for correlation

**Documentation Phase**:
1. Document tracing architecture
2. Add guide for adding custom spans
3. Document performance debugging workflow

**Acceptance Criteria**:
- [ ] Database queries appear as spans
- [ ] External API calls are traced
- [ ] Traces connect frontend → backend
- [ ] Critical paths are fully instrumented

---

## Phase 4: Integration & Dashboard Setup

### Task 4.1: PostHog Dashboard & Funnels

**Objective**: Create PostHog dashboards for key business metrics.

**Research/Explore Phase**:
1. Document all implemented events from previous tasks
2. Review onboarding flow steps
3. Understand billing/checkout flow
4. Identify key conversion points

**Planning Phase**:
1. Define key funnels:
   - Signup → Onboarding → First Spec → Checkout
   - Checkout Started → Checkout Completed
   - Free → Paid Conversion
2. Define key metrics:
   - DAU/WAU/MAU
   - Onboarding completion rate
   - Checkout conversion rate
   - Feature adoption rates
3. Plan dashboard layout

**Implementation Phase**:
1. Create PostHog actions for composite events
2. Build funnels:
   - Onboarding funnel
   - Checkout funnel
   - Activation funnel
3. Create dashboards:
   - Executive Dashboard (key metrics)
   - Onboarding Dashboard (step-by-step)
   - Revenue Dashboard (billing events)
4. Set up cohort definitions
5. Configure event-based alerts

**Documentation Phase**:
1. Create `docs/analytics/posthog-dashboards.md`
2. Document funnel definitions
3. Add metric definitions glossary

**Acceptance Criteria**:
- [ ] Funnels show conversion rates
- [ ] Dashboards display key metrics
- [ ] Cohorts are defined for analysis
- [ ] Alerts configured for critical events

---

### Task 4.2: Sentry Alert Configuration

**Objective**: Set up Sentry alerts for error monitoring.

**Research/Explore Phase**:
1. Review error patterns in codebase
2. Identify critical vs non-critical errors
3. Understand deployment environments
4. Review notification preferences (Slack, email)

**Planning Phase**:
1. Define alert rules:
   - High-frequency errors
   - New errors (first seen)
   - Regression errors (resolved then reoccurred)
   - Performance degradation
2. Define alert thresholds
3. Plan notification routing

**Implementation Phase**:
1. Create Sentry alert rules:
   - "Critical Error Rate" - >5 errors/minute
   - "New Error Type" - first occurrence
   - "Checkout Errors" - tag:checkout
   - "P95 Latency" - >3s for critical endpoints
2. Configure Slack integration
3. Set up issue assignment rules
4. Create release tracking setup

**Documentation Phase**:
1. Document alert rules and thresholds
2. Create incident response playbook
3. Document escalation procedures

**Acceptance Criteria**:
- [ ] Alert rules are configured
- [ ] Notifications work (Slack/email)
- [ ] Critical errors trigger immediate alerts
- [ ] Performance alerts are calibrated

---

### Task 4.3: Environment Variable & Deployment Setup

**Objective**: Ensure proper environment configuration for all tracking services.

**Research/Explore Phase**:
1. Review existing `.env.example` files
2. Check deployment configuration (Railway, Vercel, etc.)
3. Review CI/CD pipeline for build steps
4. Understand secret management approach

**Planning Phase**:
1. Document all required environment variables:
   - PostHog keys (public + server)
   - Sentry DSNs (frontend + backend)
   - Sentry auth tokens (for source maps)
2. Plan environment-specific configurations
3. Define secure secret storage approach

**Implementation Phase**:
1. Update `frontend/.env.example` with all PostHog/Sentry vars
2. Update `backend/.env.example` with all PostHog/Sentry vars
3. Create `docs/deployment/analytics-env-vars.md`
4. Add source map upload to CI/CD
5. Configure environment-specific settings:
   - Development: verbose logging, 100% sampling
   - Staging: full tracking, higher sampling
   - Production: optimized sampling rates

**Documentation Phase**:
1. Create environment variable reference
2. Document deployment checklist
3. Add troubleshooting for common issues

**Acceptance Criteria**:
- [ ] All env vars documented
- [ ] Example files updated
- [ ] CI/CD uploads source maps
- [ ] Environment configs are correct

---

## Task Execution Order

**Recommended execution order for Claude Code web:**

1. **Task 1.1** - PostHog Frontend Setup (foundation)
2. **Task 2.1** - Sentry Frontend Setup (parallel track)
3. **Task 1.2** - Core Analytics Events (depends on 1.1)
4. **Task 2.2** - Sentry Error Context (depends on 2.1)
5. **Task 1.3** - User Identification (depends on 1.2)
6. **Task 2.3** - Performance Monitoring (depends on 2.2)
7. **Task 3.1** - Sentry Backend Setup (new track)
8. **Task 3.2** - Backend Event Tracking (depends on 3.1)
9. **Task 3.3** - Backend Performance Tracing (depends on 3.1)
10. **Task 4.1** - PostHog Dashboards (depends on 1.2, 3.2)
11. **Task 4.2** - Sentry Alerts (depends on 2.2, 3.1)
12. **Task 4.3** - Environment Setup (final, depends on all)

---

## Quick Reference: Key Files

### Frontend
- `frontend/hooks/useOnboarding.ts` - Existing trackEvent placeholder
- `frontend/providers/AuthProvider.tsx` - User auth context
- `frontend/lib/api/client.ts` - API client
- `frontend/app/layout.tsx` - Root layout
- `frontend/next.config.js` - Next.js config

### Backend
- `backend/omoi_os/api/main.py` - FastAPI app
- `backend/omoi_os/logging.py` - Logging setup
- `backend/omoi_os/api/routes/billing.py` - Stripe webhooks
- `backend/omoi_os/observability/__init__.py` - Observability module

### Documentation
- `frontend/docs/` - Frontend documentation
- `backend/docs/` - Backend documentation
- `docs/` - Project-wide documentation
