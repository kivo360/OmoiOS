#!/usr/bin/env python3
"""
Create Daytona snapshots from the AI agent development container images.
Uses the Daytona Python SDK to create snapshots from pushed container images.
"""
import os
import sys

from daytona import Daytona, CreateSnapshotParams, Image, Resources


def create_snapshot(
    daytona: Daytona,
    name: str,
    image_url: str,
    cpu: int,
    memory: int,
    disk: int,
):
    """Create a Daytona snapshot from a container image."""
    print(f"\nCreating snapshot '{name}' from image '{image_url}'...")
    print(f"  Resources: CPU={cpu}, Memory={memory}GB, Disk={disk}GB")

    try:
        snapshot = daytona.snapshot.create(
            CreateSnapshotParams(
                name=name,
                image=Image.custom(image_url),
                resources=Resources(
                    cpu=cpu,
                    memory=memory,
                    disk=disk,
                ),
            ),
            on_logs=lambda log: print(f"  [LOG] {log}"),
        )
        print(f"  SUCCESS: Snapshot '{name}' created!")
        return snapshot
    except Exception as e:
        print(f"  ERROR: Failed to create snapshot: {e}")
        return None


def main():
    # Check for API key
    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        print("ERROR: DAYTONA_API_KEY environment variable not set")
        sys.exit(1)

    print("Connecting to Daytona...")
    daytona = Daytona()

    # Define the snapshots to create
    snapshots = [
        {
            "name": "ai-agent-dev-light",
            "image": "ghcr.io/kivo360/ai-agent-dev-light:1.0.0",
            "cpu": 2,
            "memory": 4,
            "disk": 10,
        },
        {
            "name": "ai-agent-dev",
            "image": "ghcr.io/kivo360/ai-agent-dev:1.0.0",
            "cpu": 4,
            "memory": 8,
            "disk": 20,
        },
    ]

    results = []
    for snap_config in snapshots:
        result = create_snapshot(
            daytona=daytona,
            name=snap_config["name"],
            image_url=snap_config["image"],
            cpu=snap_config["cpu"],
            memory=snap_config["memory"],
            disk=snap_config["disk"],
        )
        results.append((snap_config["name"], result is not None))

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for name, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"  {name}: {status}")

    # Check if all succeeded
    if all(success for _, success in results):
        print("\nAll snapshots created successfully!")
        print("\nTo create a sandbox from these snapshots, use:")
        print('  daytona sandbox create --snapshot ai-agent-dev-light')
        print('  daytona sandbox create --snapshot ai-agent-dev')
        return 0
    else:
        print("\nSome snapshots failed to create. Check the logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
