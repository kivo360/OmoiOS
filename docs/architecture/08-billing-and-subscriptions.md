# Part 8: Billing & Subscriptions

> Summary doc — this system has no prior design doc; this is the primary architecture reference.

## Overview

OmoiOS uses **Stripe** for payment processing with a tier-based subscription model, prepaid credit purchases, and usage-based billing for workflow executions.

## Billing Tiers

| Tier | Price | Workflows/mo | Agents | Storage | BYO Keys |
|------|-------|-------------|--------|---------|----------|
| **Free** | $0 | 5 | 1 | 2 GB | No |
| **Pro** | $50/mo | 100 | 5 | 50 GB | Yes |
| **Team** | $150/mo | 500 | 10 | 500 GB | Yes |
| **Enterprise** | Custom | Unlimited | Unlimited | Unlimited | Yes |
| **Lifetime** | $299 one-time | 50 | 5 | 50 GB | Yes |
| **BYO Platform** | $19/mo | Unlimited (user pays LLM) | 5 | 50 GB | Yes |

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                            Frontend                                  │
│  Checkout Flow → Billing Management → Usage Dashboard                │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     Billing API Routes                               │
│  billing.py (~2400 lines)                                            │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │Checkout  │ │Subscriptions│ │ Invoices │ │ Payments │ │ Promo   │ │
│  │Sessions  │ │ & Tiers    │ │          │ │          │ │ Codes   │ │
│  └────┬─────┘ └─────┬──────┘ └────┬─────┘ └────┬─────┘ └────┬────┘ │
└───────┼──────────────┼─────────────┼────────────┼────────────┼──────┘
        │              │             │            │            │
        ▼              ▼             ▼            ▼            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Service Layer                                    │
