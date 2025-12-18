# Sandbox Environment Variables Reference

This document lists all environment variables that can be used to configure Daytona sandbox creation and execution.

## Configuration Priority

Settings are loaded in this order (highest to lowest priority):
1. **Explicit parameters** (when calling functions programmatically)
2. **Environment variables** (set in shell or deployment platform)
3. **YAML config files** (`config/base.yaml`, `config/production.yaml`, etc.)
4. **Default values** (hardcoded in code)

## Sandbox Resource Configuration

### `SANDBOX_MEMORY_GB`
- **Description**: Memory allocation for sandboxes in GiB
- **Default**: `4`
- **Maximum**: `8` (Daytona limit)
- **YAML Config**: `daytona.sandbox_memory_gb`
- **Example**: `export SANDBOX_MEMORY_GB=8`

### `SANDBOX_CPU`
- **Description**: Number of CPU cores for sandboxes
- **Default**: `2`
- **Maximum**: `4` (Daytona limit)
- **YAML Config**: `daytona.sandbox_cpu`
- **Example**: `export SANDBOX_CPU=4`

### `SANDBOX_DISK_GB`
- **Description**: Disk space allocation for sandboxes in GiB
- **Default**: `8`
- **Maximum**: `10` (Daytona limit)
- **YAML Config**: `daytona.sandbox_disk_gb`
- **Example**: `export SANDBOX_DISK_GB=10`

## Sandbox Source Configuration

### `SANDBOX_SNAPSHOT`
- **Description**: Snapshot name to create sandbox from (takes precedence over image)
- **Default**: `claude-agent-sdk-medium` (from config)
- **YAML Config**: `daytona.snapshot`
- **Example**: `export SANDBOX_SNAPSHOT=claude-agent-sdk-medium`
- **Note**: If set, this will be used instead of `SANDBOX_IMAGE`

### `SANDBOX_IMAGE`
- **Description**: Docker image to create sandbox from (used if snapshot is not set)
- **Default**: `nikolaik/python-nodejs:python3.12-nodejs22`
- **YAML Config**: `daytona.image`
- **Example**: `export SANDBOX_IMAGE=my-custom-image:latest`
- **Note**: Only used if `SANDBOX_SNAPSHOT` is not set

## Daytona API Configuration

### `DAYTONA_API_KEY`
- **Description**: Daytona API key for authentication
- **Required**: Yes (for production)
- **YAML Config**: `daytona.api_key`
- **Example**: `export DAYTONA_API_KEY=your-api-key-here`

### `DAYTONA_API_URL`
- **Description**: Daytona API base URL
- **Default**: `https://app.daytona.io/api`
- **YAML Config**: `daytona.api_url`
- **Example**: `export DAYTONA_API_URL=https://app.daytona.io/api`

### `DAYTONA_TARGET`
- **Description**: Daytona target region
- **Default**: `us`
- **Options**: `us`, `eu`
- **YAML Config**: `daytona.target`
- **Example**: `export DAYTONA_TARGET=eu`

### `DAYTONA_SANDBOX_EXECUTION`
- **Description**: Enable sandbox execution mode (spawns Daytona sandboxes per task)
- **Default**: `false`
- **Options**: `true`, `false`
- **YAML Config**: `daytona.sandbox_execution`
- **Example**: `export DAYTONA_SANDBOX_EXECUTION=true`

## Worker Configuration (Inside Sandbox)

### `SANDBOX_ID`
- **Description**: Unique sandbox identifier
- **Required**: Yes (set automatically by spawner)
- **Example**: `SANDBOX_ID=omoios-abc123-def456`

### `CALLBACK_URL`
- **Description**: Main server base URL for event callbacks
- **Required**: Yes
- **Example**: `export CALLBACK_URL=https://api.example.com`

### `TASK_ID`
- **Description**: Task identifier for tracking
- **Required**: Yes (set automatically by spawner)
- **Example**: `TASK_ID=12dd12cf-32cc-446f-b52e-e93cc25e1fec`

### `AGENT_ID`
- **Description**: Agent identifier for tracking
- **Required**: Yes (set automatically by spawner)
- **Example**: `AGENT_ID=fb189b07-ad66-4cce-b80f-d80c553ef59f`

### `ANTHROPIC_API_KEY`
- **Description**: API key for Claude (or Z.AI token)
- **Required**: Yes
- **Example**: `export ANTHROPIC_API_KEY=your-key-here`

### `MODEL`
- **Description**: Model to use (e.g., "glm-4.6v" for Z.AI)
- **Default**: Claude's default
- **Example**: `export MODEL=glm-4.6v`

### `ANTHROPIC_BASE_URL`
- **Description**: Custom API endpoint (e.g., for GLM)
- **Example**: `export ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic`

### `HEARTBEAT_INTERVAL`
- **Description**: Heartbeat interval in seconds
- **Default**: `30`
- **Example**: `export HEARTBEAT_INTERVAL=30`

### `POLL_INTERVAL`
- **Description**: Message poll interval in seconds
- **Default**: `0.5`
- **Example**: `export POLL_INTERVAL=0.5`

### `MAX_TURNS`
- **Description**: Maximum turns per response
- **Default**: `50`
- **Example**: `export MAX_TURNS=50`

### `MAX_BUDGET_USD`
- **Description**: Maximum budget in USD
- **Default**: `10.0`
- **Example**: `export MAX_BUDGET_USD=10.0`

## Complete Example

```bash
# Daytona API Configuration
export DAYTONA_API_KEY=your-api-key
export DAYTONA_API_URL=https://app.daytona.io/api
export DAYTONA_TARGET=us
export DAYTONA_SANDBOX_EXECUTION=true

# Sandbox Resource Limits (to prevent OOM kills)
export SANDBOX_MEMORY_GB=8
export SANDBOX_CPU=4
export SANDBOX_DISK_GB=10

# Sandbox Source (snapshot takes precedence)
export SANDBOX_SNAPSHOT=claude-agent-sdk-medium
# OR use image instead:
# export SANDBOX_IMAGE=nikolaik/python-nodejs:python3.12-nodejs22

# Worker Configuration (set automatically by spawner, but shown for reference)
export SANDBOX_ID=omoios-abc123
export CALLBACK_URL=https://api.example.com
export TASK_ID=task-123
export AGENT_ID=agent-456
export ANTHROPIC_API_KEY=your-claude-key
export MODEL=glm-4.6v
export ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
```

## YAML Config File Example

Instead of environment variables, you can configure these in `config/base.yaml` or `config/production.yaml`:

```yaml
daytona:
  api_key: ${DAYTONA_API_KEY}
  api_url: https://app.daytona.io/api
  target: us
  snapshot: claude-agent-sdk-medium  # Default snapshot
  image: nikolaik/python-nodejs:python3.12-nodejs22  # Fallback image
  timeout: 300
  sandbox_execution: true
  # Resource limits
  sandbox_memory_gb: 8
  sandbox_cpu: 4
  sandbox_disk_gb: 10
```

## Notes

- **Resource Limits**: Higher memory (8 GiB) helps prevent OOM kills (exit code -9)
- **Snapshot vs Image**: Snapshots are faster to start and more consistent. Use snapshots when possible.
- **Priority**: Explicit parameters > Environment variables > YAML config > Defaults
- **Daytona Limits**: Maximum resources are 8 GiB RAM, 4 CPU cores, 10 GiB disk
