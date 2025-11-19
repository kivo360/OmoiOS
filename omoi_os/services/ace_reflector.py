"""Reflector service for ACE workflow (REQ-MEM-ACE-002)."""

import re
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.models.playbook_entry import PlaybookEntry
from omoi_os.models.task_memory import TaskMemory
from omoi_os.services.embedding import EmbeddingService

if TYPE_CHECKING:
    from omoi_os.services.ace_executor import ExecutorResult


@dataclass
class Error:
    """Error identified from feedback (REQ-MEM-ACE-002)."""
    
    error_type: str
    message: str
    context: Optional[str] = None


@dataclass
class Insight:
    """Structured insight extracted from task completion (REQ-MEM-ACE-002)."""
    
    insight_type: str  # pattern, gotcha, best_practice
    content: str
    confidence: float


@dataclass
class ReflectorResult:
    """Result from Reflector phase (REQ-MEM-ACE-002)."""
    
    tags_added: List[str]  # Entry IDs that were tagged
    insights_found: List[Insight]
    errors_identified: List[Error]
    related_playbook_entries: List[str]  # Entry IDs


class Reflector:
    """
    Reflector service for ACE workflow (REQ-MEM-ACE-002).
    
    Responsibilities:
    - Analyze task feedback for errors and root causes
    - Search playbook for related entries using semantic search
    - Tag related entries with supporting memory IDs
    - Extract structured insights (patterns, gotchas, best practices)
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
    ):
        """
        Initialize Reflector service.
        
        Args:
            embedding_service: Embedding service for semantic search
        """
        self.embedding_service = embedding_service
    
    def analyze(
        self,
        session: Session,
        executor_result: "ExecutorResult",
        memory_id: str,
        feedback: str,
        ticket_id: str,
        goal: str,
        result: str,
    ) -> ReflectorResult:
        """
        Reflect phase: analyze what happened and find related knowledge (REQ-MEM-ACE-002).
        
        Steps:
        1. Identify errors from feedback
        2. Find root causes
        3. Search playbook for related entries
        4. Tag related entries
        5. Extract insights
        
        Args:
            session: Database session
            executor_result: Result from Executor phase
            memory_id: Memory ID from Executor phase
            feedback: Feedback from environment
            ticket_id: Ticket ID for playbook search
            goal: Task goal
            result: Task result
            
        Returns:
            ReflectorResult with tags, insights, errors, related entries
        """
        # Identify errors from feedback (REQ-MEM-ACE-002)
        errors = self.identify_errors(feedback)
        
        # Find related playbook entries via semantic search (REQ-MEM-ACE-002)
        related_entries = self.search_playbook_entries(
            session=session,
            query_text=f"{goal}\n\nResult: {result}",
            ticket_id=ticket_id,
            limit=5,
            similarity_threshold=0.7,
        )
        
        # Tag related entries with supporting memory IDs (REQ-MEM-ACE-002)
        tags_added = []
        for entry in related_entries:
            if entry.similarity_score > 0.7:
                # Add memory ID to supporting_memory_ids if not already present
                if entry.supporting_memory_ids is None:
                    entry.supporting_memory_ids = []
                if memory_id not in entry.supporting_memory_ids:
                    entry.supporting_memory_ids.append(memory_id)
                    session.add(entry)
                    tags_added.append(entry.id)
        
        session.flush()
        
        # Extract insights (REQ-MEM-ACE-002)
        insights = self.extract_insights(goal, result, feedback)
        
        return ReflectorResult(
            tags_added=tags_added,
            insights_found=insights,
            errors_identified=errors,
            related_playbook_entries=[e.id for e in related_entries],
        )
    
    def identify_errors(self, feedback: str) -> List[Error]:
        """
        Identify errors from feedback text (REQ-MEM-ACE-002).
        
        Looks for:
        - Error messages (ImportError, ValueError, etc.)
        - Failure indicators ("failed", "error", "exception")
        - Test failures
        
        Args:
            feedback: Feedback text from environment
            
        Returns:
            List of Error objects
        """
        errors = []
        if not feedback:
            return errors
        
        # Pattern matching for common error types
        error_patterns = {
            "ImportError": r"ImportError[^\n]*",
            "ValueError": r"ValueError[^\n]*",
            "KeyError": r"KeyError[^\n]*",
            "AttributeError": r"AttributeError[^\n]*",
            "TypeError": r"TypeError[^\n]*",
            "FileNotFoundError": r"FileNotFoundError[^\n]*",
            "PermissionError": r"PermissionError[^\n]*",
        }
        
        for error_type, pattern in error_patterns.items():
            matches = re.finditer(pattern, feedback, re.IGNORECASE)
            for match in matches:
                errors.append(Error(
                    error_type=error_type,
                    message=match.group(0),
                    context=feedback[max(0, match.start() - 100):match.end() + 100],
                ))
        
        # Check for generic failure indicators
        failure_keywords = ["failed", "error", "exception", "traceback", "failed tests"]
        for keyword in failure_keywords:
            if keyword.lower() in feedback.lower():
                # Avoid duplicate errors
                if not any(e.message.lower().startswith(keyword.lower()) for e in errors):
                    # Extract surrounding context
                    idx = feedback.lower().find(keyword.lower())
                    context_start = max(0, idx - 100)
                    context_end = min(len(feedback), idx + len(keyword) + 100)
                    errors.append(Error(
                        error_type="Failure",
                        message=f"{keyword}: {feedback[context_start:context_end]}",
                        context=feedback[context_start:context_end],
                    ))
                break  # Only add one generic failure
        
        return errors
    
    def search_playbook_entries(
        self,
        session: Session,
        query_text: str,
        ticket_id: str,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[Any]:  # Returns list with similarity_score attached
        """
        Search playbook entries using semantic similarity (REQ-MEM-ACE-002).
        
        Args:
            session: Database session
            query_text: Query text for semantic search
            ticket_id: Ticket ID to search within
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of PlaybookEntry objects with similarity_score attached
        """
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query_text)
        
        if not query_embedding:
            return []
        
        # Query playbook entries for this ticket
        query = select(PlaybookEntry).where(
            PlaybookEntry.ticket_id == ticket_id,
            PlaybookEntry.is_active == True,  # noqa: E712
            PlaybookEntry.embedding.isnot(None),
        )
        
        entries = session.execute(query).scalars().all()
        
        # Calculate cosine similarity
        results = []
        for entry in entries:
            if entry.embedding:
                similarity = self._cosine_similarity(query_embedding, entry.embedding)
                if similarity >= similarity_threshold:
                    # Attach similarity_score as dynamic attribute
                    entry.similarity_score = similarity
                    results.append(entry)
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return results[:limit]
    
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
    
    def extract_insights(self, goal: str, result: str, feedback: str) -> List[Insight]:
        """
        Extract structured insights from completion (REQ-MEM-ACE-002).
        
        Uses pattern matching to identify:
        - Patterns ("always", "never", "make sure to")
        - Gotchas ("careful with", "watch out for")
        - Best practices ("prefer", "recommend")
        
        Args:
            goal: Task goal
            result: Task result
            feedback: Feedback from environment
            
        Returns:
            List of Insight objects
        """
        insights = []
        text = f"{goal}\n\nResult: {result}\n\nFeedback: {feedback}".lower()
        
        # Pattern matching for insights
        pattern_keywords = ["always", "never", "make sure", "must", "should"]
        gotcha_keywords = ["careful", "watch out", "gotcha", "beware", "caution"]
        best_practice_keywords = ["prefer", "recommend", "best practice", "should use"]
        
        # Extract patterns
        for keyword in pattern_keywords:
            if keyword in text:
                # Extract sentence containing keyword
                sentences = re.split(r'[.!?]\s+', text)
                for sentence in sentences:
                    if keyword in sentence:
                        insights.append(Insight(
                            insight_type="pattern",
                            content=sentence.strip(),
                            confidence=0.7,
                        ))
                        break
        
        # Extract gotchas
        for keyword in gotcha_keywords:
            if keyword in text:
                sentences = re.split(r'[.!?]\s+', text)
                for sentence in sentences:
                    if keyword in sentence:
                        insights.append(Insight(
                            insight_type="gotcha",
                            content=sentence.strip(),
                            confidence=0.7,
                        ))
                        break
        
        # Extract best practices
        for keyword in best_practice_keywords:
            if keyword in text:
                sentences = re.split(r'[.!?]\s+', text)
                for sentence in sentences:
                    if keyword in sentence:
                        insights.append(Insight(
                            insight_type="best_practice",
                            content=sentence.strip(),
                            confidence=0.7,
                        ))
                        break
        
        return insights

