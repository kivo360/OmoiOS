#!/usr/bin/env python3
"""Test Claude SDK with file output approach.

This version asks the agent to write JSON to a file, then we verify
the file exists and read it back. Much more reliable than parsing output text.

Usage:
    CLAUDE_CODE_OAUTH_TOKEN=your-token uv run python examples/test_sdk_write_json.py
"""

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def test_write_json_to_file():
    """Test that the agent can write JSON to a designated file."""

    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if not oauth_token:
        logger.error("CLAUDE_CODE_OAUTH_TOKEN not set!")
        return

    logger.info("Testing JSON file output with real Claude SDK")
    logger.info("=" * 60)

    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        ResultMessage,
        TextBlock,
        ToolUseBlock,
    )

    # Create temp directory for output
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_file = Path(tmp_dir) / "analysis.json"

        logger.info(f"Output file: {output_file}")
        logger.info("")

        # Options with Write tool for file output and Task tool for exploration
        options = ClaudeAgentOptions(
            model="claude-sonnet-4-5-20250929",
            max_turns=15,
            max_budget_usd=0.50,
            # Include Write for file output, Task for exploration subagent
            allowed_tools=["Read", "Glob", "Grep", "Write", "Task"],
            cwd=os.getcwd(),
            permission_mode="bypassPermissions",
            system_prompt=f"""You are a codebase analyzer. Your job is to analyze a codebase and write a JSON analysis to a file.

IMPORTANT RULES:
1. Use the Task tool with subagent_type="Explore" to explore the codebase
2. After analysis, write the results to: {output_file}
3. The JSON must have these fields:
   - project_type: string (e.g., "python_package", "web_app")
   - tech_stack: list of strings
   - key_files: list of important file paths
   - summary: one-sentence description

ALWAYS write the analysis to the specified file. This is required.""",
        )

        # Prompt asking to analyze and write to file
        prompt = f"""Analyze the current directory (which is a Python spec-sandbox project) and write a JSON analysis to:

{output_file}

Steps:
1. Use the Task tool with subagent_type="Explore" to quickly scan the codebase
2. Based on what you learn, write a JSON file with:
   - project_type
   - tech_stack
   - key_files
   - summary

Write the JSON file when done. The file path is: {output_file}"""

        logger.info("Starting execution...")
        logger.info("")

        try:
            tool_count = 0
            cost = 0.0
            text_output = []

            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)

                async for msg in client.receive_messages():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                text_output.append(block.text)
                                logger.info(f"Agent: {block.text[:100]}...")
                            elif isinstance(block, ToolUseBlock):
                                tool_count += 1
                                logger.info(f"Tool: {block.name} ({block.id[:8]}...)")

                    elif isinstance(msg, ResultMessage):
                        cost = msg.total_cost_usd or 0.0
                        logger.info(f"Complete: cost=${cost:.4f}")
                        break

            logger.info("")
            logger.info("=" * 60)
            logger.info("RESULT")
            logger.info("=" * 60)
            logger.info(f"Tool uses: {tool_count}")
            logger.info(f"Cost: ${cost:.4f}")
            logger.info("")

            # Check if the file was created
            logger.info("=" * 60)
            logger.info("FILE CHECK")
            logger.info("=" * 60)

            if output_file.exists():
                logger.info(f"SUCCESS: File exists at {output_file}")

                # Read and parse the JSON
                content = output_file.read_text()
                logger.info(f"File size: {len(content)} bytes")
                logger.info("")

                try:
                    parsed = json.loads(content)
                    logger.info("PARSED JSON:")
                    logger.info(json.dumps(parsed, indent=2))

                    # Validate required fields
                    logger.info("")
                    logger.info("VALIDATION:")
                    for field in ["project_type", "tech_stack", "key_files", "summary"]:
                        if field in parsed:
                            logger.info(f"  ✓ {field}: present")
                        else:
                            logger.warning(f"  ✗ {field}: MISSING")

                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error: {e}")
                    logger.info(f"Raw content: {content[:500]}")
            else:
                logger.error(f"FAILED: File does not exist at {output_file}")
                logger.info("Agent text output:")
                for text in text_output:
                    logger.info(f"  {text[:200]}")

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    await test_write_json_to_file()


if __name__ == "__main__":
    asyncio.run(main())
