#!/usr/bin/env python3
"""Simple hello world test for Claude Agent SDK.

This script tests the SDK step-by-step to understand the event flow.
Each step is logged clearly so we can see what's happening.

Usage:
    # From spec-sandbox directory
    uv run python examples/test_sdk_hello_world.py

Environment:
    ANTHROPIC_API_KEY - Required API key for Claude
"""

import asyncio
import logging
import os
import sys

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def test_sdk_hello_world():
    """Test Claude SDK with a simple hello world prompt."""

    # Step 1: Check authentication
    logger.info("=" * 60)
    logger.info("STEP 1: Checking environment")
    logger.info("=" * 60)

    # Check for OAuth token (preferred) or API key
    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if oauth_token:
        logger.info(f"OAuth token found (length: {len(oauth_token)})")
        logger.info("Using CLAUDE_CODE_OAUTH_TOKEN for authentication")
    elif api_key:
        logger.info(f"API key found (length: {len(api_key)})")
        logger.info("Using ANTHROPIC_API_KEY for authentication")
    else:
        logger.error("No authentication found!")
        logger.info("Set one of:")
        logger.info("  export CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token")
        logger.info("  export ANTHROPIC_API_KEY=your-api-key")
        return

    # Step 2: Import SDK
    logger.info("")
    logger.info("=" * 60)
    logger.info("STEP 2: Importing Claude Agent SDK")
    logger.info("=" * 60)

    try:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ClaudeSDKClient,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
            ToolResultBlock,
        )
        logger.info("SDK imported successfully!")
    except ImportError as e:
        logger.error(f"Failed to import SDK: {e}")
        logger.info("Install with: pip install claude-agent-sdk")
        return

    # Step 3: Configure options
    logger.info("")
    logger.info("=" * 60)
    logger.info("STEP 3: Configuring SDK options")
    logger.info("=" * 60)

    options = ClaudeAgentOptions(
        model="claude-sonnet-4-5-20250929",
        max_turns=3,  # Small for testing
        max_budget_usd=0.10,  # Low budget for hello world
        allowed_tools=["Read"],  # Minimal tools
        cwd=os.getcwd(),  # Current directory
        permission_mode="bypassPermissions",  # Auto-approve for testing
        system_prompt="You are a helpful assistant. Respond briefly.",
    )

    logger.info(f"  Model: {options.model}")
    logger.info(f"  Max turns: {options.max_turns}")
    logger.info(f"  Max budget: ${options.max_budget_usd}")
    logger.info(f"  Allowed tools: {options.allowed_tools}")
    logger.info(f"  CWD: {options.cwd}")

    # Step 4: Create client and send query
    logger.info("")
    logger.info("=" * 60)
    logger.info("STEP 4: Creating client and sending query")
    logger.info("=" * 60)

    prompt = "Say 'Hello World' and nothing else."
    logger.info(f"Prompt: {prompt}")
    logger.info("")
    logger.info("Sending query...")

    try:
        async with ClaudeSDKClient(options=options) as client:
            logger.info("Client created successfully!")

            # Send the query
            await client.query(prompt)
            logger.info("Query sent!")

            # Step 5: Process messages
            logger.info("")
            logger.info("=" * 60)
            logger.info("STEP 5: Processing response messages")
            logger.info("=" * 60)

            message_count = 0
            text_output = []
            tool_count = 0
            final_result = None

            async for msg in client.receive_messages():
                message_count += 1
                logger.info(f"")
                logger.info(f"--- Message {message_count} ---")
                logger.info(f"Type: {type(msg).__name__}")

                if isinstance(msg, AssistantMessage):
                    logger.info(f"  Content blocks: {len(msg.content)}")

                    for i, block in enumerate(msg.content):
                        logger.info(f"  Block {i}: {type(block).__name__}")

                        if isinstance(block, TextBlock):
                            logger.info(f"    Text: {block.text[:100]}...")
                            text_output.append(block.text)

                        elif isinstance(block, ToolUseBlock):
                            tool_count += 1
                            logger.info(f"    Tool: {block.name}")
                            logger.info(f"    Input: {str(block.input)[:100]}...")

                        elif isinstance(block, ToolResultBlock):
                            logger.info(f"    Tool result ID: {block.tool_use_id}")
                            result_str = str(block.content)
                            logger.info(f"    Result: {result_str[:100]}...")

                elif isinstance(msg, ResultMessage):
                    final_result = msg
                    logger.info(f"  Cost: ${msg.total_cost_usd or 0:.4f}")
                    logger.info(f"  Session ID: {msg.session_id}")
                    logger.info(f"  Is error: {msg.is_error}")
                    # ResultMessage signals the end of the response
                    break

                else:
                    logger.info(f"  Unknown message type")

            # Step 6: Summary
            logger.info("")
            logger.info("=" * 60)
            logger.info("STEP 6: Summary")
            logger.info("=" * 60)
            logger.info(f"Total messages: {message_count}")
            logger.info(f"Tool uses: {tool_count}")
            logger.info(f"Text blocks: {len(text_output)}")

            if text_output:
                logger.info("")
                logger.info("Final text output:")
                for text in text_output:
                    logger.info(f"  {text}")

            if final_result:
                logger.info("")
                logger.info(f"Total cost: ${final_result.total_cost_usd or 0:.4f}")

            logger.info("")
            logger.info("=" * 60)
            logger.info("TEST COMPLETE!")
            logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error during SDK execution: {e}")
        logger.exception("Full traceback:")
        return


async def main():
    """Main entry point."""
    logger.info("Claude Agent SDK Hello World Test")
    logger.info("=" * 60)
    await test_sdk_hello_world()


if __name__ == "__main__":
    asyncio.run(main())
