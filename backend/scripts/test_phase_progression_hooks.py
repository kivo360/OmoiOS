#!/usr/bin/env python3
"""
Test script for phase progression hooks (Hook 1 + Hook 2).

This script tests the automatic phase advancement and task spawning
functionality by creating test tickets and tasks, then simulating
the events that trigger the hooks.

Run: cd backend && uv run python scripts/test_phase_progression_hooks.py

Tests:
1. Hook 1: Task completion triggers phase advancement check
2. Hook 2: Phase transition triggers task spawning
3. Dynamic PRD: Tickets without PRD get generate_prd task
4. API endpoints: Manual trigger endpoints work correctly
"""

import sys
from uuid import uuid4

# Add parent to path for imports
sys.path.insert(0, ".")

from omoi_os.config import get_app_settings
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.phase_gate import PhaseGateService
from omoi_os.services.phase_progression_service import (
    PhaseProgressionService,
    PHASE_INITIAL_TASKS,
)
from omoi_os.services.ticket_workflow import TicketWorkflowOrchestrator
from omoi_os.models.organization import Organization
from omoi_os.models.project import Project
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.models.user import User


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(name: str, passed: bool, detail: str = ""):
    emoji = "✅" if passed else "❌"
    print(f"  {emoji} {name}")
    if detail:
        print(f"      └─ {detail}")


