#!/usr/bin/env python
"""Test real execution of spec-sandbox without mocks.

This script runs the ClaudeExecutor against the actual codebase
to verify that the Claude Agent SDK produces high-quality output
similar to what the /spec-driven-dev skill produces.

Usage:
    # Run EXPLORE phase only (fastest test)
    uv run python scripts/test_real_execution.py --phase explore

    # Run EXPLORE + PRD phases
    uv run python scripts/test_real_execution.py --phase prd

    # Run all phases
    uv run python scripts/test_real_execution.py --phase all

    # Run with custom spec
    uv run python scripts/test_real_execution.py --phase explore \
        --title "WhatsApp Integration" \
        --description "Enable WhatsApp messaging for agents"

    # Run against a different directory
    uv run python scripts/test_real_execution.py --phase explore \
        --cwd /path/to/project
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spec_sandbox.executor.claude_executor import ClaudeExecutor, ExecutorConfig
from spec_sandbox.reporters.array import ArrayReporter
from spec_sandbox.schemas.spec import SpecPhase


# Default test spec - describes a real feature request
DEFAULT_TITLE = "Spec Output Quality Improvement"
DEFAULT_DESCRIPTION = """
Improve the spec-sandbox to generate higher quality requirements and designs.

The current spec-sandbox generates generic placeholder content. We need it to:
1. Actually explore the codebase using tools (Read, Glob, Grep)
2. Generate contextual requirements based on real code patterns
3. Create design documents with accurate architecture diagrams
4. Produce tasks that reference actual files and components

