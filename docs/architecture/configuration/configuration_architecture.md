# Configuration Architecture: YAML + Environment Variables

**Created**: 2025-11-20
**Status**: Architecture Standard
**Purpose**: Define clear separation between YAML configuration and environment variables

---

## Configuration Philosophy

### ✅ Use YAML For: Application Configuration
- **What**: Business logic settings, feature flags, thresholds, timeouts
- **Why**: Version controlled, environment-specific, mergeable, reviewable
- **Examples**: Task queue weights, monitoring intervals, approval timeouts, phase configurations

### ✅ Use .env For: Environment Variables (Secrets & URLs Only)
- **What**: Sensitive data, deployment-specific values
- **Why**: Never committed to git, different per environment, secret management
- **Examples**: API keys, database passwords, JWT secrets, service URLs

---

## Directory Structure

```
config/
├── base.yaml                        # Base configuration (all environments)
├── local.yaml                       # Local development overrides
├── staging.yaml                     # Staging environment overrides
├── production.yaml                  # Production environment overrides
├── test.yaml                        # Test environment configuration
│
├── alert_rules/                     # Alert configurations
│   ├── agent_health.yaml
│   ├── ticket_blocked.yaml
│   └── watchdog_escalation.yaml
│
├── watchdog_policies/               # Guardian policies
│   ├── monitor_failover.yaml
│   └── monitor_restart.yaml
│
├── task_scoring/                    # Task scoring rules
│   ├── priority_weights.yaml
│   └── sla_thresholds.yaml
│
├── phases/                          # Phase definitions
│   ├── phase_gates.yaml
│   └── phase_transitions.yaml
│
└── features/                        # Feature flags
    ├── experimental.yaml
    └── rollout.yaml

.env.example                         # Example environment variables
.env                                 # Local environment variables (gitignored)
.env.local                           # Local overrides (gitignored)
.env.test                            # Test environment variables (gitignored)
```

---

## Configuration Loading System

### Current Implementation (Correct Pattern)

The existing `omoi_os/config.py` already implements the correct pattern:

```python
# omoi_os/config.py (EXISTING - THIS IS THE CORRECT APPROACH)

from pydantic_settings import BaseSettings
from pathlib import Path
import yaml

class OmoiBaseSettings(BaseSettings):
    """Base class for all settings that loads from YAML + environment variables."""
    
    yaml_section: ClassVar[Optional[str]] = None
    
    @classmethod
    def settings_customise_sources(cls, ...):
        """
        Priority order (highest to lowest):
        1. init_settings (kwargs passed to __init__)
        2. env_settings (environment variables like LLM_API_KEY)
        3. file_secret_settings (Docker secrets)
        4. YamlSectionSettingsSource (YAML files)
        """
        return (
            init_settings,
            env_settings,
            file_secret_settings,
            YamlSectionSettingsSource(settings_cls, section=cls.yaml_section)
        )


class LLMSettings(OmoiBaseSettings):
    """
    Configuration Priority:
    1. Environment variable: LLM_API_KEY (from .env)
    2. Environment variable: LLM_MODEL (from .env)
    3. YAML: config/base.yaml -> llm.model
    4. Code default: "openhands/claude-sonnet-4-5-20250929"
    """
    yaml_section = "llm"
    model_config = SettingsConfigDict(env_prefix="LLM_")
    
    model: str = "openhands/claude-sonnet-4-5-20250929"
    api_key: Optional[str] = None  # MUST come from .env
    base_url: Optional[str] = None  # Can come from .env
```

---

## File Purpose Definitions

### YAML Files (config/base.yaml)

**Purpose**: Version-controlled configuration that can differ by environment

