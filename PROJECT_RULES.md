# Senior Sandbox Project Rules

**Document Purpose**: Project-specific development rules and conventions to ensure consistency and avoid common pitfalls.

**Created**: 2025-11-16

---

## Port Selection Policy

### Rule: Avoid Common Default Ports

**Problem**: Using default ports (5432 for PostgreSQL, 6379 for Redis, 8000 for web servers) causes port conflicts when multiple services or projects run on the same machine.

**Solution**: Use non-standard ports by adding 10000 to the default port number.

**Port Mapping**:
- PostgreSQL: `15432` (default: 5432)
- Redis: `16379` (default: 6379)
- Web API Server: `18000` (default: 8000)
- WebSocket Server: `18001` (default: 8001)

**Rationale**:
- Easy to remember (default + 10000)
- Avoids conflicts with system services and other projects
- Still clearly indicates the service type
- High enough to avoid conflicts with most common services

**Implementation**:
- All `docker-compose.yml` services must use non-standard exposed ports
- All connection strings and configuration files must reference these ports
- Document port mappings in README.md and docker-compose.yml comments

**Example**:
```yaml
services:
  postgres:
    ports:
      - "15432:5432"  # Non-standard port to avoid conflicts
```

---

## Additional Rules

### Database Naming
- Use descriptive database names: `senior_sandbox_dev`, `senior_sandbox_test`, `senior_sandbox_prod`
- Never use generic names like `test`, `dev`, `app`

### Environment Variables
- All service ports must be configurable via environment variables
- Use `.env` file for local development (gitignored)
- Document required environment variables in README.md

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Assistant | Initial port selection policy |

