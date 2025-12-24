# Billing Frontend Development Guide

**Created**: 2025-12-24
**Status**: Development Ready
**Purpose**: Comprehensive guide for implementing the billing UI in the OmoiOS frontend

---

## Overview

This document serves as the starting point for frontend billing feature development. It consolidates all the backend API endpoints, data models, and references to existing documentation needed to implement the billing UI.

### Related Documents (Must Read)

| Document | Purpose | Location |
|----------|---------|----------|
| **Pricing Strategy** | Tier definitions, pricing, limits | `docs/design/billing/pricing_strategy.md` |
| **Frontend Implementation Guide** | General frontend patterns | `docs/frontend_implementation_guide.md` |
| **Design System** | Colors, typography, components | `docs/design_system.md` |
| **Frontend Architecture** | Next.js + ShadCN patterns | `docs/design/frontend/frontend_architecture_shadcn_nextjs.md` |
| **React Query + WebSocket** | Data fetching patterns | `docs/design/frontend/react_query_websocket.md` |

---

## Backend API Endpoints Summary

Base URL: `/api/billing`

### Stripe Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/config` | GET | Get Stripe publishable key for frontend |

**Response**: `StripeConfigResponse`
```typescript
interface StripeConfigResponse {
  publishable_key: string | null;
  is_configured: boolean;
}
```

---

### Billing Account

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/account/{organization_id}` | GET | Get or create billing account |

**Response**: `BillingAccountResponse`
```typescript
interface BillingAccountResponse {
  id: string;
  organization_id: string;
  stripe_customer_id: string | null;
  has_payment_method: boolean;
  status: string; // 'pending' | 'active' | 'suspended'
  free_workflows_remaining: number;
  free_workflows_reset_at: string | null; // ISO datetime
  credit_balance: number;
  auto_billing_enabled: boolean;
  billing_email: string | null;
  tax_exempt: boolean;
  total_workflows_completed: number;
  total_amount_spent: number;
  created_at: string | null;
  updated_at: string | null;
}
```

---

### Payment Methods

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/account/{organization_id}/payment-method` | POST | Attach payment method |
| `/account/{organization_id}/payment-methods` | GET | List all payment methods |
| `/account/{organization_id}/payment-methods/{payment_method_id}` | DELETE | Remove payment method |

**Request** (POST):
```typescript
interface PaymentMethodRequest {
  payment_method_id: string; // From Stripe.js
  set_as_default: boolean;
}
```

**Response**: `PaymentMethodResponse`
```typescript
interface PaymentMethodResponse {
  id: string;
  type: string;
  card_brand: string | null;
  card_last4: string | null;
  is_default: boolean;
}
```

---

### Subscription Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/account/{organization_id}/subscription` | GET | Get active subscription |
| `/account/{organization_id}/subscription/cancel` | POST | Cancel subscription |
| `/account/{organization_id}/subscription/reactivate` | POST | Reactivate canceled subscription |

**Response**: `SubscriptionResponse`
```typescript
interface SubscriptionResponse {
  id: string;
  organization_id: string;
  billing_account_id: string;
  tier: 'free' | 'starter' | 'pro' | 'team' | 'enterprise' | 'lifetime' | 'byo';
  status: 'active' | 'trialing' | 'past_due' | 'canceled' | 'paused' | 'incomplete';
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  canceled_at: string | null;
  trial_start: string | null;
  trial_end: string | null;
  workflows_limit: number;
  workflows_used: number;
  workflows_remaining: number;
  agents_limit: number;
  storage_limit_gb: number;
  storage_used_gb: number;
  is_lifetime: boolean;
  lifetime_purchase_date: string | null;
  lifetime_purchase_amount: number | null;
  is_byo: boolean;
  byo_providers_configured: string[] | null;
  created_at: string | null;
  updated_at: string | null;
}
```

---

### Checkout & Purchases

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/account/{organization_id}/credits/checkout` | POST | Create credit purchase checkout |
| `/account/{organization_id}/lifetime/checkout` | POST | Create lifetime purchase checkout |
| `/account/{organization_id}/portal` | POST | Create Stripe customer portal session |

**Credit Purchase Request**:
```typescript
interface CreditPurchaseRequest {
  amount_usd: number; // 0 < amount <= 1000
  success_url?: string;
  cancel_url?: string;
}
```

**Lifetime Purchase Request**:
```typescript
interface LifetimePurchaseRequest {
  success_url?: string;
  cancel_url?: string;
}
```

**Checkout Response**:
```typescript
interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}
```

**Portal Response**:
```typescript
interface PortalResponse {
  portal_url: string;
}
```

---

### Invoices

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/account/{organization_id}/invoices` | GET | List invoices (filter by status) |
| `/invoices/{invoice_id}` | GET | Get specific invoice |
| `/invoices/{invoice_id}/pay` | POST | Pay an invoice |
| `/account/{organization_id}/invoices/generate` | POST | Generate invoice for unbilled usage |

