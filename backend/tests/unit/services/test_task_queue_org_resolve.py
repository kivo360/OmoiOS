"""Unit tests for TaskQueueService._resolve_organization_id.

Confirms the workspace-first / ticket-chain-fallback precedence so we can't
regress the concurrency-limit behaviour across ticket-ful and ticket-less
sessions.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

from omoi_os.services.task_queue import TaskQueueService
from omoi_os.models.project import Project
from omoi_os.models.ticket import Ticket
from omoi_os.models.workspace import Workspace


def _session_with(gets: dict, queries: dict | None = None) -> MagicMock:
    """Build a session where session.get(Model, key) -> gets[(Model, key)]
    and session.query(Model).filter(...).first() -> queries[Model]."""
    sess = MagicMock()

    def _get(model, key):
        return gets.get((model, key))

    sess.get.side_effect = _get

    def _query(model):
        q = MagicMock()

        def _filter(*_args, **_kwargs):
            f = MagicMock()
            f.first = MagicMock(return_value=(queries or {}).get(model))
            return f

        q.filter = _filter
        return q

    sess.query = _query
    return sess


def _svc():
    """TaskQueueService instance with only the bits we need stubbed."""
    return TaskQueueService.__new__(TaskQueueService)


def test_resolve_org_via_workspace():
    org = uuid4()
    ws_id = uuid4()
    ws = SimpleNamespace(organization_id=org)
    task = SimpleNamespace(id="t1", workspace_id=ws_id, ticket_id=None)
    sess = _session_with({(Workspace, ws_id): ws})

    result = _svc()._resolve_organization_id(sess, task)

    assert result == str(org)


def test_resolve_org_falls_back_to_ticket_project():
    org = uuid4()
    ticket = SimpleNamespace(id="tk", project_id="pr")
    project = SimpleNamespace(id="pr", organization_id=org)
    task = SimpleNamespace(id="t2", workspace_id=None, ticket_id="tk")
    sess = _session_with(
        gets={},
        queries={Ticket: ticket, Project: project},
    )

    result = _svc()._resolve_organization_id(sess, task)

    assert result == str(org)


def test_resolve_org_returns_none_for_orphan():
    task = SimpleNamespace(id="t3", workspace_id=None, ticket_id=None)
    sess = _session_with(gets={}, queries={})

    assert _svc()._resolve_organization_id(sess, task) is None


def test_resolve_org_workspace_beats_ticket():
    """If both workspace and ticket resolve, workspace wins (spec §02 path)."""
    ws_org = uuid4()
    proj_org = uuid4()  # different org
    ws_id = uuid4()
    ws = SimpleNamespace(organization_id=ws_org)
    ticket = SimpleNamespace(id="tk", project_id="pr")
    project = SimpleNamespace(id="pr", organization_id=proj_org)
    task = SimpleNamespace(id="t4", workspace_id=ws_id, ticket_id="tk")
    sess = _session_with(
        gets={(Workspace, ws_id): ws},
        queries={Ticket: ticket, Project: project},
    )

    assert _svc()._resolve_organization_id(sess, task) == str(ws_org)
