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

# Backend directory
backend_dir := "backend"

# Frontend directory
frontend_dir := "frontend"

# Frontend port
frontend_port := env_var_or_default("FRONTEND_PORT", "3000")

# Python command (runs in backend directory)
python := "uv run --active python"

# Pytest command (runs in backend directory)
pytest := "uv run --active pytest"

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
    cd {{backend_dir}} && uv sync

# Install with dev and test dependencies
[group('setup')]
install-all:
    cd {{backend_dir}} && uv sync --group dev --group test

# Setup test environment (create .env.test, config/test.yaml)
[group('setup')]
setup-test:
    cd {{backend_dir}} && ./scripts/setup_test_environment.sh

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
    cd {{backend_dir}} && {{pytest}} {{pattern}} --testmon -x

# Quick mode (quiet output)
[group('test')]
test-quick pattern="":
    cd {{backend_dir}} && {{pytest}} {{pattern}} --testmon -x -q

# Run unit tests only
[group('test')]
test-unit:
    cd {{backend_dir}} && {{pytest}} tests/unit/ --testmon -v

# Run integration tests
[group('test')]
test-integration:
    cd {{backend_dir}} && {{pytest}} tests/integration/ --testmon -v

# Run end-to-end tests
[group('test')]
test-e2e:
    cd {{backend_dir}} && {{pytest}} tests/e2e/ --testmon -v

# Run performance tests
[group('test')]
test-performance:
    cd {{backend_dir}} && {{pytest}} tests/performance/ --testmon -v

# Run ALL tests (no testmon, full suite)
[group('test')]
test-all:
    cd {{backend_dir}} && {{pytest}} --no-testmon --cov

# Run fast tests in parallel (unit tests, not slow)
[group('test')]
test-fast:
    cd {{backend_dir}} && {{pytest}} -m "unit and not slow" --testmon -x -n auto

# Run tests in parallel
[group('test')]
test-parallel workers="auto":
    cd {{backend_dir}} && {{pytest}} --testmon -n {{workers}}

# Generate HTML coverage report
[group('test')]
test-coverage:
    cd {{backend_dir}} && {{pytest}} --no-testmon --cov --cov-report=html --cov-report=term
    @echo ""
    @echo "📊 Coverage report: {{backend_dir}}/htmlcov/index.html"
    @command -v open >/dev/null && open {{backend_dir}}/htmlcov/index.html || \
     command -v xdg-open >/dev/null && xdg-open {{backend_dir}}/htmlcov/index.html || true

# Re-run only failed tests
[group('test')]
test-failed:
    cd {{backend_dir}} && {{pytest}} --lf --testmon -x

# Run tests matching a keyword
[group('test')]
test-match keyword:
    cd {{backend_dir}} && {{pytest}} -k {{keyword}} --testmon -v

# Run tests with specific marker
[group('test')]
test-mark marker:
    cd {{backend_dir}} && {{pytest}} -m {{marker}} --testmon -v

# Rebuild testmon dependency cache
[group('test')]
test-rebuild:
    @echo "🔄 Rebuilding testmon cache..."
    cd {{backend_dir}} && rm -rf .testmondata
    cd {{backend_dir}} && {{pytest}} --testmon

# Clean all test artifacts
[group('test')]
test-clean:
    @echo "🧹 Cleaning test artifacts..."
    cd {{backend_dir}} && rm -rf .testmondata .pytest_cache htmlcov .coverage coverage.xml
    cd {{backend_dir}} && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Run smoke test (critical path only)
[group('test')]
test-smoke:
    cd {{backend_dir}} && {{pytest}} -m critical --testmon -x

# Show what tests would run (dry-run)
[group('test')]
test-dry:
    cd {{backend_dir}} && {{pytest}} --testmon --collect-only

# Watch mode (requires pytest-watch)
[group('test')]
test-watch:
    cd {{backend_dir}} && uv run --active ptw -- --testmon -x

# ============================================================================
# Code Quality
# ============================================================================

# Format code with ruff and black
[group('quality')]
format:
    cd {{backend_dir}} && uv run ruff check --fix .
    cd {{backend_dir}} && uv run black .

