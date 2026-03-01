# Part 15: LLM Service Layer

> Summary doc — OmoiOS uses a layered LLM service architecture with LLMService as the public API, PydanticAIService for structured outputs, and Fireworks.ai as the primary inference provider.

## Overview

The LLM Service Layer provides a unified interface for all AI-driven operations in OmoiOS. It abstracts model selection, provider-specific configurations, and complex structured output logic into a simple, typed API used by over 24 services across the codebase.

## Class Hierarchy

```md
LLMService (main interface)
  └── PydanticAIService (structured output implementation)
        └── PydanticAI Agent (via pydantic-ai library)
              └── OpenAIChatModel + OpenAIProvider (Fireworks.ai)
```

## Key Classes

### LLMService
**Location**: `backend/omoi_os/services/llm_service.py`

The primary entry point for LLM interactions. It is implemented as a singleton accessible via `get_llm_service()`.

- `complete(prompt, system_prompt, **kwargs) -> str`
  Simple text completion for unstructured tasks.
- `structured_output(prompt, output_type, system_prompt, output_retries=5, http_retries=3, **kwargs) -> T`
  Typed structured output with automatic retry logic. This is the most used method in the system.

### PydanticAIService
**Location**: `backend/omoi_os/services/pydantic_ai_service.py`

Internal implementation delegated to by LLMService. It leverages the `pydantic-ai` library to manage agent instances and model interactions.

- Creates PydanticAI Agent instances on demand.
- Default model: `accounts/fireworks/models/minimax-m2p1` (optimized for structured output).

## Configuration

Settings are managed via `LLMSettings` in `backend/omoi_os/config.py`:

- `model`: `openhands/claude-sonnet-4-5-20250929` (primary reasoning model).
- `fireworks_api_key`: Required for structured outputs via Fireworks.ai.
- `base_url`: Optional override for custom inference endpoints.

## structured_output Pattern

The canonical pattern for obtaining structured data from an LLM in OmoiOS:

1. **Define a Pydantic response model**:
   ```python
   class MyResponse(BaseModel):
       analysis: str
       score: float
       tags: list[str]
   ```

2. **Call the service**:
   ```python
   llm = get_llm_service()
   result = await llm.structured_output(
       prompt="Analyze this input...",
       output_type=MyResponse
   )
   ```

3. **Result**:
   Returns a typed, validated instance of `MyResponse`.

**Key Features**:
- **Automatic Retry**: Retries up to 5 times if the LLM output fails Pydantic validation.
- **HTTP Resilience**: Retries on 503, 429, 502, and 504 errors with exponential backoff and jitter.

## Response Models in Codebase

| Model | Location | Purpose |
|-------|----------|---------|
| `LLMTrajectoryAnalysisResponse` | `backend/omoi_os/models/trajectory_analysis.py` | Trajectory alignment, alignment score, steering needs |
| `LLMDuplicateAnalysisResponse` | `backend/omoi_os/services/conductor.py` | Duplicate detection, similarity score, work description |

## Consumers

The LLM service is a core dependency used by 24+ files. Key consumers include:

- `intelligent_guardian.py`: Trajectory analysis and steering.
- `conductor.py`: System-wide duplicate detection.
- `discovery_analyzer.py`: Discovery analysis for adaptive branching.
- `task_requirements_analyzer.py`: Task work type and dependency analysis.
- `quality_checker.py`: Quality metrics calculation.
- `context_summarizer.py`: Context summarization for agent handoffs.
- `validation_agent.py`: Phase gate reviews and quality checks.
- `memory.py`: Pattern extraction for long-term memory.
- `quality_predictor.py`: Quality prediction for planned work.
- `spec_acceptance_validator.py`: Acceptance criteria validation.
- `diagnostic.py`: Stuck workflow diagnosis and recovery.

## Prompt Management

Prompts are managed differently depending on the subsystem:

- **Spec-Sandbox**: Uses dedicated prompt templates in `subsystems/spec-sandbox/src/spec_sandbox/prompts/phases.py`.
- **Phases**: 6 core phase prompts (EXPLORE, PRD, REQUIREMENTS, DESIGN, TASKS, SYNC).
- **Access**: Accessed via `get_phase_prompt(SpecPhase.EXPLORE)`.
- **Output**: Each phase prompt is designed to produce structured JSON output compatible with the phase evaluators.

## EmbeddingService

**Location**: `backend/omoi_os/services/embedding.py`

Provides text embedding capabilities used for similarity search and deduplication.

- **Providers**: Supports Fireworks, OpenAI, and FastEmbed.
- **Usage**: Powers `task_dedup`, `spec_dedup`, `ticket_dedup`, and memory services.
- **Storage**: Integrates with `pgvector` for efficient similarity search in PostgreSQL.

## Key Files

| File | Purpose |
|------|---------|
| `backend/omoi_os/services/llm_service.py` | Public API and singleton provider |
| `backend/omoi_os/services/pydantic_ai_service.py` | Structured output implementation |
| `backend/omoi_os/services/embedding.py` | Text embedding service |
| `backend/omoi_os/config.py` | LLM and Embedding configuration |
| `subsystems/spec-sandbox/src/spec_sandbox/prompts/phases.py` | Spec-Sandbox phase prompts |

## Detailed Documentation

For implementation details and usage guides, see:
- [LLM Service Guide](../design/services/llm_service_guide.md)
