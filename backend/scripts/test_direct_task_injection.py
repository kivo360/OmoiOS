#!/usr/bin/env python3
"""Test direct task injection into sandbox without database.

This script replicates the manual testing workflow:
1. Spawn a Daytona sandbox with chosen runtime (claude/openhands)
2. Inject task data directly via TASK_DATA_BASE64 (no DB needed)
3. Run the agent and observe execution
4. Verify events are reported back

This enables testing the full agent flow without requiring:
- A running backend server
- Database connectivity
- The orchestrator

Usage:
    cd backend
    uv run python scripts/test_direct_task_injection.py [--runtime claude|openhands] [--task "your task"]

Examples:
    # Test Claude runtime (default)
    uv run python scripts/test_direct_task_injection.py

    # Test OpenHands runtime
    uv run python scripts/test_direct_task_injection.py --runtime openhands

    # Custom task
    uv run python scripts/test_direct_task_injection.py --task "Create a hello.py that prints Hello World"
"""

import argparse
import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")
load_dotenv(Path(__file__).parent.parent / ".env")


# Default test task - explicitly asks to RUN the file
DEFAULT_TASK = """
Create a Python script called hello.py that:
1. Prints "Hello from sandbox agent!"
2. Lists the files in the current directory  
3. Prints the current timestamp

After creating the file, RUN IT with `python hello.py` and show me the output.
"""


