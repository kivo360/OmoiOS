"""Task deduplication service using pgvector embeddings.

This service provides semantic similarity checking for tasks to prevent
runaway spawning of duplicate diagnostic/discovery tasks. It uses
embeddings to detect semantically similar tasks even if they have
different wording.
"""

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import text, select
from sqlalchemy.orm import Session

from omoi_os.logging import get_logger
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.embedding import EmbeddingService

logger = get_logger(__name__)

# Default similarity threshold - tasks above this are considered duplicates
DEFAULT_SIMILARITY_THRESHOLD = 0.85


@dataclass
class DuplicateTaskCandidate:
    """A potential duplicate task."""

    task_id: str
    task_type: str
    title: Optional[str]
    description: Optional[str]
    status: str
    ticket_id: str
    similarity_score: float


@dataclass
class TaskDeduplicationResult:
    """Result of duplicate check."""

    is_duplicate: bool
    candidates: List[DuplicateTaskCandidate]
    highest_similarity: float
    embedding: Optional[List[float]] = None


class TaskDeduplicationService:
    """Service for detecting duplicate tasks using embedding similarity.

    Uses pgvector's cosine distance operator to find similar tasks
    based on their embedding vectors. This is particularly useful for
    preventing runaway diagnostic task spawning.
    """

    def __init__(
        self,
        db: DatabaseService,
        embedding_service: EmbeddingService,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        """Initialize the deduplication service.

        Args:
            db: Database service for querying tasks.
            embedding_service: Service for generating embeddings.
            similarity_threshold: Minimum similarity score to consider as duplicate (0.0-1.0).
        """
        self.db = db
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold

    def check_duplicate(
        self,
        task_type: str,
        description: str,
        ticket_id: Optional[str] = None,
        title: Optional[str] = None,
        top_k: int = 5,
        threshold: Optional[float] = None,
        exclude_statuses: Optional[List[str]] = None,
        session: Optional[Session] = None,
    ) -> TaskDeduplicationResult:
        """Check if a task with similar content already exists.

        Args:
            task_type: Type of task (e.g., 'discovery_diagnostic_no_result').
            description: Task description.
            ticket_id: Optional ticket ID to scope the search.
            title: Optional task title.
            top_k: Maximum number of similar tasks to return.
            threshold: Override default similarity threshold.
            exclude_statuses: List of statuses to exclude (e.g., ['completed', 'failed']).
            session: Optional database session.

        Returns:
            TaskDeduplicationResult with duplicate status and candidates.
        """
        threshold = threshold or self.similarity_threshold
        exclude_statuses = exclude_statuses or ["completed", "failed"]

        # Generate embedding for the new task content
        content = f"{task_type}: {title or ''}\n{description}"
        embedding = self.embedding_service.generate_embedding(content)

        if not embedding:
            logger.warning("Failed to generate embedding for task deduplication check")
            return TaskDeduplicationResult(
                is_duplicate=False,
                candidates=[],
                highest_similarity=0.0,
                embedding=None,
            )

        def _check(sess: Session) -> TaskDeduplicationResult:
            # Use pgvector's cosine distance operator (<=>)
            # Cosine distance = 1 - cosine_similarity, so lower is more similar
            # We convert back to similarity score: 1 - distance

            # Build the embedding vector string for pgvector
            # Format: '[0.1,0.2,0.3,...]'
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            # Build exclude statuses for SQL IN clause
            if exclude_statuses:
                status_list = ",".join(f"'{s}'" for s in exclude_statuses)
                status_clause = f"AND status NOT IN ({status_list})"
            else:
                status_clause = ""

            # Build ticket filter if provided
            ticket_clause = ""
            if ticket_id:
                ticket_clause = f"AND ticket_id = '{ticket_id}'"

            # Build task type filter
            task_type_clause = f"AND task_type = '{task_type}'"

            # Build query with pgvector
            query = text(f"""
                SELECT
                    id,
                    task_type,
                    title,
                    description,
                    status,
                    ticket_id,
                    1 - (embedding_vector <=> '{embedding_str}'::vector) as similarity
                FROM tasks
                WHERE embedding_vector IS NOT NULL
                {status_clause}
                {ticket_clause}
                {task_type_clause}
                AND 1 - (embedding_vector <=> '{embedding_str}'::vector) >= :threshold
                ORDER BY embedding_vector <=> '{embedding_str}'::vector
                LIMIT :top_k
            """)

            try:
                result = sess.execute(
                    query,
                    {
                        "threshold": threshold,
                        "top_k": top_k,
                    },
                )
                rows = result.fetchall()
            except Exception as e:
                logger.error(f"pgvector query failed: {e}")
                # Fallback to in-memory comparison if pgvector query fails
                return self._fallback_check(
                    sess, embedding, task_type, ticket_id, threshold, top_k, exclude_statuses
                )

            candidates = [
                DuplicateTaskCandidate(
                    task_id=str(row.id),
                    task_type=row.task_type,
                    title=row.title,
                    description=row.description or "",
                    status=row.status,
                    ticket_id=str(row.ticket_id),
                    similarity_score=float(row.similarity),
                )
                for row in rows
            ]

            highest_similarity = max(
                (c.similarity_score for c in candidates), default=0.0
            )

            return TaskDeduplicationResult(
                is_duplicate=highest_similarity >= threshold,
                candidates=candidates,
                highest_similarity=highest_similarity,
                embedding=embedding,
            )

        if session:
            return _check(session)
        else:
            with self.db.get_session() as sess:
                return _check(sess)

    def _fallback_check(
        self,
        session: Session,
        embedding: List[float],
        task_type: str,
        ticket_id: Optional[str],
        threshold: float,
        top_k: int,
        exclude_statuses: List[str],
    ) -> TaskDeduplicationResult:
        """Fallback to in-memory similarity check if pgvector fails."""
        logger.info("Using fallback in-memory similarity check for tasks")

        # Build query filters
        filters = [
            Task.embedding_vector.isnot(None),
            Task.task_type == task_type,
        ]
        if exclude_statuses:
            filters.append(~Task.status.in_(exclude_statuses))
        if ticket_id:
            filters.append(Task.ticket_id == ticket_id)

        # Get all matching tasks with embeddings
        query = select(Task).where(*filters)
        result = session.execute(query)
        tasks = result.scalars().all()

        candidates = []
        for task in tasks:
            if task.embedding_vector:
                similarity = self.embedding_service.cosine_similarity(
                    embedding, list(task.embedding_vector)
                )
                if similarity >= threshold:
                    candidates.append(
                        DuplicateTaskCandidate(
                            task_id=str(task.id),
                            task_type=task.task_type,
                            title=task.title,
                            description=task.description or "",
                            status=task.status,
                            ticket_id=str(task.ticket_id),
                            similarity_score=similarity,
                        )
                    )

        # Sort by similarity descending
        candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        candidates = candidates[:top_k]

        highest_similarity = max((c.similarity_score for c in candidates), default=0.0)

        return TaskDeduplicationResult(
            is_duplicate=highest_similarity >= threshold,
            candidates=candidates,
            highest_similarity=highest_similarity,
            embedding=embedding,
        )

    def generate_and_store_embedding(
        self,
        task: Task,
        session: Optional[Session] = None,
    ) -> Optional[List[float]]:
        """Generate and store embedding for a task.

        Args:
            task: The task to generate embedding for.
            session: Optional database session.

        Returns:
            The generated embedding, or None if generation failed.
        """
        content = f"{task.task_type}: {task.title or ''}\n{task.description or ''}"
        embedding = self.embedding_service.generate_embedding(content)

        if not embedding:
            logger.warning(f"Failed to generate embedding for task {task.id}")
            return None

        # Update the embedding directly on the task object
        if session and task in session:
            task.embedding_vector = embedding
            session.flush()
        elif session:
            # If task not in session, update via SQL
            from sqlalchemy import update

            stmt = (
                update(Task)
                .where(Task.id == str(task.id))
                .values(embedding_vector=embedding)
            )
            session.execute(stmt)
            session.flush()
        else:
            with self.db.get_session() as sess:
                from sqlalchemy import update

                stmt = (
                    update(Task)
                    .where(Task.id == str(task.id))
                    .values(embedding_vector=embedding)
                )
                sess.execute(stmt)
                sess.commit()

        return embedding

    def check_similar_pending_diagnostic(
        self,
        workflow_id: str,
        description: str,
        threshold: float = 0.90,
        session: Optional[Session] = None,
    ) -> TaskDeduplicationResult:
        """Check for semantically similar pending diagnostic tasks.

        This is a convenience method specifically for the diagnostic service
        to check for existing similar diagnostic tasks before spawning new ones.

        Args:
            workflow_id: The ticket/workflow ID.
            description: Description of the diagnostic task.
            threshold: Similarity threshold (default 0.90 for strict matching).
            session: Optional database session.

        Returns:
            TaskDeduplicationResult with duplicate status.
        """
        return self.check_duplicate(
            task_type="discovery_diagnostic_no_result",
            description=description,
            ticket_id=workflow_id,
            top_k=3,
            threshold=threshold,
            exclude_statuses=["completed", "failed"],
            session=session,
        )
