#!/usr/bin/env python3
"""Simple isolated Daytona sandbox test.

Tests:
1. Create a sandbox with nikolaik/python-nodejs:python3.12-nodejs22
2. Run basic commands (python --version, node --version, echo)
3. Clean up the sandbox
"""

import os
import sys
import time
from pathlib import Path

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment
from dotenv import load_dotenv

load_dotenv(backend_dir / ".env.local")
load_dotenv(backend_dir / ".env")


def test_sandbox():
    """Run isolated sandbox test."""
    print("=" * 60)
    print("🧪 DAYTONA SANDBOX TEST")
    print("=" * 60)

    # Check API key
    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        print("❌ DAYTONA_API_KEY not set")
        print("   Set it in .env.local: DAYTONA_API_KEY=dtn_...")
        return False

    print(f"✅ API Key configured: {api_key[:10]}...")

    try:
        from daytona import Daytona, DaytonaConfig, CreateSandboxFromImageParams
    except ImportError:
        print("❌ Daytona SDK not installed")
        print("   Run: uv add daytona-sdk")
        return False

    print("✅ Daytona SDK imported")

    # Configure Daytona
    config = DaytonaConfig(
        api_key=api_key,
        api_url="https://app.daytona.io/api",
        target="us",
    )
    daytona = Daytona(config)

    sandbox = None
    try:
        # Create sandbox
        print("\n📦 Creating sandbox...")
        print("   Image: nikolaik/python-nodejs:python3.12-nodejs22")

        start_time = time.time()
        params = CreateSandboxFromImageParams(
            image="nikolaik/python-nodejs:python3.12-nodejs22",
            labels={"test": "omoios-sandbox-test"},
            ephemeral=True,
            public=False,
        )

        sandbox = daytona.create(params=params, timeout=120)
        create_time = time.time() - start_time

        print(f"✅ Sandbox created in {create_time:.1f}s")
        print(f"   ID: {sandbox.id}")

        # Test commands
        print("\n🔧 Running test commands...")

        # Python version
        result = sandbox.process.exec("python --version")
        print(f"   Python: {result.result.strip()}")

        # Node version
        result = sandbox.process.exec("node --version")
        print(f"   Node: {result.result.strip()}")

        # pip version
        result = sandbox.process.exec("pip --version")
        print(f"   Pip: {result.result.strip().split()[1]}")

        # npm version
        result = sandbox.process.exec("npm --version")
        print(f"   NPM: {result.result.strip()}")

        # Test echo
        result = sandbox.process.exec("echo 'Hello from Daytona sandbox!'")
        print(f"   Echo: {result.result.strip()}")

        # Test uv (if available)
        result = sandbox.process.exec("which uv || echo 'uv not installed'")
        print(f"   UV: {result.result.strip()}")

        # Test git
        result = sandbox.process.exec("git --version")
        print(f"   Git: {result.result.strip()}")

        # Test environment variable injection
        print("\n🔒 Testing environment injection...")

        # Set environment variables like we would for a worker
        env_commands = """
export TASK_ID="test-task-123"
export SANDBOX_ID="test-sandbox-456"
export MCP_SERVER_URL="http://host.docker.internal:18000"
echo "TASK_ID=$TASK_ID"
echo "SANDBOX_ID=$SANDBOX_ID"
"""
        result = sandbox.process.exec(env_commands)
        for line in result.result.strip().split("\n"):
            if line:
                print(f"   {line}")

        # Test file creation
        print("\n📁 Testing file operations...")
        sandbox.process.exec("echo 'Test file content' > /tmp/test.txt")
        result = sandbox.process.exec("cat /tmp/test.txt")
        print(f"   File content: {result.result.strip()}")

        # Test Python script execution
        print("\n🐍 Testing Python execution...")
        python_script = """
import sys
import json
result = {"python_version": sys.version.split()[0], "status": "ok"}
print(json.dumps(result))
"""
        sandbox.process.exec(f"echo '{python_script}' > /tmp/test.py")
        result = sandbox.process.exec("python /tmp/test.py")
        print(f"   Python output: {result.result.strip()}")

        print("\n" + "=" * 60)
        print("✅ ALL SANDBOX TESTS PASSED!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if sandbox:
            print("\n🧹 Cleaning up sandbox...")
            try:
                daytona.delete(sandbox)
                print("✅ Sandbox deleted")
            except Exception as e:
                print(f"⚠️  Cleanup error: {e}")


if __name__ == "__main__":
    success = test_sandbox()
    sys.exit(0 if success else 1)