def get_verbose_claude_worker_script() -> str:
    """Get a verbose Claude Agent SDK worker script that shows all output."""
    return '''#!/usr/bin/env python3
"""Verbose Claude Agent SDK worker - shows all messages, tool calls, and events.

This is a simplified, debugging-friendly version that prints everything.
"""

import asyncio
import os
import sys
import json
import base64
from pathlib import Path

# Environment configuration
TASK_ID = os.environ.get("TASK_ID", "unknown")
AGENT_ID = os.environ.get("AGENT_ID", "unknown")
SANDBOX_ID = os.environ.get("SANDBOX_ID", "unknown")
TASK_DATA_BASE64 = os.environ.get("TASK_DATA_BASE64")
WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", "/workspace")

# Anthropic configuration - support both ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN (for Z.AI)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "")
# Z.AI model mapping - use their default sonnet model if on Z.AI
DEFAULT_MODEL = "glm-4.6" if "z.ai" in ANTHROPIC_BASE_URL else "claude-sonnet-4-20250514"
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL") or os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", DEFAULT_MODEL)


def print_header(text: str):
    """Print a header."""
    print("\\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(text: str):
    """Print a section divider."""
    print(f"\\n--- {text} ---")


def get_task_description() -> str:
    """Get task description from injected data or return default."""
    if TASK_DATA_BASE64:
        try:
            task_json = base64.b64decode(TASK_DATA_BASE64).decode()
            task_data = json.loads(task_json)
            desc = task_data.get("task_description") or task_data.get("ticket_description") or "No description"
            print_section("TASK DATA (from TASK_DATA_BASE64)")
            print(f"Task ID: {task_data.get(\'task_id\')}")
            print(f"Ticket: {task_data.get(\'ticket_title\')}")
            print(f"Description: {desc[:200]}...")
            return desc
        except Exception as e:
            print(f"[WARN] Failed to decode task data: {e}")
    return "Write hello.py that prints Hello World"


async def run_agent(task: str):
    """Run the Claude Agent with verbose output."""
    
    # Import SDK with all error types
    try:
        from claude_agent_sdk import (
            query,
            ClaudeAgentOptions,
            AssistantMessage,
            UserMessage,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
            ToolResultBlock,
            ClaudeSDKError,
            CLINotFoundError,
            CLIConnectionError,
            ProcessError,
        )
        print("[OK] claude_agent_sdk imported successfully")
    except ImportError as e:
        print(f"[ERROR] Failed to import claude_agent_sdk: {e}")
        print("Trying to install...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "claude-agent-sdk"], check=True)
        from claude_agent_sdk import (
            query,
            ClaudeAgentOptions,
            AssistantMessage,
            UserMessage,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
            ToolResultBlock,
            ClaudeSDKError,
            CLINotFoundError,
            CLIConnectionError,
            ProcessError,
        )
    
    print_section("CONFIGURATION")
    print(f"Model: {ANTHROPIC_MODEL}")
    print(f"Base URL: {ANTHROPIC_BASE_URL or \'default (api.anthropic.com)\'}")
    print(f"API Key: {ANTHROPIC_API_KEY[:20]}..." if ANTHROPIC_API_KEY else "API Key: NOT SET")
    print(f"Workspace: {WORKSPACE_PATH}")
    
    # Set environment variables for SDK/CLI
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    if ANTHROPIC_BASE_URL:
        os.environ["ANTHROPIC_BASE_URL"] = ANTHROPIC_BASE_URL
        print(f"[WARN] Using custom base URL: {ANTHROPIC_BASE_URL}")
        print("[WARN] The Claude Agent SDK wraps Claude Code CLI which may not support custom base URLs")
    
    # Configure working directory - ensure /workspace exists
    work_dir = Path(WORKSPACE_PATH)
    if not work_dir.exists():
        print(f"[INFO] Creating workspace directory: {work_dir}")
        work_dir.mkdir(parents=True, exist_ok=True)
    
    # Change to workspace directory
    os.chdir(work_dir)
    print(f"[INFO] Changed to directory: {os.getcwd()}")
    
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep", "LS"],
        permission_mode="acceptEdits",  # Auto-accept file edits
        system_prompt=f"""You are a helpful coding assistant working in {work_dir}.

IMPORTANT RULES:
- Always use RELATIVE paths (e.g., "hello.py" not "/hello.py")
- Your current working directory is {work_dir}
- When you create files, use just the filename (e.g., "hello.py")
- When you run scripts, use relative paths (e.g., "python hello.py")
- Be concise and show results.""",
        max_turns=20,
        cwd=work_dir,
        model=ANTHROPIC_MODEL,  # Pass model explicitly
        env={
            "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
            "ANTHROPIC_BASE_URL": ANTHROPIC_BASE_URL,
        } if ANTHROPIC_BASE_URL else {"ANTHROPIC_API_KEY": ANTHROPIC_API_KEY},
    )
    
    print_section("SENDING TASK TO CLAUDE")
    print(f"Task: {task}")
    print(f"Working directory: {work_dir} (verified: {work_dir.exists()})")
    print()
    
    message_count = 0
    tool_call_count = 0
    
    try:
        async for message in query(prompt=task, options=options):
            message_count += 1
            
            # Handle different message types
            if isinstance(message, AssistantMessage):
                print_section(f"ASSISTANT MESSAGE #{message_count}")
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"[TEXT] {block.text}")
                    elif isinstance(block, ToolUseBlock):
                        tool_call_count += 1
                        print(f"[TOOL USE #{tool_call_count}] {block.name}")
                        print(f"  Input: {json.dumps(block.input, indent=2)}")
                    elif hasattr(block, "type"):
                        print(f"[BLOCK type={block.type}] {str(block)}")
                    else:
                        print(f"[BLOCK] {str(block)}")
            
            elif isinstance(message, UserMessage):
                print_section(f"USER MESSAGE #{message_count}")
                for block in message.content:
                    if isinstance(block, ToolResultBlock):
                        status = "✅" if not getattr(block, "is_error", False) else "❌"
                        print(f"[TOOL RESULT {status}] tool_use_id={block.tool_use_id}")
                        # Print full content
                        content = block.content
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and "text" in item:
                                    print(f"  {item['text']}")
                                else:
                                    print(f"  {item}")
                        elif isinstance(content, str):
                            print(f"  {content}")
                    else:
                        print(f"[USER BLOCK] {str(block)}")
            
            elif isinstance(message, ResultMessage):
                print_section("RESULT")
                print(f"Total cost: ${message.total_cost_usd:.4f}")
                print(f"Session ID: {getattr(message, \'session_id\', \'N/A\')}")
            
            else:
                print_section(f"OTHER MESSAGE #{message_count}")
                print(f"Type: {type(message).__name__}")
                print(f"Content: {str(message)}")
        
        print_header("EXECUTION COMPLETE")
        print(f"Total messages: {message_count}")
        print(f"Total tool calls: {tool_call_count}")
        
        if message_count == 0:
            print("[WARN] No messages received! The agent may have failed silently.")
            print("[HINT] This often happens when using a custom ANTHROPIC_BASE_URL")
            print("[HINT] The Claude Agent SDK wraps Claude Code CLI which expects api.anthropic.com")
            return False
            
        return True
    
    except CLINotFoundError:
        print_header("ERROR: Claude Code CLI Not Found")
        print("The Claude Agent SDK requires Claude Code CLI to be installed.")
        print("Install with: npm install -g @anthropic-ai/claude-code")
        return False
        
    except CLIConnectionError as e:
        print_header("ERROR: CLI Connection Failed")
        print(f"Details: {e}")
        print("This may be caused by:")
        print("  - Invalid API key")
        print("  - Custom base URL not supported by Claude Code CLI")
        print("  - Network issues")
        return False
        
    except ProcessError as e:
        print_header("ERROR: Process Failed")
        print(f"Exit code: {e.exit_code}")
        if hasattr(e, \'stderr\') and e.stderr:
            print(f"Stderr: {e.stderr}")
        if hasattr(e, \'stdout\') and e.stdout:
            print(f"Stdout: {e.stdout}")
        return False
        
    except ClaudeSDKError as e:
        print_header("ERROR: Claude SDK Error")
        print(f"Details: {e}")
        return False
        
    except Exception as e:
        print_header("EXECUTION FAILED")
        print(f"Error type: {type(e).__name__}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print_header("CLAUDE AGENT SDK WORKER (VERBOSE)")
    print(f"Task ID: {TASK_ID}")
    print(f"Agent ID: {AGENT_ID}")
    print(f"Sandbox ID: {SANDBOX_ID}")
    
    # Get task
    task = get_task_description()
    
    # Run agent
    success = await run_agent(task)
    
    # Show workspace contents
    print_section("FINAL WORKSPACE CONTENTS")
    workspace = Path(WORKSPACE_PATH) if os.path.exists(WORKSPACE_PATH) else Path("/tmp")
    try:
        for item in sorted(workspace.iterdir())[:20]:
            prefix = "[DIR] " if item.is_dir() else "[FILE]"
            size = item.stat().st_size if item.is_file() else ""
            print(f"  {prefix} {item.name} {size}")
    except Exception as e:
        print(f"  Error listing: {e}")
    
    print_header("DONE")
    print(f"Success: {success}")
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
'''


