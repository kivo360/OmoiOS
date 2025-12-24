# Billing User Journeys & Page Flows

**Created**: 2025-12-24
**Status**: Design Ready
**Purpose**: Map all user journeys for the billing UI to guide frontend development

---

## Current State Summary

### What's Built

| Component | Location | Status |
|-----------|----------|--------|
| Billing Page | `/organizations/[id]/billing/page.tsx` | ✅ Functional with Credits, Payment Methods, Invoices, Usage tabs |
| Success Page | `/billing/success/page.tsx` | ✅ Basic success confirmation |
| Cancel Page | `/billing/cancel/page.tsx` | ✅ Basic cancel confirmation |
| Billing Hooks | `hooks/useBilling.ts` | ✅ All account/payment/invoice hooks |
| API Client | `lib/api/billing.ts` | ✅ All billing API functions |
| Types | `lib/api/types.ts` | ✅ BillingAccount, Invoice, Payment, UsageRecord, PaymentMethod |

### What's Missing (Frontend)

| Component | Priority | Notes |
|-----------|----------|-------|
| Subscription hooks | 🔴 High | `useSubscription`, `useCancelSubscription`, `useReactivateSubscription` |
| Subscription types | 🔴 High | `Subscription` type matching backend model |
| Subscription API functions | 🔴 High | `getSubscription`, `cancelSubscription`, `reactivateSubscription` |
| SubscriptionCard component | 🔴 High | Display current tier, usage, upgrade CTA |
| PricingTable component | 🔴 High | Tier comparison for upgrade decisions |
| CostBreakdown charts | 🟡 Medium | Recharts visualization by provider/model |
| Lifetime purchase flow | 🟡 Medium | One-time purchase checkout |
| BYO API Keys UI | 🟢 Lower | Power user feature for adding own LLM keys |

---

## User Personas

### 1. New User (Trial/Free Tier)
- Just signed up, exploring the platform
- Wants to understand pricing before committing
- May convert to paid after hitting free tier limits

### 2. Solo Developer (Starter Tier Target)
- Uses platform for personal projects
- Price-sensitive, wants predictable costs
- Likely to upgrade if they see value

### 3. Small Team Lead (Pro/Team Tier Target)
- Managing 2-10 engineers
- Cares about usage visibility and cost tracking
- May need to justify costs to management

### 4. Power User (BYO API Key Target)
- Has existing LLM API keys (Anthropic, OpenAI)
- Wants unlimited usage at their own cost
- Technical, understands the value exchange

### 5. Enterprise Buyer
- Needs custom pricing, SLA, data isolation
- Requires invoice-based billing
- Longer sales cycle, less self-serve

---

## User Journeys

### Journey 1: Free User Hits Limits → Upgrade

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. User runs 5th free workflow                                            │
│     ↓                                                                       │
│  2. "Free tier exhausted" message appears in workflow UI                   │
│     ↓                                                                       │
│  3. User clicks "Upgrade" link → redirects to Billing page                 │
│     ↓                                                                       │
│  4. Billing page shows:                                                     │
│     - Current tier: FREE (0/5 workflows remaining)                         │
│     - "Upgrade to continue" prominent CTA                                   │
│     - Pricing table with tier comparison                                   │
│     ↓                                                                       │
│  5. User selects tier → clicks "Subscribe"                                 │
│     ↓                                                                       │
│  6. Stripe Checkout opens → user enters payment                            │
│     ↓                                                                       │
│  7. Redirect to /billing/success with subscription confirmation            │
│     ↓                                                                       │
│  8. User returns to workflow with new limits applied                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Pages:**
- Workflow page (shows limit warning)
- `/organizations/[id]/billing` (main billing page with upgrade flow)
- Stripe Checkout (external)
- `/billing/success` (confirmation)

