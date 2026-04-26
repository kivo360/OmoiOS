"""Session API routes — the primary session surface.

Historically this module shimmed `/api/v1/sessions/*` over `/api/v1/tasks/*`
(CRUD + update + delete). The `sessions-surface-spec-alignment` plan promotes
it to the canonical session API by adding the spec §03 endpoints directly
here:

- GET  `/api/v1/sessions/{id}/events`    — SSE with `Last-Event-ID` resume
- POST `/api/v1/sessions/{id}/messages`  — reply mid-session
- POST `/api/v1/sessions/{id}/fork`      — branch at event seq
- POST `/api/v1/sessions/{id}/share`     — ACL grants
- GET  `/api/v1/sessions/{id}/artifacts` — artifacts produced by session

The legacy list/get/create/update/delete aliases below still delegate to
`/api/v1/tasks/*` handlers — that indirection is fine, since the `tasks`
table IS the session store. The task→session rename happens at the API
surface, not the DB.
"""

from __future__ import annotations

import asyncio
import json
from io import StringIO
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import sqlalchemy as sa
from sqlalchemy import select

from omoi_os.api.dependencies import (
    get_current_user,
    get_db_service,
    get_task_queue,
    verify_task_access,
)
from omoi_os.api.routes import tasks as tasks_router
from omoi_os.config import is_feature_enabled
from omoi_os.logging import get_logger
from omoi_os.models.event import Event
from omoi_os.models.environment import EnvironmentVersion
from omoi_os.models.workspace_settings import WorkspaceSettings
from omoi_os.models.session_acl import SessionACL, SessionFork
from omoi_os.models.task import Task
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.session_event_envelope import (
    SessionEventEnvelope,
    actor_user,
)
from omoi_os.services.sandbox_session_service import SandboxSessionService
from omoi_os.services.sandbox_session_token_transport import (
    store_session_token_for_task,
)
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)

router = APIRouter()

# Deprecation header value
DEPRECATION_HEADER = "Use /api/v1/tasks instead. Removed in v2.0."


# ============================================================================
# Request/Response Models (aliases for task models with session_id support)
# ============================================================================


