# Changelog

All notable changes to OmoiOS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-07

Initial open-source release.

### Added
- Spec-driven workflow engine (EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC)
- Multi-agent orchestration with Claude Agent SDK and OpenHands SDK
- Priority-based task queue with dependency management
- Agent health monitoring (30s heartbeats, 90s timeout)
- Intelligent Guardian with LLM-powered trajectory analysis
- Conductor service for system-wide coherence
- Redis-based event bus for real-time state
- FastAPI backend with PostgreSQL + pgvector
- Next.js 15 frontend with React Flow, ShadCN UI
- Daytona sandbox integration for isolated execution
- OAuth login (GitHub, Google, GitLab)
- Stripe billing integration
- Sentry + PostHog observability
- Comprehensive YAML-based configuration system