```yaml
# config/base.yaml

# ✅ Application Settings (business logic)
task_queue:
  age_ceiling: 3600
  sla_urgency_window: 900
  starvation_limit: 7200
  w_p: 0.45  # Priority weight
  w_a: 0.2   # Age weight
  w_d: 0.15  # Dependency weight

monitoring:
  guardian_interval_seconds: 60
  conductor_interval_seconds: 300
  health_check_interval_seconds: 30
  auto_steering_enabled: false
  max_concurrent_analyses: 5

approval:
  ticket_human_review: false
  approval_timeout_seconds: 1800
  on_reject: delete

auth:
  # ✅ Policy settings (not secrets)
  jwt_algorithm: HS256
  access_token_expire_minutes: 15
  refresh_token_expire_days: 7
  min_password_length: 8
  require_uppercase: true
  require_lowercase: true
  require_digit: true
  max_login_attempts: 5
  login_attempt_window_minutes: 15

worker:
  concurrency: 2
  heartbeat_interval_seconds: 30
  stale_threshold_seconds: 90

embedding:
  provider: local  # or "openai"
  model_name: intfloat/multilingual-e5-large
  chunk_size: 1000
  chunk_overlap: 200

features:
  enable_mcp_tools: true
  enable_discoveries: true
  enable_validation: true
  enable_guardian: true

# ❌ DO NOT PUT THESE IN YAML (use .env instead):
# database:
#   url: postgresql://...  # NO - use DATABASE_URL env var
# llm:
#   api_key: sk-...        # NO - use LLM_API_KEY env var
# auth:
#   jwt_secret_key: ...    # NO - use AUTH_JWT_SECRET_KEY env var
```

### .env File (Environment Variables Only)

**Purpose**: Secrets and deployment-specific URLs (NEVER committed to git)

```bash
# .env (GITIGNORED)

# ✅ Database connection (secrets + URL)
DATABASE_URL=postgresql+psycopg://postgres:secret@localhost:15432/app_db

# ✅ Redis connection
REDIS_URL=redis://localhost:16379

# ✅ LLM API keys (secrets)
LLM_API_KEY=sk-ant-api03-...
LLM_BASE_URL=https://api.anthropic.com/v1

# ✅ Fireworks AI (if using)
FIREWORKS_API_KEY=fw_...

# ✅ Auth secrets
AUTH_JWT_SECRET_KEY=your-super-secret-key-here-change-in-production

# ✅ Supabase credentials (if using)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_DB_URL=postgresql://...

# ✅ OpenAI (if using for embeddings)
OPENAI_API_KEY=sk-...

# ✅ GitHub integration
GITHUB_TOKEN=ghp_...

# ✅ Observability (if using)
LOGFIRE_TOKEN=...

# ✅ Environment identifier
OMOIOS_ENV=local  # or staging, production

# ❌ DO NOT PUT THESE IN .env (use YAML instead):
# TASK_QUEUE_AGE_CEILING=3600  # NO - use config/base.yaml
# MONITORING_INTERVAL=60       # NO - use config/base.yaml
# WORKER_CONCURRENCY=2         # NO - use config/base.yaml
```

### .env.example (Template)

**Purpose**: Template for developers (committed to git)

```bash
# .env.example
# Copy this to .env and fill in your values

# Required: Database
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:15432/app_db

# Required: Redis
REDIS_URL=redis://localhost:16379

# Required: LLM API
LLM_API_KEY=your-api-key-here
LLM_MODEL=anthropic/claude-sonnet-4-5-20250929

# Optional: Fireworks AI
# FIREWORKS_API_KEY=

# Required: Auth
AUTH_JWT_SECRET_KEY=generate-a-secure-random-string

# Optional: Supabase
# SUPABASE_URL=
# SUPABASE_ANON_KEY=
# SUPABASE_SERVICE_ROLE_KEY=

# Optional: OpenAI (for embeddings)
# OPENAI_API_KEY=

# Optional: GitHub
# GITHUB_TOKEN=

# Optional: Observability
# LOGFIRE_TOKEN=

# Environment
OMOIOS_ENV=local
```

---

## Test Configuration

### config/test.yaml

**Purpose**: Test-specific configuration overrides

