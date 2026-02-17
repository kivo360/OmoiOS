# Billing & Subscriptions

**Part of**: [Page Flow Documentation](./README.md)

---

## Overview

The Billing system integrates with Stripe to handle subscriptions, credit purchases, payment methods, invoices, and usage tracking. Billing is scoped per organization and supports multiple tiers (Free, Pro, Team, BYO Keys, Lifetime, Enterprise).

---

## Flow 54: Organization Billing Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /organizations/:id/billing                           │
│                                                             │
│  ← Back to {org.name}                                       │
│                                                             │
│  Billing                              [Billing Portal]      │
│  Manage billing, credits, and payment methods for Acme Inc  │
│                                                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │  $247.80  │ │  ∞        │ │  34       │ │  $892.40  │  │
│  │  Credit   │ │  Workflows│ │  Workflows│ │  Total    │  │
│  │  Balance  │ │  Left     │ │  Used     │ │  Spent    │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Account Status                          [active]      │ │
│  │  Billing Email: team@acme.com                          │ │
│  │  Free Tier Reset: 2026-03-01                           │ │
│  │  Auto-Billing: Enabled                                 │ │
│  │  Tax Exempt: No                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Tabs: [Subscription] [Credits] [Payment Methods]           │
│        [Invoices] [Usage]                                   │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Subscription Tab (default)                            │ │
│  │                                                        │ │
│  │  SubscriptionCard component showing:                   │ │
│  │  - Current tier (Pro/Team/Free/Lifetime)               │ │
│  │  - Billing period and renewal date                     │ │
│  │  - Workflow limits and usage                           │ │
│  │  - [Upgrade] [Manage] [Cancel] buttons                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/organizations/[id]/billing`

### Purpose
Full billing management for an organization: subscriptions, credits, payment methods, invoices, and usage.

### Tabs

| Tab | Content |
|-----|---------|
| Subscription | Current tier, upgrade/cancel/reactivate, SubscriptionCard |
| Credits | Buy prepaid credits ($10-$1000), quick-select buttons ($25/$50/$100/$250/$500) |
| Payment Methods | View saved cards, add via Stripe portal, remove payment methods |
| Invoices | Billing history table (invoice #, date, amount, status, view/PDF links) |
| Usage | Unbilled usage records table (date, type, quantity, price, free tier flag) |

### User Actions
- **View subscription**: See current tier, usage, and billing period
- **Upgrade plan**: Opens UpgradeDialog with tier options (Pro $50/mo, Team $150/mo, BYO $19/mo, Lifetime, Enterprise)
- **Cancel subscription**: Cancel at period end with confirmation
- **Reactivate**: Reactivate a canceled subscription before period ends
- **Buy credits**: Enter amount or use quick-select, redirects to Stripe Checkout
- **Open billing portal**: External Stripe Customer Portal for advanced management
- **Manage payment methods**: View, add (via portal), remove saved cards
- **View invoices**: See billing history with links to Stripe-hosted invoices/PDFs
- **View usage**: See unbilled usage with free tier indicators

### Components
- `BillingPage` — Main billing page
- `SubscriptionCard` — Displays current subscription with actions
- `UpgradeDialog` — Modal for tier selection with pricing info

### API Endpoints
- `GET /api/v1/billing/:orgId/account` — Billing account info (via `useBillingAccount`)
- `GET /api/v1/billing/:orgId/subscription` — Current subscription (via `useSubscription`)
- `GET /api/v1/billing/:orgId/payment-methods` — Saved payment methods (via `usePaymentMethods`)
- `GET /api/v1/billing/:orgId/invoices` — Stripe invoices (via `useStripeInvoices`)
- `GET /api/v1/billing/:orgId/usage` — Usage records (via `useUsage`)
- `GET /api/v1/billing/config` — Stripe configuration status (via `useStripeConfig`)
- `POST /api/v1/billing/:orgId/checkout/credits` — Create credit checkout session
- `POST /api/v1/billing/:orgId/checkout/subscription` — Create subscription checkout session
- `POST /api/v1/billing/:orgId/checkout/lifetime` — Create lifetime checkout session
- `POST /api/v1/billing/:orgId/portal` — Create Stripe Customer Portal session
- `DELETE /api/v1/billing/:orgId/payment-methods/:pmId` — Remove payment method
- `POST /api/v1/billing/:orgId/subscription/cancel` — Cancel subscription
- `POST /api/v1/billing/:orgId/subscription/reactivate` — Reactivate subscription

### State Management
- `useBillingAccount` (React Query) — Account balance and status
- `useSubscription` (React Query) — Current subscription tier and limits
- `usePaymentMethods` (React Query) — Saved payment methods list
- `useStripeInvoices` (React Query) — Invoice history
- `useUsage` (React Query) — Unbilled usage records
- `useStripeConfig` (React Query) — Stripe configuration status
- Multiple mutations for checkout, portal, cancel, reactivate

---

## Flow 55: Billing Success

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /billing/success                                     │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                      ✅                                │ │
│  │           Payment Successful!                          │ │
│  │                                                        │ │
│  │  Your credits have been added to your account.         │ │
│  │                                                        │ │
│  │  Thank you for your purchase. Your credits are now     │ │
│  │  available for use.                                    │ │
│  │                                                        │ │
│  │           [Back to Organizations]                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/billing/success`

### Purpose
Stripe checkout success callback. Confirms credit purchase was completed.

### User Actions
- **Navigate back**: Click "Back to Organizations" to return to org list

---

## Flow 56: Billing Cancelled

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /billing/cancel                                      │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                      ✗                                 │ │
│  │           Payment Cancelled                            │ │
│  │                                                        │ │
│  │  Your payment was not completed.                       │ │
│  │                                                        │ │
│  │  You can try again or contact support if you           │ │
│  │  need help.                                            │ │
│  │                                                        │ │
│  │           [Back to Organizations]                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/billing/cancel`

### Purpose
Stripe checkout cancellation callback. Informs user the payment was not completed.

### User Actions
- **Navigate back**: Click "Back to Organizations" to return to org list

---

## Billing Workflow Summary

```
Organization Detail (/organizations/:id)
    │
    │ Click "Billing" nav or billing card
    │
    ▼
Billing Dashboard (/organizations/:id/billing)
    │
    ├── Subscription Tab
    │   ├── [Upgrade] → UpgradeDialog → Select Tier → Stripe Checkout
    │   ├── [Cancel] → Confirmation → Cancel at period end
    │   └── [Reactivate] → Reactivate canceled subscription
    │
    ├── Credits Tab
    │   └── [Buy Credits] → Stripe Checkout → /billing/success or /billing/cancel
    │
    ├── Payment Methods Tab
    │   ├── [Add] → Stripe Portal (external)
    │   └── [Remove] → Delete saved card
    │
    ├── Invoices Tab
    │   └── [View/PDF] → Stripe-hosted invoice page
    │
    └── Usage Tab
        └── View unbilled usage records with free tier indicators
```

---

**Next**: See [15_settings_expanded.md](./15_settings_expanded.md) for expanded settings workflows.
