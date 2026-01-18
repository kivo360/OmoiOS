#!/usr/bin/env python3
"""Demonstrate markdown output generation.

This script runs a mock spec through all phases and shows
the generated markdown files with YAML frontmatter.
"""

import asyncio
import tempfile
from pathlib import Path

from spec_sandbox.config import SpecSandboxSettings
from spec_sandbox.worker.state_machine import SpecStateMachine


async def main():
    """Run a mock spec and show markdown output."""
    print("=" * 60)
    print("SPEC SANDBOX - Markdown Output Demo")
    print("=" * 60)
    print()

    # Create temp output directory
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        settings = SpecSandboxSettings(
            spec_id="demo-spec-001",
            spec_title="Demo Feature Implementation",
            spec_description="Add a user authentication system with login and logout",
            cwd=str(output_dir),
            output_directory=output_dir,
            use_mock=True,  # Use mock executor
            reporter_mode="array",  # In-memory for demo
        )

        sm = SpecStateMachine(settings=settings)
        print(f"Running spec: {settings.spec_title}")
        print(f"Output directory: {output_dir}")
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

            # Show first 30 lines
            content = path.read_text()
            lines = content.split("\n")[:30]
            print("   " + "-" * 36)
            for line in lines:
                print(f"   {line}")
            if len(content.split("\n")) > 30:
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
