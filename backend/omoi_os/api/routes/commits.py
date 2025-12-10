"""Commits API routes for tracking and viewing code changes."""

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from omoi_os.api.dependencies import get_db_service, get_event_bus_service
from omoi_os.models.ticket import Ticket
from omoi_os.ticketing.models import TicketCommit
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.utils.datetime import utc_now

router = APIRouter()


class CommitResponse(BaseModel):
    """Response model for commit details."""

    id: str
    commit_sha: str
    commit_message: str
    commit_timestamp: str
    agent_id: str
    ticket_id: str
    files_changed: Optional[int] = None
    insertions: Optional[int] = None
    deletions: Optional[int] = None
    files_list: Optional[dict] = None
    linked_at: str
    link_method: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CommitListResponse(BaseModel):
    """Response model for commit list."""

    commits: list[CommitResponse]
    total: int


class LinkCommitRequest(BaseModel):
    """Request model for linking a commit to a ticket."""

    commit_sha: str
    agent_id: str
    commit_message: Optional[str] = None
    files_changed: Optional[int] = None
    insertions: Optional[int] = None
    deletions: Optional[int] = None
    files_list: Optional[dict] = None
    link_method: Optional[str] = "manual"


class FileDiff(BaseModel):
    """Model for file diff."""

    path: str
    additions: int
    deletions: int
    changes: int
    status: str  # added, modified, removed
    patch: Optional[str] = None


class CommitDiffResponse(BaseModel):
    """Response model for commit diff."""

    commit_sha: str
    files: list[FileDiff]


@router.get("/{commit_sha}", response_model=CommitResponse)
async def get_commit(
    commit_sha: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get commit details by SHA.

    Args:
        commit_sha: Full or short commit SHA
        db: Database service

    Returns:
        Commit details
    """
    with db.get_session() as session:
        # Try full SHA first, then short SHA
        commit = (
            session.query(TicketCommit)
            .filter(TicketCommit.commit_sha == commit_sha)
            .first()
        )

        if not commit:
            # Try prefix match for short SHA
            commit = (
                session.query(TicketCommit)
                .filter(TicketCommit.commit_sha.startswith(commit_sha))
                .first()
            )

        if not commit:
            raise HTTPException(status_code=404, detail="Commit not found")

        return CommitResponse.model_validate(commit)


@router.get("/ticket/{ticket_id}", response_model=CommitListResponse)
async def get_ticket_commits(
    ticket_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get all commits linked to a ticket.

    Args:
        ticket_id: Ticket ID
        limit: Maximum number of commits to return
        offset: Number of commits to skip
        db: Database service

    Returns:
        List of commits for the ticket
    """
    with db.get_session() as session:
        # Verify ticket exists
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Get commits
        commits = (
            session.query(TicketCommit)
            .filter(TicketCommit.ticket_id == ticket_id)
            .order_by(TicketCommit.commit_timestamp.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        total = (
            session.query(TicketCommit)
            .filter(TicketCommit.ticket_id == ticket_id)
            .count()
        )

        return CommitListResponse(
            commits=[CommitResponse.model_validate(c) for c in commits],
            total=total,
        )


@router.get("/agent/{agent_id}", response_model=CommitListResponse)
async def get_agent_commits(
    agent_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get all commits made by an agent.

    Args:
        agent_id: Agent ID
        limit: Maximum number of commits to return
        offset: Number of commits to skip
        db: Database service

    Returns:
        List of commits by the agent
    """
    with db.get_session() as session:
        commits = (
            session.query(TicketCommit)
            .filter(TicketCommit.agent_id == agent_id)
            .order_by(TicketCommit.commit_timestamp.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        total = (
            session.query(TicketCommit)
            .filter(TicketCommit.agent_id == agent_id)
            .count()
        )

        return CommitListResponse(
            commits=[CommitResponse.model_validate(c) for c in commits],
            total=total,
        )


@router.post("/ticket/{ticket_id}/link", response_model=CommitResponse)
async def link_commit_to_ticket(
    ticket_id: str,
    request: LinkCommitRequest,
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Manually link a commit to a ticket.

    Args:
        ticket_id: Ticket ID
        request: Commit linking data
        db: Database service
        event_bus: Event bus service

    Returns:
        Linked commit details
    """
    with db.get_session() as session:
        # Verify ticket exists
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Check if commit already linked
        existing = (
            session.query(TicketCommit)
            .filter(
                TicketCommit.ticket_id == ticket_id,
                TicketCommit.commit_sha == request.commit_sha,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409, detail="Commit already linked to this ticket"
            )

        # Create commit record
        commit = TicketCommit(
            id=f"commit-{uuid4()}",
            ticket_id=ticket_id,
            agent_id=request.agent_id,
            commit_sha=request.commit_sha,
            commit_message=request.commit_message or "",
            commit_timestamp=utc_now(),
            files_changed=request.files_changed,
            insertions=request.insertions,
            deletions=request.deletions,
            files_list=request.files_list,
            link_method=request.link_method,
        )

        session.add(commit)
        session.commit()

        # Emit event
        from omoi_os.services.event_bus import SystemEvent

        event_bus.publish(
            SystemEvent(
                event_type="COMMIT_LINKED",
                entity_type="commit",
                entity_id=commit.id,
                payload={
                    "commit_sha": commit.commit_sha,
                    "ticket_id": ticket_id,
                    "agent_id": request.agent_id,
                },
            )
        )

        return CommitResponse.model_validate(commit)


@router.get("/{commit_sha}/diff", response_model=CommitDiffResponse)
async def get_commit_diff(
    commit_sha: str,
    file_path: Optional[str] = Query(
        None, description="Specific file path to get diff for"
    ),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get commit diff (file-by-file changes).

    Note: This endpoint currently returns metadata from the database.
    For full diff content, GitHub Integration API should be used to fetch from GitHub.

    Args:
        commit_sha: Full or short commit SHA
        file_path: Optional specific file path
        db: Database service

    Returns:
        Commit diff with file changes
    """
    with db.get_session() as session:
        # Find commit
        commit = (
            session.query(TicketCommit)
            .filter(TicketCommit.commit_sha == commit_sha)
            .first()
        )

        if not commit:
            commit = (
                session.query(TicketCommit)
                .filter(TicketCommit.commit_sha.startswith(commit_sha))
                .first()
            )

        if not commit:
            raise HTTPException(status_code=404, detail="Commit not found")

        # Build file list from files_list JSONB field
        files = []
        if commit.files_list:
            for path, file_data in commit.files_list.items():
                if file_path and path != file_path:
                    continue

                files.append(
                    FileDiff(
                        path=path,
                        additions=file_data.get("additions", 0),
                        deletions=file_data.get("deletions", 0),
                        changes=file_data.get("additions", 0)
                        + file_data.get("deletions", 0),
                        status=file_data.get("status", "modified"),
                        patch=file_data.get("patch"),
                    )
                )

        return CommitDiffResponse(commit_sha=commit.commit_sha, files=files)