```yaml
# config/test.yaml
# Configuration for test environment (pytest)

# Test database settings (URLs come from .env.test)
database:
  pool_size: 5
  max_overflow: 10
  echo: false  # Disable SQL logging in tests

# Test Redis settings
redis:
  connection_timeout: 5

# Fast intervals for testing
monitoring:
  guardian_interval_seconds: 1  # Fast for tests
  conductor_interval_seconds: 2
  health_check_interval_seconds: 1
  auto_steering_enabled: false  # Disable in tests

task_queue:
  age_ceiling: 60  # Shorter for tests
  sla_urgency_window: 30
  starvation_limit: 120

approval:
  ticket_human_review: false
  approval_timeout_seconds: 10  # Short timeout for tests

auth:
  access_token_expire_minutes: 5  # Short for tests
  max_login_attempts: 3

worker:
  concurrency: 1  # Single worker for predictable tests
  heartbeat_interval_seconds: 1

features:
  enable_mcp_tools: false  # Disable external tools in tests
  enable_discoveries: true
  enable_validation: true
  enable_guardian: false  # Disable slow guardian in most tests

# Test-specific settings
testing:
  use_fakeredis: true
  cleanup_after_test: true
  strict_mode: true
  fail_fast: false
```

### .env.test

**Purpose**: Test environment variables (gitignored)

```bash
# .env.test
# Environment variables for testing

DATABASE_URL_TEST=postgresql+psycopg://postgres:postgres@localhost:15432/app_db_test
REDIS_URL_TEST=redis://localhost:16379/1

# Use test API keys (or mocks)
LLM_API_KEY=test-key-mock
FIREWORKS_API_KEY=test-key-mock

# Test auth secrets
AUTH_JWT_SECRET_KEY=test-secret-key-not-for-production

# Environment identifier
OMOIOS_ENV=test
```

---

## Updated Settings Classes

### Proper Pattern (Using YAML Section)

```python
# omoi_os/config/monitoring.py

from omoi_os.config import OmoiBaseSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict

class MonitoringSettings(OmoiBaseSettings):
    """
    Monitoring configuration loaded from config/base.yaml (or env-specific YAML).
    
    Environment variables can override:
    - MONITORING_GUARDIAN_INTERVAL_SECONDS
    - MONITORING_AUTO_STEERING_ENABLED
    
    YAML section: monitoring
    """
    
    yaml_section = "monitoring"
    model_config = SettingsConfigDict(
        env_prefix="MONITORING_",
        extra="ignore"
    )
    
    guardian_interval_seconds: int = 60
    conductor_interval_seconds: int = 300
    health_check_interval_seconds: int = 30
    auto_steering_enabled: bool = False
    max_concurrent_analyses: int = 5
    stale_threshold_seconds: int = 90
    
    # Optional environment-specific override
    # If MONITORING_GUARDIAN_INTERVAL_SECONDS=30 in .env, it overrides YAML


@lru_cache(maxsize=1)
def load_monitoring_settings() -> MonitoringSettings:
    """Load monitoring settings (cached)."""
    return MonitoringSettings()
```

### ❌ WRONG Pattern (Old Files to Update)

```python
# omoi_os/config/validation.py (NEEDS UPDATE)

# ❌ This imports get_env_files and uses only .env
class ValidationConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VALIDATION_",
        env_file=get_env_files(),  # ❌ Should use YAML section instead
    )
```

**Should be:**

```python
# omoi_os/config/validation.py (CORRECTED)

from omoi_os.config import OmoiBaseSettings
from pydantic_settings import SettingsConfigDict

class ValidationConfig(OmoiBaseSettings):
    """Validation configuration from YAML."""
    
    yaml_section = "validation"
    model_config = SettingsConfigDict(
        env_prefix="VALIDATION_",
        extra="ignore"
    )
    
    timeout_seconds: int = 3600
    max_retries: int = 3
    require_human_review: bool = False
```

And add to `config/base.yaml`:

```yaml
validation:
  timeout_seconds: 3600
  max_retries: 3
  require_human_review: false
```

---

## Files That Need Updating

### 1. config.py (Root)

**Status**: ❌ Uses old pattern with get_env_files()

