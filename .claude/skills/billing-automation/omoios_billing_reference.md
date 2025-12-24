# OmoiOS Billing Infrastructure Reference

**Created**: 2025-12-24
**Status**: Active
**Purpose**: OmoiOS-specific billing implementation details, code references, and integration patterns

This document maps the generic billing-automation skill to OmoiOS's actual infrastructure.

---

## OmoiOS Billing Architecture

### Existing Infrastructure (Already Built)

| Component | Location | Purpose |
|-----------|----------|---------|
| **BillingAccount** | `omoi_os/models/billing.py` | Org billing info, Stripe customer, free tier, credits |
| **Invoice** | `omoi_os/models/billing.py` | Generated invoices with line items |
| **Payment** | `omoi_os/models/billing.py` | Payment records with Stripe integration |
| **UsageRecord** | `omoi_os/models/billing.py` | Per-workflow usage tracking |
| **CostRecord** | `omoi_os/models/cost_record.py` | Per-LLM-call cost tracking |
| **UserCredential** | `omoi_os/models/user_credentials.py` | BYO API key storage |
| **BillingService** | `omoi_os/services/billing_service.py` | Usage tracking, invoicing, credits |
| **StripeService** | `omoi_os/services/stripe_service.py` | Full Stripe API wrapper |
| **CredentialsService** | `omoi_os/services/credentials.py` | BYO API key management |
| **CostTrackingService** | `omoi_os/services/cost_tracking.py` | LLM cost tracking |
| **BudgetEnforcerService** | `omoi_os/services/budget_enforcer.py` | Budget enforcement |
| **Billing API Routes** | `omoi_os/api/routes/billing.py` | REST endpoints + webhooks |

### What Needs Implementation (Not Yet Built)

| Component | Priority | Notes |
|-----------|----------|-------|
| **Subscription Model** | HIGH | Stripe recurring billing with tier limits |
| **Lifetime Purchase Tracking** | HIGH | One-time purchase with workflow quotas |
| **Sandbox → Cost Integration** | MEDIUM | Connect sandbox events to cost_records |
| **BYO Key → Sandbox** | MEDIUM | Use user's API keys in sandbox spawning |

### Database Tables

```
billing_accounts     - Org billing info, Stripe customer, free tier, credits
invoices            - Generated invoices with line items
payments            - Payment records with Stripe integration
usage_records       - Per-workflow usage tracking
cost_records        - Per-LLM-call cost tracking
user_credentials    - BYO API key storage (anthropic, openai, z_ai, github)
```

---

## OmoiOS Pricing Tiers

```
Tier 1: Lifetime Access ($299-$499 one-time)
├── 50 workflows/month included
├── 5 concurrent agents
├── Must add own API keys for overage
└── OmoiOS retains trajectory data

Tier 2: Monthly Subscription
├── Starter ($29/month): 20 workflows, 2 agents
├── Pro ($79/month): 100 workflows, 5 agents
├── Team ($199/month): 500 workflows, 15 agents
└── Enterprise (Custom): Unlimited

Tier 3: Usage-Based (Pay-As-You-Go)
├── $10-15 per workflow
├── LLM tokens: Pass-through + 20%
├── Free tier: 5 workflows/month
└── 2GB storage included

Tier 4: BYO API Key ($19/month platform fee)
├── User provides own LLM API keys
├── Unlimited workflows (user pays LLM directly)
└── OmoiOS gets trajectory data for training
```

---

## Quick Start: Using Existing Services

### BillingService Usage

```python
from omoi_os.services.billing_service import BillingService
from omoi_os.services.database import DatabaseService

db = DatabaseService()
billing = BillingService(db=db)

# Get or create billing account for organization
account = billing.get_or_create_billing_account(
    organization_id=org_id,
    session=session
)

# Record workflow usage (applies free tier if available)
usage = billing.record_workflow_usage(
    organization_id=org_id,
    ticket_id=ticket_id,
    usage_details={"input_tokens": 1000, "output_tokens": 500},
    session=session
)

# Check if org can execute a workflow
can_execute = account.can_use_free_workflow() or account.credit_balance > 0

# Add prepaid credits
account.add_credits(100.0)  # $100 in credits
```

### StripeService Usage

```python
from omoi_os.services.stripe_service import get_stripe_service

stripe = get_stripe_service()

# Create customer (linked to org)
customer = stripe.create_customer(
    email="billing@example.com",
    name="Acme Corp",
    organization_id=org_id
)

# Create checkout session for credits
checkout = stripe.create_checkout_session(
    customer_id=customer.id,
    price_id="price_credits_100",
    success_url="https://app.omoios.com/billing?success=true",
    cancel_url="https://app.omoios.com/billing?canceled=true"
)

# Create customer portal session (manage payment methods)
portal = stripe.create_portal_session(
    customer_id=customer.id,
    return_url="https://app.omoios.com/billing"
)
```

### CredentialsService Usage (BYO API Keys)

