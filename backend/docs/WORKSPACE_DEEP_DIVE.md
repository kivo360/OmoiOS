# Workspace Architecture Deep Dive

## Executive Summary

This document explores the different paths for agent execution isolation and how to achieve a remote server that spawns cloud sandboxes (like Daytona).

**Current state**: Your code has workspace mode infrastructure but it's not wired into Conversation objects.

**Verified SDK Facts (v1.1.0)**:
- `Conversation` accepts: `str | LocalWorkspace | RemoteWorkspace` (line 79 of SDK source)
- `DockerWorkspace` exists in `openhands-workspace` but **fails to import** outside OpenHands monorepo
- No Docker isolation available via current SDK for standalone use

**Three paths forward**:
1. **Stay local** - Use `LocalWorkspace` (current default, works now)
2. **Use OpenHands agent-server** - Deploy agent-server, connect via `RemoteWorkspace`
3. **Use Daytona** - Your existing `OpenHandsDaytonaWorkspace` adapter (needs wiring)

---

## Architecture Options Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXECUTION MODELS                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  OPTION A: LOCAL (Current Default)                                          │
│  ┌──────────────┐                                                           │
│  │ Your Backend │ ──── Conversation ──── LocalWorkspace ──── Filesystem    │
│  │              │ ──── persistence_dir (local)                              │
│  └──────────────┘                                                           │
│  ✅ Simple, works now                                                       │
│  ❌ No isolation, risky for untrusted code                                  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  OPTION B: LOCAL + DOCKER                                                   │
│  ┌──────────────┐                                                           │
│  │ Your Backend │ ──── Conversation ──── DockerWorkspace ──── Container    │
│  │              │ ──── persistence_dir (local)                              │
│  │              │ ──── mount_dir (shared volume)                            │
│  └──────────────┘                                                           │
│  ✅ Isolated execution, local control                                       │
│  ⚠️ Requires Docker on same machine                                         │
│  ⚠️ Need to fix AgentExecutor to use workspace objects                      │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  OPTION C: LOCAL + DAYTONA (What You Have Partially)                        │
│  ┌──────────────┐                                                           │
│  │ Your Backend │ ──── Conversation ────┬──── persistence_dir (local)      │
│  │              │                       │                                   │
│  └──────────────┘                       │                                   │
│                                         ▼                                   │
│                               ┌─────────────────┐                           │
│                               │  DAYTONA CLOUD  │ ◄── Commands execute here │
│                               │  (API sandbox)  │                           │
│                               └─────────────────┘                           │
│  ✅ Cloud-scalable execution                                                │
│  ✅ No local Docker needed                                                  │
│  ⚠️ persistence_dir still local (Guardian works!)                          │
│  ⚠️ Need to fix AgentExecutor to pass workspace object                      │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  OPTION D: OPENHANDS AGENT-SERVER                                           │
│  ┌──────────────┐         ┌─────────────────────────────────┐              │
│  │ Your Backend │ ──HTTP──│      OPENHANDS AGENT-SERVER     │              │
│  │              │         │                                 │              │
│  │  Guardian ───┼──HTTP───┤  ┌──────────────┐              │              │
│  │              │         │  │ Conversation │              │              │
│  └──────────────┘         │  │ persistence  │              │              │
│                           │  └──────────────┘              │              │
│                           │         │                      │              │
│                           │         ▼                      │              │
│                           │  ┌──────────────┐              │              │
│                           │  │   Docker     │              │              │
│                           │  │  Container   │              │              │
│                           │  └──────────────┘              │              │
│                           └─────────────────────────────────┘              │
│  ✅ Complete isolation                                                      │
│  ✅ Agent-server handles container lifecycle                                │
│  ✅ REST API for conversation control                                       │
│  ❌ Guardian needs HTTP-based intervention (not local filesystem)          │
│  ❌ Requires running agent-server infrastructure                            │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  OPTION E: YOUR OWN SERVER + DAYTONA (Future Goal)                          │
│  ┌──────────────┐         ┌─────────────────────────────────┐              │
│  │   Frontend   │ ──HTTP──│     YOUR ORCHESTRATION SERVER    │              │
│  │   or CLI     │         │                                 │              │
│  └──────────────┘         │  ┌──────────────┐  ┌────────┐  │              │
│                           │  │ Conversation │  │Guardian│  │              │
│                           │  │ Management   │──│Service │  │              │
│                           │  └──────────────┘  └────────┘  │              │
│                           │         │                      │              │
│                           │         ▼ (Daytona API)        │              │
│                           └─────────│───────────────────────┘              │
│                                     ▼                                       │
│                           ┌─────────────────┐                               │
│                           │  DAYTONA CLOUD  │                               │
│                           │   (Sandboxes)   │                               │
│                           └─────────────────┘                               │
│  ✅ Full control over orchestration                                         │
│  ✅ Daytona provides cloud-native sandboxes                                 │
│  ✅ Guardian can use HTTP or websocket to intervene                         │
│  ❌ Need to build the orchestration layer yourself                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Option Analysis

