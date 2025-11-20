# Answers to Organization Questions

**Date**: 2025-11-20
**Purpose**: Comprehensive answers to documentation, testing, and configuration organization questions

---

## Question 1: Best Way to Organize and Name Documents?

### Answer: Three-Tier Categorization System

#### Tier 1: By Document Type (Top Level)
```
docs/
├── requirements/      # WHAT to build (business requirements)
├── design/           # HOW to build (technical design)
├── architecture/     # WHY decisions were made (ADRs)
├── implementation/   # STATUS of building (completion logs)
├── operations/       # HOW to run (runbooks, deployment)
└── archive/          # Historical (old phases, chat logs)
```

#### Tier 2: By Feature Domain (Within Type)
```
docs/design/
├── core/             # Core system designs
├── services/         # Service-specific designs
├── workflows/        # Workflow designs
├── frontend/         # Frontend designs
├── testing/          # Testing strategies
└── configuration/    # Configuration designs
```

#### Tier 3: By Specific Feature (File Level)
```
Format: {feature}_{component}.md

Examples:
- memory_system.md
- auth_system_implementation.md
- task_queue_management.md
```

### Naming Convention Rules

✅ **DO**:
- Use `snake_case` for ALL filenames
- Be descriptive: `auth_system_implementation.md`
- Group related docs in subdirectories
- Use consistent suffixes: `_requirements.md`, `_design.md`, `_guide.md`

❌ **DON'T**:
- Use CamelCase: `AuthSystem.md`
- Use hyphens: `auth-system.md`
- Use spaces: `auth system.md`
- Use version numbers: `auth_system_v2.md` (use git history instead)
- Leave docs in root: `docs/notes.md` (categorize it!)

### Document Type Conventions

| Type | Filename Pattern | Location | Example |
|------|------------------|----------|---------|
| Requirements | `{feature}_requirements.md` | `requirements/{category}/` | `validation_requirements.md` |
| Design | `{feature}_design.md` | `design/{category}/` | `memory_system_design.md` |
| ADR | `{nnn}_{decision}.md` | `architecture/` | `001_use_postgresql.md` |
| Guide | `{topic}_guide.md` | `design/{category}/` | `config_migration_guide.md` |
| Summary | `{FEATURE}_SUMMARY.md` | `docs/` (root) | `TESTING_SUMMARY.md` |
| Status | `{feature}_complete.md` | `implementation/` | `auth_system_complete.md` |

---

## Question 2: How to Enforce Organization in CLAUDE.md?

### Answer: Add Automated Validation Rules

Add to CLAUDE.md:

```markdown
## Documentation Standards (ENFORCED)

### Before Creating ANY Documentation

1. **Check if it already exists**:
   ```bash
   grep -r "similar topic" docs/ --include="*.md"
   ```

2. **Choose correct location**:
   - Requirements → `docs/requirements/{category}/`
   - Design → `docs/design/{category}/`
   - ADR → `docs/architecture/`
   - Status → `docs/implementation/`

3. **Follow naming convention**:
   - ✅ `memory_system.md` (snake_case)
   - ❌ `MemorySystem.md` (CamelCase)
   - ❌ `memory-system.md` (hyphens)

4. **Include metadata header**:
   ```markdown
   # Document Title
   
   **Created**: 2025-11-20
   **Status**: Draft
   **Purpose**: One-sentence description
   ```

5. **Validate before committing**:
   ```bash
   python scripts/validate_docs.py
   ```

### Before Creating ANY Test File

1. **Choose correct category**:
   - Unit test → `tests/unit/{domain}/test_{feature}.py`
   - Integration → `tests/integration/{domain}/test_{feature}_integration.py`
   - E2E → `tests/e2e/test_{workflow}.py`

2. **Follow naming convention**:
   - ✅ `test_task_queue_service.py`
   - ❌ `taskQueueTest.py`
   - ❌ `test_tqs.py` (no abbreviations)

3. **Use appropriate fixtures**:
   - Check `tests/conftest.py` for existing fixtures
   - Add new fixtures to `tests/fixtures/` if reusable

4. **Add proper markers**:
   ```python
   @pytest.mark.unit
   @pytest.mark.requires_db
   def test_something():
       pass
   ```

### Configuration Standards (ENFORCED)

1. **YAML for settings, .env for secrets**:
   - ✅ `config/base.yaml` - task_queue.w_p: 0.45
   - ❌ `config/base.yaml` - llm.api_key: sk-... (NEVER!)
   - ✅ `.env` - LLM_API_KEY=sk-...

2. **Use OmoiBaseSettings pattern**:
   ```python
   class FeatureSettings(OmoiBaseSettings):
       yaml_section = "feature"
       model_config = SettingsConfigDict(env_prefix="FEATURE_")
   ```

3. **Never hardcode configuration**:
   - ❌ `interval = 60` (hardcoded)
   - ✅ `interval = settings.guardian_interval_seconds` (from YAML)

4. **Group related settings**:
   - ✅ `config/alert_rules/agent_health.yaml`
   - ❌ `config/agent_health_alert.yaml` (needs subdirectory)
```

