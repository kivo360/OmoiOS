# Spec Sandbox

Spec-driven development sandbox for Claude Agent SDK. This subsystem provides an isolated, testable implementation of the spec state machine that can run locally, in tests, or in production (Daytona sandboxes).

## Features

- **Reporter Abstraction**: Same event format, different destinations
  - `ArrayReporter`: In-memory (for tests)
  - `JSONLReporter`: Append-only file (for local debugging)
  - `HTTPReporter`: HTTP callback (for production)

- **Pydantic Settings**: Configuration with `extra="ignore"` for environment flexibility

- **CLI Tools**: Run specs locally, inspect events

## Installation

```bash
cd subsystems/spec-sandbox
uv sync
```

## Quick Start

```bash
# Run full spec locally
uv run spec-sandbox run --description "Build a REST API for todo items"

# Run single phase
uv run spec-sandbox run-phase --phase explore

# Inspect events
uv run spec-sandbox inspect .spec-output/events.jsonl
```

## Testing

```bash
# Run all tests
uv run pytest

# Run reporter tests
uv run pytest tests/test_reporters/ -v

# Run with coverage
uv run pytest --cov=spec_sandbox
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SPEC_ID` | `local-spec` | Unique spec identifier |
| `REPORTER_MODE` | `jsonl` | `array`, `jsonl`, or `http` |
| `CALLBACK_URL` | None | HTTP callback URL (for production) |
| `ANTHROPIC_API_KEY` | None | Anthropic API key |
| `MAX_TURNS` | `50` | Max turns per phase |
| `MAX_BUDGET_USD` | `10.0` | Budget limit |

See `src/spec_sandbox/config.py` for full list.