### Option A: Local (Stay Here for MVP)

**What you have**: Works today with `WORKSPACE_MODE=local`

**Guardian interventions**: ✅ Work via local filesystem

**Recommendation**: Fine for development and testing. Not production-safe.

---

### Option B: Docker (⚠️ NOT AVAILABLE via SDK)

**Reality check**: `DockerWorkspace` exists in `openhands-workspace` package but **fails to import**:
```
RuntimeError: Could not resolve the OpenHands UV workspace root.

Expected repo layout:
  pyproject.toml  (with [tool.uv.workspace].members including openhands/* subprojects)
  openhands-sdk/pyproject.toml
  ...
```

**What this means**: Docker isolation requires either:
1. Running inside the OpenHands monorepo (not practical for your use case)
2. Using the agent-server (Option D) which handles Docker internally
3. Using Daytona (Option C) which provides cloud-based isolation

**Your factory code** at `workspace_manager.py:735` will fallback to `LocalWorkspace` when `DockerWorkspace` import fails.

---

### Option C: Daytona (What You're Exploring)

**Current state**: `OpenHandsDaytonaWorkspace` exists but isn't used by `AgentExecutor`

**Same fix needed as Option B** - pass the workspace object to Conversation

**Guardian interventions**: ✅ Work - persistence_dir stays local, only execution goes to Daytona

**Key insight**: Daytona is an execution backend, not a conversation manager. Your backend still controls conversations locally.

---

### Option D: OpenHands Agent-Server

**How it works**:
1. You run `openhands-agent-server` (Docker or native)
2. Your backend uses `RemoteWorkspace` to connect
3. Agent-server spawns Docker containers per conversation
4. All conversation state lives ON the agent-server

**Guardian changes needed**:
```python
# Instead of local filesystem:
conversation = Conversation(
    persistence_dir=local_path,  # ← Won't work
    ...
)

# Use HTTP API:
POST /api/conversations/{id}/events
{
  "role": "user",
  "content": [{"type": "text", "text": "[GUARDIAN]: ..."}],
  "run": true
}
```

**Agent-server API endpoints**:
- `POST /api/conversations` - Create conversation
- `POST /api/conversations/{id}/events` - Send message
- `GET /api/conversations/{id}/events` - Get events
- `POST /api/conversations/{id}/run` - Resume execution

---

### Option E: Your Own Daytona-Backed Server (Future)

This is essentially building your own agent-server but with Daytona as the sandbox backend.