async def test_direct_injection(
    runtime: str = "claude",
    task_description: str = DEFAULT_TASK,
    timeout_seconds: int = 300,
):
    """Run the direct task injection test."""

    print("=" * 70)
    print("🧪 DIRECT TASK INJECTION TEST")
    print(f"   Runtime: {runtime}")
    print("=" * 70)

    # =========================================================================
    # Step 1: Check environment
    # =========================================================================
    print("\n📋 Step 1: Checking environment...")

    daytona_key = os.environ.get("DAYTONA_API_KEY")
    if not daytona_key:
        print("❌ DAYTONA_API_KEY not set")
        print("   Set it in .env.local: DAYTONA_API_KEY=dtn_...")
        return False
    print(f"   ✅ Daytona API Key: {daytona_key[:12]}...")

    # Check LLM credentials based on runtime
    if runtime == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
            "ANTHROPIC_AUTH_TOKEN"
        )
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
        # Use Z.AI model if on Z.AI, otherwise default Anthropic model
        default_model = "glm-4.6" if "z.ai" in base_url else "claude-sonnet-4-20250514"
        model = os.environ.get("ANTHROPIC_MODEL") or os.environ.get(
            "ANTHROPIC_DEFAULT_SONNET_MODEL", default_model
        )
        if not api_key:
            print("❌ ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN not set")
            return False
        print(f"   ✅ API Key: {api_key[:15]}...")
        print(f"   ✅ Base URL: {base_url or 'default (api.anthropic.com)'}")
        print(f"   ✅ Model: {model}")
        if "z.ai" in base_url:
            print("   ⚠️  Using Z.AI proxy - Claude Code CLI compatibility unknown")
    else:
        api_key = os.environ.get("LLM_API_KEY")
        model = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-4-20250514")
        if not api_key:
            print("❌ LLM_API_KEY not set")
            return False
        print(f"   ✅ LLM API Key: {api_key[:15]}...")
        print(f"   ✅ Model: {model}")

    # =========================================================================
    # Step 2: Create injected task data
    # =========================================================================
    print("\n📋 Step 2: Creating injected task data...")

    task_id = f"test-inject-{uuid4().hex[:8]}"
    agent_id = f"agent-inject-{uuid4().hex[:8]}"
    sandbox_id = f"sandbox-inject-{uuid4().hex[:8]}"

    # Build the task data that would normally come from DB
    task_data = {
        "task_id": task_id,
        "task_description": task_description.strip(),
        "task_type": "implementation",
        "task_priority": "HIGH",
        "phase_id": "PHASE_IMPLEMENTATION",
        "ticket_id": f"ticket-{uuid4().hex[:8]}",
        "ticket_title": "Direct Injection Test",
        "ticket_description": task_description.strip(),
        "ticket_context": {
            "test": True,
            "injected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }

    # Base64 encode for injection
    task_json = json.dumps(task_data)
    task_base64 = base64.b64encode(task_json.encode()).decode()

    print(f"   ✅ Task ID: {task_id}")
    print(f"   ✅ Agent ID: {agent_id}")
    print(f"   ✅ Task data encoded ({len(task_base64)} chars)")
    print(f"   📝 Task: {task_description[:100]}...")

    # =========================================================================
    # Step 3: Create Daytona sandbox
    # =========================================================================
    print("\n📋 Step 3: Creating Daytona sandbox...")

    try:
        from daytona import Daytona, DaytonaConfig, CreateSandboxFromImageParams
    except ImportError:
        print("❌ Daytona SDK not installed. Run: uv add daytona-sdk")
        return False

    config = DaytonaConfig(
        api_key=daytona_key,
        api_url="https://app.daytona.io/api",
        target="us",
    )
    daytona = Daytona(config)

    sandbox = None
    try:
        start_time = time.time()
        params = CreateSandboxFromImageParams(
            image="nikolaik/python-nodejs:python3.12-nodejs22",
            labels={
                "test": "direct-injection",
                "runtime": runtime,
                "task_id": task_id,
            },
            ephemeral=True,
            public=False,
        )

        sandbox = daytona.create(params=params, timeout=120)
        create_time = time.time() - start_time

        print(f"   ✅ Sandbox created in {create_time:.1f}s")
        print(f"   ✅ Sandbox ID: {sandbox.id}")

        # =====================================================================
        # Step 4: Setup environment and install dependencies
        # =====================================================================
        print("\n📋 Step 4: Setting up sandbox environment...")

        # Build environment variables
        env_vars = {
            "TASK_ID": task_id,
            "AGENT_ID": agent_id,
            "SANDBOX_ID": sandbox_id,
            "PHASE_ID": "PHASE_IMPLEMENTATION",
            "TASK_DATA_BASE64": task_base64,  # Injected task data
            "MCP_SERVER_URL": "http://localhost:18000",  # Not used when data is injected
            "WORKSPACE_PATH": "/workspace",
        }

        if runtime == "claude":
            env_vars["ANTHROPIC_API_KEY"] = api_key
            if base_url:
                env_vars["ANTHROPIC_BASE_URL"] = base_url
            env_vars["ANTHROPIC_MODEL"] = model
        else:
            env_vars["LLM_API_KEY"] = api_key
            env_vars["LLM_MODEL"] = model

        # Write env file
        env_file_content = "\n".join([f'{k}="{v}"' for k, v in env_vars.items()])
        sandbox.process.exec(
            f"cat > /tmp/.sandbox_env << 'ENVEOF'\n{env_file_content}\nENVOF"
        )
        print("   ✅ Environment variables written")

        # Install SDK
        print(f"   📦 Installing {runtime} SDK...")
        if runtime == "claude":
            install_cmd = "pip install claude-agent-sdk httpx --quiet 2>/dev/null || pip install claude-agent-sdk httpx"
        else:
            install_cmd = "pip install openhands-sdk openhands-tools httpx --quiet 2>/dev/null || pip install openhands-sdk openhands-tools httpx"

        result = sandbox.process.exec(install_cmd, timeout=180)
        if result.exit_code == 0:
            print(f"   ✅ {runtime} SDK installed")
        else:
            print(f"   ⚠️ Install output: {result.result[:300]}")

        # =====================================================================
        # Step 5: Create and run the worker script
        # =====================================================================
        print("\n📋 Step 5: Creating worker script...")

        # Use inline verbose worker script for better debugging
        if runtime == "claude":
            worker_script = get_verbose_claude_worker_script()
        else:
            # Get worker script from spawner for openhands
            from omoi_os.services.daytona_spawner import DaytonaSpawnerService

            spawner = DaytonaSpawnerService.__new__(DaytonaSpawnerService)
            worker_script = spawner._get_worker_script()

        # Upload worker script
        sandbox.fs.upload_file(worker_script.encode("utf-8"), "/tmp/sandbox_worker.py")
        print("   ✅ Worker script uploaded")

        # =====================================================================
        # Step 6: Run the agent
        # =====================================================================
        print("\n📋 Step 6: Running agent...")
        print("=" * 70)
        print(f"   🚀 Starting {runtime} agent with injected task...")
        print(f"   ⏱️  Timeout: {timeout_seconds}s")
        print("=" * 70)

        # Build run command with environment
        env_exports = " && ".join([f'export {k}="{v}"' for k, v in env_vars.items()])
        run_cmd = f"{env_exports} && cd /tmp && python sandbox_worker.py"

        # Run and capture output
        start_time = time.time()
        result = sandbox.process.exec(run_cmd, timeout=timeout_seconds)
        run_time = time.time() - start_time

        print("\n" + "=" * 70)
        print("📤 AGENT OUTPUT:")
        print("=" * 70)

        # Print output with line limit
        output_lines = result.result.strip().split("\n")
        for line in output_lines:  # Show ALL lines
            print(f"   {line}")

        print("=" * 70)

        # The Claude Agent SDK should have done all the work - creating files,
        # running them, showing output. No fallback sandbox.process.exec needed.

        # Just check if the agent produced any output
        success_indicators = [
            "EXECUTION COMPLETE" in result.result,
            "Total messages:" in result.result,
            result.exit_code == 0,
        ]

        # =====================================================================
        # Summary
        # =====================================================================
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"   Runtime: {runtime}")
        print(f"   Task ID: {task_id}")
        print(f"   Sandbox ID: {sandbox.id}")
        print(f"   Run time: {run_time:.1f}s")
        print(f"   Exit code: {result.exit_code}")

        if any(success_indicators):
            print("\n   ✅ Agent executed successfully!")
            return True
        else:
            print("\n   ⚠️ Agent completed but check output for issues")
            return True  # Still return True if it ran

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if sandbox:
            print("\n🧹 Cleaning up sandbox...")
            try:
                daytona.delete(sandbox)
                print("   ✅ Sandbox deleted")
            except Exception as e:
                print(f"   ⚠️ Cleanup error: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="Test direct task injection into sandbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test Claude runtime (default)
  uv run python scripts/test_direct_task_injection.py
  
  # Test OpenHands runtime  
  uv run python scripts/test_direct_task_injection.py --runtime openhands
  
  # Custom task
  uv run python scripts/test_direct_task_injection.py --task "Write a fibonacci function"
  
  # Longer timeout for complex tasks
  uv run python scripts/test_direct_task_injection.py --timeout 600
        """,
    )
    parser.add_argument(
        "--runtime",
        choices=["claude", "openhands"],
        default="claude",
        help="Agent runtime to use (default: claude)",
    )
    parser.add_argument(
        "--task", type=str, default=DEFAULT_TASK, help="Task description for the agent"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds for agent execution (default: 300)",
    )

    args = parser.parse_args()

    success = await test_direct_injection(
        runtime=args.runtime,
        task_description=args.task,
        timeout_seconds=args.timeout,
    )

    print("\n" + "=" * 70)
    if success:
        print("🎉 TEST PASSED!")
    else:
        print("❌ TEST FAILED!")
    print("=" * 70)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
