# Agent Workspace Platform — Architectural Decisions

## Decisions Log

### Encryption Strategy (Task 1)
- **Decision**: Use Fernet (AES-256-GCM) from `cryptography` library
- **Rationale**: Industry standard, Python-native, authenticated encryption
- **Key Management**: Env var `CREDENTIAL_ENCRYPTION_KEY`, 32 bytes hex-encoded
- **Migration**: Add `encrypted_value` column, backfill, remove `value` in follow-up

### Feature Flag Granularity (Task 2)
- **Decision**: Global flags only for v1, per-org deferred
- **Rationale**: Simpler deployment, can add per-org later without breaking changes
- **Default**: All OFF — explicit opt-in required

### Credential Broker Design (Task 3)
- **Decision**: 3 binding kinds only, DB-only storage (no Redis cache v1)
- **Rationale**: Fail-closed security, simpler implementation
- **Versioning**: Sessions pin to credential version for rotation safety

### Egress Proxy Architecture (Task 7)
- **Decision**: Shared service model (not sidecar), Go implementation
- **Rationale**: ~300 LOC, simpler ops, Daytona sandboxes handle container isolation
- **Scope**: HTTP/HTTPS only, hostname allowlists only

### Environment Immutability (Task 4)
- **Decision**: Immutable versions, create new version to change
- **Rationale**: Reproducible builds, audit trail, safe rollback
- **Scope**: Org-level only for v1 (no project-scoped)

### SDK Scope (Tasks 6, 9, 11)
- **Decision**: Thin REST wrappers only, no convenience methods
- **Rationale**: v1.0 scope control, clear API contract, user controls retry
- **Platforms**: Python + TypeScript (Node.js only, no browser)

### Session Aliases (Task 12)
- **Decision**: Route aliases only, no DB column renames
- **Rationale**: Backward compatibility, no migration risk
- **Deprecation**: `X-Deprecated` header on all `/sessions` responses

## 2026-04-23 — Workspace isolation boundaries

- Store only non-secret workspace isolation settings (`storage_path`, `environment_id`, `egress_proxy_config`) in `workspace_settings`; decrypted environment values and credentials are resolved only at sandbox spawn time.
- Require explicit `credential_binding_ids` for session credential injection to avoid implicitly injecting every workspace credential.
## 2026-04-24 — Broker session token handoff

- Chose Redis-backed ephemeral handoff (`broker:session-token:{task_id}` with short TTL) for passing newly minted broker session tokens from `POST /api/v1/sessions` to the Daytona spawner. This avoids PostgreSQL plaintext storage and avoids putting secrets into `execution_config`, which is logged in existing orchestrator paths.
- Revoke route uses existing user JWT auth (`get_current_user`) plus `is_super_admin`; session bearer tokens are therefore rejected before authorization and cannot revoke themselves.