This should match the quality of the /spec-driven-dev skill which produces:
- EARS-format requirements with 60+ acceptance criteria
- Mermaid diagrams showing real architecture
- Tasks that reference specific files like "backend/omoi_os/services/webhook.py"
"""


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_json(data: dict, max_lines: int = 50):
    """Print JSON with truncation for large outputs."""
    formatted = json.dumps(data, indent=2)
    lines = formatted.split("\n")

    if len(lines) > max_lines:
        print("\n".join(lines[:max_lines]))
        print(f"\n... ({len(lines) - max_lines} more lines)")
    else:
        print(formatted)


async def run_phase(
    executor: ClaudeExecutor,
    phase: SpecPhase,
    title: str,
    description: str,
    context: dict,
) -> tuple[bool, dict]:
    """Run a single phase and return results."""
    print_section(f"EXECUTING {phase.value.upper()} PHASE")

    print(f"\n  Title: {title}")
    print(f"  Description: {description[:100]}...")
    print(f"  Context keys: {list(context.keys())}")
    print(f"  Config: model={executor.config.model}, max_turns={executor.config.max_turns}")
    print(f"  Use mock: {executor.config.use_mock}")

    start_time = datetime.now()
    print(f"\n  Started at: {start_time.strftime('%H:%M:%S')}")
    print("  Running... (this may take a few minutes)")

    result = await executor.execute_phase(
        phase=phase,
        spec_title=title,
        spec_description=description,
        context=context,
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n  Completed at: {end_time.strftime('%H:%M:%S')}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Success: {result.success}")
    print(f"  Cost: ${result.cost_usd:.4f}")
    print(f"  Tool uses: {result.tool_uses}")

    if result.error:
        print(f"  Error: {result.error}")

    if result.output:
        print("\n  OUTPUT:")
        print("-" * 70)
        print_json(result.output)
        print("-" * 70)

        # Check for mock indicator
        if result.output.get("_mock"):
            print("\n  ⚠️  WARNING: Output contains _mock=True - this is mock data!")
            print("  The Claude Agent SDK may not be available or configured.")

    return result.success, result.output


async def run_test(
    phases: list[SpecPhase],
    title: str,
    description: str,
    cwd: Path | None,
):
    """Run the test for specified phases."""
    print_section("REAL EXECUTION TEST")

    print(f"\n  Phases to run: {[p.value for p in phases]}")
    print(f"  Working directory: {cwd or Path.cwd()}")
    print(f"  SDK availability: Checking...")

    # Check if SDK is available
    try:
        from claude_agent_sdk import ClaudeSDKClient
        print("  Claude Agent SDK: ✓ Available")
        sdk_available = True
    except ImportError:
        print("  Claude Agent SDK: ✗ Not available (will use mock)")
        sdk_available = False

    # Check for auth tokens
    has_oauth = "CLAUDE_CODE_OAUTH_TOKEN" in os.environ
    has_api_key = "ANTHROPIC_API_KEY" in os.environ
    print(f"  CLAUDE_CODE_OAUTH_TOKEN: {'✓ Set' if has_oauth else '✗ Not set'}")
    print(f"  ANTHROPIC_API_KEY: {'✓ Set' if has_api_key else '✗ Not set'}")

    if not sdk_available:
        print("\n  ⚠️  SDK not available - results will be mock data")
        print("  To get real results, ensure claude-agent-sdk is installed")
    elif not (has_oauth or has_api_key):
        print("\n  ⚠️  No auth tokens found - SDK may fail")
        print("  Set CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY")

    # Create executor with NO mocks
    reporter = ArrayReporter()
    config = ExecutorConfig(
        model="claude-sonnet-4-5-20250929",
        max_turns=45,
        max_budget_usd=5.0,  # Limit cost for testing
        cwd=cwd,
        use_mock=False,  # NO MOCKS - real execution only
    )

    executor = ClaudeExecutor(
        config=config,
        reporter=reporter,
        spec_id="test-real-execution",
    )

    # Run phases in order, accumulating context
    context = {}
    results = {}
    all_success = True

    for phase in phases:
        success, output = await run_phase(
            executor=executor,
            phase=phase,
            title=title,
            description=description,
            context=context,
        )

        results[phase.value] = {
            "success": success,
            "output": output,
        }

        if success:
            context[phase.value] = output
        else:
            all_success = False
            print(f"\n  ✗ Phase {phase.value} failed - stopping")
            break

    # Print summary
    print_section("EXECUTION SUMMARY")

    for phase_name, result in results.items():
        status = "✓" if result["success"] else "✗"
        output_size = len(json.dumps(result["output"]))
        print(f"  {status} {phase_name}: {output_size} bytes")

        # Quality indicators
        output = result["output"]
        if phase_name == "explore":
            key_files = output.get("key_files", [])
            patterns = output.get("relevant_patterns", [])
            print(f"    - Key files found: {len(key_files)}")
            print(f"    - Patterns found: {len(patterns)}")

        elif phase_name == "prd":
            user_stories = output.get("user_stories", [])
            risks = output.get("risks", [])
            print(f"    - User stories: {len(user_stories)}")
            print(f"    - Risks identified: {len(risks)}")

        elif phase_name == "requirements":
            requirements = output.get("requirements", [])
            total_ac = sum(len(r.get("acceptance_criteria", [])) for r in requirements)
            print(f"    - Requirements: {len(requirements)}")
            print(f"    - Total acceptance criteria: {total_ac}")

        elif phase_name == "design":
            components = output.get("components", [])
            endpoints = output.get("api_endpoints", [])
            models = output.get("data_models", [])
            print(f"    - Components: {len(components)}")
            print(f"    - API endpoints: {len(endpoints)}")
            print(f"    - Data models: {len(models)}")

        elif phase_name == "tasks":
            tickets = output.get("tickets", [])
            tasks = output.get("tasks", [])
            print(f"    - Tickets: {len(tickets)}")
            print(f"    - Tasks: {len(tasks)}")

    # Save results to file
    output_file = Path("test_real_execution_output.json")
    with open(output_file, "w") as f:
        json.dump({
            "title": title,
            "description": description,
            "phases": [p.value for p in phases],
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }, f, indent=2)

    print(f"\n  Results saved to: {output_file}")

    # Check reporter events
    events = reporter.events
    print(f"\n  Events emitted: {len(events)}")
    for event in events[-5:]:  # Show last 5 events
        print(f"    - {event.event_type}: {event.data.get('message', '')[:50]}")

    return all_success


def get_phases(phase_arg: str) -> list[SpecPhase]:
    """Parse phase argument into list of phases."""
    if phase_arg == "all":
        return list(SpecPhase)
    elif phase_arg == "explore":
        return [SpecPhase.EXPLORE]
    elif phase_arg == "prd":
        return [SpecPhase.EXPLORE, SpecPhase.PRD]
    elif phase_arg == "requirements":
        return [SpecPhase.EXPLORE, SpecPhase.PRD, SpecPhase.REQUIREMENTS]
    elif phase_arg == "design":
        return [SpecPhase.EXPLORE, SpecPhase.PRD, SpecPhase.REQUIREMENTS, SpecPhase.DESIGN]
    elif phase_arg == "tasks":
        return [SpecPhase.EXPLORE, SpecPhase.PRD, SpecPhase.REQUIREMENTS, SpecPhase.DESIGN, SpecPhase.TASKS]
    elif phase_arg == "sync":
        return list(SpecPhase)
    else:
        raise ValueError(f"Unknown phase: {phase_arg}")


async def main():
    parser = argparse.ArgumentParser(
        description="Test real execution of spec-sandbox without mocks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--phase",
        default="explore",
        choices=["explore", "prd", "requirements", "design", "tasks", "sync", "all"],
        help="Phase(s) to run (default: explore)",
    )
    parser.add_argument(
        "--title",
        default=DEFAULT_TITLE,
        help="Spec title",
    )
    parser.add_argument(
        "--description",
        default=DEFAULT_DESCRIPTION,
        help="Spec description",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Working directory (default: current directory)",
    )

    args = parser.parse_args()

    phases = get_phases(args.phase)

    success = await run_test(
        phases=phases,
        title=args.title,
        description=args.description,
        cwd=args.cwd,
    )

    print("\n" + "=" * 70)
    if success:
        print("  TEST COMPLETED SUCCESSFULLY")
    else:
        print("  TEST FAILED")
    print("=" * 70 + "\n")

    return 0 if success else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
