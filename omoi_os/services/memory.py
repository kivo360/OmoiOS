"""Memory service for task pattern learning and similarity search."""

import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.models.task_memory import TaskMemory
from omoi_os.models.learned_pattern import LearnedPattern, TaskPattern
from omoi_os.models.memory_type import MemoryType
from omoi_os.models.task import Task
from omoi_os.services.embedding import EmbeddingService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.pydantic_ai_service import PydanticAIService
from omoi_os.schemas.memory_analysis import MemoryClassification, PatternExtraction
from omoi_os.utils.datetime import utc_now


@dataclass
class SimilarTask:
    """Result from similarity search."""

    task_id: str
    memory_id: str
    summary: str
    success: bool
    similarity_score: float
    reused_count: int


class MemoryService:
    """
    Service for storing task execution history and learning patterns.

    Features:
    - Store task execution summaries with embeddings
    - Search for similar past tasks using vector similarity
    - Extract success/failure patterns automatically
    - Provide context suggestions for new tasks
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        event_bus: Optional[EventBusService] = None,
        ai_service: Optional[PydanticAIService] = None,
    ):
        """
        Initialize memory service.

        Args:
            embedding_service: Service for generating text embeddings.
            event_bus: Optional event bus for publishing memory events.
            ai_service: Optional PydanticAI service for structured analysis.
        """
        self.embedding_service = embedding_service
        self.event_bus = event_bus
        self.ai_service = ai_service or PydanticAIService()

    async def classify_memory_type(
        self,
        execution_summary: str,
        task_description: Optional[str] = None,
    ) -> str:
        """
        Classify memory type based on execution summary and task description (REQ-MEM-TAX-001).

        Uses PydanticAI for structured classification with confidence scoring.

        Args:
            execution_summary: Summary of task execution and results
            task_description: Optional task description for additional context

        Returns:
            Memory type string (one of MemoryType enum values)
        """
        # Create agent with structured output
        agent = self.ai_service.create_agent(
            output_type=MemoryClassification,
            system_prompt=(
                "You are a memory classification expert. Classify task execution summaries "
                "into one of these memory types:\n"
                "- error_fix: Contains fixes, errors, bugs, or issues\n"
                "- decision: Contains choices, decisions, or selections\n"
                "- learning: Contains discoveries, learnings, or realizations\n"
                "- warning: Contains warnings, gotchas, or cautions\n"
                "- codebase_knowledge: Contains architecture, structure, patterns, or design\n"
                "- discovery: Default category for other insights\n\n"
                "Provide a confidence score and brief reasoning for your classification."
            ),
        )

        # Build prompt
        prompt = f"Execution summary: {execution_summary}"
        if task_description:
            prompt += f"\nTask description: {task_description}"

        # Run classification
        result = await agent.run(prompt)
        classification = result.data

        # Validate memory type
        memory_type = classification.memory_type
        if not MemoryType.is_valid(memory_type):
            # Fallback to discovery if invalid
            return MemoryType.DISCOVERY.value

        return memory_type

    def classify_memory_type_sync(
        self,
        execution_summary: str,
        task_description: Optional[str] = None,
    ) -> str:
        """
        Synchronous wrapper for classify_memory_type (fallback to rule-based).

        Args:
            execution_summary: Summary of task execution and results
            task_description: Optional task description for additional context

        Returns:
            Memory type string (one of MemoryType enum values)
        """
        # Fallback to simple rule-based classification for sync contexts
        text = execution_summary.lower()
        if task_description:
            text = f"{text} {task_description.lower()}"

        if any(word in text for word in ["fix", "error", "bug", "issue", "bugfix"]):
            return MemoryType.ERROR_FIX.value
        elif any(word in text for word in ["chose", "decided", "selected", "choice", "decision"]):
            return MemoryType.DECISION.value
        elif any(word in text for word in ["learned", "found", "realized", "discovered", "learn"]):
            return MemoryType.LEARNING.value
        elif any(word in text for word in ["warning", "gotcha", "careful", "watch", "caution"]):
            return MemoryType.WARNING.value
        elif any(word in text for word in ["architecture", "structure", "pattern", "design", "codebase", "system"]):
            return MemoryType.CODEBASE_KNOWLEDGE.value
        else:
            return MemoryType.DISCOVERY.value

    def store_execution(
        self,
        session: Session,
        task_id: str,
        execution_summary: str,
        success: bool,
        error_patterns: Optional[Dict[str, Any]] = None,
        auto_extract_patterns: bool = True,
        memory_type: Optional[str] = None,
    ) -> TaskMemory:
        """
        Store task execution in memory with embedding and memory type classification (REQ-MEM-TAX-001).

        Args:
            session: Database session.
            task_id: Task ID to remember.
            execution_summary: Summary of what happened during execution.
            success: Whether execution was successful.
            error_patterns: Optional error patterns if failed.
            auto_extract_patterns: Whether to automatically extract patterns.
            memory_type: Optional memory type (if not provided, will be auto-classified).

        Returns:
            Created TaskMemory record.
        """
        # Verify task exists
        task = session.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Classify memory type if not provided (REQ-MEM-TAX-001)
        if memory_type is None:
            # Use sync fallback for now (can be made async in future)
            classified_type = self.classify_memory_type_sync(
                execution_summary=execution_summary,
                task_description=task.description,
            )
        else:
            # Validate provided memory type (REQ-MEM-TAX-002)
            if not MemoryType.is_valid(memory_type):
                raise ValueError(
                    f"Invalid memory_type: {memory_type}. "
                    f"Must be one of: {', '.join(MemoryType.all_types())}"
                )
            classified_type = memory_type

        # Generate embedding for the summary
        embedding = self.embedding_service.generate_embedding(execution_summary)

        # Create memory record
        memory = TaskMemory(
            task_id=task_id,
            execution_summary=execution_summary,
            memory_type=classified_type,
            context_embedding=embedding,
            success=success,
            error_patterns=error_patterns,
            learned_at=utc_now(),
            reused_count=0,
        )

        session.add(memory)
        session.flush()

        # Auto-extract patterns if enabled
        if auto_extract_patterns and success:
            self._try_extract_pattern(session, task, memory)

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="memory.stored",
                    entity_type="task_memory",
                    entity_id=str(memory.id),
                    payload={
                        "task_id": task_id,
                        "success": success,
                        "has_embedding": True,
                        "memory_type": classified_type,
                    },
                )
            )

        return memory

    def search_similar(
        self,
        session: Session,
        task_description: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        success_only: bool = False,
        memory_types: Optional[List[str]] = None,
    ) -> List[SimilarTask]:
        """
        Search for similar past tasks using embedding similarity (REQ-MEM-SEARCH-001).

        Args:
            session: Database session.
            task_description: Description of the new task.
            top_k: Number of results to return.
            similarity_threshold: Minimum similarity score (0.0 to 1.0).
            success_only: Only return successful task executions.
            memory_types: Optional list of memory types to filter by (REQ-MEM-SEARCH-005).

        Returns:
            List of similar tasks ordered by similarity.
        """
        # Generate embedding for query
        query_embedding = self.embedding_service.generate_embedding(task_description)

        # Query memories with embeddings
        query = select(TaskMemory).where(TaskMemory.context_embedding.isnot(None))

        if success_only:
            query = query.where(TaskMemory.success == True)  # noqa: E712

        # Filter by memory types if provided (REQ-MEM-SEARCH-005)
        if memory_types:
            # Validate all memory types (REQ-MEM-TAX-002)
            for mem_type in memory_types:
                if not MemoryType.is_valid(mem_type):
                    raise ValueError(
                        f"Invalid memory_type in filter: {mem_type}. "
                        f"Must be one of: {', '.join(MemoryType.all_types())}"
                    )
            query = query.where(TaskMemory.memory_type.in_(memory_types))

        memories = session.execute(query).scalars().all()

        # Calculate similarities
        results = []
        for memory in memories:
            if memory.context_embedding:
                similarity = self.embedding_service.cosine_similarity(
                    query_embedding, memory.context_embedding
                )

                if similarity >= similarity_threshold:
                    results.append(
                        SimilarTask(
                            task_id=memory.task_id,
                            memory_id=memory.id,
                            summary=memory.execution_summary,
                            success=memory.success,
                            similarity_score=similarity,
                            reused_count=memory.reused_count,
                        )
                    )

        # Sort by similarity descending
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Return top K
        top_results = results[:top_k]

        # Increment reuse counters
        for result in top_results:
            memory = session.get(TaskMemory, result.memory_id)
            if memory:
                memory.increment_reuse()

        return top_results

    def get_task_context(
        self,
        session: Session,
        task_description: str,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Get suggested context for a new task based on similar past tasks.

        Args:
            session: Database session.
            task_description: Description of the new task.
            top_k: Number of similar tasks to consider.

        Returns:
            Dictionary with context suggestions and patterns.
        """
        # Find similar tasks
        similar_tasks = self.search_similar(
            session, task_description, top_k=top_k, success_only=True
        )

        # Find matching patterns
        matching_patterns = self.find_matching_patterns(session, task_description)

        # Build context response
        context = {
            "similar_tasks": [
                {
                    "task_id": task.task_id,
                    "summary": task.summary,
                    "similarity": task.similarity_score,
                }
                for task in similar_tasks
            ],
            "matching_patterns": [
                {
                    "pattern_id": p.id,
                    "pattern_type": p.pattern_type,
                    "confidence": p.confidence_score,
                    "success_indicators": p.success_indicators,
                    "recommended_context": p.recommended_context,
                }
                for p in matching_patterns
            ],
            "recommendations": self._generate_recommendations(
                similar_tasks, matching_patterns
            ),
        }

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="memory.context.suggested",
                    entity_type="task",
                    entity_id="new",
                    payload={
                        "similar_count": len(similar_tasks),
                        "pattern_count": len(matching_patterns),
                    },
                )
            )

        return context

    def find_matching_patterns(
        self,
        session: Session,
        task_description: str,
        min_confidence: float = 0.5,
    ) -> List[LearnedPattern]:
        """
        Find learned patterns that match a task description.

        Args:
            session: Database session.
            task_description: Task description to match.
            min_confidence: Minimum confidence score.

        Returns:
            List of matching patterns.
        """
        # Get all patterns above confidence threshold
        query = select(LearnedPattern).where(
            LearnedPattern.confidence_score >= min_confidence
        )
        patterns = session.execute(query).scalars().all()

        # Filter by regex matching
        matching = []
        for pattern in patterns:
            try:
                if re.search(
                    pattern.task_type_pattern, task_description, re.IGNORECASE
                ):
                    matching.append(pattern)
                    pattern.increment_usage()
            except re.error:
                # Invalid regex, skip
                continue

        return matching

    def search_patterns(
        self,
        session: Session,
        task_type: Optional[str] = None,
        pattern_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[TaskPattern]:
        """
        Search for learned patterns (contract interface for Quality Squad).

        Args:
            session: Database session.
            task_type: Optional task type pattern to filter.
            pattern_type: Optional pattern type (success/failure/optimization).
            limit: Maximum number of patterns to return.

        Returns:
            List of TaskPattern data classes.
        """
        query = select(LearnedPattern).order_by(
            LearnedPattern.confidence_score.desc(),
            LearnedPattern.usage_count.desc(),
        )

        if pattern_type:
            query = query.where(LearnedPattern.pattern_type == pattern_type)

        if task_type:
            # Try regex match on task_type_pattern
            patterns = session.execute(query).scalars().all()
            matching = []
            for pattern in patterns:
                try:
                    if re.search(pattern.task_type_pattern, task_type, re.IGNORECASE):
                        matching.append(pattern.to_pattern())
                        if len(matching) >= limit:
                            break
                except re.error:
                    continue
            return matching
        else:
            patterns = session.execute(query.limit(limit)).scalars().all()
            return [p.to_pattern() for p in patterns]

    def extract_pattern(
        self,
        session: Session,
        task_type_pattern: str,
        pattern_type: str = "success",
        min_samples: int = 3,
    ) -> Optional[LearnedPattern]:
        """
        Extract a pattern from similar completed tasks.

        Args:
            session: Database session.
            task_type_pattern: Regex pattern for matching tasks.
            pattern_type: Type of pattern (success/failure/optimization).
            min_samples: Minimum number of samples needed to extract pattern.

        Returns:
            Extracted pattern or None if insufficient samples.
        """
        # Find matching completed tasks
        query = select(TaskMemory).where(TaskMemory.success == True)  # noqa: E712
        memories = session.execute(query).scalars().all()

        # Filter by regex
        matching_memories = []
        for memory in memories:
            task = session.get(Task, memory.task_id)
            if task and task.description:
                try:
                    if re.search(task_type_pattern, task.description, re.IGNORECASE):
                        matching_memories.append((task, memory))
                except re.error:
                    continue

        if len(matching_memories) < min_samples:
            return None

        # Extract common indicators (using sync fallback for now)
        # TODO: Make extract_pattern async to use PydanticAI
        summaries = [m[1].execution_summary for m in matching_memories if m[1].success]
        success_indicators = self._extract_indicators_fallback(summaries)

        # Generate pattern embedding (average of task embeddings)
        embeddings = [
            m[1].context_embedding for m in matching_memories if m[1].context_embedding
        ]
        pattern_embedding = self._average_embeddings(embeddings) if embeddings else None

        # Calculate confidence based on sample size and consistency
        confidence = min(1.0, len(matching_memories) / 10.0)

        # Create pattern
        pattern = LearnedPattern(
            pattern_type=pattern_type,
            task_type_pattern=task_type_pattern,
            success_indicators=success_indicators,
            failure_indicators=[],
            recommended_context={
                "source": "extracted",
                "sample_count": len(matching_memories),
            },
            embedding=pattern_embedding,
            confidence_score=confidence,
            usage_count=0,
        )

        session.add(pattern)
        session.flush()

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="memory.pattern.learned",
                    entity_type="learned_pattern",
                    entity_id=str(pattern.id),
                    payload={
                        "pattern_type": pattern_type,
                        "confidence": confidence,
                        "sample_count": len(matching_memories),
                    },
                )
            )

        return pattern

    def _try_extract_pattern(
        self,
        session: Session,
        task: Task,
        memory: TaskMemory,
    ) -> None:
        """Try to extract a pattern from successful task execution."""
        if not task.description or not memory.success:
            return

        # Simple pattern: task_type prefix
        task_type_prefix = (
            task.task_type.split("_")[0] if "_" in task.task_type else task.task_type
        )
        pattern_regex = f".*{re.escape(task_type_prefix)}.*"

        # Check if pattern already exists
        existing = session.execute(
            select(LearnedPattern).where(
                LearnedPattern.task_type_pattern == pattern_regex
            )
        ).scalar_one_or_none()

        if existing:
            # Update existing pattern
            existing.increment_usage()
        else:
            # Try to extract new pattern
            self.extract_pattern(session, pattern_regex, min_samples=2)

    async def _extract_indicators(self, summaries: List[str]) -> List[str]:
        """Extract common indicators from execution summaries using PydanticAI."""
        if not summaries:
            return []

        # Create agent for pattern extraction
        agent = self.ai_service.create_agent(
            output_type=PatternExtraction,
            system_prompt=(
                "You are a pattern extraction expert. Analyze execution summaries "
                "to identify common success and failure indicators. Extract patterns "
                "that appear across multiple summaries."
            ),
        )

        # Combine summaries for analysis
        combined_text = "\n\n".join([f"Summary {i+1}: {s}" for i, s in enumerate(summaries)])
        prompt = f"Analyze these execution summaries and extract common indicators:\n\n{combined_text}"

        try:
            result = await agent.run(prompt)
            pattern = result.data
            # Combine success and failure indicators
            all_indicators = pattern.success_indicators + pattern.failure_indicators
            return all_indicators[:10]  # Top 10
        except Exception:
            # Fallback to simple keyword extraction
            return self._extract_indicators_fallback(summaries)

    def _extract_indicators_fallback(self, summaries: List[str]) -> List[str]:
        """Fallback keyword extraction method."""
        indicators = []
        common_words = ["completed", "successful", "passed", "validated", "deployed"]

        for word in common_words:
            if (
                sum(1 for s in summaries if word.lower() in s.lower())
                >= len(summaries) // 2
            ):
                indicators.append(word)

        return indicators[:5]  # Top 5

    def _average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """Calculate average embedding vector."""
        if not embeddings:
            return []

        import numpy as np

        arr = np.array(embeddings)
        avg = np.mean(arr, axis=0)
        return avg.tolist()

    def _generate_recommendations(
        self,
        similar_tasks: List[SimilarTask],
        patterns: List[LearnedPattern],
    ) -> List[str]:
        """Generate recommendations based on similar tasks and patterns."""
        recommendations = []

        if similar_tasks:
            success_rate = sum(1 for t in similar_tasks if t.success) / len(
                similar_tasks
            )
            if success_rate > 0.8:
                recommendations.append(
                    f"Similar tasks have {success_rate * 100:.0f}% success rate. "
                    "Consider following similar approaches."
                )

        if patterns:
            high_conf_patterns = [p for p in patterns if p.confidence_score > 0.7]
            if high_conf_patterns:
                recommendations.append(
                    f"Found {len(high_conf_patterns)} high-confidence patterns. "
                    "Review success indicators for best practices."
                )

        return recommendations
