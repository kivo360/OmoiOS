# Agent Workspace Platform — Learnings & Conventions

## Project Conventions (from AGENTS.md)

### Backend (Python)
- **Never use `metadata` or `registry` as SQLAlchemy column names** — reserved by SQLAlchemy
- **Always use `omoi_os.utils.datetime.utc_now()`** — timezone-aware datetimes
- **Use `structured_output()` for LLM calls** — never manually parse JSON
- **Settings in YAML, secrets in .env** — `OmoiBaseSettings` pattern
- **Two service initialization points**: `api/main.py` and `workers/orchestrator_worker.py`

### Frontend (TypeScript)
- **Check `components/ui/` before creating new primitives** — 40+ ShadCN components available
- **One hook per domain in `hooks/`** — follow `useProjects.ts` pattern
- **API calls through `lib/api/client.ts`** — never call `fetch` directly

## Security Requirements

### Encryption (Task 1)
- Fernet AES-256-GCM from `cryptography` library
- Key from `CREDENTIAL_ENCRYPTION_KEY` env var (32 bytes, hex-encoded)
- Transparent encrypt/decrypt at service layer
- No plaintext in logs, error messages, or API responses

### Credential Broker (Task 3)
- 3 binding kinds only: `bearer_secret`, `user_oauth`, `github_app`
- Fail-closed: deny access if Redis unavailable
- Versioned credentials for rotation safety
- Audit log every access

### Egress Proxy (Task 7)
- Go implementation, ≤300 LOC
- Hostname allowlist only (no IP, no regex)
- Blocks all outbound except allowlisted
- Prometheus metrics

## Feature Flags (Task 2)
All 6 flags default to `false`:
1. `sessions_api_v1`
2. `environments_v1`
3. `broker_enabled`
4. `egress_proxy_enabled`
5. `artifacts_unified_v1`
6. `webhooks_enabled`

## Database Patterns
- Alembic migrations required for all schema changes
- Test both `upgrade head` and `downgrade -1`
- Never use reserved words: `metadata`, `registry`

## SDK Patterns (Tasks 6, 9, 11)
- Thin REST wrappers only (no convenience methods)
- Python: `httpx` async client, Pydantic models
- TypeScript: native `fetch`, strict types, Node.js only
- No auto-retry logic (leave to user)

## Testing Requirements
- TDD: RED → GREEN → REFACTOR
- 80%+ coverage on new code
- Unit tests: `backend/tests/unit/`
- Integration tests: `backend/tests/integration/`
- Evidence saved to `.sisyphus/evidence/`

## Implementation: Feature Flags (Task 2) - COMPLETED

### Files Modified
- `backend/config/base.yaml` - Added 6 feature flags with default `false`
- `backend/omoi_os/config.py` - Added `FeatureFlagsSettings` class and helper functions
- `backend/tests/unit/test_feature_flags.py` - Created comprehensive test suite

### Feature Flags Added
1. `sessions_api_v1: false` - Sessions API v1
2. `environments_v1: false` - Environments v1
3. `broker_enabled: false` - Credential broker
4. `egress_proxy_enabled: false` - Egress proxy
5. `artifacts_unified_v1: false` - Unified artifacts v1
6. `webhooks_enabled: false` - Webhooks

### API Usage
```python
from omoi_os.config import is_feature_enabled, load_feature_flags_settings

# Check if feature is enabled
if is_feature_enabled("sessions_api_v1"):
    # Feature is enabled
    pass

# Or access settings directly
settings = load_feature_flags_settings()
if settings.broker_enabled:
    # Broker is enabled
    pass
```

### Pattern Followed
- Extended `OmoiBaseSettings` with `yaml_section="feature_flags"`
- Environment variable prefix: `FEATURE_`
- Cached settings via `@lru_cache` in `load_feature_flags_settings()`
- Helper function `is_feature_enabled(flag_name)` for safe flag checking
- All tests pass (8/8)

## Task 5: Unified Artifact Model - COMPLETED

### Files Created
- backend/omoi_os/models/artifact.py - Artifact SQLAlchemy model
- backend/omoi_os/services/artifact_service.py - Service with storage backend abstraction
- backend/omoi_os/api/routes/artifacts.py - API routes with feature flag guard
- backend/migrations/versions/063_add_artifacts.py - Alembic migration
- backend/tests/unit/test_artifact_service.py - Unit tests (TDD)

### API Endpoints
- POST /api/v1/artifacts/upload - Multipart file upload
- GET /api/v1/artifacts - List artifacts by workspace
- GET /api/v1/artifacts/{id} - Get metadata
- GET /api/v1/artifacts/{id}/download - Stream download
- DELETE /api/v1/artifacts/{id} - Delete artifact

### Storage Backends
- LocalFilesystemBackend (v1) - Stores files at {base_dir}/{workspace_id}/{artifact_id}/{filename}
- S3Backend (interface only) - Raises NotImplementedError

### Test Results
- 12/12 storage backend tests PASSED
- 9/9 LocalFilesystemBackend tests PASSED
- 2/2 singleton tests PASSED
- 1/1 S3Backend interface test PASSED

