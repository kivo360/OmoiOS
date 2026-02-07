"""GitHub Integration Service for repository management and webhook handling."""

import hmac
import hashlib
from typing import Optional, Dict, Any

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

import re
from uuid import uuid4

from omoi_os.models.project import Project
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.models.ticket_commit import TicketCommit
from omoi_os.models.ticket_pull_request import TicketPullRequest
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now
from omoi_os.logging import get_logger

logger = get_logger(__name__)


class GitHubIntegrationService:
    """Service for GitHub repository integration."""

    def __init__(
        self,
        db: DatabaseService,
        event_bus: EventBusService,
        github_token: Optional[str] = None,
    ):
        """
        Initialize GitHub Integration Service.

        Args:
            db: Database service
            event_bus: Event bus service
            github_token: GitHub personal access token (optional, for API calls)
        """
        self.db = db
        self.event_bus = event_bus
        self.github_token = github_token
        self.github_api_base = "https://api.github.com"
        self.github_api_headers = {}

        if github_token:
            self.github_api_headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
            }

    def verify_webhook_signature(
        self, payload_body: bytes, signature: str, secret: str
    ) -> bool:
        """
        Verify GitHub webhook signature.

        Args:
            payload_body: Raw request body
            signature: X-Hub-Signature-256 header value
            secret: Webhook secret

        Returns:
            True if signature is valid
        """
        if not signature or not secret:
            return False

        # GitHub sends signature as "sha256=<hash>"
        if not signature.startswith("sha256="):
            return False

        expected_signature = signature[7:]  # Remove "sha256=" prefix

        # Calculate HMAC
        mac = hmac.new(
            secret.encode("utf-8"),
            msg=payload_body,
            digestmod=hashlib.sha256,
        )
        calculated_signature = mac.hexdigest()

        # Constant-time comparison
        return hmac.compare_digest(expected_signature, calculated_signature)

    async def fetch_commit_diff(
        self, owner: str, repo: str, commit_sha: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch commit diff from GitHub API.

        Args:
            owner: GitHub repository owner
            repo: Repository name
            commit_sha: Commit SHA

        Returns:
            Commit diff data or None if not found
        """
        if not HTTPX_AVAILABLE or not self.github_token:
            return None

        url = f"{self.github_api_base}/repos/{owner}/{repo}/commits/{commit_sha}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.github_api_headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            return None

    async def handle_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any],
        signature: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle GitHub webhook event.

        Args:
            event_type: GitHub event type (e.g., "push", "pull_request")
            payload: Webhook payload
            signature: Webhook signature for verification
            secret: Webhook secret

        Returns:
            Processing result
        """
        # Verify signature if provided
        if signature and secret:
            # Note: payload should be raw bytes for signature verification
            # This is a simplified version - in practice, you'd pass raw_body
            pass

        if event_type == "push":
            return await self._handle_push_event(payload)
        elif event_type == "pull_request":
            return await self._handle_pull_request_event(payload)
        elif event_type == "issues":
            return await self._handle_issue_event(payload)
        else:
            return {"success": True, "message": f"Event type {event_type} not handled"}

    async def _handle_push_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GitHub push event."""
        repository = payload.get("repository", {})
        owner = repository.get("owner", {}).get("login")
        repo = repository.get("name")
        commits = payload.get("commits", [])

        if not owner or not repo:
            return {"success": False, "message": "Invalid repository data"}

        # Find project by GitHub repo
        with self.db.get_session() as session:
            project = (
                session.query(Project)
                .filter(
                    Project.github_owner == owner,
                    Project.github_repo == repo,
                )
                .first()
            )

            if not project:
                return {
                    "success": False,
                    "message": f"Project not found for {owner}/{repo}",
                }

            linked_count = 0

            # Process each commit
            for commit_data in commits:
                commit_sha = commit_data.get("id")
                commit_message = commit_data.get("message", "")

                if not commit_sha:
                    continue

                # Try to find ticket ID in commit message
                # Pattern: "ticket-{id}" or "#{id}" or "TICKET-{id}"
                ticket_id = self._extract_ticket_id_from_message(commit_message)

                if ticket_id:
                    # Link commit to ticket
                    result = await self._link_commit_to_ticket(
                        session,
                        project.id,
                        ticket_id,
                        commit_sha,
                        commit_message,
                        commit_data,
                    )
                    if result:
                        linked_count += 1

            session.commit()

            return {
                "success": True,
                "message": f"Processed {len(commits)} commits, linked {linked_count}",
            }

    async def _handle_pull_request_event(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle GitHub pull request event.

        On PR Opened:
        1. Extract ticket ID from PR title, body, or branch name
        2. Create TicketPullRequest record with state="open"
        3. Publish PR_OPENED event

        On PR Merged:
        1. Find linked TicketPullRequest by (repo, pr_number)
        2. Update state="merged" and merged_at=now
        3. Find associated task via ticket_id
        4. Mark task as completed
        5. Mark ticket status as done
        6. Publish PR_MERGED event

        On PR Closed (without merge):
        1. Update state="closed"
        2. Publish PR_CLOSED event
        """
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        repository = payload.get("repository", {})

        owner = repository.get("owner", {}).get("login")
        repo = repository.get("name")

        if not owner or not repo:
            return {"success": False, "message": "Invalid repository data"}

        pr_number = pr.get("number")
        if not pr_number:
            return {"success": False, "message": "Missing PR number"}

        logger.info(f"Processing PR event: {action} for {owner}/{repo}#{pr_number}")

        if action == "opened":
            return await self._handle_pr_opened(payload, owner, repo, pr, pr_number)
        elif action == "closed":
            if pr.get("merged"):
                return await self._handle_pr_merged(payload, owner, repo, pr, pr_number)
            else:
                return await self._handle_pr_closed(payload, owner, repo, pr, pr_number)
        elif action == "synchronize":
            # PR was updated (new commits pushed)
            return {
                "success": True,
                "message": f"PR {pr_number} synchronize event acknowledged",
            }
        elif action == "reopened":
            return await self._handle_pr_reopened(payload, owner, repo, pr, pr_number)
        else:
            return {"success": True, "message": f"PR event {action} acknowledged"}

    async def _handle_pr_opened(
        self,
        payload: Dict[str, Any],
        owner: str,
        repo: str,
        pr: Dict[str, Any],
        pr_number: int,
    ) -> Dict[str, Any]:
        """Handle PR opened event - link to ticket and create record."""
        pr_title = pr.get("title", "")
        pr_body = pr.get("body", "") or ""
        head_branch = pr.get("head", {}).get("ref", "")
        base_branch = pr.get("base", {}).get("ref", "")
        html_url = pr.get("html_url", "")
        github_user = pr.get("user", {}).get("login", "unknown")

        # Extract ticket ID from PR title, body, or branch name
        ticket_id = self._extract_ticket_id_from_pr(pr_title, pr_body, head_branch)

        if not ticket_id:
            logger.info(f"No ticket ID found in PR {owner}/{repo}#{pr_number}")
            return {
                "success": True,
                "message": f"PR {pr_number} opened but no ticket ID found",
            }

        with self.db.get_session() as session:
            # Verify ticket exists
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found for PR {pr_number}")
                return {
                    "success": False,
                    "message": f"Ticket {ticket_id} not found",
                }

            # Check if PR already linked
            existing = (
                session.query(TicketPullRequest)
                .filter(
                    TicketPullRequest.repo_owner == owner,
                    TicketPullRequest.repo_name == repo,
                    TicketPullRequest.pr_number == pr_number,
                )
                .first()
            )

            if existing:
                logger.info(
                    f"PR {pr_number} already linked to ticket {existing.ticket_id}"
                )
                return {
                    "success": True,
                    "message": f"PR {pr_number} already linked to ticket",
                }

            # Create TicketPullRequest record
            pr_record = TicketPullRequest(
                id=f"pr-{uuid4()}",
                ticket_id=ticket_id,
                pr_number=pr_number,
                pr_title=pr_title,
                pr_body=pr_body[:10000] if pr_body else None,  # Truncate if too long
                head_branch=head_branch,
                base_branch=base_branch,
                repo_owner=owner,
                repo_name=repo,
                state="open",
                html_url=html_url,
                github_user=github_user,
            )
            session.add(pr_record)
            session.commit()

            logger.info(f"Linked PR {pr_number} to ticket {ticket_id}")

            # Publish event
            self.event_bus.publish(
                SystemEvent(
                    event_type="PR_OPENED",
                    entity_type="pull_request",
                    entity_id=pr_record.id,
                    payload={
                        "pr_number": pr_number,
                        "ticket_id": ticket_id,
                        "repo_owner": owner,
                        "repo_name": repo,
                        "html_url": html_url,
                        "head_branch": head_branch,
                        "base_branch": base_branch,
                    },
                )
            )

            return {
                "success": True,
                "message": f"PR {pr_number} linked to ticket {ticket_id}",
                "ticket_id": ticket_id,
                "pr_record_id": pr_record.id,
            }

    async def _handle_pr_merged(
        self,
        payload: Dict[str, Any],
        owner: str,
        repo: str,
        pr: Dict[str, Any],
        pr_number: int,
    ) -> Dict[str, Any]:
        """
        Handle PR merged event.

        1. Find linked TicketPullRequest
        2. Update state to merged
        3. Mark associated task as completed
        4. Mark ticket as done
        5. Publish event
        """
        merge_commit_sha = pr.get("merge_commit_sha")
        pr.get("merged_at")

        with self.db.get_session() as session:
            # Find linked PR record
            pr_record = (
                session.query(TicketPullRequest)
                .filter(
                    TicketPullRequest.repo_owner == owner,
                    TicketPullRequest.repo_name == repo,
                    TicketPullRequest.pr_number == pr_number,
                )
                .first()
            )

            if not pr_record:
                # PR was not linked to a ticket - try to find ticket ID from PR
                pr_title = pr.get("title", "")
                pr_body = pr.get("body", "") or ""
                head_branch = pr.get("head", {}).get("ref", "")

                ticket_id = self._extract_ticket_id_from_pr(
                    pr_title, pr_body, head_branch
                )
                if not ticket_id:
                    logger.info(f"PR {pr_number} merged but not linked to any ticket")
                    return {
                        "success": True,
                        "message": f"PR {pr_number} merged but not linked to any ticket",
                    }

                # Check if ticket exists
                ticket = session.get(Ticket, ticket_id)
                if not ticket:
                    return {
                        "success": False,
                        "message": f"Ticket {ticket_id} not found",
                    }

                # Create PR record retroactively
                pr_record = TicketPullRequest(
                    id=f"pr-{uuid4()}",
                    ticket_id=ticket_id,
                    pr_number=pr_number,
                    pr_title=pr_title,
                    pr_body=pr_body[:10000] if pr_body else None,
                    head_branch=head_branch,
                    base_branch=pr.get("base", {}).get("ref", ""),
                    repo_owner=owner,
                    repo_name=repo,
                    state="merged",
                    html_url=pr.get("html_url", ""),
                    github_user=pr.get("user", {}).get("login", "unknown"),
                    merge_commit_sha=merge_commit_sha,
                    merged_at=utc_now(),
                )
                session.add(pr_record)
            else:
                # Update existing PR record
                pr_record.state = "merged"
                pr_record.merge_commit_sha = merge_commit_sha
                pr_record.merged_at = utc_now()

            ticket_id = pr_record.ticket_id

            # Get the ticket
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                session.commit()
                return {
                    "success": False,
                    "message": f"Ticket {ticket_id} not found",
                }

            # Mark associated tasks as completed
            tasks_updated = 0
            running_tasks = (
                session.query(Task)
                .filter(
                    Task.ticket_id == ticket_id,
                    Task.status.in_(["pending", "assigned", "running"]),
                )
                .all()
            )

            for task in running_tasks:
                task.status = "completed"
                task.completed_at = utc_now()
                task.result = task.result or {}
                task.result["pr_merged"] = {
                    "pr_number": pr_number,
                    "merge_commit_sha": merge_commit_sha,
                    "completed_by": "github_webhook",
                }
                tasks_updated += 1

                # Publish task completed event
                self.event_bus.publish(
                    SystemEvent(
                        event_type="TASK_COMPLETED",
                        entity_type="task",
                        entity_id=str(task.id),
                        payload={
                            "ticket_id": ticket_id,
                            "completed_by": "pr_merge",
                            "pr_number": pr_number,
                        },
                    )
                )

            # Update ticket status to done
            from omoi_os.models.ticket_status import TicketStatus

            old_status = ticket.status
            if ticket.status != TicketStatus.DONE.value:
                ticket.status = TicketStatus.DONE.value
                # Sync phase_id to keep board column in sync
                ticket.phase_id = "PHASE_DONE"
                ticket.updated_at = utc_now()

                # Publish ticket status change event
                # Use TICKET_STATUS_CHANGED to match frontend expectations
                self.event_bus.publish(
                    SystemEvent(
                        event_type="TICKET_STATUS_CHANGED",
                        entity_type="ticket",
                        entity_id=str(ticket.id),
                        payload={
                            "from_status": old_status,
                            "to_status": TicketStatus.DONE.value,
                            "phase_id": "PHASE_DONE",
                            "reason": f"PR #{pr_number} merged",
                            "pr_number": pr_number,
                            "merge_commit_sha": merge_commit_sha,
                        },
                    )
                )

            session.commit()

            logger.info(
                f"PR {pr_number} merged: ticket {ticket_id} marked as done, "
                f"{tasks_updated} tasks completed"
            )

            # Publish PR merged event
            self.event_bus.publish(
                SystemEvent(
                    event_type="PR_MERGED",
                    entity_type="pull_request",
                    entity_id=pr_record.id,
                    payload={
                        "pr_number": pr_number,
                        "ticket_id": ticket_id,
                        "repo_owner": owner,
                        "repo_name": repo,
                        "merge_commit_sha": merge_commit_sha,
                        "tasks_completed": tasks_updated,
                    },
                )
            )

            return {
                "success": True,
                "message": f"PR {pr_number} merged, ticket {ticket_id} done",
                "ticket_id": ticket_id,
                "tasks_completed": tasks_updated,
            }

    async def _handle_pr_closed(
        self,
        payload: Dict[str, Any],
        owner: str,
        repo: str,
        pr: Dict[str, Any],
        pr_number: int,
    ) -> Dict[str, Any]:
        """Handle PR closed (without merge) event."""
        with self.db.get_session() as session:
            pr_record = (
                session.query(TicketPullRequest)
                .filter(
                    TicketPullRequest.repo_owner == owner,
                    TicketPullRequest.repo_name == repo,
                    TicketPullRequest.pr_number == pr_number,
                )
                .first()
            )

            if not pr_record:
                return {
                    "success": True,
                    "message": f"PR {pr_number} closed but not tracked",
                }

            pr_record.state = "closed"
            pr_record.closed_at = utc_now()
            session.commit()

            # Publish event
            self.event_bus.publish(
                SystemEvent(
                    event_type="PR_CLOSED",
                    entity_type="pull_request",
                    entity_id=pr_record.id,
                    payload={
                        "pr_number": pr_number,
                        "ticket_id": pr_record.ticket_id,
                        "repo_owner": owner,
                        "repo_name": repo,
                    },
                )
            )

            return {
                "success": True,
                "message": f"PR {pr_number} closed",
                "ticket_id": pr_record.ticket_id,
            }

    async def _handle_pr_reopened(
        self,
        payload: Dict[str, Any],
        owner: str,
        repo: str,
        pr: Dict[str, Any],
        pr_number: int,
    ) -> Dict[str, Any]:
        """Handle PR reopened event."""
        with self.db.get_session() as session:
            pr_record = (
                session.query(TicketPullRequest)
                .filter(
                    TicketPullRequest.repo_owner == owner,
                    TicketPullRequest.repo_name == repo,
                    TicketPullRequest.pr_number == pr_number,
                )
                .first()
            )

            if not pr_record:
                # Create new record if doesn't exist
                return await self._handle_pr_opened(payload, owner, repo, pr, pr_number)

            pr_record.state = "open"
            pr_record.closed_at = None
            session.commit()

            return {
                "success": True,
                "message": f"PR {pr_number} reopened",
                "ticket_id": pr_record.ticket_id,
            }

    def _extract_ticket_id_from_pr(
        self, title: str, body: str, branch: str
    ) -> Optional[str]:
        """
        Extract ticket ID from PR title, body, or branch name.

        Patterns supported:
        - PR title: "[TICKET-abc123] Add feature" or "[ticket-abc123]"
        - PR body: "Closes ticket-abc123" or "Fixes #ticket-abc123"
        - Branch name: "feature/ticket-abc123-description" or "ticket-abc123"

        Args:
            title: PR title
            body: PR body/description
            branch: Head branch name

        Returns:
            Ticket ID if found, None otherwise
        """
        # Pattern for ticket IDs (UUID format or custom format)
        # Matches: ticket-{uuid} or TICKET-{uuid}
        uuid_pattern = (
            r"ticket-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"
        )

        # Pattern for short ticket IDs
        # Matches: ticket-{alphanumeric}

        # Check title first (most explicit)
        # Look for [TICKET-xxx] or [ticket-xxx] pattern
        title_bracket_pattern = r"\[ticket-([a-f0-9-]+)\]"
        match = re.search(title_bracket_pattern, title, re.IGNORECASE)
        if match:
            ticket_id = match.group(1)
            # Return full ticket ID format if it looks like a UUID
            if len(ticket_id) == 36:
                return ticket_id
            return f"ticket-{ticket_id}"

        # Check title for direct mention
        match = re.search(uuid_pattern, title, re.IGNORECASE)
        if match:
            return match.group(1)

        # Check body for "Closes ticket-xxx" or "Fixes ticket-xxx"
        if body:
            closes_pattern = r"(?:closes?|fixes?|resolves?)\s+(?:#)?ticket-([a-f0-9-]+)"
            match = re.search(closes_pattern, body, re.IGNORECASE)
            if match:
                ticket_id = match.group(1)
                if len(ticket_id) == 36:
                    return ticket_id
                return f"ticket-{ticket_id}"

            # Also check for plain ticket-xxx mentions in body
            match = re.search(uuid_pattern, body, re.IGNORECASE)
            if match:
                return match.group(1)

        # Check branch name
        # Patterns: feature/ticket-xxx, ticket-xxx-description, xxx/ticket-xxx
        if branch:
            # Try UUID pattern first
            match = re.search(uuid_pattern, branch, re.IGNORECASE)
            if match:
                return match.group(1)

            # Try extracting from branch path
            branch_pattern = r"(?:^|/)ticket-([a-f0-9-]+)"
            match = re.search(branch_pattern, branch, re.IGNORECASE)
            if match:
                ticket_id = match.group(1)
                # Remove any trailing description after the ID
                # e.g., "abc123-add-feature" -> "abc123"
                if "-" in ticket_id:
                    # Check if it's a UUID (has 4 dashes in specific positions)
                    parts = ticket_id.split("-")
                    if len(parts) >= 5 and len(parts[0]) == 8:
                        # Looks like a UUID, keep it
                        return "-".join(parts[:5])
                    # Otherwise take just the first part
                    return f"ticket-{parts[0]}"
                return f"ticket-{ticket_id}"

        return None

    async def _handle_issue_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GitHub issue event."""
        action = payload.get("action")
        payload.get("issue", {})
        repository = payload.get("repository", {})

        repository.get("owner", {}).get("login")
        repository.get("name")

        if action == "opened":
            # Could create a ticket from issue
            # This would need additional logic
            pass

        return {"success": True, "message": f"Issue event {action} processed"}

    def _extract_ticket_id_from_message(self, message: str) -> Optional[str]:
        """
        Extract ticket ID from commit message.

        Looks for patterns like:
        - "ticket-{uuid}"
        - "#{id}"
        - "TICKET-{id}"

        Args:
            message: Commit message

        Returns:
            Ticket ID if found, None otherwise
        """
        # Pattern 1: ticket-{uuid}
        pattern1 = r"ticket-([a-f0-9-]{36})"
        match = re.search(pattern1, message, re.IGNORECASE)
        if match:
            return f"ticket-{match.group(1)}"

        # Pattern 2: # followed by ticket ID
        pattern2 = r"#(\w+-\w+)"
        match = re.search(pattern2, message, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    async def _link_commit_to_ticket(
        self,
        session,
        project_id: str,
        ticket_id: str,
        commit_sha: str,
        commit_message: str,
        commit_data: Dict[str, Any],
    ) -> bool:
        """
        Link a commit to a ticket.

        Args:
            session: Database session
            project_id: Project ID
            ticket_id: Ticket ID
            commit_sha: Commit SHA
            commit_message: Commit message
            commit_data: Full commit data from GitHub

        Returns:
            True if linked successfully
        """
        # Verify ticket exists
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            return False

        # Check if already linked
        existing = (
            session.query(TicketCommit)
            .filter(
                TicketCommit.ticket_id == ticket_id,
                TicketCommit.commit_sha == commit_sha,
            )
            .first()
        )

        if existing:
            return False

        # Extract stats from commit data
        stats = commit_data.get("stats", {})
        files_changed = (
            len(commit_data.get("added", []))
            + len(commit_data.get("modified", []))
            + len(commit_data.get("removed", []))
        )

        # Build files_list
        files_list = {}
        for file in commit_data.get("added", []):
            files_list[file] = {"status": "added", "additions": 0, "deletions": 0}
        for file in commit_data.get("modified", []):
            files_list[file] = {"status": "modified", "additions": 0, "deletions": 0}
        for file in commit_data.get("removed", []):
            files_list[file] = {"status": "removed", "additions": 0, "deletions": 0}

        # Create commit record
        commit = TicketCommit(
            id=f"commit-{uuid4()}",
            ticket_id=ticket_id,
            agent_id=commit_data.get("author", {}).get("name", "unknown"),
            commit_sha=commit_sha,
            commit_message=commit_message,
            commit_timestamp=utc_now(),  # Would use actual commit timestamp if available
            files_changed=files_changed,
            insertions=stats.get("additions", 0),
            deletions=stats.get("deletions", 0),
            files_list=files_list,
            link_method="webhook",
        )

        session.add(commit)

        # Emit event
        self.event_bus.publish(
            SystemEvent(
                event_type="COMMIT_LINKED",
                entity_type="commit",
                entity_id=commit.id,
                payload={
                    "commit_sha": commit_sha,
                    "ticket_id": ticket_id,
                    "project_id": project_id,
                    "link_method": "webhook",
                },
            )
        )

        return True

    async def connect_repository(
        self,
        project_id: str,
        owner: str,
        repo: str,
        webhook_secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Connect a GitHub repository to a project.

        Args:
            project_id: Project ID
            owner: GitHub repository owner
            repo: Repository name
            webhook_secret: Optional webhook secret

        Returns:
            Connection result
        """
        with self.db.get_session() as session:
            project = session.get(Project, project_id)
            if not project:
                return {"success": False, "message": "Project not found"}

            project.github_owner = owner
            project.github_repo = repo
            project.github_webhook_secret = webhook_secret
            project.github_connected = True

            session.commit()

            return {
                "success": True,
                "message": f"Repository {owner}/{repo} connected",
            }
