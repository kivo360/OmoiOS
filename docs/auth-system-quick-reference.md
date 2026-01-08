# User Authentication System - Quick Reference Guide

## Overview
This is a quick reference guide for implementing the User Authentication System based on the detailed specification in `user-authentication-system-spec.md`.

## Tech Stack
| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI |
| Database | Supabase (PostgreSQL) |
| Authentication | JWT (access + refresh tokens) |
| Password Hashing | bcrypt (12 rounds) |
| Email Service | SMTP or SendGrid |

## Quick API Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login and get tokens | No |
| POST | `/api/v1/auth/logout` | Logout current session | Yes |
| POST | `/api/v1/auth/logout-all` | Logout all devices | Yes |
| POST | `/api/v1/auth/refresh` | Refresh access token | No (refresh token) |
| POST | `/api/v1/auth/verify-email` | Verify email address | No |
| POST | `/api/v1/auth/request-password-reset` | Request password reset | No |
| POST | `/api/v1/auth/reset-password` | Reset password with token | No |
| POST | `/api/v1/auth/change-password` | Change password (authenticated) | Yes |
| GET | `/api/v1/auth/me` | Get current user profile | Yes |
| GET | `/api/v1/auth/sessions` | Get active sessions | Yes |
| DELETE | `/api/v1/auth/sessions/{id}` | Revoke specific session | Yes |

## Database Schema Quick Reference

### users Table
```sql
- id: UUID (PK)
- email: VARCHAR(255) UNIQUE NOT NULL
- password_hash: VARCHAR(255) NOT NULL
- full_name: VARCHAR(255)
- is_verified: BOOLEAN DEFAULT FALSE
- is_active: BOOLEAN DEFAULT TRUE
- last_login_at: TIMESTAMP
- login_count: INTEGER DEFAULT 0
- failed_login_attempts: INTEGER DEFAULT 0
- locked_until: TIMESTAMP
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

### refresh_tokens Table
```sql
- id: UUID (PK)
- user_id: UUID (FK → users)
- token_hash: VARCHAR(255) UNIQUE NOT NULL
- device_info: TEXT
- ip_address: INET
- user_agent: TEXT
- expires_at: TIMESTAMP NOT NULL
- revoked_at: TIMESTAMP
- created_at: TIMESTAMP
```

### verification_tokens Table
```sql
- id: UUID (PK)
- user_id: UUID (FK → users)
- token: VARCHAR(255) UNIQUE NOT NULL
- token_type: VARCHAR(50) -- 'email_verification', 'password_reset'
- expires_at: TIMESTAMP NOT NULL
- used_at: TIMESTAMP
- created_at: TIMESTAMP
```

## Security Requirements at a Glance

### Password Requirements
- **Minimum length:** 12 characters
- **Must contain:** Uppercase, lowercase, digit, special character
- **Must not:** Be in common passwords, contain email username

### Token Expiration
| Token Type | Expiration |
|------------|------------|
| Access Token | 15 minutes |
| Refresh Token | 7 days |
| Verification Token | 24 hours |
| Password Reset Token | 1 hour |

### Rate Limits
| Endpoint | Limit | Window |
|----------|-------|--------|
| Login | 5 attempts | 15 min (per IP) |
| Registration | 3 attempts | 1 hour (per IP) |
| Password Reset | 3 attempts | 1 hour (per email) |
| Token Refresh | 10 attempts | 1 minute (per user) |

### Account Lockout
- **Lockout threshold:** 5 failed login attempts
- **Lockout duration:** 15 minutes
- **Notification:** Email sent to user on lockout

## Environment Variables Template

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-min-32-chars-change-this
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Database (Supabase)
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourapp.com
EMAIL_FROM_NAME="Your App"

# Security
BCRYPT_ROUNDS=12
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_MINUTES=15
PASSWORD_MIN_LENGTH=12

# Rate Limiting (Redis)
RATE_LIMIT_ENABLED=true
REDIS_URL=redis://localhost:6379

# Frontend
FRONTEND_URL=http://localhost:3000
```

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── dependencies.py       # Auth dependencies (get_current_user)
│   │   └── v1/
│   │       └── auth/
│   │           ├── __init__.py
│   │           ├── router.py     # Auth endpoints
│   │           └── schemas.py    # Request/Response schemas
│   ├── core/
│   │   ├── config.py             # Settings
│   │   └── security.py           # JWT, password hashing
│   ├── models/
│   │   └── user.py               # Database models
│   ├── schemas/
│   │   └── user.py               # Pydantic schemas
│   ├── services/
│   │   ├── auth_service.py       # Business logic
│   │   └── email_service.py      # Email sending
│   └── utils/
│       └── rate_limit.py         # Rate limiting
```

## Implementation Checklist

### Phase 1: Foundation
- [ ] Set up Supabase database tables
- [ ] Configure Row Level Security (RLS)
- [ ] Create project structure
- [ ] Implement password hashing (bcrypt)
- [ ] Implement JWT utilities
- [ ] Configure environment variables

### Phase 2: Core Auth
- [ ] Implement registration endpoint
- [ ] Implement email verification endpoint
- [ ] Implement login endpoint
- [ ] Implement token refresh endpoint
- [ ] Set up email templates

### Phase 3: Session Management
- [ ] Implement logout endpoint
- [ ] Implement logout-all endpoint
- [ ] Implement active sessions endpoint
- [ ] Implement revoke session endpoint

### Phase 4: Password Management
- [ ] Implement password reset request
- [ ] Implement password reset confirmation
- [ ] Implement password change endpoint

### Phase 5: Security
- [ ] Implement rate limiting
- [ ] Implement account lockout
- [ ] Add audit logging
- [ ] Configure security headers
- [ ] Set up CORS

### Phase 6: Testing
- [ ] Unit tests for utilities
- [ ] Integration tests for endpoints
- [ ] Security tests
- [ ] Load testing

### Phase 7: Frontend Integration
- [ ] Update AuthProvider context
- [ ] Implement token refresh logic
- [ ] Create auth forms (login, register, etc.)
- [ ] Create session management UI

## Common Patterns

### Protected Endpoint Pattern
```python
from fastapi import Depends, APIRouter
from app.api.dependencies import get_current_user

