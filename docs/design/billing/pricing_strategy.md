# OmoiOS Pricing Strategy

**Created**: 2025-12-23
**Status**: Draft
**Owner**: Kevin Hill
**Purpose**: Single source of truth for pricing tiers, billing models, and monetization strategy

---

## Executive Summary

OmoiOS uses a **hybrid pricing model** combining:
1. **Lifetime/One-Time Purchases** - Early adopter acquisition with usage limits
2. **Monthly Subscriptions** - Recurring revenue with tiered pricing
3. **Usage-Based Pricing** - Pay-per-use for LLM costs and API calls
4. **BYO API Key Model** - Users provide their own LLM provider keys for unlimited usage

The core value exchange: **Users get powerful AI-driven engineering execution; OmoiOS gets trajectory data and agent behavior insights to improve the platform.**

---

## Pricing Tiers

### Tier 1: Lifetime Access (Founding Member)

**Target Audience**: First 100 users who want permanent access at a one-time cost.

| Attribute | Details |
|-----------|---------|
| **Price** | $299 one-time |
| **Concurrent Agents** | 5 agents running in parallel |
| **Workflows/Month** | 50 workflows included |
| **BYO API Keys** | Early access (before public Pro/Team release) |
| **Limits** | 5 projects, 50GB storage |
| **Support** | Priority email |
| **Data Rights** | OmoiOS retains trajectory/agent data for training |

**Value Proposition**:
- "Pay once, use forever" - appeals to cost-conscious early adopters
- **Early access to BYO keys** - founding members get this before anyone else
- Users who exceed limits bring their own API keys (no cost to OmoiOS)
- OmoiOS gets valuable training data from power users

**Marketing Hook**: *"Founding Member: Lifetime access + first dibs on BYO keys"*

---

### Tier 2: Monthly Subscription

**Target Audience**: Teams and individuals who prefer predictable monthly costs.

#### Launch Pricing (New Year Deal)

| Phase | Duration | Price | Details |
|-------|----------|-------|---------|
| **Phase 1** | Month 1 | $0.59/month | Teaser pricing - drive signups |
| **Phase 2** | Months 2-3 | $12.99/month | Discounted intro pricing |
| **Phase 3** | Month 4+ | Normal pricing | Full pricing tiers below |

#### Standard Subscription Tiers

| Tier | Price/Month | Concurrent Agents | Workflows/Month | BYO Keys | Best For |
|------|-------------|-------------------|-----------------|----------|----------|
| **Free** | $0/month | 1 | 5 | No | Trying it out |
| **Pro** | $50/month | 5 | 100 | Yes | Individual developers |
| **Team** | $150/month | 10 | 500 | Yes | Growing teams |
| **Enterprise** | Custom | Unlimited | Unlimited | Yes | Large orgs (15+) |

**Key Concepts:**
- **Concurrent Agents**: Primary differentiator. How many agents can run in parallel per project.
- **Task Queuing**: When users hit their concurrent limit, tasks queue up and run when a slot opens (no lost work).
- **BYO API Keys**: Pro+ users can bring their own LLM keys to bypass workflow limits. They pay the LLM provider directly.
- **Workflows/Month**: Secondary limit. De-emphasized in marketing but still enforced for free tier cost protection.

**Usage Overages** (applies to all subscription tiers):
- Additional workflows: $5-15 per workflow (based on complexity)
- Additional storage: $0.10/GB/month
- Additional agent hours: $2/hour

---

### Tier 3: Usage-Based (Pay-As-You-Go)

**Target Audience**: Teams with variable workloads who don't want commitments.

| Component | Price | Notes |
|-----------|-------|-------|
| **Per Workflow** | $10-15 | Based on task complexity |
| **LLM Tokens** | Pass-through + 20% | Anthropic/OpenAI pricing + margin |
| **API Calls** | $0.001/call | External integrations |
| **Storage** | $0.15/GB/month | Repository cache, embeddings |

