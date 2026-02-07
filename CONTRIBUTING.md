# Contributing to OmoiOS

Thank you for your interest in contributing to OmoiOS. This guide covers how to set up your environment, submit changes, and follow project conventions.

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 22+ with pnpm
- Docker and Docker Compose
- [uv](https://docs.astral.sh/uv/) package manager
- [just](https://github.com/casey/just) command runner

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/kivo360/OmoiOS.git
   cd OmoiOS
   ```

2. **Start infrastructure services**
   ```bash
   docker-compose up -d postgres redis
   ```

3. **Install backend dependencies**
   ```bash
   cd backend
   uv sync --group test --group dev
   ```

4. **Install frontend dependencies**
   ```bash
   cd frontend
   pnpm install
   ```

5. **Set up environment variables**
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.local
   ```
   Fill in the required values. See the comments in each `.env.example` for guidance.

6. **Run database migrations**
   ```bash
   cd backend
   uv run alembic upgrade head
   ```

7. **Verify everything works**
   ```bash
   just check        # Lint + type checks
   just test          # Run tests
   ```

## Development Workflow

### Branch Naming

- `feat/<description>` — New features
- `fix/<description>` — Bug fixes
- `refactor/<description>` — Code restructuring
- `docs/<description>` — Documentation changes

### Making Changes

1. Create a branch from `main`
2. Make your changes
3. Run quality checks: `just check`
4. Run tests: `just test`
5. Open a pull request against `main`

### Useful Commands

```bash
just --list          # See all available commands
just dev-all         # Start full stack with hot-reload
just test            # Run affected tests only (fast)
just test-all        # Full test suite
just format          # Auto-format code
just lint            # Lint check
just check           # All quality checks
```

## Code Standards

### Backend (Python)

- **Formatter**: ruff format
- **Linter**: ruff
- **Type checker**: mypy (where applicable)
- **Test framework**: pytest with pytest-testmon
- Use `async/await` for I/O operations
- Use `omoi_os.utils.datetime.utc_now()` instead of `datetime.utcnow()`
- Use `structured_output()` for LLM responses needing structured data
- Never use `metadata` or `registry` as SQLAlchemy column names (reserved)

### Frontend (TypeScript)

- **Framework**: Next.js 15 with App Router
- **UI**: ShadCN UI (Radix + Tailwind)
- **State**: Zustand (client) + React Query (server)
- Follow existing component patterns in `components/`
- Use the existing API client in `lib/api/`

### Configuration

- **Application settings** go in `config/*.yaml`
- **Secrets** go in `.env` files (never committed)
- See `backend/omoi_os/config.py` for the Settings pattern

## Testing

### Running Tests

```bash
just test              # Affected tests only (~10-30s)
just test-all          # Full suite
just test-unit         # Unit tests
just test-integration  # Integration tests
```

### Writing Tests

- Place tests in `backend/tests/` following the directory structure:
  - `tests/unit/` — Fast, isolated tests
  - `tests/integration/` — Multi-component tests
  - `tests/e2e/` — Full workflow tests
- Use descriptive test names: `test_<scenario>_<expected_outcome>`
- Follow Arrange-Act-Assert pattern
- Use pytest fixtures for shared setup

## Pull Request Process

1. **Title**: Use a clear, descriptive title (e.g., "Add rate limiting to auth endpoints")
2. **Description**: Explain what changed and why
3. **Tests**: Include tests for new functionality
4. **Review**: All PRs require at least one review before merging
5. **CI**: All checks must pass

### PR Checklist

- [ ] Tests pass locally (`just test`)
- [ ] Quality checks pass (`just check`)
- [ ] New functionality has tests
- [ ] Documentation updated if needed
- [ ] No secrets or credentials in the diff

## Database Changes

If your change requires a database migration:

```bash
cd backend
uv run alembic revision -m "description of change"
# Edit the generated migration file
uv run alembic upgrade head  # Test it
```

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include reproduction steps for bugs
- Check existing issues before creating a new one

## Security

If you discover a security vulnerability, please **do not** open a public issue. See [SECURITY.md](SECURITY.md) for our responsible disclosure process.

## License

By contributing to OmoiOS, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
