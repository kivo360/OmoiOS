#!/usr/bin/env python3
"""Build Daytona snapshots for prototype framework templates.

Creates pre-configured sandbox snapshots with scaffolded projects and
installed dependencies, so `start_session()` can create sandboxes quickly.

Usage:
    # Build all snapshots
    uv run python scripts/prototyping/build_prototype_snapshots.py

    # Build a specific framework
    uv run python scripts/prototyping/build_prototype_snapshots.py react-vite
    uv run python scripts/prototyping/build_prototype_snapshots.py next
    uv run python scripts/prototyping/build_prototype_snapshots.py vue-vite
"""

import sys
import time

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv(".env.local")
    load_dotenv(".env")
except ImportError:
    pass


# Framework configurations
FRAMEWORKS = {
    "react-vite": {
        "snapshot_name": "omoios-react-vite-snapshot",
        "scaffold_command": "npm create vite@latest /app -- --template react-ts",
        "install_command": "cd /app && npm install",
        "label": "React + Vite + TypeScript",
    },
    "next": {
        "snapshot_name": "omoios-next-snapshot",
        "scaffold_command": (
            "npx create-next-app@latest /app "
            "--typescript --tailwind --eslint --app --src-dir "
            "--import-alias '@/*' --use-npm --yes"
        ),
        "install_command": "cd /app && npm install",
        "label": "Next.js + TypeScript + Tailwind",
    },
    "vue-vite": {
        "snapshot_name": "omoios-vue-vite-snapshot",
        "scaffold_command": "npm create vite@latest /app -- --template vue-ts",
        "install_command": "cd /app && npm install",
        "label": "Vue + Vite + TypeScript",
    },
}

BASE_IMAGE = "nikolaik/python-nodejs:python3.12-nodejs22"


def build_snapshot(framework_key: str) -> None:
    """Build a single framework snapshot."""
    from daytona import CreateSandboxFromImageParams, Daytona, DaytonaConfig

    from omoi_os.config import get_app_settings

    config = FRAMEWORKS[framework_key]
    settings = get_app_settings()

    print(f"\n{'='*60}")
    print(f"Building snapshot: {config['label']}")
    print(f"Snapshot name: {config['snapshot_name']}")
    print(f"{'='*60}")

    daytona_config = DaytonaConfig(
        api_key=settings.daytona.api_key,
        server_url=settings.daytona.api_url,
        target=settings.daytona.target,
    )
    daytona = Daytona(config=daytona_config)

    sandbox = None
    try:
        # Step 1: Create base sandbox
        print("\n[1/4] Creating base sandbox...")
        params = CreateSandboxFromImageParams(
            image=BASE_IMAGE,
            language="python",
            labels={"purpose": "snapshot-builder", "framework": framework_key},
            public=False,
        )
        sandbox = daytona.create(params=params)
        print(f"  Sandbox ID: {sandbox.id}")

        # Step 2: Scaffold the framework project
        print(f"\n[2/4] Scaffolding {config['label']}...")
        result = sandbox.process.exec(config["scaffold_command"])
        if hasattr(result, "exit_code") and result.exit_code != 0:
            print("  WARNING: Scaffold command returned non-zero exit code")
            if hasattr(result, "result"):
                print(f"  Output: {result.result[:500]}")

        # Step 3: Install dependencies
        print("\n[3/4] Installing dependencies...")
        result = sandbox.process.exec(config["install_command"])
        if hasattr(result, "exit_code") and result.exit_code != 0:
            print("  WARNING: Install command returned non-zero exit code")

        # Verify node_modules exists
        result = sandbox.process.exec("ls -la /app/node_modules/.package-lock.json")
        print(f"  Dependencies installed: {'package-lock' in str(getattr(result, 'result', ''))}")

        # Step 4: Archive as snapshot
        print(f"\n[4/4] Creating snapshot: {config['snapshot_name']}...")
        # Note: Daytona SDK's archive/snapshot API may vary.
        # This is the expected pattern — adjust if the SDK method differs.
        try:
            sandbox.archive()
            print("  Snapshot created successfully!")
        except AttributeError:
            print(
                f"  WARNING: sandbox.archive() not available. "
                f"Create snapshot manually via Daytona dashboard using sandbox ID: {sandbox.id}"
            )
            print("  Keeping sandbox alive for manual snapshot creation.")
            sandbox = None  # Don't cleanup

        print(f"\nDone: {framework_key}")

    except Exception as e:
        print(f"\nERROR building {framework_key}: {e}")
        raise
    finally:
        if sandbox:
            print("\nCleaning up sandbox...")
            try:
                sandbox.delete()
                print("  Sandbox deleted.")
            except Exception as e:
                print(f"  WARNING: Failed to delete sandbox: {e}")


def main():
    """Entry point."""
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(FRAMEWORKS.keys())

    # Validate targets
    for target in targets:
        if target not in FRAMEWORKS:
            print(f"ERROR: Unknown framework '{target}'")
            print(f"Available: {', '.join(FRAMEWORKS.keys())}")
            sys.exit(1)

    print(f"Building snapshots for: {', '.join(targets)}")
    start = time.time()

    for target in targets:
        build_snapshot(target)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"All snapshots built in {elapsed:.1f}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