class SessionCreate(BaseModel):
    """Request model for creating a session.

    Spec §03 shape: `{workspace_id, environment_id, prompt, share_with,
    github_repo, metadata}`. `ticket_id` is tolerated as a legacy field but
    ignored on the way to the Task insert — the SDK never sends it, and the
    dashboard goes through `/api/v1/tickets` which creates tasks out-of-band.

    Either `workspace_id` OR `github_repo` must be present; when only
    `github_repo` is supplied and the caller has a resolvable org, a
    workspace is auto-created via `ensure_workspace_for_github_repo`
    (mirrors the auto-project pattern in tickets.py).
    """

    # Tolerate unexpected fields from legacy callers without 422ing.
    model_config = {"populate_by_name": True, "extra": "ignore"}

    # Spec-shaped fields
    workspace_id: Optional[UUID] = None
    environment_id: Optional[UUID] = None
    prompt: Optional[str] = None
    github_repo: Optional[str] = Field(
        default=None, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    )
    share_with: List[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Back-compat fields — accepted for clients that still send them, but the
    # primary session payload is `prompt`. `title`/`description` are still
    # populated on the Task row so the dashboard list view renders sanely.
    ticket_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    session_type: str = Field(default="implementation", alias="task_type")
    priority: str = "MEDIUM"
    phase_id: str = "PHASE_IMPLEMENTATION"
    dependencies: Optional[Dict[str, Any]] = None
    execution_config: Optional[tasks_router.ExecutionConfig] = None


class SessionUpdate(BaseModel):
    """Request model for updating a session (alias for task)."""

    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


# ============================================================================
# Feature Flag Guard
# ============================================================================


def check_feature_flag() -> None:
    """Check if sessions API v1 feature is enabled.

    Raises:
        HTTPException: 404 if feature flag is disabled
    """
    if not is_feature_enabled("sessions_api_v1"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessions API not available",
        )


# ============================================================================
# Response Transformation Helpers
# ============================================================================


def _add_session_id_to_response(data: Any) -> Any:
    """Add session_id field alongside id field in response data.

    This ensures backward compatibility by providing both id and session_id
    fields in responses, where session_id is an alias for task_id.
    """
    if isinstance(data, dict):
        result = dict(data)
        if "id" in result and "session_id" not in result:
            result["session_id"] = result["id"]
        return result
    elif isinstance(data, list):
        return [_add_session_id_to_response(item) for item in data]
    return data


def _session_urls(
    request: Request, session_id: str, task_result: Optional[dict]
) -> Dict[str, Any]:
    """Build spec §02 §Session `urls` object.

    `events_sse` and `websocket` are derived from the request's base URL.
    `editor` is pulled from `task.result['tunnel_urls']` (populated by the
    spawner when `env_version.exposed_ports` is set — see Wave 3 Task 7).
    Returns None for editor when no tunnel was opened.
    """
    base = str(request.base_url).rstrip("/")
    ws_base = base.replace("https://", "wss://", 1).replace("http://", "ws://", 1)

    editor_url: Optional[str] = None
    if task_result and isinstance(task_result.get("tunnel_urls"), dict):
        tunnels = task_result["tunnel_urls"]
        # Prefer 8443 (the hosted-editor convention), else first port.
        if "8443" in tunnels:
            editor_url = tunnels["8443"]
        elif tunnels:
            editor_url = next(iter(tunnels.values()))

    return {
        "events_sse": f"{base}/api/v1/sessions/{session_id}/events",
        "websocket": f"{ws_base}/api/v1/sessions/{session_id}/ws",
        "editor": editor_url,
    }


async def _session_usage(db: DatabaseService, session_id: str) -> Dict[str, Any]:
    """Aggregate per-session usage — compute_seconds + token totals.

    Matches the `/api/v1/usage/sessions/{id}` shape for consistency. Shares
    the same query pattern; duplicated here because the session response
    builder is synchronous about its own data.
    """
    from sqlalchemy import func, select as _sa_select
    from omoi_os.models.cost_record import CostRecord

    async with db.get_async_session() as session:
        stmt = _sa_select(
            func.coalesce(func.sum(CostRecord.prompt_tokens), 0),
            func.coalesce(func.sum(CostRecord.completion_tokens), 0),
            func.coalesce(func.sum(CostRecord.total_cost), 0.0),
        ).where(CostRecord.task_id == session_id)
        row = (await session.execute(stmt)).one()
        tokens_in, tokens_out, total_cost = row

        task_row = (
            await session.execute(
                _sa_select(Task.started_at, Task.completed_at).where(
                    Task.id == session_id
                )
            )
        ).first()

    compute_seconds = 0.0
    if task_row is not None and task_row.started_at is not None:
        end = task_row.completed_at or task_row.started_at
        try:
            compute_seconds = max(0.0, (end - task_row.started_at).total_seconds())
        except Exception:
            compute_seconds = 0.0

    return {
        "compute_seconds": compute_seconds,
        "tokens_input": int(tokens_in or 0),
        "tokens_output": int(tokens_out or 0),
        "total_cost": float(total_cost or 0.0),
    }


async def _enrich_session_response(
    request: Request,
    db: DatabaseService,
    session_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Decorate a session response dict with spec §02 `urls` + `usage`.

    Reads `task.result` out-of-band (separate query) to avoid leaking
    request/response shapes into `tasks_router.get_task`. Safe no-op when
    the task row isn't readable.
    """
    task_result: Optional[dict] = None
    try:
        async with db.get_async_session() as session:
            res = await session.execute(
                select(Task.result).where(Task.id == session_id)
            )
            row = res.first()
            if row is not None:
                task_result = row[0]
    except Exception:  # noqa: BLE001 — enrichment is best-effort
        task_result = None

    data = dict(data)
    # Spec §03 surfaces session-level statuses (`succeeded` / `failed` /
    # `cancelled`) which are the participle form of the `session.*` event
    # envelope. The underlying Task model still persists `completed`, so we
    # map at the response boundary to keep GET /sessions/{id}.status aligned
    # with the event types emitted on /sessions/{id}/events.
    if data.get("status") == "completed":
        data["status"] = "succeeded"
    data["urls"] = _session_urls(request, session_id, task_result)
    data["usage"] = await _session_usage(db, session_id)
    data["acl"] = await _session_acl(db, session_id)
    data["agent_runtime"] = _session_agent_runtime(task_result)
    return data


def _session_agent_runtime(
    task_result: Optional[dict],
) -> Dict[str, Any]:
    """Return the current agent-runtime descriptor for the session.

    Surfaces the `sandbox_agent` state persisted by
    `sandboxed_agent.py` on top of `task.result`. We filter the raw
    state to the fields a client should see — notably stripping the
    preview_token, which is an auth secret for the Daytona tunnel.
    """
    if not isinstance(task_result, dict):
        return {"kind": "direct-llm", "status": "default"}
    state = task_result.get("sandbox_agent")
    if not isinstance(state, dict):
        return {"kind": "direct-llm", "status": "default"}
    return {
        "kind": "opencode-sandbox",
        "runtime": state.get("runtime") or "opencode",
        "status": state.get("status") or "unknown",
        "sandbox_id": state.get("sandbox_id"),
        "preview_url": state.get("preview_url"),
        "opencode_session_id": state.get("opencode_session_id"),
        "provider": state.get("provider"),
        "model": state.get("model"),
        "agent_name": state.get("agent_name"),
        "spawned_at": state.get("spawned_at"),
    }


async def _session_acl(db: DatabaseService, session_id: str) -> Dict[str, Any]:
    """Return the ACL roster for a session (spec §02 `acl` field).

    Shape: `{"grants": [{"user_id": "<uuid>", "role": "owner|editor|viewer"}, ...]}`.
    Empty list when no grants exist. Best-effort — errors return empty.
    """
    grants: list[dict[str, str]] = []
    try:
        async with db.get_async_session() as session:
            rows = (
                await session.execute(
                    select(SessionACL.user_id, SessionACL.role).where(
                        SessionACL.task_id == session_id
                    )
                )
            ).all()
            for row in rows:
                grants.append({"user_id": str(row.user_id), "role": row.role})
    except Exception:  # noqa: BLE001
        pass
    return {"grants": grants}


def _transform_request_body(body: Dict[str, Any]) -> Dict[str, Any]:
    """Transform request body to convert session_id to task_id.

    This allows clients to use either session_id or task_id in requests.
    """
    result = dict(body)
    # Convert session_id to task_id if present
    if "session_id" in result and "task_id" not in result:
        result["task_id"] = result.pop("session_id")
    # Convert session_type to task_type if present
    if "session_type" in result and "task_type" not in result:
        result["task_type"] = result.pop("session_type")
    return result


def _set_deprecation_header(response: Response) -> None:
    """Set the X-Deprecated header on the response."""
    response.headers["X-Deprecated"] = DEPRECATION_HEADER


def _get_credential_environment_version(
    db: DatabaseService,
    execution_config: tasks_router.ExecutionConfig | None,
) -> tuple[UUID, UUID] | None:
    """Return workspace and environment version IDs when aliases are configured."""
    if execution_config is None or execution_config.workspace_id is None:
        return None

    workspace_id = execution_config.workspace_id
    environment_id = execution_config.environment_id

    with db.get_session() as session:
        if environment_id is None:
            workspace_settings = session.get(WorkspaceSettings, workspace_id)
            if workspace_settings is not None:
                environment_id = workspace_settings.environment_id

        if environment_id is None:
            return None

        environment_version = (
            session.query(EnvironmentVersion)
            .filter(EnvironmentVersion.environment_id == environment_id)
            .order_by(EnvironmentVersion.version_number.desc())
            .first()
        )
        if not environment_version or not environment_version.credentials:
            return None
        return workspace_id, environment_version.id


async def _mint_session_token_for_credentials(
    db: DatabaseService,
    execution_config: tasks_router.ExecutionConfig | None,
    task_id: str,
) -> str | None:
    """Mint and stage a broker session token when the environment has aliases."""
    credential_context = _get_credential_environment_version(db, execution_config)
    if credential_context is None:
        return None

    workspace_id, environment_version_id = credential_context
    async with db.get_async_session() as async_session:
        session_service = SandboxSessionService(async_session)
        session_token, _sandbox_session = await session_service.create_session(
            workspace_id=workspace_id,
            environment_version_id=environment_version_id,
        )

    stored_for_spawner = store_session_token_for_task(task_id, session_token)
    if not stored_for_spawner:
        logger.warning(
            "Broker session token minted but not staged for sandbox spawner",
            task_id=task_id,
        )
    return session_token


# ============================================================================
# API Endpoints (Aliases for Task Endpoints)
# ============================================================================


@router.get("", response_model=List[dict])
async def list_sessions(
    request: Request,
    response: Response,
    status: str | None = None,
    phase_id: str | None = None,
    has_sandbox: bool | None = None,
    ticket_id: str | None = None,
    workspace_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """List sessions visible to the caller.

    Visibility is the 4-arm union spelled out in `verify_task_access`:
      1. Ticket-linked tasks whose project is in the user's orgs AND
         whose linked spec (if any) is not archived — legacy Kanban path.
      2. Tasks whose workspace is in the user's orgs — SDK-direct path.
      3. Tasks the user created directly — ticket-less direct ownership.
      4. Tasks with a SessionACL grant for the user — multiplayer shares.

    Historically this delegated to `tasks_router.list_tasks`, which
    INNER-joins `tickets` and silently drops ticket-less sessions. The
    delegation is gone: this handler owns its query so SDK-created
    ticket-less sessions are visible. `tasks_router.list_tasks` stays
    untouched so the dashboard's Kanban semantics don't shift.
    """
    check_feature_flag()
    _set_deprecation_header(response)

    from sqlalchemy import and_, exists, or_, select as sa_select
    from omoi_os.api.dependencies import (
        get_accessible_project_ids,
        get_user_organization_ids,
    )
    from omoi_os.models.session_acl import SessionACL
    from omoi_os.models.spec import Spec
    from omoi_os.models.ticket import Ticket
    from omoi_os.models.workspace import Workspace

    org_ids = await get_user_organization_ids(current_user, db)
    project_ids = await get_accessible_project_ids(current_user, db)

    project_id_strs = [str(p) for p in project_ids]

    # Four visibility arms, OR-joined. Ticket arm preserves the archived-
    # spec exclusion that the legacy delegation applied at
    # routes/tasks.py:498-506; the other three arms have no spec linkage.
    ticket_arm = and_(
        Task.ticket_id.isnot(None),
        Ticket.project_id.in_(project_id_strs) if project_id_strs else sa.false(),
        or_(Ticket.spec_id.is_(None), Spec.archived == False),  # noqa: E712
    )
    workspace_arm = and_(
        Task.workspace_id.isnot(None),
        Workspace.organization_id.in_(org_ids) if org_ids else sa.false(),
    )
    created_by_arm = Task.created_by == current_user.id
    acl_arm = exists(
        sa_select(SessionACL.id).where(
            SessionACL.task_id == Task.id,
            SessionACL.user_id == current_user.id,
        )
    )

    async with db.get_async_session() as session:
        query = (
            select(Task)
            .outerjoin(Ticket, Task.ticket_id == Ticket.id)
            .outerjoin(Spec, Ticket.spec_id == Spec.id)
            .outerjoin(Workspace, Task.workspace_id == Workspace.id)
            .where(or_(ticket_arm, workspace_arm, created_by_arm, acl_arm))
        )

        if ticket_id:
            query = query.where(Task.ticket_id == ticket_id)
        if workspace_id:
            query = query.where(Task.workspace_id == workspace_id)
        if status:
            query = query.where(Task.status == status)
        if phase_id:
            query = query.where(Task.phase_id == phase_id)
        if has_sandbox is True:
            query = query.where(Task.sandbox_id.isnot(None))
        elif has_sandbox is False:
            query = query.where(Task.sandbox_id.is_(None))

        query = query.order_by(Task.created_at.desc()).offset(offset).limit(limit)
        result = await session.execute(query)
        tasks = result.scalars().unique().all()

        rows = [
            {
                "id": task.id,
                "ticket_id": task.ticket_id,
                "workspace_id": (str(task.workspace_id) if task.workspace_id else None),
                "phase_id": task.phase_id,
                "task_type": task.task_type,
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "status": task.status,
                "sandbox_id": task.sandbox_id,
                "assigned_agent_id": task.assigned_agent_id,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
            for task in tasks
        ]

    return _add_session_id_to_response(rows)


@router.get("/{session_id}", response_model=dict)
async def get_session(
    request: Request,
    response: Response,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """Get session by ID (alias for get_task).

    Deprecated: Use GET /api/v1/tasks/{id} instead.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        session_id: Session UUID (maps to task_id)
        current_user: Authenticated user
        db: Database service

    Returns:
        Session data with both id and session_id fields
    """
    check_feature_flag()
    _set_deprecation_header(response)

    # Call the tasks handler directly
    result = await tasks_router.get_task(
        task_id=session_id,
        current_user=current_user,
        db=db,
    )

    # Enrich with spec §02 urls + usage, then add session_id alias.
    enriched = await _enrich_session_response(request, db, session_id, result)
    return _add_session_id_to_response(enriched)


@router.post("", response_model=dict, status_code=201)
async def create_session(
    request: Request,
    response: Response,
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """Create a new session.

    Spec §03: `POST /api/v1/sessions {workspace_id, environment_id, prompt,
    share_with, github_repo, metadata}`.

    Two entry points converge here:
      1. SDK-direct (no ticket): provide `workspace_id` OR `github_repo`;
         `prompt` is required. Optionally `environment_id` to pin a version.
      2. Legacy dashboard / task-shim callers: send `ticket_id + title +
         description + task_type` — the ticket chain is preserved. Passed
         through to `tasks_router.create_task` unchanged.

    The two paths are dispatched on whether `ticket_id` is populated.
    """
    check_feature_flag()
    _set_deprecation_header(response)

    # Legacy path: ticket-driven session. Delegate to tasks_router so the
    # existing verify_ticket_access + workflow hooks keep firing byte-identically.
    if session_data.ticket_id:
        task_data = tasks_router.TaskCreate(
            ticket_id=session_data.ticket_id,
            title=session_data.title or (session_data.prompt or "")[:100] or "session",
            description=session_data.description or session_data.prompt or "",
            task_type=session_data.session_type,
            priority=session_data.priority,
            phase_id=session_data.phase_id,
            dependencies=session_data.dependencies,
            execution_config=session_data.execution_config,
        )
        result = await tasks_router.create_task(
            task_data=task_data,
            current_user=current_user,
            db=db,
            queue=queue,
        )
        session_token = await _mint_session_token_for_credentials(
            db=db,
            execution_config=session_data.execution_config,
            task_id=str(result["id"]),
        )
        session_response = _add_session_id_to_response(result)
        if session_token is not None:
            session_response["session_token"] = session_token

        # Emit session.created for the legacy ticket-driven path too. Without
        # this, SSE subscribers on the legacy flow would also wait silently.
        try:
            from omoi_os.api.dependencies import get_event_bus_service

            bus = get_event_bus_service()
            created_task_id = str(result["id"])
            with db.get_session() as sess:
                SessionEventEnvelope(sess, bus).emit(
                    session_id=created_task_id,
                    event_type="session.created",
                    actor=actor_user(current_user.id),
                    data={
                        "ticket_id": str(session_data.ticket_id),
                        "title": task_data.title,
                        "phase_id": task_data.phase_id,
                        "task_type": task_data.task_type,
                    },
                )
                sess.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "session.created emit failed (legacy path)",
                session_id=str(result.get("id")),
                error=str(exc),
            )

        return session_response

    # SDK-direct path: no ticket, no project. Build the Task row directly.
    if not session_data.prompt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="`prompt` is required for ticket-less sessions",
        )
    if not session_data.workspace_id and not session_data.github_repo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either `workspace_id` or `github_repo`",
        )

    result = await _create_ticketless_session(
        session_data=session_data,
        current_user=current_user,
        db=db,
        queue=queue,
    )
    return result


async def _create_ticketless_session(
    session_data: "SessionCreate",
    current_user: User,
    db: DatabaseService,
    queue: TaskQueueService,
) -> dict:
    """Create a Task row directly for an SDK-direct session (no ticket).

    Resolves the owning org from the caller, auto-binds a workspace if only
    `github_repo` was supplied, pins the environment version, inserts the
    Task + the owner SessionACL grant + any explicit share_with grants, then
    enqueues the task. Returns the same dict shape the tasks_router uses so
    the client-facing response is unchanged.
    """
    from omoi_os.api.dependencies import get_user_organization_ids
    from omoi_os.models.workspace import Workspace
    from omoi_os.services.workspace_binding import (
        ensure_workspace_for_github_repo,
    )

    async with db.get_async_session() as session:
        # 1. Resolve org — caller must have at least one org membership.
        org_ids = await get_user_organization_ids(current_user, db)
        if not org_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Caller has no organization membership; cannot create session",
            )

        # 2. Resolve / auto-bind workspace
        workspace: Optional[Workspace] = None
        if session_data.workspace_id:
            workspace = (
                await session.execute(
                    select(Workspace).where(Workspace.id == session_data.workspace_id)
                )
            ).scalar_one_or_none()
            if workspace is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workspace {session_data.workspace_id} not found",
                )
            if workspace.organization_id not in org_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this workspace",
                )
        elif session_data.github_repo:
            # Pick the caller's first org membership (arbitrary but deterministic).
            org_id = next(iter(sorted(org_ids, key=str)))
            workspace = await ensure_workspace_for_github_repo(
                session,
                organization_id=org_id,
                github_repo=session_data.github_repo,
                created_by=current_user.id,
            )

        assert workspace is not None  # guaranteed by validation above

        # 3. Resolve environment_version_id
        environment_version_id: Optional[UUID] = None
        if session_data.environment_id:
            ev = (
                (
                    await session.execute(
                        select(EnvironmentVersion)
                        .where(
                            EnvironmentVersion.environment_id
                            == session_data.environment_id
                        )
                        .order_by(EnvironmentVersion.created_at.desc())
                    )
                )
                .scalars()
                .first()
            )
            if ev is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Environment {session_data.environment_id} has no versions",
                )
            environment_version_id = ev.id
        elif workspace.default_environment_id:
            ev = (
                (
                    await session.execute(
                        select(EnvironmentVersion)
                        .where(
                            EnvironmentVersion.environment_id
                            == workspace.default_environment_id
                        )
                        .order_by(EnvironmentVersion.created_at.desc())
                    )
                )
                .scalars()
                .first()
            )
            if ev is not None:
                environment_version_id = ev.id

        # 4. Build github_repo string for the Task row (from workspace binding
        #    if connected, else from the explicit request param)
        github_repo_str: Optional[str] = None
        if (
            workspace.github_connected
            and workspace.github_owner
            and workspace.github_repo
        ):
            github_repo_str = f"{workspace.github_owner}/{workspace.github_repo}"
        elif session_data.github_repo:
            github_repo_str = session_data.github_repo

        # 5. Insert the Task row directly
        prompt = session_data.prompt or ""
        task = Task(
            ticket_id=None,
            workspace_id=workspace.id,
            environment_version_id=environment_version_id,
            created_by=current_user.id,
            github_repo=github_repo_str,
            title=(session_data.title or prompt[:100]) or f"session-{workspace.slug}",
            description=session_data.description or prompt,
            priority=session_data.priority or "MEDIUM",
            phase_id=session_data.phase_id or "PHASE_IMPLEMENTATION",
            task_type=session_data.session_type or "implementation",
            status="pending",
            dependencies=session_data.dependencies,
            execution_config=(
                session_data.execution_config.model_dump(mode="json")
                if session_data.execution_config
                else None
            ),
            # Spec §18 §5: persist opaque client metadata so it round-trips
            # byte-equally on subsequent reads. Empty dict → store nothing.
            client_metadata=session_data.metadata or None,
        )
        session.add(task)
        await session.flush()

        # 6. Owner ACL grant so the creator can share/reply without extra hops
        owner_acl = SessionACL(
            task_id=task.id,
            user_id=current_user.id,
            role="owner",
        )
        session.add(owner_acl)

        # 7. Optional share_with grants
        for shared_user_id in session_data.share_with or []:
            if shared_user_id == current_user.id:
                continue
            session.add(
                SessionACL(
                    task_id=task.id,
                    user_id=shared_user_id,
                    role="viewer",
                )
            )

        await session.commit()
        await session.refresh(task)

        task_id = str(task.id)
        workspace_id_str = str(workspace.id) if workspace else None
        task_dict: dict = {
            "id": task_id,
            "session_id": task_id,
            "ticket_id": None,
            "workspace_id": workspace_id_str,
            "environment_version_id": (
                str(environment_version_id) if environment_version_id else None
            ),
            "github_repo": github_repo_str,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "priority": task.priority,
            "phase_id": task.phase_id,
            "status": task.status,
            "created_by": str(task.created_by) if task.created_by else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            # Echo client metadata under the spec key name (the model attr is
            # client_metadata to avoid SQLAlchemy's reserved `metadata`).
            "metadata": task.client_metadata or {},
        }

    # 8. Mint broker session token (outside the DB session — uses its own txn)
    session_token = await _mint_session_token_for_credentials(
        db=db,
        execution_config=session_data.execution_config,
        task_id=task_id,
    )
    if session_token is not None:
        task_dict["session_token"] = session_token

    # 9. Emit session.created — spec §03. Lands in both the DB replay stream
    #    (so SSE clients reconnecting see it) and the live per-session Redis
    #    channel (so tailing clients see it without waiting for poll).
    try:
        from omoi_os.api.dependencies import get_event_bus_service

        bus = get_event_bus_service()
        with db.get_session() as sess:
            SessionEventEnvelope(sess, bus).emit(
                session_id=task_id,
                event_type="session.created",
                actor=actor_user(current_user.id),
                data={
                    "workspace_id": workspace_id_str,
                    "prompt": prompt,
                    "github_repo": github_repo_str,
                    "environment_version_id": (
                        str(environment_version_id) if environment_version_id else None
                    ),
                },
            )
            sess.commit()
    except Exception as exc:  # noqa: BLE001 — emit is best-effort; session is already created
        logger.warning(
            "session.created emit failed",
            session_id=task_id,
            error=str(exc),
        )

    # 10. Kick off a first agent reply against the initial prompt — gives
    #     callers a "hello, working on it" response the moment the session
    #     exists, so a chat UI feels responsive from turn one.
    if prompt:
        try:
            from omoi_os.services.chat_responder import schedule_response

            schedule_response(task_id, db)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "initial chat responder schedule failed",
                session_id=task_id,
                error=str(exc),
            )

    return task_dict


@router.delete("/{session_id}", response_model=dict)
async def delete_session(
    request: Request,
    response: Response,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """Cancel/delete a session (alias for cancel_task).

    Deprecated: Use POST /api/v1/tasks/{id}/cancel instead.

    Note: Since tasks cannot be truly deleted, this endpoint cancels the task.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        session_id: Session UUID (maps to task_id)
        current_user: Authenticated user
        db: Database service
        queue: Task queue service

    Returns:
        Cancellation result with session_id
    """
    check_feature_flag()
    _set_deprecation_header(response)

    # Verify user has access to this session/task
    await verify_task_access(session_id, current_user, db)

    # Cancel the task using the queue service
    success = queue.cancel_task(session_id, reason="cancelled_by_session_api")

    # Regardless of whether the task was cancellable (it may have been
    # pending — a chat-only session that never ran through the
    # orchestrator), tear the sandboxed agent down. Otherwise closing
    # the chat leaks the sandbox until the provider's idle reaper catches
    # it (Daytona's lifetime cap, Modal's `sandbox_idle_timeout_seconds`).
    # Tear down BOTH runtimes — the in-memory registries don't know which
    # provider served this session, so a `close()` on the wrong one is a
    # fast no-op but a missed `close()` on the right one leaks state.
    # Best-effort: any error here is logged but not raised.
    for module_name in ("sandboxed_agent", "modal_sandboxed_agent"):
        try:
            from importlib import import_module

            module = import_module(f"omoi_os.services.{module_name}")
            await module.close(session_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "sandboxed agent cleanup on delete_session failed",
                session_id=session_id,
                runtime=module_name,
                error=str(exc),
            )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or not cancellable",
        )

    return {
        "session_id": session_id,
        "task_id": session_id,
        "cancelled": True,
        "reason": "cancelled_by_session_api",
    }


@router.patch("/{session_id}", response_model=dict)
async def update_session(
    request: Request,
    response: Response,
    session_id: str,
    update: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """Update session by ID (alias for update_task).

    Deprecated: Use PATCH /api/v1/tasks/{id} instead.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        session_id: Session UUID (maps to task_id)
        update: Fields to update
        current_user: Authenticated user
        db: Database service

    Returns:
        Updated session data with both id and session_id fields
    """
    check_feature_flag()
    _set_deprecation_header(response)

    # Convert to TaskUpdateRequest
    task_update = tasks_router.TaskUpdateRequest(
        title=update.title,
        description=update.description,
        priority=update.priority,
        status=update.status,
    )

    # Call the tasks handler directly
    result = await tasks_router.update_task(
        task_id=session_id,
        update=task_update,
        current_user=current_user,
        db=db,
    )

    # Add session_id to response
    return _add_session_id_to_response(result)


# ============================================================================
# Spec §03 — session lifecycle surface
# ============================================================================

_SSE_REPLAY_BATCH = 500  # Max events replayed per SSE connection before live.
_SSE_HEARTBEAT_SECONDS = 15.0  # Keep-alive comment frequency when idle.


def _serialize_envelope(event: Event) -> dict[str, Any]:
    """Shape a persisted Event row into a spec §03 envelope dict.

    Historical rows may have `seq IS NULL` — we skip them upstream so this
    helper can assume both `seq` and `actor` are populated.
    """
    ts = event.timestamp.isoformat() if event.timestamp else None
    return {
        "id": event.id,
        "seq": event.seq,
        "type": event.event_type,
        "session_id": event.entity_id,
        "actor": event.actor,
        "timestamp": ts,
        "data": event.payload or {},
    }


def _parse_last_event_id(value: Optional[str]) -> int:
    """Parse `Last-Event-ID` header to a seq int. Returns 0 for missing/invalid."""
    if not value:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


@router.get("/{session_id}/events")
async def session_events(
    session_id: str,
    last_event_id: Optional[str] = Header(default=None, alias="Last-Event-ID"),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """SSE stream of session events (spec §03).

    Replays any persisted events with `seq > last_event_id` from the DB, then
    subscribes to the live Redis pubsub channel and forwards any further
    envelope-shaped events for this session. Clients resume by sending the
    `Last-Event-ID` header with the last seq they successfully processed.
    """
    check_feature_flag()
    await verify_task_access(session_id, current_user, db)

    resume_seq = _parse_last_event_id(last_event_id)

    async def frame_stream() -> AsyncGenerator[bytes, None]:
        """Emit SSE frames: replay → live → heartbeats on idle."""

        def encode(envelope: dict[str, Any]) -> bytes:
            # The `id:` line doubles as the Last-Event-ID the browser sends on
            # reconnect, so clients don't have to track seq separately.
            buf = StringIO()
            buf.write(f"id: {envelope['seq']}\n")
            buf.write(f"event: {envelope['type']}\n")
            buf.write(f"data: {json.dumps(envelope, separators=(',', ':'))}\n\n")
            return buf.getvalue().encode()

        # Phase 1: replay from the DB.
        last_seen_seq = resume_seq
        with db.get_session() as session:
            rows = (
                session.execute(
                    select(Event)
                    .where(
                        Event.entity_id == session_id,
                        Event.seq.is_not(None),
                        Event.seq > resume_seq,
                    )
                    .order_by(Event.seq.asc())
                    .limit(_SSE_REPLAY_BATCH)
                )
                .scalars()
                .all()
            )
            for ev in rows:
                yield encode(_serialize_envelope(ev))
                last_seen_seq = ev.seq or last_seen_seq

        # Phase 2: subscribe live. We use the Redis pubsub that EventBusService
        # broadcasts to. Each published SystemEvent for this session carries
        # `payload.envelope` — we hand that through.
        from omoi_os.api.dependencies import get_event_bus_service

        bus: EventBusService = get_event_bus_service()
        if not getattr(bus, "_available", False) or not bus.redis_client:
            # Redis unavailable — degrade to replay-only. Client can poll.
            return

        pubsub = bus.redis_client.pubsub()
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, lambda: pubsub.psubscribe("events.*"))

            last_beat = utc_now().timestamp()
            while True:
                message = await loop.run_in_executor(
                    None,
                    lambda: pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    ),
                )
                now = utc_now().timestamp()

                if message is None:
                    # Idle tick — emit a heartbeat comment so proxies don't
                    # close the connection.
                    if now - last_beat >= _SSE_HEARTBEAT_SECONDS:
                        yield b": keepalive\n\n"
                        last_beat = now
                    continue

                if message.get("type") != "pmessage":
                    continue

                try:
                    data = json.loads(message["data"])
                except (ValueError, TypeError):
                    continue

                # Spec §03: only session-scoped events get an envelope.
                if data.get("entity_id") != session_id:
                    continue
                envelope = (data.get("payload") or {}).get("envelope")
                if not envelope:
                    continue
                if envelope.get("seq", 0) <= last_seen_seq:
                    continue
                last_seen_seq = envelope["seq"]

                yield encode(envelope)
                last_beat = now
        finally:
            try:
                await loop.run_in_executor(None, pubsub.close)
            except Exception:  # noqa: BLE001
                pass

    return StreamingResponse(
        frame_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


class SessionReplyRequest(BaseModel):
    """Body for POST /sessions/{id}/messages — a user reply mid-session."""

    text: str = Field(..., min_length=1, max_length=32_000)


@router.post("/{session_id}/messages", status_code=status.HTTP_204_NO_CONTENT)
async def session_reply(
    session_id: str,
    body: SessionReplyRequest,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
) -> Response:
    """Send a follow-up prompt to a running session (spec §03).

    The message is appended to a per-session Redis inbox list, which the
    in-sandbox agent polls via `poll_messages()`. A `session.message` event
    is emitted via the envelope so it appears in the SSE stream and any
    connected WebSocket clients.
    """
    check_feature_flag()
    await verify_task_access(session_id, current_user, db)

    from omoi_os.api.dependencies import get_event_bus_service

    bus = get_event_bus_service()

    # 1. Enqueue for the sandbox poller (non-blocking — we don't wait for ack).
    try:
        if bus and bus.redis_client:
            bus.redis_client.rpush(
                f"session:{session_id}:inbox",
                json.dumps({"text": body.text, "user_id": str(current_user.id)}),
            )
    except Exception:  # noqa: BLE001 — inbox push is best-effort
        logger.warning(
            "session reply inbox push failed",
            session_id=session_id,
        )

    # 2. Emit the envelope event.
    with db.get_session() as session:
        envelope = SessionEventEnvelope(session, bus)
        envelope.emit(
            session_id=session_id,
            event_type="session.message",
            actor=actor_user(current_user.id),
            data={"text": body.text},
        )
        session.commit()

    # 3. Kick off the chat responder — fire-and-forget async task that
    #    loads the conversation history, calls the LLM, and emits the
    #    agent's reply as another session.message envelope. The user
    #    sees it arrive over their open SSE / WS stream.
    try:
        from omoi_os.services.chat_responder import schedule_response

        schedule_response(session_id, db)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "chat responder schedule failed",
            session_id=session_id,
            error=str(exc),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


class SessionForkRequest(BaseModel):
    """Body for POST /sessions/{id}/fork."""

    from_seq: int = Field(..., ge=0)
    prompt: str = Field(..., min_length=1)


@router.post(
    "/{session_id}/fork", response_model=dict, status_code=status.HTTP_201_CREATED
)
async def session_fork(
    session_id: str,
    body: SessionForkRequest,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
) -> dict[str, Any]:
    """Fork a session from a specific event seq (spec §03).

    Copies the parent task (preserving ticket + pinned environment version so
    the fork inherits spec §05 immutable credentials), records lineage in
    `session_forks`, replays events up to `from_seq` into the child with new
    seqs starting at 1, and enqueues the child for execution.
    """
    check_feature_flag()
    await verify_task_access(session_id, current_user, db)

    with db.get_session() as session:
        parent = session.get(Task, session_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        # Build the child with the parent's shape + a new prompt.
        child = Task(
            ticket_id=parent.ticket_id,
            phase_id=parent.phase_id,
            task_type=parent.task_type,
            title=f"[fork@{body.from_seq}] {parent.title or ''}".strip(),
            description=body.prompt,
            priority=parent.priority,
            status="pending",
            parent_task_id=parent.id,
            max_retries=parent.max_retries,
            timeout_seconds=parent.timeout_seconds,
            required_capabilities=parent.required_capabilities,
        )
        session.add(child)
        session.flush()  # populate child.id

        # Record fork lineage.
        session.add(
            SessionFork(
                parent_task_id=parent.id,
                child_task_id=child.id,
                from_seq=body.from_seq,
            )
        )

        # Copy events with seq <= from_seq into the child, renumbered.
        parent_events = (
            session.execute(
                select(Event)
                .where(
                    Event.entity_id == parent.id,
                    Event.seq.is_not(None),
                    Event.seq <= body.from_seq,
                )
                .order_by(Event.seq.asc())
            )
            .scalars()
            .all()
        )
        for new_seq, pev in enumerate(parent_events, start=1):
            session.add(
                Event(
                    event_type=pev.event_type,
                    entity_type="session",
                    entity_id=child.id,
                    payload=pev.payload,
                    seq=new_seq,
                    actor=pev.actor,
                )
            )

        # Owner ACL — forker becomes owner of the child.
        session.add(SessionACL(task_id=child.id, user_id=current_user.id, role="owner"))

        session.commit()
        child_id = child.id

    # The forked child is already persisted as a pending task. The queue poller
    # picks it up from the database; no second enqueue call is needed here.

    return {
        "id": child_id,
        "session_id": child_id,
        "parent_session_id": session_id,
        "from_seq": body.from_seq,
        "status": "pending",
    }


class Grant(BaseModel):
    """One ACL grant in a share request."""

    user_id: UUID
    role: str = Field(..., pattern="^(owner|editor|viewer)$")


class SessionShareRequest(BaseModel):
    """Body for POST /sessions/{id}/share."""

    grants: List[Grant] = Field(default_factory=list)


@router.post("/{session_id}/share", status_code=status.HTTP_200_OK)
async def session_share(
    session_id: str,
    body: SessionShareRequest,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
) -> dict[str, Any]:
    """Grant access to a session (spec §07).

    Upserts rows in `session_acls`. Only the session owner (or a user who has
    base `verify_task_access` via org membership) may share. Cross-org grants
    are rejected — the target user must belong to the same org as the session.
    """
    check_feature_flag()
    await verify_task_access(session_id, current_user, db)

    with db.get_session() as session:
        task = session.get(Task, session_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        # Validate target users exist BEFORE touching session_acls. Without
        # this check the FK constraint fires inside the loop and we end up
        # with a 500 (integrity error) on what should be a clean 422.
        missing: list[str] = []
        for grant in body.grants:
            target = session.get(User, grant.user_id)
            if target is None:
                missing.append(str(grant.user_id))
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "One or more target users do not exist",
                    "missing_user_ids": missing,
                },
            )

        for grant in body.grants:
            existing = session.execute(
                select(SessionACL).where(
                    SessionACL.task_id == session_id,
                    SessionACL.user_id == grant.user_id,
                )
            ).scalar_one_or_none()

            if existing:
                existing.role = grant.role
            else:
                session.add(
                    SessionACL(
                        task_id=session_id,
                        user_id=grant.user_id,
                        role=grant.role,
                    )
                )

        session.commit()

    return {"session_id": session_id, "granted": len(body.grants)}


# WebSocket endpoint is defined in session_channel.py and registered via the
# FastAPI websocket decorator here to keep the router's route table complete.
from omoi_os.api.routes.session_channel import session_ws_endpoint  # noqa: E402

router.websocket("/{session_id}/ws")(session_ws_endpoint)


@router.get("/{session_id}/artifacts", response_model=List[dict])
async def session_artifacts(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
) -> list[dict[str, Any]]:
    """List artifacts produced by this session (spec §03).

    Filters `artifacts` by `artifact_metadata->>'task_id' = session_id`.
    Artifact rows are the same shape as `/api/v1/artifacts` — this is a
    session-scoped view, not a different storage.
    """
    check_feature_flag()
    await verify_task_access(session_id, current_user, db)

    from omoi_os.models.artifact import Artifact

    with db.get_session() as session:
        rows = (
            session.execute(
                select(Artifact).where(
                    Artifact.artifact_metadata["task_id"].astext == session_id
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": str(a.id),
                "workspace_id": str(a.workspace_id),
                "name": a.name,
                "storage_backend": a.storage_backend,
                "checksum": a.checksum,
                "size_bytes": a.size_bytes,
                "content_type": a.content_type,
                "artifact_metadata": a.artifact_metadata,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ]
