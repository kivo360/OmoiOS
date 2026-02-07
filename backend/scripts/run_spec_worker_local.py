#!/usr/bin/env python3
"""
Run the spec sandbox worker locally against your local API server.

This lets you test the full spec workflow loop:
  Worker (local) → API (local) → Database → Frontend

Usage:
    # 1. Start your local API server first:
    uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 8000 --reload

    # 2. Create a spec in the frontend or via API

    # 3. Run this script with the spec ID:
    uv run python scripts/run_spec_worker_local.py \
        --spec-id "your-spec-uuid" \
        --dir /path/to/codebase \
        --api-url http://localhost:8000

    # Or use environment variables:
    SPEC_ID=xxx CALLBACK_URL=http://localhost:8000 uv run python scripts/run_spec_worker_local.py

What this does:
    - Runs ClaudeSandboxWorker locally (same code as Daytona)
    - Sends events to your local API server
    - Updates spec status and phase_data in real-time
    - You can watch the frontend update as phases complete

Requirements:
    - ANTHROPIC_API_KEY set
    - Local API server running
    - A spec created in the database (get ID from frontend URL or API)
"""

import argparse
import asyncio
import logging
import os
import sys
import uuid
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def fetch_spec_from_api(api_base_url: str, spec_id: str) -> dict:
    """Fetch spec details from the API."""
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_base_url}/api/v1/specs/{spec_id}")
        if resp.status_code != 200:
            logger.error(f"Failed to fetch spec: {resp.status_code} - {resp.text}")
            raise ValueError(
                f"Spec {spec_id} not found. Create it first in the frontend."
            )
        return resp.json()


def setup_worker_environment(
    spec_id: str,
    spec_title: str,
    spec_description: str,
    working_dir: str,
    api_base_url: str,
    model: str,
    sandbox_id: str,
) -> None:
    """Set environment variables that WorkerConfig reads."""
    # Core identifiers
    os.environ["SANDBOX_ID"] = sandbox_id
    os.environ["SPEC_ID"] = spec_id
    os.environ["SPEC_PHASE"] = "explore"  # Start from explore

    # Clear task-related vars (this is spec mode, not task mode)
    os.environ["TASK_ID"] = ""
    os.environ["TICKET_ID"] = ""
    os.environ["TICKET_TITLE"] = ""
    os.environ["TICKET_DESCRIPTION"] = ""

    # Server connection - this is where events are POSTed
    os.environ["CALLBACK_URL"] = api_base_url

    # Model settings
    os.environ["MODEL"] = model

    # Working directory
    os.environ["CWD"] = working_dir

    # SDK settings
    os.environ["MAX_TURNS"] = "100"
    os.environ["HEARTBEAT_INTERVAL"] = "30"

    # Initial prompt with spec description
    os.environ["INITIAL_PROMPT"] = f"""You are generating a technical specification for:

Title: {spec_title}

Description:
{spec_description}

Analyze the codebase and generate comprehensive requirements, design, and tasks.
"""

    # Execution mode for spec generation
    os.environ["EXECUTION_MODE"] = "exploration"

    logger.info("Environment configured for spec worker")


async def run_worker_locally(
    spec_id: str,
    working_dir: str,
    api_base_url: str,
    model: str = "claude-sonnet-4-20250514",
    sandbox_id: str | None = None,
) -> int:
    """
    Run the sandbox worker locally, sending events to the API.

    Args:
        spec_id: UUID of the spec to execute
        working_dir: Local directory to use as workspace
        api_base_url: Base URL of the API server (e.g., http://localhost:8000)
        model: Claude model to use
        sandbox_id: Optional sandbox ID (generated if not provided)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Generate sandbox ID if not provided
    if not sandbox_id:
        sandbox_id = f"local-spec-{spec_id[:8]}-{uuid.uuid4().hex[:6]}"

    working_path = Path(working_dir).resolve()
    if not working_path.exists():
        raise ValueError(f"Working directory does not exist: {working_path}")

    logger.info("=" * 70)
    logger.info("LOCAL SPEC WORKER")
    logger.info("=" * 70)
    logger.info(f"Spec ID:         {spec_id}")
    logger.info(f"Sandbox ID:      {sandbox_id}")
    logger.info(f"Working dir:     {working_path}")
    logger.info(f"API URL:         {api_base_url}")
    logger.info(f"Model:           {model}")
    logger.info("=" * 70)

    # Fetch spec details from API
    spec_data = await fetch_spec_from_api(api_base_url, spec_id)
    spec_title = spec_data.get("title", "Local Spec")
    spec_description = spec_data.get("description", "")

    logger.info(f"Spec title:      {spec_title}")
    logger.info(f"Spec desc:       {spec_description[:100]}...")
    logger.info("=" * 70)

    # Set up environment variables for WorkerConfig
    setup_worker_environment(
        spec_id=spec_id,
        spec_title=spec_title,
        spec_description=spec_description,
        working_dir=str(working_path),
        api_base_url=api_base_url,
        model=model,
        sandbox_id=sandbox_id,
    )

    # Import after setting env vars so WorkerConfig picks them up
    from omoi_os.workers.claude_sandbox_worker import ClaudeSandboxWorker, WorkerConfig

    # Create config (reads from environment)
    config = WorkerConfig()

    logger.info("Starting worker...")
    logger.info(f"  sandbox_id: {config.sandbox_id}")
    logger.info(f"  spec_id: {config.spec_id}")
    logger.info(f"  spec_phase: {config.spec_phase}")
    logger.info(f"  callback_url: {config.callback_url}")
    logger.info(f"  cwd: {config.cwd}")

    worker = ClaudeSandboxWorker(config)

    try:
        exit_code = await worker.run()
        logger.info(f"Worker completed with exit code: {exit_code}")
        return exit_code
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Worker failed: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Run spec sandbox worker locally against your API server"
    )
    parser.add_argument(
        "--spec-id",
        default=os.environ.get("SPEC_ID"),
        help="Spec UUID to execute (or set SPEC_ID env var)",
    )
    parser.add_argument(
        "--dir",
        "-d",
        default=os.environ.get("WORKSPACE_DIR", "."),
        help="Working directory (codebase to analyze)",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("CALLBACK_URL", "http://localhost:8000"),
        help="API server base URL",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=os.environ.get("MODEL", "claude-sonnet-4-20250514"),
        help="Claude model to use",
    )
    parser.add_argument(
        "--sandbox-id",
        default=os.environ.get("SANDBOX_ID"),
        help="Custom sandbox ID (generated if not provided)",
    )

    args = parser.parse_args()

    if not args.spec_id:
        parser.error("--spec-id is required (or set SPEC_ID env var)")

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    # Run
    exit_code = asyncio.run(
        run_worker_locally(
            spec_id=args.spec_id,
            working_dir=args.dir,
            api_base_url=args.api_url,
            model=args.model,
            sandbox_id=args.sandbox_id,
        )
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