---

## Question 3: Prevent Configuration Sprawl?

### Answer: Centralized Configuration System

#### Problem: Configuration Sprawl

**Symptoms**:
- Settings scattered across multiple files
- Duplicate settings in different places
- Hardcoded values in code
- Unclear which settings override others
- Secrets mixed with configuration

#### Solution: Three-Layer Architecture

```
Layer 1: Code Defaults (Fallback)
    ↓
Layer 2: YAML Configuration (Environment-specific)
    ↓
Layer 3: Environment Variables (Secrets & Overrides)
    ↓
Final Value Used
```

### Enforcement Rules

#### Rule 1: Single Source of Truth

Each setting appears in EXACTLY ONE place:

```python
# ✅ CORRECT: Setting defined once in Settings class
class MonitoringSettings(OmoiBaseSettings):
    yaml_section = "monitoring"
    guardian_interval_seconds: int = 60  # Default


# ❌ WRONG: Setting duplicated in multiple places
# In file A:
GUARDIAN_INTERVAL = 60

# In file B:
interval = config.get('guardian_interval', 60)

# In file C:
class Monitor:
    INTERVAL = 60  # Duplicated!
```

#### Rule 2: Configuration Class Registry

Create a configuration registry:

```python
# omoi_os/config/registry.py

from typing import Dict, Type
from omoi_os.config import OmoiBaseSettings

# Central registry of all configuration classes
CONFIG_REGISTRY: Dict[str, Type[OmoiBaseSettings]] = {
    "llm": LLMSettings,
    "database": DatabaseSettings,
    "redis": RedisSettings,
    "monitoring": MonitoringSettings,
    "task_queue": TaskQueueSettings,
    "auth": AuthSettings,
    "worker": WorkerSettings,
    "embedding": EmbeddingSettings,
    "validation": ValidationSettings,
    "approval": ApprovalSettings,
    # Add new settings here
}

def get_settings(section: str) -> OmoiBaseSettings:
    """Get settings for a section (cached)."""
    settings_cls = CONFIG_REGISTRY.get(section)
    if not settings_cls:
        raise ValueError(f"Unknown config section: {section}")
    return settings_cls()


def list_config_sections() -> List[str]:
    """List all available configuration sections."""
    return list(CONFIG_REGISTRY.keys())


def validate_all_configs() -> bool:
    """Validate all configuration can load."""
    for section, settings_cls in CONFIG_REGISTRY.items():
        try:
            settings_cls()
        except Exception as e:
            print(f"❌ Failed to load {section}: {e}")
            return False
    return True
```

#### Rule 3: Configuration Linting

```python
# scripts/lint_config.py

def check_yaml_has_settings_class(yaml_file: Path) -> bool:
    """Ensure every YAML section has a corresponding Settings class."""
    with open(yaml_file) as f:
        data = yaml.safe_load(f)
    
    for section in data.keys():
        if section not in CONFIG_REGISTRY:
            print(f"⚠️  YAML section '{section}' has no Settings class")
            return False
    return True


def check_settings_class_has_yaml(settings_cls: Type) -> bool:
    """Ensure every Settings class has YAML configuration."""
    if not hasattr(settings_cls, 'yaml_section'):
        return True  # No YAML section expected
    
    section = settings_cls.yaml_section
    yaml_data = load_yaml_section(section)
    
    if not yaml_data:
        print(f"⚠️  Settings class '{settings_cls.__name__}' expects YAML section '{section}' but not found")
        return False
    return True
```

