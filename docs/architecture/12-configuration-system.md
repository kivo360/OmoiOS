# Part 12: Configuration System

> Summary doc — see linked design doc for full details.

## Overview

OmoiOS uses a **dual configuration system**: YAML files for application settings (version-controlled) and `.env` files for secrets (gitignored). All config classes extend a custom `OmoiBaseSettings` base with Pydantic validation.

## Configuration Hierarchy

```
Priority (highest to lowest):
  1. Constructor arguments (init values)
  2. Environment variables (OMOI_SECTION_KEY format)
  3. YAML file defaults (config/{environment}.yaml)
```

## YAML Structure

```
config/
├── base.yaml          # Default settings (always loaded)
├── local.yaml         # Local development overrides
├── staging.yaml       # Staging environment
├── production.yaml    # Production environment
└── test.yaml          # Test environment (fast intervals, mocks)
```

### YAML Sections

| Section | Purpose | Example Settings |
|---------|---------|-----------------|
| `task_queue` | Task polling and assignment | `poll_interval`, `max_concurrent`, `priority_weights` |
| `monitoring` | Guardian/Conductor intervals | `guardian_interval`, `conductor_interval`, `health_check_interval` |
| `auth` | JWT configuration | `access_token_expire_minutes`, `refresh_token_expire_days` |
| `features` | Feature flags | `enable_discovery`, `enable_guardian`, `enable_billing` |
| `daytona` | Sandbox configuration | `memory_gb`, `cpu`, `disk_gb`, `snapshot` |

## Settings Pattern

All configuration classes follow this pattern:

```python
from omoi_os.config import OmoiBaseSettings

class MonitoringSettings(OmoiBaseSettings):
    """Monitoring loop configuration."""

    yaml_section: str = "monitoring"
    env_prefix: str = "OMOI_MONITORING_"

    guardian_interval: int = 60        # seconds
    conductor_interval: int = 300      # seconds
    health_check_interval: int = 30    # seconds
    alignment_threshold: float = 0.7

# Singleton factory with caching
@lru_cache
def get_monitoring_settings() -> MonitoringSettings:
    return MonitoringSettings()
```

## Environment Variables

Secrets go in `.env` (never committed):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:15432/omoios

# Redis
REDIS_URL=redis://localhost:16379

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
DAYTONA_API_KEY=...
GITHUB_PAT=ghp_...
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...

# JWT
JWT_SECRET_KEY=...
```

## Test Configuration

`config/test.yaml` uses fast intervals and disables external integrations:

```yaml
monitoring:
  guardian_interval: 1      # 1s instead of 60s
  conductor_interval: 1     # 1s instead of 300s

features:
  enable_daytona: false     # No real sandbox creation
  enable_stripe: false      # No real billing calls
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/omoi_os/config/` | All YAML config files |
| `backend/omoi_os/config.py` | OmoiBaseSettings base class, loaders |
| `.env` | Secrets (gitignored) |
| `.env.test` | Test database URLs |

## Detailed Documentation

| Document | Content |
|----------|---------|
| [Configuration Architecture](configuration/configuration_architecture.md) | Full configuration design (~960 lines) — YAML loading, settings pattern, environment handling |
