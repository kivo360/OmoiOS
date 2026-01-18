#!/usr/bin/env python3
"""Test EXPLORE phase with real Claude Agent SDK.

This script tests a single phase execution using the executor
with the real Claude SDK (not mock mode).

Usage:
    # From spec-sandbox directory
    CLAUDE_CODE_OAUTH_TOKEN=your-token uv run python examples/test_sdk_explore_phase.py
"""

import asyncio
import logging
import os

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def test_explore_phase():
    """Test EXPLORE phase with real SDK."""

    # Check authentication
    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if not oauth_token:
        logger.error("CLAUDE_CODE_OAUTH_TOKEN not set!")
        return

    logger.info("=" * 60)
    logger.info("Testing EXPLORE phase with real Claude SDK")
    logger.info("=" * 60)

    # Import after env check
    from spec_sandbox.executor.claude_executor import ClaudeExecutor, ExecutorConfig
    from spec_sandbox.reporters.array import ArrayReporter
    from spec_sandbox.schemas.spec import SpecPhase

    # Create reporter to collect events
    reporter = ArrayReporter()

    # Configure executor - NOT mock mode
    config = ExecutorConfig(
        model="claude-sonnet-4-5-20250929",
        max_turns=5,  # Short for testing
        max_budget_usd=0.50,  # Reasonable budget
        allowed_tools=["Read", "Glob", "Grep"],  # Exploration tools only
        cwd=os.getcwd(),
        use_mock=False,  # Real SDK!
    )

    executor = ClaudeExecutor(
        config=config,
        reporter=reporter,
        spec_id="test-explore",
    )

    logger.info("Configuration:")
    logger.info(f"  Model: {config.model}")
    logger.info(f"  Max turns: {config.max_turns}")
    logger.info(f"  Max budget: ${config.max_budget_usd}")
    logger.info(f"  Allowed tools: {config.allowed_tools}")
    logger.info(f"  CWD: {config.cwd}")
    logger.info(f"  Mock mode: {config.use_mock}")
    logger.info("")

    # Execute EXPLORE phase
    logger.info("Starting EXPLORE phase execution...")
    logger.info("")

    try:
        result = await executor.execute_phase(
            phase=SpecPhase.EXPLORE,
            spec_title="Test Feature",
            spec_description="A simple test feature to explore the codebase structure.",
            context={},
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("EXECUTION RESULT")
        logger.info("=" * 60)
        logger.info(f"Success: {result.success}")
        logger.info(f"Cost: ${result.cost_usd:.4f}")
        logger.info(f"Duration: {result.duration_ms}ms")
        logger.info(f"Tool uses: {result.tool_uses}")

        if result.error:
            logger.error(f"Error: {result.error}")

        if result.output:
            logger.info("")
            logger.info("Output keys:")
            for key in result.output.keys():
                value = result.output[key]
                if isinstance(value, str):
                    logger.info(f"  {key}: {value[:100]}...")
                elif isinstance(value, list):
                    logger.info(f"  {key}: [{len(value)} items]")
                else:
                    logger.info(f"  {key}: {type(value).__name__}")

        # Show events collected
        logger.info("")
        logger.info("=" * 60)
        logger.info("EVENTS COLLECTED")
        logger.info("=" * 60)
        logger.info(f"Total events: {len(reporter.events)}")
        for event in reporter.events:
            logger.info(f"  {event.event_type}: {event.data.get('message', '')[:50] if event.data else ''}")

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        logger.exception("Full traceback:")


async def main():
    logger.info("Claude Agent SDK - EXPLORE Phase Test")
    logger.info("=" * 60)
    await test_explore_phase()


if __name__ == "__main__":
    asyncio.run(main())