# Lint code with ruff
[group('quality')]
lint:
    cd {{backend_dir}} && uv run --active ruff check .

# Type check with mypy
[group('quality')]
type-check:
    cd {{backend_dir}} && uv run --active mypy omoi_os

# Run all quality checks
[group('quality')]
check: lint type-check
    cd {{backend_dir}} && uv run --active black --check .

# Fix all auto-fixable issues
[group('quality')]
fix:
    cd {{backend_dir}} && uv run ruff check --fix .
    cd {{backend_dir}} && uv run black .
    @echo "✅ Auto-fixes applied"

# ============================================================================
# Database Operations
# ============================================================================

# Run all migrations
[group('database')]
db-migrate:
    cd {{backend_dir}} && uv run --active alembic upgrade head

# Create new migration
[group('database')]
db-revision message:
    cd {{backend_dir}} && uv run --active alembic revision -m "{{message}}"

# Rollback one migration
[group('database')]
db-downgrade count="1":
    cd {{backend_dir}} && uv run --active alembic downgrade -{{count}}

# Show migration history
[group('database')]
db-history:
    cd {{backend_dir}} && uv run --active alembic history

# Show current migration
[group('database')]
db-current:
    cd {{backend_dir}} && uv run --active alembic current

# ============================================================================
# Docker Operations
# ============================================================================

# Start all services
[group('docker')]
docker-up:
    cd {{backend_dir}} && docker-compose up -d

# Stop all services
[group('docker')]
docker-down:
    cd {{backend_dir}} && docker-compose down

