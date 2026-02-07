"""
Scaffolding tasks for triggering spec-driven workflows after project creation.

This module provides background tasks for:
- Generating specs from feature descriptions
- Creating tickets and tasks from specs
- Triggering sandbox execution for implementation

Usage:
    from fastapi import BackgroundTasks
    from omoi_os.tasks.scaffolding import trigger_scaffolding

    # In your route:
    background_tasks.add_task(
        trigger_scaffolding,
        project_id=str(project.id),
        feature_description="User auth with OAuth2",
        user_id=str(current_user.id),
    )
"""

from typing import Optional

from omoi_os.logging import get_logger

logger = get_logger(__name__)


async def trigger_scaffolding(
    project_id: str,
    feature_description: str,
    user_id: str,
) -> dict:
    """
    Trigger scaffolding workflow for a newly created project.

    This is the main entry point called as a background task after
    repository creation. It:
    1. Creates a new Spec from the feature description
    2. Runs the spec through the state machine (EXPLORE -> TASKS -> SYNC)
    3. Creates tickets and tasks for execution

    Args:
        project_id: ID of the project to scaffold
        feature_description: Feature description provided by user
        user_id: ID of the user who created the project

    Returns:
        Dict with scaffolding result including spec_id and status
    """
    from omoi_os.api.dependencies import get_database_service
    from omoi_os.services.event_bus import get_event_bus, SystemEvent

    logger.info(
        "Starting scaffolding workflow",
        project_id=project_id,
        feature_description_length=len(feature_description),
        user_id=user_id,
    )

    event_bus = None
    try:
        db = get_database_service()
        event_bus = get_event_bus()
        # Step 1: Create a new Spec for this feature
        spec_id = await _create_spec_from_description(
            db=db,
            project_id=project_id,
            feature_description=feature_description,
            user_id=user_id,
        )

        if not spec_id:
            logger.error(
                "Failed to create spec for scaffolding",
                project_id=project_id,
            )
            return {
                "success": False,
                "error": "Failed to create spec",
                "project_id": project_id,
            }

        # Step 2: Publish event that scaffolding started
        if event_bus:
            event_bus.publish(
                SystemEvent(
                    event_type="SCAFFOLDING_STARTED",
                    entity_type="project",
                    entity_id=project_id,
                    payload={
                        "project_id": project_id,
                        "spec_id": spec_id,
                        "feature_description": feature_description[
                            :200
                        ],  # Truncate for event
                        "user_id": user_id,
                    },
                )
            )

        # Step 3: Run the spec state machine to generate requirements, design, tasks
        success = await _run_spec_state_machine(
            db=db,
            spec_id=spec_id,
            project_id=project_id,
        )

        # Step 4: Publish completion event
        if event_bus:
            event_bus.publish(
                SystemEvent(
                    event_type=(
                        "SCAFFOLDING_COMPLETED" if success else "SCAFFOLDING_FAILED"
                    ),
                    entity_type="project",
                    entity_id=project_id,
                    payload={
                        "project_id": project_id,
                        "spec_id": spec_id,
                        "success": success,
                    },
                )
            )

        logger.info(
            "Scaffolding workflow completed",
            project_id=project_id,
            spec_id=spec_id,
            success=success,
        )

        return {
            "success": success,
            "project_id": project_id,
            "spec_id": spec_id,
        }

    except Exception as e:
        logger.exception(
            "Scaffolding workflow failed with exception",
            project_id=project_id,
            error=str(e),
        )

        # Publish error event
        if event_bus:
            event_bus.publish(
                SystemEvent(
                    event_type="SCAFFOLDING_FAILED",
                    entity_type="project",
                    entity_id=project_id,
                    payload={
                        "project_id": project_id,
                        "error": str(e),
                    },
                )
            )

        return {
            "success": False,
            "error": str(e),
            "project_id": project_id,
        }


