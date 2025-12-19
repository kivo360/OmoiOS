"""Ticket deduplication service using pgvector embeddings."""

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import text, select
from sqlalchemy.orm import Session

from omoi_os.logging import get_logger
from omoi_os.models.ticket import Ticket  # Use main model (has embedding_vector now)
from omoi_os.services.database import DatabaseService
from omoi_os.services.embedding import EmbeddingService

logger = get_logger(__name__)

# Default similarity threshold - tickets above this are considered duplicates
DEFAULT_SIMILARITY_THRESHOLD = 0.85


@dataclass
class DuplicateCandidate:
    """A potential duplicate ticket."""

    ticket_id: str
    title: str
    description: str
    status: str
    similarity_score: float


@dataclass
class DeduplicationResult:
    """Result of duplicate check."""

    is_duplicate: bool
    candidates: List[DuplicateCandidate]
    highest_similarity: float
    embedding: Optional[List[float]] = None


class TicketDeduplicationService:
    """Service for detecting duplicate tickets using embedding similarity.

    Uses pgvector's cosine distance operator to find similar tickets
    based on their embedding vectors.
    """

    def __init__(
        self,
        db: DatabaseService,
        embedding_service: EmbeddingService,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        """Initialize the deduplication service.

        Args:
            db: Database service for querying tickets.
            embedding_service: Service for generating embeddings.
            similarity_threshold: Minimum similarity score to consider as duplicate (0.0-1.0).
        """
        self.db = db
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold

    def check_duplicate(
        self,
        title: str,
        description: Optional[str] = None,
        top_k: int = 5,
        threshold: Optional[float] = None,
        exclude_statuses: Optional[List[str]] = None,
        session: Optional[Session] = None,
    ) -> DeduplicationResult:
        """Check if a ticket with similar content already exists.

        Args:
            title: Ticket title.
            description: Ticket description (optional).
            top_k: Maximum number of similar tickets to return.
            threshold: Override default similarity threshold.
            exclude_statuses: List of statuses to exclude (e.g., ['done', 'cancelled']).
            session: Optional database session.

        Returns:
            DeduplicationResult with duplicate status and candidates.
        """
        threshold = threshold or self.similarity_threshold
        exclude_statuses = exclude_statuses or []

        # Generate embedding for the new ticket content
        content = f"{title}\n{description or ''}"
        embedding = self.embedding_service.generate_embedding(content)

        if not embedding:
            logger.warning("Failed to generate embedding for deduplication check")
            return DeduplicationResult(
                is_duplicate=False,
                candidates=[],
                highest_similarity=0.0,
                embedding=None,
            )

        def _check(sess: Session) -> DeduplicationResult:
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

            # Build query with pgvector - embedding is inserted directly since it's
            # already validated as a list of floats from our embedding service
            query = text(f"""
                SELECT 
                    id,
                    title,
                    description,
                    status,
                    1 - (embedding_vector <=> '{embedding_str}'::vector) as similarity
                FROM tickets
                WHERE embedding_vector IS NOT NULL
                {status_clause}
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
                    sess, embedding, threshold, top_k, exclude_statuses
                )

            candidates = [
                DuplicateCandidate(
                    ticket_id=str(row.id),
                    title=row.title,
                    description=row.description or "",
                    status=row.status,
                    similarity_score=float(row.similarity),
                )
                for row in rows
            ]

            highest_similarity = max(
                (c.similarity_score for c in candidates), default=0.0
            )

            return DeduplicationResult(
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
        threshold: float,
        top_k: int,
        exclude_statuses: List[str],
    ) -> DeduplicationResult:
        """Fallback to in-memory similarity check if pgvector fails."""
        logger.info("Using fallback in-memory similarity check")

        # Get all tickets with embeddings
        query = select(Ticket).where(
            Ticket.embedding_vector.isnot(None),
            ~Ticket.status.in_(exclude_statuses) if exclude_statuses else True,
        )
        result = session.execute(query)
        tickets = result.scalars().all()

        candidates = []
        for ticket in tickets:
            if ticket.embedding_vector:
                similarity = self.embedding_service.cosine_similarity(
                    embedding, list(ticket.embedding_vector)
                )
                if similarity >= threshold:
                    candidates.append(
                        DuplicateCandidate(
                            ticket_id=str(ticket.id),
                            title=ticket.title,
                            description=ticket.description or "",
                            status=ticket.status,
                            similarity_score=similarity,
                        )
                    )

        # Sort by similarity descending
        candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        candidates = candidates[:top_k]

        highest_similarity = max((c.similarity_score for c in candidates), default=0.0)

        return DeduplicationResult(
            is_duplicate=highest_similarity >= threshold,
            candidates=candidates,
            highest_similarity=highest_similarity,
            embedding=embedding,
        )

    def generate_and_store_embedding(
        self,
        ticket,  # Can be any Ticket model type
        session: Optional[Session] = None,
    ) -> Optional[List[float]]:
        """Generate and store embedding for a ticket.

        Args:
            ticket: The ticket to generate embedding for.
            session: Optional database session.

        Returns:
            The generated embedding, or None if generation failed.
        """
        content = f"{ticket.title}\n{ticket.description or ''}"
        embedding = self.embedding_service.generate_embedding(content)

        if not embedding:
            logger.warning(f"Failed to generate embedding for ticket {ticket.id}")
            return None

        # Update the embedding directly on the ticket object
        # This works because the ticket is already in the session
        if session and ticket in session:
            ticket.embedding_vector = embedding
            session.flush()
        elif session:
            # If ticket not in session, update via SQL
            from sqlalchemy import update

            stmt = (
                update(Ticket)
                .where(Ticket.id == str(ticket.id))
                .values(embedding_vector=embedding)
            )
            session.execute(stmt)
            session.flush()
        else:
            with self.db.get_session() as sess:
                from sqlalchemy import update

                stmt = (
                    update(Ticket)
                    .where(Ticket.id == str(ticket.id))
                    .values(embedding_vector=embedding)
                )
                sess.execute(stmt)
                sess.commit()

        return embedding
