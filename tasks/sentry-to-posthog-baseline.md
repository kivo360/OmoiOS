# Sentry → PostHog Migration — Baseline

Captured 2026-04-26 before any code changes, so we can distinguish
pre-existing failures from migration regressions.

## Environment
- Python 3.13.12
- uv workspace; backend pkg is `omoi-os`
- posthog 7.5.1 already installed (spec is `>=3.0.0`, will tighten)
- sentry-sdk 2.49.0 installed (spec is `>=2.0.0`)
- Logfire is wired separately as the OpenTelemetry-style tracer
  (`omoi_os.observability.LogfireTracer`); it stays.

## Pre-existing baseline failures (NOT caused by migration)

### Env-var leak (shell vars override pytest test fixtures)
- `tests/test_config_settings.py::test_yaml_precedence_and_env_overrides`
- `tests/test_config_settings.py::test_reload_updates_legacy_settings_reference`
  - Caused by `LLM_MODEL`, `JWT_SECRET_KEY` etc. set in the user's shell
    (sourced from `/tmp/poof-tmux.env`) overriding the values the test
    sets via monkeypatch.

### Missing local Postgres (the dev DB is the prod Railway one)
- `tests/unit/test_environment_credentials_column.py` (4 errors) — tries
  to connect to `localhost:15432`; user runs against Railway via
  `DATABASE_URL`, and these tests don't honor that.

### Other env-related failures
- `tests/unit/test_feature_flags.py` (4 failures) — same env-leak pattern.
- `tests/unit/test_workspace_isolation.py` (6 errors) — fixture issues.

## Clean
- All other observability-adjacent tests pass.
- All observability imports (`omoi_os.observability.{sentry, tracing}`,
  `omoi_os.analytics.posthog`) load without error.

## Decisions for this migration

| Q | Decision |
|---|----------|
| Q1: analytics/posthog.py reuse vs rewrite | Keep as-is for product events. New module `omoi_os/observability/posthog.py` for error tracking, using v7 module-level context API. |
| Q2: tracing.py span wrappers | Convert to no-op stubs; LogfireTracer already provides distributed tracing. |
| Q3: test baseline | Run small batches via pytest, not full `just test-all`. |
| Q4: env var name | Keep `POSTHOG_API_KEY`. Bump default host from `app.posthog.com` (deprecated) to `us.i.posthog.com`. |

## Migration ordering (two commits)

1. **Add PostHog error tracking alongside Sentry** — single commit. Sentry stays running.
2. **Remove Sentry** — single commit. After Phase 8 verification passes.