```python
from omoi_os.services.credentials import CredentialsService
from omoi_os.services.database import DatabaseService

db = DatabaseService()
creds = CredentialsService(db=db)

# Get user's Anthropic credentials (falls back to system default)
anthropic_creds = creds.get_anthropic_credentials(user_id=user_id, session=session)
# Returns: {"api_key": "...", "base_url": "https://api.z.ai/api/anthropic", "model": "glm-4.6v"}

# Save user's BYO API key
creds.save_user_credential(
    user_id=user_id,
    provider="anthropic",
    api_key="sk-ant-...",
    base_url="https://api.anthropic.com",  # Optional custom endpoint
    model="claude-sonnet-4-20250514",
    is_default=True,
    session=session
)

# Get all env vars for sandbox spawning
env_vars = creds.get_sandbox_env_vars(
    user_id=user_id,
    project_id=project_id,
    session=session
)
# Returns: {"ANTHROPIC_API_KEY": "...", "GITHUB_TOKEN": "...", "REPO_URL": "..."}
```

---

## Model Schemas

### BillingAccount Model

```python
# From omoi_os/models/billing.py
class BillingAccount(Base):
    __tablename__ = "billing_accounts"

    id: Mapped[UUID]
    organization_id: Mapped[UUID]  # FK to organizations

    # Stripe integration
    stripe_customer_id: Mapped[Optional[str]]
    stripe_payment_method_id: Mapped[Optional[str]]

    # Status: active, suspended, canceled, pending
    status: Mapped[str]

    # Free tier tracking (5 workflows/month)
    free_workflows_remaining: Mapped[int] = 5
    free_workflows_reset_at: Mapped[Optional[datetime]]

    # Prepaid credits (USD)
    credit_balance: Mapped[float] = 0.0

    # Preferences
    auto_billing_enabled: Mapped[bool] = True
    billing_email: Mapped[Optional[str]]

    # Tax
    tax_id: Mapped[Optional[str]]  # VAT/GST number
    tax_exempt: Mapped[bool] = False
    billing_address: Mapped[Optional[dict]]  # JSONB

    # Usage stats (cached)
    total_workflows_completed: Mapped[int] = 0
    total_amount_spent: Mapped[float] = 0.0

    # Helper methods
    def can_use_free_workflow(self) -> bool: ...
    def use_free_workflow(self) -> bool: ...
    def add_credits(self, amount: float) -> None: ...
    def use_credits(self, amount: float) -> float: ...
```

### UserCredential Model (BYO API Keys)

```python
# From omoi_os/models/user_credentials.py
class UserCredential(Base):
    __tablename__ = "user_credentials"

    id: Mapped[UUID]
    user_id: Mapped[UUID]  # FK to users

    # Provider: anthropic, openai, z_ai, github
    provider: Mapped[str]
    name: Mapped[Optional[str]]  # User-friendly name

    # Credentials (NOTE: should be encrypted at rest)
    api_key: Mapped[str]
    base_url: Mapped[Optional[str]]  # Custom endpoint (Z.AI, etc.)
    model: Mapped[Optional[str]]  # Default model
    config_data: Mapped[Optional[dict]]  # JSONB for extra config

    # Status
    is_active: Mapped[bool] = True
    is_default: Mapped[bool] = False
    last_used_at: Mapped[Optional[datetime]]
```

### Invoice Lifecycle

```python
# From omoi_os/models/billing.py
class Invoice(Base):
    # Status flow: draft → open → paid/past_due/void/uncollectible

    def add_line_item(
        self,
        description: str,
        unit_price: float,
        quantity: int = 1,
        ticket_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> None:
        """Add line item and recalculate totals."""

    def finalize(self) -> None:
        """Finalize invoice (no more changes)."""
        self.status = InvoiceStatus.OPEN.value
        self.finalized_at = utc_now()

    def mark_paid(self, amount: Optional[float] = None) -> None:
        """Mark invoice as paid."""

    def void(self) -> None:
        """Void the invoice."""
```

### CostRecord Model

```python
# From omoi_os/models/cost_record.py
class CostRecord(Base):
    """Tracks individual LLM call costs."""
    __tablename__ = "cost_records"

    id: Mapped[UUID]
    ticket_id: Mapped[Optional[UUID]]
    task_id: Mapped[Optional[UUID]]
    agent_id: Mapped[Optional[str]]

    # LLM usage
    model_name: Mapped[str]
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]
    total_tokens: Mapped[int]

    # Cost calculation
    cost_per_input_token: Mapped[float]
    cost_per_output_token: Mapped[float]
    total_cost: Mapped[float]

    # Context
    request_type: Mapped[str]  # 'completion', 'embedding', 'vision'
    call_metadata: Mapped[Optional[dict]]  # JSONB

    recorded_at: Mapped[datetime]
```

---

## Stripe Webhook Handling

The following webhooks are already handled in `omoi_os/api/routes/billing.py:505-649`:

