# Configuration Migration Guide

**Status**: Active
**Related**: docs/design/configuration.md, docs/implementation/config_loading.md, docs/testing/testing_guide.md, docs/architecture/adr_0001_yaml_first_config.md

---


**Created**: 2025-11-20
**Purpose**: Step-by-step guide to migrate from mixed .env/YAML to clean YAML-first architecture

---

## Migration Checklist

### Phase 1: Create .env.test (5 minutes)

```bash
# Create .env.test file with only secrets and URLs
cat > .env.test << 'EOF'
DATABASE_URL_TEST=postgresql+psycopg://postgres:postgres@localhost:15432/app_db_test
REDIS_URL_TEST=redis://localhost:16379/1
LLM_API_KEY=test-key-mock
AUTH_JWT_SECRET_KEY=test-secret-key-not-for-production
OMOIOS_ENV=test
EOF

# Verify it's in .gitignore
grep ".env.test" .gitignore || echo ".env.test" >> .gitignore
```

### Phase 2: Verify config/test.yaml (Already Created)

```bash
# Verify test configuration exists
cat config/test.yaml

# Should contain fast intervals and disabled features
# NO secrets, NO URLs, only application settings
```

### Phase 3: Update Files Using Old Pattern (30 minutes)

#### File 1: omoi_os/config/validation.py

**Before**:
```python
# ❌ OLD PATTERN
from pydantic_settings import BaseSettings

def get_env_files():
    # ...
    return env_files

class ValidationConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VALIDATION_",
        env_file=get_env_files(),
    )
```

**After**:
```python
# ✅ NEW PATTERN
from omoi_os.config import OmoiBaseSettings
from pydantic_settings import SettingsConfigDict
from functools import lru_cache

class ValidationSettings(OmoiBaseSettings):
    """Validation configuration from YAML."""
    
    yaml_section = "validation"
    model_config = SettingsConfigDict(
        env_prefix="VALIDATION_",
        extra="ignore"
    )
    
    timeout_seconds: int = 3600
    max_retries: int = 3
    require_human_review: bool = False
    validation_types: list[str] = [
        "syntax_check",
        "security_scan",
        "test_execution"
    ]


@lru_cache(maxsize=1)
def load_validation_settings() -> ValidationSettings:
    """Load validation settings (cached)."""
    return ValidationSettings()
```

Then add to `config/base.yaml`:
```yaml
validation:
  timeout_seconds: 3600
  max_retries: 3
  require_human_review: false
  validation_types:
    - syntax_check
    - security_scan
    - test_execution
```

#### File 2: omoi_os/ticketing/db.py

**Before**:
```python
# ❌ OLD PATTERN (duplicates main config)
class DBSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=get_env_files(),
    )
    url: str = "postgresql://..."
```

**After**:
```python
# ✅ NEW PATTERN (use existing config)
from omoi_os.config import load_database_settings

# Remove DBSettings class entirely
# Use load_database_settings() instead
db_settings = load_database_settings()
db_url = db_settings.url
```

#### File 3: Remove Root config.py

```bash
# The root config.py duplicates omoi_os/config.py
# Remove it and update imports

# 1. Check for imports
grep -r "from config import" . --include="*.py"

# 2. Replace imports
# OLD: from config import load_llm_settings
# NEW: from omoi_os.config import load_llm_settings

# 3. Remove file
git rm config.py
```

### Phase 4: Update .gitignore (2 minutes)

```bash
# Add to .gitignore if not already there
cat >> .gitignore << 'EOF'

# Environment variables (NEVER commit)
.env
.env.local
.env.*.local
.env.test
.env.staging
.env.production

# DO commit these:
# .env.example
# config/*.yaml
EOF
```

### Phase 5: Update pytest.ini (Already Done)

Verify `pytest.ini` has testmon configuration:

```ini
[pytest]
# ... existing config ...

# Testmon options
addopts =
    --testmon
    --suppress-no-test-exit-code
```

### Phase 6: Update tests/conftest.py (5 minutes)

Add environment setup and config cache clearing:

```python
# tests/conftest.py

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure test environment configuration is loaded."""
    os.environ['OMOIOS_ENV'] = 'test'
    yield


@pytest.fixture(scope="function", autouse=True)
def clear_config_cache():
    """Clear settings cache before each test."""
    from omoi_os.config import (
        load_monitoring_settings,
        load_task_queue_settings,
    )
    
    load_monitoring_settings.cache_clear()
    load_task_queue_settings.cache_clear()
    
    yield
```

### Phase 7: Run Tests to Verify (5 minutes)

```bash
# Set test environment
export OMOIOS_ENV=test

# Run baseline test collection with testmon
uv run pytest --testmon --collect-only

# Run fast unit tests
uv run pytest tests/unit/ --testmon -v

# Run all tests (this builds testmon database)
uv run pytest --testmon --maxfail=3
```

---

## Verification Steps

### 1. Check Configuration Loading