**Invoice Response**:
```typescript
interface InvoiceResponse {
  id: string;
  invoice_number: string;
  billing_account_id: string;
  ticket_id: string | null;
  stripe_invoice_id: string | null;
  status: 'draft' | 'open' | 'paid' | 'past_due' | 'void';
  period_start: string | null;
  period_end: string | null;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total: number;
  credits_applied: number;
  amount_due: number;
  amount_paid: number;
  currency: string;
  line_items: LineItem[];
  description: string | null;
  due_date: string | null;
  finalized_at: string | null;
  paid_at: string | null;
  created_at: string | null;
}
```

---

### Usage & Costs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/account/{organization_id}/usage` | GET | Get usage records (filter by billed) |
| `/account/{organization_id}/costs/summary` | GET | Get aggregated cost summary |
| `/account/{organization_id}/costs` | GET | Get detailed cost records |

**Usage Record Response**:
```typescript
interface UsageRecordResponse {
  id: string;
  billing_account_id: string;
  ticket_id: string | null;
  usage_type: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  free_tier_used: boolean;
  invoice_id: string | null;
  billed: boolean;
  usage_details: Record<string, any> | null;
  recorded_at: string | null;
  billed_at: string | null;
}
```

**Cost Summary Response**:
```typescript
interface CostSummaryResponse {
  scope_type: string;
  scope_id: string | null;
  total_cost: number;
  total_tokens: number;
  record_count: number;
  breakdown: CostBreakdownItem[];
}

interface CostBreakdownItem {
  provider: string;
  model: string;
  cost: number;
  tokens: number;
  records: number;
}
```

**Cost Record Response**:
```typescript
interface CostRecordResponse {
  id: string;
  task_id: string;
  agent_id: string | null;
  sandbox_id: string | null;
  billing_account_id: string | null;
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  prompt_cost: number;
  completion_cost: number;
  total_cost: number;
  recorded_at: string | null;
}
```

---

## Subscription Tiers

From `pricing_strategy.md`:

| Tier | Price/Month | Workflows | Agents | Storage |
|------|-------------|-----------|--------|---------|
| **Free** | $0 | 5 | 1 | 2GB |
| **Starter** | $29 | 20 | 2 | 10GB |
| **Pro** | $79 | 100 | 5 | 50GB |
| **Team** | $199 | 500 | 15 | 200GB |
| **Enterprise** | Custom | Unlimited | Unlimited | Unlimited |
| **Lifetime** | $499 one-time | 50/month | 5 | 100GB |
| **BYO** | $19 | Unlimited* | Unlimited* | 50GB |

*BYO = Bring Your Own API Keys (user pays LLM providers directly)

---

## Frontend Component Structure

Suggested file organization for billing UI:

```
frontend/
├── app/
│   ├── (dashboard)/
│   │   └── settings/
│   │       └── billing/
│   │           ├── page.tsx              # Main billing page
│   │           └── loading.tsx           # Loading state
│   └── billing/
│       ├── success/
│       │   └── page.tsx                  # Post-checkout success
│       └── cancel/
│           └── page.tsx                  # Checkout canceled
│
├── components/
│   └── billing/
│       ├── BillingOverview.tsx           # Main billing dashboard
│       ├── SubscriptionCard.tsx          # Current subscription info
│       ├── UsageCard.tsx                 # Usage meter/progress
│       ├── PricingTable.tsx              # Tier comparison table
│       ├── PaymentMethodList.tsx         # Payment methods manager
│       ├── AddPaymentMethodForm.tsx      # Stripe Elements form
│       ├── InvoiceList.tsx               # Invoice history
│       ├── InvoiceDetails.tsx            # Single invoice view
│       ├── CostBreakdown.tsx             # Cost by provider/model
│       ├── CreditBalance.tsx             # Credit balance display
│       ├── BuyCreditsDialog.tsx          # Credit purchase modal
│       ├── LifetimePurchaseCard.tsx      # Lifetime offer CTA
│       └── UpgradeDialog.tsx             # Tier upgrade modal
│
├── hooks/
│   └── billing/
│       ├── useBillingAccount.ts          # Billing account query
│       ├── useSubscription.ts            # Subscription query
│       ├── usePaymentMethods.ts          # Payment methods query
│       ├── useInvoices.ts                # Invoices query
│       ├── useUsage.ts                   # Usage records query
│       ├── useCosts.ts                   # Cost tracking query
│       └── useStripeConfig.ts            # Stripe config query
│
├── lib/
│   └── billing/
│       ├── api.ts                        # API client functions
│       ├── stripe.ts                     # Stripe.js initialization
│       └── types.ts                      # TypeScript types
│
└── stores/
    └── billing.ts                        # Zustand store (if needed)
```

