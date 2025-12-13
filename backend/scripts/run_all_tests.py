#!/usr/bin/env python3
"""Master test script - runs all levels of the testing ladder.

This script runs tests in order of speed and isolation:
1. Smoke tests (30s) - Quick sanity check
2. Unit tests (1-2min) - Logic validation
3. Integration tests (2-5min) - API/service tests
4. E2E tests (5-15min) - Real sandbox validation

Usage:
    cd backend
    uv run python scripts/run_all_tests.py [--quick] [--skip-e2e] [--verbose]

Options:
    --quick     Skip slow tests (E2E)
    --skip-e2e  Skip E2E tests only
    --verbose   Show full test output
    --level N   Run only up to level N (0=smoke, 1=unit, 2=integration, 3=e2e)
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def run_command(
    cmd: list[str], description: str, verbose: bool = False
) -> tuple[bool, float]:
    """Run a command and return (success, elapsed_time)."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}🧪 {description}{RESET}")
    print(f"   Command: {' '.join(cmd)}")
    print(f"{BLUE}{'=' * 60}{RESET}")

    start = time.time()

    if verbose:
        result = subprocess.run(cmd)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # Show output on failure
            if result.stdout:
                print(result.stdout[-2000:])  # Last 2000 chars
            if result.stderr:
                print(f"{RED}{result.stderr[-1000:]}{RESET}")

    elapsed = time.time() - start

    if result.returncode == 0:
        print(f"{GREEN}✅ PASSED in {elapsed:.1f}s{RESET}")
        return True, elapsed
    else:
        print(f"{RED}❌ FAILED in {elapsed:.1f}s{RESET}")
        return False, elapsed