**Missing Components:**
- [ ] `SubscriptionCard` showing current tier prominently
- [ ] `PricingTable` with tier comparison
- [ ] Subscription upgrade checkout endpoint (Stripe subscription)
- [ ] Warning banner in workflow UI when limits are low

---

### Journey 2: Existing User Manages Subscription

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. User navigates: Organization → Billing                                 │
│     ↓                                                                       │
│  2. Billing Overview shows:                                                 │
│     ┌──────────────────────────────────────────┐                           │
│     │ PRO PLAN - $79/month                      │                           │
│     │ ─────────────────────────────────────────│                           │
│     │ Workflows: ████████░░ 80/100 used        │                           │
│     │ Agents: ████░░░░░░ 2/5 active            │                           │
│     │ Storage: ██░░░░░░░░ 12GB/50GB            │                           │
│     │                                           │                           │
│     │ Renews: Jan 24, 2026                     │                           │
│     │ [Change Plan] [Cancel]                   │                           │
│     └──────────────────────────────────────────┘                           │
│     ↓                                                                       │
│  3. User clicks "Change Plan"                                              │
│     ↓                                                                       │
│  4. Modal shows PricingTable with current plan highlighted                 │
│     - Upgrade options (Team, Enterprise)                                   │
│     - Downgrade options (Starter, Free) with warnings                      │
│     ↓                                                                       │
│  5a. UPGRADE: Immediate → Stripe handles proration                         │
│  5b. DOWNGRADE: "Takes effect at period end" warning                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Components:**
- [ ] `SubscriptionCard` with usage meters
- [ ] `UpgradeDialog` with PricingTable
- [ ] Proration messaging for mid-cycle changes
- [ ] Downgrade warning (usage exceeds new limits)

---

### Journey 3: User Buys Credits (Pay-As-You-Go)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. User is on FREE tier, doesn't want subscription                        │
│     ↓                                                                       │
│  2. Navigates to Billing → Credits tab                                     │
│     ↓                                                                       │
│  3. Credit Balance card shows: $0.00                                       │
│     ↓                                                                       │
│  4. "Buy Credits" section with:                                            │
│     - Quick amounts: $25, $50, $100, $250, $500                            │
│     - Custom amount input                                                   │
│     - "Each workflow costs ~$10" explanation                               │
│     ↓                                                                       │
│  5. User selects $100 → clicks "Buy Credits"                               │
│     ↓                                                                       │
│  6. Stripe Checkout → payment                                              │
│     ↓                                                                       │
│  7. Redirect to /billing/success                                           │
│     ↓                                                                       │
│  8. Credit balance now shows $100.00                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Status:** ✅ Already implemented in current billing page

**Improvements:**
- [ ] More prominent credit balance in header stats
- [ ] Low credit warning when balance < 1 workflow cost
- [ ] Auto-billing toggle (when balance hits $0, auto-charge)

---

### Journey 4: User Purchases Lifetime Access

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. User sees "Founding Member" banner on Pricing page                     │
│     ↓                                                                       │
│  2. Banner explains:                                                        │
│     "Pay once ($499), use forever. 50 workflows/month, 5 agents"           │
│     ↓                                                                       │
│  3. User clicks "Claim Lifetime Access"                                    │
│     ↓                                                                       │
│  4. Confirmation modal:                                                     │
│     - One-time payment: $499                                               │
│     - Includes: 50 workflows/month, 5 agents, 100GB storage                │
│     - "No recurring charges ever"                                          │
│     ↓                                                                       │
│  5. Stripe Checkout → payment                                              │
│     ↓                                                                       │
│  6. /billing/success shows "Welcome, Founding Member!"                     │
│     ↓                                                                       │
│  7. Billing page shows LIFETIME badge, no renewal date                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Missing Components:**
- [ ] `LifetimePurchaseCard` with founding member messaging
- [ ] Lifetime checkout endpoint (backend exists)
- [ ] Lifetime-specific success page variant
- [ ] Lifetime badge in SubscriptionCard

---