---

## React Query Hooks Pattern

Based on `react_query_websocket.md`:

```typescript
// hooks/billing/useBillingAccount.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { billingApi } from '@/lib/billing/api';

export function useBillingAccount(organizationId: string) {
  return useQuery({
    queryKey: ['billing', 'account', organizationId],
    queryFn: () => billingApi.getBillingAccount(organizationId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useSubscription(organizationId: string) {
  return useQuery({
    queryKey: ['billing', 'subscription', organizationId],
    queryFn: () => billingApi.getSubscription(organizationId),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePaymentMethods(organizationId: string) {
  return useQuery({
    queryKey: ['billing', 'paymentMethods', organizationId],
    queryFn: () => billingApi.listPaymentMethods(organizationId),
  });
}

export function useAttachPaymentMethod(organizationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (paymentMethodId: string) =>
      billingApi.attachPaymentMethod(organizationId, paymentMethodId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['billing', 'paymentMethods', organizationId]
      });
      queryClient.invalidateQueries({
        queryKey: ['billing', 'account', organizationId]
      });
    },
  });
}

export function useCosts(organizationId: string) {
  return useQuery({
    queryKey: ['billing', 'costs', organizationId],
    queryFn: () => billingApi.getCostSummary(organizationId),
    staleTime: 1 * 60 * 1000, // 1 minute (costs update frequently)
  });
}
```

---

## Stripe.js Integration

### Setup

1. Install Stripe.js:
```bash
pnpm add @stripe/stripe-js @stripe/react-stripe-js
```

2. Initialize in `lib/billing/stripe.ts`:
```typescript
import { loadStripe, Stripe } from '@stripe/stripe-js';

let stripePromise: Promise<Stripe | null>;

export const getStripe = async () => {
  if (!stripePromise) {
    const config = await fetch('/api/billing/config').then(r => r.json());
    if (config.publishable_key) {
      stripePromise = loadStripe(config.publishable_key);
    }
  }
  return stripePromise;
};
```

3. Wrap components with `Elements` provider:
```tsx
import { Elements } from '@stripe/react-stripe-js';
import { getStripe } from '@/lib/billing/stripe';

export function PaymentMethodForm() {
  const [stripe, setStripe] = useState<Stripe | null>(null);

  useEffect(() => {
    getStripe().then(setStripe);
  }, []);

  if (!stripe) return <Skeleton />;

  return (
    <Elements stripe={stripe}>
      <AddPaymentMethodForm />
    </Elements>
  );
}
```

---

## Key UI Components to Build

### 1. Billing Overview Page

Main dashboard showing:
- Current subscription tier and status
- Usage meters (workflows, storage)
- Credit balance
- Recent invoices
- Payment methods
- Cost breakdown chart

### 2. Subscription Card

Shows:
- Current tier name and price
- Period dates (current_period_start/end)
- Usage: workflows_used / workflows_limit
- Upgrade/downgrade buttons
- Cancel/reactivate button

### 3. Usage Progress Bar

Visual representation of:
- Workflows: used / limit
- Storage: used_gb / limit_gb
- Agents: active / limit

### 4. Payment Method Manager

Features:
- List all cards with brand/last4
- Add new card (Stripe CardElement)
- Set default payment method
- Remove payment method

### 5. Invoice History

Table with:
- Invoice number
- Date
- Amount
- Status badge (paid, open, past_due)
- View/download PDF
- Pay button (for open invoices)

### 6. Cost Breakdown

Chart showing:
- Costs by provider (Anthropic, OpenAI, etc.)
- Costs by model (Claude, GPT-4, etc.)
- Timeline view (last 7/30 days)

---

## Implementation Checklist

### Phase 1: Core Billing UI

