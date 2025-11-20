# OmoiOS Justfile
# Task runner for development, testing, and deployment
# Install just: https://github.com/casey/just

# Use bash for all recipes
set shell := ["bash", "-uc"]

# Load .env file automatically
set dotenv-load := true

# Set default environment
export OMOIOS_ENV := env_var_or_default("OMOIOS_ENV", "local")

# ============================================================================
# Variables
# ============================================================================

# Python command
python := "uv run python"

# Pytest command
pytest := "uv run pytest"

# Coverage threshold
coverage_threshold := "80"

# API port
api_port := env_var_or_default("API_PORT", "18000")

# ============================================================================
# Default Recipe (show help)
# ============================================================================

default:
    @just --list

# ============================================================================
# Development Setup
# ============================================================================

# Install all dependencies
install:
    uv sync

# Install with dev and test dependencies
[group('setup')]
install-all:
    uv sync --group dev --group test

# Setup test environment (create .env.test, config/test.yaml)
[group('setup')]
setup-test:
    ./scripts/setup_test_environment.sh

# Complete first-time setup
[group('setup')]
setup: install-all setup-test
    @echo "✅ Setup complete!"
    @echo ""
    @echo "Next steps:"
    @echo "  just docker-up      # Start services"
    @echo "  just db-migrate     # Run migrations"
    @echo "  just test           # Run tests"

# ============================================================================
# Testing (with pytest-testmon)
# ============================================================================

# Quick feedback: run only affected tests
[group('test')]
test pattern="":
    {{pytest}} {{pattern}} --testmon -x

# Quick mode (quiet output)
[group('test')]
test-quick pattern="":
    {{pytest}} {{pattern}} --testmon -x -q

# Run unit tests only
[group('test')]
test-unit:
    {{pytest}} tests/unit/ --testmon -v

# Run integration tests
[group('test')]
test-integration:
    {{pytest}} tests/integration/ --testmon -v

# Run end-to-end tests
[group('test')]
test-e2e:
    {{pytest}} tests/e2e/ --testmon -v

# Run performance tests
[group('test')]
test-performance:
    {{pytest}} tests/performance/ --testmon -v

# Run ALL tests (no testmon, full suite)
[group('test')]
test-all:
    {{pytest}} --no-testmon --cov

# Run fast tests in parallel (unit tests, not slow)
[group('test')]
test-fast:
    {{pytest}} -m "unit and not slow" --testmon -x -n auto

# Run tests in parallel
[group('test')]
test-parallel workers="auto":
    {{pytest}} --testmon -n {{workers}}

# Generate HTML coverage report
[group('test')]
test-coverage:
    {{pytest}} --no-testmon --cov --cov-report=html --cov-report=term
    @echo ""
    @echo "📊 Coverage report: htmlcov/index.html"
    @command -v open >/dev/null && open htmlcov/index.html || \
     command -v xdg-open >/dev/null && xdg-open htmlcov/index.html || true

# Re-run only failed tests
[group('test')]
test-failed:
    {{pytest}} --lf --testmon -x

# Run tests matching a keyword
[group('test')]
test-match keyword:
    {{pytest}} -k {{keyword}} --testmon -v

# Run tests with specific marker
[group('test')]
test-mark marker:
    {{pytest}} -m {{marker}} --testmon -v

# Rebuild testmon dependency cache
[group('test')]
test-rebuild:
    @echo "🔄 Rebuilding testmon cache..."
    rm -rf .testmondata
    {{pytest}} --testmon

# Clean all test artifacts
[group('test')]
test-clean:
    @echo "🧹 Cleaning test artifacts..."
    rm -rf .testmondata .pytest_cache htmlcov .coverage coverage.xml
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Run smoke test (critical path only)
[group('test')]
test-smoke:
    {{pytest}} -m critical --testmon -x

# Show what tests would run (dry-run)
[group('test')]
test-dry:
    {{pytest}} --testmon --collect-only

# Watch mode (requires pytest-watch)
[group('test')]
test-watch:
    uv run ptw -- --testmon -x

# ============================================================================
# Code Quality
# ============================================================================

# Format code with ruff and black
[group('quality')]
format:
    uv run ruff check --fix .
    uv run black .

# Lint code with ruff
[group('quality')]
lint:
    uv run ruff check .

# Type check with mypy
[group('quality')]
type-check:
    uv run mypy omoi_os

