# Memory System Comparison: Hephaestus vs OmoiOS

**Created**: 2025-01-30  
**Status**: Analysis Document  
**Purpose**: Compare Hephaestus Memory System (RAG) with OmoiOS's existing memory implementation

---

## Executive Summary

OmoiOS has a **sophisticated memory system** (`MemoryService`) that implements many core RAG concepts, including semantic search, memory type taxonomy, and pattern learning. However, Hephaestus provides a **two-tier retrieval architecture** (pre-loaded context + dynamic search) and **MCP tool integration** (`save_memory`, `qdrant_find`) that could significantly enhance OmoiOS's agent experience. Key gaps include: dual storage (SQLite + Qdrant), agent-accessible MCP tools, pre-loaded context at agent spawn, and deduplication.

---

## Architecture Comparison

### Storage Architecture

#### Hephaestus: Dual Storage System
- **SQLite**: Metadata (memory ID, type, agent ID, task ID, tags, related files, timestamp)
- **Qdrant**: Vector embeddings (3072-dim using OpenAI text-embedding-3-large)
- **Separation**: Metadata in SQLite, embeddings in Qdrant for optimal performance

#### OmoiOS: Single Storage System
- **PostgreSQL**: Both metadata AND embeddings stored together
- **Embeddings**: 1536-dim using OpenAI text-embedding-3-small (or local multilingual-e5-large padded to 1536)
- **Storage**: `context_embedding` stored as PostgreSQL ARRAY in `TaskMemory` table

**Gap**: OmoiOS stores everything in PostgreSQL, which works but may not scale as well as dedicated vector DB for large memory sets.

---

## Retrieval Architecture

### Hephaestus: Two-Tier System

#### Tier 1: Pre-loaded Context (80% of needs)
- **When**: At agent spawn time
- **Process**: RAG retrieves top 20 most relevant memories based on task description similarity
- **Delivery**: Embedded in agent's initial system prompt
- **Performance**: Fast, no API calls during execution
- **Coverage**: Covers most common scenarios

#### Tier 2: Dynamic Search (20% of needs)
- **When**: During agent execution via MCP tool
- **Tool**: `qdrant_find(query, limit=5)` via MCP
- **Use Case**: Specific errors, edge cases, deep dives
- **Performance**: Real-time semantic search (~1-2 seconds)

### OmoiOS: Single-Tier System

#### Current Approach
- **When**: At task creation time via `get_task_context()`
- **Process**: `MemoryService.search_similar()` finds top 3-5 similar tasks
- **Delivery**: Context suggestions provided to task enrichment
- **Limitation**: No agent-accessible search tool during execution
- **Coverage**: Limited to initial context, no dynamic retrieval

**Gap**: OmoiOS doesn't provide agents with tools to search memory during execution. Agents can't dynamically retrieve knowledge when encountering errors or needing specific information.

---

## Memory Types Taxonomy

### Hephaestus Memory Types
1. **error_fix** - Solutions to errors
2. **discovery** - Important findings
3. **decision** - Key decisions & rationale
4. **learning** - Lessons learned
5. **warning** - Gotchas to avoid
6. **codebase_knowledge** - Code structure insights

### OmoiOS Memory Types
1. **error_fix** - Solutions to errors ✅
2. **discovery** - Important findings ✅
3. **decision** - Key decisions & rationale ✅
4. **learning** - Lessons learned ✅
5. **warning** - Gotchas to avoid ✅
6. **codebase_knowledge** - Code structure insights ✅

**Status**: ✅ **Fully aligned** - OmoiOS has identical memory type taxonomy

---

## Embedding Models

### Hephaestus
- **Model**: OpenAI `text-embedding-3-large`
- **Dimensions**: 3072
- **Context Window**: 8,191 tokens
- **Cost**: $0.00013 per 1K tokens
- **Rationale**: High dimensionality for better semantic capture, state-of-the-art quality

### OmoiOS
- **Model**: OpenAI `text-embedding-3-small` (default) or local `multilingual-e5-large`
- **Dimensions**: 1536 (OpenAI) or 1024 padded to 1536 (local)
- **Context Window**: Varies by model
- **Cost**: Lower cost with smaller model
- **Rationale**: Cost-effective, supports local development

**Gap**: OmoiOS uses smaller embeddings (1536 vs 3072), which may have lower semantic quality but is more cost-effective. This is a trade-off decision.

---

## Search Capabilities

### Hephaestus Search
- **Mode**: Semantic search via Qdrant
- **Collections**: Multiple collections (agent_memories, error_solutions, task_completions, domain_knowledge, project_context)
- **Access**: Via MCP tool `qdrant_find(query, limit)`
- **Results**: Top 5 by default with relevance scores

