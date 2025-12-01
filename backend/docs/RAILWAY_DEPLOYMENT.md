# Railway Deployment Guide
Deploy OmoiOS Backend to Railway for production use.

## Prerequisites
- [Railway CLI](https://docs.railway.com/guides/cli) installed: `brew install railway`
- Railway account with a project created
- PostgreSQL and Redis services added to your Railway project

## Quick Deploy
```bash
# 1. Login to Railway
railway login

# 2. Link to your project (if not already linked)
railway link

# 3. Deploy
railway up
```

## Project Setup (First Time)

### 1. Create Railway Project
```bash
# Create new project
railway init

# Or link existing project
railway link
```

### 2. Add Database Services

**PostgreSQL with pgvector** (for vector embeddings):
1. Deploy the pgvector template: https://railway.com/deploy/3jJFCA
2. In your API service Variables, add:
   ```
   DATABASE_URL=${{pgvector.DATABASE_URL}}
   ```

**Redis** - Add via Railway dashboard:
```bash
railway add
# Select "Redis" from the list
```
Then reference: `REDIS_URL=${{Redis.REDIS_URL}}`

### 3. Configure Environment Variables
Set these in Railway dashboard → Service → Variables:

**Required:**
```
OMOIOS_ENV=production
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
LLM_API_KEY=<your LLM API key>
DAYTONA_API_KEY=<your Daytona API key>
```

**Optional:**
```
LLM_MODEL=openai/glm-4.6
LLM_BASE_URL=https://api.z.ai/api/coding/paas/v4
GITHUB_TOKEN=<for GitHub integration>
OPENAI_API_KEY=<for embeddings>
LOGFIRE_TOKEN=<for observability>
```

**Auto-provided by Railway:**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string  
- `PORT` - Port to bind (usually 8000)
- `RAILWAY_PUBLIC_DOMAIN` - Your app's public URL

### 4. Deploy
```bash
railway up
```

## Configuration Files

### `railway.json`
Config-as-code for Railway deployment:
```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.api"
  },
  "deploy": {
    "startCommand": "python -m omoi_os.api.main",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

### `config/production.yaml`
Production configuration that reads from environment variables.

## MCP Tools Access

Once deployed, MCP tools are available at:
```
https://<your-railway-domain>/mcp
```

Agents in Daytona sandboxes can connect using:
```python
from omoi_os.services.mcp_client import MCPClientService

client = MCPClientService(mcp_url="https://<your-railway-domain>/mcp/")
await client.connect()

# Call tools
result = await client.call_tool("create_ticket", {...})
```

## Useful Commands

```bash
# View logs
railway logs

# Open dashboard
railway open

# Check service status
railway status

# Run one-off commands
railway run python -m alembic upgrade head

# SSH into container (if enabled)
railway shell
```

## Troubleshooting

### Database Connection Issues
Ensure `DATABASE_URL` is set. Railway provides this automatically when Postgres is linked.

### Migrations Not Running
Migrations run on container start. To run manually:
```bash
railway run python -m alembic upgrade head
```

### Health Check Failing
- Check `/health` endpoint returns 200
- Increase `healthcheckTimeout` in `railway.json` if startup is slow

### MCP Not Accessible
- Ensure CORS allows your Daytona sandbox IPs
- Check `/mcp` endpoint is mounted correctly

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Railway                           │
│  ┌─────────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ OmoiOS API  │──│ Postgres │  │    Redis      │  │
│  │ (Dockerfile)│  │  (PG18)  │  │   (Cache)     │  │
│  └──────┬──────┘  └──────────┘  └───────────────┘  │
│         │                                           │
│         │ /mcp endpoint                             │
└─────────┼───────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────┐
│              Daytona Sandboxes                       │
│  ┌─────────────┐  ┌─────────────┐                   │
│  │   Agent 1   │  │   Agent 2   │  ...              │
│  │ MCPClient   │  │ MCPClient   │                   │
│  └─────────────┘  └─────────────┘                   │
└─────────────────────────────────────────────────────┘
```

## Cost Optimization

- Use Railway's sleep feature for dev environments
- Scale down during low-traffic periods
- Monitor database size to stay within tier limits
