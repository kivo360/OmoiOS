#!/usr/bin/env python
"""
Test script to verify the spec state machine worker runs in isolated environments.

This script simulates the minimal sandbox environment without:
- Database connection
- Redis connection
- Full backend dependencies

Usage:
    python scripts/test_spec_worker_isolated.py

Expected outcome: All checks pass, demonstrating the worker can run standalone.
"""

import asyncio
import base64
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def print_header(msg: str) -> None:
    """Print a header with separators."""
    print()
    print("=" * 60)
    print(msg)
    print("=" * 60)


def print_check(check: str, passed: bool, details: str = "") -> None:
    """Print a check result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {check}")
    if details:
        print(f"         {details}")


async def test_imports() -> bool:
    """Test that all required modules can be imported."""
    print_header("Testing Module Imports")
    all_passed = True

    # Test core imports
    try:
        from omoi_os.workers.spec_state_machine import (
            SpecStateMachine,
            SpecPhase,
            PhaseResult,
            _MockSpec,
        )
        print_check("SpecStateMachine imports", True)
    except ImportError as e:
        print_check("SpecStateMachine imports", False, str(e))
        all_passed = False

    # Test evaluator imports
    try:
        from omoi_os.evals import (
            ExplorationEvaluator,
            RequirementEvaluator,
            DesignEvaluator,
            TaskEvaluator,
        )
        print_check("Evaluators import", True)
    except ImportError as e:
        print_check("Evaluators import", False, str(e))
        all_passed = False

    # Test schema imports
    try:
        from omoi_os.schemas.spec_generation import SpecPhase as SchemaPhase
        print_check("Schema imports", True)
    except ImportError as e:
        print_check("Schema imports", False, str(e))
        all_passed = False

    # Test SDK imports (graceful if not available)
    try:
        from claude_code_sdk import query, ClaudeCodeOptions
        print_check("Claude SDK imports", True)
    except ImportError as e:
        print_check("Claude SDK imports", True, f"(Optional - not installed: {e})")

    return all_passed


async def test_mock_database_session() -> bool:
    """Test the mock database session works."""
    print_header("Testing Mock Database Session")
    all_passed = True

    from omoi_os.workers.claude_sandbox_worker import _MockDatabaseSession, _MockResult

    # Create mock session
    db = _MockDatabaseSession()
    print_check("Mock session created", True)

    # Test async methods
    try:
        await db.commit()
        await db.flush()
        await db.refresh(object())
        print_check("Async methods work", True)
    except Exception as e:
        print_check("Async methods work", False, str(e))
        all_passed = False

    # Test execute returns MockResult
    try:
        result = await db.execute("SELECT 1")
        assert isinstance(result, _MockResult)
        print_check("Execute returns MockResult", True)
    except Exception as e:
        print_check("Execute returns MockResult", False, str(e))
        all_passed = False

    # Test scalar_one_or_none
    try:
        result = await db.execute("SELECT 1")
        value = result.scalar_one_or_none()
        assert value is None
        print_check("scalar_one_or_none returns None", True)
    except Exception as e:
        print_check("scalar_one_or_none returns None", False, str(e))
        all_passed = False

    return all_passed


async def test_mock_spec() -> bool:
    """Test the mock spec object."""
    print_header("Testing Mock Spec Object")
    all_passed = True

    from omoi_os.workers.spec_state_machine import _MockSpec

    # Create mock spec
    spec = _MockSpec("test-spec-123", "Test Title", "Test Description")
    print_check("Mock spec created", True)

    # Check attributes
    try:
        assert spec.id == "test-spec-123"
        assert spec.title == "Test Title"
        assert spec.description == "Test Description"
        assert spec.current_phase == "explore"
        assert spec.is_mock is True
        print_check("Attributes correct", True)
    except AssertionError as e:
        print_check("Attributes correct", False, str(e))
        all_passed = False

    # Check mutability
    try:
        spec.current_phase = "design"
        spec.phase_data = {"explore": {"data": 1}}
        assert spec.current_phase == "design"
        assert spec.phase_data["explore"]["data"] == 1
        print_check("Attributes mutable", True)
    except Exception as e:
        print_check("Attributes mutable", False, str(e))
        all_passed = False

    return all_passed


async def test_state_machine_creation() -> bool:
    """Test state machine can be created without database."""
    print_header("Testing State Machine Creation")
    all_passed = True

    from omoi_os.workers.spec_state_machine import SpecStateMachine, SpecPhase
    from omoi_os.workers.claude_sandbox_worker import _MockDatabaseSession

    # Create with mock database
    workspace = tempfile.mkdtemp(prefix="spec_test_")
    try:
        db = _MockDatabaseSession()
        machine = SpecStateMachine(
            spec_id="test-123",
            db_session=db,
            working_directory=workspace,
        )
        print_check("State machine created", True)

        # Check evaluators
        assert len(machine.evaluators) == 4
        print_check("Evaluators initialized (4)", True)

        # Check phase order
        assert len(machine.PHASE_ORDER) == 6
        print_check("Phase order correct (6 phases)", True)

        # Check timeouts
        assert all(t > 0 for t in machine.PHASE_TIMEOUTS.values())
        print_check("Timeouts configured", True)

    except Exception as e:
        print_check("State machine creation", False, str(e))
        all_passed = False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    return all_passed


async def test_load_spec_fallback() -> bool:
    """Test load_spec falls back to mock spec when database unavailable."""
    print_header("Testing load_spec Fallback to Mock")
    all_passed = True

    from omoi_os.workers.spec_state_machine import SpecStateMachine, _MockSpec
    from omoi_os.workers.claude_sandbox_worker import _MockDatabaseSession

    workspace = tempfile.mkdtemp(prefix="spec_test_")
    try:
        db = _MockDatabaseSession()
        machine = SpecStateMachine(
            spec_id="test-123",
            db_session=db,
            working_directory=workspace,
        )

        # Call load_spec - should return mock since DB returns None
        spec = await machine.load_spec()

        if spec is None:
            print_check("load_spec returned result", False, "Got None")
            all_passed = False
        elif isinstance(spec, _MockSpec):
            print_check("load_spec returns _MockSpec", True)
            assert spec.id == "test-123"
            print_check("Mock spec has correct ID", True)
        else:
            print_check("load_spec returned unexpected type", False, type(spec).__name__)
            all_passed = False

    except Exception as e:
        print_check("load_spec fallback", False, str(e))
        all_passed = False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    return all_passed


async def test_file_checkpoints() -> bool:
    """Test file-based checkpoints work."""
    print_header("Testing File Checkpoints")
    all_passed = True

    from omoi_os.workers.spec_state_machine import SpecStateMachine, SpecPhase, _MockSpec
    from omoi_os.workers.claude_sandbox_worker import _MockDatabaseSession

    workspace = tempfile.mkdtemp(prefix="spec_test_")
    try:
        db = _MockDatabaseSession()
        machine = SpecStateMachine(
            spec_id="test-123",
            db_session=db,
            working_directory=workspace,
        )

        # Write phase checkpoint
        phase_data = {"project_type": "api", "tech_stack": ["python"]}
        await machine._write_file_checkpoint(SpecPhase.EXPLORE, phase_data)

        # Verify file exists
        phase_file = Path(workspace) / ".omoi_os" / "phase_data" / "explore.json"
        if phase_file.exists():
            print_check("Phase checkpoint file created", True)

            # Verify content
            with open(phase_file) as f:
                loaded = json.load(f)
            if loaded == phase_data:
                print_check("Phase checkpoint content correct", True)
            else:
                print_check("Phase checkpoint content correct", False, f"Got: {loaded}")
                all_passed = False
        else:
            print_check("Phase checkpoint file created", False)
            all_passed = False

        # Test save_checkpoint creates state file
        mock_spec = _MockSpec("test-123")
        mock_spec.current_phase = "requirements"
        await machine.save_checkpoint(mock_spec)

        state_file = Path(workspace) / ".omoi_os" / "checkpoints" / "state.json"
        if state_file.exists():
            print_check("State checkpoint file created", True)
        else:
            print_check("State checkpoint file created", False)
            all_passed = False

    except Exception as e:
        print_check("File checkpoints", False, str(e))
        all_passed = False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    return all_passed


async def test_checkpoint_restore() -> bool:
    """Test checkpoint restoration works."""
    print_header("Testing Checkpoint Restoration")
    all_passed = True

    from omoi_os.workers.spec_state_machine import SpecStateMachine, _MockSpec
    from omoi_os.workers.claude_sandbox_worker import _MockDatabaseSession

    workspace = tempfile.mkdtemp(prefix="spec_test_")
    try:
        # Create checkpoint file first
        checkpoint_dir = Path(workspace) / ".omoi_os" / "checkpoints"
        checkpoint_dir.mkdir(parents=True)
        state_file = checkpoint_dir / "state.json"
        state_file.write_text(json.dumps({
            "title": "Restored Spec",
            "description": "A restored specification",
            "current_phase": "design",
            "phase_data": {"explore": {"type": "api"}},
            "phase_attempts": {"explore": 2},
        }))

        # Create state machine and load spec
        db = _MockDatabaseSession()
        machine = SpecStateMachine(
            spec_id="test-123",
            db_session=db,
            working_directory=workspace,
        )

        spec = await machine.load_spec()

        if isinstance(spec, _MockSpec):
            print_check("Restored spec is _MockSpec", True)

            if spec.current_phase == "design":
                print_check("Current phase restored (design)", True)
            else:
                print_check("Current phase restored (design)", False, f"Got: {spec.current_phase}")
                all_passed = False

            if spec.title == "Restored Spec":
                print_check("Title restored", True)
            else:
                print_check("Title restored", False, f"Got: {spec.title}")
                all_passed = False

        else:
            print_check("Checkpoint restoration", False, f"Got type: {type(spec)}")
            all_passed = False

    except Exception as e:
        print_check("Checkpoint restoration", False, str(e))
        all_passed = False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    return all_passed


async def test_worker_config_env_vars() -> bool:
    """Test WorkerConfig reads spec environment variables."""
    print_header("Testing WorkerConfig Environment Variables")
    all_passed = True

    # Set up environment
    phase_data = {"explore": {"type": "web_app"}}
    encoded_data = base64.b64encode(json.dumps(phase_data).encode()).decode()

    original_env = {}
    test_env = {
        "SPEC_ID": "spec-test-456",
        "SPEC_PHASE": "requirements",
        "PHASE_DATA_B64": encoded_data,
    }

    # Save and set env vars
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        # Need to force re-import to pick up new env vars
        # In real usage, the worker is started with these vars already set
        from omoi_os.workers.claude_sandbox_worker import WorkerConfig

        config = WorkerConfig()

        if config.spec_id == "spec-test-456":
            print_check("SPEC_ID read correctly", True)
        else:
            print_check("SPEC_ID read correctly", False, f"Got: {config.spec_id}")
            all_passed = False

        if config.spec_phase == "requirements":
            print_check("SPEC_PHASE read correctly", True)
        else:
            print_check("SPEC_PHASE read correctly", False, f"Got: {config.spec_phase}")
            all_passed = False

        if config.phase_data == phase_data:
            print_check("PHASE_DATA_B64 decoded correctly", True)
        else:
            print_check("PHASE_DATA_B64 decoded correctly", False, f"Got: {config.phase_data}")
            all_passed = False

    except Exception as e:
        print_check("WorkerConfig env vars", False, str(e))
        all_passed = False
    finally:
        # Restore original env
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    return all_passed


async def test_evaluators() -> bool:
    """Test evaluators work correctly."""
    print_header("Testing Evaluators")
    all_passed = True

    from omoi_os.evals import ExplorationEvaluator

    evaluator = ExplorationEvaluator()
    print_check("ExplorationEvaluator created", True)

    # Test with empty output (should fail)
    result = evaluator.evaluate({})
    if not result.passed:
        print_check("Empty output fails evaluation", True)
    else:
        print_check("Empty output fails evaluation", False, "Should have failed")
        all_passed = False

    # Test with valid output
    valid_output = {
        "project_type": "web_app",
        "tech_stack": ["python", "fastapi"],
        "existing_models": [{"name": "User", "file": "models.py", "fields": ["id"]}],
        "existing_routes": ["/api/users"],
        "database_type": "postgresql",
        "project_structure": {"directories": ["src/"], "entry_point": "main.py"},
        "coding_conventions": {"style_guide": "pep8", "naming": "snake_case"},
        "explored_files": ["main.py", "models.py"],
    }

    result = evaluator.evaluate(valid_output)
    if result.passed or result.score >= 0.7:
        print_check("Valid output passes evaluation", True, f"score={result.score:.2f}")
    else:
        print_check(
            "Valid output passes evaluation",
            False,
            f"score={result.score:.2f}, failures={result.failures}"
        )
        all_passed = False

    return all_passed


async def main() -> int:
    """Run all isolation tests."""
    print()
    print("=" * 60)
    print("SPEC STATE MACHINE ISOLATION TEST")
    print("=" * 60)
    print()
    print("This script verifies the spec state machine can run")
    print("in an isolated sandbox environment without:")
    print("  - Database connection")
    print("  - Redis connection")
    print("  - Full backend dependencies")
    print()

    results = []

    # Run all tests
    results.append(("Module Imports", await test_imports()))
    results.append(("Mock Database Session", await test_mock_database_session()))
    results.append(("Mock Spec Object", await test_mock_spec()))
    results.append(("State Machine Creation", await test_state_machine_creation()))
    results.append(("load_spec Fallback", await test_load_spec_fallback()))
    results.append(("File Checkpoints", await test_file_checkpoints()))
    results.append(("Checkpoint Restoration", await test_checkpoint_restore()))
    results.append(("WorkerConfig Env Vars", await test_worker_config_env_vars()))
    results.append(("Evaluators", await test_evaluators()))

    # Summary
    print_header("TEST SUMMARY")
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("The spec state machine is ready for sandbox deployment.")
        print("=" * 60)
        return 0
    else:
        print("=" * 60)
        print("SOME TESTS FAILED!")
        print("Please review the failures above.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