### Pattern Compliance
- Uses artifact_metadata (not metadata - SQLAlchemy reserved word)
- Uses utc_now() for timezone-aware datetimes
- SQLAlchemy 2.0 Mapped[] + mapped_column() pattern
- Service singleton pattern with get_artifact_service()
- Feature flag guard on all routes


## Task 6: SDK Scaffolding - Learnings (2025-04-23)

### Python SDK Patterns
- Used Pydantic v2 for type definitions with proper Field descriptions
- Abstract base class with @abstractmethod enforces client interface
- Mock client stores data in Maps for efficient lookups
- Fixtures initialized in constructor for consistent test state
- UUID generation using uuid.uuid4().hex[:8] for readable IDs

### TypeScript SDK Patterns
- TypeScript strict mode with noUncheckedIndexedAccess catches edge cases
- Using `type` keyword for type-only imports reduces bundle size
- Maps provide better type safety than plain objects for storage
- Buffer type for binary data (Node.js only, no browser support)
- Import paths use .js extension for ES module compatibility

### Build Configuration
- Python: hatchling build backend works well with uv
- TypeScript: ES2022 + ESNext modules for modern Node.js
- Vitest for fast testing with built-in type checking
- pytest-asyncio for async test support (future-proofing)

### Type Definitions
- Credentials: 3 binding kinds (bearer_secret, user_oauth, github_app)
- Environments: Immutable versions with variable types (string, secret, json)
- Artifacts: Checksum validation, multi-backend support (local, s3)
- Webhooks: Event types, subscription management, delivery tracking
- Workspaces: Settings with egress allowlist and binding kind restrictions

### Testing Strategy
- 26 tests per SDK covering all CRUD operations
- Error cases verified (NotFoundError on invalid IDs)
- Type validation through runtime assertions
- Mock data fixtures provide realistic test scenarios

## Task 7: Go Egress Proxy - Learnings (2026-04-24)

### Implementation Patterns
- Created standalone `egress-proxy/` Go module with no third-party dependencies for a minimal static binary and scratch Docker image.
- HTTP proxy requests use absolute-form URLs and `http.Transport{Proxy:nil}` so the proxy never loops through environment proxy settings.
- HTTPS support uses standard CONNECT authority filtering before TCP tunneling; TLS is not terminated, preserving end-to-end encryption.
- Allowlist supports exact lowercase hostnames and `*.domain` suffix entries; empty allowlist fails closed.
- `/health` and `/metrics` are served only for direct origin-form requests, while proxy traffic is counted separately.

### Verification Notes
- `go test ./...` passes.
- `go build -o /tmp/egress-proxy-check .` passes.
- QA evidence saved at `.sisyphus/evidence/task-7-egress-filter.txt` shows blocked `evil.example.com`, allowed `api.github.com`, health, and metrics.
- Dockerfile is multi-stage and scratch-based; local Docker build could not be completed because the Docker daemon was unavailable in the execution environment.

## Task 9: Python SDK Implementation - Learnings (2026-04-24)

### Architecture
- Implemented `AsyncOmoiOSClient` using `httpx.AsyncClient` for async HTTP requests.
- Preserved `OmoiOSClient` abstract base class for backwards compatibility with `MockOmoiOSClient`.
- Resource-based design: `client.credentials.list()`, `client.environments.get()`, etc.
- Auth modes: `X-API-Key` header for API keys, `Authorization: Bearer` for JWT tokens.

### Error Handling
- Maps HTTP status codes to SDK exceptions: 401→AuthError, 404→NotFoundError, 400/422→ValidationError, 5xx→ServerError.
- Errors include detail messages parsed from JSON response bodies.

### Type Updates
- Added `config: Optional[dict]` and `version: int` to `Credential` model.
- Added `config: Optional[dict]` to `CreateCredentialRequest`.
- Made `workspace_id` required in `CreateCredentialRequest` (was optional in mock).
- Made `org_id` required in `CreateEnvironmentRequest` (was optional in mock).
- Added `UpdateWorkspaceSettingsRequest` for workspace settings updates.

### Resource Modules
- `omoios/resources/credentials.py`: list, get, create, delete
- `omoios/resources/environments.py`: list, get, create, create_version
- `omoios/resources/artifacts.py`: upload, list, get, download, delete
- `omoios/resources/webhooks.py`: list, create, delete, list_deliveries
- `omoios/resources/workspaces.py`: get_settings, update_settings

### Testing
- Unit tests (`tests/test_client.py`): 26 tests with mocked HTTP via `unittest.mock.AsyncMock`.
- Mock tests (`tests/test_mock_client.py`): 26 tests for mock client compatibility.
- Integration tests (`tests/test_integration.py`): 16 tests that skip if API unavailable.
- All 52 unit tests pass. Integration tests skip when backend is not running.