### OmoiOS Search
- **Mode**: Hybrid search (semantic + keyword) using RRF
- **Collections**: Single collection (task_memories table)
- **Access**: Via `MemoryService.search_similar()` API
- **Results**: Top K configurable (default 5) with similarity scores
- **Features**: 
  - Semantic search using cosine similarity
  - Keyword search using PostgreSQL tsvector
  - Hybrid search using Reciprocal Rank Fusion (RRF)
  - Filter by memory type, success status

**Status**: ✅ **OmoiOS has superior search** - Hybrid search with RRF is more sophisticated than Hephaestus's semantic-only approach.

---

## Deduplication

### Hephaestus
- **Method**: Similarity threshold check (0.95)
- **Process**: 
  1. Generate embedding for new memory
  2. Search for similar memories
  3. If score > 0.95 → Mark as duplicate, store in SQLite only
  4. If score ≤ 0.95 → Store in both SQLite and Qdrant
- **Rationale**: Prevents redundant knowledge storage, reduces vector storage costs

### OmoiOS
- **Method**: No explicit deduplication
- **Process**: All memories stored regardless of similarity
- **Gap**: OmoiOS doesn't check for duplicates before storing, which could lead to redundant memories

**Gap**: OmoiOS lacks deduplication, which could lead to storage bloat and redundant knowledge.

---

## MCP Integration

### Hephaestus: Agent-Accessible Tools

#### 1. `save_memory` Tool
```python
save_memory(
    content="Fixed CORS by adding allow_origins=['*'] to FastAPI middleware",
    agent_id="agent-123",
    memory_type="error_fix",
    tags=["cors", "fastapi", "middleware"],
    related_files=["src/main.py"]
)
```
- **Access**: Agents can save memories directly during execution
- **Use Case**: When agents discover solutions, patterns, or insights
- **Integration**: Built into agent workflow

#### 2. `qdrant_find` Tool
```python
qdrant_find(
    query="How to handle PostgreSQL connection pooling",
    limit=3
)
```
- **Access**: Agents can search memories during execution
- **Use Case**: Encountering errors, needing implementation details, finding related work
- **Integration**: Available via MCP during agent execution

### OmoiOS: No Agent-Accessible Tools
- **Current**: Memory operations are backend-only via `MemoryService`
- **Gap**: Agents cannot save memories or search memories during execution
- **Impact**: Agents can't learn from each other in real-time

**Gap**: OmoiOS lacks MCP tools for agents to interact with memory system during execution.

---

## Pre-loaded Context

### Hephaestus
- **When**: At agent spawn time
- **Process**: 
  1. Generate embedding for task description
  2. Search all collections (top 5 from each)
  3. Rerank and select top 20
  4. Embed in agent's system prompt
- **Result**: Agent starts with relevant context pre-loaded
- **Coverage**: 80% of agent needs covered upfront

### OmoiOS
- **When**: At task creation time
- **Process**: `MemoryService.get_task_context()` finds top 3 similar tasks
- **Delivery**: Context suggestions provided to task enrichment
- **Limitation**: Not embedded in agent prompt, limited to 3-5 results
- **Coverage**: Less comprehensive than Hephaestus

**Gap**: OmoiOS doesn't pre-load context into agent prompts at spawn time, and provides fewer memories (3-5 vs 20).

---

## Pattern Learning

### Hephaestus
- **Approach**: Not explicitly described in documentation
- **Focus**: Memory storage and retrieval

### OmoiOS
- **Approach**: Automatic pattern extraction from successful tasks
- **Features**:
  - `extract_pattern()` - Extract patterns from similar completed tasks
  - `find_matching_patterns()` - Find patterns matching task description
  - `LearnedPattern` model - Stores extracted patterns with confidence scores
  - Pattern embedding (average of task embeddings)
  - Confidence scoring based on sample size

**Status**: ✅ **OmoiOS has superior pattern learning** - Automatic pattern extraction is more advanced than Hephaestus.

---

## Metadata & Tags

### Hephaestus
- **Tags**: JSON array of searchable tags
- **Related Files**: JSON array of file paths
- **Extra Data**: JSON object for additional metadata
- **Agent ID**: Tracks which agent created the memory
- **Task ID**: Links memory to specific task

### OmoiOS
- **Tags**: Not implemented
- **Related Files**: Not implemented
- **Extra Data**: Not implemented (but has `error_patterns` JSONB)
- **Agent ID**: Not tracked (memory linked to task, not agent)
- **Task ID**: ✅ Linked via foreign key

**Gap**: OmoiOS lacks tags, related files, and agent tracking, which limits searchability and context.

---

## Performance Characteristics

### Hephaestus Pre-loaded Context
| Metric | Value |
|--------|-------|
| Retrieval time | ~2-3 seconds |
| API calls | 1 embedding generation |
| Cost per task | ~$0.00003 |
| Coverage | 80% of agent needs |
| Context size | Top 20 memories (~4KB) |