**Free Tier** (Always Available):
- 5 workflows/month
- 1 project
- 1 concurrent agent
- 2GB storage
- Community support
- Basic analytics
- Resets on the 1st of each month

---

### Tier 4: BYO API Key (Power Users)

**Target Audience**: Lifetime and high-usage customers who want unlimited usage.

**How It Works**:
1. User provides their own LLM API keys (MiniMax, Z.ai, OpenAI, Anthropic)
2. User pays LLM providers directly for token usage
3. OmoiOS charges only for platform features (not LLM costs)
4. User gets "unlimited" workflows (limited only by their API spend)

**Supported Providers** (Planned):
| Provider | Models | Est. Cost/Workflow |
|----------|--------|-------------------|
| **MiniMax** | GPT-OSS-120B | $0.50-2.00 |
| **Z.ai** | Various | $0.30-1.50 |
| **OpenAI** | GPT-4, GPT-4o | $2.00-5.00 |
| **Anthropic** | Claude Sonnet/Opus | $2.00-8.00 |
| **Fireworks.ai** | Various OSS | $0.20-1.00 |

**Platform Fee for BYO Users**: $19/month flat (access to platform, storage, monitoring)

**Value Exchange**:
- Users get unlimited usage at their own API cost
- OmoiOS gets trajectory data for every workflow
- Win-win: power users save money, OmoiOS gets training data

---

## Value Exchange Model

### What Users Get
- Autonomous engineering execution
- Spec-driven workflow orchestration
- Real-time visibility and monitoring
- Phase gates and quality validation
- PR-based delivery with Git integration

### What OmoiOS Gets
- **Trajectory Data**: Complete agent execution traces
- **Task/Ticket Patterns**: What works, what fails
- **Workflow Branching Insights**: Discovery patterns
- **Model Performance Data**: Which LLMs perform best for which tasks

### Data Usage Policy (Draft)
- All trajectory data is anonymized before use
- Users can opt-out of data collection (with premium pricing)
- Data used only for platform improvement (not sold to third parties)
- Enterprise tier includes data isolation option

---

## Implementation Status

### Already Built

| Component | Status | Location |
|-----------|--------|----------|
| **Billing Infrastructure** | | |
| BillingAccount Model | ✅ Complete | `omoi_os/models/billing.py` |
| Invoice Model | ✅ Complete | `omoi_os/models/billing.py` |
| Payment Model | ✅ Complete | `omoi_os/models/billing.py` |
| UsageRecord Model | ✅ Complete | `omoi_os/models/billing.py` |
| Stripe Service | ✅ Complete | `omoi_os/services/stripe_service.py` |
| Billing Service | ✅ Complete | `omoi_os/services/billing_service.py` |
| Billing API Routes | ✅ Complete | `omoi_os/api/routes/billing.py` |
| Stripe Webhooks | ✅ Complete | `omoi_os/api/routes/billing.py:505-649` |
| Free Tier Tracking | ✅ Complete | 5 workflows/month in BillingAccount |
| Prepaid Credits | ✅ Complete | Credit purchase checkout |
| **Cost Tracking** | | |
| Cost Tracking Service | ✅ Complete | `omoi_os/services/cost_tracking.py` |
| Budget Enforcement | ✅ Complete | `omoi_os/services/budget_enforcer.py` |
| CostRecord Model | ✅ Complete | `omoi_os/models/cost_record.py` |
| **BYO API Key Infrastructure** | | |
| UserCredential Model | ✅ Complete | `omoi_os/models/user_credentials.py` |
| Credentials Service | ✅ Complete | `omoi_os/services/credentials.py` |
| user_credentials Table | ✅ Complete | `migrations/20241213_user_credentials.py` |

### Database Tables Already Exist

```
billing_accounts     - Org billing info, Stripe customer, free tier, credits
invoices            - Generated invoices with line items
payments            - Payment records with Stripe integration
usage_records       - Per-workflow usage tracking
cost_records        - Per-LLM-call cost tracking
user_credentials    - BYO API key storage (anthropic, openai, z_ai, github)
```

### Needs Implementation