### Journey 5: Power User Sets Up BYO API Keys

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. User on any tier wants unlimited workflows at own LLM cost             │
│     ↓                                                                       │
│  2. Navigates: Settings → API Keys (or Billing → BYO Setup)               │
│     ↓                                                                       │
│  3. "Bring Your Own API Keys" section:                                     │
│     ┌──────────────────────────────────────────┐                           │
│     │ 🔑 Anthropic API Key                      │                           │
│     │ [●●●●●●●●●●●●●●sk-ant-..abc] [Edit]       │                           │
│     │                                           │                           │
│     │ 🔑 OpenAI API Key                         │                           │
│     │ [Not configured] [Add Key]                │                           │
│     │                                           │                           │
│     │ 🔑 Z.AI (Anthropic Proxy)                 │                           │
│     │ [Not configured] [Add Key]                │                           │
│     └──────────────────────────────────────────┘                           │
│     ↓                                                                       │
│  4. User clicks "Add Key" → modal with:                                    │
│     - API key input (masked)                                               │
│     - "Test Connection" button                                             │
│     - Base URL override (for Z.AI)                                         │
│     ↓                                                                       │
│  5. After adding key, user can:                                            │
│     - Subscribe to $19/month BYO plan (platform access only)               │
│     - OR use keys with existing subscription                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Missing Components:**
- [ ] `APIKeyManager` component
- [ ] `AddAPIKeyDialog` with connection test
- [ ] Integration with existing user_credentials table
- [ ] BYO subscription checkout

**Backend Ready:** ✅ user_credentials table and CredentialsService exist

---

### Journey 6: User Reviews Usage & Costs

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. User wants to understand where costs come from                         │
│     ↓                                                                       │
│  2. Navigates to Billing → Usage/Costs tab                                 │
│     ↓                                                                       │
│  3. Cost Breakdown shows:                                                   │
│     ┌──────────────────────────────────────────┐                           │
│     │ Total This Period: $127.50               │                           │
│     │ ─────────────────────────────────────────│                           │
│     │ By Provider:                              │                           │
│     │   Anthropic  ████████░░ $98.00 (77%)     │                           │
│     │   OpenAI     ██░░░░░░░░ $29.50 (23%)     │                           │
│     │                                           │                           │
│     │ By Model:                                 │                           │
│     │   Claude Sonnet  ██████░░ $75.00         │                           │
│     │   Claude Opus    ██░░░░░░ $23.00         │                           │
│     │   GPT-4          ██░░░░░░ $29.50         │                           │
│     └──────────────────────────────────────────┘                           │
│     ↓                                                                       │
│  4. Time series chart shows daily spend                                    │
│     ↓                                                                       │
│  5. Drill down into individual workflows:                                  │
│     - Workflow ID, Date, Tokens, Cost                                      │
│     - Link to workflow details                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Missing Components:**
- [ ] `CostBreakdown` with pie/bar charts (recharts)
- [ ] `CostTimeline` with daily spend line chart
- [ ] Cost summary API hook (`useCosts`, `useCostSummary`)
- [ ] Drill-down to workflow-level costs

**Backend Ready:** ✅ cost_tracking service and endpoints exist

---

### Journey 7: User Manages Payment Methods

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. User needs to update credit card before expiration                     │
│     ↓                                                                       │
│  2. Navigates to Billing → Payment Methods tab                             │
│     ↓                                                                       │
│  3. Current cards shown:                                                    │
│     ┌──────────────────────────────────────────┐                           │
│     │ 💳 Visa ending in 4242        [Default]  │                           │
│     │    Expires 12/2026                        │                           │
│     │                              [Remove]     │                           │
│     │                                           │                           │
│     │ [+ Add Payment Method]                    │                           │
│     └──────────────────────────────────────────┘                           │
│     ↓                                                                       │
│  4. User clicks "Add Payment Method"                                       │
│     ↓                                                                       │
│  5. Current: Opens Stripe Customer Portal (external)                       │
│     Better: Inline Stripe Elements form                                    │
│     ↓                                                                       │
│  6. After adding, user sets new card as default                            │
│     ↓                                                                       │
│  7. User removes old card                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Current Status:** ✅ Basic implementation exists
**Improvements:**
- [ ] Inline Stripe Elements form (vs portal redirect)
- [ ] Card expiration warnings
- [ ] Failed payment retry UI

