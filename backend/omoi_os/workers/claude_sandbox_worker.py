#!/usr/bin/env python3
"""
Claude Sandbox Agent Worker - Production-ready agent for Daytona sandboxes.

This is a STANDALONE script with NO local dependencies.
Just copy this file + install deps:

    pip install httpx claude-agent-sdk
    python claude_sandbox_worker.py

Environment Variables (required):
    SANDBOX_ID          - Unique sandbox identifier
    CALLBACK_URL        - Main server base URL (e.g., https://api.example.com)
    ANTHROPIC_API_KEY   - API key for Claude (or Z.AI token)

Environment Variables (optional - model/API):
    MODEL               - Model to use (e.g., "glm-4.6v" for Z.AI, default: Claude's default)
    ANTHROPIC_BASE_URL  - Custom API endpoint (e.g., "https://api.z.ai/api/anthropic" for GLM)

Environment Variables (optional - task context):
    TASK_ID             - Task identifier for tracking
    AGENT_ID            - Agent identifier for tracking
    TICKET_ID           - Ticket identifier
    TICKET_TITLE        - Ticket title for context
    TICKET_DESCRIPTION  - Full ticket description
    TASK_DATA_BASE64    - Base64-encoded JSON with full task context (from orchestrator)
                          Contains: task_id, task_description, ticket_id, ticket_title, etc.
                          The task_description is the FULL spec markdown from .omoi_os/ files

Environment Variables (optional - skills & subagents):
    ENABLE_SKILLS       - Set to "true" to enable Claude skills
    ENABLE_SUBAGENTS    - Set to "true" to enable custom subagents
    SETTING_SOURCES     - Comma-separated: "user,project" to load skills

Environment Variables (optional - MCP tools):
    ENABLE_SPEC_TOOLS   - Set to "true" to enable spec workflow MCP tools (default: true)

Environment Variables (optional - skill enforcement):
    REQUIRE_SPEC_SKILL  - Set to "true" to enforce spec-driven-dev skill usage.
                          When enabled:
                          1. Skill content is injected directly into system prompt
                          2. Spec output validation runs before task completion
                          3. Task fails if .omoi_os/ files lack proper frontmatter

Environment Variables (optional - behavior):
    SYSTEM_PROMPT       - Custom system prompt (replaces default, but append still works)
    SYSTEM_PROMPT_APPEND - Additional text to append to system prompt (extends default)
    INITIAL_PROMPT      - Initial task prompt
    POLL_INTERVAL       - Message poll interval in seconds (default: 0.5)
    HEARTBEAT_INTERVAL  - Heartbeat interval in seconds (default: 30)
    MAX_TURNS           - Max turns per response (default: 50)
    MAX_BUDGET_USD      - Max budget in USD (default: 10.0)
    PERMISSION_MODE     - SDK permission mode (default: acceptEdits)
    ALLOWED_TOOLS       - Comma-separated tool list
    CWD                 - Working directory (default: /workspace)

Environment Variables (optional - GitHub):
    GITHUB_TOKEN        - GitHub access token for repo operations
    GITHUB_REPO         - Repository in owner/repo format
    BRANCH_NAME         - Branch to checkout

Environment Variables (optional - session resumption):
    RESUME_SESSION_ID   - Session ID to resume a previous conversation
    FORK_SESSION        - Set to "true" to fork from session (creates new branch)
    SESSION_TRANSCRIPT_B64 - Base64-encoded session transcript for cross-sandbox resumption
    CONVERSATION_CONTEXT - Text context/summary for conversation hydration (alternative)

Example with GLM:
    SANDBOX_ID=my-sandbox \\
    CALLBACK_URL=http://localhost:8000 \\
    ANTHROPIC_API_KEY=your_z_ai_token \\
    ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic \\
    MODEL=glm-4.6v \\
    python claude_sandbox_worker.py
"""

import asyncio
import base64
import difflib
import logging
import os
from re import Match, Pattern
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import httpx

# Configure logging for standalone sandbox operation
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("claude_sandbox_worker")

# Try to import pydantic v2 for agent model serialization
# Define dataclass for agent definitions at module level (required for SDK's asdict())
from dataclasses import dataclass


@dataclass
class AgentDefinition:
    """Agent definition dataclass for SDK compatibility."""

    description: str
    prompt: str
    tools: list[str]
    model: Optional[str] = None


# Try to import Claude Agent SDK
try:
    from claude_agent_sdk import (
        # Message types
        AssistantMessage,
        UserMessage,
        SystemMessage,
        ResultMessage,
        # Content blocks
        TextBlock,
        ThinkingBlock,
        ToolUseBlock,
        ToolResultBlock,
        # Client and options
        ClaudeAgentOptions,
        ClaudeSDKClient,
        HookMatcher,
        HookInput,
        HookContext,
        HookJSONOutput,
        # MCP tools
        tool,
        create_sdk_mcp_server,
    )

    SDK_AVAILABLE = True
    MCP_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    MCP_AVAILABLE = False


# =============================================================================
# Iteration State Tracking (Continuous Mode)
# =============================================================================


@dataclass
class IterationState:
    """Tracks state across iterations for continuous execution mode.

    When enabled, the worker runs in a loop until:
    - Validation passes (code pushed, PR created)
    - Limits are reached (max_runs, max_cost, max_duration)
    - 3 consecutive errors occur
    """

    iteration_num: int = 0  # Current iteration
    successful_iterations: int = 0  # Completed successfully
    error_count: int = 0  # Consecutive errors
    total_cost: float = 0.0  # Accumulated cost
    completion_signal_count: int = 0  # Consecutive completion signals
    start_time: Optional[float] = None  # For duration tracking
    last_session_id: Optional[str] = None  # For potential resume
    validation_passed: bool = False  # Whether git validation passed
    validation_feedback: str = ""  # Feedback from validation

    # Track what's been accomplished
    tests_passed: bool = False
    code_committed: bool = False
    code_pushed: bool = False
    pr_created: bool = False

    # Additional PR/CI info for artifact generation
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    files_changed: int = 0
    ci_status: Optional[list] = None

    def to_event_data(self) -> dict:
        """Convert state to event payload."""
        import time

        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            "iteration_num": self.iteration_num,
            "successful_iterations": self.successful_iterations,
            "error_count": self.error_count,
            "total_cost_usd": self.total_cost,
            "completion_signal_count": self.completion_signal_count,
            "elapsed_seconds": elapsed,
            "last_session_id": self.last_session_id,
            "validation_passed": self.validation_passed,
            "tests_passed": self.tests_passed,
            "code_committed": self.code_committed,
            "code_pushed": self.code_pushed,
            "pr_created": self.pr_created,
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "files_changed": self.files_changed,
            "ci_status": self.ci_status,
        }


# =============================================================================
# Git Validation (for continuous mode completion checking)
# =============================================================================


