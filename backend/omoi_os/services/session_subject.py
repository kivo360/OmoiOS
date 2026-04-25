"""SessionSubject — unified view of a Task's session context.

The orchestrator, the Daytona spawner, and the task queue all need the same
handful of facts about a session: which org owns it, which user owns the
GitHub token, which repo gets cloned, what to use for a title/description/
branch prefix. Historically each service walked its own relationship chain:

    task -> task.ticket -> task.ticket.project -> project.organization_id
                                                  project.github_owner/repo
                                                  project.created_by
                        -> ticket.user_id

That chain forced every session into the Ticket/Project workflow world, and
it was the reason an SDK caller couldn't create a session without first
hand-seeding an org + project + ticket.

Migration 071 broke the FK coupling (`tasks.ticket_id` is nullable; four
direct columns were promoted to `tasks`). This module is the runtime
counterpart: a single resolver that reads the direct columns first and
falls back to the ticket chain for legacy rows. Every consumer reads the
same dataclass, so the relationship-chasing pattern never leaks back in.

Precedence (first non-null wins per field):
    1. Direct column on the task row (workspace_id, environment_version_id,
       created_by, github_repo).
    2. Workspace relationship (workspace.organization_id,
       workspace.github_owner/repo).
    3. Ticket chain (ticket.user_id, ticket.project.organization_id,
       ticket.project.github_owner/repo, ticket.project.created_by).
    4. Defaults (the Task row's own title/description/priority, Nones
       elsewhere).

Callers pass in an open SQLAlchemy session; this module never opens its
own. `resolve()` is side-effect-free and cheap (at most two `session.get`
lookups for workspace + ticket, then one more for ticket.project).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.project import Project
from omoi_os.models.workspace import Workspace


@dataclass(frozen=True)
class SessionSubject:
    """Unified read-only view of a task's session context."""

    task_id: str
    title: str
    description: str
    priority: str
    phase_id: Optional[str]
    context: dict

    organization_id: Optional[UUID]
    workspace_id: Optional[UUID]
    environment_version_id: Optional[UUID]

    # who owns the GitHub OAuth token we should use to clone / push
    user_id_for_token: Optional[UUID]

    github_owner: Optional[str]
    github_repo: Optional[str]
    github_repo_slug: Optional[str]

    # Preserved for back-compat env vars (TICKET_ID, TICKET_TYPE)
    ticket_id: Optional[str]
    ticket_type: Optional[str]


def _split_repo_slug(slug: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Split "owner/repo" into (owner, repo). Returns (None, None) for bad input."""
    if not slug or "/" not in slug:
        return None, None
    owner, repo = slug.split("/", 1)
    owner, repo = owner.strip(), repo.strip()
    if not owner or not repo:
        return None, None
    return owner, repo


def _join_repo(owner: Optional[str], repo: Optional[str]) -> Optional[str]:
    if owner and repo:
        return f"{owner}/{repo}"
    return None


def _infer_ticket_type(priority: Optional[str], title: Optional[str]) -> Optional[str]:
    """Derive the legacy ticket_type string used by the spawner for branch prefix
    selection. Keeps the historical mapping from orchestrator_worker intact."""
    if not priority and not title:
        return None
    pri = (priority or "").upper()
    t = (title or "").lower()
    if pri == "CRITICAL" or "hotfix" in t:
        return "hotfix"
    if "bug" in t or "fix" in t:
        return "bug"
    return "feature"


def resolve(session: Session, task: Task) -> SessionSubject:
    """Resolve a SessionSubject for the given task using the caller's session.

    The caller controls transactions; this function only reads.
    """
    workspace: Optional[Workspace] = None
    if task.workspace_id:
        workspace = session.get(Workspace, task.workspace_id)

    ticket: Optional[Ticket] = None
    project: Optional[Project] = None
    if task.ticket_id:
        ticket = session.get(Ticket, task.ticket_id)
        if ticket and ticket.project_id:
            project = session.get(Project, ticket.project_id)

    # organization_id — workspace first, then ticket.project
    organization_id: Optional[UUID] = None
    if workspace and workspace.organization_id:
        organization_id = workspace.organization_id
    elif project and project.organization_id:
        organization_id = project.organization_id

    # GitHub owner/repo — task column first, then workspace, then project
    gh_owner: Optional[str] = None
    gh_repo: Optional[str] = None
    if task.github_repo:
        gh_owner, gh_repo = _split_repo_slug(task.github_repo)
    if gh_owner is None and workspace:
        if (
            workspace.github_connected
            and workspace.github_owner
            and workspace.github_repo
        ):
            gh_owner, gh_repo = workspace.github_owner, workspace.github_repo
    if gh_owner is None and project:
        if project.github_connected and project.github_owner and project.github_repo:
            gh_owner, gh_repo = project.github_owner, project.github_repo

    # user_id_for_token — direct column, then project creator, then ticket user
    user_id_for_token: Optional[UUID] = task.created_by
    if user_id_for_token is None and project:
        user_id_for_token = project.created_by
    if user_id_for_token is None and ticket:
        user_id_for_token = ticket.user_id

    # title / description / priority — Task row owns these, fall back to ticket
    title = task.title or (ticket.title if ticket else "") or f"session-{task.id[:8]}"
    description = task.description or (ticket.description if ticket else "") or ""
    priority = task.priority or (ticket.priority if ticket else None) or "MEDIUM"

    # context — ticket.context is the legacy blob used by _build_fallback_context;
    # ticket-less sessions have no context, which callers treat as {}
    context: dict = (ticket.context if ticket and ticket.context else {}) or {}

    ticket_type: Optional[str] = None
    if task.ticket_id:
        ticket_type = _infer_ticket_type(priority, title)

    return SessionSubject(
        task_id=task.id,
        title=title,
        description=description,
        priority=priority,
        phase_id=task.phase_id,
        context=context,
        organization_id=organization_id,
        workspace_id=task.workspace_id,
        environment_version_id=task.environment_version_id,
        user_id_for_token=user_id_for_token,
        github_owner=gh_owner,
        github_repo=gh_repo,
        github_repo_slug=_join_repo(gh_owner, gh_repo),
        ticket_id=task.ticket_id,
        ticket_type=ticket_type,
    )