# Run all quality checks
[group('quality')]
check: lint type-check
    uv run black --check .

# Fix all auto-fixable issues
[group('quality')]
fix:
    uv run ruff check --fix .
    uv run black .
    @echo "✅ Auto-fixes applied"

# ============================================================================
# Database Operations
# ============================================================================

# Run all migrations
[group('database')]
db-migrate:
    uv run alembic upgrade head

# Create new migration
[group('database')]
db-revision message:
    uv run alembic revision -m "{{message}}"

# Rollback one migration
[group('database')]
db-downgrade count="1":
    uv run alembic downgrade -{{count}}

# Show migration history
[group('database')]
db-history:
    uv run alembic history

# Show current migration
[group('database')]
db-current:
    uv run alembic current

# ============================================================================
# Docker Operations
# ============================================================================

# Start all services
[group('docker')]
docker-up:
    docker-compose up -d

# Stop all services
[group('docker')]
docker-down:
    docker-compose down

# View logs (optionally specify service)
[group('docker')]
docker-logs service="":
    #!/usr/bin/env bash
    if [ -z "{{service}}" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f {{service}}
    fi

# Rebuild and restart services
[group('docker')]
docker-rebuild:
    docker-compose up -d --build

# Clean Docker volumes and rebuild
[group('docker')]
docker-clean:
    docker-compose down -v
    docker-compose up -d --build

# ============================================================================
# Running Services
# ============================================================================

# Start API server (development mode with reload)
[group('services')]
api port=api_port:
    uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port {{port}} --reload

# Start worker process
[group('services')]
worker:
    uv run python -m omoi_os.worker

# Run smoke test
[group('services')]
smoke:
    {{python}} scripts/smoke_test.py

# Start API and worker in parallel (requires tmux or separate terminals)
[group('services')]
dev:
    @echo "Starting services..."
    @echo "API will be at http://localhost:{{api_port}}"
    @just api &
    @sleep 2
    @just worker

# ============================================================================
# Documentation
# ============================================================================

# Generate documentation index
[group('docs')]
docs-index:
    {{python}} scripts/generate_doc_index.py

# Validate documentation structure
[group('docs')]
docs-validate:
    {{python}} scripts/validate_docs.py

# Check for orphaned docs
[group('docs')]
docs-check:
    @echo "🔍 Checking for orphaned documents..."
    @find docs/ -maxdepth 1 -type f -name "*.md" ! -name "README.md" ! -name "*_SUMMARY.md" ! -name "DOCUMENTATION_STANDARDS.md"

# Open documentation in browser
[group('docs')]
docs-open:
    @command -v open >/dev/null && open docs/README.md || \
     command -v xdg-open >/dev/null && xdg-open docs/README.md || \
     echo "Open docs/README.md in your editor"

# Organize documentation with AI (batch processing, dry-run)
[group('docs')]
docs-organize concurrent="5":
    {{python}} scripts/organize_docs_batch.py --concurrent {{concurrent}} --detailed --export reorganization_plan.md
    @echo ""
    @echo "📋 Review the plan: reorganization_plan.md"
    @echo "Then run: just docs-organize-apply"

# Apply AI-suggested organization
[group('docs')]
docs-organize-apply:
    {{python}} scripts/organize_docs_batch.py --apply --detailed

# Organize specific pattern (batch)
[group('docs')]
docs-organize-pattern pattern concurrent="5":
    {{python}} scripts/organize_docs_batch.py --pattern "{{pattern}}" --concurrent {{concurrent}} --detailed

# Organize single file (non-batch for quick test)
[group('docs')]
docs-organize-single file:
    {{python}} scripts/organize_docs.py --pattern "{{file}}"

# ============================================================================
# Configuration
# ============================================================================

# Validate all configuration files
[group('config')]
config-validate:
    {{python}} scripts/validate_config.py

# Show current configuration (for current environment)
[group('config')]
config-show section="":
    #!/usr/bin/env bash
    if [ -z "{{section}}" ]; then
        {{python}} -c "from omoi_os.config import _load_yaml_config; import json; print(json.dumps(_load_yaml_config(), indent=2))"
    else
        {{python}} -c "from omoi_os.config import load_yaml_section; import json; print(json.dumps(load_yaml_section('{{section}}'), indent=2))"
    fi

# List all configuration sections
[group('config')]
config-list:
    {{python}} -c "from omoi_os.config import _load_yaml_config; print('\n'.join(_load_yaml_config().keys()))"

# Check for configuration drift (settings without YAML or vice versa)
[group('config')]
config-check:
    {{python}} scripts/check_config_drift.py

# ============================================================================
# Git Operations
# ============================================================================

# Stage and commit with validation
[group('git')]
commit message:
    just docs-validate
    just config-validate
    just test-quick
    git add -A
    git commit -m "{{message}}"

# Push to GitHub after running tests
[group('git')]
push:
    just test-all
    git push origin main

# Create a checkpoint commit (before major changes)
[group('git')]
checkpoint message="Checkpoint":
    git add -A
    git commit -m "🔖 {{message}} - $(date +%Y-%m-%d-%H%M)"

# ============================================================================
# Cleaning
# ============================================================================

# Clean Python cache files
[group('clean')]
clean-py:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Clean test artifacts
[group('clean')]
clean-test:
    rm -rf .pytest_cache htmlcov .coverage coverage.xml
    rm -rf .testmondata

# Clean all artifacts
[group('clean')]
clean-all: clean-py clean-test
    rm -rf dist build
    @echo "✅ Cleaned all artifacts"

# ============================================================================
# Utilities
# ============================================================================

# Show project statistics
[group('util')]
stats:
    @echo "📊 Project Statistics"
    @echo "===================="
    @echo "Python files:  $(find omoi_os -name '*.py' | wc -l | tr -d ' ')"
    @echo "Test files:    $(find tests -name 'test_*.py' | wc -l | tr -d ' ')"
    @echo "Documentation: $(find docs -name '*.md' | wc -l | tr -d ' ')"
    @echo "Lines of code: $(find omoi_os -name '*.py' -exec wc -l {} + | tail -1 | awk '{print $1}')"
    @echo "Test coverage: $(grep -A 1 'TOTAL' htmlcov/index.html 2>/dev/null | tail -1 | grep -oP '\d+%' || echo 'Run tests first')"

# Check dependency updates
[group('util')]
deps-check:
    uv pip list --outdated

# Update dependencies
[group('util')]
deps-update:
    uv sync --upgrade

# Generate dependency tree
[group('util')]
deps-tree package="omoi_os":
    uv pip tree | grep -A 20 {{package}}

# ============================================================================
# Validation
# ============================================================================

# Validate everything (docs, config, tests, code)
[group('validate')]
validate-all: docs-validate config-validate lint type-check test-quick
    @echo "✅ All validations passed"

# Validate documentation structure
[group('validate')]
validate-docs:
    {{python}} scripts/validate_docs.py

# Validate configuration
[group('validate')]
validate-config:
    {{python}} scripts/validate_config.py

# Pre-commit checks (fast)
[group('validate')]
pre-commit: validate-all

# Pre-push checks (comprehensive)
[group('validate')]
pre-push: validate-all test-all
    @echo "✅ Ready to push"

# ============================================================================
# Help & Information
# ============================================================================

# Show available recipes
help:
    @just --list

# Show recipe details
info recipe:
    @just --show {{recipe}}

# Show environment variables
env:
    @echo "OMOIOS_ENV: $OMOIOS_ENV"
    @echo "API_PORT: {{api_port}}"
    @echo "Python: $(which python)"
    @echo "UV: $(which uv)"

# Show configuration summary
config-summary:
    @echo "📋 Configuration Summary"
    @echo "======================="
    @echo "Environment: $OMOIOS_ENV"
    @echo "Config files:"
    @ls -1 config/*.yaml 2>/dev/null | sed 's/^/  - /'
    @echo "Active config: config/$OMOIOS_ENV.yaml (+ config/base.yaml)"

# ============================================================================
# Advanced Recipes
# ============================================================================

# Run a specific test file with testmon
[group('advanced')]
test-file file:
    {{pytest}} tests/{{file}} --testmon -v

# Run tests with specific marker and coverage
[group('advanced')]
test-marker-cov marker:
    {{pytest}} -m {{marker}} --testmon --cov

# Create new test file from template
[group('advanced')]
create-test category feature:
    #!/usr/bin/env bash
    set -euo pipefail
    
    mkdir -p tests/{{category}}
    
    # Capitalize feature name for class (bash string manipulation)
    feature_class=$(echo "{{feature}}" | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1' | tr -d '_')
    
    cat > tests/{{category}}/test_{{feature}}.py << EOF
    """Test {{feature}}.
    
    Tests cover:
    - Functionality 1
    - Functionality 2
    """
    
    import pytest
    
    
    class Test${feature_class}:
        """Test suite for {{feature}}."""
        
        @pytest.mark.{{category}}
        def test_{{feature}}_basic(self):
            """Test basic {{feature}} functionality."""
            # Arrange
            # Act
            # Assert
            pass
    EOF
    
    echo "✅ Created tests/{{category}}/test_{{feature}}.py"

# Create new documentation from template
[group('advanced')]
create-doc doc_type category feature:
    #!/usr/bin/env bash
    set -euo pipefail
    
    mkdir -p docs/{{doc_type}}/{{category}}
    filepath="docs/{{doc_type}}/{{category}}/{{feature}}.md"
    
    # Capitalize feature name for title (bash string manipulation)
    feature_title=$(echo "{{feature}}" | sed 's/_/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')
    
    cat > "$filepath" << EOF
    # ${feature_title}
    
    **Created**: $(date +%Y-%m-%d)
    **Status**: Draft
    **Purpose**: {One-sentence description}
    
    ---
    
    ## Overview
    
    {Description here}
    
    ## Details
    
    {Content here}
    EOF
    
    echo "✅ Created $filepath"

# Interactive Python shell with OmoiOS context
[group('advanced')]
shell:
    {{python}} -i -c "from omoi_os.services.database import DatabaseService; from omoi_os.config import load_database_settings; print('OmoiOS shell ready')"

# ============================================================================
# CI/CD Simulation
# ============================================================================

# Simulate CI pipeline locally
[group('ci')]
ci: validate-all test-all
    @echo "✅ CI pipeline passed"

# Simulate PR checks
[group('ci')]
ci-pr: validate-all test-parallel
    @echo "✅ PR checks passed"

# Generate coverage badge
[group('ci')]
coverage-badge:
    {{pytest}} --no-testmon --cov --cov-report=json
    @echo "Coverage: $(python -c 'import json; print(json.load(open(\"coverage.json\"))[\"totals\"][\"percent_covered\"])')%"

# ============================================================================
# Special Recipes
# ============================================================================

# Run everything (full validation)
all: clean-all install-all validate-all test-all
    @echo "✅ Complete validation successful"

# Development workflow (format, test, commit)
dev-commit message: format test-quick
    git add -A
    git commit -m "{{message}}"

# Release checklist
release version: validate-all test-all
    @echo "🚀 Release Checklist for v{{version}}"
    @echo "  ✅ All tests passed"
    @echo "  ✅ All validations passed"
    @echo ""
    @echo "Next steps:"
    @echo "  1. Update version in pyproject.toml"
    @echo "  2. Create git tag: git tag -a v{{version}} -m 'Release v{{version}}'"
    @echo "  3. Push: git push && git push --tags"

# ============================================================================
# Recipe Groups Help
# ============================================================================

# Show test commands
test-help:
    @just --list --list-heading $'Test Commands:\n' --list-prefix '  ' | grep -A 100 "Test Commands"

# Show setup commands
setup-help:
    @just --list | grep -A 20 "setup"

# Show all groups
groups:
    @echo "Recipe Groups:"
    @echo "  setup      - Installation and setup"
    @echo "  test       - Testing commands"
    @echo "  quality    - Code quality (lint, format, type)"
    @echo "  database   - Database operations"
    @echo "  docker     - Docker operations"
    @echo "  services   - Running services"
    @echo "  docs       - Documentation (includes AI organization)"
    @echo "  config     - Configuration"
    @echo "  git        - Git operations"
    @echo "  clean      - Cleaning artifacts"
    @echo "  validate   - Validation commands"
    @echo "  ci         - CI/CD simulation"
    @echo "  advanced   - Advanced operations"
    @echo ""
    @echo "AI-Powered Features:"
    @echo "  just docs-organize              - AI-organize docs (batch, parallel)"
    @echo "  just docs-organize 10           - Use 10 concurrent workers"
    @echo "  just docs-organize-apply        - Apply AI suggestions"
    @echo "  just docs-organize-pattern PATTERN - Organize specific files"
    @echo ""
    @echo "Use 'just --list' to see all commands"