#### Rule 4: Settings Documentation

Every settings class must have a README:

```
config/
├── README.md                        # Configuration index
├── base.yaml
├── alert_rules/
│   ├── README.md                    # Explains alert configuration
│   └── agent_health.yaml
└── watchdog_policies/
    ├── README.md                    # Explains policy configuration
    └── monitor_failover.yaml
```

### Prevention Checklist

Before adding ANY configuration:

- [ ] Is this a secret? → Use .env
- [ ] Is this a setting? → Use YAML
- [ ] Does a Settings class exist? → Use it
- [ ] No Settings class? → Create one using OmoiBaseSettings
- [ ] Add to CONFIG_REGISTRY
- [ ] Document in config README
- [ ] Add to config/base.yaml with sensible default
- [ ] Override in config/test.yaml if needed for tests
- [ ] Add validation test

---

## Question 4: Justfile vs Makefile?

### Answer: Justfile Provides Better Features

#### Advantages of Just over Make

1. **Better syntax** - More readable, less cryptic
2. **Cross-platform** - Works on Windows without modifications
3. **String interpolation** - Easier variable handling
4. **Recipe arguments** - Can pass parameters to commands
5. **Dependencies** - Clearer dependency management
6. **No tabs vs spaces** - Avoids Make's infamous tab requirement
7. **Better error messages** - More helpful debugging
8. **Dotenv integration** - Built-in .env file loading
9. **Shebang support** - Use any language for recipes
10. **Recipe documentation** - Built-in help system

#### Installation

```bash
# macOS
brew install just

# Linux
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash

# Via cargo
cargo install just
```

#### Justfile Features We'll Use

```justfile
# Set shell for all recipes
set shell := ["bash", "-uc"]

# Load .env file automatically
set dotenv-load

# Set environment variables
export OMOIOS_ENV := "local"

# Recipe with parameters
test pattern="": 
    pytest {{pattern}} --testmon

# Recipe with dependencies
test-all: clean install
    pytest --no-testmon --cov

# Multi-line recipes
setup:
    #!/usr/bin/env bash
    set -euxo pipefail
    echo "Setting up..."
    uv sync --group test
    ./scripts/setup_test_environment.sh

# Private recipes (start with _)
_internal-task:
    echo "This won't show in help"

# Default recipe
default:
    @just --list
```

See full Justfile implementation below.

---

## Question 5: Global CLAUDE.md Conventions?

### Answer: Add Testing & Documentation Section

Add to global CLAUDE.md (your personal template):

```markdown
## Testing Conventions (Apply to All Python Projects)

### Test Organization

1. **Directory Structure**:
   ```
   tests/
   ├── unit/           # Fast, isolated tests
   ├── integration/    # Multi-component tests  
   ├── e2e/           # Full workflow tests
   ├── performance/    # Load/benchmark tests
   ├── fixtures/       # Shared fixtures
   └── helpers/        # Test utilities
   ```

2. **Naming Convention**:
   - Files: `test_{feature}_{component}.py`
   - Classes: `class Test{Feature}:`
   - Functions: `def test_{scenario}():`

3. **Required Markers**:
   ```python
   @pytest.mark.unit          # For unit tests
   @pytest.mark.integration   # For integration tests
   @pytest.mark.requires_db   # For database tests
   ```

4. **Use pytest-testmon**:
   - Always install: `pytest-testmon`
   - Configure in pytest.ini: `--testmon`
   - Run: `pytest --testmon` (only affected tests)

### Test File Template

```python
"""Test {feature} {component}.

Tests cover:
- {functionality 1}
- {functionality 2}
"""

import pytest
from {module} import {FeatureClass}


class Test{Feature}:
    """Test suite for {feature}."""
    
    @pytest.mark.unit
    def test_{scenario}_success(self, fixture):
        """Test {scenario} succeeds when {condition}."""
        # Arrange
        setup = create_test_data()
        
        # Act
        result = feature.do_something(setup)
        
        # Assert
        assert result.success is True
    
    @pytest.mark.unit
    def test_{scenario}_failure(self, fixture):
        """Test {scenario} fails when {condition}."""
        # Arrange
        setup = create_invalid_data()
        
        # Act & Assert
        with pytest.raises(ExpectedException):
            feature.do_something(setup)