**Action**: Remove the root `config.py` file, use `omoi_os/config.py` instead

```bash
# Remove old config.py
rm config.py
```

### 2. omoi_os/config/validation.py

**Current**: Uses `get_env_files()` pattern
**Update**: Use `OmoiBaseSettings` with `yaml_section`

### 3. omoi_os/ticketing/db.py

**Current**: Has its own `DBSettings` with `get_env_files()`
**Update**: Should use main `DatabaseSettings` from `omoi_os/config.py`

### 4. Test Configuration

**Current**: Tests use environment variables directly
**Update**: Add `config/test.yaml` and `.env.test`

---

## Updated config/base.yaml

```yaml
# config/base.yaml
# Base configuration for all environments
# Secrets and URLs come from environment variables (.env files)

llm:
  model: openhands/claude-sonnet-4-5-20250929
  # api_key comes from LLM_API_KEY env var
  # base_url comes from LLM_BASE_URL env var
  timeout_seconds: 300
  max_retries: 3
  temperature: 0.7

task_queue:
  age_ceiling: 3600
  sla_urgency_window: 900
  starvation_limit: 7200
  blocker_ceiling: 10
  w_p: 0.45  # Priority weight
  w_a: 0.2   # Age weight
  w_d: 0.15  # Dependency weight
  w_b: 0.15  # Blocker weight
  w_r: 0.05  # Retry weight
  sla_boost_multiplier: 1.25
  starvation_floor_score: 0.6

approval:
  ticket_human_review: false
  approval_timeout_seconds: 1800
  on_reject: delete  # or "retry" or "block"
  require_evidence: true
  min_reviewers: 1

auth:
  # Policy settings (not secrets)
  # jwt_secret_key comes from AUTH_JWT_SECRET_KEY env var
  jwt_algorithm: HS256
  access_token_expire_minutes: 15
  refresh_token_expire_days: 7
  min_password_length: 8
  require_uppercase: true
  require_lowercase: true
  require_digit: true
  require_special_char: false
  max_login_attempts: 5
  login_attempt_window_minutes: 15
  session_expire_days: 30
  enable_oauth: true
  allowed_oauth_providers:
    - github
    - google

workspace:
  root: ./workspaces
  worker_dir: /tmp/omoi_os_workspaces
  max_size_mb: 1000
  cleanup_after_hours: 24

monitoring:
  guardian_interval_seconds: 60
  conductor_interval_seconds: 300
  health_check_interval_seconds: 30
  auto_steering_enabled: false
  max_concurrent_analyses: 5
  stale_threshold_seconds: 90
  alert_on_stale: true
  alert_on_duplicate: true

worker:
  concurrency: 2
  heartbeat_interval_seconds: 30
  max_task_timeout_seconds: 3600
  retry_backoff_base: 2
  max_retries: 3

integrations:
  # github_token comes from GITHUB_TOKEN env var
  # mcp_server_url comes from MCP_SERVER_URL env var
  enable_mcp_tools: true
  enable_github_sync: false
  enable_webhooks: false

embedding:
  provider: local  # or "openai"
  # openai_api_key comes from OPENAI_API_KEY env var
  model_name: intfloat/multilingual-e5-large
  chunk_size: 1000
  chunk_overlap: 200
  batch_size: 32

observability:
  enable_tracing: false
  # logfire_token comes from LOGFIRE_TOKEN env var
  sample_rate: 1.0
  log_level: INFO

features:
  enable_discoveries: true
  enable_validation: true
  enable_guardian: true
  enable_memory: true
  enable_collaboration: true
  enable_budget_tracking: true

phases:
  enable_gates: true
  strict_transitions: true
  require_artifacts: false

validation:
  timeout_seconds: 3600
  max_retries: 3
  require_human_review: false
  validation_types:
    - syntax_check
    - security_scan
    - test_execution

cost_tracking:
  enable_tracking: true
  enable_alerts: true
  daily_budget_usd: 100
  monthly_budget_usd: 3000
```

### config/test.yaml