@router.get("/protected")
async def protected_endpoint(
    current_user = Depends(get_current_user)
):
    return {"user_id": current_user.id, "email": current_user.email}
```

### Error Response Pattern
```python
from fastapi import HTTPException, status

# Invalid credentials
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid email or password"
)

# Validation error
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Password does not meet requirements"
)

# Rate limit exceeded
raise HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too many attempts. Please try again later."
)
```

## Security Best Practices

1. **Never log passwords or tokens**
2. **Always use HTTPS in production**
3. **Validate all input**
4. **Use parameterized queries**
5. **Implement rate limiting**
6. **Rotate refresh tokens**
7. **Set short access token expiration**
8. **Monitor audit logs**
9. **Keep dependencies updated**
10. **Follow OWASP guidelines**

## Testing Commands

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123!","full_name":"John Doe"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123!"}'

# Get Current User
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Logout
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Email Templates Location

Create email templates in:
```
backend/app/templates/emails/
├── verification.html
├── password_reset.html
├── password_change_confirmation.html
└── security_alert.html
```

## Monitoring & Logging

Log these events:
- User registration
- Email verification
- Login (success/failure)
- Logout
- Token refresh
- Password reset request
- Password change
- Account lockout
- Security events

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| Token invalid immediately | Clock skew | Check system time sync |
| Email not sent | SMTP config | Verify SMTP credentials |
| Rate limit too strict | Development | Disable rate limiting in dev |
| Database connection error | Supabase downtime | Check Supabase status |
| Tests failing | Database state | Clean test database |

---

**For detailed requirements, see:** `user-authentication-system-spec.md`