| Component | Priority | Effort | Notes |
|-----------|----------|--------|-------|
| **Subscription Model** | 🔴 High | Medium | Stripe recurring billing - new `subscriptions` table |
| **One-Time Purchase Model** | 🔴 High | Medium | Lifetime access tracking - extend billing_accounts or new table |
| **Billing UI (Frontend)** | 🟡 Medium | Large | React components for Org Settings → Billing tab |
| **Usage Limits Enforcement** | 🟡 Medium | Small | Configurable limits per subscription tier |
| **Tier Management API** | 🟢 Lower | Small | Upgrade/downgrade endpoints |
| **Proration Calculator** | 🟢 Lower | Small | Mid-cycle tier changes |
| **API Key Encryption** | 🟡 Medium | Small | Production-grade encryption for user_credentials |

---

## Stripe Product Configuration

### Products to Create in Stripe

```
Products:
├── omoios_lifetime
│   └── Price: $299-499 one-time
├── omoios_free
│   └── Price: $0/month (free tier tracking)
├── omoios_pro
│   └── Price: $50/month recurring
├── omoios_team
│   └── Price: $150/month recurring
├── omoios_enterprise
│   └── Price: Custom pricing
├── omoios_byo_platform
│   └── Price: $19/month recurring
├── omoios_workflow_pack_10
│   └── Price: $100 one-time (10 workflows)
└── omoios_workflow_pack_50
    └── Price: $400 one-time (50 workflows)
```

### Webhook Events to Handle

| Event | Action |
|-------|--------|
| `checkout.session.completed` | Create/update billing account |
| `customer.subscription.created` | Activate subscription tier |
| `customer.subscription.updated` | Handle tier changes |
| `customer.subscription.deleted` | Downgrade to free tier |
| `invoice.paid` | Record payment, reset usage |
| `invoice.payment_failed` | Send dunning notification |
| `charge.refunded` | Handle refund logic |

---

## Database Schema Additions

### Subscription Model (New - Needs Implementation)

```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    billing_account_id UUID NOT NULL REFERENCES billing_accounts(id),

    -- Stripe references
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_price_id VARCHAR(255),

    -- Subscription details
    tier VARCHAR(50) NOT NULL,  -- 'starter', 'pro', 'team', 'enterprise', 'lifetime', 'byo'
    status VARCHAR(50) NOT NULL,  -- 'active', 'past_due', 'canceled', 'paused'

    -- Billing cycle
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,

    -- Usage limits for this period
    workflows_limit INTEGER NOT NULL,
    workflows_used INTEGER NOT NULL DEFAULT 0,
    agents_limit INTEGER NOT NULL,
    storage_limit_gb INTEGER NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_org ON subscriptions(org_id);
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);
```

### User API Keys Model (Already Exists ✅)

The `user_credentials` table already exists and handles BYO API key storage:

**Location**: `omoi_os/models/user_credentials.py` + `migrations/20241213_user_credentials.py`

**Existing Schema**:
```sql
CREATE TABLE user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Provider details
    provider VARCHAR(50) NOT NULL,  -- 'anthropic', 'openai', 'z_ai', 'github', etc.
    name VARCHAR(100),              -- User-friendly name

    -- Credentials (NOTE: should be encrypted at rest in production)
    api_key TEXT NOT NULL,
    base_url VARCHAR(500),          -- Custom base URL for proxies (Z.AI, etc.)
    model VARCHAR(100),             -- Default model for this credential
    config_data JSONB,              -- Additional provider-specific config

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    last_used_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_credentials_user_provider ON user_credentials(user_id, provider);
CREATE UNIQUE INDEX idx_user_credentials_default ON user_credentials(user_id, provider) WHERE is_default = true;
```

**Supported Providers** (via `CredentialsService`):
- `anthropic` - Claude API (or Z.AI proxy)
- `openai` - OpenAI API
- `z_ai` - Z.AI (Anthropic-compatible endpoint)
- `github` - GitHub OAuth tokens