### API Endpoints Covered
- Credentials: `POST/GET/DELETE /api/v1/credentials`, `GET /api/v1/credentials/{id}`
- Environments: `POST/GET /api/v1/environments`, `GET /api/v1/environments/{id}`, `POST /api/v1/environments/{id}/versions`
- Artifacts: `POST /api/v1/artifacts/upload`, `GET /api/v1/artifacts`, `GET/DELETE /api/v1/artifacts/{id}`, `GET /api/v1/artifacts/{id}/download`
- Webhooks: `POST/GET /api/v1/webhooks`, `DELETE /api/v1/webhooks/{id}`, `GET /api/v1/webhooks/{id}/deliveries`
- Workspaces: `GET /api/v1/workspaces/{id}/settings`, `PUT /api/v1/workspaces/{id}/settings`

## Task 11: TypeScript SDK Implementation - Learnings (2026-04-24)

### Architecture
- Replaced abstract `OmoiOSClient` with concrete fetch-based HTTP client using native `fetch` (Node.js 18+).
- Resource-based design matching Python SDK: `client.credentials.list()`, `client.environments.get()`, etc.
- Auth modes: `X-API-Key` header for API keys, `Authorization: Bearer` for JWT tokens.
- Constructor requires `{ baseUrl, apiKey? | jwtToken? }` and strips trailing slashes.
- Request timeout via `AbortController` with configurable milliseconds (default 30000).

### Error Handling
- Maps HTTP status codes to SDK exceptions: 401→AuthError, 404→NotFoundError, 400/422→ValidationError, 5xx→ServerError.
- `_handleErrors` called automatically after every `_request`; throws on non-2xx status.

### Type Updates
- Added `GetEnvironmentResult` interface to `types.ts` (return type for `environments.get()`).
- Added `UpdateWorkspaceSettingsRequest` interface to `types.ts`.
- Added `config?: Record<string, unknown> | null` and `version?: number` to `Credential`.
- Made `storage_path` optional on `Artifact` (backend `ArtifactResponse` omits it).

### Resource Modules
- `src/resources/credentials.ts`: list, get, create, delete
- `src/resources/environments.ts`: list, get, create, create_version
- `src/resources/artifacts.ts`: upload (FormData), list, get, download (Buffer), delete
- `src/resources/webhooks.ts`: list, get, create, update, delete, list_deliveries, test
- `src/resources/workspaces.ts`: get_settings, update_settings

### Mock Client
- Rewrote `MockOmoiOSClient` as standalone class (no longer extends `OmoiOSClient`).
- Prevents constructor signature coupling between mock and real client.
- Uses in-memory Maps for all resource types.

### Testing
- Integration tests (`tests/integration.test.ts`): 34 tests using local Node.js `http.createServer` mock.
- Tests cover: initialization, auth headers, all resource methods, error handling (401/404/400/500/422), timeout abort.
- Mock client tests (`tests/mockClient.test.ts`): 26 tests unchanged, still passing.
- All 60 tests pass. TypeScript `strict` mode + `noUnusedLocals` + `noUnusedParameters` enforced.

### Build Notes
- `tsconfig.json`: `moduleResolution: Bundler` requires `.js` extensions in imports.
- `Buffer` must be wrapped as `new Uint8Array(buffer)` before passing to `Blob` constructor to satisfy strict TypeScript types.
- `FormData` from `undici` (Node.js 18+) works natively; no polyfill needed.
- `package.json` uses `"type": "module"` with ES2022 + ESNext output.

## 2026-04-23 — Workspace isolation service

- Workspace isolation can be layered through `Task.execution_config` without storing decrypted secrets in JSONB: validate IDs at queue time, then resolve credentials/environment/proxy at sandbox spawn time.
- Existing credential and environment services are synchronous DB services and can be composed directly by a workspace isolation service when tests inject shared `DatabaseService` instances.

## 2026-04-24 — Credential alias resolution

- `environment_versions.credentials` is the source of truth for sandbox alias dispatch; aliases resolve through the pinned `SandboxSession.environment_version_id`.
- `credential_access_logs` must include `sandbox_session_id` in the SQLAlchemy model as well as the migration, otherwise audit writes cannot attach session provenance through ORM instances.
- Near-expiry `user_oauth` resolution should fail closed unless a provider refresh adapter is supplied; tests can monkeypatch `_refresh_user_oauth` to verify refresh persistence without network calls.
- Local credential broker DB tests require PostgreSQL on `localhost:15432`; Docker was unavailable in this session, so evidence records infra-blocked pytest rather than a code failure.
## 2026-04-24 — Runtime broker route implementation

- Runtime broker routes should stay separate from admin credential CRUD: mount under `/broker`, keep `/api/v1/credentials` unchanged, and put the feature-flag guard on the runtime route surface.
- `SandboxSessionService` is async-session scoped and returns plaintext `sess_tok_...` only from `create_session`; for sandbox handoff, use short-lived Redis transport rather than storing plaintext in task execution config.
- `CredentialBrokerService.resolve_alias()` already returns the required per-kind credential payload and audits alias access; route code only needs to map `UnknownAliasError` to 404 and avoid logging payload values.