---

### Journey 8: User Views and Pays Invoices

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. User receives "Invoice Ready" email                                    │
│     ↓                                                                       │
│  2. Clicks link → Billing → Invoices tab                                  │
│     ↓                                                                       │
│  3. Invoice list shows:                                                     │
│     ┌──────────────────────────────────────────┐                           │
│     │ Invoice #    Date       Amount   Status  │                           │
│     │ ─────────────────────────────────────────│                           │
│     │ INV-2024-001 Dec 24     $79.00   ⚠ Open  │                           │
│     │ INV-2024-000 Nov 24     $79.00   ✓ Paid  │                           │
│     └──────────────────────────────────────────┘                           │
│     ↓                                                                       │
│  4. User clicks open invoice → Invoice Details page                        │
│     ↓                                                                       │
│  5. Details show:                                                           │
│     - Line items (subscription, overages)                                  │
│     - Subtotal, tax, credits applied, total                               │
│     - [Pay Now] [Download PDF]                                             │
│     ↓                                                                       │
│  6. User clicks "Pay Now" → payment processed                              │
│     ↓                                                                       │
│  7. Status updates to "Paid"                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Current Status:** ✅ Basic implementation exists
**Improvements:**
- [ ] Invoice detail page (`/organizations/[id]/billing/invoices/[invoiceId]`)
- [ ] PDF download button
- [ ] Line items breakdown
- [ ] Past due warning styling

---

## Page Flow Diagram

```
                                    ┌─────────────────────┐
                                    │   Organization      │
                                    │   Overview Page     │
                                    └─────────┬───────────┘
                                              │
                                    ┌─────────▼───────────┐
                                    │   Billing Button    │
                                    └─────────┬───────────┘
                                              │
              ┌───────────────────────────────┼───────────────────────────────┐
              │                               │                               │
    ┌─────────▼─────────┐         ┌──────────▼──────────┐         ┌──────────▼──────────┐
    │  Billing Overview │         │ Upgrade/Pricing     │         │ Stripe Portal       │
    │  /billing         │─────────│ Modal               │─────────│ (External)          │
    │                   │         │                     │         │                     │
    │  - Stats Cards    │         │  - PricingTable     │         │ - Manage cards      │
    │  - Subscription   │         │  - Tier comparison  │         │ - View invoices     │
    │  - Credits        │         │  - Feature list     │         │ - Cancel sub        │
    │  - Usage          │         │                     │         │                     │
    └───────┬───────────┘         └──────────┬──────────┘         └─────────────────────┘
            │                                │
            │ Tab Navigation                 │ Checkout
            ▼                                ▼
    ┌───────────────────┐         ┌──────────────────────┐
    │  Tabs:            │         │  Stripe Checkout     │
    │                   │         │  (External)          │
    │  [Overview]       │         └──────────┬───────────┘
    │  [Credits]        │                    │
    │  [Payment]        │                    ▼
    │  [Invoices]       │         ┌──────────────────────┐
    │  [Usage]          │         │  /billing/success    │
    │  [Costs] *new     │         │  or                  │
    │                   │         │  /billing/cancel     │
    └───────────────────┘         └──────────────────────┘
```

---

## Component Hierarchy

