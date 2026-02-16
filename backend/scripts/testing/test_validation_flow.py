#!/usr/bin/env python
"""Manual test script for the validation flow.

This script tests the complete validation workflow:
1. Creates test data (project, ticket, task)
2. Simulates implementer completion
3. Requests validation
4. Simulates validator result (pass or fail)
5. Verifies final task state

Usage:
    # Test passing validation
    uv run python scripts/testing/test_validation_flow.py --pass

    # Test failing validation
    uv run python scripts/testing/test_validation_flow.py --fail

    # Test full retry loop (fail, then pass)
    uv run python scripts/testing/test_validation_flow.py --retry

    # Dry run (don't actually spawn sandboxes)
    uv run python scripts/testing/test_validation_flow.py --dry-run --pass
"""

import argparse
import asyncio
import os
import sys
from uuid import uuid4

# Ensure we can import from omoi_os
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Set environment before imports
os.environ.setdefault("TASK_VALIDATION_ENABLED", "true")
os.environ.setdefault("MAX_VALIDATION_ITERATIONS", "3")


def create_test_data(db):
    """Create test project, ticket, and task."""
    from omoi_os.models.project import Project
    from omoi_os.models.ticket import Ticket
    from omoi_os.models.task import Task
    from omoi_os.models.user import User

    with db.get_session() as session:
        # Create or get test user
        user = (
            session.query(User)
            .filter(User.email == "validation-test@example.com")
            .first()
        )
        if not user:
            from omoi_os.services.auth_service import AuthService

            auth = AuthService(
                db=db,
                jwt_secret="test-secret",
                jwt_algorithm="HS256",
                access_token_expire_minutes=15,
                refresh_token_expire_days=7,
            )
            user = User(
                email="validation-test@example.com",
                full_name="Validation Test User",
                hashed_password=auth.hash_password("TestPass123!"),
                is_active=True,
                is_verified=True,
                attributes={"github_access_token": "ghp_test_token_for_validation"},
            )
            session.add(user)
            session.commit()
            print(f"✅ Created test user: {user.email}")
        else:
            print(f"✅ Using existing user: {user.email}")

        # Create project
        project = Project(
            name=f"Validation Test Project {uuid4().hex[:6]}",
            github_owner="test-owner",
            github_repo="test-repo",
            created_by=user.id,
        )
        session.add(project)
        session.commit()
        print(f"✅ Created project: {project.name} (ID: {project.id})")

        # Create ticket
        ticket = Ticket(
            title="Implement Feature for Validation Test",
            description="This ticket tests the validation flow",
            phase_id="PHASE_IMPLEMENTATION",
            status="in_progress",
            project_id=project.id,
        )
        session.add(ticket)
        session.commit()
        print(f"✅ Created ticket: {ticket.title} (ID: {ticket.id})")

        # Create task
        sandbox_id = f"impl-sandbox-{uuid4().hex[:8]}"
        branch_name = f"feature/validation-test-{uuid4().hex[:6]}"
        task = Task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Implement user authentication flow",
            status="running",
            sandbox_id=sandbox_id,
            result={"branch_name": branch_name},
        )
        session.add(task)
        session.commit()
        print(f"✅ Created task: {task.description}")
        print(f"   - Task ID: {task.id}")
        print(f"   - Sandbox ID: {sandbox_id}")
        print(f"   - Branch: {branch_name}")

        return {
            "user_id": str(user.id),
            "project_id": str(project.id),
            "ticket_id": str(ticket.id),
            "task_id": str(task.id),
            "sandbox_id": sandbox_id,
            "branch_name": branch_name,
        }