```yaml
# config/test.yaml
# Test environment configuration
# Overrides base.yaml for testing

# Fast intervals for quick tests
monitoring:
  guardian_interval_seconds: 1
  conductor_interval_seconds: 2
  health_check_interval_seconds: 1
  auto_steering_enabled: false

task_queue:
  age_ceiling: 60
  sla_urgency_window: 10
  starvation_limit: 120

approval:
  approval_timeout_seconds: 5  # Quick timeout for tests

auth:
  access_token_expire_minutes: 5
  max_login_attempts: 3

worker:
  concurrency: 1  # Single worker for predictable tests
  heartbeat_interval_seconds: 1

features:
  enable_mcp_tools: false  # Disable external integrations
  enable_github_sync: false
  enable_webhooks: false

embedding:
  provider: local  # Always use local in tests

observability:
  enable_tracing: false  # Disable in tests

testing:
  strict_mode: true
  fail_fast: false
  use_fakeredis: true
  cleanup_after_test: true
```

---

## Configuration Loading in Code

### Standard Pattern

```python
# omoi_os/services/task_queue.py

from omoi_os.config import OmoiBaseSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict
from functools import lru_cache

class TaskQueueSettings(OmoiBaseSettings):
    """Task queue configuration."""
    
    yaml_section = "task_queue"
    model_config = SettingsConfigDict(
        env_prefix="TASK_QUEUE_",
        extra="ignore"
    )
    
    age_ceiling: int = 3600
    sla_urgency_window: int = 900
    starvation_limit: int = 7200
    blocker_ceiling: int = 10
    w_p: float = Field(0.45, description="Priority weight")
    w_a: float = Field(0.2, description="Age weight")
    w_d: float = Field(0.15, description="Dependency weight")
    w_b: float = Field(0.15, description="Blocker weight")
    w_r: float = Field(0.05, description="Retry weight")


@lru_cache(maxsize=1)
def load_task_queue_settings() -> TaskQueueSettings:
    """Load task queue settings (cached)."""
    return TaskQueueSettings()


class TaskQueueService:
    def __init__(self, db: DatabaseService):
        self.db = db
        self.settings = load_task_queue_settings()  # ✅ Loads from YAML + env
    
    def calculate_score(self, task: Task) -> float:
        # Use settings from YAML
        priority_score = self.settings.w_p * task.priority_value
        age_score = self.settings.w_a * self.calculate_age_factor(task)
        # ...
```

### Loading in Tests

```python
# tests/unit/services/test_task_queue_service.py

import pytest
import os
from omoi_os.services.task_queue import TaskQueueService, load_task_queue_settings

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Ensure test environment is active."""
    os.environ['OMOIOS_ENV'] = 'test'
    yield
    # Cleanup if needed


def test_task_queue_loads_test_config():
    """Verify task queue uses test.yaml configuration."""
    settings = load_task_queue_settings()
    
    # Should load from config/test.yaml
    assert settings.age_ceiling == 60  # test.yaml value
    # Not base.yaml value (3600)


def test_task_queue_env_override(monkeypatch):
    """Verify environment variables override YAML."""
    # Clear cache
    load_task_queue_settings.cache_clear()
    
    # Set environment variable
    monkeypatch.setenv('TASK_QUEUE_AGE_CEILING', '120')
    
    settings = load_task_queue_settings()
    assert settings.age_ceiling == 120  # env var overrides YAML
```

---

## Migration Steps

### Step 1: Add config/test.yaml

```bash
# Create test configuration
cat > config/test.yaml << 'EOF'
# Test environment configuration
monitoring:
  guardian_interval_seconds: 1
  conductor_interval_seconds: 2

task_queue:
  age_ceiling: 60

features:
  enable_mcp_tools: false

testing:
  strict_mode: true
EOF
```

### Step 2: Create .env.test