# View logs (optionally specify service)
[group('docker')]
docker-logs service="":
    #!/usr/bin/env bash
    cd {{backend_dir}}
    if [ -z "{{service}}" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f {{service}}
    fi

# Rebuild and restart services
[group('docker')]
docker-rebuild:
    cd {{backend_dir}} && docker-compose up -d --build

# Clean Docker volumes and rebuild
[group('docker')]
docker-clean:
    cd {{backend_dir}} && docker-compose down -v
    docker-compose up -d --build

# ============================================================================
# Service Utilities
# ============================================================================

# Check if a port is in use
[group('services')]
check-port port:
    #!/usr/bin/env bash
    if lsof -Pi :{{port}} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Port {{port}} is already in use"
        echo "Process using port {{port}}:"
        lsof -Pi :{{port}} -sTCP:LISTEN
        exit 1
    else
        echo "✅ Port {{port}} is available"
        exit 0
    fi

# Kill process on a specific port
[group('services')]
kill-port port:
    #!/usr/bin/env bash
    PID=$(lsof -ti:{{port}})
    if [ -z "$PID" ]; then
        echo "ℹ️  No process found on port {{port}}"
    else
        echo "🛑 Killing process $PID on port {{port}}..."
        kill -9 $PID
        echo "✅ Process killed"
    fi

# Check status of all services (ports and health endpoints)
[group('services')]
status:
    #!/usr/bin/env bash
    echo "📊 Service Status"
    echo "=================="
    echo ""
    echo "Port {{api_port}} (Backend API):"
    if lsof -Pi :{{api_port}} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "  ✅ Running"
        PID=$(lsof -ti:{{api_port}})
        echo "  PID: $PID"
        if curl -s http://localhost:{{api_port}}/health >/dev/null 2>&1 ; then
            echo "  ✅ Health check: OK"
            HEALTH=$(curl -s http://localhost:{{api_port}}/health | head -c 100)
            echo "  Response: $HEALTH..."
        else
            echo "  ⚠️  Health check: FAILED"
        fi
    else
        echo "  ❌ Not running"
    fi
    echo ""
    echo "Port {{frontend_port}} (Frontend):"
    if lsof -Pi :{{frontend_port}} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "  ✅ Running"
        PID=$(lsof -ti:{{frontend_port}})
        echo "  PID: $PID"
        if curl -s http://localhost:{{frontend_port}} >/dev/null 2>&1 ; then
            echo "  ✅ Health check: OK"
        else
            echo "  ⚠️  Health check: FAILED"
        fi
    else
        echo "  ❌ Not running"
    fi
    echo ""
    echo "Worker processes:"
    WORKER_COUNT=$(ps aux | grep -c "[p]ython -m omoi_os.worker" || echo "0")
    if [ "$WORKER_COUNT" -gt 0 ]; then
        echo "  ✅ $WORKER_COUNT worker(s) running"
        ps aux | grep "[p]ython -m omoi_os.worker" | awk '{print "    PID: " $2}'
    else
        echo "  ❌ No workers running"
    fi

# Health check for backend API
[group('services')]
health-api:
    #!/usr/bin/env bash
    echo "🏥 Checking backend API health..."
    if curl -s http://localhost:{{api_port}}/health ; then
        echo ""
        echo "✅ Backend API is healthy"
    else
        echo "❌ Backend API health check failed"
        exit 1
    fi

# Health check for frontend
[group('services')]
health-frontend:
    #!/usr/bin/env bash
    echo "🏥 Checking frontend health..."
    if curl -s http://localhost:{{frontend_port}} >/dev/null 2>&1 ; then
        echo "✅ Frontend is healthy"
    else
        echo "❌ Frontend health check failed"
        exit 1
    fi

# Health check for all services
[group('services')]
health-all: health-api health-frontend
    @echo "✅ All services are healthy"

# Stop all running services
[group('services')]
stop-all:
    #!/usr/bin/env bash
    echo "🛑 Stopping all services..."
    echo ""
    # Kill API server
    API_PID=$(lsof -ti:{{api_port}} 2>/dev/null || true)
    if [ -n "$API_PID" ]; then
        echo "  Stopping API server (PID: $API_PID)..."
        kill -9 $API_PID 2>/dev/null || true
        echo "  ✅ API server stopped"
    else
        echo "  ℹ️  API server not running"
    fi
    # Kill frontend
    FRONTEND_PID=$(lsof -ti:{{frontend_port}} 2>/dev/null || true)
    if [ -n "$FRONTEND_PID" ]; then
        echo "  Stopping frontend (PID: $FRONTEND_PID)..."
        kill -9 $FRONTEND_PID 2>/dev/null || true
        echo "  ✅ Frontend stopped"
    else
        echo "  ℹ️  Frontend not running"
    fi
    # Kill workers
    WORKER_COUNT=$(pgrep -f "python -m omoi_os.worker" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
    if [ "$WORKER_COUNT" -gt 0 ]; then
        echo "  Stopping $WORKER_COUNT worker(s)..."
        pkill -9 -f "python -m omoi_os.worker" 2>/dev/null || true
        echo "  ✅ Workers stopped"
    else
        echo "  ℹ️  No workers running"
    fi
    echo ""
    echo "✅ All services stopped"

# Restart all services (stop then start)
[group('services')]
restart-all:
    just stop-all
    sleep 2
    just dev-all

# ============================================================================
# Running Services
# ============================================================================

# Start API server (development mode with reload)
[group('services')]
api port=api_port:
    cd {{backend_dir}} && uv run --active uvicorn omoi_os.api.main:app --host 0.0.0.0 --port {{port}} --reload

# Start worker process
[group('services')]
worker:
    cd {{backend_dir}} && uv run --active python -m omoi_os.worker

# Run smoke test
[group('services')]
smoke:
    cd {{backend_dir}} && uv run --active python scripts/smoke_test.py

# Start API and worker in parallel (requires tmux or separate terminals)
[group('services')]
dev:
    @echo "Starting services..."
    @echo "API will be at http://localhost:{{api_port}}"
    @just api &
    @sleep 2
    @just worker

# Start both backend services (API and worker) in separate terminals
# Note: This runs them in background - use 'backend-api' and 'backend-worker' 
# in separate terminal windows for better control
[group('services')]
backend-dev:
    @echo "🚀 Starting backend services..."
    @echo ""
    @echo "Starting API server..."
    @cd {{backend_dir}} && uv run --active uvicorn omoi_os.api.main:app --host 0.0.0.0 --port {{api_port}} --reload &
    @sleep 2
    @echo "Starting worker..."
    @cd {{backend_dir}} && uv run --active python -m omoi_os.worker

# Start only the API server (runs in backend directory)
[group('services')]
backend-api:
    @echo "🚀 Starting API server on port {{api_port}}..."
    @echo "API will be at http://localhost:{{api_port}}"
    cd {{backend_dir}} && uv run --active uvicorn omoi_os.api.main:app --host 0.0.0.0 --port {{api_port}} --reload

# Start only the worker (runs in backend directory)
[group('services')]
backend-worker:
    @echo "🚀 Starting worker..."
    cd {{backend_dir}} && uv run --active python -m omoi_os.worker

# ============================================================================
# Frontend Services
# ============================================================================

# Install frontend dependencies
[group('frontend')]
frontend-install:
    @echo "📦 Installing frontend dependencies..."
    cd {{frontend_dir}} && npm install

# Start frontend development server
[group('frontend')]
frontend-dev port=frontend_port:
    @echo "🚀 Starting frontend development server..."
    @echo "Frontend will be at http://localhost:{{port}}"
    cd {{frontend_dir}} && npm run dev -- -p {{port}}

# Build frontend for production
[group('frontend')]
frontend-build:
    @echo "🏗️  Building frontend for production..."
    cd {{frontend_dir}} && npm run build

# Start frontend production server
[group('frontend')]
frontend-start port=frontend_port:
    @echo "🚀 Starting frontend production server..."
    @echo "Frontend will be at http://localhost:{{port}}"
    cd {{frontend_dir}} && npm run start -- -p {{port}}

# Lint frontend code
[group('frontend')]
frontend-lint:
    @echo "🔍 Linting frontend code..."
    cd {{frontend_dir}} && npm run lint

# Type check frontend code
[group('frontend')]
frontend-type-check:
    @echo "🔍 Type checking frontend code..."
    cd {{frontend_dir}} && npx tsc --noEmit

# Run frontend linter and fix issues
[group('frontend')]
frontend-lint-fix:
    @echo "🔧 Fixing linting issues..."
    cd {{frontend_dir}} && npm run lint -- --fix

# Clean frontend build artifacts and cache
[group('frontend')]
frontend-clean:
    @echo "🧹 Cleaning frontend artifacts..."
    cd {{frontend_dir}} && rm -rf .next node_modules/.cache
    @echo "✅ Frontend artifacts cleaned"

# Clean and reinstall frontend dependencies
[group('frontend')]
frontend-clean-install:
    @echo "🧹 Cleaning and reinstalling frontend dependencies..."
    cd {{frontend_dir}} && rm -rf node_modules package-lock.json
    cd {{frontend_dir}} && npm install
    @echo "✅ Frontend dependencies reinstalled"

# Check for outdated frontend packages
[group('frontend')]
frontend-deps-check:
    @echo "🔍 Checking for outdated frontend packages..."
    cd {{frontend_dir}} && npm outdated

# Update frontend dependencies
[group('frontend')]
frontend-deps-update:
    @echo "🔄 Updating frontend dependencies..."
    cd {{frontend_dir}} && npm update

# Run all frontend checks (lint + type check)
[group('frontend')]
frontend-check: frontend-lint frontend-type-check
    @echo "✅ All frontend checks passed"

# Start all development services (backend API, worker, and frontend)
# Note: For better control, use separate terminals with 'backend-api', 'backend-worker', and 'frontend-dev'
[group('services')]
dev-all:
    #!/usr/bin/env bash
    set -e
    echo "🚀 Starting all development services..."
    echo ""
    echo "Backend API: http://localhost:{{api_port}}"
    echo "Frontend: http://localhost:{{frontend_port}}"
    echo ""
    
    # Check if ports are already in use
    if lsof -Pi :{{api_port}} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Port {{api_port}} is already in use"
        echo "   Use 'just kill-port {{api_port}}' to free the port, or"
        echo "   Use 'just stop-all' to stop all services"
        exit 1
    fi
    
    if lsof -Pi :{{frontend_port}} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Port {{frontend_port}} is already in use"
        echo "   Use 'just kill-port {{frontend_port}}' to free the port, or"
        echo "   Use 'just stop-all' to stop all services"
        exit 1
    fi
    
    echo "Starting backend API..."
    cd {{backend_dir}} && uv run --active uvicorn omoi_os.api.main:app --host 0.0.0.0 --port {{api_port}} --reload &
    API_PID=$!
    sleep 3
    
    # Wait for API to be ready
    echo "Waiting for API to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:{{api_port}}/health >/dev/null 2>&1 ; then
            echo "✅ API is ready!"
            break
        fi
        sleep 1
    done
    
    echo "Starting backend worker..."
    cd {{backend_dir}} && uv run --active python -m omoi_os.worker &
    WORKER_PID=$!
    sleep 2
    
    echo ""
    echo "✅ Backend services started"
    echo "   API PID: $API_PID"
    echo "   Worker PID: $WORKER_PID"
    echo ""
    echo "Starting frontend (this will block - press Ctrl+C to stop all services)..."
    echo ""
    
    # Cleanup function
    cleanup() {
        echo ""
        echo "🛑 Stopping all services..."
        kill $API_PID $WORKER_PID 2>/dev/null || true
        pkill -f "npm run dev" 2>/dev/null || true
        echo "✅ All services stopped"
        exit 0
    }
    
    trap cleanup SIGINT SIGTERM
    
    # Start frontend in foreground (this blocks)
    cd {{frontend_dir}} && npm run dev -- -p {{frontend_port}}
    
    # If frontend exits, cleanup
    cleanup

# ============================================================================
# Documentation
# ============================================================================

# Generate documentation index
[group('docs')]
docs-index:
    cd {{backend_dir}} && {{python}} scripts/generate_doc_index.py

# Validate documentation structure
[group('docs')]
docs-validate:
    cd {{backend_dir}} && {{python}} scripts/validate_docs.py

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
docs-organize concurrent="50":
    cd {{backend_dir}} && {{python}} scripts/organize_docs_batch.py --concurrent {{concurrent}} --detailed --export reorganization_plan.md
    @echo ""
    @echo "📋 Review the plan: reorganization_plan.md"
    @echo "Then run: just docs-organize-apply"

# Apply AI-suggested organization
[group('docs')]
docs-organize-apply concurrent="50":
    cd {{backend_dir}} && {{python}} scripts/organize_docs_batch.py --apply --detailed --concurrent {{concurrent}}

# Organize specific pattern (batch)
[group('docs')]
docs-organize-pattern pattern concurrent="25":
    cd {{backend_dir}} && {{python}} scripts/organize_docs_batch.py --pattern "{{pattern}}" --concurrent {{concurrent}} --detailed

# Organize single file (non-batch for quick test)
[group('docs')]
docs-organize-single file:
    cd {{backend_dir}} && {{python}} scripts/organize_docs.py --pattern "{{file}}"

# ============================================================================
# Configuration
# ============================================================================

# Validate all configuration files
[group('config')]
config-validate:
    cd {{backend_dir}} && {{python}} scripts/validate_config.py

# Show current configuration (for current environment)
[group('config')]
config-show section="":
    #!/usr/bin/env bash
    cd {{backend_dir}}
    if [ -z "{{section}}" ]; then
        uv run --active python -c "from omoi_os.config import _load_yaml_config; import json; print(json.dumps(_load_yaml_config(), indent=2))"
    else
        uv run --active python -c "from omoi_os.config import load_yaml_section; import json; print(json.dumps(load_yaml_section('{{section}}'), indent=2))"
    fi

# List all configuration sections
[group('config')]
config-list:
    cd {{backend_dir}} && uv run --active python -c "from omoi_os.config import _load_yaml_config; print('\n'.join(_load_yaml_config().keys()))"

# Check for configuration drift (settings without YAML or vice versa)
[group('config')]
config-check:
    cd {{backend_dir}} && {{python}} scripts/check_config_drift.py

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
    cd {{backend_dir}} && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    cd {{backend_dir}} && find . -type f -name "*.pyc" -delete
    cd {{backend_dir}} && find . -type f -name "*.pyo" -delete
    cd {{backend_dir}} && find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Clean test artifacts
[group('clean')]
clean-test:
    cd {{backend_dir}} && rm -rf .pytest_cache htmlcov .coverage coverage.xml
    cd {{backend_dir}} && rm -rf .testmondata

# Clean all artifacts
[group('clean')]
clean-all: clean-py clean-test
    cd {{backend_dir}} && rm -rf dist build
    @echo "✅ Cleaned all artifacts"

# ============================================================================
# Utilities
# ============================================================================

# Show project statistics
[group('util')]
stats:
    @echo "📊 Project Statistics"
    @echo "===================="
    @echo "Python files:  $(cd {{backend_dir}} && find omoi_os -name '*.py' | wc -l | tr -d ' ')"
    @echo "Test files:    $(cd {{backend_dir}} && find tests -name 'test_*.py' | wc -l | tr -d ' ')"
    @echo "Documentation: $(find docs -name '*.md' | wc -l | tr -d ' ')"
    @echo "Lines of code: $(cd {{backend_dir}} && find omoi_os -name '*.py' -exec wc -l {} + | tail -1 | awk '{print $1}')"
    @echo "Test coverage: $(cd {{backend_dir}} && grep -A 1 'TOTAL' htmlcov/index.html 2>/dev/null | tail -1 | grep -oP '\d+%' || echo 'Run tests first')"

# Check dependency updates
[group('util')]
deps-check:
    cd {{backend_dir}} && uv pip list --outdated

# Update dependencies
[group('util')]
deps-update:
    cd {{backend_dir}} && uv sync --upgrade

# Generate dependency tree
[group('util')]
deps-tree package="omoi_os":
    cd {{backend_dir}} && uv pip tree | grep -A 20 {{package}}

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
    @ls -1 {{backend_dir}}/config/*.yaml 2>/dev/null | sed 's/^/  - /'
    @echo "Active config: {{backend_dir}}/config/$OMOIOS_ENV.yaml (+ {{backend_dir}}/config/base.yaml)"

# ============================================================================
# Advanced Recipes
# ============================================================================

# Run a specific test file with testmon
[group('advanced')]
test-file file:
    cd {{backend_dir}} && {{pytest}} tests/{{file}} --testmon -v

# Run tests with specific marker and coverage
[group('advanced')]
test-marker-cov marker:
    cd {{backend_dir}} && {{pytest}} -m {{marker}} --testmon --cov

# Create new test file from template
[group('advanced')]
create-test category feature:
    #!/usr/bin/env bash
    set -euo pipefail
    cd {{backend_dir}}
    
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
    
    echo "✅ Created {{backend_dir}}/tests/{{category}}/test_{{feature}}.py"

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
    cd {{backend_dir}} && uv run --active python -i -c "from omoi_os.services.database import DatabaseService; from omoi_os.config import load_database_settings; print('OmoiOS shell ready')"

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
    cd {{backend_dir}} && {{pytest}} --no-testmon --cov --cov-report=json
    @echo "Coverage: $(cd {{backend_dir}} && uv run python -c 'import json; print(json.load(open(\"coverage.json\"))[\"totals\"][\"percent_covered\"])')%"

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
    @echo "  services   - Running services (backend & frontend)"
    @echo "    • status       - Check all service statuses"
    @echo "    • stop-all     - Stop all running services"
    @echo "    • restart-all  - Restart all services"
    @echo "    • health-*     - Health check commands"
    @echo "    • check-port   - Check if port is in use"
    @echo "    • kill-port    - Kill process on port"
    @echo "  frontend   - Frontend development commands"
    @echo "  docs       - Documentation (includes AI organization)"
    @echo "  config     - Configuration"
    @echo "  git        - Git operations"
    @echo "  clean      - Cleaning artifacts"
    @echo "  validate   - Validation commands"
    @echo "  ci         - CI/CD simulation"
    @echo "  advanced   - Advanced operations"
    @echo ""
    @echo "AI-Powered Features:"
    @echo "  just docs-organize              - AI-organize docs (50 concurrent workers)"
    @echo "  just docs-organize 100          - Use 100 concurrent workers (max speed)"
    @echo "  just docs-organize-apply        - Apply AI suggestions"
    @echo "  just docs-organize-pattern PATTERN - Organize specific files"
    @echo ""
    @echo "Use 'just --list' to see all commands"