async def test_validation_pass(db, event_bus, test_data, dry_run=False):
    """Test validation that passes on first attempt."""
    from omoi_os.services.task_validator import TaskValidatorService
    from unittest.mock import AsyncMock, patch

    print("\n" + "=" * 60)
    print("TESTING: Validation PASS Flow")
    print("=" * 60)

    validator = TaskValidatorService(db=db, event_bus=event_bus)

    if dry_run:
        # Mock the spawner
        with patch.object(
            validator, "_spawn_validator", new_callable=AsyncMock
        ) as mock_spawn:
            validator_agent_id = str(uuid4())
            mock_spawn.return_value = {
                "sandbox_id": f"validator-sandbox-{uuid4().hex[:8]}",
                "agent_id": validator_agent_id,
            }

            await _run_validation_pass(validator, db, test_data, validator_agent_id)
    else:
        # Real spawner (requires Daytona)
        print("⚠️  Real spawner mode - ensure Daytona is running")
        validation_id = await validator.request_validation(
            task_id=test_data["task_id"],
            sandbox_id=test_data["sandbox_id"],
            implementation_result={
                "success": True,
                "branch_name": test_data["branch_name"],
            },
        )
        print(f"📋 Validation requested: {validation_id}")
        print("⏳ Waiting for validator to complete (check Daytona logs)...")
        print("   When validator finishes, run:")
        print(
            "   curl -X POST http://localhost:18000/api/v1/sandbox/<validator-sandbox>/validation-result \\"
        )
        print('     -H "Content-Type: application/json" \\')
        print(
            f'     -d \'{{"task_id": "{test_data["task_id"]}", "passed": true, "feedback": "All tests pass"}}\''
        )