**Architecture**:
```
┌─────────────────────────────────────────────────────────┐
│              YOUR ORCHESTRATION SERVER                   │
│                                                         │
│  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ FastAPI Routes  │  │    ConversationManager      │  │
│  │                 │  │                             │  │
│  │ POST /convos    │──│ create_conversation()       │  │
│  │ POST /convos/   │  │ send_message()              │  │
│  │   {id}/message  │──│ run()                       │  │
│  │ GET /convos/    │  │ get_events()                │  │
│  │   {id}/events   │──│ inject_intervention()       │  │
│  └─────────────────┘  └─────────────┬───────────────┘  │
│                                     │                  │
│  ┌─────────────────┐               │                  │
│  │ Guardian Loop   │───────────────┤                  │
│  │ (monitors all   │               │                  │
│  │  conversations) │               │                  │
│  └─────────────────┘               │                  │
│                                     │                  │
│  ┌─────────────────────────────────┴─────────────────┐│
│  │              DaytonaSandboxManager                ││
│  │                                                   ││
│  │  create_sandbox(project_id) -> sandbox_id        ││
│  │  execute_command(sandbox_id, cmd) -> result      ││
│  │  upload_file(sandbox_id, src, dst)               ││
│  │  destroy_sandbox(sandbox_id)                     ││
│  └───────────────────────────────────────────────────┘│
│                           │                           │
└───────────────────────────│───────────────────────────┘
                            │ HTTPS/API
                            ▼
                  ┌─────────────────┐
                  │  DAYTONA CLOUD  │
                  │   Sandboxes     │
                  └─────────────────┘
```

**Key components you'd build**:
1. **ConversationManager** - Stores conversation state, manages OpenHands Conversation objects
2. **DaytonaSandboxManager** - Wraps Daytona API for sandbox lifecycle
3. **REST API** - Exposes conversation control to clients
4. **WebSocket** - Real-time event streaming
5. **Guardian integration** - Can call inject_intervention() directly

---

## Recommended Path

### Phase 1: Stay Local (Current State - Works Now)
- `WORKSPACE_MODE=local` (default)
- String path passed to `Conversation` creates `LocalConversation`
- Guardian interventions work via local filesystem
- **No changes needed for MVP**

### Phase 2: Wire Up Daytona (SOLVED)
**New SDK-compatible adapter created**: `omoi_os/workspace/daytona_sdk.py`

```python
from omoi_os.workspace.daytona_sdk import DaytonaLocalWorkspace

workspace = DaytonaLocalWorkspace(
    working_dir="/tmp/staging",
    daytona_api_key=settings.api_key,
    sandbox_image="nikolaik/python-nodejs:python3.12-nodejs22",
    project_id="my-project",
)

with workspace:
    conversation = Conversation(agent=agent, workspace=workspace)
    conversation.send_message("Hello")
    conversation.run()
```

**Key features**:
- Inherits from `LocalWorkspace` (passes SDK assertion)
- Commands execute in Daytona cloud sandbox
- Works with SDK Conversation directly
- Guardian still works (persistence_dir stays local)

### Phase 3: Evaluate Agent-Server (For Full Remote)
1. Run OpenHands agent-server locally
2. Use `RemoteWorkspace` to connect
3. Prototype HTTP-based Guardian interventions
4. Consider if you need full conversation state on remote server

### Phase 4: Custom Orchestration (Future)
Only if agent-server doesn't meet your needs:
1. Build REST API for conversation management
2. Integrate Daytona as sandbox backend
3. Refactor Guardian to use HTTP interventions

**Note**: Skip the Docker option - SDK doesn't support it for standalone use.

---

## Quick Reference: What Works With Guardian

| Mode | SDK Support | Guardian Works? | Notes |
|------|-------------|-----------------|-------|
| Local | ✅ `LocalWorkspace` | ✅ Yes | Default, works now |
| Docker | ❌ Import fails | N/A | Use agent-server or Daytona instead |
| Daytona | ⚠️ Custom adapter | ✅ Yes | `OpenHandsDaytonaWorkspace` exists, needs wiring |
| Agent-Server | ✅ `RemoteWorkspace` | ⚠️ HTTP needed | persistence_dir is remote |

**Verified SDK behavior (v1.1.0)**:
- `Conversation` factory (line 79): accepts `str | LocalWorkspace | RemoteWorkspace`
- String path → creates `LocalConversation` (what your code does now)
- `LocalWorkspace` → creates `LocalConversation`
- `RemoteWorkspace` → creates `RemoteConversation` (for agent-server)

**Key insight**: Guardian works with local/daytona modes because persistence_dir stays local.

---

## Files to Study

### Core Workspace Integration
- `omoi_os/services/agent_executor.py:291-314` - Unused `openhands_workspace` property
- `omoi_os/services/agent_executor.py:505-510` - Where Conversation is created
- `omoi_os/services/workspace_manager.py:660-828` - Factory implementation

