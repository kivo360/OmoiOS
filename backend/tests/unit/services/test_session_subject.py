"""Unit tests for SessionSubject.resolve() precedence across the four task shapes.

The four shapes we care about:

    (a) SDK-direct: workspace_id set, github_repo column populated,
        created_by set, ticket_id=None.
    (b) Workflow-full: ticket_id set, ticket.project linked with
        github_owner/repo + organization_id + created_by.
    (c) Ticket-only: ticket_id set but ticket.project_id=None (orphan ticket
        with only ticket.user_id for ownership).
    (d) Orphan: no ticket, no workspace, no created_by — everything falls
        back to task-row defaults.

We mock the SQLAlchemy session so the tests don't need a database; the
resolver only calls `session.get(...)` for Workspace / Ticket / Project
lookups.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock


from omoi_os.services.session_subject import resolve
from omoi_os.models.project import Project
from omoi_os.models.ticket import Ticket
from omoi_os.models.workspace import Workspace


def _mk_task(**kwargs):
    """Build a task-like SimpleNamespace with the fields resolve() reads."""
    defaults = dict(
        id=str(uuid4()),
        ticket_id=None,
        workspace_id=None,
        environment_version_id=None,
        created_by=None,
        github_repo=None,
        title=None,
        description=None,
        priority=None,
        phase_id="PHASE_IMPLEMENTATION",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _session_with(objects: dict) -> MagicMock:
    """Build a SQLAlchemy-like session whose .get(Type, id) returns objects[(Type, id)]."""
    sess = MagicMock()

    def _get(model, key):
        return objects.get((model, key))

    sess.get.side_effect = _get
    return sess


# ---------------------------------------------------------------------------
# Shape (a): SDK-direct — workspace + direct columns, no ticket
# ---------------------------------------------------------------------------
def test_resolve_sdk_direct_uses_workspace_and_direct_columns():
    org = uuid4()
    ws_id = uuid4()
    user = uuid4()
    env = uuid4()
    workspace = SimpleNamespace(
        id=ws_id,
        organization_id=org,
        github_owner="octocat",
        github_repo="hello-world",
        github_connected=True,
    )
    task = _mk_task(
        workspace_id=ws_id,
        environment_version_id=env,
        created_by=user,
        github_repo="foo/bar",  # takes precedence over workspace.github_repo
        title="Custom session title",
        description="Body",
        priority="HIGH",
    )
    sess = _session_with({(Workspace, ws_id): workspace})

    subject = resolve(sess, task)

    assert subject.organization_id == org
    assert subject.workspace_id == ws_id
    assert subject.environment_version_id == env
    assert subject.user_id_for_token == user
    # task.github_repo wins over workspace.github_owner/repo
    assert subject.github_owner == "foo"
    assert subject.github_repo == "bar"
    assert subject.github_repo_slug == "foo/bar"
    assert subject.ticket_id is None
    assert subject.ticket_type is None  # no ticket, no inferred type
    assert subject.title == "Custom session title"
    assert subject.description == "Body"
    assert subject.priority == "HIGH"


def test_resolve_sdk_direct_falls_back_to_workspace_github():
    org = uuid4()
    ws_id = uuid4()
    workspace = SimpleNamespace(
        id=ws_id,
        organization_id=org,
        github_owner="acme",
        github_repo="web",
        github_connected=True,
    )
    task = _mk_task(workspace_id=ws_id, title="t", description="d", priority="MEDIUM")
    sess = _session_with({(Workspace, ws_id): workspace})

    subject = resolve(sess, task)

    assert subject.github_owner == "acme"
    assert subject.github_repo == "web"
    assert subject.github_repo_slug == "acme/web"
    assert subject.organization_id == org


# ---------------------------------------------------------------------------
# Shape (b): Workflow-full — ticket + project, the legacy happy path
# ---------------------------------------------------------------------------
def test_resolve_workflow_full_uses_project_chain():
    org = uuid4()
    creator = uuid4()
    ticket_user = uuid4()
    ticket_id = str(uuid4())
    project_id = f"project-{uuid4()}"
    project = SimpleNamespace(
        id=project_id,
        organization_id=org,
        github_owner="acme",
        github_repo="service",
        github_connected=True,
        created_by=creator,
    )
    ticket = SimpleNamespace(
        id=ticket_id,
        project_id=project_id,
        user_id=ticket_user,
        title="Fix login bug",
        description="users can't log in",
        priority="CRITICAL",
        context={"log": "hello"},
    )
    task = _mk_task(
        ticket_id=ticket_id,
        # everything else null — this is the legacy shape
        title=None,
        description=None,
        priority=None,
    )
    sess = _session_with({(Ticket, ticket_id): ticket, (Project, project_id): project})

    subject = resolve(sess, task)

    assert subject.ticket_id == ticket_id
    assert subject.organization_id == org
    assert subject.workspace_id is None
    assert subject.github_owner == "acme"
    assert subject.github_repo == "service"
    # created_by None on the task → falls back to project.created_by
    assert subject.user_id_for_token == creator
    # Title/description/priority pulled from ticket
    assert subject.title == "Fix login bug"
    assert subject.description == "users can't log in"
    assert subject.priority == "CRITICAL"
    # Priority=CRITICAL drives ticket_type=hotfix
    assert subject.ticket_type == "hotfix"
    assert subject.context == {"log": "hello"}


# ---------------------------------------------------------------------------
# Shape (c): Ticket-only — ticket exists but has no project
# ---------------------------------------------------------------------------
def test_resolve_ticket_only_uses_ticket_user_id():
    ticket_id = str(uuid4())
    ticket_user = uuid4()
    ticket = SimpleNamespace(
        id=ticket_id,
        project_id=None,  # no project
        user_id=ticket_user,
        title="misc task",
        description=None,
        priority="LOW",
        context=None,
    )
    task = _mk_task(ticket_id=ticket_id)
    sess = _session_with({(Ticket, ticket_id): ticket})

    subject = resolve(sess, task)

    assert subject.organization_id is None
    assert subject.user_id_for_token == ticket_user
    assert subject.github_owner is None
    assert subject.github_repo is None
    assert subject.github_repo_slug is None
    assert subject.ticket_id == ticket_id
    # LOW priority + "misc task" title → feature
    assert subject.ticket_type == "feature"
    # Empty context becomes {}
    assert subject.context == {}


# ---------------------------------------------------------------------------
# Shape (d): Orphan — no ticket, no workspace, minimal task
# ---------------------------------------------------------------------------
def test_resolve_orphan_uses_task_defaults():
    task = _mk_task(
        title="Standalone session",
        description="no linkage",
        priority="MEDIUM",
    )
    sess = _session_with({})  # session.get returns None for everything

    subject = resolve(sess, task)

    assert subject.organization_id is None
    assert subject.workspace_id is None
    assert subject.environment_version_id is None
    assert subject.user_id_for_token is None
    assert subject.github_owner is None
    assert subject.github_repo is None
    assert subject.github_repo_slug is None
    assert subject.ticket_id is None
    assert subject.ticket_type is None
    assert subject.title == "Standalone session"
    assert subject.description == "no linkage"
    assert subject.priority == "MEDIUM"
    assert subject.context == {}


def test_resolve_orphan_synthesises_title_from_task_id():
    task = _mk_task(title=None, description=None, priority=None)
    sess = _session_with({})

    subject = resolve(sess, task)

    # With nothing to fall back to, title becomes "session-<first 8 chars>"
    assert subject.title.startswith("session-")
    assert subject.description == ""
    assert subject.priority == "MEDIUM"
