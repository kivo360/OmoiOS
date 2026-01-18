#!/usr/bin/env python3
"""Test the executor with real Claude SDK using file output approach.

This script tests the updated executor that uses file-based JSON output.

Usage:
    CLAUDE_CODE_OAUTH_TOKEN=your-token uv run python examples/test_sdk_executor_real.py
"""

import asyncio
import json
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def test_executor_explore_phase():
    """Test EXPLORE phase with file output approach."""

    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if not oauth_token:
        logger.error("CLAUDE_CODE_OAUTH_TOKEN not set!")
        return

    logger.info("Testing EXPLORE phase with file output executor")
    logger.info("=" * 60)

    from spec_sandbox.executor.claude_executor import ClaudeExecutor, ExecutorConfig
    from spec_sandbox.reporters.array import ArrayReporter
    from spec_sandbox.schemas.spec import SpecPhase

    reporter = ArrayReporter()

    # Configure with real SDK and higher limits (per user feedback)
    config = ExecutorConfig(
        model="claude-sonnet-4-5-20250929",
        max_turns=45,  # Higher to allow for exploration + write
        max_budget_usd=20.0,  # Allow thorough exploration
        allowed_tools=["Read", "Write", "Glob", "Grep", "Task", "Explore", "Agent", "Skill"],  # Full toolset
        cwd=os.getcwd(),
        use_mock=False,  # Real SDK!
    )

    executor = ClaudeExecutor(
        config=config,
        reporter=reporter,
        spec_id="test-explore-file-output",
    )

    logger.info("Configuration:")
    logger.info(f"  Model: {config.model}")
    logger.info(f"  Max turns: {config.max_turns}")
    logger.info(f"  Max budget: ${config.max_budget_usd}")
    logger.info(f"  Allowed tools: {config.allowed_tools}")
    logger.info(f"  CWD: {config.cwd}")
    logger.info("")

    logger.info("Starting EXPLORE phase...")
    logger.info("")

    try:
        result = await executor.execute_phase(
            phase=SpecPhase.EXPLORE,
            spec_title="Spec Sandbox Analysis",
            spec_description="Analyze the spec-sandbox codebase to understand its structure and capabilities.",
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

        logger.info("")
        logger.info("=" * 60)
        logger.info("OUTPUT ANALYSIS")
        logger.info("=" * 60)

        if result.output:
            output_source = result.output.get("_output_source", "unknown")
            logger.info(f"Output source: {output_source}")

            if output_source == "file":
                logger.info("SUCCESS: JSON was read from output file!")
            elif output_source == "text_fallback":
                logger.warning("WARNING: Fell back to text extraction")
            elif output_source == "file_error":
                logger.error("ERROR: File existed but had invalid JSON")

            # Show output keys
            logger.info("")
            logger.info("Output keys:")
            for key in result.output.keys():
                if key.startswith("_"):
                    continue
                value = result.output[key]
                if isinstance(value, str):
                    logger.info(f"  {key}: {value[:80]}...")
                elif isinstance(value, list):
                    logger.info(f"  {key}: [{len(value)} items]")
                else:
                    logger.info(f"  {key}: {type(value).__name__}")

            # Pretty print full output
            logger.info("")
            logger.info("Full output (truncated):")
            logger.info("-" * 40)
            output_str = json.dumps(result.output, indent=2)
            logger.info(output_str[:2000])
            if len(output_str) > 2000:
                logger.info("... (truncated)")

        # Show events collected
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"EVENTS COLLECTED: {len(reporter.events)}")
        logger.info("=" * 60)
        for event in reporter.events[:10]:  # First 10
            msg = event.data.get("message", "")[:50] if event.data else ""
            logger.info(f"  {event.event_type}: {msg}")
        if len(reporter.events) > 10:
            logger.info(f"  ... and {len(reporter.events) - 10} more events")

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    await test_executor_explore_phase()


if __name__ == "__main__":
    asyncio.run(main())
