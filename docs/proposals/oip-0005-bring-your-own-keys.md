```
OIP: 0005
Title: Bring Your Own API Keys
Description: Let users supply their own LLM provider keys for unlimited workflows at $19/month
Author: OmoiOS Team
Status: Draft
Type: Standards Track
Created: 2026-02-17
Requires:
Replaces:
Superseded-By:
```

## Abstract

Allow users to supply their own Anthropic, OpenAI, or other LLM provider API keys and run unlimited workflows at a $19/month platform fee. The backend models and credential fallback logic already exist; this proposal covers the remaining work: REST endpoints for credential CRUD, a settings UI for key management, API key encryption at rest, and the Stripe product for the BYO tier.

## Motivation

### The pricing gap problem

OmoiOS's current pricing jumps from Free (5 workflows/month) to Pro ($50/month, 100 workflows). Power users who already hold Anthropic or OpenAI API keys pay twice — once for OmoiOS platform access and again for LLM tokens they're already budgeting for. The BYO tier at $19/month removes this double-billing and unlocks unlimited workflows for users willing to supply their own keys.

### Competitive positioning

Competitors like Kiro (Amazon) charge $20/month for their Pro tier. A $19/month BYO tier undercuts this while offloading the highest variable cost (LLM tokens) to the user's own account. This makes OmoiOS the cheapest multi-agent orchestration platform for developers who already pay for API access.

### What already exists

The backend has significant BYO infrastructure already built:

- **`UserCredential` model** (`backend/omoi_os/models/user_credentials.py`) — stores provider, api_key, base_url, model, config_data per user
- **`CredentialsService`** (`backend/omoi_os/services/credentials.py`) — fallback chain (user credential → system config), credential CRUD at the service layer
- **`DaytonaSpawner`** (`backend/omoi_os/services/daytona_spawner.py`) — already calls `get_anthropic_credentials(user_id)` and passes keys to sandbox env vars
- **`Subscription` model** (`backend/omoi_os/models/subscription.py`) — has `is_byo`, `byo_providers_configured`, and `SubscriptionTier.BYO` enum
- **`SubscriptionService`** (`backend/omoi_os/services/subscription_service.py`) — has `create_byo_subscription()` and `update_byo_providers()` methods
- **Database migration** (`backend/migrations/versions/20241213_user_credentials.py`) — `user_credentials` table exists

What's missing: API endpoints, frontend UI, encryption, and Stripe product creation.

## Specification

### 1. API Endpoints for Credential Management

Add a new route module at `backend/omoi_os/api/routes/credentials.py`:

```python
# POST /api/v1/credentials/{provider}
# Body: { "api_key": "<user-key>", "base_url": "https://...", "model": "claude-sonnet-4-20250514" }
# Response: { "id": "uuid", "provider": "anthropic", "is_active": true, "created_at": "..." }
# Note: Never return the raw api_key — return masked version ("sk-...xxxx")

# GET /api/v1/credentials
# Response: [{ "id": "uuid", "provider": "anthropic", "is_active": true, "masked_key": "sk-...xxxx", "last_used_at": "..." }]

# DELETE /api/v1/credentials/{provider}
# Response: 204 No Content

# PATCH /api/v1/credentials/{provider}
# Body: { "base_url": "...", "model": "...", "is_default": true }
# Response: updated credential (masked key)

# POST /api/v1/credentials/{provider}/validate
# Tests the key by making a minimal API call (e.g., list models)
# Response: { "valid": true, "provider": "anthropic", "models_available": [...] }
```

Supported providers (from existing `UserCredential.provider` values): `anthropic`, `openai`, `z_ai`, `google`.

Register in `backend/omoi_os/api/main.py` alongside existing route registrations.

### 2. API Key Encryption at Rest

The `UserCredential.api_key` column is currently plain `Text`. Encrypt before storage, decrypt on read.

**Approach**: Use `cryptography.fernet` with a key derived from a new `CREDENTIAL_ENCRYPTION_KEY` environment variable.

Create `backend/omoi_os/services/encryption.py`:

```python
from cryptography.fernet import Fernet

def encrypt_api_key(plain_key: str) -> str:
    """Encrypt an API key for database storage."""
    f = Fernet(settings.credential_encryption_key)
    return f.encrypt(plain_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key from database storage."""
    f = Fernet(settings.credential_encryption_key)
    return f.decrypt(encrypted_key.encode()).decode()
```

Modify `CredentialsService.save_user_credential()` to encrypt on write and `get_credentials()` / `get_anthropic_credentials()` to decrypt on read.

**Migration**: Add a data migration that encrypts all existing plain-text keys in the `user_credentials` table.

