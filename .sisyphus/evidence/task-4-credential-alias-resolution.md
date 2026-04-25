# Task 4 Evidence — Credential Alias Resolution

## Changes

- Added `CredentialBrokerService.resolve_alias(session, alias)` with per-kind dispatch for `bearer_secret`, `user_oauth`, and `github_app`.
- Added `UnknownAliasError` and `UnsupportedBindingKindError` for route-layer mapping.
- Added sandbox-scoped audit logging through `credential_access_logs.sandbox_session_id`.
- Updated `CredentialAccessLog` model to match migration `069_add_sandbox_sessions.py`.
- Extended `backend/tests/unit/test_credential_broker.py` for bearer secret resolution, OAuth refresh path, GitHub App token minting seam, unknown aliases, and audit logging.

## Verification

- `uv run ruff format omoi_os/services/credential_broker.py omoi_os/models/credential_access_log.py tests/unit/test_credential_broker.py && uv run ruff check omoi_os/services/credential_broker.py omoi_os/models/credential_access_log.py tests/unit/test_credential_broker.py --fix` — passed.
- LSP diagnostics on changed files — clean.
- `uv run python -m py_compile omoi_os/services/credential_broker.py omoi_os/models/credential_access_log.py tests/unit/test_credential_broker.py` — passed.
- `uv run pytest tests/unit/test_credential_broker.py -q` — blocked by local PostgreSQL dependency: `connection refused` on `localhost:15432`.
- `docker-compose up -d postgres` — blocked because Docker daemon is not running.

## Notes

- No plaintext credential values are written to logs or audit metadata.
- OAuth refresh is intentionally provider-adapter driven: near-expiry tokens fail closed if no refresh adapter overrides `_refresh_user_oauth`.