### Hephaestus Dynamic Search
| Metric | Value |
|--------|-------|
| Query time | ~1-2 seconds |
| API calls | 1 embedding per search |
| Cost per search | ~$0.000003 |
| Usage | 20% of agent needs |
| Results | Top 5 by default |

### OmoiOS Search
| Metric | Value |
|--------|-------|
| Query time | ~1-2 seconds (hybrid search) |
| API calls | 1 embedding generation |
| Cost per search | Lower (smaller model) |
| Usage | At task creation only |
| Results | Top 3-5 configurable |

---

## Enhancement Opportunities

### Priority 1: Agent-Accessible MCP Tools

**Action**: Create MCP tools for agents to interact with memory:

```python
# Add to omoi_os/mcp/tools/memory.py
@mcp_tool
async def save_memory(
    content: str,
    agent_id: str,
    memory_type: str,
    tags: Optional[List[str]] = None,
    related_files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Save a memory for other agents to discover."""
    # Implementation using MemoryService
```

```python
@mcp_tool
async def find_memory(
    query: str,
    limit: int = 5,
    memory_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Search memories semantically."""
    # Implementation using MemoryService.search_similar()
```

### Priority 2: Pre-loaded Context at Agent Spawn

**Action**: Enhance agent spawn to include pre-loaded memory context:

```python
# In agent executor or spawn logic
def enrich_agent_prompt_with_memories(
    task_description: str,
    memory_service: MemoryService,
    top_k: int = 20,
) -> str:
    """Pre-load relevant memories into agent prompt."""
    similar_memories = memory_service.search_similar(
        session, task_description, top_k=top_k
    )
    # Format memories and embed in system prompt
    return formatted_prompt_with_memories
```

### Priority 3: Deduplication System

**Action**: Add deduplication check before storing memories:

```python
def store_execution_with_dedup(
    self,
    session: Session,
    task_id: str,
    execution_summary: str,
    similarity_threshold: float = 0.95,
) -> Optional[TaskMemory]:
    """Store memory with deduplication check."""
    # Generate embedding
    embedding = self.embedding_service.generate_embedding(execution_summary)
    
    # Search for similar memories
    similar = self._semantic_search(
        session, execution_summary, top_k=1, 
        similarity_threshold=similarity_threshold
    )
    
    if similar and similar[0].similarity_score >= similarity_threshold:
        # Mark as duplicate, store metadata only
        return self._store_duplicate(session, task_id, execution_summary, similar[0])
    else:
        # Store normally
        return self.store_execution(session, task_id, execution_summary)
```

### Priority 4: Tags and Related Files

**Action**: Add tags and related_files fields to TaskMemory:

```python
class TaskMemory(Base):
    # ... existing fields ...
    tags: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String), nullable=True, comment="Searchable tags"
    )
    related_files: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String), nullable=True, comment="Related file paths"
    )
    agent_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("agents.id"), nullable=True, comment="Agent that created this memory"
    )
```

### Priority 5: Multiple Collections (Optional)

**Action**: Consider separate collections for different memory types:

```python
# Future enhancement: Separate collections
collections = {
    "error_fixes": "error_fix memories",
    "discoveries": "discovery memories",
    "decisions": "decision memories",
    # ... etc
}
```

**Note**: This may be overkill if single collection with filtering works well.

---

## Alignment with Product Vision

The Hephaestus memory enhancements align perfectly with OmoiOS's product vision:

1. **"Adaptive Learning"** - Pre-loaded context and dynamic search enable agents to learn from past experiences
2. **"Mutual Agent Monitoring"** - Agent-accessible memory tools enable agents to share knowledge
3. **"Self-Healing System"** - Memory system helps agents avoid repeating mistakes
4. **"Discovery-Driven"** - Agents can save discoveries for future reference

---

## Conclusion

OmoiOS has a **solid memory foundation** with sophisticated search (hybrid RRF), pattern learning, and memory type taxonomy. The main gaps are:

1. **Agent-accessible MCP tools** - Agents can't save/search memories during execution
2. **Pre-loaded context** - Agents don't start with relevant memories embedded in prompts
3. **Deduplication** - No check for duplicate memories before storage
4. **Metadata richness** - Missing tags, related files, and agent tracking

Implementing these enhancements would make OmoiOS's memory system even more powerful, enabling true collective intelligence where agents learn from each other in real-time.

---

## Related Documents

- [Product Vision](./product_vision.md) - OmoiOS product vision
- [Memory Service Implementation](../omoi_os/services/memory.py) - Current memory service code
- [Task Memory Model](../omoi_os/models/task_memory.py) - Memory database schema