async def _run_validation_pass(validator, db, test_data, validator_agent_id):
    """Run the pass validation flow (used in dry-run mode)."""
    from omoi_os.models.task import Task
    from omoi_os.models.validation_review import ValidationReview

    # Step 1: Request validation
    print("\n📤 Step 1: Requesting validation...")
    validation_id = await validator.request_validation(
        task_id=test_data["task_id"],
        sandbox_id=test_data["sandbox_id"],
        implementation_result={
            "success": True,
            "branch_name": test_data["branch_name"],
            "commit_sha": "abc123def456",
        },
    )
    print(f"   Validation ID: {validation_id}")

    # Verify status
    with db.get_session() as session:
        task = session.get(Task, test_data["task_id"])
        print(f"   Task status: {task.status}")
        assert task.status == "pending_validation", (
            f"Expected pending_validation, got {task.status}"
        )
        print("   ✅ Task is pending_validation")

    # Step 2: Simulate validation passing
    print("\n✅ Step 2: Simulating validation PASS...")
    await validator.handle_validation_result(
        task_id=test_data["task_id"],
        validator_agent_id=validator_agent_id,
        passed=True,
        feedback="All checks passed! Tests: 42/42 pass, Build: success, PR: created",
        evidence={
            "tests": {"passed": 42, "failed": 0, "skipped": 0},
            "build": {"status": "success", "duration_s": 12.5},
            "pr": {"url": "https://github.com/test-owner/test-repo/pull/1"},
            "git_status": "clean",
        },
    )

    # Verify final state
    with db.get_session() as session:
        task = session.get(Task, test_data["task_id"])
        print(f"   Task status: {task.status}")
        assert task.status == "completed", f"Expected completed, got {task.status}"
        print("   ✅ Task is completed")

        reviews = (
            session.query(ValidationReview)
            .filter(ValidationReview.task_id == test_data["task_id"])
            .all()
        )
        print(f"   Validation reviews: {len(reviews)}")
        assert len(reviews) == 1
        assert reviews[0].validation_passed is True
        print("   ✅ ValidationReview record created")

    print("\n" + "=" * 60)
    print("✅ VALIDATION PASS TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)


async def test_validation_fail(db, event_bus, test_data, dry_run=False):
    """Test validation that fails."""
    from omoi_os.services.task_validator import TaskValidatorService
    from unittest.mock import AsyncMock, patch

    print("\n" + "=" * 60)
    print("TESTING: Validation FAIL Flow")
    print("=" * 60)

    validator = TaskValidatorService(db=db, event_bus=event_bus)

    if dry_run:
        with patch.object(
            validator, "_spawn_validator", new_callable=AsyncMock
        ) as mock_spawn:
            validator_agent_id = str(uuid4())
            mock_spawn.return_value = {
                "sandbox_id": f"validator-sandbox-{uuid4().hex[:8]}",
                "agent_id": validator_agent_id,
            }

            await _run_validation_fail(validator, db, test_data, validator_agent_id)
    else:
        print("⚠️  Real spawner mode - run with --dry-run for testing")


async def _run_validation_fail(validator, db, test_data, validator_agent_id):
    """Run the fail validation flow."""
    from omoi_os.models.task import Task

    # Step 1: Request validation
    print("\n📤 Step 1: Requesting validation...")
    await validator.request_validation(
        task_id=test_data["task_id"],
        sandbox_id=test_data["sandbox_id"],
        implementation_result={
            "success": True,
            "branch_name": test_data["branch_name"],
        },
    )

    with db.get_session() as session:
        task = session.get(Task, test_data["task_id"])
        print(f"   Task status: {task.status}")
        assert task.status == "pending_validation"
        print("   ✅ Task is pending_validation")

    # Step 2: Simulate validation failing
    print("\n❌ Step 2: Simulating validation FAIL...")
    await validator.handle_validation_result(
        task_id=test_data["task_id"],
        validator_agent_id=validator_agent_id,
        passed=False,
        feedback="Tests failing: 3 unit tests failed. Build passes but tests must be fixed.",
        evidence={
            "tests": {"passed": 39, "failed": 3, "skipped": 0},
            "failed_tests": ["test_login", "test_logout", "test_session_expiry"],
            "build": {"status": "success"},
        },
        recommendations=[
            "Fix test_login: Expected 200, got 401 - check auth middleware",
            "Fix test_logout: Session not invalidated - check session cleanup",
            "Fix test_session_expiry: Token still valid after expiry - check JWT validation",
        ],
    )

    # Verify state
    with db.get_session() as session:
        task = session.get(Task, test_data["task_id"])
        print(f"   Task status: {task.status}")
        assert task.status == "needs_revision", (
            f"Expected needs_revision, got {task.status}"
        )
        print("   ✅ Task is needs_revision")
        print(
            f"   Revision feedback: {task.result.get('revision_feedback', '')[:50]}..."
        )
        print(
            f"   Recommendations: {len(task.result.get('revision_recommendations', []))} items"
        )

    print("\n" + "=" * 60)
    print("✅ VALIDATION FAIL TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)


async def test_validation_retry(db, event_bus, test_data, dry_run=False):
    """Test validation that fails then passes on retry."""
    from omoi_os.services.task_validator import TaskValidatorService
    from omoi_os.models.task import Task
    from omoi_os.models.validation_review import ValidationReview
    from unittest.mock import AsyncMock, patch

    print("\n" + "=" * 60)
    print("TESTING: Validation RETRY Flow (Fail -> Pass)")
    print("=" * 60)

    validator = TaskValidatorService(db=db, event_bus=event_bus)

    if not dry_run:
        print("⚠️  Retry test requires --dry-run mode")
        return

    with patch.object(
        validator, "_spawn_validator", new_callable=AsyncMock
    ) as mock_spawn:
        # First validation - FAIL
        validator_agent_id_1 = str(uuid4())
        mock_spawn.return_value = {
            "sandbox_id": f"validator-1-{uuid4().hex[:8]}",
            "agent_id": validator_agent_id_1,
        }

        print("\n📤 Step 1: First validation request...")
        await validator.request_validation(
            task_id=test_data["task_id"],
            sandbox_id=test_data["sandbox_id"],
            implementation_result={
                "success": True,
                "branch_name": test_data["branch_name"],
            },
        )

        print("❌ Step 2: First validation FAILS...")
        await validator.handle_validation_result(
            task_id=test_data["task_id"],
            validator_agent_id=validator_agent_id_1,
            passed=False,
            feedback="Tests failing: 3 tests failed",
            recommendations=["Fix the tests"],
        )

        with db.get_session() as session:
            task = session.get(Task, test_data["task_id"])
            assert task.status == "needs_revision"
            print(f"   Task status: {task.status}")
            print(f"   Iteration: {task.result.get('validation_iteration')}")

        # Simulate implementer fixing and re-running
        print("\n🔧 Step 3: Simulating implementer fix...")
        with db.get_session() as session:
            task = session.get(Task, test_data["task_id"])
            task.status = "running"  # Back to running
            session.commit()
            print("   Task reset to running")

        # Second validation - PASS
        validator_agent_id_2 = str(uuid4())
        mock_spawn.return_value = {
            "sandbox_id": f"validator-2-{uuid4().hex[:8]}",
            "agent_id": validator_agent_id_2,
        }

        print("\n📤 Step 4: Second validation request...")
        await validator.request_validation(
            task_id=test_data["task_id"],
            sandbox_id=test_data["sandbox_id"],
            implementation_result={
                "success": True,
                "branch_name": test_data["branch_name"],
                "fixed_tests": True,
            },
        )

        with db.get_session() as session:
            task = session.get(Task, test_data["task_id"])
            print(f"   Iteration: {task.result.get('validation_iteration')}")
            assert task.result.get("validation_iteration") == 2

        print("✅ Step 5: Second validation PASSES...")
        await validator.handle_validation_result(
            task_id=test_data["task_id"],
            validator_agent_id=validator_agent_id_2,
            passed=True,
            feedback="All issues resolved! All 42 tests pass.",
        )

        # Verify final state
        with db.get_session() as session:
            task = session.get(Task, test_data["task_id"])
            assert task.status == "completed"
            print(f"   Final status: {task.status}")

            reviews = (
                session.query(ValidationReview)
                .filter(ValidationReview.task_id == test_data["task_id"])
                .order_by(ValidationReview.iteration_number)
                .all()
            )
            print(f"   Total reviews: {len(reviews)}")
            assert len(reviews) == 2
            assert reviews[0].validation_passed is False
            assert reviews[1].validation_passed is True

    print("\n" + "=" * 60)
    print("✅ VALIDATION RETRY TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Test the validation flow")
    parser.add_argument(
        "--pass", dest="test_pass", action="store_true", help="Test passing validation"
    )
    parser.add_argument(
        "--fail", dest="test_fail", action="store_true", help="Test failing validation"
    )
    parser.add_argument(
        "--retry", action="store_true", help="Test fail->pass retry flow"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't spawn real sandboxes"
    )
    args = parser.parse_args()

    if not any([args.test_pass, args.test_fail, args.retry]):
        parser.print_help()
        print("\n⚠️  Please specify at least one test: --pass, --fail, or --retry")
        sys.exit(1)

    # Initialize services
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.event_bus import EventBusService

    db_url = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:15432/app_db"
    )
    redis_url = os.getenv("REDIS_URL", "redis://localhost:16379")

    print("🔧 Initializing services...")
    db = DatabaseService(db_url)
    event_bus = EventBusService(redis_url)
    print(f"   Database: {db_url}")
    print(f"   Redis: {redis_url}")

    # Create test data
    print("\n📦 Creating test data...")
    test_data = create_test_data(db)

    # Run requested tests
    if args.test_pass:
        await test_validation_pass(db, event_bus, test_data, dry_run=args.dry_run)

    if args.test_fail:
        # Need fresh test data for fail test
        test_data = create_test_data(db)
        await test_validation_fail(db, event_bus, test_data, dry_run=args.dry_run)

    if args.retry:
        # Need fresh test data for retry test
        test_data = create_test_data(db)
        await test_validation_retry(db, event_bus, test_data, dry_run=args.dry_run)

    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
