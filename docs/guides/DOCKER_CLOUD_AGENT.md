# Cloud Agent Dockerfile Usage

This Dockerfile creates a single container that runs both PostgreSQL 18 (with PGVector) and Redis, configured for use in Cursor Cloud Agents.

## Features

- **PostgreSQL 18** with PGVector extension
- **Redis** server
- **UV package manager** for Python dependency management
- **Python 3.12** environment
- Ports configured to match `.env.local` defaults:
  - PostgreSQL: `15432`
  - Redis: `16379`

## Building the Image

```bash
docker build -f Dockerfile.cloud-agent -t omoi-cloud-agent .
```

## Running the Container

```bash
docker run -d \
  -p 15432:15432 \
  -p 16379:16379 \
  --name omoi-services \
  omoi-cloud-agent
```

## Connecting to Services

### PostgreSQL
```bash
# Connection string
postgresql://postgres:postgres@localhost:15432/app_db

# Using psql
psql -h localhost -p 15432 -U postgres -d app_db
```

### Redis
```bash
# Connection string
redis://localhost:16379

# Using redis-cli
redis-cli -p 16379
```

## Using Python/UV Inside the Container

1. Enter the container:
```bash
docker exec -it omoi-services bash
```

2. Navigate to your project directory (if mounted) or set up the environment:
```bash
cd /app
uv sync
```

3. Run Python commands:
```bash
uv run python -m omoi_os.api.main
```

## Mounting Your Project

To work with your actual project code, mount it as a volume:

```bash
docker run -d \
  -p 15432:15432 \
  -p 16379:16379 \
  -v $(pwd):/app \
  --name omoi-services \
  omoi-cloud-agent
```

## Environment Variables

The container uses these defaults (matching your `.env.local`):
- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=postgres`
- `POSTGRES_DB=app_db`
- PostgreSQL port: `15432`
- Redis port: `16379`

## Health Checks

The container includes health checks for both services. Check status:

```bash
docker ps  # Should show "healthy" status
```

## Troubleshooting

### View Logs
```bash
# All logs
docker logs omoi-services

# PostgreSQL logs
docker exec omoi-services tail -f /var/log/supervisor/postgresql.out.log

# Redis logs
docker exec omoi-services tail -f /var/log/supervisor/redis.out.log
```

### Check Service Status
```bash
docker exec omoi-services supervisorctl status
```

### Restart Services
```bash
docker exec omoi-services supervisorctl restart postgresql
docker exec omoi-services supervisorctl restart redis
```

