# LLM Service Usage Guide

**Created**: 2025-11-20
**Status**: Active
**Purpose**: Provides usage instructions and best practices for the LLMService across API routes, services, and standalone scripts.
**Related**: docs/services/llm_service.md, docs/guides/agents/agent_executor.md, docs/configuration/llm_settings.md, docs/schemas/memory_classification.md

---


The `LLMService` provides a simple interface for calling LLMs throughout the codebase.

## Overview

The LLM service provides two main methods:
1. **Simple Text Completion** - Just get text back from the LLM
2. **Structured Outputs** - Get type-safe structured responses using Pydantic models

**Note:** This service does NOT handle workspace execution. For that, use `AgentExecutor` separately when you need to execute code in a workspace.

## Getting the Service

### In API Routes (Dependency Injection)

```python
from fastapi import Depends
from omoi_os.api.dependencies import get_llm_service
from omoi_os.services.llm_service import LLMService

@router.post("/analyze")
async def analyze_text(
    text: str,
    llm: LLMService = Depends(get_llm_service)
):
    result = await llm.complete(f"Analyze this text: {text}")
    return {"analysis": result}
```

### In Services (Direct Import)

```python
from omoi_os.services.llm_service import get_llm_service

class MyService:
    def __init__(self):
        self.llm = get_llm_service()
    
    async def do_analysis(self, prompt: str):
        return await self.llm.complete(prompt)
```

### Standalone Usage

```python
from omoi_os.services.llm_service import get_llm_service

llm = get_llm_service()
result = await llm.complete("Hello, world!")
print(result)  # Just get text back
```

## Use Cases

### 1. Simple Text Completion

```python
from omoi_os.services.llm_service import get_llm_service

llm = get_llm_service()

# Basic completion
response = await llm.complete("What is the capital of France?")

# With system prompt
response = await llm.complete(
    "Explain quantum computing",
    system_prompt="You are a helpful science teacher."
)
```

### 2. Structured Outputs

```python
from pydantic import BaseModel, Field
from omoi_os.services.llm_service import get_llm_service

class AnalysisResult(BaseModel):
    sentiment: str = Field(..., description="Sentiment: positive, negative, or neutral")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(..., description="Brief explanation")

llm = get_llm_service()

result = await llm.structured_output(
    "Analyze the sentiment of: 'I love this product!'",
    output_type=AnalysisResult,
    system_prompt="You are a sentiment analysis expert."
)

print(result.sentiment)  # "positive"
print(result.confidence)  # 0.95
print(result.reasoning)  # "The text expresses strong positive emotion..."
```

### 3. For Workspace Execution

**Note:** The LLM service does NOT handle workspace execution. For that, use `AgentExecutor` directly:

```python
from omoi_os.services.agent_executor import AgentExecutor

# Create executor for workspace operations
executor = AgentExecutor(
    phase_id="PHASE_IMPLEMENTATION",
    workspace_dir="/path/to/workspace"
)

# Execute task in workspace
result = executor.execute_task("Create a Python function")
```

## Integration Examples

### In a Service Class

```python
from omoi_os.services.llm_service import get_llm_service
from omoi_os.schemas.memory_analysis import MemoryClassification

class MyAnalysisService:
    def __init__(self):
        self.llm = get_llm_service()
    
    async def classify_text(self, text: str) -> MemoryClassification:
        """Classify text using structured output."""
        return await self.llm.structured_output(
            f"Classify this text: {text}",
            output_type=MemoryClassification,
            system_prompt="You are a text classification expert."
        )
    
    async def summarize(self, text: str) -> str:
        """Generate a summary."""
        return await self.llm.complete(
            f"Summarize this text in one paragraph: {text}",
            system_prompt="You are a summarization expert."
        )
```

### In an API Route

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from omoi_os.api.dependencies import get_llm_service
from omoi_os.services.llm_service import LLMService

router = APIRouter()

class CompletionRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None

@router.post("/complete")
async def complete(
    request: CompletionRequest,
    llm: LLMService = Depends(get_llm_service)
):
    """Simple text completion endpoint."""
    result = await llm.complete(
        request.prompt,
        system_prompt=request.system_prompt
    )
    return {"result": result}
```

## Error Handling

The service includes built-in error handling:

```python
from omoi_os.services.llm_service import get_llm_service

llm = get_llm_service()

try:
    result = await llm.structured_output(
        "Analyze this text",
        output_type=MySchema,
        output_retries=5  # Number of retries for validation
    )
except Exception as e:
    # Handle error - service will fall back to sync methods if available
    print(f"LLM call failed: {e}")
```

## Configuration

The service uses `LLMSettings` from `omoi_os.config`:

- `LLM_MODEL` - Model name (defaults to Fireworks kimi-k2-thinking)
- `LLM_API_KEY` - API key (or `FIREWORKS_API_KEY` for PydanticAI)
- `LLM_BASE_URL` - Optional base URL

## Best Practices

1. **Use structured outputs** when you need type-safe responses (memory operations, classification, etc.)
2. **Use simple completion** for free-form text generation
3. **Use AgentExecutor separately** for workspace execution - don't use this service for that
4. **Cache the service instance** - it's a singleton, so `get_llm_service()` returns the same instance
5. **Handle errors gracefully** - structured outputs may fail and fall back to sync methods

## Migration from Direct Usage

If you're currently using `PydanticAIService` directly:

### Before:
```python
from omoi_os.services.pydantic_ai_service import PydanticAIService

ai_service = PydanticAIService()
agent = ai_service.create_agent(output_type=MySchema)
result = await agent.run("prompt")
data = result.output
```

### After:
```python
from omoi_os.services.llm_service import get_llm_service

llm = get_llm_service()
data = await llm.structured_output("prompt", output_type=MySchema)
```

Much simpler! Just call the LLM and get your result back.