Add `CREDENTIAL_ENCRYPTION_KEY` to:
- `backend/config/production.yaml` (reference to env var)
- `backend/config/development.yaml` (generated dev key)
- Railway environment variables (production)

### 3. Frontend: Settings > API Keys Page

Create `frontend/app/(app)/settings/api-keys/` as the LLM provider key management page (the current file at this path manages OmoiOS auth tokens — rename that to `settings/tokens/` or merge).

**Components**:

#### ProviderKeyCard

Shows one provider's credential status:
- Provider name + logo (Anthropic, OpenAI, Google, Z.AI)
- Masked key display (`sk-ant-...7x4f`)
- Status badge (Active / Not Configured)
- Last used timestamp
- Actions: Edit, Delete, Validate

#### AddKeyDialog

Modal for adding/editing a provider key:
- Provider selector (dropdown)
- API key input (password field, paste-friendly)
- Base URL input (optional, shown for Z.AI)
- Default model selector (optional)
- "Validate Key" button that calls `POST /api/v1/credentials/{provider}/validate`
- Save button (disabled until validation passes)

#### BYOStatusBanner

Shows at the top of the API Keys page:
- If on BYO tier: "BYO Platform — Unlimited workflows using your own keys"
- If on another tier with keys configured: "Your keys are configured but your current plan uses OmoiOS-provided keys. Switch to BYO ($19/mo) for unlimited workflows."
- If no keys: "Add your LLM provider API key to unlock the BYO tier ($19/month, unlimited workflows)"

**React Query hooks** — extend `frontend/hooks/useApiKeys.ts`:

```typescript
// Already exists: useApiKeys(), useCreateApiKey(), useRevokeApiKey()
// Add:
export function useValidateApiKey() {
  return useMutation({
    mutationFn: (params: { provider: string }) =>
      api.post(`/api/v1/credentials/${params.provider}/validate`),
  });
}

export function useLLMCredentials() {
  return useQuery({
    queryKey: ["llm-credentials"],
    queryFn: () => api.get("/api/v1/credentials"),
  });
}
```

### 4. BYO Tier Stripe Product

Create a Stripe product for the BYO tier:

- **Product name**: "OmoiOS BYO Platform"
- **Price**: $19/month recurring
- **Metadata**: `{ "tier": "byo", "workflows": "unlimited", "agents": "unlimited" }`

Wire into `PlanSelectStep.tsx` (`frontend/components/onboarding/steps/PlanSelectStep.tsx`) and `UpgradeDialog.tsx` (`frontend/components/billing/UpgradeDialog.tsx`):

- When user selects BYO tier → check if they have at least one valid credential
- If no credential → show `AddKeyDialog` inline before proceeding to Stripe checkout
- After Stripe payment → call `SubscriptionService.create_byo_subscription()` → `update_byo_providers()`

### 5. Credential Validation on Workflow Start

Before launching a workflow for a BYO user, validate their credential is still active:

In `backend/omoi_os/services/daytona_spawner.py`, add a pre-flight check:

```python
async def _validate_byo_credentials(self, user_id: UUID) -> None:
    """Verify BYO user has valid credentials before spawning."""
    sub = await self.subscription_service.get_subscription(user_id)
    if sub and sub.is_byo:
        creds = self.cred_service.get_anthropic_credentials(user_id)
        if not creds or not creds.api_key:
            raise CredentialError(
                "BYO subscription requires a configured API key. "
                "Add your key in Settings > API Keys."
            )
```

This prevents spawning sandboxes that will immediately fail due to missing credentials.

### 6. Provider-Specific Configuration

Different providers need different configuration fields:

| Provider | Required | Optional |
|----------|----------|----------|
| Anthropic | `api_key` | `base_url`, `model` |
| OpenAI | `api_key` | `base_url`, `model`, `organization_id` |
| Google | `api_key` | `project_id`, `region` |
| Z.AI | `api_key` | `base_url` (required for Z.AI) |

Store provider-specific config in the existing `config_data` JSONB column on `UserCredential`.

## Rationale

### Why Fernet encryption over column-level database encryption?

Application-level encryption (Fernet) is portable across databases, doesn't require PostgreSQL extensions, and lets us rotate keys without database-level changes. The tradeoff is that the encryption key must be managed as an environment variable, but we already manage secrets this way (JWT keys, Stripe keys).

### Why validate on workflow start instead of on a schedule?

API keys can be revoked at any time by the provider. Validating at workflow start catches invalid keys at the point of use rather than requiring a background job. This is simpler and provides immediate user feedback. The tradeoff is a small latency increase (~200ms for a list-models call) on workflow start — acceptable given sandbox creation takes 10-30 seconds.

