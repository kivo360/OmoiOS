"""GitHub Integration Service for repository management and webhook handling."""

import hmac
import hashlib
from typing import Optional, Dict, Any

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from omoi_os.models.project import Project
from omoi_os.models.ticket import Ticket
from omoi_os.ticketing.models import TicketCommit
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.utils.datetime import utc_now


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
        """Handle GitHub pull request event."""
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        repository = payload.get("repository", {})

        owner = repository.get("owner", {}).get("login")
        repo = repository.get("name")

        if action == "opened":
            # Could create a ticket from PR
            pass
        elif action == "closed" and pr.get("merged"):
            # PR merged - could mark task as completed
            pr_number = pr.get("number")
            merge_commit_sha = pr.get("merge_commit_sha")

            # Try to find linked task/ticket from PR description or labels
            # This would need additional logic

        return {"success": True, "message": f"PR event {action} processed"}

    async def _handle_issue_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GitHub issue event."""
        action = payload.get("action")
        issue = payload.get("issue", {})
        repository = payload.get("repository", {})

        owner = repository.get("owner", {}).get("login")
        repo = repository.get("name")

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
        import re

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
        from uuid import uuid4

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
        from omoi_os.services.event_bus import SystemEvent

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
