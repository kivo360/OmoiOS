#!/usr/bin/env python3
"""
Create a new Claude Agent SDK project from templates.

Usage:
    python create_agent_project.py my_agent --template basic
    python create_agent_project.py my_agent --template custom-tools
    python create_agent_project.py my_agent --template chat
"""

import argparse
from pathlib import Path

TEMPLATES = {
    "basic": {
        "description": "Simple one-shot query agent",
        "files": {
            "main.py": '''#!/usr/bin/env python3
"""Basic Claude Agent SDK application."""

import anyio
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)


async def main(prompt: str = "Hello! What can you help me with?"):
    """Run a simple agent query."""
    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant.",
        max_turns=5,
        max_budget_usd=0.50,
    )

    print(f"Sending prompt: {prompt}")
    print("-" * 40)

    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(msg, ResultMessage):
            print("-" * 40)
            print(f"Session: {msg.session_id}")
            print(f"Turns: {msg.num_turns}")
            print(f"Cost: ${msg.total_cost_usd:.4f}")


if __name__ == "__main__":
    anyio.run(main)
''',
            "pyproject.toml": '''[project]
name = "{project_name}"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "claude-agent-sdk",
    "anyio>=4.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
]
''',
            "tests/test_main.py": '''import pytest


@pytest.mark.asyncio
async def test_placeholder():
    """Placeholder test."""
    assert True
''',
        },
    },
    "custom-tools": {
        "description": "Agent with custom MCP tools",
        "files": {
            "main.py": '''#!/usr/bin/env python3
"""Claude Agent SDK with custom tools."""

import anyio
from typing import Any
from claude_agent_sdk import (
    tool,
    create_sdk_mcp_server,
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)


# Define custom tools
@tool("greet", "Greet a person by name", {"name": str})
async def greet(args: dict[str, Any]) -> dict[str, Any]:
    name = args["name"]
    return {"content": [{"type": "text", "text": f"Hello, {name}! Nice to meet you."}]}


@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args: dict[str, Any]) -> dict[str, Any]:
    result = args["a"] + args["b"]
    return {"content": [{"type": "text", "text": f"The sum is: {result}"}]}


@tool("multiply", "Multiply two numbers", {"a": float, "b": float})
async def multiply(args: dict[str, Any]) -> dict[str, Any]:
    result = args["a"] * args["b"]
    return {"content": [{"type": "text", "text": f"The product is: {result}"}]}


# Create MCP server with tools
my_tools = create_sdk_mcp_server(
    name="my_tools",
    version="1.0.0",
    tools=[greet, add, multiply]
)


async def main(prompt: str = "Greet Alice, then calculate 15 + 27"):
    """Run agent with custom tools."""
    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant with custom tools.",
        mcp_servers={"tools": my_tools},
        allowed_tools=[
            "mcp__tools__greet",
            "mcp__tools__add",
            "mcp__tools__multiply",
        ],
        permission_mode="acceptEdits",
        max_turns=10,
        max_budget_usd=0.50,
    )

    print(f"Prompt: {prompt}")
    print("-" * 40)

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")
                    elif isinstance(block, ToolUseBlock):
                        print(f"[Tool: {block.name}] Input: {block.input}")
            elif isinstance(msg, ResultMessage):
                print("-" * 40)
                print(f"Turns: {msg.num_turns}, Cost: ${msg.total_cost_usd:.4f}")


if __name__ == "__main__":
    anyio.run(main)
''',
            "tools.py": '''"""Custom tools module."""

from typing import Any
from claude_agent_sdk import tool


@tool("fetch_data", "Fetch data from an external source", {"source": str})
async def fetch_data(args: dict[str, Any]) -> dict[str, Any]:
    """Example tool that would fetch external data."""
    source = args["source"]
    # Replace with actual implementation
    return {"content": [{"type": "text", "text": f"Data from {source}: [placeholder]"}]}


@tool("process", "Process input data", {"data": str, "operation": str})
async def process(args: dict[str, Any]) -> dict[str, Any]:
    """Example processing tool."""
    data = args["data"]
    operation = args["operation"]

    if operation == "uppercase":
        result = data.upper()
    elif operation == "lowercase":
        result = data.lower()
    elif operation == "reverse":
        result = data[::-1]
    else:
        return {
            "content": [{"type": "text", "text": f"Unknown operation: {operation}"}],
            "is_error": True
        }

    return {"content": [{"type": "text", "text": f"Result: {result}"}]}
''',
            "pyproject.toml": '''[project]
name = "{project_name}"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "claude-agent-sdk",
    "anyio>=4.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
]
''',
            "tests/test_tools.py": '''"""Tests for custom tools."""

import pytest
from tools import fetch_data, process


@pytest.mark.asyncio
async def test_process_uppercase():
    result = await process({"data": "hello", "operation": "uppercase"})
    assert "HELLO" in result["content"][0]["text"]


@pytest.mark.asyncio
async def test_process_unknown_operation():
    result = await process({"data": "hello", "operation": "unknown"})
    assert result.get("is_error") is True
''',
        },
    },
    "chat": {
        "description": "Interactive chat application",
        "files": {
            "main.py": '''#!/usr/bin/env python3
"""Interactive chat application with Claude Agent SDK."""

import anyio
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)


async def main():
    """Run interactive chat session."""
    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant. Be concise and friendly.",
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        max_turns=50,
        max_budget_usd=2.00,
    )

    print("Chat with Claude (type 'quit' to exit)")
    print("-" * 40)

    async with ClaudeSDKClient(options=options) as client:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break

            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            await client.query(user_input)

            print("Claude: ", end="", flush=True)

            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end="", flush=True)
                elif isinstance(msg, ResultMessage):
                    print(f"\\n[Cost: ${msg.total_cost_usd:.4f}]")


if __name__ == "__main__":
    anyio.run(main)
''',
            "pyproject.toml": '''[project]
name = "{project_name}"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "claude-agent-sdk",
    "anyio>=4.0.0",
]
''',
        },
    },
}


def create_project(name: str, template: str, output_dir: Path):
    """Create a new project from template."""
    if template not in TEMPLATES:
        print(f"Error: Unknown template '{template}'")
        print(f"Available templates: {', '.join(TEMPLATES.keys())}")
        return False

    project_dir = output_dir / name
    if project_dir.exists():
        print(f"Error: Directory already exists: {project_dir}")
        return False

    template_data = TEMPLATES[template]
    print(f"Creating project: {name}")
    print(f"Template: {template} - {template_data['description']}")

    # Create directories
    project_dir.mkdir(parents=True)
    (project_dir / "tests").mkdir()

    # Create files
    for file_path, content in template_data["files"].items():
        full_path = project_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Replace placeholders
        content = content.replace("{project_name}", name)

        full_path.write_text(content)
        print(f"  Created: {file_path}")

    # Create __init__.py files
    (project_dir / "tests" / "__init__.py").write_text("")

    print(f"\nProject created at: {project_dir}")
    print(f"\nNext steps:")
    print(f"  cd {project_dir}")
    print(f"  pip install -e .")
    print(f"  python main.py")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Create a new Claude Agent SDK project"
    )
    parser.add_argument(
        "name",
        help="Project name"
    )
    parser.add_argument(
        "--template",
        "-t",
        choices=list(TEMPLATES.keys()),
        default="basic",
        help="Project template (default: basic)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path.cwd(),
        help="Output directory (default: current directory)"
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available templates"
    )

    args = parser.parse_args()

    if args.list:
        print("Available templates:")
        for name, data in TEMPLATES.items():
            print(f"  {name}: {data['description']}")
        return

    success = create_project(args.name, args.template, args.output)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
