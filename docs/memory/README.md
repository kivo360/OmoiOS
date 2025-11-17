# Memory & Learning System

**Phase 5 Feature** — Pattern recognition and context retrieval from task execution history.

## Overview

The Memory System provides:
- **Task Execution Storage** — Records task summaries with embeddings
- **Similarity Search** — Finds similar past tasks using vector search
- **Pattern Learning** — Automatically extracts success/failure patterns
- **Context Suggestions** — Recommends context for new tasks based on history

## Architecture

### Components

1. **EmbeddingService** (`omoi_os/services/embedding.py`)
   - Generates 1536-dimensional embeddings
   - Supports OpenAI API and local sentence-transformers
   - Configurable via `EMBEDDING_PROVIDER` environment variable

2. **MemoryService** (`omoi_os/services/memory.py`)
   - Stores task executions with embeddings
   - Searches for similar tasks using cosine similarity
   - Extracts and matches learned patterns

3. **Models**
   - `TaskMemory` — Execution history with embeddings
   - `LearnedPattern` — Pattern templates for matching

### Database Schema

```sql
-- Task execution memories
CREATE TABLE task_memories (
    id VARCHAR PRIMARY KEY,
    task_id VARCHAR REFERENCES tasks(id),
    execution_summary TEXT,
    context_embedding FLOAT[],  -- 1536 dimensions
    success BOOLEAN,
    error_patterns JSONB,
    learned_at TIMESTAMP WITH TIME ZONE,
    reused_count INTEGER DEFAULT 0
);

-- Learned patterns
CREATE TABLE learned_patterns (
    id VARCHAR PRIMARY KEY,
    pattern_type VARCHAR(50),  -- success, failure, optimization
    task_type_pattern VARCHAR,  -- Regex for matching
    success_indicators JSONB,
    failure_indicators JSONB,
    recommended_context JSONB,
    embedding FLOAT[],  -- 1536 dimensions
    confidence_score FLOAT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

## Configuration

### Environment Variables

```bash
# Embedding provider (openai or local)
EMBEDDING_PROVIDER=local

# OpenAI API key (required if using openai provider)
OPENAI_API_KEY=sk-...

# Database connection (already configured)
DATABASE_URL=postgresql+psycopg://...
```

### Embedding Providers

#### Local (Development)
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384 (padded to 1536)
- **Cost**: Free
- **Quality**: Good for development

```python
from omoi_os.services.embedding import EmbeddingService, EmbeddingProvider

service = EmbeddingService(provider=EmbeddingProvider.LOCAL)
```

#### OpenAI (Production)
- **Model**: `text-embedding-3-small`
- **Dimensions**: 1536
- **Cost**: $0.00002 per 1K tokens
- **Quality**: High accuracy

```python
service = EmbeddingService(
    provider=EmbeddingProvider.OPENAI,
    openai_api_key="sk-..."
)
```

## Usage

### Storing Task Execution

```python
from omoi_os.services.memory import MemoryService
from omoi_os.services.embedding import EmbeddingService

# Initialize services
embedding_service = EmbeddingService()
memory_service = MemoryService(embedding_service)

# Store execution
with db.get_session() as session:
    memory = memory_service.store_execution(
        session=session,
        task_id="task-123",
        execution_summary="Successfully implemented JWT authentication with Redis",
        success=True,
        auto_extract_patterns=True
    )
    session.commit()
```

### Searching Similar Tasks

```python
# Search for similar past tasks
with db.get_session() as session:
    results = memory_service.search_similar(
        session=session,
        task_description="Implement OAuth2 authentication",
        top_k=5,
        similarity_threshold=0.7,
        success_only=True
    )
    
    for result in results:
        print(f"Task: {result.task_id}")
        print(f"Similarity: {result.similarity_score:.2f}")
        print(f"Summary: {result.summary}")
```

### Getting Task Context

```python
# Get context suggestions for a new task
with db.get_session() as session:
    context = memory_service.get_task_context(
        session=session,
        task_description="Implement GitHub OAuth login",
        top_k=3
    )
    
    print("Similar tasks:", context["similar_tasks"])
    print("Matching patterns:", context["matching_patterns"])
    print("Recommendations:", context["recommendations"])
```

### Extracting Patterns

```python
# Extract pattern from completed tasks
with db.get_session() as session:
    pattern = memory_service.extract_pattern(
        session=session,
        task_type_pattern=".*authentication.*",
        pattern_type="success",
        min_samples=5
    )
    
    if pattern:
        print(f"Pattern confidence: {pattern.confidence_score}")
        print(f"Success indicators: {pattern.success_indicators}")
```

## API Endpoints

### Store Execution

```bash
POST /api/v1/memory/store
Content-Type: application/json

{
  "task_id": "task-123",
  "execution_summary": "Successfully implemented feature",
  "success": true,
  "error_patterns": null,
  "auto_extract_patterns": true
}
```

### Search Similar Tasks

```bash
POST /api/v1/memory/search
Content-Type: application/json