**Service**: `omoi_os/services/credentials.py` provides:
- `get_anthropic_credentials(user_id)` - Get user's or system Anthropic creds
- `get_github_credentials(user_id)` - Get user's GitHub OAuth token
- `get_credentials(provider, user_id)` - Generic credential lookup
- `save_user_credential(...)` - Save/update user credentials
- `get_sandbox_env_vars(user_id)` - Get all env vars for sandbox spawning

---

## Marketing Positioning by Tier

### Lifetime Tier Marketing

**Headline**: "Founding Member: Lock in Lifetime Access"

**Copy**:
> Join the first wave of OmoiOS users and get permanent access to autonomous engineering execution. Pay once, use forever. Perfect for developers who believe in the future of AI-assisted development.

**CTA**: "Claim Founding Member Access"

### Subscription Marketing

**Headline**: "Scale Your Engineering Output"

**Copy**:
> Ship more features with the team you have. OmoiOS turns feature requests into reviewed PRs—automatically. Start with 5 free workflows, upgrade when you're ready.

**CTA**: "Start Free" → "Upgrade to Pro"

### New Year Deal Marketing

**Headline**: "New Year, New Workflow"

**Copy**:
> Start 2026 shipping faster. Get your first month for just $0.59, then $12.99/month for two months. Lock in early access pricing before it's gone.

**CTA**: "Claim New Year Deal"

### BYO API Key Marketing

**Headline**: "Unlimited Workflows. Your Keys. Your Cost."

**Copy**:
> Already paying for LLM APIs? Bring your own keys and run unlimited workflows on OmoiOS. We handle the orchestration; you control the costs.

**CTA**: "Connect Your API Keys"

---

## Revenue Projections (Placeholder)

| Scenario | Year 1 Users | MRR | ARR |
|----------|--------------|-----|-----|
| Conservative | 500 | $15,000 | $180,000 |
| Moderate | 2,000 | $60,000 | $720,000 |
| Optimistic | 5,000 | $150,000 | $1,800,000 |

*Assumptions: 40% free, 30% starter, 20% pro, 10% team/lifetime*

---

## Next Steps

1. **Finalize tier pricing** - Market test $299 vs $499 lifetime
2. **Create Subscription model** - Database migration + service
3. **Build Billing UI** - Organization Settings → Billing tab
4. **Implement BYO key storage** - Secure key vault integration
5. **Set up Stripe products** - Create products and prices
6. **Launch New Year deal** - Marketing campaign prep

---

## Related Documents

- [Usage Monitoring Architecture](./usage_monitoring_architecture.md) - Technical implementation details for cost tracking and billing integration
- [Cost Tracking README](../../cost_tracking/README.md) - Cost tracking system implementation
- [Go-to-Market Strategy](../../../docs/go_to_market_strategy.md) - Launch and acquisition strategy
- [Marketing Overview](../../../docs/marketing_overview.md) - Positioning and messaging

## Code References

### Billing Infrastructure
- **Models**: `omoi_os/models/billing.py` (BillingAccount, Invoice, Payment, UsageRecord)
- **Service**: `omoi_os/services/billing_service.py` (usage tracking, invoicing, credits)
- **Stripe**: `omoi_os/services/stripe_service.py` (full Stripe API wrapper)
- **API Routes**: `omoi_os/api/routes/billing.py` (REST endpoints + webhooks)
- **Migration**: `migrations/versions/038_billing_system.py`

### BYO API Key Infrastructure
- **Model**: `omoi_os/models/user_credentials.py` (UserCredential)
- **Service**: `omoi_os/services/credentials.py` (CredentialsService)
- **Migration**: `migrations/versions/20241213_user_credentials.py`

### Cost Tracking
- **Model**: `omoi_os/models/cost_record.py` (CostRecord)
- **Service**: `omoi_os/services/cost_tracking.py` (CostTrackingService)
- **Budget**: `omoi_os/services/budget_enforcer.py` (BudgetEnforcerService)

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-12-23 | Initial draft | Kevin Hill |
