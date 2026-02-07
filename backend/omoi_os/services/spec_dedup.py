"""Spec deduplication service using content hashes and pgvector embeddings.

This service provides multi-level deduplication for the spec-driven development
workflow to prevent duplicate specs, requirements, tasks, and acceptance criteria
from being created during phase execution and retries.

Deduplication Strategy:
1. Fast path: SHA256 content hash for exact matches
2. Semantic path: Embedding similarity via pgvector for near-duplicates

Scoping:
- Specs: Deduplicated within project_id
- Requirements: Deduplicated within spec_id
- Tasks: Deduplicated within spec_id
- Acceptance Criteria: Deduplicated within requirement_id

Thresholds (tuned per entity type):
- Specs: 0.92 (should be very different to coexist)
- Requirements: 0.88 (some overlap expected)
- Tasks: 0.85 (granular, need precise matching)
- Criteria: Hash only (short text, hash is sufficient)
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from omoi_os.logging import get_logger
from omoi_os.models.spec import (
    Spec,
    SpecAcceptanceCriterion,
    SpecRequirement,
    SpecTask,
)
from omoi_os.services.database import DatabaseService
from omoi_os.services.embedding import EmbeddingService

logger = get_logger(__name__)


class EntityType(str, Enum):
    """Entity types for deduplication."""

    SPEC = "spec"
    REQUIREMENT = "requirement"
    TASK = "task"
    CRITERION = "criterion"


# Tuned thresholds per entity type
SIMILARITY_THRESHOLDS = {
    EntityType.SPEC: 0.92,  # Specs should be very different
    EntityType.REQUIREMENT: 0.88,  # Some overlap expected in requirements
    EntityType.TASK: 0.85,  # Tasks are granular
    EntityType.CRITERION: 1.0,  # Hash only for criteria
}


@dataclass
class DuplicateCandidate:
    """A potential duplicate entity."""

    entity_id: str
    entity_type: EntityType
    content_preview: str  # First 100 chars for debugging
    similarity_score: float
    is_exact_match: bool  # True if matched by hash


@dataclass
class DeduplicationResult:
    """Result of a deduplication check."""

    is_duplicate: bool
    action: str  # "create", "skip", "merge"
    candidates: List[DuplicateCandidate] = field(default_factory=list)
    highest_similarity: float = 0.0
    content_hash: Optional[str] = None
    embedding: Optional[List[float]] = None
    merge_target_id: Optional[str] = None  # If action is "merge"
    reason: str = ""


@dataclass
class BulkDeduplicationResult:
    """Result of bulk deduplication for a list of items."""

    to_create: List[dict] = field(default_factory=list)  # New items to insert
    to_skip: List[dict] = field(default_factory=list)  # Duplicates to skip
    to_merge: List[tuple] = field(default_factory=list)  # (new_item, existing_id) pairs
    stats: dict = field(default_factory=dict)


def normalize_text(text: str) -> str:
    """Normalize text for consistent hashing.

    - Lowercase
    - Strip whitespace
    - Collapse multiple spaces
    - Remove punctuation variations
    """
    if not text:
        return ""
    normalized = text.lower().strip()
    # Collapse multiple whitespace
    normalized = " ".join(normalized.split())
    return normalized


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of normalized content."""
    normalized = normalize_text(content)
    return hashlib.sha256(normalized.encode()).hexdigest()


