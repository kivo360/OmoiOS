# OpenHands Software Agent SDK Documentation

*Generated documentation for the OpenHands Software Agent SDK - A comprehensive Python framework for building intelligent software agents.*

---

> ⚠️ **Important**: This document covers the **OpenHands Software Agent SDK** (`openhands/software-agent-sdk`), which is a **Python SDK for building your own agents**. 
>
> For the full **OpenHands Platform** (`all-hands-ai/openhands`) with Docker sandbox, microagents, agentskills, and web UI, see **[openhands-platform.md](openhands-platform.md)**.
>
> | Feature | SDK (this doc) | Platform |
> |---------|---------------|----------|
> | Installation | `pip install openhands-sdk` | Docker or `pip install openhands-ai` |
> | Microagents | ❌ | ✅ |
> | Agent Skills (`agentskills`) | ❌ | ✅ |
> | Docker Sandbox | ❌ | ✅ |
> | Web UI | ❌ | ✅ |
> | Skills via `AgentContext` | ✅ | ✅ |

---

## Table of Contents

### Core SDK Documentation

1. [Overview](#overview)
   - [Key Features](#key-features)
2. [Quick Start](#quick-start)
   - [Basic Example](#basic-example)
3. [Core Architecture](#core-architecture)
4. [Components](#components)
   - [LLM Configuration](#llm-configuration)
   - [Agent](#agent)
   - [Tools](#tools)
   - [Conversation](#conversation)
   - [Workspace](#workspace)

### Deployment & Operations

5. [Deployment and Configuration](#deployment-and-configuration)
   - [Local vs Remote Mode](#local-vs-remote-mode)
   - [Agent Server Deployment](#agent-server-deployment)
   - [Workspace Environments](#workspace-environments)
   - [Configuration Management](#configuration-management)
6. [Security and Safety](#security-and-safety)
   - [Security Policies](#security-policies)
   - [Confirmation Mode](#confirmation-mode)
   - [Secret Management](#secret-management)
   - [Safety Mechanisms](#safety-mechanisms)

### Advanced Configuration

7. [Advanced LLM Configuration](#advanced-llm-configuration)
   - [Tool Calling Modes](#tool-calling-modes)
   - [Retry Logic and Error Handling](#retry-logic-and-error-handling)
   - [Metrics and Telemetry](#metrics-and-telemetry)
   - [Context Condensation](#context-condensation)
   - [Performance Optimizations](#performance-optimizations)
8. [Agent Server and Remote Conversations](#agent-server-and-remote-conversations)
   - [Server Architecture](#server-architecture)
   - [REST API Reference](#rest-api-reference)
   - [Conversation Lifecycle and States](#conversation-lifecycle-and-states)
   - [WebSocket Streaming](#websocket-streaming)
   - [Webhook System](#webhook-system)
   - [Python SDK with Remote Server](#python-sdk-with-remote-server)
   - [Production Best Practices & Common Pitfalls](#production-best-practices--common-pitfalls)

### Multi-User SaaS Integration (Sub-System Design)

9. [Multi-User SaaS Platform Architecture](#multi-user-saas-platform-architecture)
   - [Architecture Overview](#architecture-overview)
   - [Message Flow: Complete Request-Response Cycle](#message-flow-complete-request-response-cycle)
   - [Agent Execution Loop Flowchart](#agent-execution-loop-flowchart)
   - [Workspace Provisioning State Machine](#workspace-provisioning-state-machine)
   - [Data Flow Architecture](#data-flow-architecture)
   - [Webhook Event Flow](#webhook-event-flow)
   - [Entity Relationship Diagram](#entity-relationship-diagram)
   - [User Management and Authentication](#user-management-and-authentication)
   - [Resource Management and Scaling](#resource-management-and-scaling)
   - [Multi-Tenant Isolation](#multi-tenant-isolation)
   - [Programmatic Workspace Management with ConversationService](#programmatic-workspace-management-with-conversationservice)
10. [Custom Sandbox Integration](#custom-sandbox-integration)
    - [Workspace Architecture](#workspace-architecture)
    - [Creating Custom Workspaces](#creating-custom-workspaces)
    - [Daytona Integration Example](#daytona-integration-example)
    - [External Provider Integration](#external-provider-integration)

### Features & Patterns

11. [Skills System](#skills-system)
    - [Skill Definition](#skill-definition)
    - [Trigger Types](#trigger-types)
    - [Agent Context](#agent-context)
12. [Common Workflows](#common-workflows)
    - [Basic Agent Usage](#basic-agent-usage)
    - [Planning and Execution](#planning-and-execution)
    - [Vision Processing](#vision-processing)
13. [Persistence and State Management](#persistence-and-state-management)
    - [Conversation Persistence](#conversation-persistence)
    - [Event Callbacks](#event-callbacks)
14. [Advanced Features](#advanced-features)
    - [Multi-Agent Coordination](#multi-agent-coordination)
    - [Custom Tool Development](#custom-tool-development)
    - [MCP Integration](#mcp-integration)

### Reference & Best Practices

15. [Examples Directory](#examples-directory)
    - [Key Examples](#key-examples)
16. [Best Practices](#best-practices)
    - [Agent Design](#agent-design)
    - [Performance Optimization](#performance-optimization)
    - [Security Considerations](#security-considerations)
    - [Code Organization](#code-organization)

### SaaS Experiment & Expansion Guide

20. [SaaS Platform Experiment](#saas-platform-experiment)
    - [Experiment Overview](#experiment-overview)
    - [Experiment Architecture](#experiment-architecture)
    - [Key Integration Points](#key-integration-points)
    - [System Architecture Diagram](#system-architecture-diagram)
    - [Step 1: Create the Orchestration Layer](#step-1-create-the-orchestration-layer)
    - [Step 2: Create the Test Client](#step-2-create-the-test-client)
    - [Step 3: Run the Experiment](#step-3-run-the-experiment)
    - [Expected Output](#expected-output)
    - [Experiment Metrics to Collect](#experiment-metrics-to-collect)
    - [Experiment Variations](#experiment-variations)
    - [Troubleshooting](#troubleshooting)
21. [Expanding the Mini-SaaS Experiment](#expanding-the-mini-saas-experiment)
    - [Expansion Roadmap](#expansion-roadmap)
    - [Expansion 1: Add Database Persistence](#expansion-1-add-database-persistence)
    - [Expansion 2: Add User Authentication](#expansion-2-add-user-authentication)
    - [Expansion 3: Add Docker Workspace Support](#expansion-3-add-docker-workspace-support)
    - [Expansion 4: Add Usage Tracking and Billing](#expansion-4-add-usage-tracking-and-billing)
    - [Expansion 5: Add Redis for Distributed State](#expansion-5-add-redis-for-distributed-state)
    - [Expansion 6: Add Webhook System](#expansion-6-add-webhook-system)
    - [Putting It All Together: Production Architecture](#putting-it-all-together-production-architecture)
    - [Next Steps Checklist](#next-steps-checklist)

22. [Conclusion](#conclusion)

---

## Overview

> **Official Resources:**
> - 📦 **GitHub Repository**: [https://github.com/OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk)
> - 📚 **DeepWiki Documentation**: [https://deepwiki.com/OpenHands/software-agent-sdk](https://deepwiki.com/OpenHands/software-agent-sdk)

The OpenHands Software Agent SDK is a Python framework designed for building autonomous agents capable of understanding, modifying, and creating software. The SDK provides a composable architecture that enables developers to create agents ranging from simple code generators to complex multi-agent systems.

### Key Features

- **Modular Architecture**: Composable components (LLM, Agent, Tools, Conversation)
- **Extensible Tools**: Built-in tools for file operations, terminal commands, and more
- **Skills System**: Contextual knowledge injection with flexible triggers
- **Vision Support**: Process images alongside text for multimodal interactions
- **Persistence**: Save and restore conversation states
- **Multi-Agent Workflows**: Coordinate multiple specialized agents

---

## Quick Start

### Basic Example

```python
import os
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.terminal import TerminalTool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool

# Initialize LLM
llm = LLM(
    model="anthropic/claude-sonnet-4-5-20250929",
    api_key=os.getenv("LLM_API_KEY"),
)

# Create agent with tools
agent = Agent(
    llm=llm,
    tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
        Tool(name=TaskTrackerTool.name),
    ],
)

# Start conversation
conversation = Conversation(
    agent=agent,
    workspace=os.getcwd()
)

conversation.send_message("Write 3 facts about the current project into FACTS.txt.")
conversation.run()
print("All done!")
```

### Using the Default Agent (Recommended)

For quick setup, use the `get_default_agent()` helper which pre-configures an agent with common tools:

```python
import os
from openhands.sdk import LLM, Conversation
from openhands.tools.preset.default import get_default_agent

# Configure LLM
llm = LLM(
    model="openhands/claude-sonnet-4-5-20250929",
    api_key=os.getenv("LLM_API_KEY"),
)

# Get pre-configured agent with common tools
agent = get_default_agent(
    llm=llm,
    cli_mode=True,  # Disable browser tools for CLI usage
)

# Agent comes pre-loaded with:
# - TerminalTool (bash execution)
# - FileEditorTool (file operations)
# - TaskTrackerTool (task management)
# - Built-in tools (Finish, Think)

conversation = Conversation(agent=agent, workspace=os.getcwd())
conversation.send_message("Analyze this codebase and create a README.md with project overview.")
conversation.run()

print("Documentation created!")
```

---

## Core Architecture

```mermaid
graph TD
    User --> Conversation
    Conversation --> Agent
    Agent --> LLM
    Agent --> Tools
    Tools --> Workspace
    LLM --> Agent
    Agent --> Conversation
    Conversation --> User
```

The SDK follows a layered architecture:

1. **Conversation Layer**: Orchestrates user-agent interactions
2. **Agent Layer**: Contains decision-making logic and LLM integration
3. **Tool Layer**: Provides capabilities for interacting with the environment
4. **Workspace Layer**: Manages the file system and execution environment

---

## Components

### LLM Configuration

The `LLM` class encapsulates language model configuration and interaction.

```python
llm = LLM(
    model="anthropic/claude-sonnet-4-5-20250929",
    api_key=os.getenv("LLM_API_KEY"),
    base_url="https://api.anthropic.com",
    usage_id="my-agent-v1"
)

# Check vision capability
if llm.vision_is_active():
    print("LLM supports image processing")
```

#### Configuration Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | `str` | Model identifier (e.g., `anthropic/claude-sonnet-4-5-20250929`) |
| `api_key` | `SecretStr` | API key for authentication |
| `base_url` | `str` | API endpoint base URL |
| `usage_id` | `str` | Identifier for usage tracking |

### Agent

The `Agent` class represents an autonomous entity that uses an LLM and tools to accomplish tasks.

```python
agent = Agent(
    llm=llm,
    tools=[Tool(name=TerminalTool.name)],
    mcp_config=mcp_config  # Optional MCP server configuration
)
```

### Tools

Tools provide agents with capabilities to interact with their environment. Built-in tools include:

| Tool | Description |
|------|-------------|
| `TerminalTool` | Execute bash commands |
| `FileEditorTool` | Read and edit files |
| `TaskTrackerTool` | Track task progress |
| `GlobTool` | File pattern matching |
| `GrepTool` | Search file contents |
| `PlanningFileEditorTool` | Specialized editor for planning workflows |

### Conversation

The `Conversation` class manages the interaction flow between users and agents.

```python
conversation = Conversation(
    agent=agent,
    workspace="/path/to/project",
    callbacks=[event_handler],
    persistence_dir="/path/to/state",
    conversation_id="unique-conversation-id"
)

# Send message and run
conversation.send_message("Your task description here")
conversation.run()
```

#### Conversation Features

- **Message Management**: Handle user input and agent responses
- **Event Callbacks**: Register handlers for conversation events
- **Persistence**: Save and restore conversation state
- **Workspace Integration**: Operate within specified directories
- **Title Generation**: Auto-generate conversation titles
- **Statistics Tracking**: Monitor costs and metrics

#### Title Generation

Generate a descriptive title for the conversation using AI:

```python
from openhands.sdk import LLM, Conversation
from openhands.tools.preset.default import get_default_agent

# Configure separate LLM for title generation (optional)
title_gen_llm = LLM(
    usage_id="title-gen",
    model="openhands/gpt-5-mini-2025-08-07",
    api_key=os.getenv("LLM_API_KEY"),
)

# Generate title with specific LLM
title = conversation.generate_title(max_length=60, llm=title_gen_llm)
print(f"Conversation title: {title}")
# Output: "Analyzing project structure and creating README"
```

#### Conversation Statistics

Track costs and metrics during conversation:

```python
# After running a conversation
conversation.run()

# Get combined metrics
stats = conversation.conversation_stats.get_combined_metrics()
print(f"Total cost: ${stats.accumulated_cost}")
print(f"Total tokens: {stats.total_tokens}")
print(f"Total turns: {stats.total_turns}")

# Access detailed event information
total_events = len(conversation.state.events)
print(f"Total events: {total_events}")

# Get recent events
recent_events = conversation.state.events[-5:]
for event in recent_events:
    print(f"Event: {type(event).__name__}")
```

#### Event Callbacks

Register callbacks to track events in real-time:

```python
from openhands.sdk.event import ConversationStateUpdateEvent

received_events = []

def event_callback(event):
    event_type = type(event).__name__
    print(f"Received event: {event_type}")
    received_events.append(event)
    
    # Handle specific event types
    if isinstance(event, ConversationStateUpdateEvent):
        print(f"State update: {event}")

# Create conversation with callbacks
conversation = Conversation(
    agent=agent,
    workspace=workspace,
    callbacks=[event_callback],
)
```

### Workspace

The workspace provides the execution environment for agents, supporting:

- **Local File System**: Direct access to the local machine
- **Isolated Environments**: Docker or Kubernetes containers
- **Resource Management**: Controlled access to system resources

---

## Deployment and Configuration

### Local vs Remote Mode

The OpenHands SDK supports two primary deployment modes that determine where agent execution occurs and how conversation state is managed.

#### Local Mode
In Local Mode, the agent executes directly within your application's process using `LocalConversation`. All components, including the agent, LLM client, tools, and state management, run in the same Python process.

**Use Cases:**
- Development and debugging
- Standalone applications
- Single-user scenarios

```python
# Local conversation configuration
conversation = Conversation(
    agent=agent,
    workspace="/path/to/project",  # LocalWorkspace
    persistence_dir="./conversations",
    conversation_id="local-session-001"
)
```

#### Remote Mode
Remote Mode delegates agent execution to a separate agent server, with `RemoteConversation` acting as a thin client proxy. Communication occurs via HTTP/WebSocket.

**Use Cases:**
- Production deployments
- Multi-user applications
- Web applications
- Containerized execution

```python
# Remote conversation configuration
from openhands.sdk.workspace import RemoteWorkspace

remote_workspace = RemoteWorkspace(
    host="https://agent-server.example.com",
    working_dir="/workspace/project"
)

conversation = Conversation(
    agent=agent,
    workspace=remote_workspace  # Triggers RemoteConversation
)
```

### Agent Server Deployment

The OpenHands Agent Server is a FastAPI application that provides a REST API and WebSocket server for interacting with agents.

#### Starting the Server
```bash
# Basic server startup
uv run python -m openhands.agent_server

# With custom configuration
uv run python -m openhands.agent_server --host 0.0.0.0 --port 3000 --reload

# With custom workspace directory
uv run python -m openhands.agent_server --workspace-dir /workspace/data
```

#### Server Configuration
The agent server can be configured using environment variables or a JSON configuration file:

```json
{
  "session_api_keys": {
    "user1": "api-key-1",
    "user2": "api-key-2"
  },
  "allow_cors_origins": ["https://app.example.com"],
  "conversations_path": "/data/conversations",
  "max_concurrent_conversations": 50,
  "default_timeout": 300,
  "log_level": "INFO",
  "webhooks": [
    {
      "url": "https://webhook.example.com/events",
      "events": ["conversation.created", "conversation.completed"],
      "secret": "webhook-secret",
      "retry_attempts": 3
    }
  ],
  "security": {
    "require_auth": true,
    "max_request_size": "10MB",
    "rate_limit": {
      "requests_per_minute": 100,
      "burst_size": 20
    }
  }
}
```

```bash
# Set configuration file path
export OPENHANDS_AGENT_SERVER_CONFIG_PATH="/path/to/config.json"
```

#### Docker Deployment

##### Pre-built Images
OpenHands provides multi-architecture Docker images on GitHub Container Registry (GHCR):

```bash
# Pull the latest Python variant
docker pull ghcr.io/openhands/agent-server:latest-python

# Pull specific version
docker pull ghcr.io/openhands/agent-server:abc1234-python

# Available variants: python, java, go
docker pull ghcr.io/openhands/agent-server:abc1234-java
```

##### Basic Docker Deployment
```bash
# Run with port mapping and environment variables
docker run -it --rm \
  -p 8001:8001 \
  -e OPENAI_API_KEY=sk-... \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v /path/to/data:/workspace \
  ghcr.io/openhands/agent-server:latest-python --port 8001
```

##### Advanced Docker Configuration
```bash
# Production deployment with all features
docker run -d --name agent-server \
  -p 8001:8001 \
  -e OPENAI_API_KEY=sk-... \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e OH_SECRET_KEY=your-encryption-key \
  -e OH_ENABLE_VNC=true \
  -e LOG_LEVEL=INFO \
  -v agent-data:/workspace \
  -v agent-config:/app/config \
  --restart unless-stopped \
  --memory=2g \
  --cpus=1.0 \
  ghcr.io/openhands/agent-server:latest-python
```

##### Docker Compose Deployment
```yaml
# docker-compose.yml
version: '3.8'

services:
  agent-server:
    image: ghcr.io/openhands/agent-server:latest-python
    container_name: openhands-agent-server
    ports:
      - "8001:8001"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OH_SECRET_KEY=${OH_SECRET_KEY}
      - OH_ENABLE_VNC=${OH_ENABLE_VNC:-false}
      - LOG_LEVEL=INFO
    volumes:
      - agent-data:/workspace
      - ./config:/app/config
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    container_name: agent-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes

volumes:
  agent-data:
  redis-data:
```

```bash
# Deploy with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f agent-server

# Scale the service
docker-compose up -d --scale agent-server=3
```

#### Kubernetes Deployment

##### Basic Kubernetes Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openhands-agent-server
  labels:
    app: openhands-agent-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: openhands-agent-server
  template:
    metadata:
      labels:
        app: openhands-agent-server
    spec:
      containers:
      - name: agent-server
        image: ghcr.io/openhands/agent-server:latest-python
        ports:
        - containerPort: 8001
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openhands-secrets
              key: openai-api-key
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: openhands-secrets
              key: anthropic-api-key
        - name: OH_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: openhands-secrets
              key: oh-secret-key
        - name: LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: workspace-volume
          mountPath: /workspace
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: workspace-volume
        persistentVolumeClaim:
          claimName: workspace-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: openhands-agent-server-service
spec:
  selector:
    app: openhands-agent-server
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8001
  type: LoadBalancer
---
apiVersion: v1
kind: Secret
metadata:
  name: openhands-secrets
type: Opaque
data:
  openai-api-key: <base64-encoded-key>
  anthropic-api-key: <base64-encoded-key>
  oh-secret-key: <base64-encoded-key>
```

##### Persistent Volume Configuration
```yaml
# k8s/pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: workspace-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: fast-ssd
```

##### Horizontal Pod Autoscaler
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: openhands-agent-server-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: openhands-agent-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### Advanced Configuration

##### Custom Server Configuration
```python
# custom_server.py
from fastapi import FastAPI
from openhands.agent_server.main import create_app
import uvicorn

# Custom configuration
config = {
    "title": "Custom OpenHands Agent Server",
    "description": "Custom deployment of OpenHands Agent Server",
    "version": "1.0.0",
    "debug": False,
    "log_level": "INFO",
    "max_concurrent_conversations": 100,
    "default_timeout": 600,
}

app = create_app(config)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        workers=4,
        access_log=True,
        log_level="info"
    )
```

##### Environment Variables for Production
```bash
# .env.production
# Server Configuration
OPENHANDS_AGENT_SERVER_CONFIG_PATH=/app/config/production.json
LOG_LEVEL=INFO
MAX_CONCURRENT_CONVERSATIONS=50
DEFAULT_TIMEOUT=300

# Security
OH_SECRET_KEY=your-production-secret-key
CORS_ORIGINS=https://app.example.com,https://admin.example.com
SESSION_API_KEYS=user1=key1,user2=key2

# LLM Configuration
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
LLM_BASE_URL=https://api.anthropic.com

# Workspace Configuration
WORKSPACE_DIR=/workspace/data
ENABLE_FILE_UPLOADS=true
MAX_FILE_SIZE=10MB

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30

# Database (if using external storage)
DATABASE_URL=postgresql://user:password@db:5432/openhands
REDIS_URL=redis://redis:6379/0

# Docker-specific
OH_ENABLE_VNC=false
DOCKER_HOST=unix:///var/run/docker.sock
```

##### Load Balancing with Nginx
```nginx
# nginx.conf
upstream openhands_agent_server {
    least_conn;
    server agent-server-1:8001 max_fails=3 fail_timeout=30s;
    server agent-server-2:8001 max_fails=3 fail_timeout=30s;
    server agent-server-3:8001 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name openhands.example.com;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Client settings
    client_max_body_size 10M;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;

    location /api/ {
        proxy_pass http://openhands_agent_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /ws/ {
        proxy_pass http://openhands_agent_server;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://openhands_agent_server/api/health;
        access_log off;
    }
}
```

#### Monitoring and Observability

##### Health Checks
```bash
# Basic health check
curl http://localhost:8001/api/health

# Server status
curl http://localhost:8001/api/alive

# Server info
curl http://localhost:8001/api/server_info
```

##### Metrics Collection
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Metrics
REQUEST_COUNT = Counter('openhands_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('openhands_request_duration_seconds', 'Request duration')
ACTIVE_CONVERSATIONS = Gauge('openhands_active_conversations', 'Active conversations')
CONVERSATION_COST = Counter('openhands_conversation_cost_total', 'Total conversation cost')

# Start metrics server
start_http_server(9090)
```

##### Logging Configuration
```json
{
  "logging": {
    "version": 1,
    "disable_existing_loggers": false,
    "formatters": {
      "default": {
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
      },
      "json": {
        "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
      }
    },
    "handlers": {
      "console": {
        "class": "logging.StreamHandler",
        "formatter": "default",
        "level": "INFO"
      },
      "file": {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": "/var/log/openhands/agent-server.log",
        "maxBytes": 10485760,
        "backupCount": 5,
        "formatter": "json",
        "level": "INFO"
      }
    },
    "root": {
      "level": "INFO",
      "handlers": ["console", "file"]
    }
  }
}
```

### Workspace Environments

The SDK provides three workspace types for different deployment scenarios:

| Workspace Type | Isolation Level | Use Case |
|----------------|-----------------|----------|
| `LocalWorkspace` | None (host access) | Development, testing |
| `DockerWorkspace` | Container-level | Self-hosted production |
| `APIRemoteWorkspace` | Full isolation | Cloud/SaaS production |

#### Local Workspaces
`LocalWorkspace` provides direct filesystem access on the host machine for tool operations.

```python
from openhands.sdk.workspace import LocalWorkspace

workspace = LocalWorkspace("/path/to/project")
# or simply use a string path
workspace = "/path/to/project"
```

#### Docker Workspaces
`DockerWorkspace` provides a containerized execution environment for secure, isolated tool operations.

##### Basic Configuration
```python
from openhands.sdk.workspace import DockerWorkspace

docker_workspace = DockerWorkspace(
    base_image="python:3.11-slim",
    host_port=8080,
    environment_vars={"PYTHONPATH": "/workspace"},
    gpu_support=True
)
```

##### Complete Configuration Options

```python
from openhands.sdk.workspace import DockerWorkspace

docker_workspace = DockerWorkspace(
    # Container Image Configuration
    base_image="nikolaik/python-nodejs:python3.12-nodejs22",  # Base image
    # Or use pre-built agent server image:
    # base_image="ghcr.io/openhands/agent-server:latest-python",
    
    # Networking
    host_port=0,  # 0 = auto-assign available port
    use_host_network=False,  # Use isolated network by default
    runtime_binding_address="0.0.0.0",  # Network interface to bind
    
    # Environment Variables
    environment_vars={
        "PYTHONPATH": "/workspace",
        "NODE_ENV": "development",
        "CUSTOM_VAR": "value"
    },
    
    # Volume Mounts (host_path:container_path[:mode])
    volumes=[
        "/host/data:/workspace/data:rw",
        "/host/config:/app/config:ro"
    ],
    
    # GPU Support (requires nvidia-docker)
    gpu_support=False,  # Set True for GPU workloads
    
    # Resource Limits
    timeout=120,  # Sandbox timeout in seconds
    
    # Execution Settings
    user_id=1000,  # Run as specific user ID
    run_as_openhands=True,  # Run as openhands user
    
    # Development Features
    enable_auto_lint=False,  # Auto-lint after file edits
    initialize_plugins=True,  # Initialize sandbox plugins
    
    # Extra Dependencies
    runtime_extra_deps="",  # Additional packages to install
    # e.g., "ruby nodejs npm"
)
```

##### Custom Docker Images

Create a custom Dockerfile for specialized environments:

```dockerfile
# Dockerfile.custom-workspace
FROM nikolaik/python-nodejs:python3.12-nodejs22

# Install additional packages
RUN apt-get update && apt-get install -y \
    ruby \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install pandas numpy scikit-learn

# Install Node packages globally
RUN npm install -g typescript ts-node

# Set working directory
WORKDIR /workspace
```

Build and use:

```bash
# Build custom image
docker build -t my-custom-workspace -f Dockerfile.custom-workspace .
```

```python
# Use custom image
workspace = DockerWorkspace(
    base_image="my-custom-workspace",
    host_port=0
)
```

##### GPU-Enabled Workspaces

For machine learning workloads:

```python
# GPU workspace for ML tasks
ml_workspace = DockerWorkspace(
    base_image="nvidia/cuda:12.0-runtime-ubuntu22.04",
    gpu_support=True,
    environment_vars={
        "CUDA_VISIBLE_DEVICES": "0,1",  # Specific GPUs
        "TF_FORCE_GPU_ALLOW_GROWTH": "true"
    }
)
```

**Requirements for GPU support:**
- NVIDIA GPU drivers installed on host
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed

#### API Remote Workspaces
`APIRemoteWorkspace` uses the OpenHands runtime API for remote execution, ideal for cloud deployments and SaaS platforms.

##### Basic Configuration
```python
from openhands.sdk.workspace import APIRemoteWorkspace

api_workspace = APIRemoteWorkspace(
    runtime_api_url="https://api.example.com/runtime",
    api_key="your-api-key",
    server_image="openhands/agent-server:latest"
)
```

##### Complete Configuration Options

```python
from openhands.sdk.workspace import APIRemoteWorkspace

api_workspace = APIRemoteWorkspace(
    # Runtime API Connection
    runtime_api_url="https://runtime.example.com",  # Runtime API endpoint
    runtime_api_key="your-runtime-api-key",  # API key for runtime management
    
    # Agent Server Configuration
    server_image="ghcr.io/openhands/agent-server:latest-python",
    image_pull_policy="IfNotPresent",  # Always, IfNotPresent, Never
    
    # Session Management
    session_id="user-123-session-456",  # Unique session identifier
    # If not provided, auto-generates UUID-based session ID
    
    # Resource Allocation
    resource_factor=2,  # 1, 2, 4, or 8 (multiplier for resources)
    
    # Runtime Configuration
    runtime_class="sysbox-runc",  # Optional: enhanced isolation
    working_dir="/workspace",  # Working directory in container
    
    # Timeouts
    init_timeout=600.0,  # Max time to wait for runtime startup
    api_timeout=30.0,  # Timeout for individual API requests
    
    # Lifecycle Management
    keep_alive=False,  # Keep runtime running after cleanup
    pause_on_close=True,  # Pause instead of stop on cleanup
    
    # Environment Variables (passed to container)
    environment={
        "OPENAI_API_KEY": "...",
        "CUSTOM_VAR": "value"
    }
)
```

##### Resource Tiers for SaaS

```python
def create_workspace_for_tier(user_id: str, tier: str) -> APIRemoteWorkspace:
    """Create workspace with resources based on subscription tier."""
    
    tier_config = {
        "free": {"resource_factor": 1, "init_timeout": 120.0},
        "pro": {"resource_factor": 2, "init_timeout": 300.0},
        "enterprise": {"resource_factor": 4, "init_timeout": 600.0}
    }
    
    config = tier_config.get(tier, tier_config["free"])
    
    return APIRemoteWorkspace(
        runtime_api_url="https://runtime.example.com",
        runtime_api_key=os.getenv("RUNTIME_API_KEY"),
        server_image="ghcr.io/openhands/agent-server:latest-python",
        session_id=f"user-{user_id}-{uuid.uuid4().hex[:8]}",
        resource_factor=config["resource_factor"],
        init_timeout=config["init_timeout"],
        pause_on_close=True  # Allow resume for cost savings
    )
```

##### Workspace Lifecycle

```python
# Create workspace - starts runtime
workspace = APIRemoteWorkspace(...)

# Use workspace
with workspace:
    conversation = Conversation(agent=agent, workspace=workspace)
    conversation.send_message("Your task")
    conversation.run()
# On exit: pauses or stops runtime based on pause_on_close setting

# Resume a paused workspace
workspace = APIRemoteWorkspace(
    runtime_api_url="https://runtime.example.com",
    runtime_api_key="...",
    session_id="existing-session-id",  # Same session ID
    keep_alive=True  # Don't stop on this exit
)
```

### Configuration Management

#### Environment Variables
```bash
# LLM Configuration
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="https://api.example.com"

# Security
export OH_SECRET_KEY="your-secret-key-for-encryption"

# Agent Server
export OPENHANDS_AGENT_SERVER_CONFIG_PATH="/path/to/config.json"
```

#### Agent Configuration
```python
from openhands.sdk import Agent, LLM
from openhands.sdk.security import ConfirmRisky, SecurityRisk

agent = Agent(
    llm=llm,
    tools=[Tool(name=TerminalTool.name)],
    confirmation_policy=ConfirmRisky(
        threshold=SecurityRisk.MEDIUM,
        confirm_unknown=True
    ),
    max_iterations=100,
    stuck_detection=True
)
```

---

## Security and Safety

The OpenHands SDK provides comprehensive security features to control agent behavior and protect sensitive data.

### Security Policies

Security policies are integrated directly into the agent's system prompt and categorize actions into risk levels.

#### Risk Levels
Actions are categorized into `SecurityRisk` levels:
- **LOW**: Actions that are generally safe (e.g., reading files)
- **MEDIUM**: Actions that modify the environment (e.g., creating files)
- **HIGH**: Actions that could have significant impact (e.g., system-level operations)
- **UNKNOWN**: Actions that cannot be classified automatically

#### System Prompt Integration
The agent automatically includes security guidelines in its system prompt:
```python
# Built-in security policy structure
"""
SECURITY POLICY:

OK to do without Explicit User Consent:
- Read operations
- Analysis and inspection tasks

Do only with Explicit User Consent:
- File modifications
- Package installations
- Network operations

Never Do:
- Delete important system files
- Expose sensitive data
- Harmful operations

General Security Guidelines:
- Always verify before critical operations
- Use least privilege principle
- Report suspicious activities
"""
```

### Confirmation Mode

Confirmation mode allows users to review and approve or reject actions before execution.

#### Confirmation Policies

```python
from openhands.sdk.security import (
    ConfirmAll, ConfirmOnRisk, SecurityRisk
)

# Always require confirmation for all actions
confirm_all = ConfirmAll()

# Confirm based on risk threshold
confirm_risky = ConfirmOnRisk(
    min_risk=SecurityRisk.MEDIUM,  # Confirm MEDIUM and above
)

conversation = Conversation(
    agent=agent,
    workspace=os.getcwd(),
    confirmation_policy=confirm_risky
)
```

### AI-Powered Security Analysis

The SDK includes an `LLMSecurityAnalyzer` that uses AI to assess the risk of tool actions:

```python
import os
from openhands.sdk import LLM, Agent, Conversation
from openhands.sdk.security import (
    ConfirmAll,
    ConfirmOnRisk,
    SecurityRisk,
)
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

llm = LLM(
    model="openhands/claude-sonnet-4-5-20250929",
    api_key=os.getenv("LLM_API_KEY"),
)

# Create agent with AI-powered security analyzer
agent = Agent(
    llm=llm,
    tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
    ],
    security_analyzer=LLMSecurityAnalyzer(),  # AI-powered risk assessment
)

# Option 1: Confirm all actions (maximum security)
conversation_confirm_all = Conversation(
    agent=agent,
    workspace=os.getcwd(),
    confirmation_policy=ConfirmAll(),
)

# Option 2: Confirm only risky actions (balanced)
conversation_confirm_risky = Conversation(
    agent=agent,
    workspace=os.getcwd(),
    confirmation_policy=ConfirmOnRisk(min_risk=SecurityRisk.MEDIUM),
)

# The AI analyzer will assess risk for commands like:
conversation_confirm_risky.send_message(
    "List all files in the current directory, then delete any test files."
)

# Agent requests confirmation for high-risk operations
# User can approve/reject via conversation.state.pending_confirmations
conversation_confirm_risky.run()
```

#### Security Analyzer Benefits

| Feature | Description |
|---------|-------------|
| **Context-Aware** | Analyzes commands in the context of the conversation |
| **Risk Classification** | Automatically categorizes operations by risk level |
| **Explanation** | Provides reasons for risk assessments |
| **Configurable** | Works with different confirmation policies |

#### Dynamic Confirmation Management
```python
# Update confirmation policy during conversation
conversation.set_confirmation_policy(
    ConfirmRisky(threshold=SecurityRisk.HIGH)
)

# Temporarily disable confirmation for trusted operations
conversation.set_confirmation_policy(NeverConfirm())
```

### Secret Management

The SDK provides robust secret management to protect sensitive data like API keys and credentials.

#### Secret Registry
```python
from openhands.sdk.secrets import SecretRegistry, StaticSecret, LookupSecret

# Register secrets
secrets = SecretRegistry()
secrets.add_secret(
    "API_KEY",
    StaticSecret("your-api-key-here")
)

secrets.add_secret(
    "DATABASE_URL",
    LookupSecret(url="https://secret-manager.example.com/db-url")
)

# Configure conversation with secrets
conversation = Conversation(
    agent=agent,
    workspace=".",
    secrets=secrets
)
```

#### Secret Masking
The system automatically masks secrets in command outputs to prevent accidental exposure:

```python
# If API_KEY is a registered secret:
agent.send_message("echo $API_KEY")
# Output: <secret-hidden> instead of the actual key
```

#### Secret Persistence
```bash
# Set secret key for encrypting stored secrets
export OH_SECRET_KEY="your-encryption-key"
```

**Note:** Without `OH_SECRET_KEY`, secrets won't be persisted between restarts.

### Safety Mechanisms

#### Maximum Iterations
Prevent infinite loops by setting iteration limits:

```python
conversation = Conversation(
    agent=agent,
    workspace=".",
    max_iterations=50  # Stop after 50 agent steps
)
```

#### Stuck Detection
Enable stuck detection to identify when the agent is not making progress:

```python
conversation = Conversation(
    agent=agent,
    workspace=".",
    stuck_detection=True,  # Enable stuck detection
    max_iterations=100
)
```

#### Agent Reconciliation
When resuming conversations, the system automatically:
- Reconciles agent configuration with stored state
- Prioritizes runtime API keys over persisted ones (secrets aren't serialized)
- Validates tool configurations
- Checks LLM model compatibility

---

## Advanced LLM Configuration

### Tool Calling Modes

The SDK supports two modes for tool calling, each with different trade-offs:

#### Native Tool Calling (Default)
Tools are passed directly to the LLM via the LiteLLM interface:

```python
llm = LLM(
    model="anthropic/claude-sonnet-4-5-20250929",
    api_key="your-api-key",
    native_tool_calling=True  # Default
)
```

**Benefits:**
- Better performance with modern models
- Structured tool calling
- Reliable parameter extraction

#### Non-Native Tool Calling (Prompt-based)
Uses XML-style tool calling in prompts:

```python
llm = LLM(
    model="gpt-3.5-turbo",
    api_key="your-api-key",
    native_tool_calling=False
)
```

**Benefits:**
- Compatible with older models
- Transparent process
- Debuggable tool calls

### Retry Logic and Error Handling

#### Retry Configuration
```python
llm = LLM(
    model="anthropic/claude-sonnet-4-5-20250929",
    api_key="your-api-key",
    num_retries=5,              # Maximum retry attempts (default: 5)
    retry_multiplier=8.0,       # Exponential backoff multiplier
    retry_min_wait=8,           # Minimum wait time in seconds
    retry_max_wait=64           # Maximum wait time in seconds
)
```

#### Retry Listener
Monitor retry attempts with a custom callback:

```python
def retry_callback(attempt: int, error: Exception):
    print(f"Retry attempt {attempt}: {error}")

llm = LLM(
    model="anthropic/claude-sonnet-4-5-20250929",
    api_key="your-api-key",
    retry_listener=retry_callback
)
```

#### Handled Exception Types
The SDK automatically retries for these transient errors:
- `APIConnectionError`
- `RateLimitError`
- `ServiceUnavailableError`
- Timeout errors

### Metrics and Telemetry

#### Usage Metrics
Track costs and token usage:

```python
llm = LLM(model="anthropic/claude-sonnet-4-5-20250929", api_key="your-api-key")

# After some usage...
metrics = llm.metrics
print(f"Total cost: ${metrics.accumulated_cost:.4f}")
print(f"Total tokens: {metrics.accumulated_token_usage}")
print(f"Average latency: {metrics.average_latency:.2f}s")
```

#### Custom Telemetry
```python
from openhands.sdk.llm import Telemetry

class CustomTelemetry(Telemetry):
    def on_request(self, messages, tools, **kwargs):
        # Log request details
        self.log_info(f"Request with {len(messages)} messages")

    def on_response(self, response, start_time, **kwargs):
        # Log response details
        latency = time.time() - start_time
        self.log_info(f"Response in {latency:.2f}s")

llm = LLM(
    model="anthropic/claude-sonnet-4-5-20250929",
    api_key="your-api-key",
    telemetry=CustomTelemetry()
)
```

### Context Condensation

#### Automatic Summarization
For long conversations, the SDK automatically condenses context when approaching limits:

```python
from openhands.sdk.condenser import LLMSummarizingCondenser

condenser = LLMSummarizingCondenser(
    max_size=10000,  # Maximum events before condensation
    summarization_llm=llm  # LLM to use for summarization
)

conversation = Conversation(
    agent=agent,
    workspace=".",
    condenser=condenser
)
```

#### Manual Context Management
```python
# Manually trigger context condensation
conversation.condense_context()

# Add custom condensation request
conversation.add_condensation_request(
    "Focus on recent errors and current task status"
)
```

### Performance Optimizations

#### Prompt Caching
For models that support it (e.g., Anthropic models), enable prompt caching:

```python
llm = LLM(
    model="anthropic/claude-sonnet-4-5-20250929",
    api_key="your-api-key"
)

# System messages are automatically marked for caching
# Reduces costs for repeated conversations
```

#### Reasoning Effort Control
For reasoning models, control the depth of thinking:

```python
llm = LLM(
    model="openai/o1-preview",
    api_key="your-api-key",
    reasoning_effort="medium"  # "low", "medium", "high", "none"
)
```

#### Extended Thinking Budget
For Anthropic models with extended thinking:

```python
llm = LLM(
    model="anthropic/claude-sonnet-4-5-20250929",
    api_key="your-api-key",
    extended_thinking_budget=10000  # Tokens for reasoning
)
```

#### Token Counting
Estimate token usage before sending requests:

```python
messages = [{"role": "user", "content": "Your message here"}]
token_count = llm.get_token_count(messages)
print(f"Estimated tokens: {token_count}")
```

#### Responses API
For specific models (e.g., GPT-5 family), use the Responses API:

```python
llm = LLM(
    model="openai/gpt-5-preview",
    api_key="your-api-key",
    use_responses_api=True  # Enable Responses API
)
```

---

## Agent Server and Remote Conversations

The Agent Server is the deployable service layer of the OpenHands SDK. It enables multi-conversation, multi-user agent orchestration via HTTP APIs and real-time event streaming.

### Server Architecture

The agent server is built on FastAPI (`api.py:create_app`) and provides a REST API combined with WebSocket streaming for real-time communication.

#### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Agent Server                                  │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   API Server    │    │ ConversationSvc │    │  EventService   │  │
│  │  (FastAPI App)  │───▶│  (Lifecycle)    │───▶│  (Per-Convo)    │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│           │                      │                      │           │
│           ▼                      ▼                      ▼           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  Static Files   │    │    Webhooks     │    │   WebSocket     │  │
│  │   (Optional)    │    │  (Subscribers)  │    │   Streaming     │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                    SDK / Tools / Workspace                           │
└─────────────────────────────────────────────────────────────────────┘
```

#### Core Components

| Component | Responsibility |
|-----------|---------------|
| **API Server** | Entry point for FastAPI app, routes, static files, root redirects |
| **ConversationService** | Manages lifecycle of all conversations (start, update, search, count) |
| **EventService** | Manages event log/state for a single conversation (search, filter, paginate) |
| **WebhookSubscriber** | Buffers and posts event batches to external endpoints with retry logic |
| **ConversationWebhookSubscriber** | Posts conversation metadata (status changes) to webhook endpoints |
| **Config** | Server configuration including CORS, API keys, persistence paths |

#### Starting the Server

```bash
# Build the project
make build

# Start with default settings (host: 0.0.0.0, port: 8000)
uv run python -m openhands.agent_server

# Start with custom host and port
uv run python -m openhands.agent_server --host localhost --port 3000

# Start with auto-reload (for development)
uv run python -m openhands.agent_server --reload

# Or using the module directly
python -m openhands.agent_server --port 8000 --host 127.0.0.1
```

#### Server Configuration

Configure the server via a JSON configuration file:

```json
{
  "session_api_key": "your-secret-api-key",
  "allow_cors_origins": ["https://your-frontend.com"],
  "conversations_path": "workspace/conversations",
  "static_files_path": "/path/to/static/files",
  "webhooks": [
    {
      "webhook_url": "https://your-webhook-endpoint.com/events",
      "method": "POST",
      "event_buffer_size": 10,
      "num_retries": 3,
      "retry_delay": 5,
      "headers": {
        "Authorization": "Bearer your-webhook-token"
      }
    }
  ]
}
```

| Config Option | Description |
|---------------|-------------|
| `session_api_key` | API key for authenticating requests |
| `allow_cors_origins` | List of allowed CORS origins |
| `conversations_path` | Directory for conversation persistence |
| `static_files_path` | Optional path to serve static files (UI) |
| `webhooks` | Array of webhook configurations |

#### Static File Serving

The Agent Server can optionally serve static files (e.g., a web UI):

- If `static_files_path` is set and the directory exists, files are served at `/static/`
- The root endpoint `/` redirects to `/static/index.html` if present
- Directory traversal and missing file requests return 404

### REST API Reference

#### Authentication
The agent server supports optional API key authentication. Include session API key in headers:
```bash
curl -X POST "http://localhost:8000/api/conversations" \
  -H "X-Session-API-Key: your-api-key" \
  -H "Content-Type: application/json"
```

**Status Codes:**
- `200 OK`: Request successful
- `201 Created`: Resource created (for new conversations)
- `400 Bad Request`: Invalid request data or operation failed
- `401 Unauthorized`: Invalid or missing API key
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., conversation already running)
- `422 Unprocessable Entity`: Invalid request data format
- `500 Internal Server Error`: Server error

#### Search, Filter, and Pagination Patterns

Both conversations and events support advanced search, filter, sort, and pagination operations:

| Service | Filter By | Sort By | Pagination |
|---------|-----------|---------|------------|
| Conversations | `agent_status` | `created_at`, `updated_at` (asc/desc) | `limit`, `page_id` |
| Events | `kind` (MessageEvent, ActionEvent, etc.) | `timestamp` (asc/desc) | `limit`, `page_id` |

#### Complete API Endpoints

##### Conversation Management

###### Create Conversation
```bash
POST /api/conversations
Content-Type: application/json

{
  "agent": {
    "discriminator": "Agent",
    "llm": {
      "model": "openhands/claude-sonnet-4-5-20250929",
      "api_key": "your-api-key"
    },
    "tools": [
      {"name": "TerminalTool"},
      {"name": "FileEditorTool"}
    ]
  },
  "workspace": {
    "working_dir": "/workspace"
  },
  "initial_message": {
    "role": "user",
    "content": [
      {"type": "text", "text": "Create a hello.py file"}
    ],
    "run": true
  }
}

Response:
{
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

###### Get Conversation State
```bash
GET /api/conversations/{conversation_id}

Response:
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "events": [...],
  "execution_status": "completed",
  "metrics": {
    "accumulated_cost": 0.25
  }
}
```

###### Search Conversations
```bash
GET /api/conversations/search?limit=20&sort_by=UPDATED_AT_DESC

Response:
{
  "conversations": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Create and delete hello.py file",
      "updated_at": "2023-01-01T00:00:00Z",
      "execution_status": "completed"
    }
  ],
  "total": 1
}
```

###### Count Conversations
```bash
GET /api/conversations/count?status=RUNNING

Response: 42
```

###### Update Conversation
```bash
PATCH /api/conversations/{conversation_id}
Content-Type: application/json

{
  "title": "New Custom Title"
}

Response: {
  "success": true
}
```

###### Delete Conversation
```bash
DELETE /api/conversations/{conversation_id}

Response:
{
  "status": "deleted",
  "message": "Conversation 123e4567-e89b-12d3-a456-426614174000 has been permanently deleted"
}
```

##### Conversation Lifecycle

###### Run Conversation
Starts or resumes execution of an agent conversation:
```bash
POST /api/conversations/{conversation_id}/run

Response:
{
  "status": "execution_started",
  "execution_status": "running"
}
```

###### Pause Conversation
Pauses execution without terminating the conversation:
```bash
POST /api/conversations/{conversation_id}/pause

Response:
{
  "status": "paused",
  "execution_status": "paused"
}
```

###### Send Message (Add Event)
Adds a new message to the conversation history:
```bash
POST /api/conversations/{conversation_id}/events
Content-Type: application/json

{
  "role": "user",
  "content": [
    {"type": "text", "text": "Now delete that file"}
  ],
  "run": false
}

Response:
{
  "status": "message_added"
}
```

###### Get Events
Retrieve all events for a conversation:
```bash
GET /api/conversations/{conversation_id}/events

Response:
{
  "events": [
    {
      "type": "message",
      "content": "Hello, how can I help?",
      "timestamp": "2023-01-01T00:00:00Z"
    }
  ]
}
```

###### Search Events
Search events with filtering and pagination:
```bash
GET /api/conversations/{conversation_id}/events/search?limit=10

Response:
{
  "events": [
    {
      "type": "ConversationStateUpdateEvent",
      "timestamp": "2023-01-01T00:00:00Z"
    }
  ],
  "total": 15
}
```

##### Configuration Management

###### Update Secrets
```bash
POST /api/conversations/{conversation_id}/secrets
Content-Type: application/json

{
  "secrets": {
    "API_KEY": "your-api-key",
    "DATABASE_URL": "your-database-url",
    "NEW_SECRET": "new-value"
  }
}

Response: {
  "success": true
}
```

###### Set Confirmation Policy
```bash
POST /api/conversations/{conversation_id}/confirmation_policy
Content-Type: application/json

{
  "policy": {
    "policy_type": "risky",
    "threshold": "medium",
    "confirm_unknown": true
  }
}

Response: {
  "success": true
}
```

###### Set Security Analyzer
```bash
POST /api/conversations/{conversation_id}/security_analyzer
Content-Type: application/json

{
  "security_analyzer": {
    "type": "llm",
    "model": "anthropic/claude-sonnet-4-5-20250929"
  }
}

Response: {
  "success": true
}
```

###### Generate Title
Generates a human-readable title based on conversation content:
```bash
POST /api/conversations/{conversation_id}/generate_title
Content-Type: application/json

{
  "max_length": 60
}

Response:
{
  "title": "Create and delete hello.py file"
}
```

##### Server Information

###### Health Check
```bash
GET /api/health

Response: "OK"
```

###### Server Status
```bash
GET /api/alive

Response: {
  "status": "ok",
  "uptime_seconds": 3600,
  "version": "1.0.0"
}
```

###### Server Info
```bash
GET /api/server_info

Response: {
  "uptime": "2 hours, 15 minutes",
  "idle_time": "45 minutes",
  "active_conversations": 3,
  "total_conversations": 25
}
```

#### Complete curl Examples

Here's a comprehensive workflow using curl:

```bash
# 1. Start a new conversation
curl -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "agent": {
      "discriminator": "Agent",
      "llm": {
        "model": "openhands/claude-sonnet-4-5-20250929",
        "api_key": "your-api-key"
      },
      "tools": [
        {"name": "TerminalTool"},
        {"name": "FileEditorTool"}
      ]
    },
    "workspace": {
      "working_dir": "/workspace"
    },
    "initial_message": {
      "role": "user",
      "content": [
        {"type": "text", "text": "Create a hello.py file"}
      ],
      "run": true
    }
  }'

# Response: {"conversation_id": "123e4567-e89b-12d3-a456-426614174000", ...}

# 2. Send a message to existing conversation
curl -X POST http://localhost:8000/api/conversations/123e4567-e89b-12d3-a456-426614174000/events \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": [
      {"type": "text", "text": "Now delete that file"}
    ],
    "run": false
  }'

# 3. Run the conversation
curl -X POST http://localhost:8000/api/conversations/123e4567-e89b-12d3-a456-426614174000/run

# 4. Get conversation state
curl http://localhost:8000/api/conversations/123e4567-e89b-12d3-a456-426614174000

# 5. Search events in conversation
curl "http://localhost:8000/api/conversations/123e4567-e89b-12d3-a456-426614174000/events/search?limit=10"

# 6. Pause running conversation
curl -X POST http://localhost:8000/api/conversations/123e4567-e89b-12d3-a456-426614174000/pause

# 7. Generate conversation title
curl -X POST http://localhost:8000/api/conversations/123e4567-e89b-12d3-a456-426614174000/generate_title \
  -H "Content-Type: application/json" \
  -d '{"max_length": 60}'

# 8. List all conversations
curl "http://localhost:8000/api/conversations/search?limit=20&sort_by=UPDATED_AT_DESC"

# 9. Delete conversation
curl -X DELETE http://localhost:8000/api/conversations/123e4567-e89b-12d3-a456-426614174000
```

### Conversation Lifecycle and States

#### Conversation States

The conversation lifecycle is managed by the `ConversationExecutionStatus` enum, defining the possible states:

```python
from enum import Enum

class ConversationExecutionStatus(Enum):
    IDLE = "IDLE"                           # Ready to receive tasks
    RUNNING = "RUNNING"                     # Actively processing
    PAUSED = "PAUSED"                       # Paused by user
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"  # Awaiting user confirmation
    FINISHED = "FINISHED"                   # Task completed
    ERROR = "ERROR"                         # Error occurred
    STUCK = "STUCK"                         # Stuck in loop or unable to proceed
```

#### State Transitions

```mermaid
stateDiagram-v2
    [*] --> IDLE: Create Conversation
    IDLE --> RUNNING: Send Message / Run
    RUNNING --> PAUSED: Pause Request
    RUNNING --> WAITING_FOR_CONFIRMATION: Risky Action
    RUNNING --> FINISHED: Task Complete
    RUNNING --> ERROR: Error Occurs
    RUNNING --> STUCK: Stuck Detection
    PAUSED --> RUNNING: Resume Request
    WAITING_FOR_CONFIRMATION --> RUNNING: User Confirmation
    WAITING_FOR_CONFIRMATION --> PAUSED: Pause Request
    ERROR --> IDLE: Reset / New Message
    STUCK --> IDLE: Manual Intervention
    FINISHED --> IDLE: New Message
    IDLE --> [*]: Delete Conversation
```

#### State Management

```python
# Monitoring conversation state
conversation = Conversation(agent=agent, workspace=".")

# Check current state
current_status = conversation.get_status()
print(f"Current status: {current_status}")

# State-based operations
if current_status == ConversationExecutionStatus.RUNNING:
    conversation.pause()
elif current_status == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION:
    # Handle confirmation
    conversation.confirm_action(action_id="123", approved=True)
```

#### Event System

The event system is central to communication within the agent system, particularly for remote conversations and UI updates.

##### Core Event Types

```python
from openhands.sdk.event import (
    SystemPromptEvent,
    ActionEvent,
    ObservationEvent,
    MessageEvent,
    AgentErrorEvent,
    ConversationStateUpdateEvent,
    ConversationErrorEvent
)
```

###### SystemPromptEvent
Emitted during agent initialization:
```json
{
  "type": "SystemPromptEvent",
  "data": {
    "system_prompt": "You are an AI assistant...",
    "tool_schemas": {
      "bash": {
        "name": "bash",
        "description": "Execute bash commands",
        "parameters": {...}
      }
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

###### ActionEvent
Represents an action the agent intends to perform:
```json
{
  "type": "ActionEvent",
  "data": {
    "action": "bash",
    "args": {
      "command": "ls -la"
    },
    "message_id": "msg_123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

###### ObservationEvent
Contains the result of an executed action:
```json
{
  "type": "ObservationEvent",
  "data": {
    "action": "bash",
    "result": "total 24\ndrwxr-xr-x  6 user user 4096 Jan 15 10:30 .",
    "message_id": "msg_123",
    "timestamp": "2024-01-15T10:30:05Z"
  }
}
```

###### MessageEvent
Represents messages exchanged in the conversation:
```json
{
  "type": "MessageEvent",
  "data": {
    "role": "assistant",
    "content": "I can see the files in the current directory...",
    "message_id": "msg_124",
    "timestamp": "2024-01-15T10:30:10Z"
  }
}
```

###### AgentErrorEvent
Signifies an error during tool processing:
```json
{
  "type": "AgentErrorEvent",
  "data": {
    "error": "Command failed with exit code 1",
    "action": "bash",
    "message_id": "msg_123",
    "timestamp": "2024-01-15T10:30:05Z"
  }
}
```

###### ConversationStateUpdateEvent
Sent via WebSocket to synchronize state changes:
```json
{
  "type": "ConversationStateUpdateEvent",
  "data": {
    "full_state": {
      "status": "RUNNING",
      "step_count": 15,
      "cost": 0.1234,
      "last_updated": "2024-01-15T10:30:00Z"
    },
    "updated_fields": ["status", "step_count"],
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

###### ConversationErrorEvent
Represents a conversation-level failure:
```json
{
  "type": "ConversationErrorEvent",
  "data": {
    "error": "Failed to connect to LLM service",
    "error_code": "LLM_CONNECTION_ERROR",
    "recoverable": false,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### WebSocket Streaming

#### WebSocket Endpoint
Real-time event streaming via WebSocket:

```
WebSocket /conversations/{conversation_id}/events/socket
WebSocket /sockets/events/{conversation_id}
```

#### Basic Connection (JavaScript)

```javascript
// Simple WebSocket connection
const conversationId = "123e4567-e89b-12d3-a456-426614174000";
const ws = new WebSocket(`ws://localhost:8000/conversations/${conversationId}/events/socket`);

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received event:', data);
};

// Send a message to the agent
ws.send(JSON.stringify({
    type: 'message',
    content: 'Hello, agent!'
}));
```

#### Connection Management with Reconnection
The WebSocket system provides real-time event streaming with automatic reconnection:

```javascript
class ConversationWebSocket {
  constructor(conversationId, apiKey) {
    this.conversationId = conversationId;
    this.apiKey = apiKey;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second

    this.connect();
  }

  connect() {
    const wsUrl = `ws://localhost:8000/sockets/events/${this.conversationId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (event) => {
      this.handleMessage(JSON.parse(event.data));
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect();
      }, this.reconnectDelay);
      this.reconnectDelay *= 2; // Exponential backoff
    }
  }

  handleMessage(event) {
    // Validate event structure
    if (!event.type || !event.timestamp) {
      console.error('Invalid event format:', event);
      return;
    }

    switch (event.type) {
      case 'SystemPromptEvent':
        this.onSystemPrompt(event.data);
        break;
      case 'ActionEvent':
        this.onAction(event.data);
        break;
      case 'ObservationEvent':
        this.onObservation(event.data);
        break;
      case 'MessageEvent':
        this.onMessage(event.data);
        break;
      case 'AgentErrorEvent':
        this.onError(event.data);
        break;
      case 'ConversationStateUpdateEvent':
        this.onStateUpdate(event.data);
        break;
      case 'ConversationErrorEvent':
        this.onConversationError(event.data);
        break;
      default:
        console.log('Unknown event type:', event.type);
    }
  }

  // Event handlers
  onSystemPrompt(data) { /* Handle system prompt */ }
  onAction(data) { /* Handle agent action */ }
  onObservation(data) { /* Handle action result */ }
  onMessage(data) { /* Handle conversation message */ }
  onError(data) { /* Handle agent error */ }
  onStateUpdate(data) { /* Handle state update */ }
  onConversationError(data) { /* Handle conversation error */ }
}

// Usage
const wsClient = new ConversationWebSocket('conv-123', 'your-api-key');
```

#### WebSocket Event Types and Formats

##### Conversation Lifecycle Events

###### Conversation Created
```json
{
  "type": "conversation.created",
  "data": {
    "conversation_id": "conv-123",
    "status": "IDLE",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

###### Conversation Status Changed
```json
{
  "type": "conversation.status_changed",
  "data": {
    "conversation_id": "conv-123",
    "old_status": "IDLE",
    "new_status": "RUNNING",
    "reason": "message_received"
  },
  "timestamp": "2024-01-15T10:30:05Z"
}
```

##### Agent Execution Events

###### Agent Thinking
```json
{
  "type": "agent.think",
  "data": {
    "conversation_id": "conv-123",
    "step_number": 5,
    "thinking_duration_ms": 2500,
    "estimated_completion": "30s"
  },
  "timestamp": "2024-01-15T10:30:05Z"
}
```

###### Action Started
```json
{
  "type": "action.started",
  "data": {
    "conversation_id": "conv-123",
    "action_id": "action-456",
    "action_type": "bash",
    "action_args": {
      "command": "ls -la"
    },
    "step_number": 5
  },
  "timestamp": "2024-01-15T10:30:05Z"
}
```

###### Action Completed
```json
{
  "type": "action.completed",
  "data": {
    "conversation_id": "conv-123",
    "action_id": "action-456",
    "action_type": "bash",
    "result": {
      "exit_code": 0,
      "output": "total 24\ndrwxr-xr-x...",
      "duration_ms": 150
    },
    "step_number": 5
  },
  "timestamp": "2024-01-15T10:30:05Z"
}
```

##### Confirmation Events

###### Confirmation Required
```json
{
  "type": "confirmation.required",
  "data": {
    "conversation_id": "conv-123",
    "action_id": "action-456",
    "action_type": "file_editor",
    "action_args": {
      "file_path": "/etc/hosts",
      "operation": "delete"
    },
    "security_risk": "HIGH",
    "confirmation_id": "conf-789",
    "expires_at": "2024-01-15T10:35:00Z"
  },
  "timestamp": "2024-01-15T10:30:05Z"
}
```

###### Confirmation Response
```json
{
  "type": "confirmation.response",
  "data": {
    "conversation_id": "conv-123",
    "confirmation_id": "conf-789",
    "approved": false,
    "reason": "File deletion not authorized",
    "user_id": "user-123"
  },
  "timestamp": "2024-01-15T10:31:00Z"
}
```

##### Progress and Metrics Events

###### Step Progress
```json
{
  "type": "step.progress",
  "data": {
    "conversation_id": "conv-123",
    "step_number": 15,
    "total_steps": 100,
    "progress_percentage": 15,
    "current_cost": 0.0234,
    "estimated_total_cost": 0.156
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

###### Cost Updated
```json
{
  "type": "cost.updated",
  "data": {
    "conversation_id": "conv-123",
    "total_cost": 0.0456,
    "incremental_cost": 0.0022,
    "token_usage": {
      "input_tokens": 1250,
      "output_tokens": 320,
      "total_tokens": 1570
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

##### Error Events

###### Action Error
```json
{
  "type": "action.error",
  "data": {
    "conversation_id": "conv-123",
    "action_id": "action-456",
    "action_type": "bash",
    "error": {
      "code": "COMMAND_FAILED",
      "message": "Command 'invalid_command' not found",
      "exit_code": 127
    },
    "recoverable": true
  },
  "timestamp": "2024-01-15T10:30:05Z"
}
```

###### Conversation Error
```json
{
  "type": "conversation.error",
  "data": {
    "conversation_id": "conv-123",
    "error": {
      "code": "LLM_CONNECTION_FAILED",
      "message": "Unable to connect to LLM service",
      "recoverable": false
    },
    "context": {
      "attempted_model": "anthropic/claude-sonnet-4-5-20250929",
      "endpoint": "https://api.anthropic.com"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Webhook System

The Agent Server supports outbound webhooks for both event and conversation notifications via two subscriber types:

#### Webhook Types

| Subscriber | Purpose | Payload |
|------------|---------|---------|
| **WebhookSubscriber** | Event notifications | Buffered event batches |
| **ConversationWebhookSubscriber** | Conversation metadata | Status changes, title updates |

#### Webhook Configuration
```json
{
  "webhooks": [
    {
      "webhook_url": "https://your-app.example.com/webhooks/openhands",
      "method": "POST",
      "event_buffer_size": 10,
      "num_retries": 3,
      "retry_delay": 5,
      "flush_delay_ms": 1000,
      "headers": {
        "Authorization": "Bearer your-webhook-token"
      }
    }
  ]
}
```

#### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `webhook_url` | Endpoint URL for webhook delivery | Required |
| `method` | HTTP method (POST) | POST |
| `event_buffer_size` | Max events before auto-flush | 10 |
| `num_retries` | Retry attempts on failure | 3 |
| `retry_delay` | Seconds between retries | 5 |
| `flush_delay_ms` | Milliseconds before flushing buffer | 1000 |
| `headers` | Custom headers (auth tokens, etc.) | {} |

#### WebhookSubscriber Behavior

- **Buffering**: Events are buffered and posted in batches
- **Flush Triggers**: Buffer full OR flush delay exceeded
- **Retry Logic**: Failed deliveries are retried with configurable attempts
- **Re-queuing**: Events are re-queued on network errors
- **At-least-once Delivery**: Guarantees event delivery

#### ConversationWebhookSubscriber

Posts conversation metadata changes:
- Status updates (RUNNING → PAUSED → FINISHED)
- Title changes
- Session API key injection for secure calls

### Python SDK with Remote Server

#### Connecting to a Remote Agent Server

```python
import os
from pydantic import SecretStr

from openhands.sdk import LLM, Conversation, Workspace, get_logger
from openhands.sdk.event import ConversationStateUpdateEvent
from openhands.tools.preset.default import get_default_agent

logger = get_logger(__name__)

# Configure LLMs
llm = LLM(
    usage_id="agent",
    model="openhands/claude-sonnet-4-5-20250929",
    api_key=SecretStr(os.getenv("LLM_API_KEY")),
)

title_gen_llm = LLM(
    usage_id="title-gen",
    model="openhands/gpt-5-mini-2025-08-07",
    api_key=SecretStr(os.getenv("LLM_API_KEY")),
)

# Create agent configuration
agent = get_default_agent(llm=llm, cli_mode=True)

# Event tracking
received_events = []

def event_callback(event):
    event_type = type(event).__name__
    logger.info(f"Received event: {event_type}")
    received_events.append(event)

# Connect to remote workspace (server must be running)
# Start server: python -m openhands.agent_server --port 8000 --host 127.0.0.1
workspace = Workspace(host="http://localhost:8000")

# Test workspace connection
result = workspace.execute_command("pwd")
logger.info(f"Command completed with exit code {result.exit_code}")
logger.info(f"Output: {result.stdout}")

# Create remote conversation
conversation = Conversation(
    agent=agent,
    workspace=workspace,
    callbacks=[event_callback],
)

logger.info(f"Conversation ID: {conversation.state.id}")

# Send message and run
conversation.send_message(
    "Read the current repo and write 3 facts into FACTS.txt."
)

# Generate title using specific LLM
title = conversation.generate_title(max_length=60, llm=title_gen_llm)
logger.info(f"Generated title: {title}")

# Execute task
conversation.run()
logger.info(f"Agent status: {conversation.state.execution_status}")

# Access conversation events
total_events = len(conversation.state.events)
logger.info(f"Total events: {total_events}")

# Get recent events
recent_events = conversation.state.events[-5:]
for event in recent_events:
    logger.info(f"Event: {type(event).__name__}")

# Access state updates
for event in conversation.state.events:
    if isinstance(event, ConversationStateUpdateEvent):
        logger.info(f"State update: {event}")

# Get metrics
cost = conversation.conversation_stats.get_combined_metrics().accumulated_cost
print(f"Total cost: ${cost}")

# Cleanup
conversation.close()
```

#### Async Conversations in FastAPI

```python
import asyncio
import os
from pydantic import SecretStr

from openhands.sdk import (
    LLM, Agent, Conversation, Event, LLMConvertibleEvent
)
from openhands.sdk.conversation.types import ConversationCallbackType
from openhands.sdk.tool import Tool
from openhands.sdk.utils.async_utils import AsyncCallbackWrapper
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

# Configure agent
llm = LLM(
    model="openhands/claude-sonnet-4-5-20250929",
    api_key=SecretStr(os.getenv("LLM_API_KEY")),
)

agent = Agent(
    llm=llm,
    tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
    ],
)

# Async callback coroutine
async def async_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        print(f"Event: {type(event).__name__}")
        # Can perform async operations here
        await asyncio.sleep(0)  # Simulate async work

# Synchronous conversation runner
def run_conversation(callback: ConversationCallbackType):
    conversation = Conversation(
        agent=agent,
        workspace=os.getcwd(),
        callbacks=[callback]
    )

    conversation.send_message("Create hello.py that prints 'Hello, World!'")
    conversation.run()

    conversation.send_message("Now delete that file.")
    conversation.run()

# Run in async context (e.g., FastAPI endpoint)
async def main():
    loop = asyncio.get_running_loop()

    # Wrap async callback for sync conversation
    callback = AsyncCallbackWrapper(async_callback, loop)

    # Run conversation in background thread
    await loop.run_in_executor(None, run_conversation, callback)

    print("Conversation finished!")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Webhook Payload
```json
{
  "event": "conversation.completed",
  "conversation_id": "conv_123456",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "status": "completed",
    "total_cost": 0.1234,
    "duration_seconds": 120,
    "steps_completed": 25
  },
  "signature": "sha256=..."
}
```

#### Webhook Signature Verification
```python
import hmac
import hashlib

def verify_webhook_signature(payload_body, secret_token, signature_header):
    """Verify webhook signature"""
    if not signature_header:
        return False

    sha_name, signature = signature_header.split('=', 1)
    if sha_name != 'sha256':
        return False

    mac = hmac.new(secret_token.encode(), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()

    return hmac.compare_digest(expected_signature, signature)
```

### Production Best Practices & Common Pitfalls

> **⚠️ Critical Section**: This section covers real-world implementation patterns and common mistakes that cause production failures. Review carefully before deploying.

#### Configuration Reference

##### Retry Configuration

Configure retry behavior for LLM API calls to handle rate limits and transient failures:

```python
# Python configuration
from openhands.sdk import LLM

llm = LLM(
    model="openhands/claude-sonnet-4-5-20250929",
    api_key=api_key,
    num_retries=8,              # Number of retry attempts (default: 8)
    retry_min_wait=15,          # Minimum wait between retries in seconds
    retry_max_wait=120,         # Maximum wait between retries in seconds  
    retry_multiplier=2.0,       # Exponential backoff multiplier
)
```

```toml
# TOML configuration (config.toml)
[llm]
num_retries = 8
retry_min_wait = 15
retry_max_wait = 120
retry_multiplier = 2.0
```

##### Timeout Configuration

```python
# Multiple timeout types to configure
config = {
    # LLM API timeout (seconds) - how long to wait for LLM response
    "timeout": 60,
    
    # Sandbox execution timeout (seconds) - max time for command execution
    "sandbox_timeout": 300,
    
    # API request timeout (seconds) - for Agent Server REST calls
    "api_timeout": 30,
}
```

```bash
# Environment variable configuration
export LLM_TIMEOUT=60
export SANDBOX_TIMEOUT=300
```

##### Message Limits

Prevent context overflow and manage costs:

```python
# Message handling limits
max_message_chars: int = 30000      # Max chars sent to LLM per message
max_input_tokens: int = 0           # 0 = unlimited, set for cost control
max_output_tokens: int = 0          # 0 = unlimited, set for cost control

# History management (prevents context window overflow)
enable_history_truncation: bool = True
```

#### WebSocket Reconnection Patterns

##### ❌ Common Mistake: No Reconnection Logic

```javascript
// BAD: Connection dies silently
const socket = io("http://localhost:3000", {
  transports: ["websocket"],
  query: { conversation_id: "conv-123" }
});

socket.on("disconnect", (reason) => {
  console.log("Disconnected:", reason);
  // Connection lost forever - no recovery!
});
```

##### ✅ Production Pattern: Robust Reconnection

```javascript
class RobustWebSocketClient {
  constructor(serverUrl, conversationId) {
    this.serverUrl = serverUrl;
    this.conversationId = conversationId;
    this.lastEventId = -1;  // Track for resumption
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000;  // Start with 1 second
    this.maxReconnectDelay = 30000;  // Cap at 30 seconds
    this.socket = null;
  }

  connect() {
    this.socket = io(this.serverUrl, {
      transports: ["websocket"],
      query: {
        conversation_id: this.conversationId,
        latest_event_id: this.lastEventId,  // Resume from last known event
      },
      reconnection: false  // Handle manually for better control
    });

    this.socket.on("connect", () => {
      console.log("Connected to OpenHands WebSocket");
      this.reconnectAttempts = 0;  // Reset on successful connection
      this.reconnectDelay = 1000;
    });

    this.socket.on("oh_event", (event) => {
      // Track last event ID for resumption
      if (event.id && event.id > this.lastEventId) {
        this.lastEventId = event.id;
      }
      this.handleEvent(event);
    });

    this.socket.on("connect_error", (error) => {
      console.error("Connection error:", error);
      this.attemptReconnect();
    });

    this.socket.on("disconnect", (reason) => {
      console.log("Disconnected:", reason);
      
      // Only reconnect for unexpected disconnections
      if (reason !== "io client disconnect") {
        this.attemptReconnect();
      }
    });
  }

  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("Max reconnection attempts reached");
      this.onMaxReconnectFailed();
      return;
    }

    this.reconnectAttempts++;
    
    // Exponential backoff with jitter
    const jitter = Math.random() * 1000;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1) + jitter,
      this.maxReconnectDelay
    );

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => this.connect(), delay);
  }

  onMaxReconnectFailed() {
    // Notify user, trigger fallback, or escalate
    console.error("WebSocket connection permanently failed");
  }

  handleEvent(event) {
    // Process event
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
}
```

##### Key Points for WebSocket Handling

| Scenario | Recommended Action |
|----------|-------------------|
| Normal disconnect (user-initiated) | Don't reconnect |
| Server restart | Reconnect with exponential backoff |
| Network failure | Reconnect, resume from `latest_event_id` |
| Auth token expired | Refresh token, then reconnect |
| Max retries exceeded | Notify user, offer manual retry |

#### Error Handling Patterns

##### HTTP Error Codes Reference

| Code | Meaning | Recommended Handling |
|------|---------|---------------------|
| `400` | Bad Request | Check request payload format, don't retry |
| `401` | Unauthorized | Refresh auth token, retry once |
| `404` | Not Found | Conversation/resource doesn't exist, don't retry |
| `409` | Conflict | Resource state conflict (e.g., already running), check state first |
| `422` | Unprocessable | Invalid data format, fix payload |
| `429` | Rate Limited | Back off exponentially, respect `Retry-After` header |
| `500` | Server Error | Retry with exponential backoff |
| `502/503/504` | Gateway Error | Retry with exponential backoff |

##### ❌ Common Mistake: Retry Everything

```python
# BAD: Retrying non-retryable errors wastes resources
async def send_message_bad(conversation_id: str, message: str):
    for attempt in range(5):
        try:
            return await client.post(f"/conversations/{conversation_id}/events", json=payload)
        except Exception as e:
            await asyncio.sleep(2 ** attempt)  # Retries 404s, 400s, etc.
```

##### ✅ Production Pattern: Selective Retry

```python
from httpx import HTTPStatusError

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
NON_RETRYABLE_STATUS_CODES = {400, 401, 404, 409, 422}

async def send_message_with_retry(
    client: httpx.AsyncClient,
    conversation_id: str,
    message: str,
    max_retries: int = 3
) -> dict:
    """Send message with intelligent retry logic."""
    
    payload = {
        "role": "user",
        "content": [{"type": "text", "text": message}]
    }
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            response = await client.post(
                f"/api/conversations/{conversation_id}/events",
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
            
        except HTTPStatusError as e:
            last_error = e
            status_code = e.response.status_code
            
            # Don't retry client errors (except rate limits)
            if status_code in NON_RETRYABLE_STATUS_CODES:
                raise ConversationError(
                    f"Non-retryable error: {status_code}",
                    status_code=status_code,
                    response=e.response.json() if e.response.content else None
                )
            
            # Handle rate limiting
            if status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 60))
                await asyncio.sleep(retry_after)
                continue
            
            # Retry server errors with exponential backoff
            if status_code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                delay = min(2 ** attempt + random.uniform(0, 1), 30)
                await asyncio.sleep(delay)
                continue
            
            raise
            
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            last_error = e
            if attempt < max_retries:
                delay = min(2 ** attempt + random.uniform(0, 1), 30)
                await asyncio.sleep(delay)
                continue
            raise
    
    raise last_error
```

#### Conversation State Edge Cases

##### ❌ Common Mistake: Ignoring State Before Operations

```python
# BAD: Assuming conversation is ready
async def send_message(conversation_id: str, message: str):
    await client.post(f"/conversations/{conversation_id}/events", json=payload)
    await client.post(f"/conversations/{conversation_id}/run")  # Might fail if already running!
```

##### ✅ Production Pattern: State-Aware Operations

```python
async def safe_send_and_run(
    client: httpx.AsyncClient,
    conversation_id: str,
    message: str
) -> dict:
    """Send message and run conversation, respecting state."""
    
    # 1. Check current state first
    state_response = await client.get(f"/api/conversations/{conversation_id}")
    current_state = state_response.json()
    execution_status = current_state.get("execution_status", "IDLE")
    
    # 2. Handle based on current state
    if execution_status == "RUNNING":
        # Already running - just send the message, don't call /run
        await client.post(f"/api/conversations/{conversation_id}/events", json=payload)
        return {"action": "message_queued", "status": execution_status}
    
    elif execution_status == "PAUSED":
        # Resume first, then send
        await client.post(f"/api/conversations/{conversation_id}/run")
        await client.post(f"/api/conversations/{conversation_id}/events", json=payload)
        return {"action": "resumed_and_sent", "status": "RUNNING"}
    
    elif execution_status in ("IDLE", "FINISHED", "ERROR"):
        # Safe to send and run
        await client.post(f"/api/conversations/{conversation_id}/events", json=payload)
        await client.post(f"/api/conversations/{conversation_id}/run")
        return {"action": "sent_and_started", "status": "RUNNING"}
    
    elif execution_status == "WAITING_FOR_CONFIRMATION":
        raise ConversationError(
            "Conversation waiting for user confirmation",
            status="WAITING_FOR_CONFIRMATION"
        )
    
    elif execution_status == "STUCK":
        raise ConversationError(
            "Conversation is stuck and requires manual intervention",
            status="STUCK"
        )
    
    else:
        raise ConversationError(f"Unknown state: {execution_status}")
```

#### Resource Management

##### Concurrent Conversation Limits

```python
from asyncio import Semaphore
from collections import defaultdict

class ConversationLimiter:
    """Enforce per-user and system-wide conversation limits."""
    
    def __init__(
        self,
        max_per_user: int = 5,
        max_total: int = 100
    ):
        self.max_per_user = max_per_user
        self.max_total = max_total
        self.user_conversations: dict[str, set[str]] = defaultdict(set)
        self.total_semaphore = Semaphore(max_total)
        self._lock = asyncio.Lock()
    
    async def acquire(self, user_id: str, conversation_id: str) -> bool:
        """Attempt to start a new conversation."""
        async with self._lock:
            # Check per-user limit
            if len(self.user_conversations[user_id]) >= self.max_per_user:
                raise RateLimitError(
                    f"User {user_id} has reached max concurrent conversations ({self.max_per_user})"
                )
            
            # Check system-wide limit
            if self.total_semaphore.locked():
                raise RateLimitError(
                    f"System at max capacity ({self.max_total} conversations)"
                )
            
            await self.total_semaphore.acquire()
            self.user_conversations[user_id].add(conversation_id)
            return True
    
    async def release(self, user_id: str, conversation_id: str):
        """Release a conversation slot."""
        async with self._lock:
            if conversation_id in self.user_conversations[user_id]:
                self.user_conversations[user_id].discard(conversation_id)
                self.total_semaphore.release()
```

##### Resource Cleanup (Zombie Conversations)

```python
import asyncio
from datetime import datetime, timedelta

class ConversationCleaner:
    """Clean up stale/zombie conversations."""
    
    def __init__(
        self,
        client: httpx.AsyncClient,
        max_idle_minutes: int = 30,
        max_running_minutes: int = 60,
        cleanup_interval_seconds: int = 300
    ):
        self.client = client
        self.max_idle = timedelta(minutes=max_idle_minutes)
        self.max_running = timedelta(minutes=max_running_minutes)
        self.cleanup_interval = cleanup_interval_seconds
    
    async def start_cleanup_loop(self):
        """Run cleanup periodically."""
        while True:
            try:
                await self.cleanup_stale_conversations()
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")
            await asyncio.sleep(self.cleanup_interval)
    
    async def cleanup_stale_conversations(self):
        """Find and clean up stale conversations."""
        now = datetime.utcnow()
        
        # Get all conversations
        response = await self.client.get("/api/conversations/search?limit=100")
        conversations = response.json().get("conversations", [])
        
        for conv in conversations:
            conv_id = conv["conversation_id"]
            status = conv.get("execution_status", "IDLE")
            last_activity = datetime.fromisoformat(conv.get("last_event_timestamp", now.isoformat()))
            idle_duration = now - last_activity
            
            # Clean up stuck conversations
            if status == "STUCK":
                logger.warning(f"Cleaning up STUCK conversation: {conv_id}")
                await self._terminate_conversation(conv_id)
                continue
            
            # Clean up idle conversations that exceeded timeout
            if status == "IDLE" and idle_duration > self.max_idle:
                logger.info(f"Cleaning up idle conversation: {conv_id} (idle for {idle_duration})")
                await self._terminate_conversation(conv_id)
                continue
            
            # Force-pause long-running conversations
            if status == "RUNNING" and idle_duration > self.max_running:
                logger.warning(f"Force-pausing runaway conversation: {conv_id}")
                await self.client.post(f"/api/conversations/{conv_id}/pause")
    
    async def _terminate_conversation(self, conversation_id: str):
        """Safely terminate a conversation."""
        try:
            # Pause first if running
            await self.client.post(f"/api/conversations/{conversation_id}/pause")
        except:
            pass
        
        # Delete
        await self.client.delete(f"/api/conversations/{conversation_id}")
```

#### Graceful Shutdown

```python
import signal
import asyncio

class GracefulShutdownManager:
    """Handle graceful shutdown of agent conversations."""
    
    def __init__(self, orchestrator: OrchestrationLayer):
        self.orchestrator = orchestrator
        self.shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._handle_shutdown_signal)
    
    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signal."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.shutdown())
    
    async def shutdown(self, timeout_seconds: int = 30):
        """Gracefully shutdown all active conversations."""
        self.shutdown_event.set()
        
        # Get all active workspaces
        active_workspaces = self.orchestrator.get_active_workspaces()
        
        logger.info(f"Shutting down {len(active_workspaces)} active workspaces...")
        
        # Pause all conversations (preserves state)
        pause_tasks = [
            self._safe_pause(ws.workspace_id)
            for ws in active_workspaces
        ]
        
        # Wait with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*pause_tasks, return_exceptions=True),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"Shutdown timed out after {timeout_seconds}s")
        
        logger.info("Graceful shutdown complete")
    
    async def _safe_pause(self, workspace_id: str):
        """Safely pause a workspace."""
        try:
            await self.orchestrator.pause_workspace(workspace_id)
            logger.info(f"Paused workspace: {workspace_id}")
        except Exception as e:
            logger.error(f"Failed to pause workspace {workspace_id}: {e}")
```

#### Idempotency Patterns

##### ❌ Common Mistake: Duplicate Operations on Retry

```python
# BAD: Retrying creates duplicate conversations
async def create_workspace(user_id: str):
    try:
        return await client.post("/workspaces", json={"user_id": user_id})
    except TimeoutError:
        # Retry might create another workspace!
        return await client.post("/workspaces", json={"user_id": user_id})
```

##### ✅ Production Pattern: Idempotency Keys

```python
import uuid

async def create_workspace_idempotent(
    client: httpx.AsyncClient,
    user_id: str,
    idempotency_key: str | None = None
) -> dict:
    """Create workspace with idempotency protection."""
    
    # Generate or use provided idempotency key
    idempotency_key = idempotency_key or str(uuid.uuid4())
    
    headers = {
        "Idempotency-Key": idempotency_key
    }
    
    for attempt in range(3):
        try:
            response = await client.post(
                "/api/workspaces",
                json={"user_id": user_id},
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.ReadTimeout:
            # Safe to retry with same idempotency key
            continue
    
    raise WorkspaceCreationError("Failed after 3 attempts")

# Usage - store idempotency_key in your database
idempotency_key = f"create-workspace-{user_id}-{timestamp}"
workspace = await create_workspace_idempotent(client, user_id, idempotency_key)
```

#### Event Ordering and Deduplication

##### Handle Out-of-Order Events

```python
class EventProcessor:
    """Process events with ordering and deduplication."""
    
    def __init__(self):
        self.processed_event_ids: set[str] = set()
        self.last_processed_id: int = -1
        self.event_buffer: dict[int, dict] = {}
        self.max_buffer_size = 100
    
    def process_event(self, event: dict) -> bool:
        """Process event, handling duplicates and out-of-order delivery."""
        event_id = event.get("id")
        
        # Skip duplicates
        if event_id in self.processed_event_ids:
            return False
        
        # If event is next in sequence, process immediately
        if event_id == self.last_processed_id + 1:
            self._handle_event(event)
            self.last_processed_id = event_id
            self.processed_event_ids.add(event_id)
            
            # Process any buffered events that are now in order
            self._process_buffered_events()
            return True
        
        # If event is out of order, buffer it
        if event_id > self.last_processed_id + 1:
            if len(self.event_buffer) < self.max_buffer_size:
                self.event_buffer[event_id] = event
            return False
        
        # Event is old (already processed sequence), skip
        return False
    
    def _process_buffered_events(self):
        """Process buffered events that are now in sequence."""
        while self.last_processed_id + 1 in self.event_buffer:
            next_id = self.last_processed_id + 1
            event = self.event_buffer.pop(next_id)
            self._handle_event(event)
            self.last_processed_id = next_id
            self.processed_event_ids.add(next_id)
    
    def _handle_event(self, event: dict):
        """Actually process the event."""
        # Your event handling logic here
        pass
```

#### Quick Reference: Common Pitfalls Checklist

| Category | ❌ Don't | ✅ Do |
|----------|---------|-------|
| **WebSocket** | Assume connection stays alive | Implement reconnection with exponential backoff |
| **WebSocket** | Start fresh on reconnect | Resume from `latest_event_id` |
| **Retry** | Retry all errors | Only retry 429, 5xx errors |
| **Retry** | Fixed delays | Exponential backoff with jitter |
| **State** | Assume conversation is ready | Check state before operations |
| **State** | Call `/run` on running conversation | Check status first, skip if already running |
| **Resources** | Unlimited conversations | Enforce per-user and system limits |
| **Resources** | Forget cleanup | Run periodic cleanup for zombies |
| **Shutdown** | Hard kill | Pause conversations to preserve state |
| **Idempotency** | Retry creates duplicates | Use idempotency keys |
| **Events** | Assume ordered delivery | Buffer and reorder if needed |
| **Timeouts** | One timeout fits all | Configure LLM, sandbox, API timeouts separately |

---

## Multi-User SaaS Platform Architecture

This section covers how to build a multi-tenant SaaS platform using the OpenHands SDK, enabling dynamic workspace spawning for multiple users with proper isolation and resource management.

> **📝 Note on API Examples**: The code examples in this section use a **simplified API abstraction layer** for clarity. The actual Agent Server REST API endpoints (documented in [Agent Server and Remote Conversations](#agent-server-and-remote-conversations)) use a more structured format:
> - Endpoint prefix: `/api/conversations` (not `/conversations`)
> - Message format: Structured content arrays with `role` and `content` fields
> - WebSocket: `/sockets/events/{id}` or `/conversations/{id}/events/socket`
> 
> When implementing, refer to the [REST API Reference](#rest-api-reference) for exact request/response formats.

### Architecture Overview

For a SaaS application with multiple users, the **Remote Mode** deployment is recommended. In this architecture:

1. **Agent Server**: A centralized FastAPI server manages multiple concurrent conversations and workspaces
2. **ConversationService**: Maintains a dictionary of `EventService` instances, each representing an active conversation
3. **Workspaces**: Each conversation is associated with an isolated workspace (Local, Docker, or API Remote)
4. **Authentication**: Session API keys control access per user/tenant

```mermaid
graph TD
    subgraph "SaaS Platform"
        FE[Frontend Application]
        AUTH[Auth Service]
        API[Your API Layer]
    end
    
    subgraph "OpenHands Infrastructure"
        AS[Agent Server]
        CS[ConversationService]
        ES1[EventService 1]
        ES2[EventService 2]
        ES3[EventService N]
        WS1[Workspace 1]
        WS2[Workspace 2]
        WS3[Workspace N]
    end
    
    FE --> AUTH
    AUTH --> API
    API --> AS
    AS --> CS
    CS --> ES1
    CS --> ES2
    CS --> ES3
    ES1 --> WS1
    ES2 --> WS2
    ES3 --> WS3
```

### Message Flow: Complete Request-Response Cycle

This sequence diagram shows the complete flow when a user sends a message through your SaaS platform:

```mermaid
sequenceDiagram
    autonumber
    participant User as User Browser
    participant FE as Frontend App
    participant API as Your API Layer
    participant AS as Agent Server
    participant ES as EventService
    participant Agent as Agent
    participant LLM as LLM Provider
    participant Tool as Tool Executor
    participant WS as Workspace
    
    User->>FE: Send message
    FE->>API: POST /api/chat (user token)
    API->>API: Validate user session
    API->>AS: POST /conversations/{id}/events
    Note over API,AS: X-Session-API-Key header
    
    AS->>ES: send_message(content)
    ES->>Agent: Append UserMessageEvent
    ES->>Agent: run()
    
    loop Agent Execution Loop
        Agent->>Agent: prepare_llm_messages()
        Agent->>LLM: make_llm_completion()
        LLM-->>Agent: Response with tool_calls
        
        Agent->>Agent: Create ActionEvent
        Agent->>Tool: execute_action()
        Tool->>WS: Execute in workspace
        WS-->>Tool: Result
        Tool-->>Agent: ObservationEvent
        
        Agent->>ES: emit(ObservationEvent)
        ES-->>FE: WebSocket: event
    end
    
    Agent->>ES: emit(FinishEvent)
    ES-->>FE: WebSocket: conversation.finished
    FE-->>User: Display result
```

### Agent Execution Loop Flowchart

This flowchart details the decision-making process within each agent iteration:

```mermaid
flowchart TD
    START([Start Step]) --> CHECK_PENDING{Pending Actions?}
    
    CHECK_PENDING -->|Yes| EXEC_PENDING[Execute Pending Actions]
    CHECK_PENDING -->|No| PREP_MSG[Prepare LLM Messages]
    
    EXEC_PENDING --> EMIT_OBS[Emit ObservationEvents]
    EMIT_OBS --> CHECK_DONE{All Actions Done?}
    CHECK_DONE -->|No| EXEC_PENDING
    CHECK_DONE -->|Yes| PREP_MSG
    
    PREP_MSG --> CONDENSE{Context Too Large?}
    CONDENSE -->|Yes| RUN_CONDENSER[Run Condenser]
    CONDENSE -->|No| LLM_CALL
    RUN_CONDENSER --> LLM_CALL[Call LLM]
    
    LLM_CALL --> PARSE_RESP{Response Type?}
    
    PARSE_RESP -->|Tool Calls| CREATE_ACTION[Create ActionEvents]
    PARSE_RESP -->|Message Only| CREATE_MSG[Create MessageEvent]
    PARSE_RESP -->|Error| HANDLE_ERR[Handle Error]
    
    CREATE_ACTION --> CONFIRM{Requires Confirmation?}
    CONFIRM -->|Yes| WAIT_CONFIRM[Set WAITING_FOR_CONFIRMATION]
    CONFIRM -->|No| EXEC_ACTION[Execute Actions]
    
    WAIT_CONFIRM --> RETURN_WAIT([Return - Wait for User])
    
    EXEC_ACTION --> EMIT_ACTION[Emit ActionEvent]
    EMIT_ACTION --> TOOL_EXEC[Tool Executor]
    TOOL_EXEC --> WORKSPACE[Execute in Workspace]
    WORKSPACE --> EMIT_RESULT[Emit ObservationEvent]
    
    CREATE_MSG --> EMIT_MSG[Emit MessageEvent]
    EMIT_MSG --> CHECK_FINISH{Finish Tool Called?}
    
    EMIT_RESULT --> CHECK_STUCK{Stuck Pattern?}
    CHECK_STUCK -->|Yes| SET_STUCK[Set STUCK Status]
    CHECK_STUCK -->|No| CHECK_MAX{Max Iterations?}
    
    CHECK_MAX -->|Yes| SET_FINISH[Set FINISHED Status]
    CHECK_MAX -->|No| CONTINUE([Continue Loop])
    
    CHECK_FINISH -->|Yes| SET_FINISH
    CHECK_FINISH -->|No| CONTINUE
    
    HANDLE_ERR --> SET_ERROR[Set ERROR Status]
    SET_STUCK --> END_LOOP([End Loop])
    SET_FINISH --> END_LOOP
    SET_ERROR --> END_LOOP
    
    style START fill:#90EE90
    style END_LOOP fill:#FFB6C1
    style RETURN_WAIT fill:#FFE4B5
    style CONTINUE fill:#87CEEB
```

### Workspace Provisioning State Machine

This state diagram shows the lifecycle of a workspace in a SaaS environment:

```mermaid
stateDiagram-v2
    [*] --> Requested: User requests workspace
    
    Requested --> Provisioning: Resources available
    Requested --> Queued: Resources exhausted
    
    Queued --> Provisioning: Resources freed
    Queued --> Cancelled: User cancels / Timeout
    
    Provisioning --> Initializing: Container started
    Provisioning --> Failed: Provisioning error
    
    Initializing --> Ready: Health check passed
    Initializing --> Failed: Init timeout
    
    Ready --> Active: User connects
    Ready --> Idle: No activity timeout
    
    Active --> Ready: User disconnects
    Active --> Paused: User requests pause
    Active --> Terminated: Session timeout
    
    Idle --> Paused: Auto-pause policy
    Idle --> Terminated: Cleanup policy
    
    Paused --> Resuming: User requests resume
    Paused --> Terminated: Max pause duration
    
    Resuming --> Active: Resume complete
    Resuming --> Failed: Resume error
    
    Failed --> Terminated: Cleanup
    Terminated --> [*]: Resources released
    Cancelled --> [*]: No resources used
    
    note right of Active
        Billing active
        Resources allocated
    end note
    
    note right of Paused
        Billing paused
        State preserved
    end note
```

### Data Flow Architecture

This diagram shows how data flows between components in a production SaaS deployment:

```mermaid
flowchart LR
    subgraph "Client Layer"
        WEB[Web App]
        CLI[CLI Client]
        SDK_CLIENT[SDK Client]
    end
    
    subgraph "API Gateway"
        LB[Load Balancer]
        RATE[Rate Limiter]
        AUTH_GW[Auth Gateway]
    end
    
    subgraph "Application Layer"
        API_1[Agent Server 1]
        API_2[Agent Server 2]
        API_N[Agent Server N]
    end
    
    subgraph "Message Bus"
        REDIS[(Redis PubSub)]
        QUEUE[(Task Queue)]
    end
    
    subgraph "Workspace Layer"
        subgraph "Docker Pool"
            D1[Container 1]
            D2[Container 2]
            DN[Container N]
        end
        subgraph "K8s Cluster"
            K1[Pod 1]
            K2[Pod 2]
            KN[Pod N]
        end
    end
    
    subgraph "Storage Layer"
        PG[(PostgreSQL)]
        S3[(Object Storage)]
        CACHE[(Redis Cache)]
    end
    
    subgraph "External Services"
        LLM_API[LLM APIs]
        WEBHOOK[Webhooks]
        MONITOR[Monitoring]
    end
    
    WEB --> LB
    CLI --> LB
    SDK_CLIENT --> LB
    
    LB --> RATE
    RATE --> AUTH_GW
    AUTH_GW --> API_1
    AUTH_GW --> API_2
    AUTH_GW --> API_N
    
    API_1 <--> REDIS
    API_2 <--> REDIS
    API_N <--> REDIS
    
    API_1 --> QUEUE
    QUEUE --> D1
    QUEUE --> K1
    
    D1 --> S3
    K1 --> S3
    
    API_1 --> PG
    API_1 --> CACHE
    
    API_1 --> LLM_API
    API_1 --> WEBHOOK
    API_1 --> MONITOR
```

### Webhook Event Flow

This diagram shows how webhooks notify your external services:

```mermaid
sequenceDiagram
    autonumber
    participant Agent as Agent Server
    participant Buffer as Event Buffer
    participant WH as Webhook Sender
    participant EXT as Your Backend
    participant DB as Your Database
    
    Note over Agent,EXT: Event-Triggered Webhooks
    
    Agent->>Buffer: Event occurs
    Buffer->>Buffer: Add to queue
    
    alt Buffer full OR flush_delay reached
        Buffer->>WH: Flush events
        WH->>EXT: POST /events/{conversation_id}
        Note over WH,EXT: JSON array of events
        
        alt Success
            EXT->>DB: Store events
            EXT-->>WH: 200 OK
        else Failure
            EXT-->>WH: 5xx Error
            WH->>WH: Retry with backoff
            WH->>EXT: Retry POST
        end
    end
    
    Note over Agent,EXT: Lifecycle Webhooks (Immediate)
    
    Agent->>WH: Conversation started/paused/deleted
    WH->>EXT: POST /conversations
    Note over WH,EXT: ConversationInfo JSON
    EXT->>DB: Update conversation state
    EXT-->>WH: 200 OK
```

### Entity Relationship Diagram

This shows the data model for a SaaS platform using OpenHands:

```mermaid
erDiagram
    TENANT ||--o{ USER : has
    USER ||--o{ WORKSPACE : owns
    USER ||--o{ API_KEY : has
    WORKSPACE ||--|| CONVERSATION : contains
    CONVERSATION ||--o{ EVENT : generates
    CONVERSATION ||--o{ MESSAGE : contains
    WORKSPACE ||--o{ FILE : stores
    USER ||--o{ SUBSCRIPTION : has
    SUBSCRIPTION ||--|| TIER : defines
    
    TENANT {
        uuid id PK
        string name
        string domain
        timestamp created_at
        json settings
    }
    
    USER {
        uuid id PK
        uuid tenant_id FK
        string email
        string name
        timestamp created_at
        boolean active
    }
    
    API_KEY {
        uuid id PK
        uuid user_id FK
        string key_hash
        timestamp created_at
        timestamp expires_at
        json permissions
    }
    
    WORKSPACE {
        uuid id PK
        uuid user_id FK
        string session_id
        string status
        string runtime_url
        integer resource_factor
        timestamp created_at
        timestamp last_active
    }
    
    CONVERSATION {
        uuid id PK
        uuid workspace_id FK
        string status
        float total_cost
        integer step_count
        timestamp created_at
        timestamp updated_at
    }
    
    EVENT {
        uuid id PK
        uuid conversation_id FK
        string type
        json data
        timestamp timestamp
    }
    
    SUBSCRIPTION {
        uuid id PK
        uuid user_id FK
        uuid tier_id FK
        timestamp start_date
        timestamp end_date
        string status
    }
    
    TIER {
        uuid id PK
        string name
        integer resource_factor
        integer max_workspaces
        integer max_iterations
        float price_monthly
    }
```

### User Management and Authentication

The Agent Server uses session API key authentication to secure its API and WebSocket connections.

#### Configuration

```python
# Server configuration with multiple user API keys
config = {
    "session_api_keys": [
        "user1-api-key-abc123",
        "user2-api-key-def456",
        "user3-api-key-ghi789"
    ],
    "allow_cors_origins": ["https://your-app.example.com"],
    "webhooks": [...]
}
```

Or via environment variables:

```bash
# Set multiple API keys
export OH_SESSION_API_KEYS="user1-key,user2-key,user3-key"
```

#### Authentication Flow

1. **HTTP Requests**: Include the API key in the `X-Session-API-Key` header
2. **WebSocket Connections**: Pass the key as a query parameter `session_api_key`
3. **Key Validation**: Server validates against configured `session_api_keys` list

```python
# Client-side: RemoteWorkspace with user-specific API key
from openhands.sdk.workspace import RemoteWorkspace

user_workspace = RemoteWorkspace(
    host="https://agent-server.example.com",
    api_key="user-specific-api-key",  # Unique per user
    working_dir="/workspace/user-123"
)
```

#### SaaS Integration Pattern

```python
# Your SaaS backend - generating and managing user API keys
class UserService:
    def create_user_session(self, user_id: str) -> dict:
        """Create a new agent session for a user."""
        # Generate unique API key for this user session
        api_key = generate_secure_api_key()
        
        # Register with Agent Server (add to session_api_keys)
        self.register_api_key(api_key, user_id)
        
        # Create workspace for user
        workspace_config = {
            "type": "api_remote",
            "session_id": f"user-{user_id}-{uuid.uuid4()}",
            "resource_factor": 2
        }
        
        return {
            "api_key": api_key,
            "workspace_config": workspace_config,
            "agent_server_url": "https://agent-server.example.com"
        }
```

### Resource Management and Scaling

#### Resource Allocation per User

The `APIRemoteWorkspace` supports resource scaling via the `resource_factor` parameter:

```python
from openhands.workspace import APIRemoteWorkspace

# Standard user workspace
standard_workspace = APIRemoteWorkspace(
    runtime_api_url="https://runtime.example.com",
    runtime_api_key="your-runtime-api-key",
    session_id="user-123-session",
    resource_factor=1  # Base resources
)

# Premium user workspace with more resources
premium_workspace = APIRemoteWorkspace(
    runtime_api_url="https://runtime.example.com",
    runtime_api_key="your-runtime-api-key",
    session_id="user-456-session",
    resource_factor=4  # 4x resources
)
```

#### Workspace Lifecycle Management

```python
# ConversationService manages workspace lifecycle
class WorkspaceManager:
    """Manages workspace lifecycle for SaaS users."""
    
    async def create_workspace(self, user_id: str, tier: str) -> str:
        """Create a new workspace for a user."""
        resource_factor = {"free": 1, "pro": 2, "enterprise": 4}.get(tier, 1)
        
        workspace = APIRemoteWorkspace(
            runtime_api_url=self.runtime_url,
            runtime_api_key=self.runtime_key,
            session_id=f"user-{user_id}-{uuid.uuid4()}",
            resource_factor=resource_factor,
            init_timeout=300.0,
            keep_alive=False,  # Clean up when done
            pause_on_close=True  # Pause instead of destroy for resume
        )
        
        return workspace.session_id
    
    async def pause_workspace(self, session_id: str):
        """Pause a workspace (preserves state, reduces costs)."""
        # APIRemoteWorkspace handles this via pause_on_close
        pass
    
    async def destroy_workspace(self, session_id: str):
        """Permanently destroy a workspace."""
        # Call cleanup() on the workspace
        pass
```

#### Concurrent Conversation Limits

```python
# Server configuration for resource limits
config = {
    "max_concurrent_conversations": 50,  # Per server instance
    "default_timeout": 300,  # 5 minutes per operation
    "max_iterations": 100,  # Prevent runaway agents
}
```

### Multi-Tenant Isolation

#### Workspace Isolation Strategies

| Strategy | Use Case | Isolation Level |
|----------|----------|-----------------|
| `LocalWorkspace` | Development/Testing | Process-level |
| `DockerWorkspace` | Production (self-hosted) | Container-level |
| `APIRemoteWorkspace` | Production (cloud) | Full VM/Container |

#### Docker-based Isolation

```python
from openhands.workspace import DockerWorkspace

# Each user gets their own Docker container
user_workspace = DockerWorkspace(
    base_image="python:3.11-slim",
    host_port=0,  # Auto-assign port
    environment_vars={
        "USER_ID": user_id,
        "WORKSPACE_ID": workspace_id
    }
)
```

#### API Remote Workspace Isolation

```python
from openhands.workspace import APIRemoteWorkspace

# Each user session gets isolated runtime
user_workspace = APIRemoteWorkspace(
    runtime_api_url="https://runtime.example.com",
    runtime_api_key="your-api-key",
    server_image="ghcr.io/openhands/agent-server:latest-python",
    session_id=f"tenant-{tenant_id}-user-{user_id}",  # Unique per user
    resource_factor=2,
    runtime_class="sysbox-runc",  # Enhanced isolation
    init_timeout=600.0
)
```

#### File System Isolation

```python
# Each conversation gets isolated storage
conversations_path = f"/data/tenants/{tenant_id}/users/{user_id}/conversations"
workspace_path = f"/data/tenants/{tenant_id}/users/{user_id}/workspace"

conversation = Conversation(
    agent=agent,
    workspace=workspace_path,
    persistence_dir=conversations_path,
    conversation_id=f"{user_id}-{uuid.uuid4()}"
)
```

### Programmatic Workspace Management with ConversationService

The `ConversationService` is the central component for managing conversations and their associated workspaces in a SaaS environment.

#### ConversationService Architecture

```mermaid
graph TD
    subgraph ConversationService
        CS[ConversationService]
        ES_MAP[EventService Dictionary]
    end
    
    subgraph "Per-User Sessions"
        ES1[EventService 1]
        ES2[EventService 2]
        ES3[EventService N]
        WS1[Workspace 1]
        WS2[Workspace 2]
        WS3[Workspace N]
        STATE1[ConversationState 1]
        STATE2[ConversationState 2]
        STATE3[ConversationState N]
    end
    
    CS --> ES_MAP
    ES_MAP --> ES1
    ES_MAP --> ES2
    ES_MAP --> ES3
    ES1 --> WS1
    ES1 --> STATE1
    ES2 --> WS2
    ES2 --> STATE2
    ES3 --> WS3
    ES3 --> STATE3
```

#### Creating Workspaces via ConversationService

```python
from openhands.agent_server.conversation_service import ConversationService
from openhands.agent_server.models import StartConversationRequest
from openhands.sdk import Agent, LLM
from openhands.sdk.workspace import LocalWorkspace

# Initialize ConversationService
conversation_service = ConversationService(
    session_api_key="your-session-api-key",
    conversations_path="/data/conversations",
    webhooks=[]  # Optional webhook subscribers
)

# Create agent configuration
llm = LLM(model="anthropic/claude-sonnet-4-5-20250929", api_key="...")
agent = Agent(llm=llm, tools=["bash", "file_editor"])

# Start a new conversation (creates workspace)
request = StartConversationRequest(
    agent=agent,
    workspace=LocalWorkspace("/workspace/user-123"),
    conversation_id=None,  # Auto-generate, or provide custom ID
    initial_message="Hello, analyze this project"
)

conversation_id = await conversation_service.start_conversation(request)
print(f"Created conversation: {conversation_id}")
```

#### Pausing and Resuming Workspaces

```python
# Pause a conversation (preserves state, reduces resource usage)
await conversation_service.pause_conversation(conversation_id)

# Resume a paused conversation
await conversation_service.resume_conversation(conversation_id)

# Check conversation status
event_service = conversation_service.get_event_service(conversation_id)
status = event_service.state.execution_status
print(f"Status: {status}")  # IDLE, RUNNING, PAUSED, FINISHED, etc.
```

#### Destroying Workspaces

```python
# Delete a conversation and clean up resources
# Note: This removes the EventService and cleans conversation directory
await conversation_service.delete_conversation(conversation_id)
```

#### Complete SaaS Workspace Manager Implementation

```python
import uuid
from typing import Optional
from dataclasses import dataclass
from enum import Enum

class WorkspaceStatus(Enum):
    CREATING = "creating"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class UserWorkspace:
    workspace_id: str
    user_id: str
    conversation_id: str
    status: WorkspaceStatus
    tier: str
    created_at: str
    
class SaaSWorkspaceManager:
    """
    High-level workspace manager for SaaS platforms.
    Wraps ConversationService with user/tenant management.
    """
    
    def __init__(
        self,
        conversation_service: ConversationService,
        runtime_api_url: str,
        runtime_api_key: str,
        base_workspace_path: str = "/data/workspaces"
    ):
        self.conversation_service = conversation_service
        self.runtime_api_url = runtime_api_url
        self.runtime_api_key = runtime_api_key
        self.base_workspace_path = base_workspace_path
        self._user_workspaces: dict[str, UserWorkspace] = {}
    
    async def create_workspace(
        self,
        user_id: str,
        tier: str = "free",
        initial_message: Optional[str] = None
    ) -> UserWorkspace:
        """Create a new workspace for a user."""
        
        workspace_id = f"ws-{uuid.uuid4().hex[:12]}"
        
        # Configure workspace based on tier
        resource_factor = {"free": 1, "pro": 2, "enterprise": 4}.get(tier, 1)
        
        # Create workspace path for this user
        workspace_path = f"{self.base_workspace_path}/{user_id}/{workspace_id}"
        
        # Configure agent
        llm = LLM(
            model="anthropic/claude-sonnet-4-5-20250929",
            api_key=self._get_user_api_key(user_id)
        )
        agent = Agent(llm=llm, tools=["bash", "file_editor", "task_tracker"])
        
        # For cloud deployment, use APIRemoteWorkspace
        from openhands.workspace import APIRemoteWorkspace
        workspace = APIRemoteWorkspace(
            runtime_api_url=self.runtime_api_url,
            runtime_api_key=self.runtime_api_key,
            session_id=f"user-{user_id}-{workspace_id}",
            resource_factor=resource_factor,
            pause_on_close=True
        )
        
        # Start conversation
        request = StartConversationRequest(
            agent=agent,
            workspace=workspace,
            initial_message=initial_message
        )
        
        conversation_id = await self.conversation_service.start_conversation(request)
        
        # Track workspace
        user_workspace = UserWorkspace(
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            status=WorkspaceStatus.RUNNING,
            tier=tier,
            created_at=datetime.utcnow().isoformat()
        )
        self._user_workspaces[workspace_id] = user_workspace
        
        return user_workspace
    
    async def pause_workspace(self, workspace_id: str) -> bool:
        """Pause a workspace to save resources."""
        workspace = self._user_workspaces.get(workspace_id)
        if not workspace:
            return False
        
        await self.conversation_service.pause_conversation(workspace.conversation_id)
        workspace.status = WorkspaceStatus.PAUSED
        return True
    
    async def resume_workspace(self, workspace_id: str) -> bool:
        """Resume a paused workspace."""
        workspace = self._user_workspaces.get(workspace_id)
        if not workspace:
            return False
        
        await self.conversation_service.resume_conversation(workspace.conversation_id)
        workspace.status = WorkspaceStatus.RUNNING
        return True
    
    async def destroy_workspace(self, workspace_id: str) -> bool:
        """Permanently destroy a workspace."""
        workspace = self._user_workspaces.get(workspace_id)
        if not workspace:
            return False
        
        await self.conversation_service.delete_conversation(workspace.conversation_id)
        workspace.status = WorkspaceStatus.STOPPED
        del self._user_workspaces[workspace_id]
        return True
    
    async def send_message(self, workspace_id: str, message: str) -> bool:
        """Send a message to a workspace."""
        workspace = self._user_workspaces.get(workspace_id)
        if not workspace or workspace.status != WorkspaceStatus.RUNNING:
            return False
        
        event_service = self.conversation_service.get_event_service(
            workspace.conversation_id
        )
        await event_service.send_message(message)
        return True
    
    def get_user_workspaces(self, user_id: str) -> list[UserWorkspace]:
        """Get all workspaces for a user."""
        return [
            ws for ws in self._user_workspaces.values()
            if ws.user_id == user_id
        ]
    
    def _get_user_api_key(self, user_id: str) -> str:
        """Retrieve user's LLM API key from your user management system."""
        # Implement based on your user/secrets management
        pass


# Usage Example
async def main():
    # Initialize services
    conversation_service = ConversationService(...)
    
    workspace_manager = SaaSWorkspaceManager(
        conversation_service=conversation_service,
        runtime_api_url="https://runtime.example.com",
        runtime_api_key="runtime-api-key"
    )
    
    # Create workspace for user
    workspace = await workspace_manager.create_workspace(
        user_id="user-123",
        tier="pro",
        initial_message="Help me build a Python REST API"
    )
    
    print(f"Created workspace: {workspace.workspace_id}")
    
    # Send additional messages
    await workspace_manager.send_message(
        workspace.workspace_id,
        "Add authentication using JWT"
    )
    
    # Pause when user is inactive
    await workspace_manager.pause_workspace(workspace.workspace_id)
    
    # Resume when user returns
    await workspace_manager.resume_workspace(workspace.workspace_id)
    
    # Clean up when done
    await workspace_manager.destroy_workspace(workspace.workspace_id)
```

---

## Custom Sandbox Integration

This section covers how to integrate external workspace providers (Daytona, Kubernetes, cloud providers) and implement custom workspace providers for dynamic sandbox spawning.

### Workspace Architecture

The SDK uses an abstract `BaseWorkspace` class that defines the interface for all workspace implementations:

```mermaid
classDiagram
    class BaseWorkspace {
        <<abstract>>
        +working_dir: str
        +execute_command(command, cwd, timeout) CommandResult
        +file_upload(source, destination) FileOperationResult
        +file_download(source, destination) FileOperationResult
        +git_changes(repo_path) List~GitChange~
        +git_diff(file_path) GitDiff
        +__enter__()
        +__exit__()
    }
    
    class LocalWorkspace {
        +execute_command()
        +file_upload()
        +file_download()
    }
    
    class RemoteWorkspace {
        +host: str
        +api_key: str
        +_client: httpx.Client
    }
    
    class DockerWorkspace {
        +base_image: str
        +container_id: str
        +_start_container()
        +_stop_container()
    }
    
    class APIRemoteWorkspace {
        +runtime_api_url: str
        +session_id: str
        +resource_factor: int
        +_start_runtime()
        +_resume_runtime()
    }
    
    BaseWorkspace <|-- LocalWorkspace
    BaseWorkspace <|-- RemoteWorkspace
    RemoteWorkspace <|-- DockerWorkspace
    RemoteWorkspace <|-- APIRemoteWorkspace
```

### Creating Custom Workspaces

To create a custom workspace provider, implement the `BaseWorkspace` interface:

#### Required Interface

```python
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass

@dataclass
class CommandResult:
    exit_code: int
    output: str
    error: str = ""

@dataclass
class FileOperationResult:
    success: bool
    message: str = ""

@dataclass
class GitChange:
    file_path: str
    change_type: str  # added, modified, deleted

@dataclass
class GitDiff:
    file_path: str
    diff_content: str

class BaseWorkspace(ABC):
    """Abstract base class for workspace implementations."""
    
    working_dir: str
    
    @abstractmethod
    def execute_command(
        self, 
        command: str, 
        cwd: str | Path | None = None, 
        timeout: float = 30.0
    ) -> CommandResult:
        """Execute a bash command within the workspace."""
        pass
    
    @abstractmethod
    def file_upload(
        self, 
        source_path: str | Path, 
        destination_path: str | Path
    ) -> FileOperationResult:
        """Upload a file to the workspace."""
        pass
    
    @abstractmethod
    def file_download(
        self, 
        source_path: str | Path, 
        destination_path: str | Path
    ) -> FileOperationResult:
        """Download a file from the workspace."""
        pass
    
    @abstractmethod
    def git_changes(self, repo_path: str | Path) -> list[GitChange]:
        """Get list of Git changes in the repository."""
        pass
    
    @abstractmethod
    def git_diff(self, file_path: str | Path) -> GitDiff:
        """Get Git diff for a specific file."""
        pass
    
    def __enter__(self):
        """Context manager entry - setup resources."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        pass
```

#### Custom Workspace Implementation Example

```python
import httpx
from typing import Optional

class CustomCloudWorkspace(BaseWorkspace):
    """Custom workspace provider for a cloud service."""
    
    def __init__(
        self,
        api_url: str,
        api_key: str,
        instance_type: str = "small",
        region: str = "us-east-1",
        timeout: float = 300.0
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.instance_type = instance_type
        self.region = region
        self.timeout = timeout
        self._instance_id: Optional[str] = None
        self._client = httpx.Client(
            base_url=api_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout
        )
    
    def __enter__(self):
        """Provision cloud instance on context entry."""
        response = self._client.post("/instances", json={
            "instance_type": self.instance_type,
            "region": self.region
        })
        response.raise_for_status()
        data = response.json()
        self._instance_id = data["instance_id"]
        self.working_dir = data["working_dir"]
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Terminate cloud instance on context exit."""
        if self._instance_id:
            self._client.delete(f"/instances/{self._instance_id}")
        self._client.close()
    
    def execute_command(
        self, 
        command: str, 
        cwd: str | Path | None = None, 
        timeout: float = 30.0
    ) -> CommandResult:
        """Execute command on cloud instance."""
        response = self._client.post(
            f"/instances/{self._instance_id}/execute",
            json={"command": command, "cwd": str(cwd) if cwd else None},
            timeout=timeout
        )
        data = response.json()
        return CommandResult(
            exit_code=data["exit_code"],
            output=data["stdout"],
            error=data["stderr"]
        )
    
    def file_upload(
        self, 
        source_path: str | Path, 
        destination_path: str | Path
    ) -> FileOperationResult:
        """Upload file to cloud instance."""
        with open(source_path, "rb") as f:
            response = self._client.post(
                f"/instances/{self._instance_id}/files",
                files={"file": f},
                data={"path": str(destination_path)}
            )
        return FileOperationResult(
            success=response.status_code == 200,
            message=response.json().get("message", "")
        )
    
    def file_download(
        self, 
        source_path: str | Path, 
        destination_path: str | Path
    ) -> FileOperationResult:
        """Download file from cloud instance."""
        response = self._client.get(
            f"/instances/{self._instance_id}/files",
            params={"path": str(source_path)}
        )
        if response.status_code == 200:
            with open(destination_path, "wb") as f:
                f.write(response.content)
            return FileOperationResult(success=True)
        return FileOperationResult(success=False, message=response.text)
    
    def git_changes(self, repo_path: str | Path) -> list[GitChange]:
        """Get Git changes from cloud instance."""
        result = self.execute_command(f"cd {repo_path} && git status --porcelain")
        changes = []
        for line in result.output.strip().split("\n"):
            if line:
                status, filepath = line[:2].strip(), line[3:]
                change_type = {"A": "added", "M": "modified", "D": "deleted"}.get(status, "modified")
                changes.append(GitChange(file_path=filepath, change_type=change_type))
        return changes
    
    def git_diff(self, file_path: str | Path) -> GitDiff:
        """Get Git diff for file from cloud instance."""
        result = self.execute_command(f"git diff {file_path}")
        return GitDiff(file_path=str(file_path), diff_content=result.output)
```

### Daytona Integration Example

[Daytona](https://daytona.io) provides development environment management. Here's how to integrate it:

```python
import httpx
from typing import Optional

class DaytonaWorkspace(BaseWorkspace):
    """Workspace provider using Daytona for development environments."""
    
    def __init__(
        self,
        daytona_url: str,
        api_key: str,
        project_config: dict,
        timeout: float = 600.0
    ):
        self.daytona_url = daytona_url
        self.api_key = api_key
        self.project_config = project_config
        self.timeout = timeout
        self._workspace_id: Optional[str] = None
        self._client = httpx.Client(
            base_url=daytona_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout
        )
    
    def __enter__(self):
        """Create Daytona workspace."""
        # Create workspace via Daytona API
        response = self._client.post("/workspaces", json={
            "project": self.project_config,
            "target": "local"  # or specific target
        })
        response.raise_for_status()
        data = response.json()
        self._workspace_id = data["id"]
        self.working_dir = "/workspace"
        
        # Wait for workspace to be ready
        self._wait_for_ready()
        return self
    
    def _wait_for_ready(self, max_attempts: int = 60):
        """Wait for Daytona workspace to be ready."""
        import time
        for _ in range(max_attempts):
            response = self._client.get(f"/workspaces/{self._workspace_id}")
            if response.json().get("state") == "running":
                return
            time.sleep(5)
        raise TimeoutError("Daytona workspace failed to start")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop and optionally delete Daytona workspace."""
        if self._workspace_id:
            # Stop the workspace
            self._client.post(f"/workspaces/{self._workspace_id}/stop")
            # Optionally delete: self._client.delete(f"/workspaces/{self._workspace_id}")
        self._client.close()
    
    def execute_command(
        self, 
        command: str, 
        cwd: str | Path | None = None, 
        timeout: float = 30.0
    ) -> CommandResult:
        """Execute command in Daytona workspace."""
        response = self._client.post(
            f"/workspaces/{self._workspace_id}/exec",
            json={
                "command": command,
                "workdir": str(cwd) if cwd else self.working_dir
            },
            timeout=timeout
        )
        data = response.json()
        return CommandResult(
            exit_code=data.get("exitCode", 0),
            output=data.get("stdout", ""),
            error=data.get("stderr", "")
        )
    
    def file_upload(self, source_path, destination_path) -> FileOperationResult:
        """Upload file to Daytona workspace."""
        with open(source_path, "rb") as f:
            response = self._client.post(
                f"/workspaces/{self._workspace_id}/files/upload",
                files={"file": f},
                data={"path": str(destination_path)}
            )
        return FileOperationResult(success=response.status_code == 200)
    
    def file_download(self, source_path, destination_path) -> FileOperationResult:
        """Download file from Daytona workspace."""
        response = self._client.get(
            f"/workspaces/{self._workspace_id}/files/download",
            params={"path": str(source_path)}
        )
        if response.status_code == 200:
            with open(destination_path, "wb") as f:
                f.write(response.content)
            return FileOperationResult(success=True)
        return FileOperationResult(success=False, message=response.text)
    
    def git_changes(self, repo_path) -> list[GitChange]:
        result = self.execute_command(f"cd {repo_path} && git status --porcelain")
        # Parse git status output...
        return []
    
    def git_diff(self, file_path) -> GitDiff:
        result = self.execute_command(f"git diff {file_path}")
        return GitDiff(file_path=str(file_path), diff_content=result.output)


# Usage example
daytona_workspace = DaytonaWorkspace(
    daytona_url="https://daytona.example.com/api",
    api_key="your-daytona-api-key",
    project_config={
        "name": "user-project",
        "repository": "https://github.com/user/repo.git",
        "branch": "main"
    }
)

with daytona_workspace as workspace:
    conversation = Conversation(
        agent=agent,
        workspace=workspace
    )
    conversation.send_message("Analyze this codebase")
    conversation.run()
```

### External Provider Integration

#### Kubernetes-based Workspace Provider

```python
from kubernetes import client, config
from kubernetes.stream import stream

class KubernetesWorkspace(BaseWorkspace):
    """Workspace provider using Kubernetes pods."""
    
    def __init__(
        self,
        namespace: str = "openhands-workspaces",
        image: str = "python:3.11-slim",
        resource_requests: dict = None,
        resource_limits: dict = None
    ):
        self.namespace = namespace
        self.image = image
        self.resource_requests = resource_requests or {"cpu": "500m", "memory": "512Mi"}
        self.resource_limits = resource_limits or {"cpu": "2", "memory": "2Gi"}
        self._pod_name: Optional[str] = None
        
        # Load Kubernetes config
        config.load_incluster_config()  # or config.load_kube_config()
        self.v1 = client.CoreV1Api()
    
    def __enter__(self):
        """Create Kubernetes pod."""
        import uuid
        self._pod_name = f"workspace-{uuid.uuid4().hex[:8]}"
        
        pod_manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": self._pod_name,
                "namespace": self.namespace,
                "labels": {"app": "openhands-workspace"}
            },
            "spec": {
                "containers": [{
                    "name": "workspace",
                    "image": self.image,
                    "command": ["sleep", "infinity"],
                    "resources": {
                        "requests": self.resource_requests,
                        "limits": self.resource_limits
                    },
                    "volumeMounts": [{
                        "name": "workspace-data",
                        "mountPath": "/workspace"
                    }]
                }],
                "volumes": [{
                    "name": "workspace-data",
                    "emptyDir": {}
                }]
            }
        }
        
        self.v1.create_namespaced_pod(self.namespace, pod_manifest)
        self._wait_for_pod_ready()
        self.working_dir = "/workspace"
        return self
    
    def _wait_for_pod_ready(self, timeout: int = 300):
        """Wait for pod to be ready."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            pod = self.v1.read_namespaced_pod(self._pod_name, self.namespace)
            if pod.status.phase == "Running":
                return
            time.sleep(2)
        raise TimeoutError(f"Pod {self._pod_name} failed to start")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Delete Kubernetes pod."""
        if self._pod_name:
            self.v1.delete_namespaced_pod(
                self._pod_name, 
                self.namespace,
                body=client.V1DeleteOptions()
            )
    
    def execute_command(self, command: str, cwd=None, timeout: float = 30.0) -> CommandResult:
        """Execute command in Kubernetes pod."""
        exec_command = ["/bin/sh", "-c", command]
        if cwd:
            exec_command = ["/bin/sh", "-c", f"cd {cwd} && {command}"]
        
        resp = stream(
            self.v1.connect_get_namespaced_pod_exec,
            self._pod_name,
            self.namespace,
            command=exec_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=False
        )
        
        output = ""
        error = ""
        while resp.is_open():
            resp.update(timeout=timeout)
            if resp.peek_stdout():
                output += resp.read_stdout()
            if resp.peek_stderr():
                error += resp.read_stderr()
        
        return CommandResult(exit_code=resp.returncode or 0, output=output, error=error)
    
    # ... implement file_upload, file_download, git_changes, git_diff


# Usage with resource tiers
def create_workspace_for_tier(tier: str) -> KubernetesWorkspace:
    """Create workspace with resources based on user tier."""
    resource_configs = {
        "free": {
            "requests": {"cpu": "250m", "memory": "256Mi"},
            "limits": {"cpu": "500m", "memory": "512Mi"}
        },
        "pro": {
            "requests": {"cpu": "1", "memory": "1Gi"},
            "limits": {"cpu": "2", "memory": "2Gi"}
        },
        "enterprise": {
            "requests": {"cpu": "2", "memory": "4Gi"},
            "limits": {"cpu": "4", "memory": "8Gi"}
        }
    }
    
    config = resource_configs.get(tier, resource_configs["free"])
    return KubernetesWorkspace(
        resource_requests=config["requests"],
        resource_limits=config["limits"]
    )
```

#### Using APIRemoteWorkspace with Custom Runtime

The built-in `APIRemoteWorkspace` can connect to any runtime API that implements the OpenHands runtime protocol:

```python
from openhands.workspace import APIRemoteWorkspace

# Connect to your custom runtime API
workspace = APIRemoteWorkspace(
    runtime_api_url="https://your-runtime-api.example.com",
    runtime_api_key="your-api-key",
    server_image="your-custom-agent-image:latest",
    session_id=f"user-{user_id}-session",
    resource_factor=2,
    runtime_class="sysbox-runc",  # Optional: enhanced isolation
    init_timeout=600.0,
    api_timeout=30.0,
    keep_alive=False,
    pause_on_close=True,
    image_pull_policy="IfNotPresent"
)

# Use with conversation
with workspace:
    conversation = Conversation(agent=agent, workspace=workspace)
    conversation.send_message("Your task here")
    conversation.run()
```

#### Runtime API Protocol

If implementing your own runtime API, it should support these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/start` | POST | Start a new runtime instance |
| `/status/{session_id}` | GET | Get runtime status |
| `/resume/{session_id}` | POST | Resume a paused runtime |
| `/stop/{session_id}` | POST | Stop a runtime |
| `/health` | GET | Health check |

```python
# Example runtime API payload for /start
{
    "session_id": "user-123-session",
    "server_image": "ghcr.io/openhands/agent-server:latest-python",
    "command": "/app/start.sh",
    "working_dir": "/workspace",
    "resource_factor": 2,
    "runtime_class": "sysbox-runc",
    "environment": {
        "OPENAI_API_KEY": "..."
    }
}

# Response
{
    "runtime_id": "rt-abc123",
    "runtime_url": "https://runtime-abc123.example.com",
    "session_api_key": "session-key-xyz",
    "status": "starting"
}
```

---

## Skills System

Skills provide contextual knowledge that can be injected into agent prompts. They enable agents to access specialized information or behaviors based on triggers.

### Skill Definition

```python
from openhands_sdk.skills import Skill, KeywordTrigger

python_help_skill = Skill(
    name="python-help",
    content="Expert Python programming assistance with best practices...",
    trigger=KeywordTrigger(keywords=["python", "code", "debug"]),
    source="team-guidelines"
)
```

### Trigger Types

#### None Trigger
Always active,适用于通用指导原则。

```python
repo_guidelines = Skill(
    name="repo-guidelines",
    content="Repository-specific coding standards...",
    trigger=None  # Always active
)
```

#### KeywordTrigger
Activated when specific keywords appear in user messages.

```python
Skill(
    name="database-help",
    content="Database query optimization patterns...",
    trigger=KeywordTrigger(keywords=["database", "sql", "query"])
)
```

#### TaskTrigger
Activated for specific tasks, potentially requiring user input.

```python
from openhands_sdk.skills import TaskTrigger, InputMetadata

deployment_skill = Skill(
    name="deploy-app",
    content="Application deployment procedures...",
    trigger=TaskTrigger(
        triggers=["deploy", "deployment"],
        inputs=[
            InputMetadata(
                name="environment",
                description="Target deployment environment (staging/production)"
            )
        ]
    )
)
```

### Agent Context

The `AgentContext` class manages skills and message suffixes.

```python
from openhands.sdk.context import AgentContext

context = AgentContext(
    skills=[python_help_skill, repo_guidelines],
    system_message_suffix="\nAlways follow Python best practices.",
    user_message_suffix="\nConsider security implications."
)
```

---

## Common Workflows

### Basic Agent Usage

1. **Setup Components**: Initialize LLM, Agent, and Tools
2. **Create Conversation**: Configure workspace and callbacks
3. **Send Message**: Provide task description
4. **Execute**: Run the conversation loop

### Planning and Execution

Multi-agent workflows separate planning from execution for better reliability.

```python
# Planning Agent (read-only tools)
planning_agent = Agent(
    llm=llm,
    tools=[Tool(name=GlobTool.name), Tool(name=GrepTool.name)]
)

# Execution Agent (full capabilities)
execution_agent = Agent(
    llm=llm,
    tools=[Tool(name=FileEditorTool.name), Tool(name=TerminalTool.name)]
)

# Two-stage workflow
planning_conversation = Conversation(agent=planning_agent, workspace=".")
planning_conversation.send_message("Plan the refactoring of this module")
planning_conversation.run()

# Transfer plan to execution agent
execution_conversation = Conversation(agent=execution_agent, workspace=".")
execution_conversation.send_message("Implement the plan in PLAN.md")
execution_conversation.run()
```

### Vision Processing

Agents can process images when using vision-capable models.

```python
from openhands_sdk.content import ImageContent, Message

# Create image message
image_message = Message(
    content=[
        "Analyze this architecture diagram:",
        ImageContent.from_file("architecture.png")
    ]
)

conversation.send_message(image_message)
conversation.run()
```

---

## Persistence and State Management

### Conversation Persistence

Save and restore conversation states for resuming work:

```python
# Save conversation state
conversation = Conversation(
    agent=agent,
    workspace=".",
    persistence_dir="./conversations",
    conversation_id="project-refactor-001"
)

# Restore existing conversation
restored_conversation = Conversation.load(
    persistence_dir="./conversations",
    conversation_id="project-refactor-001"
)
```

### Event Callbacks

Monitor and react to conversation events:

```python
def conversation_callback(event):
    if isinstance(event, LLMConvertibleEvent):
        # Log LLM messages
        log_message(event.to_llm_message())

    if isinstance(event, ToolExecutionEvent):
        # Track tool usage
        monitor_tool_usage(event.tool_name, event.result)

conversation = Conversation(
    agent=agent,
    callbacks=[conversation_callback],
    workspace="."
)
```

---

## Advanced Features

### Multi-Agent Coordination

Chain multiple agents for complex tasks:

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant PlanningAgent
    participant ExecutionAgent
    participant ReviewAgent

    User->>+PlanningAgent: Complex Task
    PlanningAgent->>PlanningAgent: Create detailed plan
    PlanningAgent-->>-User: Plan Ready

    User->>+ExecutionAgent: Implement Plan
    ExecutionAgent->>ExecutionAgent: Execute steps
    ExecutionAgent-->>-User: Implementation Complete

    User->>+ReviewAgent: Review Implementation
    ReviewAgent->>ReviewAgent: Validate against requirements
    ReviewAgent-->>-User: Review Results
```

### Custom Tool Development

Create custom tools for specialized capabilities:

```python
from openhands.tools import BaseTool

class DatabaseTool(BaseTool):
    name = "database_query"

    def __init__(self, connection_string):
        self.connection = create_connection(connection_string)

    def execute(self, query: str) -> str:
        result = self.connection.execute(query)
        return json.dumps(result.fetchall())

# Register with agent
agent = Agent(
    llm=llm,
    tools=[Tool(name=DatabaseTool.name, connection_string=conn_str)]
)
```

### MCP Integration

Configure Model Context Protocol (MCP) servers to extend agent capabilities with external tools:

```python
import os
from pydantic import SecretStr
from openhands.sdk import LLM, Agent, Conversation
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

# Configure LLM
llm = LLM(
    model="openhands/claude-sonnet-4-5-20250929",
    api_key=SecretStr(os.getenv("LLM_API_KEY")),
)

# Configure MCP servers
mcp_config = {
    "mcpServers": {
        "fetch": {
            "command": "uvx",
            "args": ["mcp-server-fetch"]
        },
        "repomix": {
            "command": "npx",
            "args": ["-y", "repomix@1.4.2", "--mcp"]
        },
        "file-manager": {
            "command": "file-manager-server",
            "args": ["--port", "8080"]
        }
    }
}

# Create agent with MCP tools
agent = Agent(
    llm=llm,
    tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
    ],
    mcp_config=mcp_config,
    # Filter which MCP tools are available
    filter_tools_regex="^(?!repomix)(.*)|^repomix.*pack_codebase.*$",
)

# Use agent with MCP-provided tools
conversation = Conversation(agent=agent, workspace=os.getcwd())
conversation.send_message(
    "Read https://github.com/OpenHands/OpenHands and write 3 facts into FACTS.txt."
)
conversation.run()

print(f"Cost: ${llm.metrics.accumulated_cost}")
```

#### MCP Configuration Options

| Key | Description | Example |
|-----|-------------|---------|
| `mcpServers` | Dictionary of MCP server configurations | See above |
| `command` | Command to start the MCP server | `"uvx"`, `"npx"` |
| `args` | Command arguments | `["mcp-server-fetch"]` |
| `filter_tools_regex` | Regex to filter available MCP tools | `"^fetch.*"` |

#### Common MCP Servers

| Server | Purpose | Command |
|--------|---------|---------|
| `mcp-server-fetch` | Web fetching capabilities | `uvx mcp-server-fetch` |
| `repomix` | Codebase analysis and packing | `npx -y repomix@1.4.2 --mcp` |
| `mcp-server-github` | GitHub API integration | `uvx mcp-server-github` |

---

## Examples Directory

The `examples/` directory contains comprehensive usage examples:

- **`01_standalone_sdk/`**: Basic SDK usage patterns
- **`02_agent_server/`**: Server-based deployments
- **`03_advanced/`**: Complex multi-agent workflows
- **`04_custom_tools/`**: Custom tool development
- **`05_skills/`**: Skills system usage

### Key Examples

| Example | Description |
|---------|-------------|
| `10_persistence.py` | Conversation persistence and state management |
| `17_image_input.py` | Vision capabilities with image processing |
| `24_planning_agent_workflow.py` | Multi-stage planning and execution |
| `30_custom_tools.py` | Developing custom tools |

---

## Best Practices

### Agent Design

1. **Single Purpose**: Design agents for specific tasks
2. **Appropriate Tools**: Provide only necessary tools
3. **Clear Instructions**: Use specific task descriptions
4. **Error Handling**: Implement graceful failure recovery

### Performance Optimization

1. **Tool Selection**: Choose efficient tools for tasks
2. **State Management**: Use persistence for long-running tasks
3. **Resource Limits**: Set appropriate timeouts and limits
4. **Monitoring**: Track agent performance and resource usage

### Security Considerations

1. **Input Validation**: Validate user inputs and tool parameters
2. **Workspace Isolation**: Use sandboxed environments for untrusted code
3. **API Key Security**: Securely store and manage API keys
4. **Access Control**: Limit agent access to sensitive resources

### Code Organization

```
project/
├── agents/           # Agent definitions
├── tools/            # Custom tools
├── skills/           # Skill definitions
├── conversations/    # Saved conversation states
├── config/          # Configuration files
└── examples/        # Usage examples
```

---

## SaaS Platform Experiment

This section provides a hands-on experiment to validate the core concepts of building a SaaS sub-system with dynamic workspace spawning. The key insight is that we **leverage the existing Agent Server** rather than rebuilding conversation management, and we use **Daytona** for isolated sandbox provisioning.

### Experiment Overview

**Goal**: Build a thin orchestration layer that:
1. Calls the **OpenHands Agent Server** REST API for conversation management
2. Provisions isolated sandboxes via **Daytona** 
3. Routes user requests to their designated workspaces
4. Streams events back to clients via WebSockets

**Key Principle**: The Agent Server already handles:
- Conversation lifecycle management
- Event streaming via WebSocket
- Agent execution loop
- Tool invocation

Your SaaS backend only needs to:
- Manage user authentication (use your existing system)
- Map users to Daytona sandboxes
- Proxy requests to the Agent Server
- Store metadata in your existing database

**Duration**: 2-4 hours

**Prerequisites**:
- Daytona account and API key
- Python 3.11+
- OpenHands Agent Server running (or use the SDK to start one)
- `pip install httpx websockets pydantic fastapi uvicorn`
- An LLM API key (OpenAI or Anthropic)

### Experiment Architecture

```mermaid
flowchart TB
    subgraph "Your Existing System"
        CLIENT[Your Frontend]
        AUTH[Your Auth Service]
        DB[(Your Database)]
    end
    
    subgraph "New Sub-System (This Experiment)"
        ORCH[Orchestration Layer<br/>Thin FastAPI Service]
    end
    
    subgraph "OpenHands (Already Built)"
        AGENT[Agent Server<br/>REST API + WebSocket]
    end
    
    subgraph "Daytona (Sandbox Provider)"
        DAYTONA[Daytona API]
        WS1[User A Sandbox<br/>Isolated Container]
        WS2[User B Sandbox<br/>Isolated Container]
    end
    
    CLIENT -->|1. Authenticated Request| AUTH
    AUTH -->|2. User Context| ORCH
    ORCH -->|3. Create Sandbox| DAYTONA
    DAYTONA -->|4. Spawn| WS1
    DAYTONA -->|4. Spawn| WS2
    
    ORCH -->|5. Store sandbox mapping| DB
    ORCH -->|6. POST /conversations| AGENT
    AGENT <-->|7. Execute in sandbox| WS1
    AGENT -->|8. WebSocket events| ORCH
    ORCH -->|9. Forward events| CLIENT
    
    style CLIENT fill:#90EE90
    style AUTH fill:#90EE90
    style DB fill:#90EE90
    style ORCH fill:#87CEEB
    style AGENT fill:#FFE4B5
    style DAYTONA fill:#E6E6FA
    style WS1 fill:#DDA0DD
    style WS2 fill:#DDA0DD
```

### Key Integration Points

```mermaid
sequenceDiagram
    participant User as Your User
    participant Auth as Your Auth
    participant Orch as Orchestration Layer
    participant Daytona as Daytona API
    participant Agent as Agent Server
    participant Sandbox as Daytona Sandbox

    User->>Auth: Login (existing flow)
    Auth->>User: JWT Token
    
    User->>Orch: Create Workspace (with JWT)
    Orch->>Auth: Validate JWT
    Auth->>Orch: User ID
    
    Orch->>Daytona: POST /sandbox (create)
    Daytona->>Sandbox: Provision container
    Daytona->>Orch: sandbox_id, preview_url
    
    Orch->>Agent: POST /conversations (with sandbox config)
    Agent->>Orch: conversation_id
    
    Orch->>User: workspace_id (maps to sandbox + conversation)
    
    User->>Orch: Send Message
    Orch->>Agent: POST /conversations/{id}/send
    Agent->>Sandbox: Execute command
    Sandbox->>Agent: Result
    Agent->>Orch: WebSocket event
    Orch->>User: WebSocket event
```

### System Architecture Diagram

> **Note**: The REST API endpoints shown below are simplified for readability. See the [REST API Reference](#rest-api-reference) for actual endpoint paths and payload formats.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              YOUR EXISTING SYSTEM                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                                   │
│  │   Frontend   │  │  Auth Service│  │   Database   │                                   │
│  │   (React,    │  │  (JWT/OAuth) │  │  (Postgres,  │                                   │
│  │    Vue, etc) │  │              │  │   MongoDB)   │                                   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                                   │
└─────────┼─────────────────┼─────────────────┼───────────────────────────────────────────┘
          │                 │                 │
          │    ┌────────────┴─────────────────┘
          │    │
          ▼    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         NEW SUB-SYSTEM (ORCHESTRATION LAYER)                            │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                        orchestration_layer.py                                   │    │
│  │                                                                                 │    │
│  │   • Maps users → Daytona sandboxes                                              │    │
│  │   • Proxies requests → Agent Server API                                         │    │
│  │   • Streams WebSocket events → Frontend                                         │    │
│  │   • Stores workspace mappings → Your Database                                   │    │
│  │                                                                                 │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                          │                              │                               │
└──────────────────────────┼──────────────────────────────┼───────────────────────────────┘
                           │                              │
           ┌───────────────┘                              └───────────────┐
           │                                                              │
           ▼                                                              ▼
┌──────────────────────────────────────────┐    ┌──────────────────────────────────────────┐
│       OPENHANDS AGENT SERVER             │    │              DAYTONA                     │
│         (Already Built!)                 │    │        (Sandbox Provider)                │
│                                          │    │                                          │
│  ┌────────────────────────────────────┐  │    │  ┌────────────────────────────────────┐  │
│  │  REST API                          │  │    │  │  Daytona API                       │  │
│  │  • POST /conversations             │  │    │  │  • POST /sandbox (create)          │  │
│  │  • POST /conversations/{id}/send   │  │    │  │  • GET /sandbox/{id} (status)      │  │
│  │  • GET /conversations/{id}         │  │    │  │  • DELETE /sandbox/{id}            │  │
│  │  • POST /conversations/{id}/pause  │  │    │  │  • POST /sandbox/{id}/exec         │  │
│  └────────────────────────────────────┘  │    │  └────────────────────────────────────┘  │
│                                          │    │                                          │
│  ┌────────────────────────────────────┐  │    │                    │                     │
│  │  WebSocket                         │  │    │                    │                     │
│  │  • /ws/{conversation_id}           │  │    │                    ▼                     │
│  │  • Streams all agent events        │  │    │  ┌────────────────────────────────────┐  │
│  └────────────────────────────────────┘  │    │  │  Isolated Sandboxes (per user)     │  │
│                                          │    │  │                                    │  │
│               │                          │    │  │  ┌──────────┐ ┌──────────┐         │  │
│               │                          │    │  │  │ User A   │ │ User B   │  ...    │  │
│               └──────────────────────────┼────┼──│  │ Sandbox  │ │ Sandbox  │         │  │
│                                          │    │  │  │ (Docker) │ │ (Docker) │         │  │
│                 Executes in sandbox ─────┼────┼──│  └──────────┘ └──────────┘         │  │
│                                          │    │  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘    └──────────────────────────────────────────┘

LEGEND:
  ────────►  HTTP/REST Request
  ─ ─ ─ ─►  WebSocket Stream
  ════════►  Command Execution
```

**Key Insight**: The Orchestration Layer is intentionally **thin**. It doesn't rebuild what the Agent Server already provides. It simply:

1. **Integrates** with your existing auth system
2. **Provisions** Daytona sandboxes for user isolation
3. **Proxies** requests to the Agent Server REST API
4. **Forwards** WebSocket events to your frontend

### Step 1: Create the Orchestration Layer

This thin service sits between your existing system and OpenHands Agent Server + Daytona.

Create a file called `orchestration_layer.py`:

```python
#!/usr/bin/env python3
"""
Orchestration Layer for OpenHands SaaS Integration

This service:
1. Provisions Daytona sandboxes for users
2. Calls the Agent Server REST API (not rebuilding it!)
3. Proxies WebSocket events to your frontend
4. Stores workspace mappings in your existing database

Key Principle: The Agent Server already does the heavy lifting.
We just orchestrate and map users to resources.
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ============================================================================
# Configuration - Connect to your existing infrastructure
# ============================================================================

class Config:
    # Daytona Configuration
    DAYTONA_API_URL = os.getenv("DAYTONA_API_URL", "https://api.daytona.io")
    DAYTONA_API_KEY = os.getenv("DAYTONA_API_KEY", "your-daytona-api-key")
    DAYTONA_TARGET_REGION = os.getenv("DAYTONA_TARGET_REGION", "us")
    
    # Agent Server Configuration (the already-built OpenHands server)
    AGENT_SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://localhost:8080")
    AGENT_SERVER_API_KEY = os.getenv("AGENT_SERVER_API_KEY", "your-agent-server-key")
    
    # LLM Configuration
    LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "your-llm-api-key")

# ============================================================================
# Data Models
# ============================================================================

class WorkspaceStatus(str, Enum):
    PROVISIONING = "provisioning"    # Daytona sandbox being created
    READY = "ready"                  # Sandbox ready, no active conversation
    ACTIVE = "active"                # Conversation running
    PAUSED = "paused"                # Conversation paused
    TERMINATED = "terminated"        # Sandbox destroyed
    ERROR = "error"

@dataclass
class UserWorkspace:
    """Maps a user to their Daytona sandbox and Agent Server conversation."""
    workspace_id: str                # Your internal ID
    user_id: str                     # From your auth system
    daytona_sandbox_id: str          # Daytona's sandbox ID
    daytona_preview_url: str         # URL to access the sandbox
    agent_conversation_id: Optional[str] = None  # Agent Server's conversation ID
    status: WorkspaceStatus = WorkspaceStatus.PROVISIONING
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

class CreateWorkspaceRequest(BaseModel):
    initial_message: Optional[str] = None
    workspace_name: Optional[str] = None
    # Add any custom config your system needs

class SendMessageRequest(BaseModel):
    message: str

class WorkspaceResponse(BaseModel):
    workspace_id: str
    user_id: str
    status: str
    preview_url: str
    conversation_id: Optional[str]
    created_at: str

# ============================================================================
# Daytona Client - Sandbox Provisioning
# ============================================================================

class DaytonaClient:
    """
    Client for Daytona sandbox provisioning.
    Daytona provides isolated, ephemeral development environments.
    """
    
    def __init__(self):
        self.api_url = Config.DAYTONA_API_URL
        self.api_key = Config.DAYTONA_API_KEY
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=120.0  # Sandbox creation can take time
        )
    
    async def create_sandbox(
        self, 
        name: str,
        auto_stop_interval: int = 15,  # Minutes of inactivity before auto-stop
        auto_archive_interval: int = 10080  # 7 days before archive
    ) -> Dict[str, Any]:
        """
        Create a new Daytona sandbox.
        Returns sandbox_id and preview_url for accessing the sandbox.
        """
        response = await self.client.post(
            f"{self.api_url}/sandbox",
            json={
                "id": name,  # Optional: let Daytona generate if not provided
                "target": Config.DAYTONA_TARGET_REGION,
                "auto_stop_interval": str(auto_stop_interval),
                "auto_archive_interval": str(auto_archive_interval),
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_sandbox(self, sandbox_id: str) -> Dict[str, Any]:
        """Get sandbox details including status."""
        response = await self.client.get(f"{self.api_url}/sandbox/{sandbox_id}")
        response.raise_for_status()
        return response.json()
    
    async def execute_command(self, sandbox_id: str, command: str) -> Dict[str, Any]:
        """Execute a command in the sandbox."""
        response = await self.client.post(
            f"{self.api_url}/sandbox/{sandbox_id}/exec",
            json={"command": command}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_preview_url(self, sandbox_id: str, port: int = 8080) -> str:
        """Get the preview URL for a service running in the sandbox."""
        response = await self.client.post(
            f"{self.api_url}/sandbox/{sandbox_id}/preview",
            json={"port": str(port), "description": "OpenHands Agent", "check_server": False}
        )
        response.raise_for_status()
        return response.json().get("url", "")
    
    async def destroy_sandbox(self, sandbox_id: str) -> bool:
        """Destroy a sandbox and clean up resources."""
        response = await self.client.delete(f"{self.api_url}/sandbox/{sandbox_id}")
        return response.status_code == 200
    
    async def close(self):
        await self.client.aclose()

# ============================================================================
# Agent Server Client - Conversation Management
# ============================================================================

class AgentServerClient:
    """
    Client for the OpenHands Agent Server REST API.
    The Agent Server is already built - we just call its API!
    
    NOTE: This example uses simplified endpoint names for clarity.
    Actual Agent Server endpoints use the /api prefix and structured payloads.
    See the REST API Reference section for exact formats:
    
    Simplified (this example)  →  Actual Agent Server API
    ─────────────────────────────────────────────────────
    POST /conversations        →  POST /api/conversations
    POST /conversations/{id}/send  →  POST /api/conversations/{id}/events
    POST /conversations/{id}/resume  →  POST /api/conversations/{id}/run
    WS /ws/{id}                →  WS /sockets/events/{id}
    """
    
    def __init__(self):
        self.base_url = Config.AGENT_SERVER_URL
        self.api_key = Config.AGENT_SERVER_API_KEY
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0
        )
    
    async def create_conversation(
        self,
        initial_message: Optional[str] = None,
        workspace_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation on the Agent Server.
        The Agent Server handles all conversation lifecycle management.
        """
        payload = {
            "llm_config": {
                "model": Config.LLM_MODEL,
                "api_key": Config.LLM_API_KEY,
            },
            "agent_config": {
                "tools": ["terminal", "file_editor", "browser"]
            }
        }
        
        if workspace_config:
            payload["workspace_config"] = workspace_config
        
        if initial_message:
            payload["initial_message"] = initial_message
        
        response = await self.client.post(
            f"{self.base_url}/conversations",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def send_message(self, conversation_id: str, message: str) -> Dict[str, Any]:
        """Send a message to an existing conversation."""
        response = await self.client.post(
            f"{self.base_url}/conversations/{conversation_id}/send",
            json={"content": message}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation status and details."""
        response = await self.client.get(
            f"{self.base_url}/conversations/{conversation_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def pause_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Pause conversation execution."""
        response = await self.client.post(
            f"{self.base_url}/conversations/{conversation_id}/pause"
        )
        response.raise_for_status()
        return response.json()
    
    async def resume_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Resume a paused conversation."""
        response = await self.client.post(
            f"{self.base_url}/conversations/{conversation_id}/resume"
        )
        response.raise_for_status()
        return response.json()
    
    async def stop_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Stop a conversation."""
        response = await self.client.post(
            f"{self.base_url}/conversations/{conversation_id}/stop"
        )
        response.raise_for_status()
        return response.json()
    
    def get_websocket_url(self, conversation_id: str) -> str:
        """Get WebSocket URL for streaming events."""
        ws_base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{ws_base}/ws/{conversation_id}"
    
    async def close(self):
        await self.client.aclose()

# ============================================================================
# Orchestration Layer - The Thin Glue
# ============================================================================

class OrchestrationLayer:
    """
    The main orchestration service.
    
    This is intentionally thin - it just:
    1. Maps users to Daytona sandboxes
    2. Proxies requests to the Agent Server
    3. Manages workspace lifecycle
    
    Your existing auth, billing, and database systems handle everything else.
    """
    
    def __init__(self):
        self.daytona = DaytonaClient()
        self.agent_server = AgentServerClient()
        
        # In production, this would be your existing database
        # For the experiment, we use in-memory storage
        self.workspaces: Dict[str, UserWorkspace] = {}
        self.websocket_connections: Dict[str, list[WebSocket]] = {}
    
    async def create_workspace(
        self, 
        user_id: str, 
        initial_message: Optional[str] = None,
        workspace_name: Optional[str] = None
    ) -> UserWorkspace:
        """
        Create a new workspace for a user.
        
        Steps:
        1. Provision Daytona sandbox
        2. Create Agent Server conversation pointing to the sandbox
        3. Store the mapping
        """
        workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
        sandbox_name = workspace_name or f"openhands-{user_id}-{workspace_id}"
        
        # Step 1: Provision Daytona sandbox
        print(f"[Orchestrator] Provisioning Daytona sandbox: {sandbox_name}")
        try:
            sandbox_result = await self.daytona.create_sandbox(name=sandbox_name)
            daytona_sandbox_id = sandbox_result.get("id", sandbox_name)
            
            # Get preview URL for the sandbox
            preview_url = await self.daytona.get_preview_url(daytona_sandbox_id)
            
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to provision Daytona sandbox: {str(e)}"
            )
        
        # Create workspace record
        workspace = UserWorkspace(
            workspace_id=workspace_id,
            user_id=user_id,
            daytona_sandbox_id=daytona_sandbox_id,
            daytona_preview_url=preview_url,
            status=WorkspaceStatus.PROVISIONING
        )
        
        # Step 2: Create Agent Server conversation
        print(f"[Orchestrator] Creating Agent Server conversation for sandbox: {daytona_sandbox_id}")
        try:
            # Configure workspace to point to the Daytona sandbox
            workspace_config = {
                "type": "remote",
                "sandbox_id": daytona_sandbox_id,
                "sandbox_url": preview_url,
                # The Agent Server will use this to connect to the sandbox
            }
            
            conversation_result = await self.agent_server.create_conversation(
                initial_message=initial_message,
                workspace_config=workspace_config
            )
            
            workspace.agent_conversation_id = conversation_result.get("conversation_id")
            workspace.status = WorkspaceStatus.ACTIVE if initial_message else WorkspaceStatus.READY
            
        except Exception as e:
            # Clean up sandbox if conversation creation fails
            await self.daytona.destroy_sandbox(daytona_sandbox_id)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create Agent Server conversation: {str(e)}"
            )
        
        # Step 3: Store the mapping (in production, save to your database)
        self.workspaces[workspace_id] = workspace
        print(f"[Orchestrator] Workspace {workspace_id} created successfully")
        
        return workspace
    
    async def send_message(self, workspace_id: str, message: str) -> Dict[str, Any]:
        """Send a message to a workspace's conversation."""
        workspace = self._get_workspace(workspace_id)
        
        if not workspace.agent_conversation_id:
            raise HTTPException(status_code=400, detail="No active conversation")
        
        workspace.status = WorkspaceStatus.ACTIVE
        return await self.agent_server.send_message(
            workspace.agent_conversation_id, 
            message
        )
    
    async def pause_workspace(self, workspace_id: str) -> bool:
        """Pause a workspace's conversation."""
        workspace = self._get_workspace(workspace_id)
        
        if workspace.agent_conversation_id:
            await self.agent_server.pause_conversation(workspace.agent_conversation_id)
        
        workspace.status = WorkspaceStatus.PAUSED
        return True
    
    async def resume_workspace(self, workspace_id: str) -> bool:
        """Resume a paused workspace."""
        workspace = self._get_workspace(workspace_id)
        
        if workspace.status != WorkspaceStatus.PAUSED:
            raise HTTPException(status_code=400, detail="Workspace is not paused")
        
        if workspace.agent_conversation_id:
            await self.agent_server.resume_conversation(workspace.agent_conversation_id)
        
        workspace.status = WorkspaceStatus.ACTIVE
        return True
    
    async def destroy_workspace(self, workspace_id: str) -> bool:
        """
        Destroy a workspace completely.
        
        Steps:
        1. Stop the Agent Server conversation
        2. Destroy the Daytona sandbox
        3. Remove from storage
        """
        workspace = self._get_workspace(workspace_id)
        
        # Stop conversation
        if workspace.agent_conversation_id:
            try:
                await self.agent_server.stop_conversation(workspace.agent_conversation_id)
            except:
                pass  # Conversation might already be stopped
        
        # Destroy Daytona sandbox
        try:
            await self.daytona.destroy_sandbox(workspace.daytona_sandbox_id)
        except Exception as e:
            print(f"[Orchestrator] Warning: Failed to destroy sandbox: {e}")
        
        workspace.status = WorkspaceStatus.TERMINATED
        del self.workspaces[workspace_id]
        
        return True
    
        """Get workspace details."""
        return self.workspaces.get(workspace_id)
    
    def _get_workspace(self, workspace_id: str) -> UserWorkspace:
        """Get workspace or raise 404."""
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace
    
    def get_user_workspaces(self, user_id: str) -> list[UserWorkspace]:
        """Get all workspaces for a user."""
        return [ws for ws in self.workspaces.values() if ws.user_id == user_id]
    
    def register_websocket(self, workspace_id: str, websocket: WebSocket):
        """Register a WebSocket connection for a workspace."""
        if workspace_id not in self.websocket_connections:
            self.websocket_connections[workspace_id] = []
        self.websocket_connections[workspace_id].append(websocket)
    
    def unregister_websocket(self, workspace_id: str, websocket: WebSocket):
        """Unregister a WebSocket connection."""
        if workspace_id in self.websocket_connections:
            try:
                self.websocket_connections[workspace_id].remove(websocket)
            except ValueError:
                pass
    
    async def stream_events_to_websocket(self, workspace_id: str, websocket: WebSocket):
        """
        Stream events from Agent Server to the client WebSocket.
        
        This is the key integration point - we proxy events from
        the Agent Server's WebSocket to the client.
        """
        workspace = self._get_workspace(workspace_id)
        
        if not workspace.agent_conversation_id:
            raise HTTPException(status_code=400, detail="No active conversation")
        
        # Connect to Agent Server WebSocket
        agent_ws_url = self.agent_server.get_websocket_url(workspace.agent_conversation_id)
        
        import websockets
        async with websockets.connect(agent_ws_url) as agent_ws:
            async for message in agent_ws:
                # Forward events to the client
                await websocket.send_text(message)
    
    async def cleanup(self):
        """Cleanup resources on shutdown."""
        await self.daytona.close()
        await self.agent_server.close()


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="OpenHands SaaS Orchestration Layer",
    description="Thin orchestration service connecting your system to Agent Server + Daytona"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your existing CORS policy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestration layer
orchestrator = OrchestrationLayer()


# ============================================================================
# Authentication Dependency (integrate with your existing auth)
# ============================================================================

async def get_current_user(authorization: str = Header(None)) -> str:
    """
    Validate user from your existing auth system.
    
    In production, this would:
    1. Validate the JWT/token from your auth service
    2. Return the user_id from your existing user database
    
    For the experiment, we just extract user_id from a simple header.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Example: "Bearer user-123" -> "user-123"
    # Replace with your actual auth validation
    try:
        token = authorization.replace("Bearer ", "")
        # In production: validate token with your auth service
        user_id = token  # Simplified for experiment
        return user_id
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============================================================================
# API Endpoints
# ============================================================================

@app.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(
    request: CreateWorkspaceRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Create a new workspace for the authenticated user.
    
    This provisions a Daytona sandbox and creates an Agent Server conversation.
    """
    workspace = await orchestrator.create_workspace(
        user_id=user_id,  # From auth dependency
        initial_message=request.initial_message,
        workspace_name=request.workspace_name
    )
    return WorkspaceResponse(
        workspace_id=workspace.workspace_id,
        user_id=workspace.user_id,
        status=workspace.status.value,
        preview_url=workspace.daytona_preview_url,
        conversation_id=workspace.agent_conversation_id,
        created_at=workspace.created_at.isoformat()
    )


@app.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace_details(
    workspace_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get workspace details."""
    workspace = orchestrator.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Verify ownership (integrate with your auth/RBAC)
    if workspace.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return WorkspaceResponse(
        workspace_id=workspace.workspace_id,
        user_id=workspace.user_id,
        status=workspace.status.value,
        preview_url=workspace.daytona_preview_url,
        conversation_id=workspace.agent_conversation_id,
        created_at=workspace.created_at.isoformat()
    )


@app.get("/workspaces")
async def list_my_workspaces(user_id: str = Depends(get_current_user)):
    """List all workspaces for the authenticated user."""
    workspaces = orchestrator.get_user_workspaces(user_id)
    return [
        WorkspaceResponse(
            workspace_id=ws.workspace_id,
            user_id=ws.user_id,
            status=ws.status.value,
            preview_url=ws.daytona_preview_url,
            conversation_id=ws.agent_conversation_id,
            created_at=ws.created_at.isoformat()
        )
        for ws in workspaces
    ]


@app.post("/workspaces/{workspace_id}/messages")
async def send_message_to_workspace(
    workspace_id: str, 
    request: SendMessageRequest,
    user_id: str = Depends(get_current_user)
):
    """Send a message to a workspace's agent conversation."""
    # Verify ownership
    workspace = orchestrator.get_workspace(workspace_id)
    if not workspace or workspace.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await orchestrator.send_message(workspace_id, request.message)
    return {"success": True, "result": result}


@app.post("/workspaces/{workspace_id}/pause")
async def pause_workspace_endpoint(
    workspace_id: str,
    user_id: str = Depends(get_current_user)
):
    """Pause a workspace's agent conversation."""
    workspace = orchestrator.get_workspace(workspace_id)
    if not workspace or workspace.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await orchestrator.pause_workspace(workspace_id)
    return {"success": True, "status": "paused"}


@app.post("/workspaces/{workspace_id}/resume")
async def resume_workspace_endpoint(
    workspace_id: str,
    user_id: str = Depends(get_current_user)
):
    """Resume a paused workspace."""
    workspace = orchestrator.get_workspace(workspace_id)
    if not workspace or workspace.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await orchestrator.resume_workspace(workspace_id)
    return {"success": True, "status": "resumed"}


@app.delete("/workspaces/{workspace_id}")
async def destroy_workspace_endpoint(
    workspace_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Destroy a workspace completely.
    
    This will:
    1. Stop the Agent Server conversation
    2. Destroy the Daytona sandbox
    3. Clean up all resources
    """
    workspace = orchestrator.get_workspace(workspace_id)
    if not workspace or workspace.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await orchestrator.destroy_workspace(workspace_id)
    return {"success": True, "status": "terminated"}


@app.websocket("/ws/{workspace_id}")
async def websocket_endpoint(websocket: WebSocket, workspace_id: str):
    """
    WebSocket endpoint for real-time event streaming.
    
    This proxies events from the Agent Server WebSocket to your client.
    The Agent Server handles all the event generation - we just forward.
    """
    await websocket.accept()
    orchestrator.register_websocket(workspace_id, websocket)
    
    try:
        # Stream events from Agent Server to client
        await orchestrator.stream_events_to_websocket(workspace_id, websocket)
    except WebSocketDisconnect:
        orchestrator.unregister_websocket(workspace_id, websocket)
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        orchestrator.unregister_websocket(workspace_id, websocket)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await orchestrator.cleanup()


# ============================================================================
# Run the Orchestration Layer
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("OpenHands SaaS Orchestration Layer")
    print("=" * 60)
    print(f"Agent Server URL: {Config.AGENT_SERVER_URL}")
    print(f"Daytona API URL: {Config.DAYTONA_API_URL}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 2: Create the Test Client

Create a file called `test_client.py`:

```python
#!/usr/bin/env python3
"""
Test Client for OpenHands SaaS Orchestration Layer

This simulates your frontend calling the orchestration layer.
In production, the auth token would come from your existing auth system.
"""

import asyncio
import httpx
import websockets
import json
from datetime import datetime

# Configuration
ORCHESTRATOR_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


def get_auth_headers(user_id: str) -> dict:
    """
    Get auth headers for a user.
    
    In production, this would be a real JWT from your auth system.
    For the experiment, we use a simple token format.
    """
    return {"Authorization": f"Bearer {user_id}"}


async def test_workspace_lifecycle():
    """
    Test the complete workspace lifecycle.
    
    This demonstrates:
    1. Creating workspaces (which provisions Daytona sandboxes)
    2. Routing messages to the Agent Server
    3. Managing workspace lifecycle
    4. Multi-user isolation
    """
    
    print("=" * 70)
    print("OpenHands SaaS Orchestration Layer - Integration Test")
    print("=" * 70)
    print(f"Orchestrator URL: {ORCHESTRATOR_URL}")
    print("=" * 70)
    
    # User A credentials (from your auth system)
    user_a = "user-alice-123"
    user_a_headers = get_auth_headers(user_a)
    
    # User B credentials
    user_b = "user-bob-456"
    user_b_headers = get_auth_headers(user_b)
    
    async with httpx.AsyncClient(base_url=ORCHESTRATOR_URL, timeout=120.0) as client:
        
        # ----------------------------------------------------------------
        # Test 1: Create workspace for User A (provisions Daytona sandbox)
        # ----------------------------------------------------------------
        print("\n[Test 1] Creating workspace for User A...")
        print("         This provisions a Daytona sandbox and creates an Agent Server conversation")
        
        response = await client.post(
            "/workspaces",
            json={
                "initial_message": "Create a Python script that prints 'Hello from Alice!'",
                "workspace_name": "alice-dev-workspace"
            },
            headers=user_a_headers
        )
        
        if response.status_code != 200:
            print(f"  ✗ Failed: {response.status_code} - {response.text}")
            return
            
        workspace_a = response.json()
        print(f"  ✓ Workspace ID: {workspace_a['workspace_id']}")
        print(f"  ✓ Daytona Preview URL: {workspace_a['preview_url']}")
        print(f"  ✓ Agent Conversation ID: {workspace_a['conversation_id']}")
        print(f"  ✓ Status: {workspace_a['status']}")
        
        # ----------------------------------------------------------------
        # Test 2: Create workspace for User B
        # ----------------------------------------------------------------
        print("\n[Test 2] Creating workspace for User B...")
        
        response = await client.post(
            "/workspaces",
            json={
                "initial_message": "Create a Node.js script that prints 'Hello from Bob!'",
                "workspace_name": "bob-dev-workspace"
            },
            headers=user_b_headers
        )
        
        if response.status_code != 200:
            print(f"  ✗ Failed: {response.status_code} - {response.text}")
            return
            
        workspace_b = response.json()
        print(f"  ✓ Workspace ID: {workspace_b['workspace_id']}")
        print(f"  ✓ Daytona Preview URL: {workspace_b['preview_url']}")
        print(f"  ✓ Agent Conversation ID: {workspace_b['conversation_id']}")
        print(f"  ✓ Status: {workspace_b['status']}")
        
        # Wait for sandboxes to initialize and agents to process
        print("\n[Waiting] Letting Daytona sandboxes initialize and agents process...")
        await asyncio.sleep(15)
        
        # ----------------------------------------------------------------
        # Test 3: Check workspace status
        # ----------------------------------------------------------------
        print("\n[Test 3] Checking workspace statuses...")
        
        response = await client.get(
            f"/workspaces/{workspace_a['workspace_id']}",
            headers=user_a_headers
        )
        ws_a_status = response.json()
        print(f"  User A workspace: {ws_a_status['status']}")
        
        response = await client.get(
            f"/workspaces/{workspace_b['workspace_id']}",
            headers=user_b_headers
        )
        ws_b_status = response.json()
        print(f"  User B workspace: {ws_b_status['status']}")
        
        # ----------------------------------------------------------------
        # Test 4: Verify user isolation (User A cannot access User B's workspace)
        # ----------------------------------------------------------------
        print("\n[Test 4] Testing user isolation...")
        
        response = await client.get(
            f"/workspaces/{workspace_b['workspace_id']}",
            headers=user_a_headers  # User A trying to access User B's workspace
        )
        if response.status_code == 403:
            print("  ✓ User isolation working: User A cannot access User B's workspace")
        else:
            print(f"  ✗ Isolation failure: Got status {response.status_code}")
        
        # ----------------------------------------------------------------
        # Test 5: Send follow-up message to User A workspace
        # ----------------------------------------------------------------
        print("\n[Test 5] Sending follow-up message to User A workspace...")
        
        response = await client.post(
            f"/workspaces/{workspace_a['workspace_id']}/messages",
            json={"message": "Now modify the script to also print the current date and time"},
            headers=user_a_headers
        )
        
        if response.status_code == 200:
            print("  ✓ Message sent to Agent Server conversation")
        else:
            print(f"  ✗ Failed: {response.text}")
        
        await asyncio.sleep(10)
        
        # ----------------------------------------------------------------
        # Test 6: Pause workspace
        # ----------------------------------------------------------------
        print("\n[Test 6] Pausing User B workspace...")
        
        response = await client.post(
            f"/workspaces/{workspace_b['workspace_id']}/pause",
            headers=user_b_headers
        )
        
        if response.status_code == 200:
            print("  ✓ Workspace paused (Agent Server conversation paused)")
        
        response = await client.get(
            f"/workspaces/{workspace_b['workspace_id']}",
            headers=user_b_headers
        )
        print(f"  Status after pause: {response.json()['status']}")
        
        # ----------------------------------------------------------------
        # Test 7: Resume workspace
        # ----------------------------------------------------------------
        print("\n[Test 7] Resuming User B workspace...")
        
        response = await client.post(
            f"/workspaces/{workspace_b['workspace_id']}/resume",
            headers=user_b_headers
        )
        
        if response.status_code == 200:
            print("  ✓ Workspace resumed")
        
        response = await client.get(
            f"/workspaces/{workspace_b['workspace_id']}",
            headers=user_b_headers
        )
        print(f"  Status after resume: {response.json()['status']}")
        
        # ----------------------------------------------------------------
        # Test 8: List all workspaces for User A
        # ----------------------------------------------------------------
        print("\n[Test 8] Listing all workspaces for User A...")
        
        response = await client.get("/workspaces", headers=user_a_headers)
        user_a_workspaces = response.json()
        print(f"  ✓ User A has {len(user_a_workspaces)} workspace(s)")
        for ws in user_a_workspaces:
            print(f"    - {ws['workspace_id']}: {ws['status']}")
        
        # ----------------------------------------------------------------
        # Test 9: Destroy workspace B (destroys Daytona sandbox)
        # ----------------------------------------------------------------
        print("\n[Test 9] Destroying User B workspace...")
        print("         This will stop the Agent Server conversation and destroy the Daytona sandbox")
        
        response = await client.delete(
            f"/workspaces/{workspace_b['workspace_id']}",
            headers=user_b_headers
        )
        
        if response.status_code == 200:
            print("  ✓ Workspace destroyed")
            print("  ✓ Daytona sandbox terminated")
            print("  ✓ Agent Server conversation stopped")
        
        # Verify it's gone
        response = await client.get(
            f"/workspaces/{workspace_b['workspace_id']}",
            headers=user_b_headers
        )
        if response.status_code == 404:
            print("  ✓ Verified workspace no longer exists")
        
        # ----------------------------------------------------------------
        # Cleanup
        # ----------------------------------------------------------------
        print("\n[Cleanup] Destroying User A workspace...")
        await client.delete(
            f"/workspaces/{workspace_a['workspace_id']}",
            headers=user_a_headers
        )
        print("  ✓ Cleanup complete")
    
    print("\n" + "=" * 70)
    print("Experiment Complete!")
    print("=" * 70)


async def test_websocket_events():
    """
    Test WebSocket event streaming.
    
    Events flow: Agent Server → Orchestration Layer → Your Frontend
    """
    
    user_id = "ws-test-user"
    headers = get_auth_headers(user_id)
    
    print("\n[WebSocket Test] Testing real-time event streaming...")
    print("  Events flow: Agent Server → Orchestration Layer → Client")
    
    async with httpx.AsyncClient(base_url=ORCHESTRATOR_URL, timeout=120.0) as client:
        # Create a workspace with Daytona sandbox
        response = await client.post(
            "/workspaces",
            json={"workspace_name": "websocket-test"},
            headers=headers
        )
        workspace = response.json()
        workspace_id = workspace['workspace_id']
        print(f"  Created workspace: {workspace_id}")
        print(f"  Daytona sandbox URL: {workspace['preview_url']}")
        
        # Wait for sandbox to initialize
        await asyncio.sleep(10)
        
        # Connect WebSocket
        async with websockets.connect(f"{WS_URL}/ws/{workspace_id}") as ws:
            print("  ✓ Connected to WebSocket (proxied from Agent Server)")
            
            # Send a message (this will trigger events from Agent Server)
            await client.post(
                f"/workspaces/{workspace_id}/messages",
                json={"message": "List files in current directory"},
                headers=headers
            )
            print("  Sent message, waiting for events from Agent Server...")
            
            # Receive events
            events_received = []
            try:
                for _ in range(15):
                    event = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    event_data = json.loads(event)
                    event_type = event_data.get('type', event_data.get('event_type', 'unknown'))
                    events_received.append(event_type)
                    print(f"  ← Event: {event_type}")
            except asyncio.TimeoutError:
                print(f"  (Received {len(events_received)} events before timeout)")
        
        # Cleanup
        await client.delete(f"/workspaces/{workspace_id}", headers=headers)
        print("  ✓ WebSocket test complete, Daytona sandbox destroyed")


async def main():
    """Run all experiments."""
    print("\nStarting OpenHands SaaS Integration Tests")
    print("Make sure the following are running:")
    print("  1. Orchestration Layer (python orchestration_layer.py)")
    print("  2. OpenHands Agent Server")
    print("  3. Daytona API (or you have valid Daytona credentials)")
    print()
    
    await test_workspace_lifecycle()
    # await test_websocket_events()  # Uncomment to test WebSocket


if __name__ == "__main__":
    asyncio.run(main())
```

### Step 3: Run the Experiment

**Prerequisites Setup:**

```bash
# 1. Set environment variables
export DAYTONA_API_KEY="your-daytona-api-key"
export DAYTONA_API_URL="https://api.daytona.io"  # or your Daytona instance

export AGENT_SERVER_URL="http://localhost:8080"  # OpenHands Agent Server
export AGENT_SERVER_API_KEY="your-agent-server-key"

export LLM_API_KEY="your-anthropic-or-openai-api-key"
export LLM_MODEL="anthropic/claude-sonnet-4-5-20250929"
```

**Run the services:**

```bash
# Terminal 1: Start the OpenHands Agent Server (if not already running)
# This is the already-built server - you're not rebuilding it!
openhands-server --port 8080

# Terminal 2: Start the Orchestration Layer
python orchestration_layer.py

# Terminal 3: Run the Test Client
python test_client.py
```

### Expected Output

```
======================================================================
OpenHands SaaS Orchestration Layer - Integration Test
======================================================================
Orchestrator URL: http://localhost:8000
======================================================================

[Test 1] Creating workspace for User A...
         This provisions a Daytona sandbox and creates an Agent Server conversation
  ✓ Workspace ID: ws-a1b2c3d4
  ✓ Daytona Preview URL: https://a1b2c3d4.sandbox.daytona.io
  ✓ Agent Conversation ID: conv-xyz789
  ✓ Status: active

[Test 2] Creating workspace for User B...
  ✓ Workspace ID: ws-e5f6g7h8
  ✓ Daytona Preview URL: https://e5f6g7h8.sandbox.daytona.io
  ✓ Agent Conversation ID: conv-abc123
  ✓ Status: active

[Waiting] Letting Daytona sandboxes initialize and agents process...

[Test 3] Checking workspace statuses...
  User A workspace: ready
  User B workspace: ready

[Test 4] Testing user isolation...
  ✓ User isolation working: User A cannot access User B's workspace

[Test 5] Sending follow-up message to User A workspace...
  ✓ Message sent to Agent Server conversation

...

[Test 9] Destroying User B workspace...
         This will stop the Agent Server conversation and destroy the Daytona sandbox
  ✓ Workspace destroyed
  ✓ Daytona sandbox terminated
  ✓ Agent Server conversation stopped
  ✓ Verified workspace no longer exists

======================================================================
Experiment Complete!
======================================================================
```

### Experiment Metrics to Collect

| Metric | How to Measure | Target |
|--------|----------------|--------|
| Daytona Sandbox Provisioning | Time from request to sandbox ready | < 30 seconds |
| Workspace Creation (total) | Time including sandbox + conversation | < 45 seconds |
| Message Latency | Time from send to first Agent Server event | < 2 seconds |
| Concurrent Workspaces | Max simultaneous Daytona sandboxes | 5+ (depends on Daytona plan) |
| Event Streaming Latency | Agent Server → Client via proxy | < 100ms |

### Experiment Variations

Try these variations to validate your integration:

1. **Daytona Sandbox Reuse**: Create multiple conversations in the same sandbox
2. **Sandbox Recovery**: Test what happens when a Daytona sandbox crashes
3. **Agent Server Failover**: Test with Agent Server restart during conversation
4. **User Isolation Stress**: Verify users truly can't access each other's resources
5. **Long-Running Tasks**: Send complex multi-file coding tasks

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Daytona connection failed | Verify `DAYTONA_API_KEY` and `DAYTONA_API_URL` |
| Agent Server unreachable | Ensure Agent Server is running on `AGENT_SERVER_URL` |
| Sandbox timeout | Increase `init_timeout` in DaytonaClient |
| Auth errors (401/403) | Check auth token format, verify with your auth service |
| Conversation stuck | Check Agent Server logs, verify LLM API key |
| WebSocket disconnects | Check network, Agent Server WebSocket endpoint |

---

## Expanding the Mini-SaaS Experiment

Once you've validated the core concepts with the mini-SaaS experiment, here's a roadmap for expanding it into a production-ready platform.

### Expansion Roadmap

```mermaid
gantt
    title SaaS Platform Development Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 1: Foundation
    Database Integration     :p1a, 2024-01-01, 7d
    User Authentication      :p1b, after p1a, 7d
    API Rate Limiting        :p1c, after p1b, 3d
    
    section Phase 2: Production
    Docker Workspace Support :p2a, after p1c, 10d
    Webhook System           :p2b, after p2a, 5d
    Usage Tracking           :p2c, after p2b, 5d
    
    section Phase 3: Scale
    Redis for State          :p3a, after p2c, 7d
    Kubernetes Deployment    :p3b, after p3a, 10d
    Auto-scaling             :p3c, after p3b, 5d
    
    section Phase 4: Enterprise
    Multi-tenancy            :p4a, after p3c, 10d
    Billing Integration      :p4b, after p4a, 7d
    Admin Dashboard          :p4c, after p4b, 10d
```

### Expansion 1: Add Database Persistence

Replace in-memory storage with PostgreSQL for production reliability.

```python
# models/database.py
from sqlalchemy import create_engine, Column, String, DateTime, Enum, Float, Integer, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True)
    settings = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    users = relationship("User", back_populates="tenant")


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    password_hash = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(String(1), default="Y")
    
    tenant = relationship("Tenant", back_populates="users")
    workspaces = relationship("Workspace", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")
    subscription = relationship("Subscription", back_populates="user", uselist=False)


class ApiKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    key_hash = Column(String(255), nullable=False)
    name = Column(String(255))
    permissions = Column(JSON, default=["read", "write"])
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)
    
    user = relationship("User", back_populates="api_keys")


class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    session_id = Column(String(255), unique=True)
    name = Column(String(255))
    status = Column(String(50), default="creating")
    runtime_url = Column(String(500))
    resource_factor = Column(Integer, default=1)
    workspace_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime)
    total_cost = Column(Float, default=0.0)
    
    user = relationship("User", back_populates="workspaces")
    conversations = relationship("Conversation", back_populates="workspace")


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    status = Column(String(50), default="idle")
    title = Column(String(255))
    total_cost = Column(Float, default=0.0)
    step_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    workspace = relationship("Workspace", back_populates="conversations")
    events = relationship("Event", back_populates="conversation")


class Event(Base):
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"))
    event_type = Column(String(100), nullable=False)
    data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="events")


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    tier = Column(String(50), default="free")  # free, pro, enterprise
    status = Column(String(50), default="active")
    stripe_customer_id = Column(String(255))
    stripe_subscription_id = Column(String(255))
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    
    user = relationship("User", back_populates="subscription")


class UsageRecord(Base):
    __tablename__ = "usage_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    record_type = Column(String(50))  # llm_tokens, compute_minutes, storage_gb
    quantity = Column(Float)
    unit_cost = Column(Float)
    total_cost = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)


# Database setup
DATABASE_URL = "postgresql://user:password@localhost:5432/openhands_saas"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Expansion 2: Add User Authentication

Implement JWT-based authentication with refresh tokens.

```python
# auth/jwt_auth.py
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

SECRET_KEY = "your-super-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class TokenPayload(BaseModel):
    sub: str  # user_id
    tenant_id: str
    exp: datetime
    type: str  # "access" or "refresh"


class AuthService:
    """Authentication service for the SaaS platform."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def create_access_token(self, user_id: str, tenant_id: str) -> str:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "exp": expire,
            "type": "access"
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def create_refresh_token(self, user_id: str, tenant_id: str) -> str:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "exp": expire,
            "type": "refresh"
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def decode_token(self, token: str) -> Optional[TokenPayload]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def authenticate_user(self, email: str, password: str):
        from models.database import User
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not self.verify_password(password, user.password_hash):
            return None
        return user
    
    async def register_user(self, email: str, password: str, name: str, tenant_id: str):
        from models.database import User, Subscription
        
        # Check if user exists
        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        user = User(
            email=email,
            password_hash=self.hash_password(password),
            name=name,
            tenant_id=tenant_id
        )
        self.db.add(user)
        
        # Create free subscription
        subscription = Subscription(user_id=user.id, tier="free")
        self.db.add(subscription)
        
        self.db.commit()
        return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
):
    """Dependency to get the current authenticated user."""
    token = credentials.credentials
    auth_service = AuthService(db)
    payload = auth_service.decode_token(token)
    
    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    from models.database import User
    user = db.query(User).filter(User.id == payload.sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


# Auth endpoints
from fastapi import APIRouter

auth_router = APIRouter(prefix="/auth", tags=["authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

@auth_router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db = Depends(get_db)):
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    return TokenResponse(
        access_token=auth_service.create_access_token(str(user.id), str(user.tenant_id)),
        refresh_token=auth_service.create_refresh_token(str(user.id), str(user.tenant_id))
    )

@auth_router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db = Depends(get_db)):
    # For simplicity, auto-create tenant for new users
    from models.database import Tenant
    tenant = Tenant(name=f"{request.name}'s Organization")
    db.add(tenant)
    db.flush()
    
    auth_service = AuthService(db)
    user = await auth_service.register_user(
        email=request.email,
        password=request.password,
        name=request.name,
        tenant_id=str(tenant.id)
    )
    
    return TokenResponse(
        access_token=auth_service.create_access_token(str(user.id), str(tenant.id)),
        refresh_token=auth_service.create_refresh_token(str(user.id), str(tenant.id))
    )

@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
):
    auth_service = AuthService(db)
    payload = auth_service.decode_token(credentials.credentials)
    
    if payload.type != "refresh":
        raise HTTPException(status_code=400, detail="Invalid token type")
    
    return TokenResponse(
        access_token=auth_service.create_access_token(payload.sub, payload.tenant_id),
        refresh_token=auth_service.create_refresh_token(payload.sub, payload.tenant_id)
    )
```

### Expansion 3: Add Docker Workspace Support

Upgrade from LocalWorkspace to DockerWorkspace for real isolation.

```python
# workspaces/docker_manager.py
import docker
import uuid
from typing import Optional
from dataclasses import dataclass
import asyncio

@dataclass
class DockerWorkspaceConfig:
    base_image: str = "ghcr.io/openhands/agent-server:latest-python"
    memory_limit: str = "2g"
    cpu_limit: float = 1.0
    network_mode: str = "bridge"
    auto_remove: bool = True


class DockerWorkspaceManager:
    """Manages Docker-based workspaces for user isolation."""
    
    def __init__(self):
        self.client = docker.from_env()
        self.containers: dict[str, docker.models.containers.Container] = {}
    
    async def create_workspace(
        self,
        workspace_id: str,
        user_id: str,
        config: DockerWorkspaceConfig = DockerWorkspaceConfig()
    ) -> dict:
        """Create a new Docker workspace."""
        
        container_name = f"openhands-workspace-{workspace_id}"
        
        # Find available port
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            port = s.getsockname()[1]
        
        # Environment variables
        environment = {
            "WORKSPACE_ID": workspace_id,
            "USER_ID": user_id,
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        }
        
        # Create container
        container = self.client.containers.run(
            config.base_image,
            name=container_name,
            detach=True,
            ports={"8001/tcp": port},
            environment=environment,
            mem_limit=config.memory_limit,
            cpu_quota=int(config.cpu_limit * 100000),
            network_mode=config.network_mode,
            auto_remove=config.auto_remove,
            labels={
                "openhands.workspace_id": workspace_id,
                "openhands.user_id": user_id,
            }
        )
        
        self.containers[workspace_id] = container
        
        # Wait for container to be ready
        await self._wait_for_healthy(workspace_id, port)
        
        return {
            "workspace_id": workspace_id,
            "container_id": container.id,
            "port": port,
            "url": f"http://localhost:{port}"
        }
    
    async def _wait_for_healthy(self, workspace_id: str, port: int, timeout: int = 60):
        """Wait for workspace to be healthy."""
        import httpx
        
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"http://localhost:{port}/api/health")
                    if response.status_code == 200:
                        return
            except:
                pass
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Workspace {workspace_id} failed to become healthy")
    
    async def pause_workspace(self, workspace_id: str) -> bool:
        """Pause a workspace container."""
        container = self.containers.get(workspace_id)
        if container:
            container.pause()
            return True
        return False
    
    async def resume_workspace(self, workspace_id: str) -> bool:
        """Resume a paused workspace container."""
        container = self.containers.get(workspace_id)
        if container:
            container.unpause()
            return True
        return False
    
    async def destroy_workspace(self, workspace_id: str) -> bool:
        """Destroy a workspace container."""
        container = self.containers.get(workspace_id)
        if container:
            try:
                container.stop(timeout=10)
                container.remove(force=True)
            except:
                pass
            del self.containers[workspace_id]
            return True
        return False
    
    async def get_workspace_stats(self, workspace_id: str) -> Optional[dict]:
        """Get resource usage stats for a workspace."""
        container = self.containers.get(workspace_id)
        if container:
            stats = container.stats(stream=False)
            return {
                "cpu_percent": self._calculate_cpu_percent(stats),
                "memory_usage_mb": stats["memory_stats"]["usage"] / (1024 * 1024),
                "memory_limit_mb": stats["memory_stats"]["limit"] / (1024 * 1024),
                "network_rx_bytes": stats["networks"]["eth0"]["rx_bytes"],
                "network_tx_bytes": stats["networks"]["eth0"]["tx_bytes"],
            }
        return None
    
    def _calculate_cpu_percent(self, stats: dict) -> float:
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                    stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                       stats["precpu_stats"]["system_cpu_usage"]
        if system_delta > 0:
            return (cpu_delta / system_delta) * 100.0
        return 0.0
    
    def list_workspaces(self, user_id: Optional[str] = None) -> list[dict]:
        """List all workspace containers."""
        filters = {"label": "openhands.workspace_id"}
        if user_id:
            filters["label"] = f"openhands.user_id={user_id}"
        
        containers = self.client.containers.list(filters=filters)
        return [
            {
                "workspace_id": c.labels.get("openhands.workspace_id"),
                "user_id": c.labels.get("openhands.user_id"),
                "status": c.status,
                "created": c.attrs["Created"],
            }
            for c in containers
        ]
```

### Expansion 4: Add Usage Tracking and Billing

Track usage for billing purposes.

```python
# billing/usage_tracker.py
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal
import asyncio

class UsageTracker:
    """Tracks usage metrics for billing."""
    
    # Pricing per unit
    PRICING = {
        "llm_tokens": Decimal("0.00001"),  # Per token
        "compute_minutes": Decimal("0.01"),  # Per minute
        "storage_gb": Decimal("0.10"),  # Per GB per month
    }
    
    # Tier limits
    TIER_LIMITS = {
        "free": {
            "llm_tokens_per_month": 100_000,
            "compute_minutes_per_month": 60,
            "max_workspaces": 1,
            "max_iterations": 50,
        },
        "pro": {
            "llm_tokens_per_month": 1_000_000,
            "compute_minutes_per_month": 600,
            "max_workspaces": 5,
            "max_iterations": 200,
        },
        "enterprise": {
            "llm_tokens_per_month": 10_000_000,
            "compute_minutes_per_month": 6000,
            "max_workspaces": 50,
            "max_iterations": 500,
        },
    }
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def record_llm_usage(
        self,
        user_id: str,
        workspace_id: str,
        input_tokens: int,
        output_tokens: int,
        model: str
    ):
        """Record LLM token usage."""
        from models.database import UsageRecord
        
        total_tokens = input_tokens + output_tokens
        unit_cost = float(self.PRICING["llm_tokens"])
        total_cost = total_tokens * unit_cost
        
        record = UsageRecord(
            user_id=user_id,
            workspace_id=workspace_id,
            record_type="llm_tokens",
            quantity=total_tokens,
            unit_cost=unit_cost,
            total_cost=total_cost,
        )
        self.db.add(record)
        self.db.commit()
        
        return record
    
    async def record_compute_usage(
        self,
        user_id: str,
        workspace_id: str,
        minutes: float
    ):
        """Record compute time usage."""
        from models.database import UsageRecord
        
        unit_cost = float(self.PRICING["compute_minutes"])
        total_cost = minutes * unit_cost
        
        record = UsageRecord(
            user_id=user_id,
            workspace_id=workspace_id,
            record_type="compute_minutes",
            quantity=minutes,
            unit_cost=unit_cost,
            total_cost=total_cost,
        )
        self.db.add(record)
        self.db.commit()
        
        return record
    
    async def get_usage_summary(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get usage summary for a user."""
        from models.database import UsageRecord
        from sqlalchemy import func
        
        if not start_date:
            start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        if not end_date:
            end_date = datetime.utcnow()
        
        records = self.db.query(
            UsageRecord.record_type,
            func.sum(UsageRecord.quantity).label("total_quantity"),
            func.sum(UsageRecord.total_cost).label("total_cost")
        ).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.recorded_at >= start_date,
            UsageRecord.recorded_at <= end_date
        ).group_by(UsageRecord.record_type).all()
        
        summary = {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "usage": {},
            "total_cost": 0.0
        }
        
        for record in records:
            summary["usage"][record.record_type] = {
                "quantity": float(record.total_quantity),
                "cost": float(record.total_cost)
            }
            summary["total_cost"] += float(record.total_cost)
        
        return summary
    
    async def check_limits(self, user_id: str, resource_type: str, requested: float) -> dict:
        """Check if user is within their tier limits."""
        from models.database import User, Subscription, UsageRecord
        from sqlalchemy import func
        
        # Get user's subscription tier
        user = self.db.query(User).filter(User.id == user_id).first()
        subscription = self.db.query(Subscription).filter(Subscription.user_id == user_id).first()
        
        tier = subscription.tier if subscription else "free"
        limits = self.TIER_LIMITS[tier]
        
        # Get current month's usage
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        current_usage = self.db.query(
            func.sum(UsageRecord.quantity)
        ).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.record_type == resource_type,
            UsageRecord.recorded_at >= month_start
        ).scalar() or 0
        
        limit_key = f"{resource_type}_per_month"
        limit = limits.get(limit_key, float("inf"))
        
        return {
            "allowed": current_usage + requested <= limit,
            "current_usage": float(current_usage),
            "limit": limit,
            "remaining": max(0, limit - current_usage),
            "tier": tier
        }


# Usage tracking middleware
from starlette.middleware.base import BaseHTTPMiddleware

class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track API usage."""
    
    async def dispatch(self, request, call_next):
        start_time = datetime.utcnow()
        response = await call_next(request)
        
        # Track compute time for workspace operations
        if "/workspaces/" in request.url.path:
            end_time = datetime.utcnow()
            duration_minutes = (end_time - start_time).total_seconds() / 60
            
            # Get user from request state (set by auth middleware)
            user_id = getattr(request.state, "user_id", None)
            workspace_id = request.path_params.get("workspace_id")
            
            if user_id and workspace_id and duration_minutes > 0.01:
                # Record async (don't block response)
                asyncio.create_task(
                    self._record_usage(user_id, workspace_id, duration_minutes)
                )
        
        return response
    
    async def _record_usage(self, user_id: str, workspace_id: str, minutes: float):
        from models.database import get_db
        db = next(get_db())
        tracker = UsageTracker(db)
        await tracker.record_compute_usage(user_id, workspace_id, minutes)
```

### Expansion 5: Add Redis for Distributed State

Enable horizontal scaling with Redis for shared state.

```python
# state/redis_state.py
import redis
import json
from typing import Optional, Any
from datetime import timedelta

class RedisStateManager:
    """Manages distributed state using Redis."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.pubsub = self.redis.pubsub()
    
    # -------------------------------------------------------------------------
    # Workspace State
    # -------------------------------------------------------------------------
    
    def set_workspace_state(self, workspace_id: str, state: dict, ttl: int = 3600):
        """Store workspace state in Redis."""
        key = f"workspace:{workspace_id}:state"
        self.redis.setex(key, ttl, json.dumps(state))
    
    def get_workspace_state(self, workspace_id: str) -> Optional[dict]:
        """Get workspace state from Redis."""
        key = f"workspace:{workspace_id}:state"
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def delete_workspace_state(self, workspace_id: str):
        """Delete workspace state from Redis."""
        key = f"workspace:{workspace_id}:state"
        self.redis.delete(key)
    
    # -------------------------------------------------------------------------
    # Event Streaming
    # -------------------------------------------------------------------------
    
    async def publish_event(self, workspace_id: str, event: dict):
        """Publish an event to Redis PubSub."""
        channel = f"workspace:{workspace_id}:events"
        self.redis.publish(channel, json.dumps(event))
    
    async def subscribe_to_events(self, workspace_id: str, callback):
        """Subscribe to events for a workspace."""
        channel = f"workspace:{workspace_id}:events"
        self.pubsub.subscribe(**{channel: callback})
        self.pubsub.run_in_thread(sleep_time=0.001)
    
    def unsubscribe_from_events(self, workspace_id: str):
        """Unsubscribe from workspace events."""
        channel = f"workspace:{workspace_id}:events"
        self.pubsub.unsubscribe(channel)
    
    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------
    
    def create_session(self, session_id: str, user_id: str, data: dict, ttl: int = 86400):
        """Create a user session."""
        key = f"session:{session_id}"
        session_data = {"user_id": user_id, **data}
        self.redis.setex(key, ttl, json.dumps(session_data))
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        key = f"session:{session_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def extend_session(self, session_id: str, ttl: int = 86400):
        """Extend session TTL."""
        key = f"session:{session_id}"
        self.redis.expire(key, ttl)
    
    def delete_session(self, session_id: str):
        """Delete a session."""
        key = f"session:{session_id}"
        self.redis.delete(key)
    
    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    
    def check_rate_limit(
        self,
        user_id: str,
        action: str,
        limit: int,
        window_seconds: int = 60
    ) -> dict:
        """Check and update rate limit for a user action."""
        key = f"ratelimit:{user_id}:{action}"
        
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = pipe.execute()
        
        current_count = results[0]
        
        return {
            "allowed": current_count <= limit,
            "current_count": current_count,
            "limit": limit,
            "remaining": max(0, limit - current_count),
            "reset_in_seconds": self.redis.ttl(key)
        }
    
    # -------------------------------------------------------------------------
    # Distributed Locking
    # -------------------------------------------------------------------------
    
    def acquire_lock(self, resource: str, ttl: int = 30) -> Optional[str]:
        """Acquire a distributed lock."""
        import uuid
        lock_id = str(uuid.uuid4())
        key = f"lock:{resource}"
        
        if self.redis.set(key, lock_id, nx=True, ex=ttl):
            return lock_id
        return None
    
    def release_lock(self, resource: str, lock_id: str) -> bool:
        """Release a distributed lock."""
        key = f"lock:{resource}"
        
        # Use Lua script to ensure atomic check-and-delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        return bool(self.redis.eval(script, 1, key, lock_id))


# WebSocket manager using Redis PubSub
class RedisWebSocketManager:
    """Manages WebSocket connections across multiple server instances."""
    
    def __init__(self, redis_state: RedisStateManager):
        self.redis_state = redis_state
        self.local_connections: dict[str, list] = {}
    
    async def connect(self, workspace_id: str, websocket):
        """Register a WebSocket connection."""
        if workspace_id not in self.local_connections:
            self.local_connections[workspace_id] = []
            # Subscribe to Redis channel for this workspace
            await self.redis_state.subscribe_to_events(
                workspace_id,
                lambda msg: self._handle_redis_message(workspace_id, msg)
            )
        
        self.local_connections[workspace_id].append(websocket)
    
    def disconnect(self, workspace_id: str, websocket):
        """Unregister a WebSocket connection."""
        if workspace_id in self.local_connections:
            try:
                self.local_connections[workspace_id].remove(websocket)
            except ValueError:
                pass
            
            if not self.local_connections[workspace_id]:
                self.redis_state.unsubscribe_from_events(workspace_id)
                del self.local_connections[workspace_id]
    
    async def broadcast(self, workspace_id: str, event: dict):
        """Broadcast event to all connected clients (via Redis)."""
        await self.redis_state.publish_event(workspace_id, event)
    
    def _handle_redis_message(self, workspace_id: str, message):
        """Handle message from Redis and forward to local WebSockets."""
        if message["type"] == "message":
            event = json.loads(message["data"])
            asyncio.create_task(self._broadcast_local(workspace_id, event))
    
    async def _broadcast_local(self, workspace_id: str, event: dict):
        """Broadcast to local WebSocket connections."""
        connections = self.local_connections.get(workspace_id, [])
        for ws in connections:
            try:
                await ws.send_json(event)
            except:
                pass
```

### Expansion 6: Add Webhook System

Notify external services about important events.

```python
# webhooks/webhook_service.py
import httpx
import hashlib
import hmac
import json
import asyncio
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

@dataclass
class WebhookConfig:
    url: str
    secret: str
    events: list[str] = field(default_factory=lambda: ["*"])
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0


class WebhookService:
    """Service for sending webhooks to external services."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.webhooks: dict[str, list[WebhookConfig]] = {}  # user_id -> webhooks
        self._client = httpx.AsyncClient(timeout=30.0)
    
    def register_webhook(self, user_id: str, config: WebhookConfig):
        """Register a webhook for a user."""
        if user_id not in self.webhooks:
            self.webhooks[user_id] = []
        self.webhooks[user_id].append(config)
    
    def unregister_webhook(self, user_id: str, url: str):
        """Unregister a webhook."""
        if user_id in self.webhooks:
            self.webhooks[user_id] = [
                wh for wh in self.webhooks[user_id] if wh.url != url
            ]
    
    async def send_webhook(
        self,
        user_id: str,
        event_type: str,
        payload: dict
    ):
        """Send webhook to all registered endpoints for this event type."""
        webhooks = self.webhooks.get(user_id, [])
        
        for webhook in webhooks:
            if "*" in webhook.events or event_type in webhook.events:
                asyncio.create_task(
                    self._send_with_retry(webhook, event_type, payload)
                )
    
    async def _send_with_retry(
        self,
        webhook: WebhookConfig,
        event_type: str,
        payload: dict
    ):
        """Send webhook with retry logic."""
        body = json.dumps({
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload
        })
        
        # Generate signature
        signature = self._generate_signature(body, webhook.secret)
        
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Event": event_type,
        }
        
        for attempt in range(webhook.retry_attempts):
            try:
                response = await self._client.post(
                    webhook.url,
                    content=body,
                    headers=headers,
                    timeout=webhook.timeout
                )
                
                if response.status_code < 300:
                    return  # Success
                
                # Log non-2xx response
                print(f"Webhook returned {response.status_code}: {response.text}")
                
            except Exception as e:
                print(f"Webhook attempt {attempt + 1} failed: {e}")
            
            if attempt < webhook.retry_attempts - 1:
                await asyncio.sleep(webhook.retry_delay * (2 ** attempt))
        
        # All retries failed
        print(f"Webhook to {webhook.url} failed after {webhook.retry_attempts} attempts")
    
    def _generate_signature(self, body: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        return hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()


# Webhook events
WEBHOOK_EVENTS = [
    "workspace.created",
    "workspace.paused",
    "workspace.resumed",
    "workspace.destroyed",
    "conversation.started",
    "conversation.completed",
    "conversation.error",
    "message.received",
    "action.executed",
    "usage.limit_reached",
]


# Webhook endpoints for user management
from fastapi import APIRouter

webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])

class WebhookCreateRequest(BaseModel):
    url: str
    secret: str
    events: list[str] = ["*"]

@webhook_router.post("/")
async def create_webhook(
    request: WebhookCreateRequest,
    current_user = Depends(get_current_user),
    webhook_service: WebhookService = Depends()
):
    """Register a new webhook endpoint."""
    config = WebhookConfig(
        url=request.url,
        secret=request.secret,
        events=request.events
    )
    webhook_service.register_webhook(str(current_user.id), config)
    return {"success": True, "message": "Webhook registered"}

@webhook_router.delete("/")
async def delete_webhook(
    url: str,
    current_user = Depends(get_current_user),
    webhook_service: WebhookService = Depends()
):
    """Unregister a webhook endpoint."""
    webhook_service.unregister_webhook(str(current_user.id), url)
    return {"success": True, "message": "Webhook unregistered"}

@webhook_router.get("/events")
async def list_webhook_events():
    """List all available webhook events."""
    return {"events": WEBHOOK_EVENTS}
```

### Putting It All Together: Production Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web App]
        MOBILE[Mobile App]
        API_CLIENT[API Clients]
    end
    
    subgraph "Edge Layer"
        CDN[CDN / Static Assets]
        LB[Load Balancer<br/>nginx / ALB]
    end
    
    subgraph "API Gateway"
        KONG[API Gateway<br/>Kong / AWS API GW]
        AUTH_MW[Auth Middleware]
        RATE_MW[Rate Limiter]
    end
    
    subgraph "Application Layer"
        API_1[API Server 1<br/>FastAPI]
        API_2[API Server 2<br/>FastAPI]
        API_N[API Server N<br/>FastAPI]
        WS_1[WebSocket Server 1]
        WS_2[WebSocket Server 2]
    end
    
    subgraph "Message Layer"
        REDIS[(Redis<br/>PubSub + Cache)]
        QUEUE[(Task Queue<br/>Celery / SQS)]
    end
    
    subgraph "Workspace Layer"
        subgraph "Kubernetes Cluster"
            WS_MGR[Workspace Manager]
            POD_1[Agent Pod 1]
            POD_2[Agent Pod 2]
            POD_N[Agent Pod N]
        end
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL<br/>Primary)]
        PG_R[(PostgreSQL<br/>Replica)]
        S3[(S3 / Object Storage)]
    end
    
    subgraph "External Services"
        LLM[LLM APIs<br/>OpenAI / Anthropic]
        STRIPE[Stripe<br/>Billing]
        SENDGRID[SendGrid<br/>Email]
        WEBHOOK_EXT[External Webhooks]
    end
    
    subgraph "Observability"
        PROM[Prometheus]
        GRAF[Grafana]
        SENTRY[Sentry]
        LOGS[Log Aggregator]
    end
    
    WEB --> CDN
    MOBILE --> LB
    API_CLIENT --> LB
    CDN --> LB
    
    LB --> KONG
    KONG --> AUTH_MW
    AUTH_MW --> RATE_MW
    RATE_MW --> API_1
    RATE_MW --> API_2
    RATE_MW --> API_N
    
    LB --> WS_1
    LB --> WS_2
    
    API_1 <--> REDIS
    API_2 <--> REDIS
    WS_1 <--> REDIS
    WS_2 <--> REDIS
    
    API_1 --> QUEUE
    QUEUE --> WS_MGR
    WS_MGR --> POD_1
    WS_MGR --> POD_2
    WS_MGR --> POD_N
    
    API_1 --> PG
    PG --> PG_R
    POD_1 --> S3
    
    API_1 --> LLM
    API_1 --> STRIPE
    API_1 --> SENDGRID
    API_1 --> WEBHOOK_EXT
    
    API_1 --> PROM
    PROM --> GRAF
    API_1 --> SENTRY
    API_1 --> LOGS
```

### Next Steps Checklist

After completing the expansions, here's what to build next:

- [ ] **Admin Dashboard**: UI for managing tenants, users, and workspaces
- [ ] **Monitoring Dashboard**: Real-time metrics and alerting
- [ ] **API Documentation**: OpenAPI/Swagger with interactive docs
- [ ] **SDK Clients**: JavaScript, Python, Go client libraries
- [ ] **CI/CD Pipeline**: Automated testing and deployment
- [ ] **Disaster Recovery**: Backup and restore procedures
- [ ] **Security Audit**: Penetration testing and compliance review
- [ ] **Performance Testing**: Load testing and optimization

---

## Conclusion

The OpenHands Software Agent SDK provides a comprehensive framework for building intelligent software agents. Its modular architecture, extensible tool system, and skills framework enable the creation of sophisticated agents for various software development tasks.

For more detailed examples and advanced usage patterns, explore the `examples/` directory and the source code documentation.