│  ┌─────────────────┐  ┌───────────────────┐  ┌────────────────────┐ │
│  │ BillingService   │  │SubscriptionService│  │ CostTrackingService│ │
│  │ - Account mgmt   │  │ - Tier limits     │  │ - LLM cost/task    │ │
│  │ - Usage tracking │  │ - Upgrade/down    │  │ - Sandbox cost     │ │
│  │ - Invoice gen    │  │ - Pause/resume    │  │ - Cost forecasting │ │
│  │ - Quota enforce  │  │ - BYO keys        │  │ - Per-org rollups  │ │
│  └────────┬────────┘  └───────────────────┘  └────────────────────┘ │
│           │                                                           │
│  ┌────────▼────────┐  ┌───────────────────┐                         │
│  │  StripeService   │  │ Background Tasks  │                         │
│  │  - Customers     │  │ - Dunning (6h)    │                         │
│  │  - Payments      │  │ - Reminders (daily)│                        │
│  │  - Subscriptions │  │ - Invoice gen (mo) │                        │
│  │  - Refunds       │  │ - Low credit (daily)│                       │
│  │  - Portal        │  └───────────────────┘                         │
│  │  - Webhooks      │                                                │
│  └──────────────────┘                                                │
└──────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stripe API                                                          │
│  Webhook Events: checkout.session.completed,                         │
│  customer.subscription.{created,updated,deleted},                    │
│  invoice.{paid,payment_failed}                                       │
└──────────────────────────────────────────────────────────────────────┘
```

## Key Capabilities

### Stripe Integration
- Customer creation linked to OmoiOS organizations
- Checkout sessions for credit purchases, lifetime purchases, and subscriptions
- Customer portal for self-service payment method management
- Webhook handler with signature verification for 6 event types
- Payment intents for automated dunning (off-session charges)
- Full refund support with reason tracking

### Subscription Management
- 5 tiers with configurable limits (workflows, agents, storage)
- Upgrade/downgrade with tier limit adjustment
- Pause/resume subscriptions
- Lifetime one-time purchase option ($499)
- BYO (Bring Your Own) API keys tier support
- Automatic monthly usage reset

### Usage Tracking & Enforcement
- `check_and_reserve_workflow()` validates quota before execution starts
- Consumption priority: subscription quota → free tier quota → prepaid credits
- Reservation pattern prevents over-consumption during parallel execution
- Per-task LLM cost tracking (prompt/completion tokens, model, provider)
- Per-sandbox cost aggregation
- Cost forecasting for pending tasks

### Invoice & Payment Processing
- Auto-generates monthly invoices from unbilled usage records
- Credits applied automatically to outstanding balance
- Automated dunning: 3 retries (24h, 72h, 72h) before account suspension
- Daily payment reminders for invoices due within 3 days
- Low credit balance warnings ($5 threshold)

### Promo Codes
- Discount types: PERCENTAGE, FIXED_AMOUNT, FULL_BYPASS, TRIAL_EXTENSION
- Usage limits, validity periods, tier restrictions
- Redemption tracking with audit trail

### Analytics (PostHog Integration)
- Tracked events: `checkout_completed`, `subscription_created`, `subscription_canceled`, `payment_failed`, `payment_succeeded`

## Database Tables

| Table | Purpose |
|-------|---------|
| `billing_accounts` | Organization billing state, Stripe customer link, credit balance |
| `subscriptions` | Tier, status, usage limits, Stripe subscription link |
| `invoices` | Billing period, line items (JSONB), payment status |
| `payments` | Payment intents, charges, refund tracking |
| `usage_records` | Per-workflow usage with token details (JSONB) |
| `cost_records` | Per-task/agent/sandbox LLM cost breakdown |
| `promo_codes` | Discount definitions with usage tracking |
| `promo_code_redemptions` | Redemption audit trail |

## Key Files

| File | Purpose |
|------|---------|
| `backend/omoi_os/api/routes/billing.py` | Billing API endpoints (~2400 lines) |
| `backend/omoi_os/services/billing_service.py` | Account management, usage tracking, invoicing |
| `backend/omoi_os/services/stripe_service.py` | Stripe API wrapper (customers, payments, webhooks) |
| `backend/omoi_os/services/subscription_service.py` | Tier management, quota enforcement |
| `backend/omoi_os/services/cost_tracking.py` | Per-task/agent/sandbox cost tracking |
| `backend/omoi_os/services/budget_enforcer.py` | Budget limit enforcement |
| `backend/omoi_os/tasks/billing_tasks.py` | Background tasks (dunning, invoicing, reminders) |
| `backend/omoi_os/models/billing.py` | BillingAccount, Invoice, Payment, UsageRecord models |
| `backend/omoi_os/models/subscription.py` | Subscription model with tier limits |
| `backend/omoi_os/models/cost_record.py` | Cost record model |
| `backend/omoi_os/models/promo_code.py` | PromoCode and PromoCodeRedemption models |

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/billing/account/{org_id}` | GET | Get/create billing account |
| `/api/v1/billing/account/{org_id}/credits` | POST | Add prepaid credits |
| `/api/v1/billing/checkout/credits` | POST | Stripe credit purchase checkout |
| `/api/v1/billing/checkout/lifetime` | POST | Stripe lifetime purchase checkout |
| `/api/v1/billing/subscriptions/checkout` | POST | Stripe subscription checkout |
| `/api/v1/billing/subscriptions/{org_id}` | GET | Get active subscription |
| `/api/v1/billing/subscriptions/{id}/cancel` | POST | Cancel subscription |
| `/api/v1/billing/subscriptions/{id}/upgrade` | POST | Upgrade tier |
| `/api/v1/billing/subscriptions/{id}/downgrade` | POST | Downgrade tier |
| `/api/v1/billing/invoices/{org_id}` | GET | List invoices |
| `/api/v1/billing/invoices/{id}/pay` | POST | Pay invoice |
| `/api/v1/billing/payment-methods` | POST | Attach payment method |
| `/api/v1/billing/portal/{org_id}` | GET | Stripe Customer Portal URL |
| `/api/v1/billing/usage/{org_id}` | GET | Usage summary |
| `/api/v1/billing/costs/{scope}/{id}` | GET | Cost breakdown |
| `/api/v1/billing/promo-codes/validate` | POST | Validate promo code |
| `/api/v1/billing/promo-codes/redeem` | POST | Redeem promo code |
| `/api/v1/billing/webhooks/stripe` | POST | Stripe webhook handler |
| `/api/v1/billing/config` | GET | Stripe publishable key |

## Known TODOs

- Budget/cost events (`BUDGET_EXCEEDED`, `BUDGET_WARNING`, `COST_RECORDED`) are published but have no subscribers (see [Integration Gaps](14-integration-gaps.md#gap-2-event-system-gaps))
- Tax calculation is manual (not automated)
- Multi-currency not yet supported (USD only)
- BYO API key storage/rotation not implemented