```bash
# Create test environment variables
cat > .env.test << 'EOF'
DATABASE_URL_TEST=postgresql+psycopg://postgres:postgres@localhost:15432/app_db_test
REDIS_URL_TEST=redis://localhost:16379/1
LLM_API_KEY=test-key-mock
AUTH_JWT_SECRET_KEY=test-secret-key
OMOIOS_ENV=test
EOF

# Add to .gitignore
echo ".env.test" >> .gitignore
```

### Step 3: Update Files Using Old Pattern

```bash
# Find files using old pattern
grep -r "get_env_files" omoi_os/ --include="*.py"

# Files to update:
# - omoi_os/config/validation.py
# - omoi_os/ticketing/db.py
# - Any other files with custom get_env_files()
```

### Step 4: Update Root config.py

The root `config.py` should be removed in favor of `omoi_os/config.py`:

```bash
# Remove old config.py
git rm config.py

# Update imports in any files using it
# OLD: from config import load_llm_settings
# NEW: from omoi_os.config import load_llm_settings
```

---

## .gitignore Updates

```gitignore
# .gitignore

# Environment variables (NEVER commit these)
.env
.env.local
.env.*.local
.env.test
.env.staging
.env.production

# But DO commit these:
# .env.example (template)
# config/*.yaml (all YAML configs)

# Test artifacts
.testmondata
.pytest_cache/
.coverage
htmlcov/
coverage.xml

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environments
venv/
env/
ENV/
```

---

## Configuration Best Practices

### 1. Secrets Management

```python
# ✅ CORRECT: Secrets from environment
class LLMSettings(OmoiBaseSettings):
    yaml_section = "llm"
    api_key: Optional[str] = None  # From LLM_API_KEY env var


# ❌ WRONG: Secrets in YAML
# config/base.yaml
llm:
  api_key: sk-ant-...  # NEVER DO THIS
```

### 2. Environment-Specific Config

```yaml
# config/base.yaml (defaults)
monitoring:
  guardian_interval_seconds: 60

# config/test.yaml (test overrides)
monitoring:
  guardian_interval_seconds: 1  # Fast for tests

# config/production.yaml (production overrides)
monitoring:
  guardian_interval_seconds: 300  # Less frequent in prod
  auto_steering_enabled: true  # Enable in prod
```

### 3. Feature Flags

```yaml
# config/base.yaml
features:
  enable_discoveries: true
  enable_validation: true
  enable_guardian: false  # Default off

# config/production.yaml
features:
  enable_guardian: true  # Enable in production
```

### 4. Testing Configuration

```python
# tests/conftest.py

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Ensure test environment configuration is loaded."""
    monkeypatch.setenv('OMOIOS_ENV', 'test')
    
    # Clear any cached settings
    from omoi_os.config import load_monitoring_settings
    load_monitoring_settings.cache_clear()
    
    yield
```

---

## Quick Reference

### When to use .env
✅ Database URLs (with passwords)
✅ API keys and secrets
✅ OAuth client secrets
✅ JWT secret keys
✅ Service URLs (external services)
✅ Credentials

### When to use YAML
✅ Business logic settings (weights, thresholds)
✅ Feature flags
✅ Timeouts and intervals
✅ Concurrency limits
✅ Algorithm parameters
✅ Policy configurations
✅ UI preferences
✅ Phase definitions

### Examples

| Setting | Use | File |
|---------|-----|------|
| `LLM_API_KEY` | ✅ .env | Secret credential |
| `llm.model` | ✅ YAML | Model selection (not secret) |
| `DATABASE_URL` | ✅ .env | Contains password |
| `task_queue.w_p` | ✅ YAML | Algorithm weight |
| `AUTH_JWT_SECRET_KEY` | ✅ .env | Secret key |
| `auth.jwt_algorithm` | ✅ YAML | Algorithm choice |
| `monitoring.guardian_interval` | ✅ YAML | Business setting |
| `GITHUB_TOKEN` | ✅ .env | Secret token |
| `features.enable_guardian` | ✅ YAML | Feature flag |

---

This configuration architecture provides:
- Clear separation of concerns
- Environment-specific overrides
- Version-controlled settings
- Secure secret management
- Easy testing
- Scalable structure

