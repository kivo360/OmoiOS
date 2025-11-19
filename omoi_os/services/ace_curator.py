"""Curator service for ACE workflow (REQ-MEM-ACE-003)."""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.models.playbook_entry import PlaybookEntry
from omoi_os.models.playbook_change import PlaybookChange
from omoi_os.services.embedding import EmbeddingService
from omoi_os.utils.datetime import utc_now

# Forward reference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from omoi_os.services.ace_reflector import ReflectorResult, Insight
    from omoi_os.services.ace_executor import ExecutorResult


@dataclass
class DeltaOperation:
    """Delta operation for playbook changes (REQ-MEM-ACE-003)."""
    
    operation: str  # add, update, delete
    content: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    entry_id: Optional[str] = None  # For update/delete operations


@dataclass
class PlaybookDelta:
    """Playbook delta with operations and summary (REQ-MEM-ACE-003)."""
    
    operations: List[DeltaOperation]
    summary: str


@dataclass
class PlaybookBullet:
    """Playbook bullet entry (REQ-MEM-ACE-003)."""
    
    id: str
    content: str
    category: Optional[str]
    tags: Optional[List[str]]
    supporting_memory_ids: Optional[List[str]]


@dataclass
class CuratorResult:
    """Result from Curator phase (REQ-MEM-ACE-003)."""
    
    playbook_delta: PlaybookDelta
    updated_bullets: List[PlaybookBullet]
    change_id: Optional[str]


