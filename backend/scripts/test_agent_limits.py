#!/usr/bin/env python3
"""
Test script for organization-level agent limits.

Tests that the TaskQueueService correctly enforces agent limits
from subscriptions when claiming tasks.

Run: cd backend && uv run python scripts/test_agent_limits.py
"""

import asyncio
import sys
from uuid import uuid4

# Add parent to path for imports
sys.path.insert(0, ".")

from omoi_os.config import get_app_settings
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.models.organization import Organization
from omoi_os.models.project import Project
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.models.user import User
from omoi_os.models.billing import BillingAccount
from omoi_os.models.subscription import (
    Subscription,
    SubscriptionTier,
    SubscriptionStatus,
    TIER_LIMITS,
)
from omoi_os.utils.datetime import utc_now
from datetime import timedelta


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(name: str, passed: bool, detail: str = ""):
    emoji = "✅" if passed else "❌"
    print(f"  {emoji} {name}")
    if detail:
        print(f"      └─ {detail}")


class AgentLimitTester:
    """Test harness for agent limit enforcement."""

    def __init__(self):
        settings = get_app_settings()
        self.db = DatabaseService(connection_string=settings.database.url)
        self.queue = TaskQueueService(self.db)
        self.test_ids = {
            "users": [],
            "orgs": [],
            "billing_accounts": [],
            "subscriptions": [],
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
                ticket = session.query(Ticket).filter(Ticket.id == str(ticket_id)).first()
                if ticket:
                    session.delete(ticket)

            for project_id in self.test_ids["projects"]:
                project = session.query(Project).filter(Project.id == project_id).first()
                if project:
                    session.delete(project)

            for sub_id in self.test_ids["subscriptions"]:
                sub = session.query(Subscription).filter(Subscription.id == sub_id).first()
                if sub:
                    session.delete(sub)

            for ba_id in self.test_ids["billing_accounts"]:
                ba = session.query(BillingAccount).filter(BillingAccount.id == ba_id).first()
                if ba:
                    session.delete(ba)

            for org_id in self.test_ids["orgs"]:
                org = session.query(Organization).filter(Organization.id == org_id).first()
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
            email=f"test-agent-limit-{uuid4().hex[:8]}@test.local",
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

    def create_billing_account(self, session, org: Organization) -> BillingAccount:
        """Create a billing account for an org."""
        ba = BillingAccount(
            id=uuid4(),
            organization_id=org.id,
            status="active",
        )
        session.add(ba)
        session.flush()
        self.test_ids["billing_accounts"].append(ba.id)
        return ba

    def create_subscription(
        self, session, org: Organization, ba: BillingAccount, tier: SubscriptionTier
    ) -> Subscription:
        """Create a subscription for an org."""
        limits = TIER_LIMITS[tier]
        now = utc_now()
        sub = Subscription(
            id=uuid4(),
            organization_id=org.id,
            billing_account_id=ba.id,
            tier=tier.value,
            status=SubscriptionStatus.ACTIVE.value,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            workflows_limit=limits["workflows_limit"],
            agents_limit=limits["agents_limit"],
            storage_limit_gb=limits["storage_limit_gb"],
        )
        session.add(sub)
        session.flush()
        self.test_ids["subscriptions"].append(sub.id)
        return sub

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

    def create_ticket(self, session, project: Project) -> Ticket:
        """Create a test ticket."""
        ticket_id = str(uuid4())
        ticket = Ticket(
            id=ticket_id,
            project_id=project.id,
            title=f"Test Ticket {uuid4().hex[:8]}",
            status="open",
            priority="medium",
            phase_id="PHASE_IMPLEMENTATION",
        )
        session.add(ticket)
        session.flush()
        self.test_ids["tickets"].append(ticket_id)
        return ticket

    def create_task(
        self, session, ticket: Ticket, status: str = "pending"
    ) -> Task:
        """Create a test task."""
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            ticket_id=ticket.id,  # ticket.id is already a string
            task_type="test_task",
            status=status,
            phase_id="PHASE_IMPLEMENTATION",
            priority="medium",
        )
        session.add(task)
        session.flush()
        self.test_ids["tasks"].append(task_id)
        return task

    def run_tests(self):
        """Run all agent limit tests."""
        results = []

        try:
            # Test 1: get_agent_limit_for_organization with different tiers
            print_header("Test 1: Agent Limit Lookup by Tier")
            results.append(self.test_agent_limit_lookup())

            # Test 2: get_running_count_by_organization
            print_header("Test 2: Running Count by Organization")
            results.append(self.test_running_count())

            # Test 3: can_spawn_agent_for_organization
            print_header("Test 3: Can Spawn Agent Check")
            results.append(self.test_can_spawn_agent())

            # Test 4: get_next_task_with_concurrency_limit respects org limits
            print_header("Test 4: Task Claiming Respects Org Limits")
            results.append(self.test_task_claiming_respects_limits())

            # Test 5: No subscription defaults to FREE tier
            print_header("Test 5: No Subscription Defaults to FREE")
            results.append(self.test_no_subscription_defaults())

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

    def test_agent_limit_lookup(self) -> bool:
        """Test that agent limits are correctly fetched from subscriptions."""
        all_passed = True

        with self.db.get_session() as session:
            user = self.create_test_user(session)

            for tier in [SubscriptionTier.FREE, SubscriptionTier.PRO, SubscriptionTier.TEAM]:
                org = self.create_test_org(session, user)
                ba = self.create_billing_account(session, org)
                sub = self.create_subscription(session, org, ba, tier)
                session.commit()

                expected = TIER_LIMITS[tier]["agents_limit"]
                actual = self.queue.get_agent_limit_for_organization(str(org.id))

                passed = actual == expected
                all_passed = all_passed and passed
                print_result(
                    f"{tier.value} tier",
                    passed,
                    f"expected {expected}, got {actual}"
                )

        return all_passed

    def test_running_count(self) -> bool:
        """Test that running task count is correct."""
        with self.db.get_session() as session:
            user = self.create_test_user(session)
            org = self.create_test_org(session, user)
            ba = self.create_billing_account(session, org)
            sub = self.create_subscription(session, org, ba, SubscriptionTier.PRO)
            project = self.create_project(session, org, user)
            ticket = self.create_ticket(session, project)

            # Create tasks with different statuses
            self.create_task(session, ticket, status="pending")  # shouldn't count
            self.create_task(session, ticket, status="running")  # should count
            self.create_task(session, ticket, status="assigned")  # should count
            self.create_task(session, ticket, status="completed")  # shouldn't count
            self.create_task(session, ticket, status="claiming")  # should count

            session.commit()

            count = self.queue.get_running_count_by_organization(str(org.id))
            expected = 3  # running + assigned + claiming

            passed = count == expected
            print_result(
                "Running count",
                passed,
                f"expected {expected}, got {count}"
            )
            return passed

    def test_can_spawn_agent(self) -> bool:
        """Test can_spawn_agent_for_organization logic."""
        all_passed = True

        with self.db.get_session() as session:
            user = self.create_test_user(session)
            org = self.create_test_org(session, user)
            ba = self.create_billing_account(session, org)
            # FREE tier = 1 agent limit
            sub = self.create_subscription(session, org, ba, SubscriptionTier.FREE)
            project = self.create_project(session, org, user)
            ticket = self.create_ticket(session, project)
            session.commit()

            # No running tasks - should be able to spawn
            can_spawn, reason = self.queue.can_spawn_agent_for_organization(str(org.id))
            passed = can_spawn is True
            all_passed = all_passed and passed
            print_result("Can spawn when empty", passed, reason)

            # Add a running task - should NOT be able to spawn (limit is 1)
            self.create_task(session, ticket, status="running")
            session.commit()

            can_spawn, reason = self.queue.can_spawn_agent_for_organization(str(org.id))
            passed = can_spawn is False
            all_passed = all_passed and passed
            print_result("Cannot spawn when at limit", passed, reason)

        return all_passed

    def test_task_claiming_respects_limits(self) -> bool:
        """Test that get_next_task_with_concurrency_limit respects org limits."""
        with self.db.get_session() as session:
            user = self.create_test_user(session)
            org = self.create_test_org(session, user)
            ba = self.create_billing_account(session, org)
            # FREE tier = 1 agent limit
            sub = self.create_subscription(session, org, ba, SubscriptionTier.FREE)
            project = self.create_project(session, org, user)
            ticket = self.create_ticket(session, project)

            # Create a running task (uses up the 1 agent slot)
            self.create_task(session, ticket, status="running")

            # Create a pending task that SHOULD be blocked
            pending_task = self.create_task(session, ticket, status="pending")
            session.commit()

        # Try to claim - should return None because org is at capacity
        claimed = self.queue.get_next_task_with_concurrency_limit()

        passed = claimed is None
        print_result(
            "Task claiming blocked when org at limit",
            passed,
            f"claimed task: {claimed.id if claimed else 'None'}"
        )
        return passed

    def test_no_subscription_defaults(self) -> bool:
        """Test that orgs without subscriptions default to FREE tier limits."""
        with self.db.get_session() as session:
            user = self.create_test_user(session)
            org = self.create_test_org(session, user)
            # NO billing account or subscription created
            session.commit()

            limit = self.queue.get_agent_limit_for_organization(str(org.id))
            expected = TIER_LIMITS[SubscriptionTier.FREE]["agents_limit"]

            passed = limit == expected
            print_result(
                "No subscription defaults to FREE",
                passed,
                f"expected {expected}, got {limit}"
            )
            return passed


def main():
    print("\n" + "="*60)
    print("  🧪 Agent Limit Enforcement Tests")
    print("="*60)

    tester = AgentLimitTester()
    return tester.run_tests()


if __name__ == "__main__":
    sys.exit(main())
