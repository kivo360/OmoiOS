"""Executor service for ACE workflow (REQ-MEM-ACE-001)."""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session

from omoi_os.models.task import Task
from omoi_os.models.task_memory import TaskMemory
from omoi_os.services.embedding import EmbeddingService
from omoi_os.services.memory import MemoryService
from omoi_os.utils.datetime import utc_now


@dataclass
class ToolUsage:
    """Tool usage record (REQ-MEM-ACE-001)."""
    
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None


@dataclass
class ExecutorResult:
    """Result from Executor phase (REQ-MEM-ACE-001)."""
    
    memory_id: str
    memory_type: str
    files_linked: List[str]
    tags: List[str]


class Executor:
    """
    Executor service for ACE workflow (REQ-MEM-ACE-001).
    
    Responsibilities:
    - Parse tool_usage to extract file paths and classify relations
    - Classify memory_type based on goal and result
    - Generate embeddings for content
    - Create memory record
    - Link memory to relevant files
    """
    
    def __init__(
        self,
        memory_service: MemoryService,
        embedding_service: EmbeddingService,
    ):
        """
        Initialize Executor service.
        
        Args:
            memory_service: Memory service for creating memories
            embedding_service: Embedding service for generating vectors
        """
        self.memory_service = memory_service
        self.embedding_service = embedding_service
    
    def execute(
        self,
        session: Session,
        task_id: str,
        goal: str,
        result: str,
        tool_usage: List[Dict[str, Any]],
        feedback: Optional[str] = None,
    ) -> ExecutorResult:
        """
        Execute phase: create memory from task completion (REQ-MEM-ACE-001).
        
        Steps:
        1. Parse tool_usage to extract file paths
        2. Classify memory_type
        3. Generate embedding
        4. Create memory record
        5. Link to files (if file tracking implemented)
        
        Args:
            session: Database session
            task_id: Task ID
            goal: What the agent was trying to accomplish
            result: What actually happened
            tool_usage: List of tool usage records
            feedback: Optional feedback from environment
            
        Returns:
            ExecutorResult with memory_id, memory_type, files_linked, tags
        """
        # Verify task exists
        task = session.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Parse tool usage to extract file paths (REQ-MEM-ACE-001)
        files_linked = self.extract_file_paths(tool_usage)
        
        # Classify memory type based on goal and result (REQ-MEM-ACE-001)
        memory_type = self.memory_service.classify_memory_type(
            execution_summary=f"{goal}\n\nResult: {result}",
            task_description=task.description,
        )
        
        # Generate content for embedding
        content = f"{goal}\n\nResult: {result}"
        if feedback:
            content += f"\n\nFeedback: {feedback}"
        
        # Generate embedding (REQ-MEM-ACE-001)
        embedding = self.embedding_service.generate_embedding(content)
        
        # Create memory record (REQ-MEM-ACE-001)
        memory = TaskMemory(
            task_id=task_id,
            execution_summary=content,
            memory_type=memory_type,
            goal=goal,
            result=result,
            feedback=feedback,
            tool_usage={"tools": tool_usage},  # Store as JSONB
            context_embedding=embedding,
            success=True,  # Will be updated based on feedback if needed
            learned_at=utc_now(),
            reused_count=0,
        )
        
        session.add(memory)
        session.flush()
        
        # Extract tags from goal and result
        tags = self.extract_tags(goal, result)
        
        return ExecutorResult(
            memory_id=memory.id,
            memory_type=memory_type,
            files_linked=files_linked,
            tags=tags,
        )
    
    def extract_file_paths(self, tool_usage: List[Dict[str, Any]]) -> List[str]:
        """
        Extract file paths from tool usage (REQ-MEM-ACE-001).
        
        Parses tool usage to find file paths from operations like:
        - file_read: reads file paths from arguments
        - file_edit: reads file paths from arguments
        - file_create: reads file paths from arguments
        
        Args:
            tool_usage: List of tool usage dictionaries
            
        Returns:
            List of unique file paths
        """
        files = set()
        
        for tool in tool_usage:
            tool_name = tool.get("tool_name", "").lower()
            arguments = tool.get("arguments", {})
            
            # Extract file paths based on tool type
            if tool_name in ["file_read", "file_edit", "file_create", "read_file", "write_file", "edit_file"]:
                file_path = arguments.get("path") or arguments.get("file_path") or arguments.get("file")
                if file_path:
                    files.add(str(file_path))
        
        return sorted(list(files))
    
    def extract_tags(self, goal: str, result: str) -> List[str]:
        """
        Extract tags from goal and result.
        
        Simple keyword-based tag extraction. In a full implementation,
        this could use LLM-based extraction or more sophisticated NLP.
        
        Args:
            goal: Task goal
            result: Task result
            
        Returns:
            List of extracted tags
        """
        tags = []
        text = (goal + " " + result).lower()
        
        # Extract common patterns as tags
        common_tags = {
            "authentication": ["auth", "login", "jwt", "oauth"],
            "database": ["db", "sql", "postgres", "mysql", "database"],
            "api": ["api", "endpoint", "rest", "graphql"],
            "testing": ["test", "pytest", "unit", "integration"],
            "frontend": ["react", "vue", "angular", "ui", "frontend"],
            "backend": ["backend", "server", "api"],
        }
        
        for tag, keywords in common_tags.items():
            if any(keyword in text for keyword in keywords):
                tags.append(tag)
        
        return tags