class PhaseProgressionTester:
    """Test harness for phase progression hooks."""

    def __init__(self):
        settings = get_app_settings()
        self.db = DatabaseService(connection_string=settings.database.url)
        self.queue = TaskQueueService(self.db)
        self.event_bus = EventBusService(redis_url=settings.redis.url)
        self.phase_gate = PhaseGateService(self.db)
        self.workflow = TicketWorkflowOrchestrator(
            db=self.db,
            task_queue=self.queue,
            phase_gate=self.phase_gate,
            event_bus=self.event_bus,
        )
        self.progression = PhaseProgressionService(
            db=self.db,
            task_queue=self.queue,
            phase_gate=self.phase_gate,
            event_bus=self.event_bus,
        )
        self.progression.set_workflow_orchestrator(self.workflow)

        self.test_ids = {
            "users": [],
            "orgs": [],
            "projects": [],
            "tickets": [],
            "tasks": [],
        }

    def cleanup(self):
        """Remove all test data."""
        print_header("Cleanup")
        with self.db.get_session() as session:
            # Delete in reverse dependency order
            for task_id in self.test_ids["tasks"]:
                task = session.query(Task).filter(Task.id == str(task_id)).first()
                if task:
                    session.delete(task)

            for ticket_id in self.test_ids["tickets"]:
                ticket = (
                    session.query(Ticket).filter(Ticket.id == str(ticket_id)).first()
                )
                if ticket:
                    session.delete(ticket)

            for project_id in self.test_ids["projects"]:
                project = (
                    session.query(Project).filter(Project.id == project_id).first()
                )
                if project:
                    session.delete(project)

            for org_id in self.test_ids["orgs"]:
                org = (
                    session.query(Organization)
                    .filter(Organization.id == org_id)
                    .first()
                )
                if org:
                    session.delete(org)

            for user_id in self.test_ids["users"]:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    session.delete(user)

            session.commit()
        print("  ✅ Cleaned up test data")

    def create_test_user(self, session) -> User:
        """Create a test user."""
        user = User(
            id=uuid4(),
            email=f"test-phase-hooks-{uuid4().hex[:8]}@test.local",
            full_name="Test User",
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        session.flush()
        self.test_ids["users"].append(user.id)
        return user

    def create_test_org(self, session, owner: User) -> Organization:
        """Create a test organization."""
        org = Organization(
            id=uuid4(),
            name=f"Test Org {uuid4().hex[:8]}",
            slug=f"test-org-{uuid4().hex[:8]}",
            owner_id=owner.id,
        )
        session.add(org)
        session.flush()
        self.test_ids["orgs"].append(org.id)
        return org

    def create_project(self, session, org: Organization, user: User) -> Project:
        """Create a test project."""
        project = Project(
            id=f"project-test-{uuid4().hex[:8]}",
            organization_id=org.id,
            created_by=user.id,
            name=f"Test Project {uuid4().hex[:8]}",
        )
        session.add(project)
        session.flush()
        self.test_ids["projects"].append(project.id)
        return project

    def create_ticket(
        self,
        session,
        project: Project,
        phase_id: str = "PHASE_BACKLOG",
        status: str = "backlog",
        context: dict | None = None,
    ) -> Ticket:
        """Create a test ticket."""
        ticket_id = str(uuid4())
        ticket = Ticket(
            id=ticket_id,
            project_id=project.id,
            title=f"Test Ticket {uuid4().hex[:8]}",
            description="Test ticket description for phase progression testing",
            status=status,
            priority="medium",
            phase_id=phase_id,
            context=context,
        )
        session.add(ticket)
        session.flush()
        self.test_ids["tickets"].append(ticket_id)
        return ticket

    def create_task(
        self, session, ticket: Ticket, phase_id: str, status: str = "pending"
    ) -> Task:
        """Create a test task."""
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            ticket_id=ticket.id,
            task_type="test_task",
            status=status,
            phase_id=phase_id,
            priority="medium",
        )
        session.add(task)
        session.flush()
        self.test_ids["tasks"].append(task_id)
        return task

    def run_tests(self):
        """Run all phase progression tests."""
        results = []

        try:
            # Test 1: Check phase tasks complete detection
            print_header("Test 1: Phase Completion Detection")
            results.append(self.test_phase_completion_detection())

            # Test 2: Hook 2 - Task spawning on phase transition
            print_header("Test 2: Task Spawning on Phase Transition")
            results.append(self.test_task_spawning())

            # Test 3: Dynamic PRD generation
            print_header("Test 3: Dynamic PRD Generation")
            results.append(self.test_prd_generation())

            # Test 4: API endpoints work
            print_header("Test 4: Manual Trigger Methods")
            results.append(self.test_manual_triggers())

            # Test 5: Event handling
            print_header("Test 5: Event Handler Registration")
            results.append(self.test_event_subscription())

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

    def test_phase_completion_detection(self) -> bool:
        """Test that phase completion is correctly detected."""
        all_passed = True

        with self.db.get_session() as session:
            user = self.create_test_user(session)
            org = self.create_test_org(session, user)
            project = self.create_project(session, org, user)
            ticket = self.create_ticket(
                session, project, phase_id="PHASE_IMPLEMENTATION", status="building"
            )

            # Create two tasks in the phase
            task1 = self.create_task(session, ticket, "PHASE_IMPLEMENTATION", "pending")
            task2 = self.create_task(session, ticket, "PHASE_IMPLEMENTATION", "pending")
            session.commit()

            # Not all complete - should return False
            result = self.progression._are_all_phase_tasks_complete(
                ticket.id, "PHASE_IMPLEMENTATION"
            )
            passed = result is False
            all_passed = all_passed and passed
            print_result("Not complete when tasks pending", passed, f"result={result}")

            # Complete task1
            task1.status = "completed"
            session.commit()

            # Still not all complete
            result = self.progression._are_all_phase_tasks_complete(
                ticket.id, "PHASE_IMPLEMENTATION"
            )
            passed = result is False
            all_passed = all_passed and passed
            print_result("Not complete when some pending", passed, f"result={result}")

            # Complete task2
            task2.status = "completed"
            session.commit()

            # Now all complete
            result = self.progression._are_all_phase_tasks_complete(
                ticket.id, "PHASE_IMPLEMENTATION"
            )
            passed = result is True
            all_passed = all_passed and passed
            print_result("Complete when all done", passed, f"result={result}")

        return all_passed

    def test_task_spawning(self) -> bool:
        """Test that tasks are spawned when entering a new phase."""
        all_passed = True

        with self.db.get_session() as session:
            user = self.create_test_user(session)
            org = self.create_test_org(session, user)
            project = self.create_project(session, org, user)

            # Create ticket in PHASE_IMPLEMENTATION (has default tasks)
            ticket = self.create_ticket(
                session, project, phase_id="PHASE_IMPLEMENTATION", status="building"
            )
            session.commit()
            # Capture ID before session closes
            ticket_id = ticket.id

        # Spawn tasks for the phase
        count = self.progression._spawn_phase_tasks(ticket_id, "PHASE_IMPLEMENTATION")

        passed = count > 0
        all_passed = all_passed and passed
        print_result("Tasks spawned for phase", passed, f"count={count}")

        # Verify tasks were created
        with self.db.get_session() as session:
            tasks = (
                session.query(Task)
                .filter(
                    Task.ticket_id == ticket_id,
                    Task.phase_id == "PHASE_IMPLEMENTATION",
                )
                .all()
            )
            for task in tasks:
                self.test_ids["tasks"].append(task.id)

            passed = len(tasks) == count
            all_passed = all_passed and passed
            print_result("Tasks in database", passed, f"found={len(tasks)}")

            # Verify task type
            if tasks:
                expected_type = PHASE_INITIAL_TASKS["PHASE_IMPLEMENTATION"][0][
                    "task_type"
                ]
                passed = tasks[0].task_type == expected_type
                all_passed = all_passed and passed
                print_result("Correct task type", passed, f"type={tasks[0].task_type}")

        return all_passed

    def test_prd_generation(self) -> bool:
        """Test that PRD generation task is spawned when no PRD exists."""
        all_passed = True

        with self.db.get_session() as session:
            user = self.create_test_user(session)
            org = self.create_test_org(session, user)
            project = self.create_project(session, org, user)

            # Create ticket WITHOUT PRD (no context)
            ticket_no_prd = self.create_ticket(
                session,
                project,
                phase_id="PHASE_REQUIREMENTS",
                status="analyzing",
                context=None,
            )
            ticket_no_prd_id = ticket_no_prd.id

            # Create ticket WITH PRD (has prd_url in context)
            ticket_with_prd = self.create_ticket(
                session,
                project,
                phase_id="PHASE_REQUIREMENTS",
                status="analyzing",
                context={"prd_url": "https://example.com/prd.md"},
            )
            ticket_with_prd_id = ticket_with_prd.id
            session.commit()

        # Test PRD detection
        has_prd = self.progression._check_prd_exists(ticket_no_prd_id, {})
        passed = has_prd is False
        all_passed = all_passed and passed
        print_result("No PRD detected (empty context)", passed, f"has_prd={has_prd}")

        has_prd = self.progression._check_prd_exists(
            ticket_with_prd_id, {"prd_url": "https://example.com/prd.md"}
        )
        passed = has_prd is True
        all_passed = all_passed and passed
        print_result("PRD detected (has prd_url)", passed, f"has_prd={has_prd}")

        # Spawn tasks for ticket without PRD
        count = self.progression._spawn_phase_tasks(
            ticket_no_prd_id, "PHASE_REQUIREMENTS"
        )

        passed = count == 1
        all_passed = all_passed and passed
        print_result("PRD generation task spawned", passed, f"count={count}")

        # Verify generate_prd task was created
        with self.db.get_session() as session:
            prd_task = (
                session.query(Task)
                .filter(
                    Task.ticket_id == ticket_no_prd_id,
                    Task.task_type == "generate_prd",
                )
                .first()
            )
            if prd_task:
                self.test_ids["tasks"].append(prd_task.id)

            passed = prd_task is not None
            all_passed = all_passed and passed
            print_result("generate_prd task in database", passed)

        return all_passed

    def test_manual_triggers(self) -> bool:
        """Test the manual trigger methods (for API use)."""
        all_passed = True

        with self.db.get_session() as session:
            user = self.create_test_user(session)
            org = self.create_test_org(session, user)
            project = self.create_project(session, org, user)
            ticket = self.create_ticket(
                session, project, phase_id="PHASE_TESTING", status="testing"
            )
            session.commit()
            # Capture ticket_id before session closes
            ticket_id = ticket.id

        # Test check_phase_completion method
        result = self.progression.check_phase_completion(ticket_id)

        passed = "ticket_id" in result and "all_phase_tasks_complete" in result
        all_passed = all_passed and passed
        print_result(
            "check_phase_completion returns correct structure",
            passed,
            f"keys={list(result.keys())}",
        )

        # Test spawn_tasks_for_phase method
        result = self.progression.spawn_tasks_for_phase(ticket_id, "PHASE_TESTING")

        passed = "ticket_id" in result and "tasks_spawned" in result
        all_passed = all_passed and passed
        print_result(
            "spawn_tasks_for_phase returns correct structure",
            passed,
            f"keys={list(result.keys())}",
        )

        # Clean up spawned tasks
        with self.db.get_session() as session:
            tasks = session.query(Task).filter(Task.ticket_id == ticket_id).all()
            for task in tasks:
                self.test_ids["tasks"].append(task.id)

        return all_passed

    def test_event_subscription(self) -> bool:
        """Test that event handlers can be subscribed."""
        all_passed = True

        # Test subscription (this would normally happen at startup)
        try:
            self.progression.subscribe_to_events()
            passed = True
            print_result("Event subscription successful", passed)
        except Exception as e:
            passed = False
            print_result("Event subscription failed", passed, str(e))

        all_passed = all_passed and passed

        return all_passed


def main():
    print("\n" + "=" * 60)
    print("  🧪 Phase Progression Hooks Tests")
    print("=" * 60)

    tester = PhaseProgressionTester()
    return tester.run_tests()


if __name__ == "__main__":
    sys.exit(main())