### Daytona Implementation
- `omoi_os/workspace/daytona.py:605-873` - OpenHandsDaytonaWorkspace adapter
- `omoi_os/config.py:398-420` - DaytonaSettings

### OpenHands SDK Reference
- https://docs.openhands.dev/sdk/api-reference/openhands.sdk.workspace
- https://docs.openhands.dev/sdk/guides/agent-server/overview
- https://docs.openhands.dev/sdk/guides/agent-server/docker-sandbox

### Agent-Server API
- https://docs.openhands.dev/sdk/guides/agent-server/api-reference/events/send-message

---

## Verification Log

**Date**: 2025-12-01
**SDK Version**: openhands-sdk 1.1.0, openhands-workspace 1.1.0

### Verified Inconsistencies

#### 1. OpenHandsDaytonaWorkspace WILL FAIL with SDK
**Location**: `omoi_os/workspace/daytona.py:605`
**Issue**: Does NOT inherit from `BaseWorkspace`
```python
class OpenHandsDaytonaWorkspace:  # ← No BaseWorkspace inheritance
```
**Why it matters**: `LocalConversation` has assertion at line 93:
```python
assert isinstance(workspace, LocalWorkspace), "workspace must be a LocalWorkspace instance"
```
Passing `OpenHandsDaytonaWorkspace` → `AssertionError`

#### 2. Return Type Annotation Wrong
**Location**: `workspace_manager.py:763`
```python
def _create_remote_workspace(self, workspace_path: Path) -> "LocalWorkspace":  # ← WRONG
    # ... actually returns RemoteWorkspace
```

#### 3. SDK Conversation Type Union Too Restrictive
**Location**: SDK `conversation.py:79`
```python
workspace: str | LocalWorkspace | RemoteWorkspace  # ← No BaseWorkspace!
```
Custom workspace adapters cannot be used with SDK Conversation.

#### 4. DockerWorkspace Import Fails Outside Monorepo
**Location**: SDK `openhands.workspace.docker`
```
RuntimeError: Could not resolve the OpenHands UV workspace root.
```
Factory at `workspace_manager.py:735` will silently fallback to LocalWorkspace.

#### 5. openhands_workspace Property Unused
**Location**: `agent_executor.py:291-314`
- Property creates workspace objects via factory
- Never called by `execute_task()` or `prepare_conversation()`
- Conversation always receives `self.workspace_dir` (string)

### SDK Source Verification

1. **LocalConversation** (`.venv/.../local_conversation.py:91-95`):
   ```python
   if isinstance(workspace, str):
       workspace = LocalWorkspace(working_dir=workspace)
   assert isinstance(workspace, LocalWorkspace), "workspace must be a LocalWorkspace instance"
   ```

2. **RemoteWorkspace parameters** (`.venv/.../remote_workspace_mixin.py:21-27`):
   ```python
   host: str  # Required
   api_key: str | None  # Optional
   working_dir: str  # Required
   ```

3. **Agent-server API** (`.venv/.../agent_server/conversation_router.py`):
   - `POST /conversations` - Start conversation
   - `POST /conversations/{id}/run` - Run conversation
   - `POST /conversations/{id}/pause` - Pause conversation
   - `GET /conversations/{id}` - Get conversation info
   - `DELETE /conversations/{id}` - Delete conversation

### Experiment Results (2025-12-01)

Ran `experiments/test_daytona_sdk_workspace.py`:

1. **OLD OpenHandsDaytonaWorkspace**: `isinstance(LocalWorkspace) = False` ❌
2. **NEW DaytonaLocalWorkspace**: `isinstance(LocalWorkspace) = True` ✅
3. **Sandbox operations**: Commands executed in Daytona cloud ✅
4. **SDK Conversation**: Created successfully with DaytonaLocalWorkspace ✅

**Solution**: Use `DaytonaLocalWorkspace` from `omoi_os/workspace/daytona_sdk.py`

### Claims NOT Verified (Needs Manual Testing)

- Agent-server actual runtime behavior
- RemoteWorkspace connectivity to agent-server
- Guardian intervention injection timing
