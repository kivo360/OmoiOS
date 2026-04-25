"""Unit tests for orchestrator_worker._extract_session_env.

Validates that the env-var emission correctly handles both the legacy
ticket-driven subject shape and the new SDK-direct ticket-less shape.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4


from omoi_os.services.session_subject import SessionSubject
from omoi_os.workers.orchestrator_worker import (
    SandboxSpawnContext,
    _extract_session_env,
)


def _null_log():
    log = SimpleNamespace()
    log.warning = lambda *a, **k: None
    log.info = lambda *a, **k: None
    log.error = lambda *a, **k: None
    log.debug = lambda *a, **k: None
    return log


def _mk_ctx(task_id="task-1", ticket_id=None, spawn_mode="implementation"):
    return SandboxSpawnContext(
        task_id=task_id,
        phase_id="PHASE_IMPLEMENTATION",
        ticket_id=ticket_id,
        task_type="implement_feature",
        task_description="desc",
        task_priority="HIGH",
        spawn_mode=spawn_mode,
    )


def test_extract_session_env_ticketless_sdk_direct():
    org = uuid4()
    ws = uuid4()
    user = uuid4()
    subject = SessionSubject(
        task_id="task-1",
        title="ticketless hello",
        description="no ticket attached",
        priority="MEDIUM",
        phase_id="PHASE_IMPLEMENTATION",
        context={},
        organization_id=org,
        workspace_id=ws,
        environment_version_id=None,
        user_id_for_token=user,
        github_owner="octocat",
        github_repo="hello-world",
        github_repo_slug="octocat/hello-world",
        ticket_id=None,
        ticket_type=None,
    )
    ctx = _mk_ctx()

    _extract_session_env(ctx, subject, _null_log())

    assert ctx.extra_env["SESSION_ID"] == "task-1"
    assert "TICKET_ID" not in ctx.extra_env
    assert ctx.extra_env["TICKET_TITLE"] == "ticketless hello"
    assert (
        ctx.extra_env["TICKET_TYPE"] == "feature"
    )  # from priority=MEDIUM + clean title
    assert ctx.extra_env["TICKET_PRIORITY"] == "MEDIUM"
    assert ctx.extra_env["OMOIOS_WORKSPACE_ID"] == str(ws)
    assert ctx.extra_env["OMOIOS_ORGANIZATION_ID"] == str(org)
    assert ctx.extra_env["USER_ID"] == str(user)
    assert ctx.extra_env["GITHUB_REPO"] == "octocat/hello-world"
    assert ctx.extra_env["GITHUB_REPO_OWNER"] == "octocat"
    assert ctx.extra_env["GITHUB_REPO_NAME"] == "hello-world"
    assert ctx.user_id_for_token == user


def test_extract_session_env_legacy_ticket_full():
    org = uuid4()
    user = uuid4()
    subject = SessionSubject(
        task_id="task-legacy",
        title="Fix login bug",
        description="users can't log in",
        priority="CRITICAL",
        phase_id="PHASE_IMPLEMENTATION",
        context={"log": "abc"},
        organization_id=org,
        workspace_id=None,
        environment_version_id=None,
        user_id_for_token=user,
        github_owner="acme",
        github_repo="service",
        github_repo_slug="acme/service",
        ticket_id="TKT-123",
        ticket_type="hotfix",
    )
    ctx = _mk_ctx(task_id="task-legacy", ticket_id="TKT-123")

    _extract_session_env(ctx, subject, _null_log())

    assert ctx.extra_env["TICKET_ID"] == "TKT-123"
    assert ctx.extra_env["TICKET_TYPE"] == "hotfix"
    assert ctx.extra_env["TICKET_PRIORITY"] == "CRITICAL"
    assert ctx.extra_env["GITHUB_REPO"] == "acme/service"
    # No workspace for legacy shape
    assert "OMOIOS_WORKSPACE_ID" not in ctx.extra_env
    assert ctx.extra_env["OMOIOS_ORGANIZATION_ID"] == str(org)
    assert ctx.user_id_for_token == user


def test_extract_session_env_no_github_no_user_logs_warnings():
    subject = SessionSubject(
        task_id="task-orphan",
        title="standalone",
        description="",
        priority="LOW",
        phase_id="PHASE_IMPLEMENTATION",
        context={},
        organization_id=None,
        workspace_id=None,
        environment_version_id=None,
        user_id_for_token=None,
        github_owner=None,
        github_repo=None,
        github_repo_slug=None,
        ticket_id=None,
        ticket_type=None,
    )
    ctx = _mk_ctx(task_id="task-orphan")

    _extract_session_env(ctx, subject, _null_log())

    # SESSION_ID always set; nothing else has to be present
    assert ctx.extra_env["SESSION_ID"] == "task-orphan"
    assert "TICKET_ID" not in ctx.extra_env
    assert "GITHUB_REPO" not in ctx.extra_env
    assert "USER_ID" not in ctx.extra_env
    assert ctx.user_id_for_token is None
