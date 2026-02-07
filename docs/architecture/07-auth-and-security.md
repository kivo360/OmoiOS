# Part 7: Authentication & Security

> Summary doc — see linked design docs for full details.

## Overview

OmoiOS uses **self-hosted JWT authentication** with bcrypt password hashing, refresh tokens, and role-based access control. The codebase includes a Supabase auth design doc, but the actual implementation is self-hosted via `auth_service.py`.

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Email/password registration | Implemented | bcrypt hashing via `passlib` |
| JWT access tokens | Implemented | 15-minute expiry, `python-jose` |
| Refresh tokens | Implemented | 7-day expiry |
| Email verification | Partial | Token generation works, email sending is TODO |
| Password reset | Partial | Token generation works, email sending is TODO |
| OAuth (GitHub/Google) | Implemented | OAuth routes in `oauth.py` |
| API keys (agent-scoped) | Implemented | For sandbox/automation access |
| Role-based access control | Implemented | Organization-level roles |

## Authentication Flow

```
┌──────────┐     POST /auth/login      ┌──────────────┐
│  Client  │ ──────────────────────────→│  AuthService  │
│          │                            │              │
│          │←── access_token (15min) ──│  bcrypt hash │
│          │←── refresh_token (7day) ──│  JWT (jose)  │
└──────────┘                            └──────────────┘
      │
      │  Authorization: Bearer <token>
      ▼
┌──────────────────┐
│  FastAPI Middleware│
│  get_current_user │──→ JWT verification → User context injection
└──────────────────┘
```

## Token Types

| Token | Lifetime | Purpose |
|-------|----------|---------|
| **Access Token** | 15 minutes | API request authentication |
| **Refresh Token** | 7 days | Access token renewal |
| **Email Verification** | 24 hours | Account activation |
| **Password Reset** | 1 hour | Password recovery |
| **API Key** | Configurable | Agent/automation access |

## Role-Based Access Control

Organization-level roles control permissions:

| Role | Capabilities |
|------|-------------|
| `owner` | Full access, billing, member management, delete org |
| `admin` | Member management, project CRUD, settings |
| `member` | Project access, task execution, spec creation |
| `viewer` | Read-only access to projects and dashboards |

## Key Files

| File | Purpose |
|------|---------|
| `backend/omoi_os/services/auth_service.py` | Core auth logic: registration, login, JWT, sessions |
| `backend/omoi_os/api/routes/auth.py` | Auth API endpoints (login, register, refresh, verify) |
| `backend/omoi_os/api/routes/oauth.py` | OAuth flow (GitHub, Google) |
| `backend/omoi_os/models/auth.py` | User model with hashed_password, is_verified, is_active |
| `backend/omoi_os/models/user_credentials.py` | Stored credentials for integrations |

## Security Considerations

- Passwords hashed with bcrypt (via `passlib`)
- JWT signed with configurable secret key
- API keys scoped to specific agent/project contexts
- Waitlist status checked during registration flow
- Session tracking with `last_login_at` timestamps

## Known TODOs

- `auth.py:199` — Track logout in audit log
- `auth.py:284` — Send email with reset link (email sending not implemented)

## Detailed Documentation

| Document | Content |
|----------|---------|
| [Auth System Plan](../design/auth/auth_system_plan.md) | Full auth design including OAuth, API keys, RBAC details |
| [Supabase Auth Integration](../design/auth/supabase_auth_integration.md) | Alternative design (not implemented) — Supabase-based auth with database replication |