class SpecDeduplicationService:
    """Service for detecting and handling duplicate spec entities.

    Handles deduplication at multiple levels:
    1. Spec-level (within project)
    2. Requirement-level (within spec)
    3. Task-level (within spec)
    4. Criterion-level (within requirement)

    Uses a two-phase approach:
    1. Fast hash check for exact duplicates
    2. Embedding similarity for semantic near-duplicates
    """

    def __init__(
        self,
        db: DatabaseService,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        """Initialize the deduplication service.

        Args:
            db: Database service for queries.
            embedding_service: Optional embedding service for semantic similarity.
                              If not provided, only hash-based dedup is used.
        """
        self.db = db
        self.embedding_service = embedding_service

    # =========================================================================
    # Public API - Single Entity Checks
    # =========================================================================

    async def check_spec_duplicate(
        self,
        project_id: str,
        title: str,
        description: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> DeduplicationResult:
        """Check if a spec with similar content exists in the project.

        Args:
            project_id: Project to scope the search.
            title: Spec title.
            description: Spec description.
            session: Optional async session.

        Returns:
            DeduplicationResult with action recommendation.
        """
        content = f"{title}\n{description or ''}"
        return await self._check_duplicate(
            entity_type=EntityType.SPEC,
            scope_field="project_id",
            scope_value=project_id,
            content=content,
            model_class=Spec,
            session=session,
        )

    async def check_requirement_duplicate(
        self,
        spec_id: str,
        title: str,
        condition: str,
        action: str,
        session: Optional[AsyncSession] = None,
    ) -> DeduplicationResult:
        """Check if a requirement with similar content exists in the spec.

        Uses EARS format (condition + action) for content comparison.

        Args:
            spec_id: Spec to scope the search.
            title: Requirement title.
            condition: EARS "WHEN" clause.
            action: EARS "THE SYSTEM SHALL" clause.
            session: Optional async session.

        Returns:
            DeduplicationResult with action recommendation.
        """
        # EARS format content - title is less important than condition+action
        content = f"{condition}\n{action}"
        return await self._check_duplicate(
            entity_type=EntityType.REQUIREMENT,
            scope_field="spec_id",
            scope_value=spec_id,
            content=content,
            model_class=SpecRequirement,
            session=session,
        )

    async def check_task_duplicate(
        self,
        spec_id: str,
        title: str,
        description: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> DeduplicationResult:
        """Check if a task with similar content exists in the spec.

        Args:
            spec_id: Spec to scope the search.
            title: Task title.
            description: Task description.
            session: Optional async session.

        Returns:
            DeduplicationResult with action recommendation.
        """
        content = f"{title}\n{description or ''}"
        return await self._check_duplicate(
            entity_type=EntityType.TASK,
            scope_field="spec_id",
            scope_value=spec_id,
            content=content,
            model_class=SpecTask,
            session=session,
        )

    async def check_criterion_duplicate(
        self,
        requirement_id: str,
        text: str,
        session: Optional[AsyncSession] = None,
    ) -> DeduplicationResult:
        """Check if an acceptance criterion exists in the requirement.

        Uses hash-only comparison (criteria are short).

        Args:
            requirement_id: Requirement to scope the search.
            text: Criterion text.
            session: Optional async session.

        Returns:
            DeduplicationResult with action recommendation.
        """
        content_hash = compute_content_hash(text)

        async def _check(sess: AsyncSession) -> DeduplicationResult:
            # Hash-only check for criteria
            query = select(SpecAcceptanceCriterion).where(
                SpecAcceptanceCriterion.requirement_id == requirement_id,
                SpecAcceptanceCriterion.content_hash == content_hash,
            )
            result = await sess.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                return DeduplicationResult(
                    is_duplicate=True,
                    action="skip",
                    candidates=[
                        DuplicateCandidate(
                            entity_id=existing.id,
                            entity_type=EntityType.CRITERION,
                            content_preview=existing.text[:100],
                            similarity_score=1.0,
                            is_exact_match=True,
                        )
                    ],
                    highest_similarity=1.0,
                    content_hash=content_hash,
                    reason="Exact content match via hash",
                )

            return DeduplicationResult(
                is_duplicate=False,
                action="create",
                content_hash=content_hash,
                reason="No duplicate found",
            )

        if session:
            return await _check(session)
        else:
            async with self.db.get_async_session() as sess:
                return await _check(sess)

    # =========================================================================
    # Public API - Bulk Deduplication
    # =========================================================================

    async def deduplicate_requirements_bulk(
        self,
        spec_id: str,
        requirements: List[dict],
        session: Optional[AsyncSession] = None,
    ) -> BulkDeduplicationResult:
        """Deduplicate a batch of requirements before insertion.

        This is optimized for the SYNC phase where multiple requirements
        are generated and need to be checked in bulk.

        Args:
            spec_id: Spec to scope the search.
            requirements: List of requirement dicts with title, condition, action.
            session: Optional async session.

        Returns:
            BulkDeduplicationResult with categorized items.
        """
        result = BulkDeduplicationResult(
            stats={"total": len(requirements), "created": 0, "skipped": 0, "merged": 0}
        )

        for req in requirements:
            title = req.get("title", "")
            condition = req.get("condition", "")
            action = req.get("action", "")

            dedup_result = await self.check_requirement_duplicate(
                spec_id=spec_id,
                title=title,
                condition=condition,
                action=action,
                session=session,
            )

            # Add hash and embedding to the requirement dict
            req["content_hash"] = dedup_result.content_hash
            if dedup_result.embedding:
                req["embedding_vector"] = dedup_result.embedding

            if dedup_result.action == "create":
                result.to_create.append(req)
                result.stats["created"] += 1
            elif dedup_result.action == "skip":
                result.to_skip.append(req)
                result.stats["skipped"] += 1
                logger.info(
                    "Skipping duplicate requirement",
                    extra={
                        "title": title[:50],
                        "duplicate_of": (
                            dedup_result.candidates[0].entity_id
                            if dedup_result.candidates
                            else None
                        ),
                        "similarity": dedup_result.highest_similarity,
                    },
                )
            elif dedup_result.action == "merge":
                result.to_merge.append((req, dedup_result.merge_target_id))
                result.stats["merged"] += 1

        logger.info(
            "Bulk requirement deduplication complete",
            extra={
                "spec_id": spec_id,
                "stats": result.stats,
            },
        )

        return result

    async def deduplicate_tasks_bulk(
        self,
        spec_id: str,
        tasks: List[dict],
        session: Optional[AsyncSession] = None,
    ) -> BulkDeduplicationResult:
        """Deduplicate a batch of tasks before insertion.

        Args:
            spec_id: Spec to scope the search.
            tasks: List of task dicts with title, description.
            session: Optional async session.

        Returns:
            BulkDeduplicationResult with categorized items.
        """
        result = BulkDeduplicationResult(
            stats={"total": len(tasks), "created": 0, "skipped": 0, "merged": 0}
        )

        for task in tasks:
            title = task.get("title", "")
            description = task.get("description", "")

            dedup_result = await self.check_task_duplicate(
                spec_id=spec_id,
                title=title,
                description=description,
                session=session,
            )

            task["content_hash"] = dedup_result.content_hash
            if dedup_result.embedding:
                task["embedding_vector"] = dedup_result.embedding

            if dedup_result.action == "create":
                result.to_create.append(task)
                result.stats["created"] += 1
            elif dedup_result.action == "skip":
                result.to_skip.append(task)
                result.stats["skipped"] += 1
                logger.info(
                    "Skipping duplicate task",
                    extra={
                        "title": title[:50],
                        "duplicate_of": (
                            dedup_result.candidates[0].entity_id
                            if dedup_result.candidates
                            else None
                        ),
                        "similarity": dedup_result.highest_similarity,
                    },
                )
            elif dedup_result.action == "merge":
                result.to_merge.append((task, dedup_result.merge_target_id))
                result.stats["merged"] += 1

        logger.info(
            "Bulk task deduplication complete",
            extra={
                "spec_id": spec_id,
                "stats": result.stats,
            },
        )

        return result

    async def deduplicate_criteria_bulk(
        self,
        requirement_id: str,
        criteria: List[dict],
        session: Optional[AsyncSession] = None,
    ) -> BulkDeduplicationResult:
        """Deduplicate a batch of acceptance criteria before insertion.

        Uses hash-only comparison for efficiency.

        Args:
            requirement_id: Requirement to scope the search.
            criteria: List of criterion dicts with text.
            session: Optional async session.

        Returns:
            BulkDeduplicationResult with categorized items.
        """
        result = BulkDeduplicationResult(
            stats={"total": len(criteria), "created": 0, "skipped": 0, "merged": 0}
        )

        for criterion in criteria:
            text = criterion.get("text", "")

            dedup_result = await self.check_criterion_duplicate(
                requirement_id=requirement_id,
                text=text,
                session=session,
            )

            criterion["content_hash"] = dedup_result.content_hash

            if dedup_result.action == "create":
                result.to_create.append(criterion)
                result.stats["created"] += 1
            else:
                result.to_skip.append(criterion)
                result.stats["skipped"] += 1

        return result

    # =========================================================================
    # Public API - Generate and Store Embeddings
    # =========================================================================

    async def generate_and_store_spec_embedding(
        self,
        spec: Spec,
        session: Optional[AsyncSession] = None,
    ) -> Optional[List[float]]:
        """Generate and store embedding for a spec.

        Also computes and stores the content hash.

        Args:
            spec: The spec to generate embedding for.
            session: Optional async session.

        Returns:
            The generated embedding, or None if generation failed.
        """
        content = f"{spec.title}\n{spec.description or ''}"
        content_hash = compute_content_hash(content)

        embedding = None
        if self.embedding_service:
            embedding = self.embedding_service.generate_embedding(content)

        async def _store(sess: AsyncSession) -> Optional[List[float]]:
            stmt = (
                update(Spec)
                .where(Spec.id == spec.id)
                .values(
                    content_hash=content_hash,
                    embedding_vector=embedding,
                )
            )
            await sess.execute(stmt)
            await sess.flush()
            return embedding

        if session:
            return await _store(session)
        else:
            async with self.db.get_async_session() as sess:
                result = await _store(sess)
                await sess.commit()
                return result

    async def generate_and_store_requirement_embedding(
        self,
        requirement: SpecRequirement,
        session: Optional[AsyncSession] = None,
    ) -> Optional[List[float]]:
        """Generate and store embedding for a requirement."""
        content = f"{requirement.condition}\n{requirement.action}"
        content_hash = compute_content_hash(content)

        embedding = None
        if self.embedding_service:
            embedding = self.embedding_service.generate_embedding(content)

        async def _store(sess: AsyncSession) -> Optional[List[float]]:
            stmt = (
                update(SpecRequirement)
                .where(SpecRequirement.id == requirement.id)
                .values(
                    content_hash=content_hash,
                    embedding_vector=embedding,
                )
            )
            await sess.execute(stmt)
            await sess.flush()
            return embedding

        if session:
            return await _store(session)
        else:
            async with self.db.get_async_session() as sess:
                result = await _store(sess)
                await sess.commit()
                return result

    # =========================================================================
    # Private - Core Deduplication Logic
    # =========================================================================

    async def _check_duplicate(
        self,
        entity_type: EntityType,
        scope_field: str,
        scope_value: str,
        content: str,
        model_class: Any,
        session: Optional[AsyncSession] = None,
    ) -> DeduplicationResult:
        """Core deduplication logic for any entity type.

        Two-phase approach:
        1. Fast hash check for exact matches
        2. Embedding similarity for near-duplicates (if embedding service available)

        Args:
            entity_type: Type of entity being checked.
            scope_field: Field name for scoping (e.g., "project_id", "spec_id").
            scope_value: Value for the scope field.
            content: Content to check for duplicates.
            model_class: SQLAlchemy model class.
            session: Optional async session.

        Returns:
            DeduplicationResult with action recommendation.
        """
        content_hash = compute_content_hash(content)
        threshold = SIMILARITY_THRESHOLDS[entity_type]

        async def _check(sess: AsyncSession) -> DeduplicationResult:
            # Phase 1: Fast hash check
            hash_query = select(model_class).where(
                getattr(model_class, scope_field) == scope_value,
                model_class.content_hash == content_hash,
            )
            result = await sess.execute(hash_query)
            exact_match = result.scalar_one_or_none()

            if exact_match:
                preview = self._get_content_preview(exact_match, entity_type)
                return DeduplicationResult(
                    is_duplicate=True,
                    action="skip",
                    candidates=[
                        DuplicateCandidate(
                            entity_id=exact_match.id,
                            entity_type=entity_type,
                            content_preview=preview,
                            similarity_score=1.0,
                            is_exact_match=True,
                        )
                    ],
                    highest_similarity=1.0,
                    content_hash=content_hash,
                    reason="Exact content match via hash",
                )

            # Phase 2: Semantic similarity (if embedding service available)
            embedding = None
            if self.embedding_service:
                embedding = self.embedding_service.generate_embedding(content)

                if embedding:
                    candidates = await self._find_similar_by_embedding(
                        sess=sess,
                        model_class=model_class,
                        scope_field=scope_field,
                        scope_value=scope_value,
                        embedding=embedding,
                        entity_type=entity_type,
                        threshold=threshold,
                        top_k=3,
                    )

                    if candidates:
                        highest = candidates[0]
                        # Determine action based on similarity
                        if highest.similarity_score >= threshold:
                            return DeduplicationResult(
                                is_duplicate=True,
                                action="skip",
                                candidates=candidates,
                                highest_similarity=highest.similarity_score,
                                content_hash=content_hash,
                                embedding=embedding,
                                reason=f"Semantic similarity {highest.similarity_score:.2f} >= {threshold}",
                            )

            # No duplicate found
            return DeduplicationResult(
                is_duplicate=False,
                action="create",
                content_hash=content_hash,
                embedding=embedding,
                reason="No duplicate found",
            )

        if session:
            return await _check(session)
        else:
            async with self.db.get_async_session() as sess:
                return await _check(sess)

    async def _find_similar_by_embedding(
        self,
        sess: AsyncSession,
        model_class: Any,
        scope_field: str,
        scope_value: str,
        embedding: List[float],
        entity_type: EntityType,
        threshold: float,
        top_k: int = 3,
    ) -> List[DuplicateCandidate]:
        """Find similar entities by embedding using pgvector.

        Uses cosine distance operator for similarity search.

        Args:
            sess: Async database session.
            model_class: SQLAlchemy model class.
            scope_field: Field name for scoping.
            scope_value: Value for the scope field.
            embedding: Embedding vector to compare against.
            entity_type: Type of entity.
            threshold: Minimum similarity threshold.
            top_k: Maximum number of candidates to return.

        Returns:
            List of DuplicateCandidate sorted by similarity descending.
        """
        # Build embedding string for pgvector
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        table_name = model_class.__tablename__

        # Use raw SQL for pgvector query
        query = text(f"""
            SELECT
                id,
                1 - (embedding_vector <=> '{embedding_str}'::vector) as similarity
            FROM {table_name}
            WHERE {scope_field} = :scope_value
            AND embedding_vector IS NOT NULL
            AND 1 - (embedding_vector <=> '{embedding_str}'::vector) >= :threshold
            ORDER BY embedding_vector <=> '{embedding_str}'::vector
            LIMIT :top_k
        """)

        try:
            result = await sess.execute(
                query,
                {
                    "scope_value": scope_value,
                    "threshold": threshold,
                    "top_k": top_k,
                },
            )
            rows = result.fetchall()
        except Exception as e:
            logger.warning(f"pgvector similarity query failed: {e}")
            # Fallback to in-memory comparison
            return await self._fallback_similarity_check(
                sess,
                model_class,
                scope_field,
                scope_value,
                embedding,
                entity_type,
                threshold,
                top_k,
            )

        candidates = []
        for row in rows:
            # Fetch the full entity for preview
            entity_query = select(model_class).where(model_class.id == row.id)
            entity_result = await sess.execute(entity_query)
            entity = entity_result.scalar_one_or_none()

            if entity:
                preview = self._get_content_preview(entity, entity_type)
                candidates.append(
                    DuplicateCandidate(
                        entity_id=str(row.id),
                        entity_type=entity_type,
                        content_preview=preview,
                        similarity_score=float(row.similarity),
                        is_exact_match=False,
                    )
                )

        return candidates

    async def _fallback_similarity_check(
        self,
        sess: AsyncSession,
        model_class: Any,
        scope_field: str,
        scope_value: str,
        embedding: List[float],
        entity_type: EntityType,
        threshold: float,
        top_k: int,
    ) -> List[DuplicateCandidate]:
        """Fallback to in-memory similarity check if pgvector fails."""
        logger.info("Using fallback in-memory similarity check")

        query = select(model_class).where(
            getattr(model_class, scope_field) == scope_value,
            model_class.embedding_vector.isnot(None),
        )
        result = await sess.execute(query)
        entities = result.scalars().all()

        candidates = []
        for entity in entities:
            if entity.embedding_vector:
                similarity = self._cosine_similarity(
                    embedding, list(entity.embedding_vector)
                )
                if similarity >= threshold:
                    preview = self._get_content_preview(entity, entity_type)
                    candidates.append(
                        DuplicateCandidate(
                            entity_id=str(entity.id),
                            entity_type=entity_type,
                            content_preview=preview,
                            similarity_score=similarity,
                            is_exact_match=False,
                        )
                    )

        # Sort by similarity descending
        candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        return candidates[:top_k]

    def _get_content_preview(self, entity: Any, entity_type: EntityType) -> str:
        """Get a preview of entity content for debugging."""
        if entity_type == EntityType.SPEC:
            return f"{entity.title}: {(entity.description or '')[:80]}"
        elif entity_type == EntityType.REQUIREMENT:
            return f"{entity.title}: {entity.condition[:80]}"
        elif entity_type == EntityType.TASK:
            return f"{entity.title}: {(entity.description or '')[:80]}"
        elif entity_type == EntityType.CRITERION:
            return entity.text[:100]
        return str(entity)[:100]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


# =============================================================================
# Factory Function
# =============================================================================


def get_spec_dedup_service(
    db: DatabaseService,
    embedding_service: Optional[EmbeddingService] = None,
) -> SpecDeduplicationService:
    """Factory function to create a SpecDeduplicationService instance.

    Args:
        db: Database service.
        embedding_service: Optional embedding service for semantic similarity.

    Returns:
        Configured SpecDeduplicationService instance.
    """
    return SpecDeduplicationService(db=db, embedding_service=embedding_service)
