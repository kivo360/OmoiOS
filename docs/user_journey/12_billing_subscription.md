# 12 Billing & Subscription Management

**Part of**: [User Journey Documentation](./README.md)

---

## Overview

Billing management is scoped per organization and integrates with Stripe for subscriptions, credit purchases, payment methods, and invoicing. Users access billing through the organization detail page.

---

## 12.1 Accessing Billing

```
User navigates to organization:
   ↓
1. From sidebar → Organizations → Click organization
   ↓
2. Organization detail page → Click "Billing" tab/link
   ↓
3. Arrives at /organizations/:id/billing
   ↓
4. Billing dashboard loads with 5 tabs:
   - Subscription (default)
   - Credits
   - Payment Methods
   - Invoices
   - Usage
```

---

## 12.2 Subscription Management

```
Billing Dashboard → Subscription Tab (default):
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Stats Bar                                                   │
│  [$247.80 Balance] [∞ Workflows Left] [34 Used] [$892 Spent]│
│                                                              │
│  Account Status                                   [active]   │
│  Billing Email: team@acme.com                                │
│  Auto-Billing: Enabled                                       │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  SubscriptionCard                                      │ │
│  │  Current: Pro Plan ($50/month)                         │ │
│  │  Period: Feb 1 - Mar 1, 2026                           │ │
│  │  Workflows: 34/100 used                                │ │
│  │                                                        │ │
│  │  [Upgrade Plan] [Manage →] [Cancel Subscription]       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Upgrade Flow

```
User clicks [Upgrade Plan]:
   ↓
UpgradeDialog opens with tier options:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Choose Your Plan                                            │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Starter  │ │ Pro      │ │ Team     │ │ BYO Keys │      │
│  │ Free     │ │ $50/mo   │ │ $150/mo  │ │ $19/mo   │      │
│  │ 1 agent  │ │ 5 agents │ │ 25 agents│ │ Use your │      │
│  │ 5 flows  │ │ 100 flows│ │ 500 flows│ │ own keys │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                              │
│  Also available: Lifetime ($499) | Enterprise (Contact)      │
└─────────────────────────────────────────────────────────────┘
   ↓
User selects tier:
   ↓
┌─ Pro/Team → POST /checkout/subscription → Stripe Checkout
│   ↓ success → /organizations/:id/billing?checkout=success
│   ↓ cancel → /organizations/:id/billing?checkout=cancelled
│
├─ BYO Keys → POST /checkout/subscription (tier=byo)
│
├─ Lifetime → POST /checkout/lifetime → Stripe Checkout
│   ↓ success → /billing/success
│   ↓ cancel → /billing/cancel
│
├─ Enterprise → mailto:sales@omoios.com
│
└─ Already subscribed → Opens Stripe Customer Portal
```

### Cancel / Reactivate Flow

```
User clicks [Cancel Subscription]:
   ↓
Confirmation toast → Cancels at period end
   ↓
SubscriptionCard shows "Canceling at end of period"
   ↓
User can click [Reactivate] before period ends
   ↓
Reactivation restores subscription immediately
```

---

## 12.3 Credit Purchases

```
Billing Dashboard → Credits Tab:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Buy Credits                                                 │
│  Purchase prepaid credits. Each workflow costs $10.           │
│                                                              │
│  Amount (USD): [$____50_____]        [Buy Credits]          │
│                                                              │
│  Quick options: [$25] [$50] [$100] [$250] [$500]            │
└─────────────────────────────────────────────────────────────┘
   ↓
User enters amount ($10-$1000) or clicks quick option:
   ↓
Clicks [Buy Credits]:
   ↓
POST /checkout/credits → Stripe Checkout session
   ↓
User completes Stripe payment:
   ↓
┌─ Success → /billing/success → "Payment Successful!"
│   ↓ [Back to Organizations] → /organizations
│
└─ Cancelled → /billing/cancel → "Payment Cancelled"
    ↓ [Back to Organizations] → /organizations
```

---

## 12.4 Payment Method Management

```
Billing Dashboard → Payment Methods Tab:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Payment Methods                       [+ Add Payment Method]│
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  💳 Visa ending in 4242                  [Default]   │   │
│  │                                             [🗑]     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  💳 Mastercard ending in 5555                        │   │
│  │                                             [🗑]     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

Actions:
- [+ Add Payment Method] → Opens Stripe Customer Portal (new tab)
- [🗑 Remove] → DELETE /payment-methods/:id → Toast confirmation
```

---

## 12.5 Invoice History

```
Billing Dashboard → Invoices Tab:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Invoices — Your billing history                             │
│                                                              │
│  Invoice #    | Date       | Amount  | Status | Action      │
│  INV-2026-042 | 2026-02-01 | $50.00  | paid   | [View]     │
│  INV-2026-041 | 2026-01-01 | $50.00  | paid   | [PDF]      │
│  INV-2026-040 | 2025-12-01 | $50.00  | paid   | [View]     │
└─────────────────────────────────────────────────────────────┘

[View] → Opens Stripe-hosted invoice page (new tab)
[PDF] → Downloads invoice PDF (new tab)
```

---

## 12.6 Usage Tracking

```
Billing Dashboard → Usage Tab:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Current Usage — Unbilled usage for the current period       │
│                                                              │
│  Date       | Type     | Qty | Price  | Free Tier           │
│  2026-02-17 | workflow | 1   | $10.00 | [Paid]              │
│  2026-02-16 | workflow | 1   | $0.00  | [Free]              │
│  2026-02-15 | workflow | 1   | $10.00 | [Paid]              │
└─────────────────────────────────────────────────────────────┘

- Free tier workflows show "Free" badge
- Paid workflows show "Paid" badge
- Usage records are per-workflow completion
```

---

## Billing Journey Summary

```
Organization Detail
    │
    ├── First-time user (Free Tier)
    │   ├── Uses 5 free workflows/month
    │   ├── Hits limit → Sees upgrade prompt
    │   └── Clicks Upgrade → UpgradeDialog → Selects Pro/Team → Stripe Checkout
    │
    ├── Subscribed user (Pro/Team)
    │   ├── Workflows counted against monthly limit
    │   ├── Can buy additional credits for overflow
    │   ├── Manages payment methods
    │   ├── Reviews invoices
    │   └── Can cancel (effective at period end) or reactivate
    │
    └── BYO Keys user
        ├── $19/month base subscription
        ├── Uses own API keys for LLM costs
        └── Workflow tracking still applies

External Touchpoints:
    ├── Stripe Checkout (payment collection)
    ├── Stripe Customer Portal (advanced management)
    └── Stripe-hosted invoices (billing history)
```

---

**Related**: See [page_flows/14_billing.md](../page_flows/14_billing.md) for detailed page-level flow documentation.