class Curator:
    """
    Curator service for ACE workflow (REQ-MEM-ACE-003).
    
    Responsibilities:
    - Propose playbook updates based on insights
    - Generate delta operations (add/update/delete)
    - Validate deltas (check duplicates, quality thresholds)
    - Apply accepted deltas to playbook
    - Record change history
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
    ):
        """
        Initialize Curator service.
        
        Args:
            embedding_service: Embedding service for semantic search
        """
        self.embedding_service = embedding_service
    
    def curate(
        self,
        session: Session,
        executor_result: "ExecutorResult",
        reflector_result: "ReflectorResult",
        ticket_id: str,
        memory_id: str,
        agent_id: str,
    ) -> CuratorResult:
        """
        Curate phase: update playbook with new knowledge (REQ-MEM-ACE-003).
        
        Steps:
        1. Get current playbook state
        2. Propose updates from insights
        3. Generate delta operations
        4. Validate delta
        5. Apply delta
        6. Record change history
        
        Args:
            session: Database session
            executor_result: Result from Executor phase
            reflector_result: Result from Reflector phase
            ticket_id: Ticket ID for playbook
            memory_id: Memory ID that triggered this curation
            agent_id: Agent ID that created the memory
            
        Returns:
            CuratorResult with playbook_delta, updated_bullets, change_id
        """
        # Get current playbook entries for this ticket (REQ-MEM-ACE-003)
        current_playbook_query = select(PlaybookEntry).where(
            PlaybookEntry.ticket_id == ticket_id,
            PlaybookEntry.is_active == True,  # noqa: E712
        )
        current_playbook = session.execute(current_playbook_query).scalars().all()
        
        # Propose updates from insights (REQ-MEM-ACE-003)
        proposals = []
        for insight in reflector_result.insights_found:
            # Check if insight is novel (not already in playbook)
            existing = self.search_playbook_for_similar(
                session=session,
                content=insight.content,
                ticket_id=ticket_id,
                threshold=0.85,
            )
            
            if not existing:
                # Infer category from insight type
                category = self.infer_category(insight)
                
                proposals.append(DeltaOperation(
                    operation="add",
                    content=insight.content,
                    category=category,
                    tags=executor_result.tags,
                ))
        
        # Generate delta (REQ-MEM-ACE-003)
        delta = PlaybookDelta(
            operations=proposals,
            summary=f"Added {len(proposals)} new insights from task completion",
        )
        
        # Validate delta (REQ-MEM-ACE-003)
        if not self.validate_delta(delta, current_playbook):
            return CuratorResult(
                playbook_delta=PlaybookDelta(operations=[], summary="No valid updates"),
                updated_bullets=[],
                change_id=None,
            )
        
        # Apply delta (REQ-MEM-ACE-003)
        updated_bullets = []
        for op in delta.operations:
            if op.operation == "add":
                # Generate embedding for new entry
                embedding = self.embedding_service.generate_embedding(op.content)
                
                # Create playbook entry
                entry = PlaybookEntry(
                    ticket_id=ticket_id,
                    content=op.content,
                    category=op.category,
                    tags=op.tags,
                    embedding=embedding,
                    supporting_memory_ids=[memory_id],
                    created_by=agent_id,
                    priority=0,  # Default priority
                    is_active=True,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                session.add(entry)
                session.flush()
                
                updated_bullets.append(PlaybookBullet(
                    id=entry.id,
                    content=entry.content,
                    category=entry.category,
                    tags=entry.tags,
                    supporting_memory_ids=entry.supporting_memory_ids,
                ))
        
        session.flush()
        
        # Record change history (REQ-MEM-DM-007)
        change_id = None
        if updated_bullets:
            change = PlaybookChange(
                ticket_id=ticket_id,
                operation="add",
                new_content=str([b.content for b in updated_bullets]),
                delta={
                    "operations": [
                        {"operation": op.operation, "content": op.content, "category": op.category}
                        for op in delta.operations
                    ],
                    "summary": delta.summary,
                },
                reason="ACE workflow completion",
                related_memory_id=memory_id,
                changed_by=agent_id,
                changed_at=utc_now(),
            )
            session.add(change)
            session.flush()
            change_id = change.id
        
        return CuratorResult(
            playbook_delta=delta,
            updated_bullets=updated_bullets,
            change_id=change_id,
        )
    
    def search_playbook_for_similar(
        self,
        session: Session,
        content: str,
        ticket_id: str,
        threshold: float = 0.85,
    ) -> Optional[PlaybookEntry]:
        """
        Search playbook for similar entries (REQ-MEM-ACE-003).
        
        Args:
            session: Database session
            content: Content to search for
            ticket_id: Ticket ID to search within
            threshold: Minimum similarity threshold
            
        Returns:
            Similar PlaybookEntry if found, None otherwise
        """
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(content)
        
        if not query_embedding:
            return None
        
        # Query playbook entries
        query = select(PlaybookEntry).where(
            PlaybookEntry.ticket_id == ticket_id,
            PlaybookEntry.is_active == True,  # noqa: E712
            PlaybookEntry.embedding.isnot(None),
        )
        
        entries = session.execute(query).scalars().all()
        
        # Calculate similarity
        for entry in entries:
            if entry.embedding:
                similarity = self._cosine_similarity(query_embedding, entry.embedding)
                if similarity >= threshold:
                    return entry
        
        return None
    
    def validate_delta(
        self,
        delta: PlaybookDelta,
        current_playbook: List[PlaybookEntry],
    ) -> bool:
        """
        Validate delta operations (REQ-MEM-ACE-003).
        
        Checks:
        - No exact duplicates
        - Content meets minimum quality (>10 chars)
        - Category is valid (if provided)
        
        Args:
            delta: Playbook delta to validate
            current_playbook: Current playbook entries
            
        Returns:
            True if delta is valid, False otherwise
        """
        for op in delta.operations:
            # Check minimum content length
            if len(op.content) < 10:
                return False
            
            # Check for exact duplicates in current playbook
            for entry in current_playbook:
                if entry.content.strip().lower() == op.content.strip().lower():
                    return False
        
        return True
    
    def infer_category(self, insight: "Insight") -> str:
        """
        Infer playbook category from insight type (REQ-MEM-ACE-003).
        
        Args:
            insight: Insight object
            
        Returns:
            Category string
        """
        category_map = {
            "pattern": "patterns",
            "gotcha": "gotchas",
            "best_practice": "best_practices",
        }
        
        return category_map.get(insight.insight_type, "general")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        
        return dot_product / (norm1 * norm2)

