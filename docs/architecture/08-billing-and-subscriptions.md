# Part 8: Billing & Subscriptions

> Summary doc — this system has no prior design doc; this is the primary architecture reference.

## Overview

OmoiOS uses **Stripe** for payment processing with a tier-based subscription model, prepaid credit purchases, and usage-based billing for workflow executions.

## Billing Tiers

| Tier | Price | Workflows/Month | Features |
|------|-------|-----------------|----------|
| **Free** | $0 | 5 | Basic workflow execution |
| **Starter** | $19/mo | 50 | Priority support |
| **Pro** | $99/mo | 300 | Advanced analytics, higher concurrency |
| **Enterprise** | Custom | Unlimited | SLA, dedicated support |

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Frontend   │────→│  Billing Routes  │────→│ BillingService│
│  (checkout)  │     │  (billing.py)    │     │              │
└──────────────┘     └──────────────────┘     │  Stripe SDK  │
                                               │  Usage Track │
                                               │  Enforcement │
                                               └──────────────┘
```

## Key Capabilities

### Stripe Integration
- Customer creation linked to OmoiOS organizations
- Checkout sessions for credit purchases
- Customer portal for payment method management
- Webhook handling for payment events

### Usage Tracking
- Workflow completion triggers usage records
- Consumption priority: free tier quota → prepaid credits → subscription quota
- Usage metrics tracked per organization per billing period

### Quota Enforcement
- `check_and_reserve_workflow()` validates quota before execution starts
- Reservation pattern prevents over-consumption during parallel execution
- Account suspension for payment failures

### Invoice Generation
- Auto-generates invoices for unbilled usage
- Credits applied automatically to outstanding balance
- 7-day payment terms

## Key Files

| File | Purpose |
|------|---------|
| `backend/omoi_os/api/routes/billing.py` | Billing API endpoints (~1336 lines) |
| `backend/omoi_os/services/billing_service.py` | Business logic, Stripe integration |
| `backend/omoi_os/services/cost_tracking.py` | Per-workflow cost tracking |
| `backend/omoi_os/services/budget_enforcer.py` | Budget limit enforcement |
| `backend/omoi_os/models/billing.py` | Billing database model |
| `backend/omoi_os/models/subscription.py` | Subscription model |
| `backend/omoi_os/models/cost_record.py` | Cost record model |
| `backend/omoi_os/models/promo_code.py` | Promotional code model |

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/billing/checkout` | POST | Create Stripe checkout session |
| `/api/v1/billing/portal` | POST | Create Stripe customer portal session |
| `/api/v1/billing/usage` | GET | Get current usage and quota |
| `/api/v1/billing/invoices` | GET | List invoices |
| `/api/v1/billing/credits` | GET | Get credit balance |
| `/api/v1/billing/webhook` | POST | Stripe webhook handler |

## Known TODOs

- `billing.py:842-927` — Add proper admin authentication check (3 places)
- Budget/cost events (`BUDGET_EXCEEDED`, `BUDGET_WARNING`, `COST_RECORDED`) are published but have no subscribers (see [Integration Gaps](14-integration-gaps.md#gap-2-event-system-gaps))