```

## Documentation Conventions (Apply to All Projects)

### Document Organization

1. **Categorize by purpose**, not chronologically:
   - `requirements/` - What to build
   - `design/` - How to build
   - `architecture/` - Why decisions were made
   - `implementation/` - Build status
   - `operations/` - How to run

2. **Naming convention**: `snake_case` for all files
   - ✅ `auth_system_design.md`
   - ❌ `AuthSystemDesign.md`
   - ❌ `auth-system-design.md`

3. **Required metadata** (every document):
   ```markdown
   # Document Title
   
   **Created**: YYYY-MM-DD
   **Status**: Draft | Review | Approved | Active | Archived
   **Purpose**: One-sentence description
   ```

4. **Single H1** per document
   - Title only
   - All other headings are H2, H3, H4

5. **Validate before commit**:
   ```bash
   python scripts/validate_docs.py
   ```

## Configuration Conventions (Apply to All Python Projects)

### Configuration Architecture

1. **YAML for settings, .env for secrets**:
   ```yaml
   # config/base.yaml (settings)
   task_queue:
     age_ceiling: 3600
     w_p: 0.45
   ```
   
   ```bash
   # .env (secrets - GITIGNORED)
   DATABASE_URL=postgresql://...
   API_KEY=sk-...
   ```

2. **Use Pydantic Settings with YAML**:
   ```python
   class FeatureSettings(OmoiBaseSettings):
       yaml_section = "feature"
       model_config = SettingsConfigDict(env_prefix="FEATURE_")
   ```

3. **Configuration registry** (prevent sprawl):
   ```python
   # config/registry.py
   CONFIG_REGISTRY = {
       "feature": FeatureSettings,
       # All settings classes registered here
   }
   ```

4. **Never hardcode configuration**:
   - ❌ `interval = 60`
   - ✅ `interval = settings.guardian_interval_seconds`

5. **Validate all configs**:
   ```bash
   python scripts/validate_config.py
   ```

### Configuration Checklist

Before adding ANY configuration:

- [ ] Is this a secret? → Use `.env` file
- [ ] Is this a setting? → Use YAML file
- [ ] Does Settings class exist? → Use it
- [ ] Need new Settings class? → Extend `OmoiBaseSettings`
- [ ] Add to config registry
- [ ] Document in config README
- [ ] Add to appropriate YAML file
- [ ] Test can load correctly

## Project Setup Conventions

### Standard Files Required

Every Python project must have:

1. **pyproject.toml** - Package definition and dependencies
2. **pytest.ini** - Test configuration
3. **Justfile** - Task runner (preferred over Makefile)
4. **CLAUDE.md** - Project-specific AI guidance
5. **.env.example** - Environment variable template
6. **config/base.yaml** - Base configuration
7. **README.md** - Project overview
8. **docs/DOCUMENTATION_STANDARDS.md** - Documentation rules

### Directory Structure

```
project/
├── src/ or {package_name}/    # Source code
├── tests/                      # Tests (organized by type)
├── config/                     # YAML configuration
├── docs/                       # Documentation (organized by purpose)
├── scripts/                    # Utility scripts
├── migrations/                 # Database migrations
├── .env.example               # Environment template
├── .env                       # Local env (gitignored)
├── pyproject.toml             # Package definition
├── pytest.ini                 # Test configuration
├── Justfile                   # Task runner
└── CLAUDE.md                  # AI guidance
```

## Automation Rules

### Pre-commit Hooks

```bash
# .git/hooks/pre-commit
#!/bin/bash

# 1. Validate documentation
python scripts/validate_docs.py || exit 1

# 2. Validate configuration
python scripts/validate_config.py || exit 1

# 3. Run affected tests
just test-quick || exit 1

# 4. Lint code
just lint || exit 1

echo "✅ Pre-commit checks passed"
```

### CI/CD Requirements

Every project must have:

- ✅ Automated testing (pytest with testmon)
- ✅ Code coverage reporting (> 80%)
- ✅ Linting (ruff, black)
- ✅ Type checking (mypy)
- ✅ Documentation validation
- ✅ Configuration validation

---

This provides comprehensive answers to all organization questions with actionable rules and templates.
```

These conventions ensure consistency across all your Python projects!

