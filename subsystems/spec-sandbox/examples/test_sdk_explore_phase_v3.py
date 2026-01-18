#!/usr/bin/env python3
"""Test EXPLORE phase with real Claude Agent SDK - v3.

This version uses a simpler prompt that directly asks for JSON output.

Usage:
    CLAUDE_CODE_OAUTH_TOKEN=your-token uv run python examples/test_sdk_explore_phase_v3.py
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


async def test_simple_json_output():
    """Test that the agent can produce JSON output."""

    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if not oauth_token:
        logger.error("CLAUDE_CODE_OAUTH_TOKEN not set!")
        return

    logger.info("Testing simple JSON output with real Claude SDK")
    logger.info("=" * 60)

    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        ResultMessage,
        TextBlock,
        ToolUseBlock,
    )

    # Simple options with more turns
    options = ClaudeAgentOptions(
        model="claude-sonnet-4-5-20250929",
        max_turns=10,  # More turns to complete the task
        max_budget_usd=0.30,
        allowed_tools=["Read", "Glob"],
        cwd=os.getcwd(),
        permission_mode="bypassPermissions",
        system_prompt="""You are a codebase analyzer. Your job is to analyze a codebase and return structured JSON.

IMPORTANT: Your FINAL response must be a JSON code block with the analysis results. Do not just say you'll do something - actually do it and return JSON.

Example format:
```json
{
  "project_type": "python_package",
  "main_features": ["feature1", "feature2"],
  "key_files": ["file1.py", "file2.py"]
}
```""",
    )

    # Simple prompt asking for JSON
    prompt = """Analyze the current directory and return a JSON summary.

Use the Glob and Read tools to explore, then output a JSON code block with:
1. project_type: What kind of project this is
2. main_files: List of main Python files
3. summary: A one-sentence summary

Respond ONLY with the JSON code block after your analysis."""

    logger.info(f"Prompt: {prompt[:100]}...")
    logger.info("Starting execution...")

    try:
        text_parts = []
        tool_count = 0
        cost = 0.0

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            async for msg in client.receive_messages():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            text_parts.append(block.text)
                            logger.info(f"Text: {block.text[:80]}...")
                        elif isinstance(block, ToolUseBlock):
                            tool_count += 1
                            logger.info(f"Tool: {block.name}")

                elif isinstance(msg, ResultMessage):
                    cost = msg.total_cost_usd or 0.0
                    break

        raw_output = "\n".join(text_parts)

        logger.info("")
        logger.info("=" * 60)
        logger.info("RESULT")
        logger.info("=" * 60)
        logger.info(f"Tool uses: {tool_count}")
        logger.info(f"Cost: ${cost:.4f}")
        logger.info("")
        logger.info("Full raw output:")
        logger.info("-" * 40)
        logger.info(raw_output)
        logger.info("-" * 40)

        # Try to extract JSON
        import re
        import json

        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw_output)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1).strip())
                logger.info("")
                logger.info("PARSED JSON:")
                logger.info(json.dumps(parsed, indent=2))
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
        else:
            logger.warning("No JSON code block found in output")

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    await test_simple_json_output()


if __name__ == "__main__":
    asyncio.run(main())