{
  "task_description": "Implement OAuth2 authentication",
  "top_k": 5,
  "similarity_threshold": 0.7,
  "success_only": true
}
```

**Response:**
```json
[
  {
    "task_id": "task-123",
    "memory_id": "mem-456",
    "summary": "Implemented JWT auth successfully",
    "success": true,
    "similarity_score": 0.85,
    "reused_count": 3
  }
]
```

### Get Task Context

```bash
GET /api/v1/memory/tasks/{task_id}/context?top_k=3
```

**Response:**
```json
{
  "similar_tasks": [
    {
      "task_id": "task-123",
      "summary": "...",
      "similarity": 0.85
    }
  ],
  "matching_patterns": [
    {
      "pattern_id": "pat-789",
      "pattern_type": "success",
      "confidence": 0.8,
      "success_indicators": ["validated", "tested"],
      "recommended_context": {...}
    }
  ],
  "recommendations": [
    "Similar tasks have 90% success rate. Consider following similar approaches."
  ]
}
```

### List Patterns

```bash
GET /api/v1/memory/patterns?pattern_type=success&limit=10
```

### Extract Pattern

```bash
POST /api/v1/memory/patterns/extract
Content-Type: application/json

{
  "task_type_pattern": ".*authentication.*",
  "pattern_type": "success",
  "min_samples": 3
}
```

### Provide Pattern Feedback

```bash
POST /api/v1/memory/patterns/{pattern_id}/feedback
Content-Type: application/json

{
  "helpful": true,
  "confidence_adjustment": 0.1
}
```

## Integration with Quality Gates (Phase 5)

The Memory System exports a contract interface for the Quality Gates Squad:

```python
from omoi_os.models.learned_pattern import TaskPattern

# Quality Squad can search patterns
patterns = memory_service.search_patterns(
    session=session,
    task_type="implement_api",
    pattern_type="success",
    limit=5
)

# Each pattern is a TaskPattern dataclass
for pattern in patterns:
    print(f"Pattern: {pattern.pattern_id}")
    print(f"Confidence: {pattern.confidence_score}")
    print(f"Success indicators: {pattern.success_indicators}")
```

## Performance Considerations

### Vector Similarity Indexes

For production with >1000 memories, create vector indexes:

```sql
-- Create IVFFlat index (good for <1M vectors)
CREATE INDEX ON task_memories 
USING ivfflat (context_embedding vector_cosine_ops)
WITH (lists = 100);

-- Or HNSW index (better accuracy, slower writes)
CREATE INDEX ON task_memories 
USING hnsw (context_embedding vector_cosine_ops);
```

### Caching

Embeddings are computed on demand. For high-traffic scenarios:
1. Cache embeddings in Redis
2. Pre-compute embeddings for common queries
3. Use batch generation for multiple tasks

### Scaling

- Local embeddings: Fast, no API costs, lower quality
- OpenAI embeddings: Higher quality, API costs, rate limits
- Consider hybrid: Local for dev/test, OpenAI for production

## Monitoring

The Memory System publishes events:

```python
# Events published by MemoryService
"memory.stored"               # Task execution stored
"memory.pattern.learned"      # New pattern extracted
"memory.pattern.matched"      # Pattern matched a task
"memory.context.suggested"    # Context provided for task
```

Subscribe to these events for monitoring:

```python
from omoi_os.services.event_bus import EventBusService

event_bus = EventBusService()

def handle_pattern_learned(event):
    print(f"New pattern learned: {event.payload}")

event_bus.subscribe("memory.pattern.learned", handle_pattern_learned)
```

## Testing

Run memory tests:

```bash
# All memory tests
uv run pytest tests/test_memory.py tests/test_pattern_learning.py tests/test_similarity_search.py -v

# Just storage tests
uv run pytest tests/test_memory.py -v

# Just pattern tests
uv run pytest tests/test_pattern_learning.py -v

# Just similarity tests
uv run pytest tests/test_similarity_search.py -v
```

## Migration

Apply the memory migration:

```bash
# Run migration
uv run alembic upgrade head

# Verify tables created
psql $DATABASE_URL -c "\dt task_memories learned_patterns"
```

## Troubleshooting

### Embeddings Not Working

```python
# Check provider configuration
from omoi_os.services.embedding import EmbeddingService

service = EmbeddingService()
print(f"Provider: {service.provider}")
print(f"Model: {service.model_name}")

# Test embedding generation
embedding = service.generate_embedding("test")
print(f"Dimensions: {len(embedding)}")
```

### Low Similarity Scores

Local embeddings (sentence-transformers) have lower quality than OpenAI:
- Local threshold: 0.3-0.5
- OpenAI threshold: 0.7-0.8

### Pattern Extraction Failing

Requires minimum samples (default 3):
```python
# Check how many matching tasks exist
from omoi_os.models.task import Task

with db.get_session() as session:
    count = session.query(Task).filter(
        Task.description.ilike('%authentication%')
    ).count()
    print(f"Matching tasks: {count}")
```

## Future Enhancements

- [ ] Hierarchical clustering of task patterns
- [ ] Multi-modal embeddings (code + text)
- [ ] Active learning from user feedback
- [ ] Pattern evolution tracking
- [ ] Cross-ticket pattern detection

## References

- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [sentence-transformers](https://www.sbert.net/)
- [pgvector](https://github.com/pgvector/pgvector)
- Phase 5 Spec: `docs/PHASE5_PARALLEL_PLAN.md`