| Event | Handler Action |
|-------|---------------|
| `checkout.session.completed` | Create/update billing account, apply credits |
| `customer.subscription.created` | Activate subscription tier |
| `customer.subscription.updated` | Handle tier changes |
| `customer.subscription.deleted` | Downgrade to free tier |
| `invoice.paid` | Record payment, reset usage |
| `invoice.payment_failed` | Start dunning notification |
| `charge.refunded` | Handle refund logic |

---

## TODO: Subscription Model Implementation

The subscription model needs to be created. Here's the proposed schema:

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

---

## Stripe Products to Configure

```
Products to create in Stripe Dashboard:
├── omoios_lifetime         ($299-499 one-time)
├── omoios_starter          ($29/month recurring)
├── omoios_pro              ($79/month recurring)
├── omoios_team             ($199/month recurring)
├── omoios_byo_platform     ($19/month recurring)
├── omoios_workflow_pack_10 ($100 one-time)
└── omoios_workflow_pack_50 ($400 one-time)
```

---

## Code References

### Models
- `omoi_os/models/billing.py` - BillingAccount, Invoice, Payment, UsageRecord
- `omoi_os/models/cost_record.py` - CostRecord for LLM costs
- `omoi_os/models/user_credentials.py` - UserCredential for BYO keys

### Services
- `omoi_os/services/billing_service.py` - Core billing logic
- `omoi_os/services/stripe_service.py` - Stripe API wrapper
- `omoi_os/services/credentials.py` - BYO API key management
- `omoi_os/services/cost_tracking.py` - LLM cost tracking
- `omoi_os/services/budget_enforcer.py` - Budget enforcement

### API Routes
- `omoi_os/api/routes/billing.py` - REST endpoints + webhooks

### Migrations
- `migrations/versions/038_billing_system.py` - Billing tables
- `migrations/versions/20241213_user_credentials.py` - User credentials

### Documentation
- `docs/design/billing/pricing_strategy.md` - Full pricing details
- `docs/design/billing/usage_monitoring_architecture.md` - Technical architecture

---

## Common Patterns

### Check if Org Can Execute Workflow

```python
from omoi_os.models.billing import BillingAccountStatus

async def can_execute_workflow(org_id: UUID, session: Session) -> tuple[bool, str]:
    """Check if organization can execute a workflow."""
    account = billing.get_billing_account(org_id, session)

    if not account:
        return False, "No billing account"

    if account.status == BillingAccountStatus.SUSPENDED.value:
        return False, "Account suspended"

    if account.can_use_free_workflow():
        return True, "free_tier"

    if account.credit_balance >= WORKFLOW_BASE_COST:
        return True, "credits"

    if account.stripe_payment_method_id:
        return True, "auto_billing"

    return False, "No payment method"
```

### Record Workflow Completion with Cost

```python
async def record_workflow_complete(
    org_id: UUID,
    ticket_id: UUID,
    total_cost: float,
    session: Session
) -> None:
    """Record workflow completion and charge."""
    account = billing.get_or_create_billing_account(org_id, session)

    # Try free tier first
    if account.use_free_workflow():
        usage = billing.record_workflow_usage(
            organization_id=org_id,
            ticket_id=ticket_id,
            usage_details={"free_tier": True, "cost": 0},
            session=session
        )
        return

    # Use credits if available
    credits_used = account.use_credits(total_cost)
    remaining = total_cost - credits_used

    if remaining > 0 and account.auto_billing_enabled:
        # Charge remaining via Stripe
        payment = await charge_customer(account, remaining)

    # Record usage
    billing.record_workflow_usage(
        organization_id=org_id,
        ticket_id=ticket_id,
        usage_details={
            "credits_used": credits_used,
            "charged": remaining,
            "total_cost": total_cost
        },
        session=session
    )
```

---

## Best Practices for OmoiOS Billing

1. **Always use sessions**: Pass database sessions through service calls
2. **Check free tier first**: Use `can_use_free_workflow()` before charging
3. **Log billing events**: All billing actions should emit events via EventBusService
4. **Handle Stripe failures gracefully**: Webhook handlers must be idempotent
5. **Use CredentialsService for API keys**: Never access user_credentials directly
6. **Track costs per-ticket**: Always associate CostRecords with ticket_id

---

## Dunning Management

```python
# Dunning is triggered when invoice.payment_failed webhook fires
# See: omoi_os/api/routes/billing.py:handle_invoice_payment_failed()

DUNNING_SCHEDULE = [
    {"days": 3, "action": "send_reminder_email"},
    {"days": 7, "action": "send_final_warning"},
    {"days": 14, "action": "suspend_account"},
]
```

---

## Testing Billing

```bash
# Use Stripe test mode
export STRIPE_API_KEY=sk_test_...
export STRIPE_WEBHOOK_SECRET=whsec_test_...

# Run billing tests
uv run pytest tests/integration/test_billing_service.py -v

# Test webhook locally with Stripe CLI
stripe listen --forward-to localhost:18000/api/billing/webhooks
```
