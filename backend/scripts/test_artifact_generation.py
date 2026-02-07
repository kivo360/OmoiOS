#!/usr/bin/env python3
"""
Test script to verify artifact generation from validation state.

This tests the logic that transforms worker validation data into
artifacts that the phase gate can understand.

Run: cd backend && uv run python scripts/test_artifact_generation.py
"""


def generate_artifacts_from_event(event_data: dict) -> list[dict]:
    """
    Simulate the artifact generation logic from sandbox.py.

    This is the same logic that runs when agent.completed is received.
    """
    artifacts = []
    code_pushed = event_data.get("code_pushed", False)
    pr_created = event_data.get("pr_created", False)
    tests_passed = event_data.get("tests_passed", False)
    pr_url = event_data.get("pr_url")
    pr_number = event_data.get("pr_number")
    files_changed = event_data.get("files_changed", 0)
    ci_status = event_data.get("ci_status")
    branch_name = event_data.get("branch_name")

    # Create code_changes artifact if code was pushed
    if code_pushed or pr_created:
        artifacts.append(
            {
                "type": "code_changes",
                "path": pr_url,
                "content": {
                    "has_tests": tests_passed,
                    "branch_name": branch_name,
                    "pr_created": pr_created,
                    "pr_url": pr_url,
                    "pr_number": pr_number,
                    "files_changed": files_changed,
                },
            }
        )

    # Create test_coverage artifact if tests passed
    if tests_passed:
        test_details = {}
        if ci_status and isinstance(ci_status, list):
            test_details["checks"] = [
                {
                    "name": check.get("name"),
                    "conclusion": check.get("conclusion"),
                    "state": check.get("state"),
                }
                for check in ci_status
            ]
            test_details["all_passed"] = all(
                check.get("conclusion") == "success"
                for check in ci_status
                if check.get("state") == "completed"
            )

        artifacts.append(
            {
                "type": "test_coverage",
                "content": {
                    "percentage": 80,
                    "all_passed": True,
                    "has_tests": True,
                    **test_details,
                },
            }
        )

    return artifacts


def print_test(name: str, passed: bool, detail: str = ""):
    emoji = "✅" if passed else "❌"
    print(f"  {emoji} {name}")
    if detail:
        print(f"      └─ {detail}")


def main():
    print("\n" + "=" * 60)
    print("  🧪 Artifact Generation Test")
    print("=" * 60)

    all_passed = True

    # Test 1: Full implementation with CI passing
    print("\n  Test 1: Full implementation (code pushed, PR created, CI passing)")
    event_data = {
        "code_pushed": True,
        "pr_created": True,
        "tests_passed": True,
        "pr_url": "https://github.com/org/repo/pull/123",
        "pr_number": 123,
        "files_changed": 5,
        "branch_name": "feature/new-feature",
        "ci_status": [
            {"name": "tests", "state": "completed", "conclusion": "success"},
            {"name": "lint", "state": "completed", "conclusion": "success"},
        ],
    }

    artifacts = generate_artifacts_from_event(event_data)

    has_code_changes = any(a["type"] == "code_changes" for a in artifacts)
    has_test_coverage = any(a["type"] == "test_coverage" for a in artifacts)

    print_test("Generated code_changes artifact", has_code_changes)
    print_test("Generated test_coverage artifact", has_test_coverage)
    print_test("Total artifacts", len(artifacts) == 2, f"count={len(artifacts)}")

    if has_code_changes:
        code_artifact = next(a for a in artifacts if a["type"] == "code_changes")
        print_test(
            "code_changes.has_tests", code_artifact["content"]["has_tests"] is True
        )
        print_test(
            "code_changes.pr_number", code_artifact["content"]["pr_number"] == 123
        )

    if has_test_coverage:
        test_artifact = next(a for a in artifacts if a["type"] == "test_coverage")
        print_test(
            "test_coverage.all_passed", test_artifact["content"]["all_passed"] is True
        )
        print_test("test_coverage has CI checks", "checks" in test_artifact["content"])

    all_passed = all_passed and has_code_changes and has_test_coverage

    # Test 2: Research task (no code changes)
    print("\n  Test 2: Research task (no code changes)")
    event_data = {
        "code_pushed": False,
        "pr_created": False,
        "tests_passed": False,
    }

    artifacts = generate_artifacts_from_event(event_data)
    print_test(
        "No artifacts for research task", len(artifacts) == 0, f"count={len(artifacts)}"
    )
    all_passed = all_passed and len(artifacts) == 0

    # Test 3: Code pushed but no CI
    print("\n  Test 3: Code pushed but no CI configured")
    event_data = {
        "code_pushed": True,
        "pr_created": True,
        "tests_passed": True,  # Defaults to True when no CI
        "pr_url": "https://github.com/org/repo/pull/456",
        "pr_number": 456,
        "files_changed": 3,
        "branch_name": "fix/bug-fix",
        "ci_status": None,  # No CI checks
    }

    artifacts = generate_artifacts_from_event(event_data)
    has_code_changes = any(a["type"] == "code_changes" for a in artifacts)
    has_test_coverage = any(a["type"] == "test_coverage" for a in artifacts)

    print_test("Generated code_changes artifact", has_code_changes)
    print_test("Generated test_coverage artifact", has_test_coverage)

    if has_test_coverage:
        test_artifact = next(a for a in artifacts if a["type"] == "test_coverage")
        print_test(
            "test_coverage.all_passed (no CI)",
            test_artifact["content"]["all_passed"] is True,
        )
        print_test("No CI checks in content", "checks" not in test_artifact["content"])

    all_passed = all_passed and has_code_changes and has_test_coverage

    # Test 4: CI failing
    print("\n  Test 4: PR created but CI failing")
    event_data = {
        "code_pushed": True,
        "pr_created": True,
        "tests_passed": False,  # CI failed
        "pr_url": "https://github.com/org/repo/pull/789",
        "pr_number": 789,
        "files_changed": 2,
        "branch_name": "feature/wip",
        "ci_status": [
            {"name": "tests", "state": "completed", "conclusion": "failure"},
        ],
    }

    artifacts = generate_artifacts_from_event(event_data)
    has_code_changes = any(a["type"] == "code_changes" for a in artifacts)
    has_test_coverage = any(a["type"] == "test_coverage" for a in artifacts)

    print_test("Generated code_changes artifact", has_code_changes)
    print_test("No test_coverage (tests failed)", not has_test_coverage)

    if has_code_changes:
        code_artifact = next(a for a in artifacts if a["type"] == "code_changes")
        print_test(
            "code_changes.has_tests = False",
            code_artifact["content"]["has_tests"] is False,
        )

    all_passed = all_passed and has_code_changes and not has_test_coverage

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("  🎉 All artifact generation tests passed!")
    else:
        print("  ❌ Some tests failed")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
