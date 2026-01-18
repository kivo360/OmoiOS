#!/usr/bin/env python3
"""Test EXPLORE phase with real Claude Agent SDK - v2.

This version shows the full raw output to understand what's happening.

Usage:
    CLAUDE_CODE_OAUTH_TOKEN=your-token uv run python examples/test_sdk_explore_phase_v2.py
"""

import asyncio
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def test_explore_phase():
    """Test EXPLORE phase with real SDK."""

    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if not oauth_token:
        logger.error("CLAUDE_CODE_OAUTH_TOKEN not set!")
        return

    logger.info("Testing EXPLORE phase with real Claude SDK")
    logger.info("=" * 60)

    from spec_sandbox.executor.claude_executor import ClaudeExecutor, ExecutorConfig
    from spec_sandbox.reporters.array import ArrayReporter
    from spec_sandbox.schemas.spec import SpecPhase

    reporter = ArrayReporter()

    # More restrictive config to encourage JSON output
    config = ExecutorConfig(
        model="claude-sonnet-4-5-20250929",
        max_turns=3,  # Very short
        max_budget_usd=0.20,
        allowed_tools=["Read", "Glob", "Grep"],  # No Bash
        cwd=os.getcwd(),
        use_mock=False,
    )

    executor = ClaudeExecutor(
        config=config,
        reporter=reporter,
        spec_id="test-explore-v2",
    )

    logger.info("Starting EXPLORE phase...")

    try:
        result = await executor.execute_phase(
            phase=SpecPhase.EXPLORE,
            spec_title="Spec Sandbox Analysis",
            spec_description="Understand the spec-sandbox codebase structure.",
            context={},
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("RESULT")
        logger.info("=" * 60)
        logger.info(f"Success: {result.success}")
        logger.info(f"Cost: ${result.cost_usd:.4f}")
        logger.info(f"Duration: {result.duration_ms}ms")
        logger.info(f"Tool uses: {result.tool_uses}")

        if result.error:
            logger.error(f"Error: {result.error}")

        # Show full raw output
        logger.info("")
        logger.info("=" * 60)
        logger.info("RAW OUTPUT (first 2000 chars)")
        logger.info("=" * 60)
        logger.info(result.raw_output[:2000] if result.raw_output else "(no raw output)")

        # Show parsed output
        logger.info("")
        logger.info("=" * 60)
        logger.info("PARSED OUTPUT")
        logger.info("=" * 60)
        if result.output:
            import json
            logger.info(json.dumps(result.output, indent=2, default=str)[:2000])
        else:
            logger.info("(no parsed output)")

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    await test_explore_phase()


if __name__ == "__main__":
    asyncio.run(main())