def check_environment():
    """Check that required environment is set up."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}🔍 Environment Check{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")

    # Check we're in backend directory
    cwd = Path.cwd()
    if not (cwd / "omoi_os").exists():
        if (cwd / "backend" / "omoi_os").exists():
            print(f"{YELLOW}⚠️  Please run from backend directory: cd backend{RESET}")
            return False
        print(f"{RED}❌ Not in backend directory{RESET}")
        return False

    print("   ✅ In backend directory")

    # Check .env.local exists
    if not (cwd / ".env.local").exists():
        print(f"{YELLOW}⚠️  No .env.local found - some tests may fail{RESET}")
    else:
        print("   ✅ .env.local exists")

    # Check tests directory exists
    if not (cwd / "tests").exists():
        print(f"{RED}❌ tests/ directory not found{RESET}")
        return False
    print("   ✅ tests/ directory exists")

    return True


def main():
    parser = argparse.ArgumentParser(description="Run all tests in the testing ladder")
    parser.add_argument("--quick", action="store_true", help="Skip slow tests (E2E)")
    parser.add_argument("--skip-e2e", action="store_true", help="Skip E2E tests only")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show full test output"
    )
    parser.add_argument(
        "--level", type=int, default=4, help="Run only up to level N (0-4)"
    )
    parser.add_argument(
        "--no-stop", action="store_true", help="Continue even if tests fail"
    )
    args = parser.parse_args()

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}🪜 TESTING LADDER - Full Validation{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    if not check_environment():
        sys.exit(1)

    results = []
    total_time = 0

    # Level 0: Smoke test
    if args.level >= 0:
        smoke_script = Path("scripts/smoke_test.py")
        if smoke_script.exists():
            passed, elapsed = run_command(
                ["uv", "run", "python", str(smoke_script)],
                "Level 0: Smoke Test",
                verbose=args.verbose,
            )
            results.append(("Level 0: Smoke", passed, elapsed))
            total_time += elapsed

            if not passed and not args.no_stop:
                print(f"\n{RED}❌ Smoke test failed - fix before continuing{RESET}")
                print_summary(results, total_time)
                sys.exit(1)
        else:
            print(
                f"{YELLOW}⚠️  Skipping smoke test (scripts/smoke_test.py not found){RESET}"
            )

    # Level 1: Unit tests
    if args.level >= 1:
        unit_tests = Path("tests/unit")
        if unit_tests.exists():
            passed, elapsed = run_command(
                ["pytest", str(unit_tests), "-v", "--maxfail=3", "-q"],
                "Level 1: Unit Tests",
                verbose=args.verbose,
            )
            results.append(("Level 1: Unit", passed, elapsed))
            total_time += elapsed

            if not passed and not args.no_stop:
                print(f"\n{RED}❌ Unit tests failed{RESET}")
                print_summary(results, total_time)
                sys.exit(1)
        else:
            print(f"{YELLOW}⚠️  Skipping unit tests (tests/unit/ not found){RESET}")

    # Level 2: Integration tests
    if args.level >= 2:
        integration_tests = Path("tests/integration/sandbox")
        if integration_tests.exists():
            passed, elapsed = run_command(
                ["pytest", str(integration_tests), "-v", "--maxfail=3", "-q"],
                "Level 2: Integration Tests",
                verbose=args.verbose,
            )
            results.append(("Level 2: Integration", passed, elapsed))
            total_time += elapsed

            if not passed and not args.no_stop:
                print(f"\n{RED}❌ Integration tests failed{RESET}")
                print_summary(results, total_time)
                sys.exit(1)
        else:
            # Try general integration tests
            integration_tests = Path("tests/integration")
            if integration_tests.exists():
                passed, elapsed = run_command(
                    ["pytest", str(integration_tests), "-v", "--maxfail=3", "-q"],
                    "Level 2: Integration Tests",
                    verbose=args.verbose,
                )
                results.append(("Level 2: Integration", passed, elapsed))
                total_time += elapsed

    # Level 3: E2E tests
    if args.level >= 3 and not args.quick and not args.skip_e2e:
        e2e_script = Path("scripts/test_spawner_e2e.py")
        if e2e_script.exists():
            passed, elapsed = run_command(
                ["uv", "run", "python", str(e2e_script)],
                "Level 3: E2E Tests (Real Sandboxes)",
                verbose=args.verbose,
            )
            results.append(("Level 3: E2E", passed, elapsed))
            total_time += elapsed
        else:
            print(
                f"{YELLOW}⚠️  Skipping E2E (scripts/test_spawner_e2e.py not found){RESET}"
            )
    elif args.level >= 3:
        print(f"{YELLOW}⚠️  Skipping E2E tests (--quick or --skip-e2e){RESET}")

    # Level 4: Contract tests (if they exist)
    if args.level >= 4:
        contract_tests = Path("tests/contract")
        if contract_tests.exists():
            passed, elapsed = run_command(
                ["pytest", str(contract_tests), "-v", "--maxfail=3", "-q"],
                "Level 4: Contract Tests",
                verbose=args.verbose,
            )
            results.append(("Level 4: Contract", passed, elapsed))
            total_time += elapsed

    print_summary(results, total_time)

    all_passed = all(passed for _, passed, _ in results)
    sys.exit(0 if all_passed else 1)


def print_summary(results: list[tuple[str, bool, float]], total_time: float):
    """Print test summary."""
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}📊 TESTING LADDER RESULTS{RESET}")
    print(f"{'=' * 60}")

    all_passed = True
    for name, passed, elapsed in results:
        status = f"{GREEN}✅" if passed else f"{RED}❌"
        print(f"   {status} {name} ({elapsed:.1f}s){RESET}")
        if not passed:
            all_passed = False

    print(f"{'=' * 60}")
    print(f"   Total time: {total_time:.1f}s")

    if all_passed:
        print(f"\n{GREEN}{BOLD}🎉 ALL TESTS PASSED!{RESET}")
    else:
        print(f"\n{RED}{BOLD}❌ SOME TESTS FAILED{RESET}")
        print(f"\n{YELLOW}💡 Tips:{RESET}")
        print("   - Run failing test with verbose: pytest <test> -v -s")
        print("   - Check the debugging guide in 12_improved_testing_guide.md")

    print()


if __name__ == "__main__":
    main()
