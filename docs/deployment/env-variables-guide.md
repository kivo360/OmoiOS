# Environment Variables Deployment Guide

This guide explains which environment variables should be **shared** across services vs **service-specific** when deploying to Vercel (frontend) and Railway (backend).

## Quick Reference

### Shared Variables (Set Once, Use Everywhere)

| Variable | Used By | Platform | Description |
|----------|---------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Frontend, Backend | Both | API URL (`https://api.omoios.dev`) |
| `NEXT_PUBLIC_SITE_URL` | Frontend, Backend | Both | Site URL (`https://omoios.dev`) |
| `AUTH_JWT_SECRET_KEY` | API, Workers | Railway | JWT signing key |
| `AUTH_GITHUB_CLIENT_ID` | API | Railway | GitHub OAuth app ID |
| `AUTH_GITHUB_CLIENT_SECRET` | API | Railway | GitHub OAuth secret |
| `AUTH_GOOGLE_CLIENT_ID` | API | Railway | Google OAuth app ID |
| `AUTH_GOOGLE_CLIENT_SECRET` | API | Railway | Google OAuth secret |
| `AUTH_OAUTH_REDIRECT_URI` | API | Railway | OAuth callback URL |
| `DATABASE_URL` | API, Workers | Railway | PostgreSQL connection |
| `REDIS_URL` | API, Workers | Railway | Redis connection |
| `LLM_API_KEY` | API, Workers | Railway | Primary LLM API key |
| `LLM_FIREWORKS_API_KEY` | API, Workers | Railway | Fireworks AI key |
| `ANTHROPIC_API_KEY` | API, Workers | Railway | Anthropic API key |
| `GITHUB_TOKEN` | API, Workers | Railway | GitHub personal access token |
| `DAYTONA_API_KEY` | Workers | Railway | Daytona sandbox API key |
| `SENTRY_ORG` | Frontend, Backend | Both | Sentry organization slug |
| `SENTRY_AUTH_TOKEN` | Frontend, Backend | Both | Sentry auth for source maps |
| `POSTHOG_API_KEY` / `NEXT_PUBLIC_POSTHOG_KEY` | All | Both | PostHog project key |

### Service-Specific Variables

| Variable | Service | Platform | Description |
|----------|---------|----------|-------------|
| `SENTRY_PROJECT` | Each service | Both | Sentry project slug (different per service) |
| `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` | Each service | Both | Sentry DSN (different per project) |
| `OMOIOS_ENV` | API, Workers | Railway | Environment name |
| `WORKER_CONCURRENCY` | Workers only | Railway | Number of concurrent workers |
| `DAYTONA_SANDBOX_EXECUTION` | Workers only | Railway | Enable sandbox mode |

---

## Vercel (Frontend) Setup

### Step 1: Shared Variables
In Vercel project settings, add these shared variables:

```bash
# URLs
NEXT_PUBLIC_API_URL=https://api.omoios.dev
NEXT_PUBLIC_SITE_URL=https://omoios.dev

# Sentry (shared org, different project)
SENTRY_ORG=your-sentry-org
SENTRY_AUTH_TOKEN=your-sentry-auth-token

# PostHog (same project for frontend & backend)
NEXT_PUBLIC_POSTHOG_KEY=phc_your_key
NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com
```

### Step 2: Frontend-Specific Variables
```bash
# Sentry frontend project
SENTRY_PROJECT=omoios-frontend
NEXT_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
NEXT_PUBLIC_SENTRY_ENVIRONMENT=production
```

---

## Railway (Backend) Setup

### Step 1: Create Shared Variables Group
In Railway, create a shared variable group or set these on all services:

```bash
# URLs
NEXT_PUBLIC_API_URL=https://api.omoios.dev
NEXT_PUBLIC_SITE_URL=https://omoios.dev
AUTH_OAUTH_REDIRECT_URI=https://omoios.dev/auth/callback

# Database (Railway plugin provides this)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (Railway plugin provides this)
REDIS_URL=${{Redis.REDIS_URL}}

# Auth
AUTH_JWT_SECRET_KEY=your-jwt-secret

# OAuth
AUTH_GITHUB_CLIENT_ID=your-github-client-id
AUTH_GITHUB_CLIENT_SECRET=your-github-client-secret
AUTH_GOOGLE_CLIENT_ID=your-google-client-id
AUTH_GOOGLE_CLIENT_SECRET=your-google-client-secret

# LLM
LLM_API_KEY=your-fireworks-key
LLM_FIREWORKS_API_KEY=your-fireworks-key
ANTHROPIC_API_KEY=your-anthropic-key

# Integrations
GITHUB_TOKEN=your-github-pat
DAYTONA_API_KEY=your-daytona-key

# Observability (shared)
SENTRY_ENVIRONMENT=production
POSTHOG_API_KEY=phc_your_key
POSTHOG_HOST=https://app.posthog.com
```

### Step 2: API Service Variables
```bash
OMOIOS_ENV=production
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx-api
```

### Step 3: Worker Service Variables
```bash
OMOIOS_ENV=production
WORKER_CONCURRENCY=2
DAYTONA_SANDBOX_EXECUTION=false
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx-worker
```

---

## Variable Categories Explained

### 🔗 URL Configuration
- **Shared**: Same URLs used by all services to communicate
- These define where services are located

### 🔐 Authentication
- **Shared**: JWT secret must be identical across API and workers for token validation
- OAuth credentials are shared since it's the same OAuth apps

### 🗄️ Infrastructure
- **Shared**: Database and Redis are single instances shared by all backend services
- Railway provides these through plugins

### 🤖 AI/LLM
- **Shared**: Same API keys for all services that need LLM access
- Keeps billing consolidated

### 📊 Observability
- **Mixed**:
  - Sentry org and auth token are shared
  - Sentry DSN is per-project (so errors are categorized)
  - PostHog key is shared (same analytics project)

### ⚙️ Service Configuration
- **Service-specific**: Worker concurrency, sandbox mode, etc.
- Each service may need different operational settings

---

## Generating Secrets

```bash
# Generate JWT secret
openssl rand -hex 32

# Generate secure random string
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Checklist Before Deployment

- [ ] All shared variables set in Vercel project
- [ ] All shared variables set in Railway (or as shared group)
- [ ] Sentry projects created for frontend and backend
- [ ] PostHog project created
- [ ] OAuth apps created (GitHub, Google)
- [ ] Database and Redis provisioned in Railway
- [ ] JWT secret generated and set
- [ ] API keys obtained (Fireworks, Anthropic, Daytona)