def check_git_status(cwd: str) -> dict[str, Any]:
    """Check git status for validation.

    Returns dict with:
    - is_clean: No uncommitted changes
    - is_pushed: Not ahead of remote
    - has_pr: PR exists for current branch
    - branch_name: Current branch
    - errors: List of validation errors
    - ci_status: CI check results (if PR exists)
    - tests_passed: Whether all CI checks passed
    - pr_url: URL of the PR (if exists)
    - pr_number: PR number (if exists)
    - files_changed: Number of files changed in PR
    """
    result = {
        "is_clean": False,
        "is_pushed": False,
        "has_pr": False,
        "branch_name": None,
        "status_output": "",
        "errors": [],
        "ci_status": None,
        "tests_passed": False,
        "pr_url": None,
        "pr_number": None,
        "files_changed": 0,
    }

    try:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if branch_result.returncode == 0:
            result["branch_name"] = branch_result.stdout.strip()

        # Check git status
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        result["status_output"] = status_result.stdout
        result["is_clean"] = (
            status_result.returncode == 0 and not status_result.stdout.strip()
        )

        if not result["is_clean"]:
            result["errors"].append("Uncommitted changes detected")

        # Check if ahead of remote
        status_verbose = subprocess.run(
            ["git", "status"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        status_text = status_verbose.stdout

        if "Your branch is ahead" in status_text:
            result["is_pushed"] = False
            result["errors"].append("Code not pushed to remote")
        elif (
            "Your branch is up to date" in status_text
            or "nothing to commit" in status_text
        ):
            result["is_pushed"] = True
        else:
            # If we can't determine, assume it's pushed
            result["is_pushed"] = True

        # Check for PR using gh CLI
        try:
            pr_result = subprocess.run(
                ["gh", "pr", "view", "--json", "number,title,state,url,changedFiles"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if pr_result.returncode == 0 and pr_result.stdout.strip():
                result["has_pr"] = True
                # Parse PR info
                try:
                    import json

                    pr_data = json.loads(pr_result.stdout)
                    result["pr_number"] = pr_data.get("number")
                    result["pr_url"] = pr_data.get("url")
                    result["files_changed"] = pr_data.get("changedFiles", 0)
                except json.JSONDecodeError:
                    pass

                # Check CI status if PR exists
                ci_result = subprocess.run(
                    ["gh", "pr", "checks", "--json", "name,state,conclusion"],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if ci_result.returncode == 0 and ci_result.stdout.strip():
                    try:
                        ci_checks = json.loads(ci_result.stdout)
                        result["ci_status"] = ci_checks

                        # Determine if all checks passed
                        if ci_checks:
                            all_passed = all(
                                check.get("conclusion") == "success"
                                or check.get("state") == "pending"  # Allow pending
                                for check in ci_checks
                            )
                            # But require at least one completed success
                            has_success = any(
                                check.get("conclusion") == "success"
                                for check in ci_checks
                            )
                            result["tests_passed"] = all_passed and has_success
                        else:
                            # No CI checks configured - assume tests pass
                            result["tests_passed"] = True
                    except json.JSONDecodeError:
                        result["tests_passed"] = True
                else:
                    # No CI checks configured
                    result["tests_passed"] = True
            else:
                result["has_pr"] = False
                result["errors"].append("No PR found for current branch")
        except FileNotFoundError:
            result["errors"].append("GitHub CLI (gh) not available")
        except subprocess.TimeoutExpired:
            result["errors"].append("Timeout checking PR status")

    except subprocess.TimeoutExpired:
        result["errors"].append("Timeout running git commands")
    except Exception as e:
        result["errors"].append(f"Git validation error: {str(e)}")

    return result


# =============================================================================
# Spec Output Validation (for exploration mode completion checking)
# =============================================================================


def check_spec_output(cwd: str) -> dict[str, Any]:
    """Check spec output for exploration mode validation.

    Validates that:
    1. .omoi_os/ directory exists
    2. At least one spec file was created (tickets or tasks)
    3. Files have valid YAML frontmatter with required fields

    Returns dict with:
    - has_omoi_dir: .omoi_os directory exists
    - files_found: List of spec files found
    - files_with_frontmatter: Files that have valid frontmatter
    - files_missing_frontmatter: Files missing or with invalid frontmatter
    - errors: List of validation errors
    - is_valid: Overall validation passed
    """
    import re

    result = {
        "has_omoi_dir": False,
        "files_found": [],
        "files_with_frontmatter": [],
        "files_missing_frontmatter": [],
        "errors": [],
        "is_valid": False,
    }

    omoi_dir = Path(cwd) / ".omoi_os"

    # Check if .omoi_os directory exists
    if not omoi_dir.exists():
        result["errors"].append(".omoi_os/ directory does not exist - no specs created")
        return result

    result["has_omoi_dir"] = True

    # Define spec directories and required frontmatter fields
    # Note: tasks use "parent_ticket" (not "ticket_id") per SKILL.md template
    spec_dirs: dict[str, list[str]] = {
        "docs": ["id", "title", "status"],
        "requirements": ["id", "title", "status", "category"],
        "designs": ["id", "title", "status"],
        "tickets": ["id", "title", "status", "priority"],
        "tasks": ["id", "title", "status", "parent_ticket"],
    }

    # YAML frontmatter pattern
    frontmatter_pattern: Pattern[str] = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

    for dir_name, required_fields in spec_dirs.items():
        dir_path = omoi_dir / dir_name
        if not dir_path.exists():
            continue

        for file_path in dir_path.glob("*.md"):
            result["files_found"].append(str(file_path.relative_to(cwd)))

            try:
                content = file_path.read_text()

                # Check for frontmatter
                match: Match[str] | None = frontmatter_pattern.match(content)
                if not match:
                    result["files_missing_frontmatter"].append(
                        str(file_path.relative_to(cwd))
                    )
                    result["errors"].append(
                        f"{file_path.name}: Missing YAML frontmatter"
                    )
                    continue

                # Parse frontmatter (basic check - look for required fields)
                frontmatter_text = match.group(1)
                missing_fields = []
                for field in required_fields:
                    # Simple check - field should appear at start of line
                    if not re.search(rf"^{field}:", frontmatter_text, re.MULTILINE):
                        missing_fields.append(field)

                if missing_fields:
                    result["files_missing_frontmatter"].append(
                        str(file_path.relative_to(cwd))
                    )
                    result["errors"].append(
                        f"{file_path.name}: Missing required fields: {', '.join(missing_fields)}"
                    )
                else:
                    result["files_with_frontmatter"].append(
                        str(file_path.relative_to(cwd))
                    )

            except Exception as e:
                result["errors"].append(
                    f"{file_path.name}: Error reading file: {str(e)}"
                )

    # Determine if valid
    # Valid if: has directory, has at least one file, all files have proper frontmatter
    if not result["files_found"]:
        result["errors"].append(
            "No spec files found in .omoi_os/ - create tickets and tasks"
        )
    elif result["files_missing_frontmatter"]:
        # Some files are invalid
        pass
    else:
        result["is_valid"] = True

    return result


def get_spec_skill_content() -> str:
    """Get the critical sections of the spec-driven-dev skill for prompt injection.

    Returns the frontmatter templates and CLI workflow sections that MUST be
    included directly in the system prompt to ensure compliance.
    """
    # This is extracted from the first ~250 lines of SKILL.md
    # Contains: critical warnings, frontmatter templates, CLI workflow
    return """## 🚨 SPEC-DRIVEN-DEV SKILL (MANDATORY - READ CAREFULLY)

This skill content is REQUIRED. You MUST follow these formats exactly.

### YAML Frontmatter Templates (COPY EXACTLY)

**EVERY file in `.omoi_os/` MUST begin with YAML frontmatter.** No exceptions.

**PRDs** (`.omoi_os/docs/prd-*.md`):
```yaml
---
id: PRD-{FEATURE}-001
title: {Feature Name} PRD
feature: {feature-name}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: draft
author: Claude
---
```

**Requirements** (`.omoi_os/requirements/*.md`):
```yaml
---
id: REQ-{FEATURE}-001
title: {Feature Name} Requirements
feature: {feature-name}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: draft
category: functional
priority: HIGH
prd_ref: docs/prd-{feature-name}.md
design_ref: designs/{feature-name}.md
---
```

**Designs** (`.omoi_os/designs/*.md`):
```yaml
---
id: DESIGN-{FEATURE}-001
title: {Feature Name} Design
feature: {feature-name}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: draft
requirements:
  - REQ-{FEATURE}-001
---
```

**Tickets** (`.omoi_os/tickets/TKT-*.md`):
```yaml
---
id: TKT-{NNN}
title: {Ticket Title}
status: backlog
priority: HIGH
estimate: M
design_ref: designs/{feature-name}.md
requirements:
  - REQ-{FEATURE}-FUNC-001
dependencies:
  blocked_by: []
  blocks: []
---
```

**Tasks** (`.omoi_os/tasks/TSK-*.md`):
```yaml
---
id: TSK-{NNN}
title: {Task Title}
status: pending
ticket_id: TKT-{NNN}
estimate: S
type: implementation
dependencies:
  depends_on: []
  blocks: []
---
```

### Required Workflow: Create → Validate → Sync

**EVERY time you create files in `.omoi_os/`, you MUST run:**

```bash
# Navigate to spec CLI
cd /root/.claude/skills/spec-driven-dev/scripts

# Validate (check for errors)
python spec_cli.py validate

# Sync specs (PRDs, requirements, designs)
python spec_cli.py sync-specs push

# Sync tickets and tasks
python spec_cli.py sync push
```

### Directory Structure

Create these directories and files:
- `.omoi_os/docs/prd-{feature}.md` - Product Requirements Document
- `.omoi_os/requirements/{feature}.md` - Functional requirements
- `.omoi_os/designs/{feature}.md` - Technical design
- `.omoi_os/tickets/TKT-001.md` - Work tickets
- `.omoi_os/tasks/TSK-001.md` - Individual tasks

### ❌ Files Without Frontmatter WILL FAIL Validation

The validation hook checks ALL files. If ANY file is missing frontmatter
or has incorrect fields, the task will NOT complete successfully.

### Validation Checks (Automatic)

Before task completion, the system validates:
1. `.omoi_os/` directory exists
2. At least one ticket or task file exists
3. ALL files have valid YAML frontmatter
4. ALL required fields are present

**If validation fails, you must fix the issues and try again.**
"""


# =============================================================================
# File Change Tracking
# =============================================================================


class FileChangeTracker:
    """Tracks file changes for diff generation."""

    def __init__(self):
        self.file_cache: dict[str, str] = {}  # path → content before edit

    def cache_file_before_edit(self, path: str, content: str):
        """Cache file content before Write/Edit tool executes."""
        self.file_cache[path] = content

    def generate_diff(self, path: str, new_content: str) -> dict:
        """Generate unified diff after edit completes."""
        old_content = self.file_cache.pop(path, "")

        # Handle new file vs modified file
        if not old_content:
            # New file - split without keepends for clean output
            new_lines = new_content.splitlines()
            lines_added = len(new_lines)
            lines_removed = 0
            diff = ["--- /dev/null", f"+++ b/{path}"]
            for line in new_lines:
                diff.append(f"+{line}")
            change_type = "created"
        else:
            # Modified file - split without keepends for clean diff
            old_lines = old_content.splitlines()
            new_lines = new_content.splitlines()
            diff = list(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm="",  # Don't add line terminators, we join with \n later
                )
            )
            lines_added = sum(
                1
                for line in diff
                if line.startswith("+") and not line.startswith("+++")
            )
            lines_removed = sum(
                1
                for line in diff
                if line.startswith("-") and not line.startswith("---")
            )
            change_type = "modified"

        # Join with newlines - each line is now clean (no embedded newlines)
        diff_text = "\n".join(diff)
        diff_preview = "\n".join(diff[:100])
        if len(diff) > 100:
            diff_preview += f"\n... ({len(diff) - 100} more lines)"

        return {
            "file_path": path,
            "change_type": change_type,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "diff_preview": diff_preview[:5000],
            "full_diff": diff_text if len(diff_text) <= 50000 else None,
            "full_diff_available": len(diff_text) > 5000,
            "full_diff_size": len(diff_text),
        }


# =============================================================================
# Spec Workflow MCP Tools (Embedded for Standalone Operation)
# =============================================================================

# API timeout for spec workflow tools
SPEC_API_TIMEOUT = 30.0


def _format_mcp_response(text: str) -> dict[str, Any]:
    """Format a text response in MCP tool format."""
    return {"content": [{"type": "text", "text": text}]}


def _format_mcp_error(error: str) -> dict[str, Any]:
    """Format an error response in MCP tool format."""
    return {"content": [{"type": "text", "text": f"Error: {error}"}]}


def _get_api_base() -> str:
    """Get API base URL from environment (CALLBACK_URL is already set by spawner)."""
    return os.environ.get("CALLBACK_URL", "http://localhost:18000")


# Only define tools if SDK is available
if SDK_AVAILABLE:

    @tool(
        "create_spec",
        "Create a new specification for a project. Specs are containers for requirements, design, and tasks.",
        {
            "project_id": "Project ID to create spec under (required)",
            "title": "Title of the specification (required)",
            "description": "Detailed description of what this spec covers (optional)",
        },
    )
    async def create_spec(args: dict[str, Any]) -> dict[str, Any]:
        """Create a new spec via API."""
        try:
            api_base = _get_api_base()
            async with httpx.AsyncClient(timeout=SPEC_API_TIMEOUT) as client:
                response = await client.post(
                    f"{api_base}/api/v1/specs",
                    json={
                        "project_id": args["project_id"],
                        "title": args["title"],
                        "description": args.get("description"),
                    },
                )
                response.raise_for_status()
                spec = response.json()
                return _format_mcp_response(
                    f"Created spec '{spec['title']}'\n"
                    f"ID: {spec['id']}\n"
                    f"Status: {spec['status']}\n"
                    f"Phase: {spec['phase']}"
                )
        except httpx.HTTPStatusError as e:
            return _format_mcp_error(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return _format_mcp_error(str(e))

    @tool(
        "get_spec",
        "Get full details of a specification including requirements, design, and tasks.",
        {"spec_id": "Spec ID to retrieve (required)"},
    )
    async def get_spec(args: dict[str, Any]) -> dict[str, Any]:
        """Get spec details via API."""
        try:
            api_base = _get_api_base()
            async with httpx.AsyncClient(timeout=SPEC_API_TIMEOUT) as client:
                response = await client.get(
                    f"{api_base}/api/v1/specs/{args['spec_id']}"
                )
                response.raise_for_status()
                spec = response.json()

                output = f"Spec: {spec['title']}\n"
                output += f"ID: {spec['id']}\n"
                output += f"Status: {spec['status']} | Phase: {spec['phase']}\n"
                output += f"Progress: {spec['progress']}%\n\n"

                output += f"Requirements ({len(spec['requirements'])}):\n"
                for req in spec["requirements"]:
                    output += f"  [{req['status']}] {req['title']}\n"
                    output += f"    WHEN {req['condition']}\n"
                    output += f"    THE SYSTEM SHALL {req['action']}\n"
                    for c in req.get("criteria", []):
                        status = "x" if c["completed"] else " "
                        output += f"    [{status}] {c['text']}\n"

                output += f"\nTasks ({len(spec['tasks'])}):\n"
                for task in spec["tasks"]:
                    output += (
                        f"  [{task['status']}] {task['title']} ({task['priority']})\n"
                    )

                return _format_mcp_response(output)
        except httpx.HTTPStatusError as e:
            return _format_mcp_error(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return _format_mcp_error(str(e))

    @tool(
        "list_project_specs",
        "List all specifications for a project.",
        {
            "project_id": "Project ID (required)",
            "status": "Filter by status: draft, requirements, design, executing, completed (optional)",
        },
    )
    async def list_project_specs(args: dict[str, Any]) -> dict[str, Any]:
        """List specs for a project."""
        try:
            api_base = _get_api_base()
            async with httpx.AsyncClient(timeout=SPEC_API_TIMEOUT) as client:
                url = f"{api_base}/api/v1/specs/project/{args['project_id']}"
                params = {}
                if args.get("status"):
                    params["status"] = args["status"]
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                output = f"Specs ({data['total']}):\n"
                for spec in data["specs"]:
                    output += f"  - {spec['title']} (ID: {spec['id']})\n"
                    output += f"    Status: {spec['status']} | Phase: {spec['phase']}\n"

                return _format_mcp_response(output)
        except httpx.HTTPStatusError as e:
            return _format_mcp_error(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return _format_mcp_error(str(e))

    @tool(
        "add_requirement",
        "Add an EARS-style requirement to a spec. Uses 'WHEN condition, THE SYSTEM SHALL action' format.",
        {
            "spec_id": "Spec ID to add requirement to (required)",
            "title": "Brief title for the requirement (required)",
            "condition": "EARS 'WHEN' clause - the trigger condition (required)",
            "action": "EARS 'THE SYSTEM SHALL' clause - what the system does (required)",
        },
    )
    async def add_requirement(args: dict[str, Any]) -> dict[str, Any]:
        """Add a requirement to a spec."""
        try:
            api_base = _get_api_base()
            async with httpx.AsyncClient(timeout=SPEC_API_TIMEOUT) as client:
                response = await client.post(
                    f"{api_base}/api/v1/specs/{args['spec_id']}/requirements",
                    json={
                        "title": args["title"],
                        "condition": args["condition"],
                        "action": args["action"],
                    },
                )
                response.raise_for_status()
                req = response.json()
                return _format_mcp_response(
                    f"Added requirement '{req['title']}'\n"
                    f"ID: {req['id']}\n"
                    f"WHEN {req['condition']}\n"
                    f"THE SYSTEM SHALL {req['action']}"
                )
        except httpx.HTTPStatusError as e:
            return _format_mcp_error(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return _format_mcp_error(str(e))

    @tool(
        "add_acceptance_criterion",
        "Add an acceptance criterion to a requirement. These define how to verify the requirement is met.",
        {
            "spec_id": "Spec ID (required)",
            "requirement_id": "Requirement ID to add criterion to (required)",
            "text": "The acceptance criterion text (required)",
        },
    )
    async def add_acceptance_criterion(args: dict[str, Any]) -> dict[str, Any]:
        """Add an acceptance criterion to a requirement."""
        try:
            api_base = _get_api_base()
            async with httpx.AsyncClient(timeout=SPEC_API_TIMEOUT) as client:
                response = await client.post(
                    f"{api_base}/api/v1/specs/{args['spec_id']}/requirements/{args['requirement_id']}/criteria",
                    json={"text": args["text"]},
                )
                response.raise_for_status()
                criterion = response.json()
                return _format_mcp_response(
                    f"Added acceptance criterion\n"
                    f"ID: {criterion['id']}\n"
                    f"Text: {criterion['text']}"
                )
        except httpx.HTTPStatusError as e:
            return _format_mcp_error(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return _format_mcp_error(str(e))

    @tool(
        "update_design",
        "Update the design artifacts for a spec including architecture, data model, and API spec.",
        {
            "spec_id": "Spec ID (required)",
            "architecture": "Architecture description/diagram in markdown (optional)",
            "data_model": "Data model description/diagram in markdown (optional)",
            "api_spec": "List of API endpoints: [{method, endpoint, description}] (optional)",
        },
    )
    async def update_design(args: dict[str, Any]) -> dict[str, Any]:
        """Update design for a spec."""
        try:
            api_base = _get_api_base()
            async with httpx.AsyncClient(timeout=SPEC_API_TIMEOUT) as client:
                design = {
                    "architecture": args.get("architecture"),
                    "data_model": args.get("data_model"),
                    "api_spec": args.get("api_spec", []),
                }
                response = await client.put(
                    f"{api_base}/api/v1/specs/{args['spec_id']}/design",
                    json=design,
                )
                response.raise_for_status()
                return _format_mcp_response(
                    f"Updated design for spec {args['spec_id']}"
                )
        except httpx.HTTPStatusError as e:
            return _format_mcp_error(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return _format_mcp_error(str(e))

    @tool(
        "add_spec_task",
        "Add a task to a specification. Tasks are discrete units of work derived from requirements.",
        {
            "spec_id": "Spec ID (required)",
            "title": "Task title (required)",
            "description": "Task description (optional)",
            "phase": "Development phase: Implementation, Testing, Integration, etc. (default: Implementation)",
            "priority": "Priority: low, medium, high, critical (default: medium)",
        },
    )
    async def add_spec_task(args: dict[str, Any]) -> dict[str, Any]:
        """Add a task to a spec."""
        try:
            api_base = _get_api_base()
            async with httpx.AsyncClient(timeout=SPEC_API_TIMEOUT) as client:
                response = await client.post(
                    f"{api_base}/api/v1/specs/{args['spec_id']}/tasks",
                    json={
                        "title": args["title"],
                        "description": args.get("description"),
                        "phase": args.get("phase", "Implementation"),
                        "priority": args.get("priority", "medium"),
                    },
                )
                response.raise_for_status()
                task = response.json()
                return _format_mcp_response(
                    f"Added task '{task['title']}'\n"
                    f"ID: {task['id']}\n"
                    f"Phase: {task['phase']}\n"
                    f"Priority: {task['priority']}"
                )
        except httpx.HTTPStatusError as e:
            return _format_mcp_error(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return _format_mcp_error(str(e))

    @tool(
        "create_ticket",
        "Create a ticket for the workflow system. Tickets represent work items that agents execute.",
        {
            "title": "Ticket title (required)",
            "description": "Ticket description (optional)",
            "priority": "Priority: LOW, MEDIUM, HIGH, CRITICAL (default: MEDIUM)",
            "phase_id": "Initial phase: PHASE_REQUIREMENTS, PHASE_INITIAL, PHASE_IMPLEMENTATION (default: PHASE_REQUIREMENTS)",
            "project_id": "Project ID (optional)",
        },
    )
    async def create_ticket(args: dict[str, Any]) -> dict[str, Any]:
        """Create a ticket via API."""
        try:
            api_base = _get_api_base()
            async with httpx.AsyncClient(timeout=SPEC_API_TIMEOUT) as client:
                response = await client.post(
                    f"{api_base}/api/v1/tickets",
                    json={
                        "title": args["title"],
                        "description": args.get("description"),
                        "priority": args.get("priority", "MEDIUM"),
                        "phase_id": args.get("phase_id", "PHASE_REQUIREMENTS"),
                        "project_id": args.get("project_id"),
                    },
                )
                response.raise_for_status()
                ticket = response.json()
                return _format_mcp_response(
                    f"Created ticket '{ticket['title']}'\n"
                    f"ID: {ticket['id']}\n"
                    f"Priority: {ticket['priority']}\n"
                    f"Phase: {ticket['phase_id']}"
                )
        except httpx.HTTPStatusError as e:
            return _format_mcp_error(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return _format_mcp_error(str(e))

    @tool(
        "get_ticket",
        "Get details of a ticket including its current status and tasks.",
        {"ticket_id": "Ticket ID (required)"},
    )
    async def get_ticket(args: dict[str, Any]) -> dict[str, Any]:
        """Get ticket details."""
        try:
            api_base = _get_api_base()
            async with httpx.AsyncClient(timeout=SPEC_API_TIMEOUT) as client:
                response = await client.get(
                    f"{api_base}/api/v1/tickets/{args['ticket_id']}"
                )
                response.raise_for_status()
                ticket = response.json()

                output = f"Ticket: {ticket['title']}\n"
                output += f"ID: {ticket['id']}\n"
                output += f"Status: {ticket['status']}\n"
                output += f"Priority: {ticket['priority']}\n"
                output += f"Phase: {ticket['phase_id']}\n"
                if ticket.get("description"):
                    output += f"\nDescription:\n{ticket['description']}\n"

                return _format_mcp_response(output)
        except httpx.HTTPStatusError as e:
            return _format_mcp_error(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return _format_mcp_error(str(e))

    @tool(
        "approve_requirements",
        "Approve all requirements for a spec and transition to the Design phase.",
        {"spec_id": "Spec ID to approve requirements for (required)"},
    )
    async def approve_requirements(args: dict[str, Any]) -> dict[str, Any]:
        """Approve requirements for a spec."""
        try:
            api_base = _get_api_base()
            async with httpx.AsyncClient(timeout=SPEC_API_TIMEOUT) as client:
                response = await client.post(
                    f"{api_base}/api/v1/specs/{args['spec_id']}/approve-requirements"
                )
                response.raise_for_status()
                return _format_mcp_response(
                    f"Requirements approved for spec {args['spec_id']}.\n"
                    f"Spec is now in the Design phase."
                )
        except httpx.HTTPStatusError as e:
            return _format_mcp_error(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return _format_mcp_error(str(e))

    @tool(
        "approve_design",
        "Approve the design for a spec and transition to the Implementation phase.",
        {"spec_id": "Spec ID to approve design for (required)"},
    )
    async def approve_design(args: dict[str, Any]) -> dict[str, Any]:
        """Approve design for a spec."""
        try:
            api_base = _get_api_base()
            async with httpx.AsyncClient(timeout=SPEC_API_TIMEOUT) as client:
                response = await client.post(
                    f"{api_base}/api/v1/specs/{args['spec_id']}/approve-design"
                )
                response.raise_for_status()
                return _format_mcp_response(
                    f"Design approved for spec {args['spec_id']}.\n"
                    f"Spec is now in the Implementation phase."
                )
        except httpx.HTTPStatusError as e:
            return _format_mcp_error(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return _format_mcp_error(str(e))

    # All available spec workflow tools
    SPEC_WORKFLOW_TOOLS = [
        create_spec,
        get_spec,
        list_project_specs,
        add_requirement,
        add_acceptance_criterion,
        update_design,
        add_spec_task,
        create_ticket,
        get_ticket,
        approve_requirements,
        approve_design,
    ]

    def create_spec_workflow_mcp_server():
        """Create the MCP server with all spec workflow tools.

        Returns an MCP server that can be passed to ClaudeAgentOptions.mcp_servers.
        """
        return create_sdk_mcp_server(name="spec_workflow", tools=SPEC_WORKFLOW_TOOLS)

    def get_spec_workflow_tool_names() -> list[str]:
        """Get list of all spec workflow tool names in MCP format.

        These can be used in ClaudeAgentOptions.allowed_tools.

        Returns:
            List of tool names in format 'mcp__spec_workflow__<tool_name>'
        """
        return [f"mcp__spec_workflow__{t._tool_name}" for t in SPEC_WORKFLOW_TOOLS]

else:
    # SDK not available - define stubs
    SPEC_WORKFLOW_TOOLS = []

    def create_spec_workflow_mcp_server():
        raise ImportError("claude_agent_sdk is required to create MCP servers")

    def get_spec_workflow_tool_names() -> list[str]:
        return []


# =============================================================================
# Configuration
# =============================================================================


class WorkerConfig:
    """Worker configuration from environment variables."""

    def __init__(self):
        # Core identifiers
        self.sandbox_id = os.environ.get("SANDBOX_ID", f"sandbox-{uuid4().hex[:8]}")
        self.task_id = os.environ.get("TASK_ID", "")
        self.agent_id = os.environ.get("AGENT_ID", "")
        self.ticket_id = os.environ.get("TICKET_ID", "")
        self.ticket_title = os.environ.get("TICKET_TITLE", "")
        self.ticket_description = os.environ.get("TICKET_DESCRIPTION", "")

        # Phase 6: Decode TASK_DATA_BASE64 if present (from orchestrator)
        # This contains full task context including the complete task description
        self.task_data: dict = {}
        self.task_description = ""  # Full task description from spec files
        task_data_b64 = os.environ.get("TASK_DATA_BASE64")
        if task_data_b64:
            try:
                import base64
                import json

                task_json = base64.b64decode(task_data_b64).decode()
                self.task_data = json.loads(task_json)
                # Extract task description (this is the FULL spec markdown)
                self.task_description = self.task_data.get("task_description", "")
                # Also populate ticket fields from task_data if not already set
                if not self.ticket_id and self.task_data.get("ticket_id"):
                    self.ticket_id = self.task_data["ticket_id"]
                if not self.ticket_title and self.task_data.get("ticket_title"):
                    self.ticket_title = self.task_data["ticket_title"]
                if not self.ticket_description and self.task_data.get(
                    "ticket_description"
                ):
                    self.ticket_description = self.task_data["ticket_description"]
                if not self.task_id and self.task_data.get("task_id"):
                    self.task_id = self.task_data["task_id"]
                logger.info(
                    f"Loaded task data from TASK_DATA_BASE64: task_description={len(self.task_description)} chars"
                )
            except Exception as e:
                logger.warning(f"Failed to decode TASK_DATA_BASE64: {e}")

        # Server connection
        self.callback_url = os.environ.get("CALLBACK_URL", "http://localhost:8000")
        self.api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
            "ANTHROPIC_AUTH_TOKEN", ""
        )

        # Model settings (for GLM or other models)
        self.model = os.environ.get("MODEL") or os.environ.get("ANTHROPIC_MODEL")
        self.api_base_url = os.environ.get("ANTHROPIC_BASE_URL")

        # Task and prompts
        # INITIAL_PROMPT can be overridden, but we prefer task_description from TASK_DATA_BASE64
        self.initial_prompt = os.environ.get("INITIAL_PROMPT", "")
        self.poll_interval = float(os.environ.get("POLL_INTERVAL", "0.5"))
        self.heartbeat_interval = int(os.environ.get("HEARTBEAT_INTERVAL", "30"))

        # SDK settings
        self.max_turns = int(os.environ.get("MAX_TURNS", "50"))
        self.max_budget_usd = float(os.environ.get("MAX_BUDGET_USD", "10.0"))
        self.permission_mode = os.environ.get("PERMISSION_MODE", "bypassPermissions")
        self.cwd = os.environ.get("CWD", "/workspace")

        # System prompt - use append pattern to extend rather than replace
        # Build append text from enabled features
        append_parts = []

        # Tools configuration - SDK defaults + optional control
        #
        # The SDK provides a comprehensive default toolset including:
        #   Read, Write, Bash, Edit, Glob, Grep, Task, Skill, WebFetch, WebSearch, etc.
        #
        # Environment variables:
        #   ALLOWED_TOOLS: Comma-separated list to REPLACE defaults (use with caution!)
        #   DISALLOWED_TOOLS: Comma-separated list to BLOCK specific tools from defaults
        #
        # Recommended approach:
        #   - Don't set ALLOWED_TOOLS (let SDK use full defaults)
        #   - Use DISALLOWED_TOOLS only if you need to block dangerous tools
        #   - MCP tools are auto-registered when mcp_servers are configured
        #
        allowed_tools_env = os.environ.get("ALLOWED_TOOLS")
        if allowed_tools_env:
            # User explicitly wants to replace defaults - use their exact list
            # WARNING: This loses SDK defaults like Skill, Task, WebSearch, etc.
            self.allowed_tools = [
                t.strip() for t in allowed_tools_env.split(",") if t.strip()
            ]
            self.tools_mode = "replace"
        else:
            # Use SDK defaults (recommended) - includes all standard tools
            self.allowed_tools = None
            self.tools_mode = "default"

        # Disallowed tools - block specific tools from the default set
        # Example: DISALLOWED_TOOLS=Bash,Write to prevent file modifications
        #
        # Default disallowed tools:
        # - AskUserQuestion: Disabled by default because it disrupts automated
        #   workflows and renders poorly in the event view. The discovery questions
        #   it generates are not compatible with our spec-driven workflow.
        #   Set ENABLE_ASK_USER_QUESTION=true to re-enable if needed.
        DEFAULT_DISALLOWED = ["AskUserQuestion"]

        # Allow re-enabling AskUserQuestion via environment if needed
        if os.environ.get("ENABLE_ASK_USER_QUESTION", "").lower() == "true":
            DEFAULT_DISALLOWED = []

        disallowed_tools_env = os.environ.get("DISALLOWED_TOOLS")
        if disallowed_tools_env:
            # Merge user-specified disallowed tools with defaults
            user_disallowed = [
                t.strip() for t in disallowed_tools_env.split(",") if t.strip()
            ]
            self.disallowed_tools = list(set(DEFAULT_DISALLOWED + user_disallowed))
        else:
            self.disallowed_tools = DEFAULT_DISALLOWED if DEFAULT_DISALLOWED else None

        # Skills and subagents (informational flags - SDK handles these by default)
        self.enable_skills = os.environ.get("ENABLE_SKILLS", "true").lower() == "true"
        self.enable_subagents = (
            os.environ.get("ENABLE_SUBAGENTS", "true").lower() == "true"
        )

        # Execution mode - controls prompts and tool availability
        # - exploration: For feature definition (create specs, tickets, tasks)
        # - implementation: For task execution (write code, run tests)
        # - validation: For verifying implementation
        self.execution_mode = os.environ.get("EXECUTION_MODE", "implementation")

        # Agent type - passed from orchestrator for proper event handling
        # Used to identify validator agents vs implementer agents
        self.agent_type = os.environ.get("AGENT_TYPE", "implementer")

        # MCP spec workflow tools - only enable for exploration mode
        # Implementation agents should NOT be creating new specs/tickets
        self.enable_spec_tools = (
            os.environ.get("ENABLE_SPEC_TOOLS", "").lower() == "true"
            or self.execution_mode == "exploration"
        )

        # Spec-driven-dev skill enforcement
        # When REQUIRE_SPEC_SKILL=true (set from frontend dropdown):
        # 1. Provide clear intent and reference to skill file (not content injection)
        # 2. Run spec output validation before task completion
        # This is NOT automatic for all exploration - only when explicitly requested
        self.require_spec_skill = (
            os.environ.get("REQUIRE_SPEC_SKILL", "").lower() == "true"
        )

        # Add dependency management instructions (applies to all modes)
        append_parts.append("""
## Dependency Management (CRITICAL - Do This First!)

**BEFORE running ANY code**, you MUST install dependencies based on the project type.

---

### Python Projects

**Step 1: Detect the Python dependency manager**
Check which files exist in the project root:
- `pyproject.toml` with `[tool.uv]` section → **UV** (preferred)
- `pyproject.toml` with `[tool.poetry]` section → **Poetry**
- `pyproject.toml` (generic) → **pip with pyproject.toml**
- `requirements.txt` → **pip**
- `setup.py` → **pip**

**Step 2: Install and run based on detected manager**

| Manager | Install | Run Script | Run Module |
|---------|---------|------------|------------|
| **UV** | `uv sync` | `uv run python script.py` | `uv run python -m module` |
| **Poetry** | `poetry install` | `poetry run python script.py` | `poetry run python -m module` |
| **pip** | `pip install -r requirements.txt` | `python script.py` (after venv activation) | `python -m module` |

**For pip projects**, create/activate venv first:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Common Python tool examples** (always prefix with runner!):
```bash
# UV examples
uv run uvicorn main:app --reload          # Run FastAPI/Starlette server
uv run pytest tests/                       # Run tests
uv run alembic upgrade head                # Run database migrations
uv run flask run                           # Run Flask server
uv run celery worker                       # Run Celery worker
uv run python -m http.server 8000          # Simple HTTP server

# Poetry examples
poetry run uvicorn main:app --reload
poetry run pytest tests/
poetry run alembic upgrade head

# pip (after venv activation)
uvicorn main:app --reload
pytest tests/
alembic upgrade head
```

**NEVER run `python script.py` or `uvicorn` directly without installing dependencies!**
If you see "ModuleNotFoundError", you forgot to install dependencies.

---

### Node.js Projects

**Step 1: Detect the Node.js package manager**
Check which lock files exist in the project root:
- `pnpm-lock.yaml` → **pnpm** (fastest, most efficient)
- `yarn.lock` → **Yarn**
- `package-lock.json` → **npm**
- `package.json` only (no lock file) → **npm** (default)

**Step 2: Install and run based on detected manager**

| Manager | Install | Run Script | Run Binary |
|---------|---------|------------|------------|
| **pnpm** | `pnpm install` | `pnpm run <script>` | `pnpm exec <binary>` or `pnpm <binary>` |
| **Yarn** | `yarn install` | `yarn <script>` | `yarn <binary>` |
| **npm** | `npm install` | `npm run <script>` | `npx <binary>` |

**Common scripts** (defined in package.json):
```bash
# Development server
pnpm dev  # or: yarn dev, npm run dev

# Build for production
pnpm build  # or: yarn build, npm run build

# Run tests
pnpm test  # or: yarn test, npm run test

# Linting
pnpm lint  # or: yarn lint, npm run lint
```

**Running binaries from node_modules:**
```bash
# pnpm
pnpm exec tsc --version
pnpm exec eslint .

# yarn
yarn tsc --version
yarn eslint .

# npm
npx tsc --version
npx eslint .
```

**NEVER run `node script.js` with imports without installing dependencies!**
If you see "Cannot find module", you forgot to run install.

---

### Quick Project Detection
```bash
# Detect project type and show correct commands
if [ -f "pnpm-lock.yaml" ]; then
    echo "pnpm project - use: pnpm install && pnpm run <script>"
elif [ -f "yarn.lock" ]; then
    echo "Yarn project - use: yarn install && yarn <script>"
elif [ -f "package-lock.json" ] || [ -f "package.json" ]; then
    echo "npm project - use: npm install && npm run <script>"
elif [ -f "pyproject.toml" ] && grep -q "tool.uv" pyproject.toml 2>/dev/null; then
    echo "UV project - use: uv sync && uv run python ..."
elif [ -f "pyproject.toml" ] && grep -q "tool.poetry" pyproject.toml 2>/dev/null; then
    echo "Poetry project - use: poetry install && poetry run python ..."
elif [ -f "requirements.txt" ]; then
    echo "pip project - use: pip install -r requirements.txt && python ..."
elif [ -f "setup.py" ]; then
    echo "pip project - use: pip install -e . && python ..."
fi
```""")

        # Add execution mode-specific instructions to system prompt
        if self.execution_mode == "exploration":
            if self.require_spec_skill:
                # Use clear intent + skill reference instead of content injection
                # This gives the agent explicit instructions to READ and FOLLOW the skill
                append_parts.append("""
## Execution Mode: EXPLORATION (Spec-Driven Development)

You are in **exploration mode** with **spec-driven-dev skill MANDATORY**.

## ⚠️ YOUR JOB IS NOT COMPLETE UNTIL SPECS ARE SYNCED TO THE API ⚠️

**CRITICAL**: Your task is to CREATE specs (requirements, designs, tickets, tasks) and SYNC them to the OmoiOS API. Confirming the CLI works is just a prerequisite - NOT the goal.

**You MUST complete ALL of these steps:**
1. Load the skill (prerequisite)
2. Ask discovery questions
3. **CREATE** requirements, designs, tickets, and tasks in `.omoi_os/`
4. **VALIDATE** the specs
5. **SYNC** the specs to the API
6. **COMMIT** and push to git

**If you stop after confirming spec_cli.py works, YOU HAVE NOT DONE YOUR JOB.**

---

### Step 1: Load the Skill (Prerequisite Only)

**Option A: If you have Claude Code Agent's skill system:**
```
/spec-driven-dev
```

**Option B: If you don't have the Skill tool:**
```bash
cat /root/.claude/skills/spec-driven-dev/SKILL.md
```

**After loading the skill, PROCEED IMMEDIATELY to discovery questions - do NOT stop here.**

---

### Step 2: Discovery Phase (5-15 Questions)

Ask the user clarifying questions about:
- Problem & value (what pain does this solve?)
- Users & journeys (who uses this? what's the flow?)
- Scope & boundaries (what's in/out of scope?)
- Technical context (integrations, constraints, performance?)
- Trade-offs & risks

---

### Step 3: CREATE THE SPECS (This is the actual work!)

After discovery, you MUST create these files in `.omoi_os/`:

```
.omoi_os/
├── docs/prd-{feature}.md           # Product Requirements Document
├── requirements/{feature}.md        # EARS-format requirements
├── designs/{feature}.md             # Technical design
├── tickets/TKT-001.md, TKT-002.md   # Work tickets
└── tasks/TSK-001.md, TSK-002.md...  # Individual tasks
```

**EVERY file MUST have YAML frontmatter.** Copy the exact templates from the skill file.

---

### Step 4: VALIDATE the Specs

```bash
cd /root/.claude/skills/spec-driven-dev/scripts && python spec_cli.py validate
```

Fix any errors before proceeding.

---

### Step 5: SYNC TO THE API (Critical!)

**Run these commands IN ORDER. Each command must succeed before the next.**

```bash
# First, cd to the scripts directory
cd /root/.claude/skills/spec-driven-dev/scripts

# Push specs (requirements & designs) to create specs in the system
python spec_cli.py sync-specs push

# Push tickets and tasks
python spec_cli.py sync push

# Verify it worked - you should see your specs, tickets, and tasks
python spec_cli.py api-trace
```

**IMPORTANT**: If any sync command fails, READ THE ERROR MESSAGE and fix the issue before proceeding.

**If you skip this step, your work is INVISIBLE to the system and the task WILL FAIL.**

---

### Step 6: Commit and Push to Git

```bash
cd /workspace && git add -A && git commit -m "docs(feature): add spec for {feature-name}" && git push
```

---

## 🔴 AUTOMATIC VALIDATION

**Your output WILL BE AUTOMATICALLY VALIDATED before task completion.**

Validation checks:
1. `.omoi_os/` directory exists with files
2. At least one ticket or task file was created
3. ALL files have valid YAML frontmatter
4. ALL required fields are present

**If validation fails, your task is NOT complete.**

### Required Frontmatter Fields

- **docs**: id, title, status
- **requirements**: id, title, status, category
- **designs**: id, title, status
- **tickets**: id, title, status, priority
- **tasks**: id, title, status, parent_ticket

---

## ❌ COMMON MISTAKES TO AVOID

- ❌ Stopping after confirming spec_cli.py works
- ❌ Creating plain markdown without YAML frontmatter
- ❌ Skipping the sync step (specs stay local-only)
- ❌ Writing implementation code instead of specs
- ❌ Not validating before syncing

---

## ✅ SUCCESS CRITERIA

Your task is ONLY complete when:
1. ✅ Discovery questions were asked and answered
2. ✅ `.omoi_os/` contains requirements, designs, tickets, AND tasks
3. ✅ All files have valid YAML frontmatter
4. ✅ `spec_cli.py validate` passes
5. ✅ `spec_cli.py sync push` successfully synced to API
6. ✅ `spec_cli.py api-trace` shows items in the system
7. ✅ Changes committed and pushed to git

**DO NOT signal completion until ALL criteria are met.**""")
            else:
                # Normal exploration mode - no forced skill, just general guidance
                append_parts.append("""
## Execution Mode: EXPLORATION

You are in **exploration mode**. Your purpose is to explore the codebase, research solutions,
and optionally create documentation or specifications.

### Available Skills

You have access to skills in `/root/.claude/skills/` that can help with various tasks.
Use them as needed based on your objectives.

### If Creating Documentation

If you create any files, ensure you:
1. Use consistent formats with proper markdown
2. Commit and push your work: `git add -A && git commit -m "..." && git push`
3. Create a PR if appropriate: `gh pr create --title "..." --body "..."`

**DO NOT write implementation code in this mode.** Focus on exploration, research, and documentation.""")
        elif self.execution_mode == "validation":
            append_parts.append("""
## Execution Mode: VALIDATION

You are in **validation mode**. Your purpose is to:
1. Review the implementation for correctness
2. Run tests and verify they pass
3. Check code quality and adherence to requirements
4. Verify the implementation matches the task specification
5. Report validation results (pass/fail with feedback)

**DO NOT write new features or make major changes.** Focus on verification.

If you find issues:
- Document specific problems found
- Provide actionable feedback for fixes
- Do NOT fix the issues yourself (implementation agent will handle)""")
        else:  # implementation mode (default)
            append_parts.append("""
## Execution Mode: IMPLEMENTATION

You are in **implementation mode**. Your purpose is to:
1. Execute the assigned task
2. Write code to implement features or fix bugs
3. Run tests to verify your implementation
4. **MANDATORY: Complete the git workflow** (commit, push, create PR)

**DO NOT create new specs, tickets, or tasks.** Focus on executing this specific task.

### Before coding:
1. Read the task specification carefully
2. Check for existing patterns in the codebase
3. Understand the requirements and acceptance criteria

### After coding is complete (MANDATORY):
You MUST complete these steps before considering your work done:

1. **Run tests**: Ensure all tests pass (`pytest`, `npm test`, etc.)
2. **Stage and commit**: `git add -A && git commit -m "feat(scope): description"`
3. **Push to remote**: `git push` (or `git push -u origin <branch>` for first push)
4. **Create a Pull Request**: Use `gh pr create --title "..." --body "..."`

**CRITICAL**: Your work is NOT complete until code is pushed and a PR is created.
The validator will check for:
- Clean git status (no uncommitted changes)
- Code pushed to remote (not ahead of origin)
- PR exists with proper title and description""")

        # Note: MCP tools are automatically available when we register MCP servers
        # No need to explicitly add them to allowed_tools - the SDK handles this
        if self.enable_spec_tools and MCP_AVAILABLE:
            # Add spec tools documentation to system prompt append (exploration mode only)
            append_parts.append("""
## Spec Workflow MCP Tools (mcp__spec_workflow__*)
You have access to spec workflow tools for managing specifications, requirements, and tickets:
- create_spec: Create new specifications for a project
- get_spec: Get spec details including requirements and tasks
- list_project_specs: List all specs for a project
- add_requirement: Add EARS-style requirements (WHEN/THE SYSTEM SHALL)
- add_acceptance_criterion: Add acceptance criteria to requirements
- update_design: Update architecture and design artifacts
- add_spec_task: Add tasks to a specification
- create_ticket: Create tickets for the workflow system
- get_ticket: Get ticket details (use UUID, not title)
- get_task: Get task details including full description and acceptance criteria
- approve_requirements: Approve requirements and move to Design phase
- approve_design: Approve design and move to Implementation phase""")

        # Add mandatory task context instruction for implementation/validation modes
        # Exploration mode creates tasks, it doesn't execute them
        if self.task_id and self.execution_mode in ("implementation", "validation"):
            append_parts.append(f"""
## CRITICAL: Task Context (MUST READ FIRST)

You are assigned to work on task ID: `{self.task_id}`

**BEFORE doing ANY other work, you MUST:**
1. Call `mcp__spec_workflow__get_task` with task_id="{self.task_id}" to get the full task details
2. Read the task's description, acceptance criteria, and implementation notes carefully
3. If the task references a parent ticket, call `mcp__spec_workflow__get_ticket` with the ticket's UUID to get additional context

The task description contains the complete specification including:
- Detailed description of what to implement
- Acceptance criteria (checklist of requirements)
- Implementation notes and constraints
- Dependencies on other tasks

DO NOT start {"coding" if self.execution_mode == "implementation" else "validation"} until you have read and understood the full task specification.""")

        # Check for custom SYSTEM_PROMPT env var or additional append content
        custom_system_prompt = os.environ.get("SYSTEM_PROMPT")
        system_prompt_append = os.environ.get("SYSTEM_PROMPT_APPEND", "")

        if system_prompt_append:
            append_parts.append(system_prompt_append)

        # Build final system_prompt config
        # Use preset with append to extend claude_code's default prompt
        combined_append = "\n".join(append_parts) if append_parts else ""

        if custom_system_prompt:
            # User provided full custom prompt - use it directly with any appends
            if combined_append:
                self.system_prompt = custom_system_prompt + "\n" + combined_append
            else:
                self.system_prompt = custom_system_prompt
        else:
            # Use preset pattern to extend default claude_code prompt
            # This preserves the SDK's default system prompt and appends our additions
            self.system_prompt = (
                {
                    "type": "preset",
                    "preset": "claude_code",
                    "append": combined_append,
                }
                if combined_append
                else None
            )

        # Setting sources for loading skills and settings
        # - user: ~/.claude/settings.json (user-level defaults)
        # - project: .claude/settings.json (project-specific overrides)
        # - local: ~/.claude.json or .claude.json (per-user project state)
        setting_sources_str = os.environ.get("SETTING_SOURCES", "user,project,local")
        self.setting_sources = [
            s.strip() for s in setting_sources_str.split(",") if s.strip()
        ]

        # GitHub config
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        self.github_repo = os.environ.get("GITHUB_REPO", "")
        self.branch_name = os.environ.get("BRANCH_NAME", "")

        # Session resumption - pass a session_id to continue a previous conversation
        self.resume_session_id = os.environ.get("RESUME_SESSION_ID")
        # Fork session - if True, creates a new branch from the resumed session
        # If False (default), continues the exact same session
        self.fork_session = os.environ.get("FORK_SESSION", "false").lower() == "true"

        # Session transcript for cross-sandbox resumption (Base64 encoded JSONL)
        # If provided, this transcript will be written to the local session store
        # before resuming, enabling session portability across sandboxes
        self.session_transcript_b64 = os.environ.get("SESSION_TRANSCRIPT_B64")

        # Conversation context for hydration (alternative to full transcript)
        # Use this to provide a summary of previous conversation
        self.conversation_context = os.environ.get("CONVERSATION_CONTEXT", "")

        # =================================================================
        # Continuous Mode Settings
        # =================================================================
        # When enabled, the worker runs in a loop until task truly completes
        # or limits are reached. This ensures tasks don't stop due to
        # context length issues.

        # Enable continuous mode by default for all execution modes
        # All modes need iteration to ensure work is ACTUALLY completed:
        # - implementation: code pushed, PR created
        # - validation: tests run, results reported
        # - exploration: docs/specs pushed if files created
        continuous_default = self.execution_mode in (
            "implementation",
            "validation",
            "exploration",
        )
        continuous_env = os.environ.get("CONTINUOUS_MODE", "")
        self.continuous_mode = (
            continuous_env.lower() == "true" if continuous_env else continuous_default
        )

        # Log continuous mode configuration for debugging
        logger.info(
            "WORKER: Continuous mode configuration",
            extra={
                "continuous_mode": self.continuous_mode,
                "continuous_env_var": continuous_env or "(not set)",
                "continuous_default": continuous_default,
                "execution_mode": self.execution_mode,
                "task_id": self.task_id,
            },
        )

        # Iteration limits
        self.max_iterations = int(os.environ.get("MAX_ITERATIONS", "10"))
        self.max_total_cost_usd = float(os.environ.get("MAX_TOTAL_COST_USD", "20.0"))
        self.max_duration_seconds = int(
            os.environ.get("MAX_DURATION_SECONDS", "3600")
        )  # 1 hour
        self.max_consecutive_errors = int(os.environ.get("MAX_CONSECUTIVE_ERRORS", "3"))

        # Completion detection
        self.completion_signal = os.environ.get("COMPLETION_SIGNAL", "TASK_COMPLETE")
        self.completion_threshold = int(os.environ.get("COMPLETION_THRESHOLD", "1"))

        # Notes file for cross-iteration context preservation
        self.notes_file = os.environ.get("NOTES_FILE", "ITERATION_NOTES.md")

        # Git validation requirements for implementation mode completion
        self.require_clean_git = (
            os.environ.get("REQUIRE_CLEAN_GIT", "true").lower() == "true"
        )
        self.require_code_pushed = (
            os.environ.get("REQUIRE_CODE_PUSHED", "true").lower() == "true"
        )
        self.require_pr_created = (
            os.environ.get("REQUIRE_PR_CREATED", "true").lower() == "true"
        )

        # Log full continuous mode settings
        if self.continuous_mode:
            logger.info(
                "WORKER: Continuous mode ENABLED with settings",
                extra={
                    "max_iterations": self.max_iterations,
                    "max_total_cost_usd": self.max_total_cost_usd,
                    "max_duration_seconds": self.max_duration_seconds,
                    "max_consecutive_errors": self.max_consecutive_errors,
                    "completion_signal": self.completion_signal,
                    "completion_threshold": self.completion_threshold,
                    "require_clean_git": self.require_clean_git,
                    "require_code_pushed": self.require_code_pushed,
                    "require_pr_created": self.require_pr_created,
                },
            )
        else:
            logger.info(
                "WORKER: Continuous mode DISABLED - running single iteration only",
                extra={
                    "execution_mode": self.execution_mode,
                    "continuous_env_var": continuous_env or "(not set)",
                },
            )

        # Append conversation context to system prompt if provided (for hydration)
        # NOTE: Must be after conversation_context is initialized above
        if self.conversation_context:
            self.system_prompt = f"""{self.system_prompt}

## Previous Conversation Context
You are resuming a previous conversation. Here's what happened before:
{self.conversation_context}

Continue from where we left off, acknowledging the previous context."""

    def validate(self) -> list[str]:
        """Validate configuration, return list of errors."""
        errors = []
        if not self.api_key:
            errors.append("ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN required")
        if not self.callback_url:
            errors.append("CALLBACK_URL required")
        return errors

    def to_dict(self) -> dict:
        """Return config as dict (redacting sensitive values)."""
        return {
            "sandbox_id": self.sandbox_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "callback_url": self.callback_url,
            "api_key": "***" if self.api_key else "NOT SET",
            "model": self.model or "default",
            "api_base_url": self.api_base_url or "default",
            "poll_interval": self.poll_interval,
            "heartbeat_interval": self.heartbeat_interval,
            "max_turns": self.max_turns,
            "max_budget_usd": self.max_budget_usd,
            "permission_mode": self.permission_mode,
            "tools_mode": self.tools_mode,
            "allowed_tools": self.allowed_tools
            if self.allowed_tools
            else "SDK_DEFAULTS",
            "disallowed_tools": self.disallowed_tools or [],
            "enable_skills": self.enable_skills,
            "enable_subagents": self.enable_subagents,
            "enable_spec_tools": self.enable_spec_tools,
            "setting_sources": self.setting_sources,
            "cwd": self.cwd,
            "resume_session_id": self.resume_session_id or "none",
            "fork_session": self.fork_session,
            "has_session_transcript": bool(self.session_transcript_b64),
            "has_conversation_context": bool(self.conversation_context),
            # Continuous mode settings
            "continuous_mode": self.continuous_mode,
            "max_iterations": self.max_iterations,
            "max_total_cost_usd": self.max_total_cost_usd,
            "max_duration_seconds": self.max_duration_seconds,
            "max_consecutive_errors": self.max_consecutive_errors,
            "completion_signal": self.completion_signal,
            "require_clean_git": self.require_clean_git,
            "require_code_pushed": self.require_code_pushed,
            "require_pr_created": self.require_pr_created,
        }

    def get_custom_agents(self) -> dict:
        """Return custom subagent definitions.

        Returns pydantic BaseModel instances if available, otherwise plain dicts.
        This allows the SDK to use model_dump() instead of asdict() for serialization.
        """
        agent_defs = {
            "code-reviewer": {
                "description": "Expert code review specialist. Use for security, quality, and maintainability reviews.",
                "prompt": """You are a code review specialist with expertise in security, performance, and best practices.
When reviewing code:
- Identify security vulnerabilities and injection risks
- Check for performance issues and memory leaks
- Verify adherence to coding standards
- Suggest specific, actionable improvements
Be thorough but concise in your feedback.""",
                "tools": ["Read", "Grep", "Glob"],
                "model": "sonnet",
            },
            "test-runner": {
                "description": "Runs and analyzes test suites. Use for test execution and coverage analysis.",
                "prompt": """You are a test execution specialist. Run tests and provide clear analysis of results.
Focus on:
- Running test commands (pytest, npm test, etc.)
- Analyzing test output and identifying patterns
- Identifying failing tests and their root causes
- Suggesting fixes for test failures""",
                "tools": ["Bash", "Read", "Grep"],
            },
            "architect": {
                "description": "Software architecture specialist. Use for design decisions and codebase structure.",
                "prompt": """You are a software architecture specialist.
Analyze code structure, identify patterns, suggest architectural improvements.
Focus on:
- Module organization and dependencies
- Design patterns and anti-patterns
- Scalability and maintainability concerns
- API design and contracts""",
                "tools": ["Read", "Grep", "Glob"],
            },
            "debugger": {
                "description": "Debugging specialist. Use for investigating bugs and unexpected behavior.",
                "prompt": """You are a debugging specialist.
Systematically investigate issues:
- Reproduce the problem
- Add logging/tracing to narrow down the cause
- Identify root causes
- Propose and test fixes""",
                "tools": ["Read", "Bash", "Edit", "Grep"],
            },
        }

        # Convert to dataclass instances - SDK's asdict() requires dataclass instances
        # Must use module-level dataclass for proper serialization
        return {
            name: AgentDefinition(**agent_data)
            for name, agent_data in agent_defs.items()
        }

    def to_sdk_options(
        self, pre_tool_hook=None, post_tool_hook=None, stderr_callback=None
    ) -> "ClaudeAgentOptions":
        """Create ClaudeAgentOptions from config.

        Args:
            pre_tool_hook: Hook to run before tool execution
            post_tool_hook: Hook to run after tool execution
            stderr_callback: Callback to receive stderr output from CLI subprocess.
                             If not provided, stderr is logged at DEBUG level.
        """
        # Build environment variables for the CLI subprocess
        env = {"ANTHROPIC_API_KEY": self.api_key}
        if self.api_base_url:
            env["ANTHROPIC_BASE_URL"] = self.api_base_url

        # Build options dict
        # Convert cwd to Path if it's a string (SDK expects Path)
        cwd_path = Path(self.cwd) if isinstance(self.cwd, str) else self.cwd

        # Create stderr handler to capture CLI errors
        # This is critical for debugging initialization failures
        def default_stderr_handler(line: str):
            logger.debug("CLI stderr: %s", line.strip())

        stderr_handler = stderr_callback or default_stderr_handler

        options_kwargs = {
            "system_prompt": self.system_prompt,
            "permission_mode": self.permission_mode,
            "max_turns": self.max_turns,
            "max_budget_usd": self.max_budget_usd,
            "cwd": cwd_path,
            "env": env,
            "stderr": stderr_handler,  # Capture CLI stderr for debugging
        }

        # Only set allowed_tools if explicitly configured
        # Otherwise, SDK uses its default preset (includes all standard tools like Skill, Task, etc.)
        if self.allowed_tools is not None:
            options_kwargs["allowed_tools"] = self.allowed_tools

        # Set disallowed_tools if configured (to block specific tools)
        if self.disallowed_tools is not None:
            options_kwargs["disallowed_tools"] = self.disallowed_tools

        # Add model if specified
        if self.model:
            options_kwargs["model"] = self.model

        # Add setting sources for skills
        if self.setting_sources:
            options_kwargs["setting_sources"] = self.setting_sources

        # Add custom subagents
        # Convert agent dicts to pydantic models so SDK can use model_dump() instead of asdict()
        if self.enable_subagents:
            options_kwargs["agents"] = self.get_custom_agents()

        # Add session resumption options
        if self.resume_session_id:
            options_kwargs["resume"] = self.resume_session_id
            options_kwargs["fork_session"] = self.fork_session

        # Add MCP servers for spec workflow tools
        # MCP servers are registered as a dict with server names as keys
        # Tools are automatically available once the server is registered (mcp__{server}__{tool})
        if self.enable_spec_tools and MCP_AVAILABLE:
            try:
                mcp_server = create_spec_workflow_mcp_server()
                options_kwargs["mcp_servers"] = {"spec_workflow": mcp_server}
                logger.info("Spec workflow MCP server enabled")
            except Exception as e:
                logger.warning(
                    "Failed to create spec workflow MCP server", extra={"error": str(e)}
                )

        # Add hooks
        hooks = {}
        if pre_tool_hook:
            hooks["PreToolUse"] = [
                HookMatcher(matcher="Write", hooks=[pre_tool_hook]),
                HookMatcher(matcher="Edit", hooks=[pre_tool_hook]),
            ]
        if post_tool_hook:
            # matcher=None means match ALL tools (for comprehensive event tracking)
            # The hook itself filters for specific tools (e.g., Bash for spec validation)
            hooks["PostToolUse"] = [
                HookMatcher(matcher=None, hooks=[post_tool_hook]),
            ]

        if hooks:
            options_kwargs["hooks"] = hooks

        return ClaudeAgentOptions(**options_kwargs)

    def get_session_transcript_path(self, session_id: str) -> Path:
        """Get the path where session transcripts are stored.

        Claude Code stores sessions in ~/.claude/projects/<project-key>/<session-id>.jsonl
        The project key is derived from cwd, replacing slashes with dashes.
        """
        # Convert cwd to project key format (e.g., /workspace -> -workspace)
        project_key = self.cwd.replace("/", "-")
        if not project_key.startswith("-"):
            project_key = "-" + project_key
        return (
            Path.home() / ".claude" / "projects" / project_key / f"{session_id}.jsonl"
        )

    def import_session_transcript(self) -> bool:
        """Import a session transcript from base64-encoded content.

        This enables session portability across sandboxes by:
        1. Decoding the base64 transcript content
        2. Writing it to the correct local path
        3. Enabling the resume option to find and use it

        Returns True if import succeeded, False otherwise.
        """
        if not self.session_transcript_b64 or not self.resume_session_id:
            return False

        try:
            # Decode the transcript
            transcript_content = base64.b64decode(self.session_transcript_b64).decode(
                "utf-8"
            )

            # Get the target path and ensure directory exists
            transcript_path = self.get_session_transcript_path(self.resume_session_id)
            transcript_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the transcript
            transcript_path.write_text(transcript_content)
            logger.info(
                "Imported session transcript",
                extra={
                    "session_id": self.resume_session_id,
                    "path": str(transcript_path),
                },
            )
            return True

        except Exception as e:
            logger.error("Failed to import session transcript", extra={"error": str(e)})
            return False

    def export_session_transcript(self, session_id: str) -> Optional[str]:
        """Export a session transcript as base64-encoded content.

        This can be used to save the session for later resumption on
        a different sandbox.

        Returns base64-encoded transcript content, or None if not found.
        """
        transcript_path = self.get_session_transcript_path(session_id)
        if not transcript_path.exists():
            return None

        try:
            transcript_content = transcript_path.read_text()
            return base64.b64encode(transcript_content.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logger.error("Failed to export session transcript", extra={"error": str(e)})
            return None


# =============================================================================
# Event Reporter (Webhook Client)
# =============================================================================


class EventReporter:
    """Reports events back to main server via HTTP POST with comprehensive tracking."""

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self.event_count = 0

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    async def report(
        self,
        event_type: str,
        event_data: dict[str, Any],
        source: str = "agent",
    ) -> bool:
        """Report event to main server with full context."""
        if not self.client:
            return False

        self.event_count += 1

        # Always add core identifiers
        event_data = {
            **event_data,
            "task_id": self.config.task_id,
            "agent_id": self.config.agent_id,
            "sandbox_id": self.config.sandbox_id,
        }

        url = f"{self.config.callback_url}/api/v1/sandboxes/{self.config.sandbox_id}/events"

        try:
            response = await self.client.post(
                url,
                json={
                    "event_type": event_type,
                    "event_data": event_data,
                    "source": source,
                },
            )
            success = response.status_code == 200
            if not success:
                # Suppress 502 errors (Bad Gateway) - server temporarily unavailable
                # This is common during server restarts, load balancer issues, or DB timeouts
                if response.status_code == 502:
                    # Silently fail - heartbeats are non-critical and 502s are transient
                    return False
                # Log other non-200 status codes
                logger.warning(
                    "Event report failed",
                    extra={
                        "event_type": event_type,
                        "status_code": response.status_code,
                    },
                )
            return success
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors (like 502 Bad Gateway)
            status_code = e.response.status_code if hasattr(e, "response") else None
            if status_code == 502:
                # Server temporarily unavailable - don't spam logs
                # Heartbeats are non-critical, so we silently fail
                return False
            else:
                logger.warning(
                    "HTTP error reporting event",
                    extra={"event_type": event_type, "status_code": status_code},
                )
            return False
        except httpx.RequestError as e:
            # Network-level errors (connection refused, timeout, etc.)
            # Check if it's a 502-related error
            error_str = str(e).lower()
            if "502" in error_str or "bad gateway" in error_str:
                # Silently fail for 502-related network errors
                return False
            # Log other network errors (but not for heartbeats to reduce spam)
            if event_type != "agent.heartbeat":
                logger.warning(
                    "Network error reporting event",
                    extra={"event_type": event_type, "error": str(e)},
                )
            return False
        except Exception as e:
            # Only log unexpected errors, not network timeouts or 502s
            error_str = str(e).lower()
            if "502" in error_str or "bad gateway" in error_str:
                # Silently fail for 502-related errors
                return False
            # Log other unexpected errors (but not for heartbeats)
            if event_type != "agent.heartbeat":
                logger.error(
                    "Failed to report event",
                    extra={"event_type": event_type, "error": str(e)},
                )
            return False

    async def heartbeat(self) -> bool:
        """Send heartbeat event."""
        return await self.report(
            "agent.heartbeat",
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "alive",
                "event_count": self.event_count,
            },
            source="worker",
        )


# =============================================================================
# Message Poller
# =============================================================================


class MessagePoller:
    """Polls main server for injected messages."""

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    async def poll(self) -> list[dict]:
        """Poll for pending messages."""
        if not self.client:
            return []

        url = f"{self.config.callback_url}/api/v1/sandboxes/{self.config.sandbox_id}/messages"

        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning("Message poll failed", extra={"error": str(e)})

        return []


# =============================================================================
# GitHub Setup
# =============================================================================


def setup_github_workspace(config: WorkerConfig) -> bool:
    """Clone GitHub repo and setup workspace if configured."""
    if not config.github_token or not config.github_repo:
        logger.info("No GitHub credentials, skipping repo clone")
        return False

    # Check if already cloned
    if os.path.exists(os.path.join(config.cwd, ".git")):
        logger.info("Workspace already has git repo", extra={"cwd": config.cwd})
        return True

    # Configure git user
    subprocess.run(
        ["git", "config", "--global", "user.email", "agent@omoios.ai"], check=False
    )
    subprocess.run(
        ["git", "config", "--global", "user.name", "OmoiOS Agent"], check=False
    )

    # Clone with token
    clone_url = f"https://x-access-token:{config.github_token}@github.com/{config.github_repo}.git"
    logger.info("Cloning GitHub repository", extra={"repo": config.github_repo})

    result = subprocess.run(
        ["git", "clone", clone_url, config.cwd], capture_output=True, text=True
    )

    if result.returncode != 0:
        logger.error("GitHub clone failed", extra={"stderr": result.stderr})
        return False

    os.chdir(config.cwd)

    # Checkout branch if specified
    if config.branch_name:
        logger.info("Checking out branch", extra={"branch": config.branch_name})
        subprocess.run(["git", "checkout", config.branch_name], check=False)

    logger.info("Repository ready", extra={"cwd": config.cwd})
    return True


def find_dependency_files(cwd: str) -> dict:
    """Search for dependency files recursively using glob.

    Uses pathlib.rglob to find dependency files anywhere in the workspace,
    excluding common vendor/cache directories like node_modules, .venv, etc.

    Returns:
        dict mapping file types to their full paths (or None if not found).
        Prefers files closer to root (shallowest depth).
    """
    from pathlib import Path

    # Directories to exclude from search (vendor dirs, caches, etc.)
    EXCLUDE_DIRS = {
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        ".tox",
        ".nox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".eggs",
        "site-packages",
        ".cache",
        ".uv",
        ".npm",
        ".yarn",
        ".pnpm-store",
        ".next",
        ".nuxt",
        "vendor",
        "vendors",
        "third_party",
        "external",
    }

    found = {
        # Python
        "uv_lock": None,
        "poetry_lock": None,
        "pyproject": None,
        "requirements": None,
        "setup_py": None,
        # Node.js
        "pnpm_lock": None,
        "yarn_lock": None,
        "npm_lock": None,
        "package_json": None,
    }

    file_mappings = {
        "uv_lock": "uv.lock",
        "poetry_lock": "poetry.lock",
        "pyproject": "pyproject.toml",
        "requirements": "requirements.txt",
        "setup_py": "setup.py",
        "pnpm_lock": "pnpm-lock.yaml",
        "yarn_lock": "yarn.lock",
        "npm_lock": "package-lock.json",
        "package_json": "package.json",
    }

    root = Path(cwd)

    def is_excluded(path: Path) -> bool:
        """Check if any parent directory is in the exclude list."""
        try:
            rel_path = path.relative_to(root)
            for part in rel_path.parts:
                if part in EXCLUDE_DIRS or part.endswith(".egg-info"):
                    return True
        except ValueError:
            return True  # Path not relative to root
        return False

    def find_closest(filename: str) -> Optional[str]:
        """Find the closest (shallowest) match for a filename.

        Prefers files closer to root to avoid finding files in nested
        example projects or test fixtures.
        """
        matches = []
        try:
            for match in root.rglob(filename):
                if match.is_file() and not is_excluded(match):
                    # Calculate depth (number of directories from root)
                    depth = len(match.relative_to(root).parts) - 1
                    matches.append((depth, str(match)))
        except (OSError, PermissionError) as e:
            logger.debug(f"Error searching for {filename}: {e}")
            return None

        if matches:
            # Sort by depth (shallowest first), then by path (alphabetical)
            matches.sort(key=lambda x: (x[0], x[1]))
            return matches[0][1]
        return None

    # Find each dependency file
    for key, filename in file_mappings.items():
        filepath = find_closest(filename)
        if filepath:
            found[key] = filepath
            logger.debug(f"Found {filename} at {filepath}")

    return found


def install_project_dependencies(cwd: str) -> dict:
    """Detect and install project dependencies automatically.

    Detects Python (UV, Poetry, pip) and Node.js (pnpm, yarn, npm) projects
    and runs the appropriate install command. Uses recursive glob search to
    find dependency files anywhere in the workspace, excluding vendor/cache
    directories (node_modules, .venv, __pycache__, etc.).

    Prefers files closest to the workspace root to avoid installing from
    nested example projects or test fixtures.

    Returns:
        dict with keys: python_installed, node_installed, errors, summary
    """
    result = {
        "python_installed": False,
        "python_manager": None,
        "python_dir": None,
        "node_installed": False,
        "node_manager": None,
        "node_dir": None,
        "errors": [],
        "summary": ""  # Human-readable summary for system prompt
    }

    logger.info("Detecting and installing project dependencies", extra={"cwd": cwd})

    # Find dependency files (searches root + common subdirs)
    found = find_dependency_files(cwd)

    # Python dependency detection and installation
    # Priority: uv.lock > poetry.lock > pyproject.toml > requirements.txt > setup.py

    # Helper to run install command and track result
    def run_install(cmd: list, install_cwd: str, manager: str, lang: str) -> bool:
        """Run install command and update result dict."""
        logger.info(f"Running {' '.join(cmd)} in {install_cwd}")
        try:
            proc = subprocess.run(
                cmd,
                cwd=install_cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            if proc.returncode == 0:
                if lang == "python":
                    result["python_installed"] = True
                    result["python_manager"] = manager
                    result["python_dir"] = install_cwd
                else:
                    result["node_installed"] = True
                    result["node_manager"] = manager
                    result["node_dir"] = install_cwd
                logger.info(f"{manager} install completed successfully in {install_cwd}")
                return True
            else:
                error = f"{' '.join(cmd)} failed in {install_cwd}: {proc.stderr}"
                result["errors"].append(error)
                logger.warning(error)
                return False
        except subprocess.TimeoutExpired:
            error = f"{' '.join(cmd)} timed out in {install_cwd}"
            result["errors"].append(error)
            logger.warning(error)
            return False
        except Exception as e:
            error = f"{' '.join(cmd)} error in {install_cwd}: {e}"
            result["errors"].append(error)
            logger.warning(error)
            return False

    # Python dependency installation
    # Priority: uv.lock > poetry.lock > pyproject.toml > requirements.txt > setup.py
    python_installed = False

    if found["uv_lock"]:
        install_dir = os.path.dirname(found["uv_lock"])
        logger.info(f"Detected UV project (uv.lock found at {found['uv_lock']})")
        python_installed = run_install(["uv", "sync"], install_dir, "uv", "python")

    elif found["poetry_lock"]:
        install_dir = os.path.dirname(found["poetry_lock"])
        logger.info(f"Detected Poetry project (poetry.lock found at {found['poetry_lock']})")
        python_installed = run_install(["poetry", "install"], install_dir, "poetry", "python")

    elif found["pyproject"]:
        install_dir = os.path.dirname(found["pyproject"])
        # Read pyproject.toml to detect manager
        try:
            with open(found["pyproject"]) as f:
                content = f.read()

            if "[tool.uv]" in content:
                logger.info(f"Detected UV project ([tool.uv] in {found['pyproject']})")
                python_installed = run_install(["uv", "sync"], install_dir, "uv", "python")
            elif "[tool.poetry]" in content:
                logger.info(f"Detected Poetry project ([tool.poetry] in {found['pyproject']})")
                python_installed = run_install(["poetry", "install"], install_dir, "poetry", "python")
            else:
                logger.info(f"Detected generic pyproject.toml at {found['pyproject']}")
                python_installed = run_install(["pip", "install", "-e", "."], install_dir, "pip", "python")
        except Exception as e:
            error = f"Error reading {found['pyproject']}: {e}"
            result["errors"].append(error)
            logger.warning(error)

    elif found["requirements"]:
        install_dir = os.path.dirname(found["requirements"])
        logger.info(f"Detected requirements.txt at {found['requirements']}")
        python_installed = run_install(["pip", "install", "-r", "requirements.txt"], install_dir, "pip", "python")

    elif found["setup_py"]:
        install_dir = os.path.dirname(found["setup_py"])
        logger.info(f"Detected setup.py at {found['setup_py']}")
        python_installed = run_install(["pip", "install", "-e", "."], install_dir, "pip", "python")

    # Node.js dependency installation
    # Priority: pnpm-lock.yaml > yarn.lock > package-lock.json > package.json
    node_installed = False

    if found["package_json"]:
        install_dir = os.path.dirname(found["package_json"])

        if found["pnpm_lock"]:
            logger.info(f"Detected pnpm project (pnpm-lock.yaml found)")
            node_installed = run_install(["pnpm", "install"], install_dir, "pnpm", "node")
        elif found["yarn_lock"]:
            logger.info(f"Detected Yarn project (yarn.lock found)")
            node_installed = run_install(["yarn", "install"], install_dir, "yarn", "node")
        elif found["npm_lock"]:
            logger.info(f"Detected npm project (package-lock.json found)")
            node_installed = run_install(["npm", "install"], install_dir, "npm", "node")

    # Build human-readable summary for system prompt
    summary_parts = []

    if result["python_installed"]:
        rel_dir = os.path.relpath(result["python_dir"], cwd) if result["python_dir"] != cwd else "root"
        summary_parts.append(
            f"✅ Python dependencies installed via `{result['python_manager']}` in `{rel_dir}/`"
        )
        if result["python_manager"] == "uv":
            summary_parts.append(f"   → Use `uv run <command>` to run Python tools (e.g., `uv run python script.py`)")
        elif result["python_manager"] == "poetry":
            summary_parts.append(f"   → Use `poetry run <command>` to run Python tools")
    elif found["pyproject"] or found["requirements"] or found["setup_py"]:
        summary_parts.append("⚠️ Python dependency files found but installation failed - check errors")

    if result["node_installed"]:
        rel_dir = os.path.relpath(result["node_dir"], cwd) if result["node_dir"] != cwd else "root"
        summary_parts.append(
            f"✅ Node.js dependencies installed via `{result['node_manager']}` in `{rel_dir}/`"
        )
        if result["node_manager"] == "pnpm":
            summary_parts.append(f"   → Use `pnpm run <script>` or `pnpm exec <binary>`")
        elif result["node_manager"] == "yarn":
            summary_parts.append(f"   → Use `yarn <script>` or `yarn <binary>`")
        else:
            summary_parts.append(f"   → Use `npm run <script>` or `npx <binary>`")
    elif found["package_json"]:
        summary_parts.append("⚠️ package.json found but installation failed - check errors")

    if result["errors"]:
        summary_parts.append(f"⚠️ Errors during dependency installation:")
        for err in result["errors"][:3]:  # Limit to first 3 errors
            summary_parts.append(f"   - {err[:200]}")  # Truncate long errors

    if not summary_parts:
        summary_parts.append("ℹ️ No dependency files detected in project root or common subdirectories")

    result["summary"] = "\n".join(summary_parts)

    # Log summary
    if result["python_installed"] or result["node_installed"]:
        logger.info(
            "Dependency installation complete",
            extra={
                "python_manager": result["python_manager"],
                "python_dir": result["python_dir"],
                "node_manager": result["node_manager"],
                "node_dir": result["node_dir"],
            }
        )
    elif not result["errors"]:
        logger.info("No dependency files detected (searched root and common subdirs)")

    return result


# =============================================================================
# Main Worker
# =============================================================================


class SandboxWorker:
    """Main worker orchestrator with comprehensive event tracking.

    Supports both single-run and continuous modes:
    - Single-run: Execute task once and wait for messages
    - Continuous: Iterate until task truly completes (code pushed, PR created)
    """

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.running = False
        self._shutdown_event = asyncio.Event()
        self._should_stop = False
        self.turn_count = 0
        self.reporter: Optional[EventReporter] = None
        self.file_tracker = FileChangeTracker()

        # Iteration state for continuous mode
        self.iteration_state = IterationState()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown on SIGTERM/SIGINT."""

        def handle_signal(signum, frame):
            logger.info("Received shutdown signal", extra={"signum": signum})
            self._shutdown_event.set()
            self._should_stop = True

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

    async def _create_post_tool_hook(self):
        """Create PostToolUse hook for comprehensive tool tracking."""
        # Capture references - reporter may be None initially, check before use
        reporter_ref = self.reporter
        file_tracker = self.file_tracker
        turn_count = self.turn_count

        async def track_tool_use(input_data, tool_use_id, context):
            """PostToolUse hook for comprehensive event reporting."""
            tool_name = input_data.get("tool_name", "unknown")
            tool_input = input_data.get("tool_input", {})

            # Debug: Log every hook invocation to confirm hooks are working
            logger.debug(
                "PostToolUse hook invoked",
                extra={
                    "tool_name": tool_name,
                    "tool_use_id": tool_use_id,
                    "require_spec_skill": self.config.require_spec_skill,
                },
            )

            # Get current reporter (may have been set after hook creation)
            reporter = self.reporter or reporter_ref
            if not reporter:
                return {}  # Skip reporting if reporter not available
            tool_response = input_data.get("tool_response", "")

            # NEW: File diff generation for Write/Edit
            if tool_name == "Write":
                file_path = tool_input.get("file_path")
                new_content = tool_input.get("content", "")
                if file_path and new_content:
                    try:
                        diff_info = file_tracker.generate_diff(file_path, new_content)
                        await reporter.report(
                            "agent.file_edited",
                            {
                                "turn": turn_count,
                                "tool_use_id": tool_use_id,
                                **diff_info,
                            },
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to generate diff",
                            extra={"file_path": file_path, "error": str(e)},
                        )

            elif tool_name == "Edit":
                file_path = tool_input.get("file_path")
                if file_path:
                    try:
                        file_path = Path(file_path)
                        if file_path.exists():
                            new_content = file_path.read_text()
                            diff_info = file_tracker.generate_diff(
                                str(file_path), new_content
                            )
                            await reporter.report(
                                "agent.file_edited",
                                {
                                    "turn": turn_count,
                                    "tool_use_id": tool_use_id,
                                    **diff_info,
                                },
                            )
                    except Exception as e:
                        logger.warning(
                            "Failed to read file after edit",
                            extra={"file_path": str(file_path), "error": str(e)},
                        )

            # Serialize tool_response properly
            # Claude SDK tool results (like CLIResult) are objects with stdout/stderr fields
            serialized_response = None
            if tool_response:
                if hasattr(tool_response, "stdout"):
                    # CLIResult-like object from Bash tool
                    serialized_response = tool_response.stdout or ""
                    if hasattr(tool_response, "stderr") and tool_response.stderr:
                        serialized_response += f"\n[stderr]: {tool_response.stderr}"
                elif hasattr(tool_response, "__dict__"):
                    # Generic object - try to serialize nicely
                    import json

                    try:
                        serialized_response = json.dumps(
                            tool_response.__dict__, default=str
                        )
                    except (TypeError, ValueError):
                        serialized_response = str(tool_response)
                else:
                    serialized_response = str(tool_response)

            # Full tool tracking
            event_data = {
                "turn": turn_count,
                "tool": tool_name,
                "tool_input": tool_input,
                "tool_response": serialized_response,
            }

            # Special tracking for subagents
            if tool_name == "Task":
                event_data["subagent_type"] = tool_input.get("subagent_type")
                event_data["description"] = tool_input.get("description")
                event_data["subagent_prompt"] = tool_input.get("prompt")

                # Extract the actual subagent result from tool_response
                # Task tool returns: {"result": "...", "usage": {...}, "total_cost_usd": ..., "duration_ms": ...}
                subagent_result = None
                subagent_usage = None
                subagent_cost = None
                subagent_duration = None

                if serialized_response:
                    try:
                        import json

                        # Try to parse the response as JSON
                        if isinstance(serialized_response, str):
                            result_data = json.loads(serialized_response)
                        else:
                            result_data = serialized_response

                        if isinstance(result_data, dict):
                            subagent_result = result_data.get("result")
                            subagent_usage = result_data.get("usage")
                            subagent_cost = result_data.get("total_cost_usd")
                            subagent_duration = result_data.get("duration_ms")
                    except (json.JSONDecodeError, TypeError):
                        # If parsing fails, use the raw response as result
                        subagent_result = serialized_response

                event_data["subagent_result"] = subagent_result
                event_data["subagent_usage"] = subagent_usage
                event_data["subagent_cost_usd"] = subagent_cost
                event_data["subagent_duration_ms"] = subagent_duration

                await reporter.report("agent.subagent_completed", event_data)
            # Special tracking for skills
            elif tool_name == "Skill":
                event_data["skill_name"] = tool_input.get("name") or tool_input.get(
                    "skill_name"
                )
                await reporter.report("agent.skill_completed", event_data)
            else:
                await reporter.report("agent.tool_completed", event_data)

            # Spec-driven workflow auto-sync reminder
            # ONLY runs when REQUIRE_SPEC_SKILL=true to avoid overhead on normal sandboxes
            # When we detect a successful `spec_cli.py validate` command,
            # inject a system message reminding the agent to sync to the API
            if self.config.require_spec_skill and tool_name == "Bash":
                command = tool_input.get("command", "")
                # Detect spec_cli.py validate command
                if "spec_cli.py" in command and "validate" in command:
                    response_str = serialized_response or ""

                    # Debug logging to diagnose detection issues
                    logger.info(
                        "PostToolUse: spec_cli.py validate detected",
                        extra={
                            "command": command,
                            "response_length": len(response_str),
                            "response_preview": response_str[:500] if response_str else "(empty)",
                        },
                    )

                    # Check for successful validation
                    # The validate command outputs on success:
                    #   "========================================================================"
                    #   " VALIDATION"
                    #   "========================================================================"
                    #   ""
                    #   "✓ No circular dependencies detected"
                    #   "✓ All task references valid"
                    #   "✓ All ticket references valid"
                    #
                    # On failure, exits with code 1 and shows "✗ Found X validation error(s)"
                    response_lower = response_str.lower()

                    # SUCCESS indicators - comprehensive list
                    # Checkmarks (multiple unicode representations)
                    has_checkmark = (
                        "✓" in response_str or           # Direct checkmark
                        "\u2713" in response_str or      # Unicode CHECK MARK
                        "\u2714" in response_str or      # Unicode HEAVY CHECK MARK
                        "[x]" in response_lower or       # Markdown checkbox
                        "[✓]" in response_str            # Bracketed checkmark
                    )

                    # Specific success messages from spec_cli.py
                    has_no_circular = "no circular dependencies" in response_lower
                    has_task_refs_valid = "all task references valid" in response_lower
                    has_ticket_refs_valid = "all ticket references valid" in response_lower

                    # Generic success patterns
                    has_validation_header = "validation" in response_lower and "======" in response_str
                    has_success_keyword = (
                        "success" in response_lower or
                        "passed" in response_lower or
                        "valid" in response_lower
                    )

                    # Exit code success (if captured in output)
                    has_exit_zero = "exit code: 0" in response_lower or "exit code 0" in response_lower

                    # FAILURE indicators (if present, don't inject reminder)
                    has_error = (
                        "validation error" in response_lower or
                        "error(" in response_lower or      # "Found X error(s)"
                        "✗" in response_str or             # X mark
                        "\u2717" in response_str or        # Unicode BALLOT X
                        "\u2718" in response_str or        # Unicode HEAVY BALLOT X
                        "failed" in response_lower or
                        "invalid" in response_lower or
                        "circular dependency" in response_lower and "no circular" not in response_lower or
                        "missing" in response_lower or
                        "not found" in response_lower
                    )

                    # Combine success indicators
                    success_signals = (
                        has_checkmark or
                        has_no_circular or
                        has_task_refs_valid or
                        has_ticket_refs_valid or
                        has_exit_zero or
                        (has_validation_header and has_success_keyword)
                    )

                    validation_passed = success_signals and not has_error

                    logger.info(
                        "PostToolUse: validation detection result",
                        extra={
                            "has_checkmark": has_checkmark,
                            "has_no_circular": has_no_circular,
                            "has_task_refs_valid": has_task_refs_valid,
                            "has_ticket_refs_valid": has_ticket_refs_valid,
                            "has_validation_header": has_validation_header,
                            "has_success_keyword": has_success_keyword,
                            "has_exit_zero": has_exit_zero,
                            "has_error": has_error,
                            "success_signals": success_signals,
                            "validation_passed": validation_passed,
                        },
                    )

                    if validation_passed:
                        logger.info(
                            "Spec validation successful - injecting sync reminder",
                            extra={"command": command},
                        )
                        return {
                            "systemMessage": """
🔔 SPEC VALIDATION PASSED - SYNC REQUIRED!

Your specs validated successfully. Now you MUST sync them to the API to make them visible.

Run these commands IN ORDER:
```bash
cd /root/.claude/skills/spec-driven-dev/scripts

# Sync requirements & designs to create specs in the API
python spec_cli.py sync-specs push

# Sync tickets and tasks
python spec_cli.py sync push

# Verify everything synced correctly
python spec_cli.py api-trace
```

⚠️ Your work is NOT complete until all sync commands succeed.
""",
                            "hookSpecificOutput": {
                                "hookEventName": "PostToolUse",
                                "additionalContext": "Spec validation passed - auto-sync reminder injected",
                            },
                        }

            return {}

        return track_tool_use

    async def _create_pre_tool_hook(self):
        """Create PreToolUse hook for file caching."""
        file_tracker = self.file_tracker

        async def pre_tool_use_file_cache(
            input_data: HookInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookJSONOutput:
            tool_name = input_data.get("tool_name", "")
            tool_input = input_data.get("tool_input", {})

            if tool_name in ["Write", "Edit"]:
                file_path = tool_input.get("file_path")
                if file_path:
                    file_path = Path(file_path)
                    if file_path.exists():
                        try:
                            old_content = file_path.read_text()
                            file_tracker.cache_file_before_edit(
                                str(file_path), old_content
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to cache file",
                                extra={"file_path": str(file_path), "error": str(e)},
                            )

            return {}

        return pre_tool_use_file_cache

    async def _process_messages(
        self,
        client: "ClaudeSDKClient",
    ):
        """Process streaming messages with comprehensive event tracking."""
        final_output = []

        # Ensure reporter is available
        if not self.reporter:
            logger.warning("Reporter not available, skipping event reporting")
            # Still process messages but without reporting

        try:
            # Wrap receive_messages() with better error handling for SIGKILL (-9) errors
            try:
                message_stream = client.receive_messages()
            except Exception as stream_init_error:
                error_msg = str(stream_init_error)
                logger.error(
                    "Failed to initialize message stream", extra={"error": error_msg}
                )
                if self.reporter:
                    await self.reporter.report(
                        "agent.stream_error",
                        {
                            "error": f"Stream initialization failed: {error_msg}",
                            "turn": self.turn_count,
                            "error_type": "stream_init",
                        },
                    )
                raise

            async for msg in message_stream:
                if isinstance(msg, AssistantMessage):
                    self.turn_count += 1

                    # Report assistant message metadata
                    if self.reporter:
                        await self.reporter.report(
                            "agent.assistant_message",
                            {
                                "turn": self.turn_count,
                                "model": getattr(msg, "model", self.config.model),
                                "stop_reason": getattr(msg, "stop_reason", None),
                                "block_count": len(msg.content),
                            },
                        )

                    for block in msg.content:
                        if isinstance(block, ThinkingBlock):
                            if self.reporter:
                                await self.reporter.report(
                                    "agent.thinking",
                                    {
                                        "turn": self.turn_count,
                                        "content": block.text,  # Full content
                                        "thinking_type": "extended_thinking",
                                    },
                                )
                            logger.debug(
                                "Agent thinking",
                                extra={"content_preview": block.text[:100]},
                            )

                        elif isinstance(block, ToolUseBlock):
                            tool_event = {
                                "turn": self.turn_count,
                                "tool": block.name,
                                "tool_use_id": block.id,
                                "input": block.input,  # Full input
                            }

                            # Special handling for subagent dispatch
                            if block.name == "Task":
                                tool_event["event_subtype"] = "subagent_invoked"
                                tool_event["subagent_type"] = block.input.get(
                                    "subagent_type"
                                )
                                tool_event["subagent_description"] = block.input.get(
                                    "description"
                                )
                                tool_event["subagent_prompt"] = block.input.get(
                                    "prompt"
                                )
                                if self.reporter:
                                    await self.reporter.report(
                                        "agent.subagent_invoked", tool_event
                                    )
                                logger.info(
                                    "Subagent invoked",
                                    extra={
                                        "subagent_type": block.input.get(
                                            "subagent_type"
                                        )
                                    },
                                )

                            # Special handling for skill invocation
                            elif block.name == "Skill":
                                tool_event["event_subtype"] = "skill_invoked"
                                tool_event["skill_name"] = block.input.get(
                                    "name"
                                ) or block.input.get("skill_name")
                                if self.reporter:
                                    await self.reporter.report(
                                        "agent.skill_invoked", tool_event
                                    )
                                logger.info(
                                    "Skill invoked",
                                    extra={"skill_name": tool_event["skill_name"]},
                                )

                            # Standard tool use
                            else:
                                tool_event["event_subtype"] = "tool_use"
                                if self.reporter:
                                    await self.reporter.report(
                                        "agent.tool_use", tool_event
                                    )
                                logger.info("Tool use", extra={"tool": block.name})

                        elif isinstance(block, ToolResultBlock):
                            result_content = str(block.content)
                            if self.reporter:
                                await self.reporter.report(
                                    "agent.tool_result",
                                    {
                                        "turn": self.turn_count,
                                        "tool_use_id": block.tool_use_id,
                                        "result": result_content[:5000]
                                        if len(result_content) > 5000
                                        else result_content,
                                        "result_truncated": len(result_content) > 5000,
                                        "result_full_length": len(result_content),
                                        "is_error": getattr(block, "is_error", False),
                                    },
                                )
                            is_error = getattr(block, "is_error", False)
                            logger.debug(
                                "Tool result",
                                extra={
                                    "is_error": is_error,
                                    "result_preview": result_content[:80],
                                },
                            )

                        elif isinstance(block, TextBlock):
                            if self.reporter:
                                await self.reporter.report(
                                    "agent.message",
                                    {
                                        "turn": self.turn_count,
                                        "content": block.text,  # Full content
                                        "content_length": len(block.text),
                                    },
                                )
                            final_output.append(block.text)
                            logger.debug(
                                "Agent message",
                                extra={"content_preview": block.text[:100]},
                            )

                elif isinstance(msg, UserMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            if self.reporter:
                                await self.reporter.report(
                                    "agent.user_message",
                                    {
                                        "turn": self.turn_count,
                                        "content": block.text,
                                        "content_length": len(block.text),
                                    },
                                )
                        elif isinstance(block, ToolResultBlock):
                            result_content = str(block.content)
                            if self.reporter:
                                await self.reporter.report(
                                    "agent.user_tool_result",
                                    {
                                        "turn": self.turn_count,
                                        "tool_use_id": block.tool_use_id,
                                        "result": result_content[:5000]
                                        if len(result_content) > 5000
                                        else result_content,
                                        "result_truncated": len(result_content) > 5000,
                                    },
                                )

                elif isinstance(msg, SystemMessage):
                    if self.reporter:
                        await self.reporter.report(
                            "agent.system_message",
                            {
                                "turn": self.turn_count,
                                "metadata": getattr(msg, "metadata", {}),
                            },
                        )

                elif isinstance(msg, ResultMessage):
                    usage = getattr(msg, "usage", None)

                    # Export session transcript for cross-sandbox resumption
                    transcript_b64 = None
                    if hasattr(msg, "session_id") and msg.session_id:
                        try:
                            transcript_b64 = self.config.export_session_transcript(
                                msg.session_id
                            )
                            if transcript_b64:
                                logger.info(
                                    "Exported session transcript",
                                    extra={"size_bytes": len(transcript_b64)},
                                )
                        except Exception as e:
                            logger.warning(
                                "Failed to export session transcript",
                                extra={"error": str(e)},
                            )

                    # Safely extract message attributes (handle both object and dict)
                    num_turns = getattr(msg, "num_turns", None)
                    total_cost_usd = getattr(msg, "total_cost_usd", 0.0)
                    session_id = getattr(msg, "session_id", None)
                    stop_reason = getattr(msg, "stop_reason", None)

                    if self.reporter:
                        # Handle usage as dict or object
                        input_tokens = None
                        output_tokens = None
                        cache_read_tokens = None
                        cache_write_tokens = None

                        if usage:
                            if isinstance(usage, dict):
                                input_tokens = usage.get("input_tokens")
                                output_tokens = usage.get("output_tokens")
                                cache_read_tokens = usage.get("cache_read_input_tokens")
                                cache_write_tokens = usage.get(
                                    "cache_creation_input_tokens"
                                )
                            else:
                                input_tokens = getattr(usage, "input_tokens", None)
                                output_tokens = getattr(usage, "output_tokens", None)
                                cache_read_tokens = getattr(
                                    usage, "cache_read_input_tokens", None
                                )
                                cache_write_tokens = getattr(
                                    usage, "cache_creation_input_tokens", None
                                )

                        # ALWAYS capture git/CI state before completion event
                        # This ensures artifacts are generated regardless of how agent completed
                        # (continuous mode, single-run mode, natural completion, etc.)
                        try:
                            git_status = check_git_status(self.config.cwd)
                            state = self.iteration_state
                            state.code_committed = git_status["is_clean"]
                            state.code_pushed = git_status["is_pushed"]
                            state.pr_created = git_status["has_pr"]
                            state.tests_passed = git_status["tests_passed"]
                            state.pr_url = git_status.get("pr_url")
                            state.pr_number = git_status.get("pr_number")
                            state.files_changed = git_status.get("files_changed", 0)
                            state.ci_status = git_status.get("ci_status")
                            logger.info(
                                "Pre-completion git validation",
                                extra={
                                    "code_pushed": state.code_pushed,
                                    "pr_created": state.pr_created,
                                    "tests_passed": state.tests_passed,
                                    "pr_url": state.pr_url,
                                },
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to capture git status before completion",
                                extra={"error": str(e)},
                            )

                        # Build completion event with final output
                        completion_event: dict[str, Any] = {
                            "success": True,
                            "turns": num_turns,
                            "cost_usd": total_cost_usd,
                            "session_id": session_id,
                            "transcript_b64": transcript_b64,  # Include transcript for server storage
                            "stop_reason": stop_reason,
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "cache_read_tokens": cache_read_tokens,
                            "cache_write_tokens": cache_write_tokens,
                            "final_output": "\n".join(final_output)
                            if final_output
                            else None,  # Include final output for task result
                            # Include branch name for validation workflow
                            "branch_name": self.config.branch_name
                            if self.config.branch_name
                            else None,
                            # Include agent type for proper event handling (validator vs implementer)
                            "agent_type": self.config.agent_type,
                        }

                        # Include validation/iteration state for artifact generation
                        if self.iteration_state:
                            state = self.iteration_state
                            completion_event.update(
                                {
                                    "validation_passed": state.validation_passed,
                                    "tests_passed": state.tests_passed,
                                    "code_committed": state.code_committed,
                                    "code_pushed": state.code_pushed,
                                    "pr_created": state.pr_created,
                                    "pr_url": state.pr_url,
                                    "pr_number": state.pr_number,
                                    "files_changed": state.files_changed,
                                    "ci_status": state.ci_status,
                                }
                            )

                        # Try to report completion with retries (critical for task finalization)
                        max_retries = 3
                        retry_delay: float = 1.0
                        reported = False

                        for attempt in range(max_retries):
                            reported: bool = await self.reporter.report(
                                "agent.completed",
                                completion_event,
                            )
                            if reported:
                                break
                            if attempt < max_retries - 1:
                                logger.warning(
                                    "Retrying completion event",
                                    extra={
                                        "attempt": attempt + 1,
                                        "max_retries": max_retries,
                                    },
                                )
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff

                        if not reported:
                            logger.warning(
                                "Failed to report completion after retries - task status may not update"
                            )
                    logger.info(
                        "Agent completed",
                        extra={"turns": num_turns, "cost_usd": total_cost_usd},
                    )
                    return msg, final_output

        except Exception as e:
            error_str = str(e)
            error_type = "unknown"

            # Detect specific error types
            if "exit code -9" in error_str or "SIGKILL" in error_str:
                error_type = "sigkill"
                logger.error(
                    "Stream error: Process killed (SIGKILL/exit -9)",
                    extra={
                        "possible_causes": [
                            "OOM killer",
                            "Resource limits exceeded",
                            "Process timeout",
                            "System resource constraints",
                        ]
                    },
                )
            elif "Command failed" in error_str:
                error_type = "command_failed"
                logger.error(
                    "Stream error: Command failed in message reader",
                    extra={"error": error_str},
                )
            else:
                logger.error("Stream error", extra={"error": str(e)})

            if self.reporter:
                await self.reporter.report(
                    "agent.stream_error",
                    {
                        "error": error_str,
                        "error_type": error_type,
                        "turn": self.turn_count,
                        "final_output_length": len("\n".join(final_output))
                        if final_output
                        else 0,
                    },
                )

            # If we have partial output, return it instead of None
            if final_output:
                logger.warning(
                    "Returning partial output", extra={"block_count": len(final_output)}
                )

        return None, final_output

    # =========================================================================
    # Continuous Mode Helper Methods
    # =========================================================================

    def _should_continue_iteration(self) -> bool:
        """Check if iteration should continue in continuous mode."""
        import time

        state = self.iteration_state
        config = self.config

        # Check if validation already passed
        if state.validation_passed:
            return False

        # Check completion signal threshold
        if state.completion_signal_count >= config.completion_threshold:
            # Only stop if validation passed
            if not state.validation_passed:
                # Continue to allow agent to fix issues
                logger.info(
                    "Completion signal reached but validation not passed - continuing"
                )
                state.completion_signal_count = 0  # Reset to allow more iterations
            else:
                return False

        # Check max iterations
        if state.successful_iterations >= config.max_iterations:
            return False

        # Check max cost
        if state.total_cost >= config.max_total_cost_usd:
            return False

        # Check max duration
        if state.start_time:
            elapsed = time.time() - state.start_time
            if elapsed >= config.max_duration_seconds:
                return False

        # Check consecutive errors
        if state.error_count >= config.max_consecutive_errors:
            return False

        # Check shutdown signal
        if self._should_stop:
            return False

        return True

    def _get_stop_reason(self) -> str:
        """Determine why the iteration loop stopped."""
        import time

        state = self.iteration_state
        config = self.config

        if state.validation_passed:
            return "validation_passed"
        if state.completion_signal_count >= config.completion_threshold:
            return "completion_signal"
        if state.successful_iterations >= config.max_iterations:
            return "max_iterations_reached"
        if state.total_cost >= config.max_total_cost_usd:
            return "max_cost_reached"
        if state.start_time:
            elapsed = time.time() - state.start_time
            if elapsed >= config.max_duration_seconds:
                return "max_duration_reached"
        if state.error_count >= config.max_consecutive_errors:
            return "consecutive_errors"
        if self._should_stop:
            return "shutdown_signal"
        return "unknown"

    async def _run_validation(self):
        """Run git validation to check if work is truly complete.

        Handles two scenarios:
        1. Implementation tasks: Require clean git, code pushed, and PR created
        2. Research/analysis tasks: No code changes, so skip git validation

        Detection of research tasks:
        - Working directory is clean (no changes made)
        - Not ahead of remote (nothing to push)
        - On main/master branch (no feature branch created)
        - OR execution_mode is "exploration"
        """
        state = self.iteration_state
        config = self.config

        logger.info("Running git validation...")

        git_status = check_git_status(config.cwd)

        # Update state with validation results
        state.code_committed = git_status["is_clean"]
        state.code_pushed = git_status["is_pushed"]
        state.pr_created = git_status["has_pr"]
        state.tests_passed = git_status["tests_passed"]

        # Store additional PR info for artifact generation
        state.pr_url = git_status.get("pr_url")
        state.pr_number = git_status.get("pr_number")
        state.files_changed = git_status.get("files_changed", 0)
        state.ci_status = git_status.get("ci_status")

        # CRITICAL: Detect research/analysis tasks that don't produce code changes
        # These tasks should pass validation without requiring a PR
        # A task is "research only" if:
        # 1. Working directory is clean (no uncommitted changes)
        # 2. Not ahead of remote (nothing to push)
        # 3. On main/master branch (no feature branch was created)
        # This applies to ALL modes - if no files were created, no git workflow needed
        is_research_task = (
            # Clean working directory (no uncommitted changes)
            git_status["is_clean"]
            and
            # Not ahead of remote (nothing to push)
            git_status["is_pushed"]
            and
            # On main/master branch (no feature branch was created)
            git_status.get("branch_name") in ("main", "master", None)
        )

        # NOTE: exploration mode NO LONGER auto-passes validation
        # If exploration creates files (specs, PRDs, docs), it must push them
        # Only pure analysis with no file output passes without git workflow

        if is_research_task:
            logger.info(
                "Detected research/analysis task - no code changes needed",
                extra={
                    "branch": git_status.get("branch_name"),
                    "is_clean": git_status["is_clean"],
                    "is_pushed": git_status["is_pushed"],
                    "execution_mode": config.execution_mode,
                },
            )
            state.validation_passed = True
            state.validation_feedback = (
                "Research/analysis task completed - no code changes required"
            )

            # Report validation result for research task
            if self.reporter:
                await self.reporter.report(
                    "iteration.validation",
                    {
                        "iteration_num": state.iteration_num,
                        "passed": True,
                        "feedback": state.validation_feedback,
                        "task_type": "research",
                        "git_status": {
                            "is_clean": git_status["is_clean"],
                            "is_pushed": git_status["is_pushed"],
                            "has_pr": git_status["has_pr"],
                            "branch_name": git_status["branch_name"],
                        },
                        "errors": [],
                    },
                )
            return

        # Standard validation for implementation tasks
        validation_errors = []

        if config.require_clean_git and not git_status["is_clean"]:
            validation_errors.append("Uncommitted changes exist")

        if config.require_code_pushed and not git_status["is_pushed"]:
            validation_errors.append("Code not pushed to remote")

        if config.require_pr_created and not git_status["has_pr"]:
            validation_errors.append("No PR created")

        # Additional validation for spec-driven-dev skill
        # When REQUIRE_SPEC_SKILL is set, validate spec output format
        if config.require_spec_skill:
            logger.info("Running spec output validation (REQUIRE_SPEC_SKILL=true)...")
            spec_status = check_spec_output(config.cwd)

            if not spec_status["is_valid"]:
                validation_errors.extend(spec_status["errors"])
                logger.info(
                    "Spec validation FAILED",
                    extra={
                        "files_found": spec_status["files_found"],
                        "files_with_frontmatter": spec_status["files_with_frontmatter"],
                        "files_missing_frontmatter": spec_status[
                            "files_missing_frontmatter"
                        ],
                        "errors": spec_status["errors"],
                    },
                )
            else:
                logger.info(
                    "Spec validation PASSED",
                    extra={
                        "files_found": len(spec_status["files_found"]),
                        "files_with_frontmatter": len(
                            spec_status["files_with_frontmatter"]
                        ),
                    },
                )

        if not validation_errors:
            state.validation_passed = True
            state.validation_feedback = "All validation checks passed"
            logger.info("Git validation PASSED")
        else:
            state.validation_passed = False
            state.validation_feedback = "; ".join(validation_errors)
            logger.info("Validation FAILED", extra={"errors": validation_errors})

            # Update notes file with validation feedback for next iteration
            self._update_notes_with_validation(validation_errors, git_status)

        # Report validation result
        if self.reporter:
            await self.reporter.report(
                "iteration.validation",
                {
                    "iteration_num": state.iteration_num,
                    "passed": state.validation_passed,
                    "feedback": state.validation_feedback,
                    "git_status": {
                        "is_clean": git_status["is_clean"],
                        "is_pushed": git_status["is_pushed"],
                        "has_pr": git_status["has_pr"],
                        "branch_name": git_status["branch_name"],
                    },
                    "errors": validation_errors,
                },
            )

    def _update_notes_with_validation(self, errors: list[str], git_status: dict):
        """Update notes file with validation feedback for next iteration."""
        config = self.config
        notes_path = Path(config.cwd) / config.notes_file

        try:
            existing = notes_path.read_text() if notes_path.exists() else ""

            feedback_section = f"""

## VALIDATION FAILED - Iteration {self.iteration_state.iteration_num}

The completion signal was detected, but validation checks failed.
**You must fix these issues before the task is truly complete:**

### Issues Found:
"""
            for error in errors:
                feedback_section += f"- ❌ {error}\n"

            feedback_section += f"""
### Git Status:
- Branch: {git_status.get("branch_name", "unknown")}
- Clean working directory: {"✅ Yes" if git_status["is_clean"] else "❌ No"}
- Code pushed to remote: {"✅ Yes" if git_status["is_pushed"] else "❌ No"}
- PR exists: {"✅ Yes" if git_status["has_pr"] else "❌ No"}

### Required Actions:
"""
            if not git_status["is_clean"]:
                feedback_section += '1. Stage and commit all changes: `git add -A && git commit -m "..."`\n'
            if not git_status["is_pushed"]:
                feedback_section += "2. Push code to remote: `git push`\n"
            if not git_status["has_pr"]:
                feedback_section += '3. Create a pull request: `gh pr create --title "..." --body "..."`\n'

            feedback_section += f"""
**After fixing these issues, include `{config.completion_signal}` in your response again.**
"""

            notes_path.write_text(existing + feedback_section)
            logger.info("Updated notes file with validation feedback")

        except Exception as e:
            logger.warning(
                "Failed to update notes with validation feedback",
                extra={"error": str(e)},
            )

    def _build_iteration_prompt(self, base_task: str) -> str:
        """Build enhanced prompt with iteration context."""
        config = self.config
        state = self.iteration_state

        # Read notes file if exists
        notes_content = ""
        notes_path = Path(config.cwd) / config.notes_file
        if notes_path.exists():
            try:
                notes_content = notes_path.read_text()
            except Exception:
                pass

        # First iteration - return base task with completion instructions
        if state.iteration_num == 1:
            prompt = f"""{base_task}

---

## Completion Requirements (IMPORTANT)

When you have completed the task, you MUST:
1. Ensure all tests pass
2. Commit all changes: `git add -A && git commit -m "..."`
3. Push to remote: `git push`
4. Create a PR: `gh pr create --title "..." --body "..."`

**When all work is done and pushed, include the phrase `{config.completion_signal}` in your response.**
"""
            return prompt

        # Subsequent iterations - include notes file and previous context
        prompt = f"""## Continuing Task (Iteration {state.iteration_num})

This is a continuation of your previous work. Please review the notes below and complete any remaining work.

### Original Task:
{base_task}

### Previous Iteration Notes:
{notes_content if notes_content else "(No notes from previous iterations)"}

### Current Status:
- Iterations completed: {state.successful_iterations}
- Validation passed: {state.validation_passed}
- Code committed: {state.code_committed}
- Code pushed: {state.code_pushed}
- PR created: {state.pr_created}

### What to do:
1. Review the validation feedback above (if any)
2. Fix any issues identified
3. Ensure all work is committed, pushed, and a PR exists
4. Include `{config.completion_signal}` when truly done
"""
        return prompt

    async def run(self):
        """Main worker loop with comprehensive event tracking."""
        self._setup_signal_handlers()
        self.running = True

        logger.info("=" * 60)
        logger.info("CLAUDE SANDBOX WORKER (Production)")
        logger.info("=" * 60)
        logger.info("Configuration: %s", self.config.to_dict())

        # Validate config
        errors = self.config.validate()
        if errors:
            logger.error("Configuration errors", extra={"errors": errors})
            return 1

        if not SDK_AVAILABLE:
            logger.error(
                "claude_agent_sdk package not installed - Run: pip install claude-agent-sdk"
            )
            return 1

        # Setup workspace
        Path(self.config.cwd).mkdir(parents=True, exist_ok=True)
        setup_github_workspace(self.config)

        # Auto-install project dependencies (UV, Poetry, pip, pnpm, yarn, npm)
        # This runs BEFORE the agent starts to ensure dependencies are available
        dep_result = install_project_dependencies(self.config.cwd)
        if dep_result["errors"]:
            logger.warning(
                "Some dependency installation errors occurred",
                extra={"errors": dep_result["errors"]}
            )

        # Add dependency status to system prompt so agent knows what's installed
        if dep_result["summary"]:
            dep_prompt_section = f"""
## Pre-Installed Dependencies

The following dependencies were automatically installed before you started:

{dep_result["summary"]}

**Do NOT re-run dependency installation commands** unless you encounter errors or need to add new packages.
"""
            self.config.system_prompt = self.config.system_prompt + "\n" + dep_prompt_section
            logger.info("Added dependency status to system prompt")

        # Import session transcript if provided (for cross-sandbox resumption)
        if self.config.session_transcript_b64 and self.config.resume_session_id:
            logger.info("Importing session transcript for cross-sandbox resumption")
            if self.config.import_session_transcript():
                logger.info("Session transcript imported successfully")
            else:
                logger.warning("Session transcript import failed, starting fresh")
                self.config.resume_session_id = None  # Reset to avoid resume failure

        async with EventReporter(self.config) as reporter:
            self.reporter = reporter

            # Collect stderr lines for error reporting
            cli_stderr_lines = []

            def stderr_collector(line: str):
                """Collect CLI stderr output for debugging.

                This captures stderr from the Claude CLI subprocess.
                Critical for diagnosing initialization failures.
                """
                stripped = line.strip()
                if stripped:
                    cli_stderr_lines.append(stripped)
                    # Log immediately at WARNING level so we see it
                    logger.warning("CLI stderr: %s", stripped)

            async with MessagePoller(self.config) as poller:
                # Create hooks and options
                pre_tool_hook = await self._create_pre_tool_hook()
                post_tool_hook = await self._create_post_tool_hook()
                sdk_options = self.config.to_sdk_options(
                    pre_tool_hook=pre_tool_hook,
                    post_tool_hook=post_tool_hook,
                    stderr_callback=stderr_collector,
                )

                # Report startup
                await reporter.report(
                    "agent.started",
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sdk": "claude_agent_sdk",
                        "model": self.config.model or "default",
                        "task": self.config.task_description
                        or self.config.initial_prompt
                        or self.config.ticket_description,
                        "task_description_length": len(self.config.task_description),
                        "ticket_title": self.config.ticket_title,
                        "resumed_session_id": self.config.resume_session_id,
                        "is_resuming": bool(self.config.resume_session_id),
                        "fork_session": self.config.fork_session,
                    },
                    source="worker",
                )

                try:
                    # Debug: Log options structure before creating client
                    logger.debug("Creating SDK client with options")
                    logger.debug(
                        "SDK options type",
                        extra={"options_type": str(type(sdk_options))},
                    )
                    if hasattr(sdk_options, "hooks") and sdk_options.hooks:
                        logger.debug(
                            "Hooks present in SDK options",
                            extra={"hooks": list(sdk_options.hooks.keys())},
                        )

                    async with ClaudeSDKClient(options=sdk_options) as client:
                        # Process initial prompt
                        # Priority: task_description (from TASK_DATA_BASE64) > initial_prompt > ticket_description > ticket_title
                        initial_task = (
                            self.config.task_description  # Full task spec from orchestrator
                            or self.config.initial_prompt
                            or self.config.ticket_description
                            or f"Analyze ticket: {self.config.ticket_title}"
                        )

                        if initial_task and initial_task.strip():
                            # Initialize iteration state
                            import time

                            self.iteration_state.start_time = time.time()

                            # Log mode decision for debugging
                            logger.info(
                                "WORKER RUN: Mode decision point",
                                extra={
                                    "continuous_mode": self.config.continuous_mode,
                                    "execution_mode": self.config.execution_mode,
                                    "task_id": self.config.task_id,
                                    "initial_task_preview": initial_task[:200],
                                },
                            )

                            if self.config.continuous_mode:
                                # =================================================
                                # CONTINUOUS MODE: Iterate until task truly completes
                                # =================================================
                                logger.info("=" * 60)
                                logger.info("WORKER RUN: CONTINUOUS MODE ACTIVATED")
                                logger.info("=" * 60)
                                logger.info(
                                    "Will iterate until: validation_passed OR max_iterations=%d OR max_cost=$%.2f OR max_duration=%ds",
                                    self.config.max_iterations,
                                    self.config.max_total_cost_usd,
                                    self.config.max_duration_seconds,
                                )

                                # Report continuous mode start
                                await reporter.report(
                                    "continuous.started",
                                    {
                                        "goal": initial_task[:500],
                                        "limits": {
                                            "max_iterations": self.config.max_iterations,
                                            "max_cost_usd": self.config.max_total_cost_usd,
                                            "max_duration_seconds": self.config.max_duration_seconds,
                                        },
                                        "completion_signal": self.config.completion_signal,
                                        "completion_threshold": self.config.completion_threshold,
                                        "validation_requirements": {
                                            "require_clean_git": self.config.require_clean_git,
                                            "require_code_pushed": self.config.require_code_pushed,
                                            "require_pr_created": self.config.require_pr_created,
                                        },
                                    },
                                    source="worker",
                                )

                                # Iteration loop
                                while self._should_continue_iteration():
                                    self.iteration_state.iteration_num += 1
                                    iteration_prompt = self._build_iteration_prompt(
                                        initial_task
                                    )

                                    # Report iteration start
                                    await reporter.report(
                                        "iteration.started",
                                        {
                                            "iteration_num": self.iteration_state.iteration_num,
                                            "prompt_preview": iteration_prompt[:500],
                                            **self.iteration_state.to_event_data(),
                                        },
                                    )

                                    logger.info(
                                        "Starting iteration %d",
                                        self.iteration_state.iteration_num,
                                        extra={
                                            "state": self.iteration_state.to_event_data()
                                        },
                                    )

                                    try:
                                        await client.query(iteration_prompt)
                                        result, output = await self._process_messages(
                                            client
                                        )

                                        if result:
                                            # Track cost
                                            iteration_cost = (
                                                getattr(result, "total_cost_usd", 0.0)
                                                or 0.0
                                            )
                                            self.iteration_state.total_cost += (
                                                iteration_cost
                                            )
                                            self.iteration_state.last_session_id = (
                                                getattr(result, "session_id", None)
                                            )

                                            # Check for completion signal in output
                                            output_text = (
                                                "\n".join(output) if output else ""
                                            )
                                            if (
                                                self.config.completion_signal
                                                in output_text
                                            ):
                                                self.iteration_state.completion_signal_count += 1
                                                logger.info(
                                                    "Completion signal detected (%d/%d)",
                                                    self.iteration_state.completion_signal_count,
                                                    self.config.completion_threshold,
                                                )

                                                await reporter.report(
                                                    "iteration.completion_signal",
                                                    {
                                                        "iteration_num": self.iteration_state.iteration_num,
                                                        "signal_count": self.iteration_state.completion_signal_count,
                                                        "threshold": self.config.completion_threshold,
                                                    },
                                                )

                                                # Run git validation
                                                await self._run_validation()

                                                # If validation passed, we're done!
                                                if self.iteration_state.validation_passed:
                                                    logger.info(
                                                        "Validation PASSED - task truly complete!"
                                                    )
                                                    break
                                            else:
                                                # No completion signal - reset counter
                                                self.iteration_state.completion_signal_count = 0

                                            self.iteration_state.successful_iterations += 1
                                            self.iteration_state.error_count = 0

                                            # Report iteration completion
                                            await reporter.report(
                                                "iteration.completed",
                                                {
                                                    "iteration_num": self.iteration_state.iteration_num,
                                                    "cost_usd": iteration_cost,
                                                    "output_preview": output_text[:1000]
                                                    if output_text
                                                    else None,
                                                    **self.iteration_state.to_event_data(),
                                                },
                                            )
                                        else:
                                            # No result - iteration failed
                                            self.iteration_state.error_count += 1
                                            await reporter.report(
                                                "iteration.failed",
                                                {
                                                    "iteration_num": self.iteration_state.iteration_num,
                                                    "error": "No result message received",
                                                    "error_count": self.iteration_state.error_count,
                                                },
                                            )

                                    except Exception as e:
                                        self.iteration_state.error_count += 1
                                        logger.error(
                                            "Iteration %d failed",
                                            self.iteration_state.iteration_num,
                                            extra={"error": str(e)},
                                            exc_info=True,
                                        )
                                        await reporter.report(
                                            "iteration.failed",
                                            {
                                                "iteration_num": self.iteration_state.iteration_num,
                                                "error": str(e),
                                                "error_type": type(e).__name__,
                                                "error_count": self.iteration_state.error_count,
                                            },
                                        )

                                # Report continuous mode completion
                                stop_reason = self._get_stop_reason()
                                await reporter.report(
                                    "continuous.completed",
                                    {
                                        "stop_reason": stop_reason,
                                        **self.iteration_state.to_event_data(),
                                    },
                                )

                                logger.info(
                                    "Continuous mode completed",
                                    extra={
                                        "stop_reason": stop_reason,
                                        "iterations": self.iteration_state.iteration_num,
                                        "successful": self.iteration_state.successful_iterations,
                                        "total_cost": self.iteration_state.total_cost,
                                        "validation_passed": self.iteration_state.validation_passed,
                                    },
                                )

                            else:
                                # =================================================
                                # SINGLE-RUN MODE: Execute once (original behavior)
                                # =================================================
                                logger.info("=" * 60)
                                logger.info(
                                    "WORKER RUN: SINGLE-RUN MODE (no iteration)"
                                )
                                logger.info("=" * 60)
                                logger.info(
                                    "WORKER RUN: Single-run mode - task will execute ONCE only",
                                    extra={
                                        "execution_mode": self.config.execution_mode,
                                        "task_id": self.config.task_id,
                                        "continuous_mode": self.config.continuous_mode,
                                        "task_preview": initial_task[:200],
                                    },
                                )
                                try:
                                    await client.query(initial_task)
                                    await self._process_messages(client)
                                except Exception as e:
                                    logger.error(
                                        "Failed to process initial task",
                                        extra={"error": str(e)},
                                        exc_info=True,
                                    )
                                    if self.reporter:
                                        await self.reporter.report(
                                            "agent.error",
                                            {
                                                "error": f"Initial task failed: {str(e)}",
                                                "phase": "initial_task",
                                            },
                                        )
                        else:
                            logger.warning(
                                "No initial task provided - worker will wait for messages"
                            )

                        # Report ready
                        await reporter.report(
                            "agent.waiting",
                            {"message": "Ready for messages"},
                        )
                        logger.info("Waiting for messages")

                        # Main loop
                        last_heartbeat = asyncio.get_event_loop().time()
                        intervention_count = 0

                        while not self._shutdown_event.is_set():
                            try:
                                # Check for stop
                                if self._should_stop:
                                    await client.interrupt()
                                    await reporter.report(
                                        "agent.interrupted",
                                        {
                                            "reason": "shutdown_signal",
                                            "turn": self.turn_count,
                                        },
                                    )
                                    break

                                # Poll for messages
                                messages = await poller.poll()

                                for msg in messages:
                                    intervention_count += 1
                                    content = msg.get("content", "")
                                    msg_type = msg.get("message_type", "user_message")
                                    sender_id = msg.get("sender_id")
                                    message_id = msg.get("message_id")

                                    if not content:
                                        continue

                                    logger.info(
                                        "Received message",
                                        extra={
                                            "msg_type": msg_type,
                                            "content_preview": content[:80],
                                        },
                                    )

                                    # Handle interrupt
                                    if msg_type == "interrupt":
                                        self._should_stop = True
                                        await client.interrupt()
                                        await reporter.report(
                                            "agent.interrupted",
                                            {
                                                "reason": content,
                                                "sender_id": sender_id,
                                                "turn": self.turn_count,
                                            },
                                        )
                                        break

                                    # Report message injection
                                    await reporter.report(
                                        "agent.message_injected",
                                        {
                                            "message_type": msg_type,
                                            "content": content,  # Full content
                                            "content_length": len(content),
                                            "sender_id": sender_id,
                                            "message_id": message_id,
                                            "intervention_number": intervention_count,
                                            "turn": self.turn_count,
                                        },
                                    )

                                    # Process message
                                    try:
                                        await client.query(content)
                                        await self._process_messages(client)
                                    except Exception as e:
                                        logger.error(
                                            "Failed to process message",
                                            extra={"error": str(e)},
                                            exc_info=True,
                                        )
                                        if self.reporter:
                                            await self.reporter.report(
                                                "agent.error",
                                                {
                                                    "error": f"Message processing failed: {str(e)}",
                                                    "message_type": msg_type,
                                                    "content_length": len(content),
                                                },
                                            )

                                    # Report ready
                                    await reporter.report(
                                        "agent.waiting",
                                        {"message": "Ready for messages"},
                                    )

                                # Heartbeat
                                now = asyncio.get_event_loop().time()
                                if (
                                    now - last_heartbeat
                                    >= self.config.heartbeat_interval
                                ):
                                    await reporter.heartbeat()
                                    last_heartbeat = now

                                await asyncio.sleep(self.config.poll_interval)

                            except asyncio.CancelledError:
                                break
                            except Exception as e:
                                logger.error(
                                    "Main loop error",
                                    extra={"error": str(e)},
                                    exc_info=True,
                                )
                                await reporter.report("agent.error", {"error": str(e)})
                                await asyncio.sleep(1)

                except Exception as e:
                    import traceback

                    logger.error(
                        "SDK initialization error",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "traceback": traceback.format_exc(),
                        },
                        exc_info=True,
                    )

                    # Try to identify what's causing the asdict() error
                    if "asdict()" in str(e):
                        debug_info = {"options_type": str(type(sdk_options))}
                        if hasattr(sdk_options, "__dict__"):
                            debug_info["options_keys"] = list(
                                sdk_options.__dict__.keys()
                            )
                            if hasattr(sdk_options, "hooks"):
                                debug_info["hooks_type"] = str(type(sdk_options.hooks))
                                if sdk_options.hooks:
                                    hooks_debug = {}
                                    for (
                                        hook_type,
                                        hook_list,
                                    ) in sdk_options.hooks.items():
                                        hooks_debug[hook_type] = {
                                            "type": str(type(hook_list)),
                                            "length": len(hook_list)
                                            if isinstance(hook_list, list)
                                            else "N/A",
                                        }
                                        if isinstance(hook_list, list) and hook_list:
                                            hooks_debug[hook_type][
                                                "first_item_type"
                                            ] = str(type(hook_list[0]))
                                    debug_info["hooks"] = hooks_debug
                        logger.debug(
                            "asdict() error - options structure debug", extra=debug_info
                        )

                    await reporter.report(
                        "agent.error",
                        {
                            "error": str(e),
                            "phase": "initialization",
                            "traceback": traceback.format_exc(),
                        },
                    )
                    return 1

                # Shutdown
                await reporter.report(
                    "agent.shutdown",
                    {
                        "reason": "complete",
                        "total_turns": self.turn_count,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    source="worker",
                )
                logger.info(
                    "Worker shutdown complete", extra={"total_turns": self.turn_count}
                )

        return 0


# =============================================================================
# Entry Point
# =============================================================================


async def main():
    config = WorkerConfig()
    worker = SandboxWorker(config)
    return await worker.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