async def _create_spec_from_description(
    db,
    project_id: str,
    feature_description: str,
    user_id: str,
) -> Optional[str]:
    """
    Create a new Spec from a feature description.

    Args:
        db: Database service
        project_id: Project ID to create spec under
        feature_description: Feature description from user
        user_id: User ID for ownership

    Returns:
        Spec ID if created, None if failed
    """
    from omoi_os.models.spec import Spec
    from omoi_os.models.project import Project
    from sqlalchemy import select
    from uuid import UUID as PythonUUID

    try:
        async with db.get_async_session() as session:
            # Verify project exists
            result = await session.execute(
                select(Project).filter(Project.id == project_id)
            )
            project = result.scalar_one_or_none()

            if not project:
                logger.error(
                    "Project not found for scaffolding",
                    project_id=project_id,
                )
                return None

            # Generate a title from the feature description
            title = _generate_title_from_description(feature_description)

            # Create the spec
            spec = Spec(
                project_id=project_id,
                user_id=PythonUUID(user_id),
                title=title,
                description=feature_description,
                status="processing",
                phase="Requirements",
                current_phase="explore",  # Start at explore phase
                spec_context={
                    "source": "scaffolding",
                    "auto_generated": True,
                    "original_description": feature_description,
                },
            )

            session.add(spec)
            await session.commit()
            await session.refresh(spec)

            logger.info(
                "Created spec for scaffolding",
                spec_id=spec.id,
                project_id=project_id,
                title=title,
            )

            return spec.id

    except Exception as e:
        logger.exception(
            "Failed to create spec from description",
            project_id=project_id,
            error=str(e),
        )
        return None


def _generate_title_from_description(description: str) -> str:
    """
    Generate a concise title from a feature description.

    Args:
        description: Feature description text

    Returns:
        A concise title (max 100 chars)
    """
    # Take the first sentence or first 100 chars
    first_sentence = description.split(".")[0].strip()

    if len(first_sentence) <= 100:
        return first_sentence

    # Truncate at word boundary
    truncated = first_sentence[:97]
    last_space = truncated.rfind(" ")
    if last_space > 50:
        truncated = truncated[:last_space]

    return truncated + "..."


async def _run_spec_state_machine(
    db,
    spec_id: str,
    project_id: str,
) -> bool:
    """
    Run the spec through the state machine to generate requirements, design, and tasks.

    This runs the SpecStateMachine which orchestrates the multi-phase workflow:
    EXPLORE -> REQUIREMENTS -> DESIGN -> TASKS -> SYNC

    Args:
        db: Database service
        spec_id: Spec ID to process
        project_id: Project ID for context

    Returns:
        True if state machine completed successfully, False otherwise
    """
    from omoi_os.models.project import Project
    from sqlalchemy import select

    try:
        # Get project's working directory (repo path) if available
        working_directory = "/workspace"  # Default

        async with db.get_async_session() as session:
            result = await session.execute(
                select(Project).filter(Project.id == project_id)
            )
            project = result.scalar_one_or_none()

            if project and project.github_owner and project.github_repo:
                # Could be cloned to a specific path
                working_directory = f"/workspace/{project.github_repo}"

        # Import here to avoid circular imports
        from omoi_os.workers.spec_state_machine import SpecStateMachine

        # Create and run the state machine
        machine = SpecStateMachine(
            spec_id=spec_id,
            db_session=db,
            working_directory=working_directory,
            max_retries=2,  # Fewer retries for scaffolding
        )

        # Run the state machine
        success = await machine.run()

        logger.info(
            "Spec state machine completed",
            spec_id=spec_id,
            success=success,
        )

        return success

    except Exception as e:
        logger.exception(
            "Spec state machine failed",
            spec_id=spec_id,
            error=str(e),
        )
        return False


async def trigger_scaffolding_for_ticket(
    ticket_id: str,
    project_id: str,
    user_id: str,
) -> dict:
    """
    Trigger scaffolding workflow from an existing ticket.

    This is an alternative entry point when scaffolding is triggered
    from a ticket's description instead of during repo creation.

    Args:
        ticket_id: Source ticket ID
        project_id: Project ID
        user_id: User ID for ownership

    Returns:
        Dict with scaffolding result
    """
    from omoi_os.api.dependencies import get_database_service
    from omoi_os.models.ticket import Ticket
    from sqlalchemy import select

    db = get_database_service()

    # Get the ticket's description as feature description
    async with db.get_async_session() as session:
        result = await session.execute(select(Ticket).filter(Ticket.id == ticket_id))
        ticket = result.scalar_one_or_none()

        if not ticket:
            return {
                "success": False,
                "error": "Ticket not found",
                "ticket_id": ticket_id,
            }

        feature_description = f"{ticket.title}\n\n{ticket.description or ''}"

    # Delegate to main scaffolding function
    result = await trigger_scaffolding(
        project_id=project_id,
        feature_description=feature_description,
        user_id=user_id,
    )

    # Add ticket context to result
    result["source_ticket_id"] = ticket_id
    return result