```
BillingPage
├── PageHeader
│   ├── BackLink (to Organization)
│   ├── Title & Description
│   └── BillingPortalButton
│
├── StatsGrid (4 cards)
│   ├── CreditBalanceCard    ← exists
│   ├── FreeWorkflowsCard    ← exists
│   ├── WorkflowsCompletedCard ← exists
│   └── TotalSpentCard       ← exists
│
├── SubscriptionCard         ← NEW (high priority)
│   ├── TierBadge
│   ├── UsageMeters (workflows, agents, storage)
│   ├── RenewalDate
│   └── ActionButtons (Change Plan, Cancel)
│
├── Tabs
│   ├── CreditsTab           ← exists
│   │   ├── BuyCreditsForm
│   │   └── QuickAmountButtons
│   │
│   ├── PaymentMethodsTab    ← exists
│   │   ├── PaymentMethodList
│   │   ├── AddPaymentMethodButton
│   │   └── RemovePaymentMethodButton
│   │
│   ├── InvoicesTab          ← exists
│   │   └── InvoiceTable
│   │
│   ├── UsageTab             ← exists
│   │   └── UsageTable
│   │
│   └── CostsTab             ← NEW (medium priority)
│       ├── CostSummary
│       ├── CostByProviderChart
│       ├── CostByModelChart
│       └── CostTimelineChart
│
└── UpgradeDialog            ← NEW (high priority)
    ├── PricingTable
    │   ├── TierCard (Free)
    │   ├── TierCard (Starter)
    │   ├── TierCard (Pro) - highlighted
    │   ├── TierCard (Team)
    │   └── TierCard (Enterprise) - contact sales
    └── ConfirmButton
```

---

## Implementation Priority

### Phase 1: Core Subscription UI (High Priority)

1. **Add Subscription Types & API** (1-2 hours)
   - Add `Subscription` type to `lib/api/types.ts`
   - Add subscription API functions to `lib/api/billing.ts`
   - Add subscription hooks to `hooks/useBilling.ts`

2. **SubscriptionCard Component** (2-3 hours)
   - Display current tier with badge
   - Usage meters (workflows, agents, storage)
   - Renewal date or lifetime badge
   - Change Plan / Cancel buttons

3. **PricingTable Component** (2-3 hours)
   - Tier comparison grid
   - Feature list per tier
   - Current plan highlighted
   - Upgrade/downgrade CTAs

4. **UpgradeDialog** (1-2 hours)
   - Modal with PricingTable
   - Checkout redirect

### Phase 2: Cost Visualization (Medium Priority)

5. **Add Cost API & Hooks** (1 hour)
   - Add `useCostSummary` hook
   - Add cost API functions

6. **CostBreakdown Component** (2-3 hours)
   - Pie chart by provider
   - Bar chart by model
   - Using recharts

7. **CostTimeline Component** (1-2 hours)
   - Line chart of daily spend
   - Date range filter

### Phase 3: Polish & Power Features (Lower Priority)

8. **Lifetime Purchase Flow** (1-2 hours)
   - LifetimePurchaseCard
   - Founding member messaging

9. **BYO API Keys UI** (3-4 hours)
   - APIKeyManager component
   - AddAPIKeyDialog with test
   - Integration with credentials service

10. **Invoice Details Page** (2 hours)
    - Full invoice view with line items
    - PDF download

---

## Success Metrics

- [ ] User can see current subscription tier and usage at a glance
- [ ] User can upgrade/downgrade subscription without leaving the app
- [ ] User can understand their costs by provider/model
- [ ] User can purchase lifetime access in one click
- [ ] User can add their own API keys for BYO mode
- [ ] All flows have clear success/error feedback

---

## Design References

- **Design System**: `docs/design_system.md`
- **Frontend Architecture**: `docs/design/frontend/frontend_architecture_shadcn_nextjs.md`
- **Pricing Strategy**: `docs/design/billing/pricing_strategy.md`
- **Frontend Implementation Guide**: `docs/guides/BILLING_FRONTEND_DEVELOPMENT_GUIDE.md`

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-12-24 | Initial creation with complete user journeys | Claude |
