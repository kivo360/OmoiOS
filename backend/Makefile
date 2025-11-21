# OmoiOS Makefile
# Development and testing shortcuts

.DEFAULT_GOAL := help

# ============================================================================
# Testing Targets
# ============================================================================

.PHONY: test test-unit test-integration test-e2e test-all test-quick test-parallel test-coverage test-clean test-rebuild test-help

# Quick development feedback (affected tests only)
test:
	OMOIOS_ENV=test uv run pytest --testmon -x

test-quick:
	OMOIOS_ENV=test uv run pytest --testmon -x -q

# Category-specific tests
test-unit:
	OMOIOS_ENV=test uv run pytest tests/unit/ --testmon -v

test-integration:
	OMOIOS_ENV=test uv run pytest tests/integration/ --testmon -v

test-e2e:
	OMOIOS_ENV=test uv run pytest tests/e2e/ --testmon -v

test-performance:
	OMOIOS_ENV=test uv run pytest tests/performance/ --testmon -v

# Full suite (CI/pre-push)
test-all:
	OMOIOS_ENV=test uv run pytest --no-testmon --cov

# Fast tests only (unit, not slow, parallel)
test-fast:
	OMOIOS_ENV=test uv run pytest -m "unit and not slow" --testmon -x -n auto

# Parallel execution (all affected tests)
test-parallel:
	OMOIOS_ENV=test uv run pytest --testmon -n auto

# Coverage report with HTML output
test-coverage:
	OMOIOS_ENV=test uv run pytest --no-testmon --cov --cov-report=html --cov-report=term
	@echo "\n📊 Coverage report generated in htmlcov/index.html"
	@command -v open >/dev/null 2>&1 && open htmlcov/index.html || \
	 command -v xdg-open >/dev/null 2>&1 && xdg-open htmlcov/index.html || \
	 echo "Open htmlcov/index.html in your browser"

# Failed tests only
test-failed:
	OMOIOS_ENV=test uv run pytest --lf --testmon -x

# Rebuild testmon dependency graph
test-rebuild:
	@echo "🔄 Rebuilding testmon cache..."
	rm -rf .testmondata
	OMOIOS_ENV=test uv run pytest --testmon

# Clean all test artifacts
test-clean:
	@echo "🧹 Cleaning test artifacts..."
	rm -rf .testmondata .pytest_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Smoke test (critical path only)
test-smoke:
	OMOIOS_ENV=test uv run pytest -m critical --testmon -x

# Dry run (show what tests would execute)
test-dry:
	OMOIOS_ENV=test uv run pytest --testmon --collect-only

# ============================================================================
# Development Targets
# ============================================================================

.PHONY: install install-dev sync format lint type-check check

# Install dependencies
install:
	uv sync

install-dev:
	uv sync --group dev --group test

# Sync dependencies
sync:
	uv sync --group dev --group test

# Format code
format:
	uv run ruff check --fix .
	uv run black .

# Lint code
lint:
	uv run ruff check .

# Type check
type-check:
	uv run mypy omoi_os

# Run all checks (lint + type + format check)
check:
	uv run ruff check .
	uv run black --check .
	uv run mypy omoi_os

# ============================================================================
# Database Targets
# ============================================================================

.PHONY: db-migrate db-upgrade db-downgrade db-revision db-history

# Run migrations
db-migrate:
	uv run alembic upgrade head

db-upgrade:
	uv run alembic upgrade head

# Rollback one migration
db-downgrade:
	uv run alembic downgrade -1

# Create new migration
db-revision:
	@read -p "Migration message: " msg; \
	uv run alembic revision -m "$$msg"

# View migration history
db-history:
	uv run alembic history

# ============================================================================
# Docker Targets
# ============================================================================

.PHONY: docker-up docker-down docker-logs docker-rebuild

# Start all services
docker-up:
	docker-compose up -d

# Stop all services
docker-down:
	docker-compose down

# View logs
docker-logs:
	docker-compose logs -f

# Rebuild and restart
docker-rebuild:
	docker-compose up -d --build

# ============================================================================
# Running Services
# ============================================================================

.PHONY: api worker smoke

# Start API server
api:
	uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000 --reload

# Start worker
worker:
	uv run python -m omoi_os.worker

# Run smoke test
smoke:
	uv run python scripts/smoke_test.py

# ============================================================================
# Help Target
# ============================================================================

.PHONY: help

help:
	@echo "OmoiOS Development Commands"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run affected tests (quick feedback)"
	@echo "  make test-unit     - Run unit tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-all      - Run ALL tests (full suite)"
	@echo "  make test-fast     - Run fast tests in parallel"
	@echo "  make test-coverage - Generate coverage report"
	@echo "  make test-clean    - Clean test artifacts"
	@echo ""
	@echo "Development:"
	@echo "  make install       - Install dependencies"
	@echo "  make sync          - Sync all dependencies"
	@echo "  make format        - Format code (ruff + black)"
	@echo "  make lint          - Lint code (ruff)"
	@echo "  make type-check    - Type check (mypy)"
	@echo "  make check         - Run all checks"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate    - Run migrations"
	@echo "  make db-downgrade  - Rollback one migration"
	@echo "  make db-revision   - Create new migration"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up     - Start all services"
	@echo "  make docker-down   - Stop all services"
	@echo "  make docker-logs   - View logs"
	@echo ""
	@echo "Services:"
	@echo "  make api           - Start API server"
	@echo "  make worker        - Start worker"
	@echo "  make smoke         - Run smoke test"
	@echo ""
	@echo "Use 'make test-help' for detailed testing options"

