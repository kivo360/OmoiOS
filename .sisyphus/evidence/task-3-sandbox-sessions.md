# Task 3: sandbox_sessions table + SandboxSessionService

## Deliverables

| File | Status |
|------|--------|
| `backend/migrations/versions/069_add_sandbox_sessions.py` | Created |
| `backend/omoi_os/models/sandbox_session.py` | Created |
| `backend/omoi_os/services/sandbox_session_service.py` | Created |
| `backend/tests/unit/services/test_sandbox_session_service.py` | Created |
| `backend/omoi_os/models/__init__.py` | Updated (SandboxSession registered) |
| `credential_access_logs.sandbox_session_id` FK | Added in migration 069 |

## Test Results

```
19 passed in 0.74s
```

### Test Coverage

- `TestTokenHelpers` (4 tests): mint prefix, length, SHA-256 hash, prefix extraction
- `TestCreateSession` (6 tests): returns tuple, stores hash not plaintext, prefix correctness, default TTL, custom TTL, DB commit
- `TestVerifySessionToken` (5 tests): valid token, expired, revoked, unknown, last_used_at update
- `TestRevoke` (2 tests): sets revoked_at, targets correct ID
- `TestSecurityNoPlaintext` (2 tests): hash column != plaintext, prefix too short to reconstruct

## Security Verification

- No plaintext token stored in any column
- `session_token_hash` = SHA-256 hex digest (64 chars)
- `session_token_prefix` = first 8 chars only (insufficient to reconstruct)
- Token format: `sess_tok_` + 40 random hex chars = 49 total

## LSP Diagnostics

All 4 files: clean (0 errors, 0 warnings)