- [ ] Create `/app/(dashboard)/settings/billing/page.tsx`
- [ ] Implement `useBillingAccount` hook
- [ ] Implement `useSubscription` hook
- [ ] Create `BillingOverview` component
- [ ] Create `SubscriptionCard` component
- [ ] Create `UsageCard` with progress bars

### Phase 2: Payment Methods

- [ ] Setup Stripe.js in `lib/billing/stripe.ts`
- [ ] Create `PaymentMethodList` component
- [ ] Create `AddPaymentMethodForm` with Stripe Elements
- [ ] Implement attach/remove payment method mutations
- [ ] Add Stripe customer portal link

### Phase 3: Invoices & Usage

- [ ] Create `InvoiceList` component with status badges
- [ ] Create `InvoiceDetails` modal/page
- [ ] Implement invoice payment flow
- [ ] Create `UsageRecordList` component
- [ ] Add usage filtering (billed/unbilled)

### Phase 4: Cost Tracking

- [ ] Create `CostBreakdown` component
- [ ] Add chart visualization (recharts or similar)
- [ ] Implement cost filtering by date range
- [ ] Add cost export functionality

### Phase 5: Checkout Flows

- [ ] Create `/billing/success/page.tsx`
- [ ] Create `/billing/cancel/page.tsx`
- [ ] Implement credit purchase flow
- [ ] Implement lifetime purchase flow
- [ ] Add upgrade tier modal

### Phase 6: Polish

- [ ] Add loading states (skeletons)
- [ ] Add error boundaries
- [ ] Add toast notifications
- [ ] Responsive design
- [ ] Dark mode support

---

## Testing Checklist

### API Integration

- [ ] Billing account created on first visit
- [ ] Subscription data loads correctly
- [ ] Payment methods list/add/remove work
- [ ] Invoices load and filter correctly
- [ ] Cost data loads and displays

### Stripe Integration

- [ ] Stripe.js loads with correct publishable key
- [ ] Card form validates input
- [ ] Payment method attaches successfully
- [ ] Checkout redirects work
- [ ] Customer portal opens

### UI/UX

- [ ] Loading states display properly
- [ ] Error messages are user-friendly
- [ ] Tier comparison is clear
- [ ] Usage warnings appear at limits
- [ ] Mobile responsive

---

## Environment Variables

Required in frontend `.env`:

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Stripe (loaded from backend /api/billing/config)
# No frontend env var needed - fetched dynamically
```

Required in backend `.env`:

```bash
# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_FRONTEND_URL=http://localhost:3000
```

---

## Code References

### Backend Files

| File | Purpose |
|------|---------|
| `omoi_os/api/routes/billing.py` | All billing API endpoints |
| `omoi_os/models/billing.py` | BillingAccount, Invoice, Payment, UsageRecord models |
| `omoi_os/models/subscription.py` | Subscription model with tiers |
| `omoi_os/services/billing_service.py` | Billing business logic |
| `omoi_os/services/subscription_service.py` | Subscription management |
| `omoi_os/services/stripe_service.py` | Stripe API wrapper |
| `omoi_os/services/cost_tracking.py` | Cost tracking and aggregation |

### Migrations

| Migration | Tables Created |
|-----------|----------------|
| `038_billing_system.py` | billing_accounts, invoices, payments, usage_records |
| `040_subscriptions_table.py` | subscriptions |
| `041_cost_record_billing_integration.py` | Adds sandbox_id, billing_account_id to cost_records |

---

## Quick Start Commands

```bash
# Navigate to frontend
cd /Users/kevinhill/Coding/Experiments/senior-sandbox/senior_sandbox/frontend

# Install Stripe packages
pnpm add @stripe/stripe-js @stripe/react-stripe-js

# Create billing components directory
mkdir -p components/billing hooks/billing lib/billing

# Start dev server
pnpm dev
```

---

## Notes for Development

1. **Organization Context**: All billing operations require an `organization_id`. Get this from your auth/user context.

2. **Error Handling**: The backend returns 4xx errors with `detail` messages. Display these to users.

3. **Real-time Updates**: Consider WebSocket integration for usage/cost updates during active workflows.

4. **Caching Strategy**: Billing data changes infrequently - use 5-minute staleTime. Costs change more often - use 1-minute.

5. **Stripe Webhooks**: Backend handles all Stripe events. Frontend just needs to poll or use WebSocket for status updates.

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-12-24 | Initial creation with full API reference | Claude |
