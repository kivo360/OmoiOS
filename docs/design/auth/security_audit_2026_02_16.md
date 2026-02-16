# Security Audit — 2026-02-16

**Created**: 2026-02-16
**Status**: In Progress
**Purpose**: Track all vulnerabilities found during comprehensive security audit and their remediation status.

## Summary

Full security audit conducted across authentication, authorization, input validation, sandbox security, database security, secrets management, and frontend rendering. Found **16 vulnerabilities** across 6 attack surface areas.

**Scorecard**: 6 Critical, 5 High, 6 Medium, 3 Low

---

## Day 1 — Critical / Immediate (DONE)

All Day 1 items have been fixed and pushed.

### 1. CORS Wildcard in Production
- **Severity**: Critical
- **Status**: DONE (`cc79c294`)
- **File**: `backend/omoi_os/api/main.py`
- **Issue**: `allow_origins=["*"]` with `allow_credentials=True` enabled CSRF and credential theft from any origin.
- **Fix**: Origins restricted to `https://omoios.dev` and `https://www.omoios.dev` in production; wildcard only in dev/test.

### 2. WebSocket Authentication Bypass
- **Severity**: Critical
- **Status**: DONE (`cc79c294` backend, `912de1da` frontend)
- **File**: `backend/omoi_os/api/routes/events.py`, `frontend/providers/WebSocketProvider.tsx`, `frontend/hooks/useEvents.ts`, `frontend/hooks/useBoardEvents.ts`
- **Issue**: `/ws/events` endpoint had zero authentication — any unauthenticated user could subscribe to all real-time events.
- **Fix**: JWT verification via `?token=` query parameter (standard for WebSocket since browsers can't send Authorization headers on upgrade). Frontend passes token from localStorage. Backend returns 4401 close code on auth failure.

### 3. Hardcoded Credentials in Docs
- **Severity**: Critical
- **Status**: DONE (`cc79c294`)
- **Files**: `docs/design/auth/supabase_auth_integration.md`, `scripts/db/supabase_setup_rls_and_triggers.sql`
- **Issue**: Real Supabase database password, service role key, anon key, and project references committed to git.
- **Fix**: Replaced all 11 occurrences with `<YOUR_SUPABASE_*>` placeholders. Note: Supabase is no longer used (migrated to custom auth), but credentials should still be rotated.

### 4. Weak JWT Secret in Production
- **Severity**: Critical
- **Status**: DONE (`cc79c294`)
- **Files**: `backend/omoi_os/config.py`, `backend/config/production.yaml`
- **Issue**: Default JWT secret `"dev-secret-key-change-in-production"` in YAML would allow token forgery if `AUTH_JWT_SECRET_KEY` env var wasn't set.
- **Fix**: Pydantic `model_validator` rejects known insecure defaults and secrets shorter than 32 chars when `OMOIOS_ENV=production`. Removed placeholder from `production.yaml`.

---

## Day 2 — High Priority (TODO)

### 5. SQL Injection in Vector Search
- **Severity**: Critical
- **Status**: TODO
- **Area**: Embedding/similarity queries
- **Issue**: Raw string interpolation in vector similarity queries bypasses SQLAlchemy's parameterized query protections.
- **Action**: Audit all pgvector/embedding queries. Replace any raw SQL string formatting with parameterized queries or SQLAlchemy constructs.

### 6. Command Injection in Agent Tool Interface
- **Severity**: Critical
- **Status**: TODO
- **File**: `backend/omoi_os/workspace/managers.py:114`
- **Issue**: `subprocess.run()` with `shell=True` and unescaped user-controlled repository URLs. Also `eval()` usage in alert condition evaluation.
- **Action**: Replace `shell=True` with list-form arguments. Use `shlex.quote()` for any shell-interpolated values. Remove `eval()` and replace with safe expression parser.

### 7. Sandbox Callback Authentication Bypass
- **Severity**: Critical
- **Status**: TODO
- **File**: `backend/omoi_os/api/routes/sandbox.py`
- **Issue**: Callback endpoints (`POST /{sandbox_id}/events`, `/messages`, `/task-complete`, `/validation-result`) lack authentication entirely. Comments say "No auth required — worker calls this from inside the sandbox." This allows sandbox hijacking and fake event injection.
- **Action**: Implement HMAC signature verification for sandbox callbacks using a per-sandbox secret generated at spawn time.

### 8. IDOR in API Key Creation
- **Severity**: Critical
- **Status**: TODO
- **File**: `backend/omoi_os/api/routes/auth.py:362-384`
- **Issue**: Users can create API keys for any organization without ownership validation.
- **Action**: Add `verify_organization_access()` check before API key creation.

### 9. API Key Scopes Not Enforced
- **Severity**: Critical
- **Status**: TODO
- **File**: `backend/omoi_os/services/auth_service.py:370-408`
- **Issue**: API keys store scopes (read/write/admin) but the authorization layer never checks them.
- **Action**: Implement scope validation middleware that enforces permissions defined on API keys.

### 10. No Rate Limiting on Auth Endpoints
- **Severity**: High
- **Status**: TODO
- **File**: `backend/omoi_os/api/routes/auth.py`
- **Issue**: `/login`, `/register`, `/forgot-password`, `/verify-email` have no rate limiting. Enables brute force, account enumeration, and email flooding.
- **Action**: Add rate limiting middleware (e.g., `slowapi` or Redis-based limiter). Suggested limits: 5 login attempts/min per IP, 3 registrations/hour per IP, 3 password resets/hour per email.

### 11. Debug Endpoints in Production
- **Severity**: High
- **Status**: TODO
- **File**: `backend/omoi_os/api/routes/` (debug routes)
- **Issue**: `/debug` routes accessible in production without environment-based gating.
- **Action**: Conditionally register debug routes only when `OMOIOS_ENV != production`.

### 12. OpenAPI Docs Exposed in Production
- **Severity**: High
- **Status**: TODO
- **File**: `backend/omoi_os/api/main.py`
- **Issue**: `/docs`, `/redoc`, `/openapi.json` accessible at `https://api.omoios.dev/docs`, exposing full API schema.
- **Action**: Set `docs_url=None, redoc_url=None, openapi_url=None` in production FastAPI app constructor.

### 13. No Refresh Token Rotation
- **Severity**: High
- **Status**: TODO
- **File**: `backend/omoi_os/api/routes/auth.py:147-184`
- **Issue**: Stolen refresh tokens remain valid for full 7-day lifetime. No family tracking or rotation per RFC 6749 Section 10.4.
- **Action**: Implement refresh token rotation — issue new refresh token on each use, invalidate the old one, detect reuse as a breach signal.

---

## Day 3 — Medium Priority (TODO)

### 14. XSS via Markdown Rendering
- **Severity**: High
- **Status**: TODO
- **File**: `frontend/components/ui/markdown.tsx:286,364`
- **Issue**: `dangerouslySetInnerHTML` with Mermaid `securityLevel: 'loose'` enables arbitrary JS execution.
- **Action**: Set Mermaid `securityLevel: 'strict'`. Sanitize HTML output with DOMPurify before rendering.

### 15. LLM Prompt Injection via User Content
- **Severity**: High
- **Status**: TODO
- **File**: `backend/omoi_os/services/template_service.py:27`
- **Issue**: User-controlled spec/task content flows into Jinja2 templates with `autoescape=False`, enabling prompt manipulation.
- **Action**: Enable `autoescape=True` on Jinja2 environment. Add input sanitization layer that strips injection patterns before template rendering.

### 16. Missing Input Validation on JSONB Fields
- **Severity**: Medium
- **Status**: TODO
- **Files**: `backend/omoi_os/api/routes/tasks.py`, `backend/omoi_os/api/routes/specs.py`
- **Issue**: `execution_config`, `spec.design`, `user.attributes` accept arbitrary JSON without schema validation.
- **Action**: Add Pydantic models or JSON Schema validation for all JSONB input fields.

### 17. Explore Routes Missing Authentication
- **Severity**: Medium
- **Status**: TODO
- **File**: `backend/omoi_os/api/routes/` (explore endpoints)
- **Issue**: Some `/explore` endpoints don't require authentication.
- **Action**: Add `Depends(get_current_user)` to all explore route handlers.

### 18. GitHub Webhook Signature Not Verified
- **Severity**: Medium
- **Status**: TODO
- **File**: `backend/omoi_os/api/routes/github.py`
- **Issue**: Webhook endpoint doesn't verify `X-Hub-Signature-256` header, allowing spoofed events.
- **Action**: Implement HMAC-SHA256 signature verification using the webhook secret.

### 19. Missing Security Headers
- **Severity**: Medium
- **Status**: TODO
- **File**: `backend/omoi_os/api/main.py`
- **Issue**: No `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Content-Security-Policy` headers.
- **Action**: Add security headers middleware. Vercel handles some of these for the frontend, but the backend API needs them explicitly.

### 20. OAuth Tokens Stored Unencrypted
- **Severity**: Medium
- **Status**: TODO
- **File**: `backend/omoi_os/services/oauth_service.py:305-312`
- **Issue**: OAuth access/refresh tokens stored in plaintext in `user.attributes` JSONB field.
- **Action**: Encrypt tokens at rest using Fernet symmetric encryption with a key from env vars.

### 21. Password Reset Token Reuse
- **Severity**: Medium
- **Status**: TODO
- **File**: `backend/omoi_os/services/auth_service.py:486-489`
- **Issue**: Password reset tokens reusable within 1-hour window. Session invalidation query executes SELECT instead of DELETE.
- **Action**: Fix query to DELETE. Mark token as used immediately on first use.

---

## Week 2 — Hardening (TODO)

### 22. Sandbox Ownership Validation
- **Severity**: High
- **Status**: TODO
- **Issue**: No sandbox-to-user ownership check — any authenticated user can access other users' sandbox events by iterating sandbox IDs.
- **Action**: Add ownership validation on all sandbox endpoints.

### 23. Sandbox Resource Limits
- **Severity**: Medium
- **Status**: TODO
- **Issue**: Global CPU/memory/disk limits not enforced per-user or per-subscription tier. Single user can exhaust shared resources.
- **Action**: Implement per-user sandbox quotas tied to billing tier.

### 24. Environment Variable Injection in Sandbox Bootstrap
- **Severity**: Medium
- **Status**: TODO
- **File**: `backend/omoi_os/services/daytona_spawner.py:1895-1927`
- **Issue**: Unescaped environment variable values written to `.bashrc` in sandbox bootstrap, enabling command execution.
- **Action**: Properly escape values or use a safe serialization format.

### 25. Dependency CVE Audit
- **Severity**: Medium
- **Status**: TODO
- **Action**: Run `uv pip audit` (Python) and `pnpm audit` (JS). Fix or pin any packages with known CVEs.

### 26. Credential Rotation
- **Severity**: Medium
- **Status**: TODO
- **Issue**: Supabase credentials were committed to git history. Even though scrubbed from HEAD, they exist in history.
- **Action**: Rotate all previously-exposed Supabase credentials. Consider `git filter-branch` or BFG to remove from history if repo will go public.

### 27. Audit Logging
- **Severity**: Low
- **Status**: TODO
- **Action**: Log all authentication events (login, logout, failed login, password change, API key creation/revocation), permission changes, and admin actions to a dedicated audit table.

### 28. Database SSL/TLS
- **Severity**: High
- **Status**: TODO
- **File**: `backend/config/base.yaml:9`
- **Issue**: No `sslmode` parameter in database connection strings.
- **Action**: Add `sslmode=require` for production database connections (Railway PostgreSQL supports this).

### 29. API Key Prefix Exposure
- **Severity**: Low
- **Status**: TODO
- **File**: `backend/omoi_os/models/auth.py`, `backend/omoi_os/workers/claude_sandbox_worker.py:1650-1652`
- **Issue**: API key prefixes (16 chars) stored in plaintext and logged in worker output, reducing brute-force search space.
- **Action**: Reduce prefix to 4-8 chars. Remove key data from log output.

### 30. Stack Traces in Error Responses
- **Severity**: Medium
- **Status**: TODO
- **Files**: `backend/omoi_os/api/routes/sandbox.py`, `backend/omoi_os/api/routes/agents.py`
- **Issue**: `traceback.format_exc()` included in API error responses, exposing internal file paths and implementation details.
- **Action**: Return generic error messages in production. Log full tracebacks server-side only.

---

## Positive Security Findings

These are already done right:

- **No SQL injection** — all queries use SQLAlchemy ORM with parameterized queries
- **Proper password hashing** — bcrypt with strength validation (8 chars, uppercase, lowercase, digit)
- **Multi-tenant isolation** — `verify_organization_access`, `verify_project_access`, `verify_ticket_access` dependency injection
- **JWT architecture** — short-lived access tokens (15 min), separate refresh tokens (7 days), bearer header (not cookies)
- **Secret scanning in CI** — detect-secrets pre-commit hook and baseline
- **Sentry PII filtering** — configured to redact sensitive data
- **Proper .gitignore** — `.env` files excluded from version control
- **API response filtering** — `UserResponse` schema excludes `hashed_password` and sensitive fields
