"""Unit tests for the new SessionCreate body model (Wave 3 Task 7)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from omoi_os.api.routes.sessions import SessionCreate


def test_sdk_direct_minimal_body_accepted():
    body = SessionCreate(
        workspace_id=uuid4(),
        prompt="hello from ticketless session",
    )
    assert body.prompt == "hello from ticketless session"
    assert body.ticket_id is None
    assert body.title is None


def test_sdk_direct_with_github_repo_only():
    body = SessionCreate(
        github_repo="octocat/hello-world",
        prompt="explore",
    )
    assert body.workspace_id is None
    assert body.github_repo == "octocat/hello-world"


def test_legacy_ticketful_body_still_accepted():
    body = SessionCreate(
        ticket_id="TKT-1",
        title="Fix bug",
        description="we have a bug",
    )
    assert body.ticket_id == "TKT-1"
    assert body.title == "Fix bug"


def test_rejects_malformed_github_repo():
    with pytest.raises(Exception):
        SessionCreate(github_repo="not_a_slug", prompt="hi")


def test_accepts_task_type_alias_for_session_type():
    body = SessionCreate(task_type="validation", prompt="run validation")
    assert body.session_type == "validation"


def test_ignores_unknown_fields_without_422():
    # Legacy clients may send stray fields; we ignore rather than reject.
    body = SessionCreate.model_validate(
        {
            "workspace_id": str(uuid4()),
            "prompt": "hello",
            "legacy_field_that_does_not_exist": "whatever",
        }
    )
    assert body.prompt == "hello"


def test_share_with_list_accepts_uuids():
    user_a = uuid4()
    user_b = uuid4()
    body = SessionCreate(
        workspace_id=uuid4(),
        prompt="hi",
        share_with=[user_a, user_b],
    )
    assert body.share_with == [user_a, user_b]