```python
# test_config_loading.py

import os
import pytest

def test_yaml_config_loads():
    """Verify YAML configuration loads correctly."""
    os.environ['OMOIOS_ENV'] = 'test'
    
    from omoi_os.config import load_monitoring_settings
    settings = load_monitoring_settings()
    
    # Should load from config/test.yaml
    assert settings.guardian_interval_seconds == 1  # test.yaml value
    # Not 60 (base.yaml value)


def test_env_var_overrides_yaml(monkeypatch):
    """Verify environment variables override YAML."""
    os.environ['OMOIOS_ENV'] = 'test'
    
    from omoi_os.config import load_monitoring_settings
    load_monitoring_settings.cache_clear()
    
    # Set env var to override YAML
    monkeypatch.setenv('MONITORING_GUARDIAN_INTERVAL_SECONDS', '99')
    
    settings = load_monitoring_settings()
    assert settings.guardian_interval_seconds == 99  # env var wins


def test_secrets_from_env_only():
    """Verify secrets come from environment, not YAML."""
    from omoi_os.config import load_llm_settings
    
    settings = load_llm_settings()
    
    # api_key must come from LLM_API_KEY env var
    # Should be None if not set, never from YAML
    assert settings.api_key is None or settings.api_key == os.getenv('LLM_API_KEY')
```

### 2. Verify Testmon Works

```bash
# First run: Create baseline
uv run pytest --testmon

# Make a code change (no test change)
echo "# comment" >> omoi_os/services/task_queue.py

# Second run: Only affected tests run
uv run pytest --testmon  # Should run fewer tests

# Verify testmon data exists
ls -la .testmondata
```

### 3. Verify Test Configuration

```bash
# Run a specific test and check it uses test config
uv run pytest tests/test_01_database.py::test_database_service_create_tables -v -s

# Should see log output showing config/test.yaml settings
```

---

## Common Migration Issues

### Issue 1: Settings Cache Not Cleared

**Symptom**: Tests use wrong configuration values

**Solution**:
```python
# Add to conftest.py
@pytest.fixture(autouse=True)
def clear_config_cache():
    from omoi_os.config import load_monitoring_settings
    load_monitoring_settings.cache_clear()
    yield
```

### Issue 2: Environment Not Set

**Symptom**: Tests load base.yaml instead of test.yaml

**Solution**:
```python
# Add to conftest.py
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    os.environ['OMOIOS_ENV'] = 'test'
    yield
```

### Issue 3: .env.test Not Found

**Symptom**: Tests fail with "DATABASE_URL_TEST not found"

**Solution**:
```bash
# Create .env.test file
cp .env.example .env.test
# Edit with test values
```

### Issue 4: Import Errors After Removing config.py

**Symptom**: `ImportError: cannot import name 'load_llm_settings' from 'config'`

**Solution**:
```python
# Update imports
# OLD: from config import load_llm_settings
# NEW: from omoi_os.config import load_llm_settings
```

---

## Quick Start (for New Developers)

```bash
# 1. Clone repo
git clone <repo>
cd senior_sandbox

# 2. Copy environment template
cp .env.example .env

# 3. Fill in your secrets
nano .env  # Add your API keys

# 4. Create test environment
cat > .env.test << 'EOF'
DATABASE_URL_TEST=postgresql+psycopg://postgres:postgres@localhost:15432/app_db_test
REDIS_URL_TEST=redis://localhost:16379/1
LLM_API_KEY=test-key-mock
AUTH_JWT_SECRET_KEY=test-secret-key
OMOIOS_ENV=test
EOF

# 5. Install dependencies
uv sync --group test

# 6. Run tests
uv run pytest --testmon
```

---

## Configuration Priority Order

For any setting, the value is determined by (highest to lowest priority):

1. **Python kwargs** - `MonitoringSettings(guardian_interval_seconds=10)`
2. **Environment variable** - `MONITORING_GUARDIAN_INTERVAL_SECONDS=30`
3. **YAML (environment-specific)** - `config/test.yaml` → `monitoring.guardian_interval_seconds: 1`
4. **YAML (base)** - `config/base.yaml` → `monitoring.guardian_interval_seconds: 60`
5. **Code default** - `guardian_interval_seconds: int = 60`

**Example**:
```bash
# config/base.yaml has: monitoring.guardian_interval_seconds: 60
# config/test.yaml has: monitoring.guardian_interval_seconds: 1
# .env has: MONITORING_GUARDIAN_INTERVAL_SECONDS=5

# Result when OMOIOS_ENV=test:
# guardian_interval_seconds = 5 (env var wins)
```

---

## Summary

### ✅ Use YAML For
- Task queue weights and thresholds
- Monitoring intervals
- Feature flags
- Phase configurations
- Approval policies
- Worker settings
- Algorithm parameters

### ✅ Use .env For
- Database URLs (contain passwords)
- Redis URLs
- API keys (LLM, OpenAI, Fireworks)
- JWT secrets
- OAuth client secrets
- Service tokens (GitHub, Logfire)

### ✅ Keep in Git
- `config/*.yaml` (all YAML files)
- `.env.example` (template)
- `.env.test.example` (test template)

### ❌ Never Commit
- `.env`
- `.env.local`
- `.env.test`
- `.env.staging`
- `.env.production`

---

This migration ensures clean separation, better security, and easier configuration management across environments.

