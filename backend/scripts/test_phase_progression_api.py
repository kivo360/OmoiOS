#!/usr/bin/env python3
"""
API-based integration test for phase progression hooks.

This script tests the phase progression system through the API endpoints,
providing end-to-end verification that the hooks work correctly.

Prerequisites:
1. Backend server running: cd backend && uv run uvicorn omoi_os.main:app --reload
2. Valid auth token (or modify to use test auth)

Run: cd backend && uv run python scripts/test_phase_progression_api.py

For local testing without auth, set SKIP_AUTH=1 environment variable.
"""

import os
import sys
import requests
from uuid import uuid4
from typing import Optional

# Configuration
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")
SKIP_AUTH = os.environ.get("SKIP_AUTH", "0") == "1"

# Test configuration
TEST_PROJECT_ID = os.environ.get("TEST_PROJECT_ID", "")  # Set if you have an existing project


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(name: str, passed: bool, detail: str = ""):
    emoji = "✅" if passed else "❌"
    print(f"  {emoji} {name}")
    if detail:
        print(f"      └─ {detail}")


class APITester:
    """Test harness for phase progression API endpoints."""

    def __init__(self):
        self.session = requests.Session()
        if AUTH_TOKEN and not SKIP_AUTH:
            self.session.headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
            self.session.headers["Content-Type"] = "application/json"

        self.created_tickets = []
        self.created_tasks = []

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an API request."""
        url = f"{API_BASE}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except requests.exceptions.ConnectionError:
            print(f"\n❌ Connection Error: Could not connect to {API_BASE}")
            print("   Make sure the backend server is running:")
            print("   cd backend && uv run uvicorn omoi_os.main:app --reload")
            sys.exit(1)

    def cleanup(self):
        """Cleanup created test data."""
        print_header("Cleanup")
        # Note: In a real test, we'd delete the created tickets/tasks
        # For now, just report what was created
        print(f"  Created {len(self.created_tickets)} tickets (cleanup manually if needed)")
        print(f"  Created {len(self.created_tasks)} tasks (cleanup manually if needed)")

    def run_tests(self) -> int:
        """Run all API tests."""
        results = []

        try:
            # Test 1: Health check
            print_header("Test 1: System Health Check")
            results.append(self.test_health_check())

            # Test 2: Phase progression status
            print_header("Test 2: Phase Progression Status")
            results.append(self.test_phase_progression_status())

            # Test 3: Debug endpoints accessible
            print_header("Test 3: Debug Endpoints Accessible")
            results.append(self.test_debug_endpoints())

            # Test 4: Task queue stats
            print_header("Test 4: Task Queue Stats")
            results.append(self.test_task_queue_stats())

            # Test 5: Phase initial tasks config
            print_header("Test 5: Phase Initial Tasks Config")
            results.append(self.test_phase_initial_tasks())

            # Only run integration tests if we have a project ID
            if TEST_PROJECT_ID:
                print_header("Test 6: Integration - Create Ticket & Test Hooks")
                results.append(self.test_hook_integration())
            else:
                print_header("Test 6: Integration Tests (SKIPPED)")
                print("  ⚠️  Set TEST_PROJECT_ID to run integration tests")

        finally:
            self.cleanup()

        # Summary
        print_header("Test Summary")
        passed = sum(results)
        total = len(results)
        print(f"\n  {passed}/{total} tests passed")

        if passed == total:
            print("\n  🎉 All tests passed!")
            return 0
        else:
            print("\n  ⚠️  Some tests failed")
            return 1

    def test_health_check(self) -> bool:
        """Test that the API is responding."""
        response = self._request("GET", "/api/v1/debug/health")

        if response.status_code == 401:
            print_result("Health endpoint", False, "Auth required - set AUTH_TOKEN")
            return False

        if response.status_code != 200:
            print_result("Health endpoint", False, f"Status: {response.status_code}")
            return False

        data = response.json()
        all_healthy = all([
            data.get("database", False),
            data.get("task_queue", False),
        ])

        print_result("Database connected", data.get("database", False))
        print_result("Event bus connected", data.get("event_bus", False))
        print_result("Task queue active", data.get("task_queue", False))
        print_result("Phase progression active", data.get("phase_progression_active", False))

        return all_healthy

    def test_phase_progression_status(self) -> bool:
        """Test phase progression service status."""
        response = self._request("GET", "/api/v1/debug/phase-progression/status")

        if response.status_code == 401:
            print_result("Phase progression status", False, "Auth required")
            return False

        if response.status_code != 200:
            print_result("Phase progression status", False, f"Status: {response.status_code}")
            return False

        data = response.json()
        active = data.get("active", False)

        print_result("Service active", active)
        if active:
            print_result(
                "Phases configured",
                True,
                f"phases={data.get('phases_with_initial_tasks', [])}"
            )

        return active

    def test_debug_endpoints(self) -> bool:
        """Test that debug endpoints are accessible."""
        endpoints = [
            "/api/v1/debug/health",
            "/api/v1/debug/tasks/stats",
            "/api/v1/debug/phase-progression/status",
            "/api/v1/debug/phase-progression/initial-tasks",
        ]

        all_passed = True
        for endpoint in endpoints:
            response = self._request("GET", endpoint)
            passed = response.status_code == 200
            all_passed = all_passed and passed
            print_result(endpoint, passed, f"Status: {response.status_code}")

        return all_passed

    def test_task_queue_stats(self) -> bool:
        """Test task queue statistics endpoint."""
        response = self._request("GET", "/api/v1/debug/tasks/stats")

        if response.status_code != 200:
            print_result("Task queue stats", False, f"Status: {response.status_code}")
            return False

        data = response.json()
        required_fields = ["pending_count", "running_count", "completed_count"]
        all_present = all(field in data for field in required_fields)

        print_result("Stats response valid", all_present)
        if all_present:
            print_result(
                "Current stats",
                True,
                f"pending={data['pending_count']}, running={data['running_count']}, completed={data['completed_count']}"
            )

        return all_present

    def test_phase_initial_tasks(self) -> bool:
        """Test phase initial tasks configuration endpoint."""
        response = self._request("GET", "/api/v1/debug/phase-progression/initial-tasks")

        if response.status_code != 200:
            print_result("Phase initial tasks", False, f"Status: {response.status_code}")
            return False

        data = response.json()
        phase_tasks = data.get("phase_initial_tasks", {})
        prd_task = data.get("prd_generation_task", {})

        has_phases = len(phase_tasks) > 0
        has_prd = prd_task.get("task_type") == "generate_prd"

        print_result("Phase tasks configured", has_phases, f"phases={list(phase_tasks.keys())}")
        print_result("PRD generation configured", has_prd)

        return has_phases and has_prd

    def test_hook_integration(self) -> bool:
        """Integration test: Create ticket and test hook endpoints."""
        all_passed = True

        # Step 1: Create a ticket
        print("\n  Creating test ticket...")
        response = self._request("POST", "/api/v1/tickets", json={
            "title": f"Test Ticket {uuid4().hex[:8]}",
            "description": "Integration test for phase progression hooks",
            "project_id": TEST_PROJECT_ID,
            "phase_id": "PHASE_REQUIREMENTS",
            "priority": "MEDIUM",
            "force_create": True,
        })

        if response.status_code not in [200, 201]:
            print_result("Create ticket", False, f"Status: {response.status_code}")
            return False

        ticket_data = response.json()
        ticket_id = ticket_data.get("id")
        self.created_tickets.append(ticket_id)
        print_result("Ticket created", True, f"id={ticket_id}")

        # Step 2: Check phase gate status
        response = self._request("GET", f"/api/v1/debug/tickets/{ticket_id}/phase-gate-status")
        if response.status_code == 200:
            gate_data = response.json()
            print_result(
                "Phase gate status",
                True,
                f"phase={gate_data.get('current_phase')}, can_advance={gate_data.get('can_advance')}"
            )
        else:
            print_result("Phase gate status", False, f"Status: {response.status_code}")
            all_passed = False

        # Step 3: Test Hook 2 - Spawn phase tasks
        response = self._request("POST", f"/api/v1/tickets/{ticket_id}/spawn-phase-tasks")
        if response.status_code == 200:
            spawn_data = response.json()
            tasks_spawned = spawn_data.get("tasks_spawned", 0)
            print_result("Spawn phase tasks (Hook 2)", True, f"spawned={tasks_spawned}")

            # Check if it was generate_prd (no PRD exists)
            if tasks_spawned > 0:
                print("      └─ Likely spawned generate_prd task (no PRD in ticket)")
        else:
            print_result("Spawn phase tasks (Hook 2)", False, f"Status: {response.status_code}")
            all_passed = False

        # Step 4: Get tasks for the ticket
        response = self._request("GET", f"/api/v1/debug/tickets/{ticket_id}/tasks-by-phase")
        if response.status_code == 200:
            tasks_data = response.json()
            total_tasks = tasks_data.get("total_tasks", 0)
            phases = tasks_data.get("phases", {})
            print_result("Tasks by phase", True, f"total={total_tasks}, phases={list(phases.keys())}")
        else:
            print_result("Tasks by phase", False, f"Status: {response.status_code}")
            all_passed = False

        # Step 5: Test Hook 1 - Check phase completion
        response = self._request("POST", f"/api/v1/tickets/{ticket_id}/check-phase-completion")
        if response.status_code == 200:
            check_data = response.json()
            print_result(
                "Check phase completion (Hook 1)",
                True,
                f"complete={check_data.get('all_phase_tasks_complete')}, advanced={check_data.get('advanced')}"
            )
        else:
            print_result("Check phase completion (Hook 1)", False, f"Status: {response.status_code}")
            all_passed = False

        return all_passed


def main():
    print("\n" + "=" * 60)
    print("  🧪 Phase Progression API Integration Tests")
    print("=" * 60)

    # Check prerequisites
    if not SKIP_AUTH and not AUTH_TOKEN:
        print("\n⚠️  Note: AUTH_TOKEN not set. Some tests may fail.")
        print("   Set AUTH_TOKEN=<your-token> or SKIP_AUTH=1 for local dev.")

    if not TEST_PROJECT_ID:
        print("\n⚠️  Note: TEST_PROJECT_ID not set. Integration tests will be skipped.")
        print("   Set TEST_PROJECT_ID=<project-uuid> to run full integration tests.")

    tester = APITester()
    return tester.run_tests()


if __name__ == "__main__":
    sys.exit(main())
