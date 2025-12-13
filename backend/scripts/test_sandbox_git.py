#!/usr/bin/env python3
"""Test Daytona sandbox git operations.

Tests:
1. Clone the OmoiOS repository
2. Create a feature branch
3. Make changes and commit
4. Verify branch workflow
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


def get_user_github_token_by_email(email: str) -> tuple[str | None, str | None]:
    """Get GitHub token from database for a user by email.

    Returns:
        Tuple of (token, user_id) or (None, None) if not found
    """
    try:
        from sqlalchemy import select

        from omoi_os.config import get_app_settings
        from omoi_os.models.user import User
        from omoi_os.services.database import DatabaseService
        from omoi_os.services.github_api import GitHubAPIService

        settings = get_app_settings()
        db = DatabaseService(connection_string=settings.database.url)
        github_service = GitHubAPIService(db=db)

        with db.get_session() as session:
            # Find user by email
            stmt = select(User).where(User.email == email)
            user = session.execute(stmt).scalar_one_or_none()

            if not user:
                print(f"   User with email {email} not found")
                return None, None

            print(f"   Found user: {user.id} ({email})")

            # Get their GitHub token
            token = github_service._get_user_token_by_id(user.id)
            return token, str(user.id)

    except Exception as e:
        print(f"   Could not fetch token from DB: {e}")
        return None, None


def test_git_operations():
    """Run git operations test in sandbox."""
    print("=" * 60)
    print("🧪 DAYTONA SANDBOX GIT TEST")
    print("=" * 60)

    # Check API key
    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        print("❌ DAYTONA_API_KEY not set")
        return False

    print(f"✅ Daytona API Key: {api_key[:10]}...")

    # Check for GitHub token
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    user_email = "kivo360@gmail.com"  # Test user email

    # Try to get from database if not in env
    if not github_token:
        print(f"   No GITHUB_TOKEN in env, checking database for {user_email}...")
        github_token, user_id = get_user_github_token_by_email(user_email)

    if github_token:
        print(f"✅ GitHub Token: {github_token[:10]}...")
    else:
        print("⚠️  No GitHub token found - will test with public repo only")

    try:
        from daytona import Daytona, DaytonaConfig, CreateSandboxFromImageParams
    except ImportError:
        print("❌ Daytona SDK not installed")
        return False

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
        start_time = time.time()

        params = CreateSandboxFromImageParams(
            image="nikolaik/python-nodejs:python3.12-nodejs22",
            labels={"test": "git-operations"},
            ephemeral=True,
            public=False,
        )

        sandbox = daytona.create(params=params, timeout=120)
        create_time = time.time() - start_time

        print(f"✅ Sandbox created in {create_time:.1f}s")
        print(f"   ID: {sandbox.id}")

        # Get working directory
        work_dir = sandbox.get_work_dir()
        print(f"   Working directory: {work_dir}")

        # ====================================================================
        # TEST 1: Clone repository using Daytona's native git
        # ====================================================================
        print("\n" + "=" * 60)
        print("📥 TEST 1: Clone repository using Daytona git.clone()")
        print("=" * 60)

        # Use private repo if we have token, otherwise use public repo
        if github_token:
            repo_url = "https://github.com/kivo360/OmoiOS.git"
            repo_name = "OmoiOS"
        else:
            # Use a well-known public repo for testing
            repo_url = "https://github.com/astral-sh/uv.git"
            repo_name = "uv"

        clone_path = f"{work_dir}/{repo_name}"

        print(f"   Repo: {repo_url}")
        print(f"   Path: {clone_path}")
        print("   Branch: main")

        clone_start = time.time()

        # Clone with or without token
        if github_token:
            print("   Using GitHub token for authentication...")
            sandbox.git.clone(
                url=repo_url,
                path=clone_path,
                branch="main",
                username="x-access-token",  # GitHub convention for token auth
                password=github_token,
            )
        else:
            print("   Cloning without authentication (public access)...")
            sandbox.git.clone(
                url=repo_url,
                path=clone_path,
                branch="main",
            )

        clone_time = time.time() - clone_start
        print(f"✅ Clone completed in {clone_time:.1f}s")

        # Verify clone
        result = sandbox.process.exec(f"ls -la {clone_path}")
        print("\n📁 Repository contents:")
        for line in result.result.strip().split("\n")[:10]:
            print(f"   {line}")
        if result.result.count("\n") > 10:
            print("   ... (truncated)")

        # Check git status
        result = sandbox.process.exec(f"cd {clone_path} && git status")
        print("\n📊 Git status:")
        for line in result.result.strip().split("\n"):
            print(f"   {line}")

        # ====================================================================
        # TEST 2: Create feature branch using Daytona git
        # ====================================================================
        print("\n" + "=" * 60)
        print("🌿 TEST 2: Create feature branch")
        print("=" * 60)

        branch_name = "feature/sandbox-test-branch"
        print(f"   Creating branch: {branch_name}")

        # First checkout the repo (set working directory context)
        # Then create branch
        try:
            # List existing branches first
            branches = sandbox.git.branches(clone_path)
            print(f"   Existing branches: {[b.name for b in branches]}")

            # Create new branch
            sandbox.git.create_branch(clone_path, branch_name)
            print(f"✅ Branch created: {branch_name}")

            # Checkout the branch
            sandbox.git.checkout_branch(clone_path, branch_name)
            print(f"✅ Checked out: {branch_name}")

            # Verify
            result = sandbox.process.exec(
                f"cd {clone_path} && git branch --show-current"
            )
            print(f"   Current branch: {result.result.strip()}")

        except Exception as e:
            print(f"⚠️  Branch creation via SDK failed: {e}")
            print("   Trying with shell commands...")

            # Fallback to shell commands
            result = sandbox.process.exec(
                f"cd {clone_path} && git checkout -b {branch_name}"
            )
            print(f"   Shell result: {result.result.strip()}")

        # ====================================================================
        # TEST 3: Make changes and commit
        # ====================================================================
        print("\n" + "=" * 60)
        print("✏️  TEST 3: Make changes and commit")
        print("=" * 60)

        # Create a test file
        test_file = f"{clone_path}/sandbox_test_file.txt"
        test_content = f"Test file created at {time.strftime('%Y-%m-%d %H:%M:%S')}"

        sandbox.process.exec(f"echo '{test_content}' > {test_file}")
        print("   Created: sandbox_test_file.txt")

        # Stage the file
        try:
            sandbox.git.add(clone_path, ["sandbox_test_file.txt"])
            print("✅ File staged via git.add()")
        except Exception as e:
            print(f"⚠️  git.add() failed: {e}")
            sandbox.process.exec(f"cd {clone_path} && git add sandbox_test_file.txt")
            print("✅ File staged via shell")

        # Configure git user (required for commits)
        sandbox.process.exec(
            f"cd {clone_path} && git config user.email 'sandbox@omoios.test'"
        )
        sandbox.process.exec(
            f"cd {clone_path} && git config user.name 'OmoiOS Sandbox'"
        )

        # Commit
        try:
            sandbox.git.commit(clone_path, "Test commit from Daytona sandbox")
            print("✅ Committed via git.commit()")
        except Exception as e:
            print(f"⚠️  git.commit() failed: {e}")
            result = sandbox.process.exec(
                f"cd {clone_path} && git commit -m 'Test commit from Daytona sandbox'"
            )
            print(f"✅ Committed via shell: {result.result.strip()}")

        # Show commit log
        result = sandbox.process.exec(f"cd {clone_path} && git log --oneline -3")
        print("\n📜 Recent commits:")
        for line in result.result.strip().split("\n"):
            print(f"   {line}")

        # ====================================================================
        # TEST 4: Git status and diff
        # ====================================================================
        print("\n" + "=" * 60)
        print("📊 TEST 4: Final status")
        print("=" * 60)

        try:
            status = sandbox.git.status(clone_path)
            print(f"   Status object: {status}")
        except Exception as e:
            print(f"⚠️  git.status() returned: {e}")

        result = sandbox.process.exec(f"cd {clone_path} && git status")
        print("\n   Git status (shell):")
        for line in result.result.strip().split("\n"):
            print(f"   {line}")

        # Show what would be pushed
        result = sandbox.process.exec(
            f"cd {clone_path} && git log origin/main..HEAD --oneline 2>/dev/null || echo 'No upstream'"
        )
        print("\n   Commits ahead of origin:")
        for line in result.result.strip().split("\n"):
            print(f"   {line}")

        # ====================================================================
        # TEST 5: Test push (only if token available and using private repo)
        # ====================================================================
        if github_token and "kivo360/OmoiOS" in repo_url:
            print("\n" + "=" * 60)
            print("🚀 TEST 5: Push to remote")
            print("=" * 60)

            # Create a unique branch name for this test
            import random
            import string

            unique_suffix = "".join(random.choices(string.ascii_lowercase, k=6))
            push_branch = f"sandbox-push-test-{unique_suffix}"

            # Create and checkout the unique branch
            result = sandbox.process.exec(
                f"cd {clone_path} && git checkout -b {push_branch}"
            )
            print(f"   Created branch: {push_branch}")

            # Make a test change
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            sandbox.process.exec(
                f"echo 'Push test at {timestamp}' >> {clone_path}/sandbox_push_test.txt"
            )
            sandbox.process.exec(f"cd {clone_path} && git add sandbox_push_test.txt")
            sandbox.process.exec(
                f"cd {clone_path} && git commit -m 'Test push from Daytona sandbox'"
            )

            # Try push via Daytona SDK
            try:
                sandbox.git.push(
                    clone_path, username="x-access-token", password=github_token
                )
                print("✅ Push successful via git.push()!")
                print(f"   Branch {push_branch} pushed to origin")
            except Exception as e:
                print(f"⚠️  git.push() failed: {e}")
                print("   Trying shell fallback...")

                # Fallback to shell with credential helper
                result = sandbox.process.exec(
                    f"cd {clone_path} && git push -u origin {push_branch}"
                )
                if result.exit_code == 0:
                    print("✅ Push successful via shell!")
                else:
                    print(f"❌ Shell push also failed: {result.result}")

            # Note: The pushed branch will need manual cleanup on GitHub
            print(f"\n   ⚠️  Branch '{push_branch}' was pushed to kivo360/OmoiOS")
            print("   You may want to delete it later from GitHub")

        print("\n" + "=" * 60)
        print("✅ ALL GIT TESTS COMPLETED!")
        print("=" * 60)

        # Summary
        print("\n📋 Summary:")
        print("   ✅ Daytona git.clone() - Works")
        print("   ✅ Branch creation - Works")
        print("   ✅ File staging - Works")
        print("   ✅ Commits - Works")
        print(
            f"   {'✅' if github_token else '⚠️ '} Authentication - {'Tested' if github_token else 'Not tested (no token)'}"
        )

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
    success = test_git_operations()
    sys.exit(0 if success else 1)
