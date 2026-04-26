# 01 · Auth & Tenancy

> **Implementation reference:** this file describes the conceptual model. For the concrete implementation — which Better Auth plugins cover what, full `auth.ts` config, RBAC statements, and custom-plugin sketches — see [`13-better-auth-integration.md`](./13-better-auth-integration.md).

Three token types. Every auth question (RBAC, scoping, sandbox callback) reduces to *which of these is this, and what scope does it carry?*

| Token | Prefix | Subject | Lifetime | Scope |
|---|---|---|---|---|
| **Platform API Key** | `rpk_live_…` | tenant backend | long-lived, rotatable | full org |
| **User JWT** | `eyJ…` | human end-user | 15 min access + refresh | RBAC subset of org |
| **Session Token** | `sess_tok_…` | the sandbox itself | 1h sliding | one session + declared scopes |

**Platform API Key** — server-to-server calls from the tenant's own backend. Rotate on employee offboarding. Never exposed to browsers.

**User JWT** — issued via OAuth2 PKCE for customer IDPs, or via signed delegation (token exchange) from the tenant backend. Scoped by RBAC rules the tenant defines.

**Session Token** — what the sandbox presents to the Credential Broker to fetch ephemeral GitHub/DB tokens. Losing one compromises one session; never more.

## Tenant scoping

Every path includes the org. Every token is bound to one org. A mismatch is `403`, never silently ignored.

```http
POST /v1/organizations/org_2fJx/sessions
Authorization: Bearer rpk_live_…
X-Organization-Id: org_2fJx           # MUST match org in path and token
Idempotency-Key: 7f3a8c…              # dedup retries on create
```

## Token exchange: tenant backend → user JWT

The tenant mints a short-lived user JWT for its own user without that user ever seeing the platform key.

```bash
curl -X POST https://api.example.com/v1/oauth/token \
  -H "Authorization: Bearer $PLATFORM_KEY" \
  -d grant_type=urn:ietf:params:oauth:grant-type:token-exchange \
  -d subject_token="$INTERNAL_USER_ID" \
  -d subject_token_type=urn:example:internal-user \
  -d scope="sessions:write sessions:read"

# → { access_token: "eyJ…", expires_in: 900, refresh_token: "…" }
```
