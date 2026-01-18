#!/usr/bin/env python3
"""Demonstrate Claude-based markdown generation.

This script runs a mock spec and shows the generated markdown files
using the Claude Agent SDK-based generator with mock mode enabled.
"""

import asyncio
import tempfile
from pathlib import Path

from spec_sandbox.config import SpecSandboxSettings
from spec_sandbox.worker.state_machine import SpecStateMachine


async def main():
    """Run a mock spec and show Claude-generated markdown output."""
    print("=" * 60)
    print("SPEC SANDBOX - Claude-Based Markdown Generator Demo")
    print("=" * 60)
    print()

    # Create temp output directory
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        settings = SpecSandboxSettings(
            spec_id="demo-spec-001",
            spec_title="User Authentication System",
            spec_description="Add a user authentication system with JWT tokens, login, logout, and password reset",
            cwd=str(output_dir),
            output_directory=output_dir,
            use_mock=True,  # Use mock executor for phases
            reporter_mode="array",  # In-memory for demo
            markdown_generator="claude",  # Use Claude-based generator
        )

        sm = SpecStateMachine(settings=settings)
        print(f"Running spec: {settings.spec_title}")
        print(f"Output directory: {output_dir}")
        print(f"Generator: {settings.markdown_generator}")
        print()

        # Run the spec
        success = await sm.run()

        print()
        print("=" * 60)
        print(f"Spec completed: {'SUCCESS' if success else 'FAILED'}")
        print("=" * 60)
        print()

        # Show generated markdown files
        print("Generated Markdown Artifacts:")
        print("-" * 40)

        for artifact_type, path in sm.markdown_artifacts.items():
            print(f"\n📄 {artifact_type}: {path.name}")

            # Show first 40 lines
            content = path.read_text()
            lines = content.split("\n")[:40]
            print("   " + "-" * 36)
            for line in lines:
                print(f"   {line}")
            if len(content.split("\n")) > 40:
                print("   ... (truncated)")

        print()
        print("=" * 60)
        print("File Structure:")
        print("-" * 40)

        for f in sorted(output_dir.rglob("*.md")):
            relative = f.relative_to(output_dir)
            print(f"  📄 {relative}")

        for f in sorted(output_dir.rglob("*.json")):
            relative = f.relative_to(output_dir)
            print(f"  📋 {relative}")

        for f in sorted(output_dir.rglob("*.jsonl")):
            relative = f.relative_to(output_dir)
            print(f"  📜 {relative}")


if __name__ == "__main__":
    asyncio.run(main())