### Why not support arbitrary providers?

The credential fallback logic in `CredentialsService` and environment variable mapping in `DaytonaSpawner` are provider-specific. Supporting a generic "any provider" would require a plugin system that's premature. Starting with the 4 providers that OmoiOS actually uses (Anthropic, OpenAI, Google, Z.AI) covers the practical use cases.

### Why $19/month instead of free?

The platform fee covers infrastructure costs (PostgreSQL, Redis, sandbox orchestration, event bus) that exist regardless of which LLM the user calls. $19/month positions below Kiro's $20 Pro tier while generating sustainable per-user revenue.

## Backwards Compatibility

- **Existing Free/Pro/Team users**: No change. They continue using system-provided API keys. If they add their own keys, those keys are stored but not used until they switch to the BYO tier.
- **Existing `user_credentials` rows**: The encryption migration must handle rows with plain-text keys. A data migration will encrypt all existing rows in-place.
- **Existing `CredentialsService` consumers**: The `get_anthropic_credentials()` method signature doesn't change — it returns the same `AnthropicCredentials` dataclass. Encryption/decryption is transparent to callers.

## Security Considerations

### API Key Storage

- **At rest**: Fernet-encrypted in the `user_credentials.api_key` column. Encryption key stored in `CREDENTIAL_ENCRYPTION_KEY` environment variable (Railway/production only).
- **In transit**: All API calls over HTTPS. Keys never appear in URL parameters — always in request body.
- **In logs**: API keys must never be logged. Add a log filter or use the existing masked key format (`sk-...xxxx`) in all log output.
- **In responses**: The `GET /api/v1/credentials` endpoint returns masked keys only. The raw key is never sent back to the client after initial submission.

### Access Control

- Credentials are scoped to the authenticated user (`user_id` from JWT). Users cannot read, modify, or delete other users' credentials.
- The validation endpoint (`POST /credentials/{provider}/validate`) makes a minimal API call (list models) — it does not execute workflows or consume significant provider resources.

### Rate Limiting

- `POST /credentials/{provider}`: Rate limit to 10 requests/minute per user (prevents key-stuffing attacks).
- `POST /credentials/{provider}/validate`: Rate limit to 5 requests/minute per user (prevents using OmoiOS as a key-validation oracle).

### Key Rotation

- Users can update their key at any time via `PATCH /credentials/{provider}`. The old key is overwritten (not versioned).
- If `CREDENTIAL_ENCRYPTION_KEY` needs rotation: add a migration that decrypts with old key and re-encrypts with new key.

## Impact Assessment

### Effort

| Component | Scope |
|-----------|-------|
| API endpoints (`credentials.py`) | New file, ~200 lines |
| Encryption service | New file, ~50 lines |
| Encryption migration | New migration, ~30 lines |
| Frontend Settings page | New page + 3 components, ~400 lines |
| React Query hooks | Extend existing file, ~40 lines |
| BYO upgrade flow | Modify 2 existing components, ~100 lines |
| Pre-flight validation | Modify spawner, ~20 lines |
| Stripe product setup | Manual Stripe dashboard configuration |
| Tests | ~300 lines across unit + integration |

### Infrastructure Cost

- **Additional**: None. Uses existing PostgreSQL column. Fernet encryption is CPU-trivial.
- **Stripe**: Standard 2.9% + 30c per $19 transaction ($0.85/user/month).

### Success Metrics

- **Adoption**: % of users who configure at least one API key within 7 days of signup
- **Conversion**: % of key-configured users who subscribe to BYO ($19/month)
- **Retention**: 30-day retention rate of BYO subscribers vs Pro subscribers
- **Workflow volume**: Average workflows/month for BYO users vs Pro users (expect higher since unlimited)

## Open Issues

1. **Should BYO users be able to mix their own keys with system keys?** For example, use their Anthropic key for Claude but fall back to system OpenAI for embeddings. Current design: BYO means all LLM calls use user keys — no system fallback.

2. **Key rotation UX**: Should we proactively warn users when their key is about to expire (if the provider supports expiry metadata)? Or just fail at workflow start?

3. **Multi-provider workflows**: If a workflow uses both Claude and GPT-4, does the user need keys for both? Current design: yes, each provider requires its own credential. Alternative: fall back to system key for unconfigured providers.

4. **Organization-level keys vs user-level keys**: The current `UserCredential` model is user-scoped. Team/Enterprise plans may want org-level keys shared across members. This could be a follow-up OIP.

5. **Usage attribution**: When a BYO user's API key is used, OmoiOS has no visibility into their spend. Should we add cost estimation based on token counts even when using user keys?
