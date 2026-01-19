# Intelligent Telephony Interface Specification

**Created**: 2026-01-19
**Status**: Draft
**Purpose**: Enable developers to have natural voice conversations with AI agents for software development tasks
**Related**: docs/design/sandbox-agents/01_architecture.md, docs/design/services/llm_service_guide.md

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Requirements](#requirements)
5. [Architecture](#architecture)
6. [Data Model](#data-model)
7. [API Specification](#api-specification)
8. [Implementation Tasks](#implementation-tasks)
9. [Security Considerations](#security-considerations)
10. [Success Metrics](#success-metrics)

---

## Executive Summary

The Intelligent Telephony Interface enables developers to interact with OmoiOS AI agents through natural voice conversations. Instead of typing commands or code, developers can speak naturally to discuss architecture, debug issues, review code, and manage development tasks.

The system integrates with the existing OmoiOS multi-agent orchestration platform, leveraging:
- **Real-time WebSocket infrastructure** for signaling and events
- **LLM Service** for natural language understanding and generation
- **Agent Executor** for task execution
- **Memory Service** for conversation context preservation

Key capabilities:
- Real-time voice streaming with low latency (<500ms)
- Speech-to-text and text-to-speech with developer-optimized vocabulary
- Seamless handoff between voice and text modalities
- Multi-agent voice conferencing for complex discussions
- Voice-activated code navigation and debugging

---

## Problem Statement

### Current Pain Points

1. **Context Switching**: Developers must stop coding to type detailed prompts or commands, breaking their flow state.

2. **Complex Explanations**: Describing architectural decisions, debugging scenarios, or code review feedback is cumbersome through text.

3. **Hands-Busy Situations**: During whiteboard sessions, pair programming, or when reviewing physical documentation, typing is impractical.

4. **Accessibility**: Text-heavy interfaces exclude developers with certain disabilities or preferences.

5. **Meeting Integration**: Teams cannot seamlessly bring AI agents into voice meetings for real-time assistance.

### Opportunity

Voice interaction enables:
- **Faster context delivery**: Speaking is 3-4x faster than typing for most people
- **Natural discussion flow**: Back-and-forth technical discussions feel more natural
- **Parallel work**: Developers can code while discussing with AI agents
- **Inclusive design**: Voice provides an alternative modality for all users

---

## Goals and Non-Goals

### Goals

1. **Natural Voice Conversations**: Enable fluid, natural technical discussions with AI agents
2. **Low Latency**: Achieve <500ms response latency for voice interactions
3. **Code-Aware Context**: Maintain awareness of the current codebase and development context
4. **Multi-Modal Support**: Allow seamless switching between voice, text, and hybrid interactions
5. **Integration Ready**: Plug into existing phone systems, conferencing tools, and IDE extensions
6. **Conversation Persistence**: Record, transcribe, and make conversations searchable
7. **Multi-Agent Support**: Enable voice interactions with multiple specialized agents

### Non-Goals (Out of Scope for V1)

1. **Video Processing**: No video call or screen sharing analysis
2. **Emotion Detection**: No sentiment or emotional analysis of voice
3. **Voice Cloning**: No custom voice synthesis for agents
4. **Multi-Language Support**: English only for V1
5. **Real-time Code Execution**: Voice cannot trigger production deployments
6. **PSTN Integration**: No traditional phone network support (WebRTC/SIP only)

---

## Requirements

### Functional Requirements

#### R1: Voice Call Management
**WHEN** a developer initiates a voice call,
**THE SYSTEM SHALL** establish a bidirectional audio stream with an available AI agent within 2 seconds.

**Acceptance Criteria:**
- AC1.1: Call setup completes within 2000ms from initiation
- AC1.2: Audio quality maintains minimum 16kHz sample rate
- AC1.3: System supports hold, mute, and transfer operations
- AC1.4: Call state persists across network interruptions (reconnect within 5s)

#### R2: Speech-to-Text Processing
**WHEN** the developer speaks during an active call,
**THE SYSTEM SHALL** transcribe speech to text with >95% accuracy for technical vocabulary.

**Acceptance Criteria:**
- AC2.1: Transcription latency <300ms from end of utterance
- AC2.2: Technical terms (function names, libraries, acronyms) recognized correctly
- AC2.3: Code dictation mode available ("open bracket", "semicolon", etc.)
- AC2.4: Speaker diarization distinguishes developer from agent

#### R3: Text-to-Speech Response
**WHEN** the AI agent generates a text response,
**THE SYSTEM SHALL** synthesize natural speech and stream it to the developer.

**Acceptance Criteria:**
- AC3.1: Speech synthesis begins within 200ms of text generation start
- AC3.2: Voice sounds natural and professional (not robotic)
- AC3.3: Code snippets read with appropriate pauses and emphasis
- AC3.4: Interruptible - developer can speak to stop playback

#### R4: Conversation Context
**WHEN** a voice conversation is active,
**THE SYSTEM SHALL** maintain full context including code references, previous discussions, and current task state.

**Acceptance Criteria:**
- AC4.1: Agent recalls previous conversations from same session
- AC4.2: Code file references automatically loaded into context
- AC4.3: Context persists across call drops and reconnections
- AC4.4: Memory service integration for long-term recall

#### R5: Multi-Modal Handoff
**WHEN** a developer requests a modality switch (voice to text or vice versa),
**THE SYSTEM SHALL** transfer the conversation with full context preservation within 1 second.

**Acceptance Criteria:**
- AC5.1: Voice-to-text handoff preserves complete transcript
- AC5.2: Text-to-voice handoff reads recent context summary
- AC5.3: Active code references transfer between modalities
- AC5.4: No information loss during transition

#### R6: Agent Routing and Transfer
**WHEN** the conversation topic requires specialized expertise,
**THE SYSTEM SHALL** route or transfer the call to an appropriate agent.

**Acceptance Criteria:**
- AC6.1: Automatic agent suggestion based on conversation topic
- AC6.2: Developer can request specific agent by name/role
- AC6.3: Warm transfer includes context summary for receiving agent
- AC6.4: Conference mode allows multiple agents simultaneously

#### R7: Recording and Transcription
**WHEN** a voice call is active,
**THE SYSTEM SHALL** record, transcribe, and store the conversation for future reference.

**Acceptance Criteria:**
- AC7.1: Full audio recording with consent indicator
- AC7.2: Real-time transcript with speaker labels
- AC7.3: Searchable conversation history
- AC7.4: Privacy controls for recording opt-out

#### R8: Voice Commands
**WHEN** the developer issues a voice command (prefixed or hot-word triggered),
**THE SYSTEM SHALL** execute the corresponding action immediately.

**Acceptance Criteria:**
- AC8.1: "Hey Agent" wake word with <500ms detection
- AC8.2: Commands: navigate, search, read file, run tests, etc.
- AC8.3: Confirmation feedback for destructive actions
- AC8.4: Command history and undo support

### Non-Functional Requirements

#### NFR1: Latency
- End-to-end voice response latency: <500ms (95th percentile)
- Speech-to-text latency: <300ms
- Text-to-speech start: <200ms

#### NFR2: Availability
- 99.9% uptime for voice services
- Graceful degradation to text on voice service failure

#### NFR3: Scalability
- Support 1000 concurrent voice sessions
- Horizontal scaling for transcription and synthesis

#### NFR4: Security
- End-to-end encryption for audio streams (SRTP)
- Authentication required for all calls
- Rate limiting to prevent abuse

#### NFR5: Compliance
- GDPR-compliant recording and storage
- SOC2 Type II controls for voice data

---

## Architecture

### High-Level Architecture

```
                                    ┌─────────────────────────────────────┐
                                    │           CLIENT LAYER              │
                                    │                                     │
                                    │  ┌───────────┐    ┌───────────┐    │
                                    │  │  Web App  │    │    IDE    │    │
                                    │  │ (WebRTC)  │    │ Extension │    │
                                    │  └─────┬─────┘    └─────┬─────┘    │
                                    │        │                │          │
                                    │        └───────┬────────┘          │
                                    │                │                   │
                                    └────────────────┼───────────────────┘
                                                     │
                                    ┌────────────────┼───────────────────┐
                                    │                ▼                   │
                                    │  ┌─────────────────────────────┐   │
                                    │  │     Media Gateway Layer     │   │
                                    │  │                             │   │
                                    │  │  ┌─────────┐  ┌─────────┐   │   │
                                    │  │  │ Twilio  │  │  Vonage │   │   │
                                    │  │  │ Voice   │  │  Voice  │   │   │
                                    │  │  └────┬────┘  └────┬────┘   │   │
                                    │  │       │            │        │   │
                                    │  │       └─────┬──────┘        │   │
                                    │  │             │               │   │
                                    │  └─────────────┼───────────────┘   │
                                    │                │                   │
                                    │                ▼                   │
                                    │  ┌─────────────────────────────┐   │
                                    │  │     Voice Processing        │   │
                                    │  │                             │   │
                                    │  │  ┌─────────────────────┐    │   │
                                    │  │  │ Speech-to-Text      │    │   │
                                    │  │  │ (Deepgram/Whisper)  │    │   │
                                    │  │  └──────────┬──────────┘    │   │
                                    │  │             │               │   │
                                    │  │  ┌─────────────────────┐    │   │
                                    │  │  │ Text-to-Speech      │    │   │
                                    │  │  │ (ElevenLabs/Azure)  │    │   │
                                    │  │  └──────────┬──────────┘    │   │
                                    │  │             │               │   │
                                    │  └─────────────┼───────────────┘   │
                                    │                │                   │
                                    │     TELEPHONY  │  LAYER            │
                                    └────────────────┼───────────────────┘
                                                     │
                                    ┌────────────────┼───────────────────┐
                                    │                ▼                   │
                                    │  ┌─────────────────────────────┐   │
                                    │  │    FastAPI Backend          │   │
                                    │  │                             │   │
                                    │  │  ┌───────────────────────┐  │   │
                                    │  │  │ Telephony Service     │  │   │
                                    │  │  │  - Call management    │  │   │
                                    │  │  │  - Session state      │  │   │
                                    │  │  │  - Agent routing      │  │   │
                                    │  │  └───────────┬───────────┘  │   │
                                    │  │              │              │   │
                                    │  │  ┌───────────┴───────────┐  │   │
                                    │  │  │                       │  │   │
                                    │  │  ▼                       ▼  │   │
                                    │  │┌─────────────┐ ┌───────────┐│   │
                                    │  ││ LLM Service │ │   Agent   ││   │
                                    │  ││             │ │  Executor ││   │
                                    │  │└─────────────┘ └───────────┘│   │
                                    │  │                             │   │
                                    │  └─────────────────────────────┘   │
                                    │                                    │
                                    │       ORCHESTRATION LAYER          │
                                    └────────────────────────────────────┘
                                                     │
                                    ┌────────────────┼───────────────────┐
                                    │                ▼                   │
                                    │  ┌────────────────────────────┐    │
                                    │  │      Data Layer            │    │
                                    │  │                            │    │
                                    │  │  ┌──────┐  ┌──────┐  ┌────┴┐   │
                                    │  │  │Postgr│  │Redis │  │S3/  │   │
                                    │  │  │ SQL  │  │      │  │Blob │   │
                                    │  │  └──────┘  └──────┘  └─────┘   │
                                    │  │   Calls     Events   Audio     │
                                    │  │  Transcr.   State   Recordings │
                                    │  │                                │
                                    │  └────────────────────────────────┘
                                    │                                    │
                                    │          DATA LAYER                │
                                    └────────────────────────────────────┘
```

### Component Descriptions

#### 1. Media Gateway Layer
Handles real-time voice communication using industry-standard protocols.

**Recommended Provider**: Twilio Voice (primary) with Vonage as backup

**Responsibilities:**
- WebRTC/SIP endpoint management
- Audio codec negotiation (Opus preferred)
- NAT traversal (TURN/STUN)
- Call quality monitoring (MOS scores)

#### 2. Voice Processing Layer
Converts between speech and text using AI models.

**Speech-to-Text Options:**
| Provider | Latency | Accuracy | Cost | Recommendation |
|----------|---------|----------|------|----------------|
| Deepgram | <300ms | 95%+ | $0.0043/min | Primary |
| OpenAI Whisper | <500ms | 97%+ | $0.006/min | Backup |
| AssemblyAI | <400ms | 95%+ | $0.0025/min | Cost-effective |

**Text-to-Speech Options:**
| Provider | Latency | Naturalness | Cost | Recommendation |
|----------|---------|-------------|------|----------------|
| ElevenLabs | <200ms | Excellent | $0.30/1K chars | Primary |
| Azure Neural TTS | <150ms | Good | $0.016/1K chars | Cost-effective |
| OpenAI TTS | <250ms | Very Good | $0.015/1K chars | Backup |

#### 3. Telephony Service
Core service managing call lifecycle and agent interactions.

```python
class TelephonyService:
    """Manages voice call lifecycle and agent interactions."""

    async def initiate_call(
        self,
        user_id: str,
        agent_type: str = "general",
        context: CallContext | None = None
    ) -> Call:
        """Start a new voice call with an AI agent."""

    async def handle_speech(
        self,
        call_id: str,
        audio_chunk: bytes,
        is_final: bool = False
    ) -> TranscriptionResult:
        """Process incoming speech audio."""

    async def generate_response(
        self,
        call_id: str,
        transcript: str
    ) -> AsyncGenerator[bytes, None]:
        """Generate and stream TTS response."""

    async def transfer_call(
        self,
        call_id: str,
        target_agent_id: str,
        warm: bool = True
    ) -> TransferResult:
        """Transfer call to another agent."""

    async def end_call(
        self,
        call_id: str,
        reason: str = "user_hangup"
    ) -> CallSummary:
        """End call and generate summary."""
```

#### 4. Integration Points

**Existing OmoiOS Services:**
- `LLMService`: Natural language understanding and response generation
- `AgentExecutor`: Task execution when voice commands trigger actions
- `EventBusService`: Real-time event broadcasting for call state
- `MemoryService`: Conversation context and long-term recall
- `CollaborationService`: Multi-agent voice conferences

---

## Data Model

### Database Schema

```sql
-- Voice call sessions
CREATE TABLE voice_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    agent_id UUID REFERENCES agents(id),

    -- Call metadata
    status VARCHAR(50) NOT NULL DEFAULT 'initiating',
    -- initiating, ringing, connected, on_hold, transferring, ended

    started_at TIMESTAMPTZ,
    connected_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,

    -- Call configuration
    config JSONB NOT NULL DEFAULT '{}',
    -- {
    --   "record": true,
    --   "transcribe": true,
    --   "language": "en-US",
    --   "voice_id": "alloy"
    -- }

    -- Quality metrics
    quality_metrics JSONB,
    -- {
    --   "avg_latency_ms": 245,
    --   "packet_loss_pct": 0.1,
    --   "mos_score": 4.2
    -- }

    -- Context
    context JSONB,
    -- {
    --   "task_id": "...",
    --   "ticket_id": "...",
    --   "workspace_path": "...",
    --   "initial_prompt": "..."
    -- }

    ended_reason VARCHAR(100),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_voice_calls_user_id ON voice_calls(user_id);
CREATE INDEX idx_voice_calls_status ON voice_calls(status);
CREATE INDEX idx_voice_calls_agent_id ON voice_calls(agent_id);

-- Call transcripts (real-time and final)
CREATE TABLE call_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID NOT NULL REFERENCES voice_calls(id) ON DELETE CASCADE,

    speaker VARCHAR(50) NOT NULL, -- 'user', 'agent', 'system'
    content TEXT NOT NULL,

    -- Timing
    started_at_ms INTEGER NOT NULL, -- Offset from call start
    ended_at_ms INTEGER,
    duration_ms INTEGER,

    -- Confidence and processing
    confidence FLOAT,
    is_final BOOLEAN NOT NULL DEFAULT false,

    -- For agent responses
    llm_tokens_used INTEGER,
    llm_model VARCHAR(100),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_call_transcripts_call_id ON call_transcripts(call_id);
CREATE INDEX idx_call_transcripts_content_gin ON call_transcripts USING gin(to_tsvector('english', content));

-- Call recordings (references to blob storage)
CREATE TABLE call_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID NOT NULL REFERENCES voice_calls(id) ON DELETE CASCADE,

    storage_provider VARCHAR(50) NOT NULL, -- 's3', 'azure_blob', 'gcs'
    storage_path TEXT NOT NULL,

    format VARCHAR(20) NOT NULL DEFAULT 'wav', -- wav, mp3, ogg
    sample_rate INTEGER NOT NULL DEFAULT 16000,
    channels INTEGER NOT NULL DEFAULT 1,
    duration_seconds INTEGER,
    size_bytes BIGINT,

    -- Encryption
    encrypted BOOLEAN NOT NULL DEFAULT true,
    encryption_key_id VARCHAR(100),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Call events (for audit and debugging)
CREATE TABLE call_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID NOT NULL REFERENCES voice_calls(id) ON DELETE CASCADE,

    event_type VARCHAR(100) NOT NULL,
    -- call_initiated, call_connected, speech_started, speech_ended,
    -- transcription_received, response_generated, tts_started, tts_ended,
    -- call_transferred, call_ended, error_occurred

    payload JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_call_events_call_id ON call_events(call_id);
CREATE INDEX idx_call_events_type ON call_events(event_type);

-- Voice preferences per user
CREATE TABLE voice_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id),

    -- TTS preferences
    preferred_voice_id VARCHAR(100) DEFAULT 'alloy',
    speech_rate FLOAT DEFAULT 1.0, -- 0.5 to 2.0

    -- STT preferences
    vocabulary_boost JSONB, -- ["kubernetes", "pytest", "asyncio"]

    -- Behavior
    auto_record BOOLEAN DEFAULT true,
    wake_word_enabled BOOLEAN DEFAULT true,
    confirmation_for_actions BOOLEAN DEFAULT true,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Pydantic Models

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID

class CallStatus(str, Enum):
    INITIATING = "initiating"
    RINGING = "ringing"
    CONNECTED = "connected"
    ON_HOLD = "on_hold"
    TRANSFERRING = "transferring"
    ENDED = "ended"

class Speaker(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"

class CallConfig(BaseModel):
    record: bool = True
    transcribe: bool = True
    language: str = "en-US"
    voice_id: str = "alloy"
    agent_type: str = "general"

class CallContext(BaseModel):
    task_id: UUID | None = None
    ticket_id: UUID | None = None
    workspace_path: str | None = None
    initial_prompt: str | None = None
    code_files: list[str] = Field(default_factory=list)

class QualityMetrics(BaseModel):
    avg_latency_ms: float
    packet_loss_pct: float
    mos_score: float  # Mean Opinion Score (1-5)
    jitter_ms: float

class VoiceCall(BaseModel):
    id: UUID
    user_id: UUID
    agent_id: UUID | None
    status: CallStatus
    started_at: datetime | None
    connected_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    config: CallConfig
    quality_metrics: QualityMetrics | None
    context: CallContext | None
    ended_reason: str | None

class TranscriptSegment(BaseModel):
    id: UUID
    call_id: UUID
    speaker: Speaker
    content: str
    started_at_ms: int
    ended_at_ms: int | None
    duration_ms: int | None
    confidence: float | None
    is_final: bool

class CallEvent(BaseModel):
    id: UUID
    call_id: UUID
    event_type: str
    payload: dict | None
    created_at: datetime

class VoiceCommand(BaseModel):
    """Parsed voice command from user speech."""
    command: str  # navigate, search, read, run, etc.
    target: str | None  # file path, search query, etc.
    parameters: dict = Field(default_factory=dict)
    confidence: float
```

---

## API Specification

### REST Endpoints

#### Call Management

```yaml
/api/v1/voice/calls:
  post:
    summary: Initiate a new voice call
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              agent_type:
                type: string
                default: general
              config:
                $ref: '#/components/schemas/CallConfig'
              context:
                $ref: '#/components/schemas/CallContext'
    responses:
      201:
        description: Call initiated
        content:
          application/json:
            schema:
              type: object
              properties:
                call_id:
                  type: string
                  format: uuid
                websocket_url:
                  type: string
                ice_servers:
                  type: array

/api/v1/voice/calls/{call_id}:
  get:
    summary: Get call details
    responses:
      200:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/VoiceCall'

  delete:
    summary: End a call
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              reason:
                type: string

/api/v1/voice/calls/{call_id}/transfer:
  post:
    summary: Transfer call to another agent
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              target_agent_id:
                type: string
                format: uuid
              warm:
                type: boolean
                default: true
              context_summary:
                type: string

/api/v1/voice/calls/{call_id}/hold:
  post:
    summary: Put call on hold

  delete:
    summary: Resume call from hold

/api/v1/voice/calls/{call_id}/transcript:
  get:
    summary: Get call transcript
    parameters:
      - name: format
        in: query
        schema:
          type: string
          enum: [json, text, srt]
    responses:
      200:
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/components/schemas/TranscriptSegment'
```

#### Recording Management

```yaml
/api/v1/voice/calls/{call_id}/recording:
  get:
    summary: Get recording metadata
    responses:
      200:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CallRecording'

  delete:
    summary: Delete recording (GDPR compliance)

/api/v1/voice/calls/{call_id}/recording/download:
  get:
    summary: Get signed URL for recording download
    responses:
      200:
        content:
          application/json:
            schema:
              type: object
              properties:
                url:
                  type: string
                expires_at:
                  type: string
                  format: date-time
```

#### User Preferences

```yaml
/api/v1/voice/preferences:
  get:
    summary: Get user's voice preferences

  put:
    summary: Update voice preferences
    requestBody:
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/VoicePreferences'
```

### WebSocket Protocol

```yaml
/api/v1/ws/voice/{call_id}:
  description: Real-time voice communication channel

  # Client -> Server messages
  client_messages:
    audio_chunk:
      type: object
      properties:
        type: { const: "audio" }
        data: { type: string, format: base64 }
        sequence: { type: integer }
        is_final: { type: boolean }

    command:
      type: object
      properties:
        type: { const: "command" }
        action: { type: string, enum: [mute, unmute, hold, resume, end] }

    text_input:
      type: object
      properties:
        type: { const: "text" }
        content: { type: string }

  # Server -> Client messages
  server_messages:
    audio_response:
      type: object
      properties:
        type: { const: "audio" }
        data: { type: string, format: base64 }
        sequence: { type: integer }

    transcription:
      type: object
      properties:
        type: { const: "transcription" }
        speaker: { type: string }
        content: { type: string }
        is_final: { type: boolean }
        confidence: { type: number }

    agent_thinking:
      type: object
      properties:
        type: { const: "thinking" }
        status: { type: string }

    call_state:
      type: object
      properties:
        type: { const: "state" }
        status: { $ref: '#/components/schemas/CallStatus' }
        agent_id: { type: string }

    error:
      type: object
      properties:
        type: { const: "error" }
        code: { type: string }
        message: { type: string }
```

### Event Bus Events

```python
# Events published to Redis for system-wide consumption

VOICE_CALL_INITIATED = "VOICE_CALL_INITIATED"
# payload: { call_id, user_id, agent_type }

VOICE_CALL_CONNECTED = "VOICE_CALL_CONNECTED"
# payload: { call_id, user_id, agent_id, connected_at }

VOICE_SPEECH_DETECTED = "VOICE_SPEECH_DETECTED"
# payload: { call_id, speaker, started_at_ms }

VOICE_TRANSCRIPTION_READY = "VOICE_TRANSCRIPTION_READY"
# payload: { call_id, speaker, content, is_final, confidence }

VOICE_RESPONSE_STARTED = "VOICE_RESPONSE_STARTED"
# payload: { call_id, agent_id }

VOICE_RESPONSE_COMPLETED = "VOICE_RESPONSE_COMPLETED"
# payload: { call_id, agent_id, duration_ms, tokens_used }

VOICE_CALL_TRANSFERRED = "VOICE_CALL_TRANSFERRED"
# payload: { call_id, from_agent_id, to_agent_id, warm }

VOICE_CALL_ENDED = "VOICE_CALL_ENDED"
# payload: { call_id, reason, duration_seconds, summary }

VOICE_COMMAND_EXECUTED = "VOICE_COMMAND_EXECUTED"
# payload: { call_id, command, result }
```

---

## Implementation Tasks

### Phase 1: Core Infrastructure (Foundation)

| Task | Description | Priority | Estimate |
|------|-------------|----------|----------|
| T1.1 | Create database migrations for voice tables | P0 | 2h |
| T1.2 | Implement VoiceCall Pydantic models and schemas | P0 | 2h |
| T1.3 | Set up Twilio Voice SDK integration | P0 | 4h |
| T1.4 | Implement basic TelephonyService class | P0 | 6h |
| T1.5 | Create WebSocket endpoint for voice streaming | P0 | 4h |
| T1.6 | Add voice event types to EventBusService | P0 | 2h |

### Phase 2: Speech Processing

| Task | Description | Priority | Estimate |
|------|-------------|----------|----------|
| T2.1 | Integrate Deepgram STT with streaming support | P0 | 4h |
| T2.2 | Integrate ElevenLabs TTS with streaming | P0 | 4h |
| T2.3 | Implement audio chunk buffering and sequencing | P0 | 3h |
| T2.4 | Add technical vocabulary boosting for STT | P1 | 2h |
| T2.5 | Implement interruption detection | P1 | 3h |

### Phase 3: Agent Integration

| Task | Description | Priority | Estimate |
|------|-------------|----------|----------|
| T3.1 | Connect TelephonyService to LLMService | P0 | 3h |
| T3.2 | Implement conversation context management | P0 | 4h |
| T3.3 | Add agent routing logic | P1 | 4h |
| T3.4 | Implement warm transfer with context summary | P1 | 3h |
| T3.5 | Integrate with MemoryService for long-term recall | P2 | 4h |

### Phase 4: Recording and Transcription

| Task | Description | Priority | Estimate |
|------|-------------|----------|----------|
| T4.1 | Implement call recording to S3/Blob storage | P1 | 4h |
| T4.2 | Build transcript storage and retrieval | P1 | 3h |
| T4.3 | Add full-text search for transcripts | P2 | 3h |
| T4.4 | Implement GDPR deletion endpoints | P1 | 2h |

### Phase 5: Voice Commands

| Task | Description | Priority | Estimate |
|------|-------------|----------|----------|
| T5.1 | Implement voice command parser | P1 | 4h |
| T5.2 | Add wake word detection ("Hey Agent") | P2 | 4h |
| T5.3 | Build command execution pipeline | P1 | 4h |
| T5.4 | Integrate with existing agent tools | P1 | 3h |

### Phase 6: Frontend Integration

| Task | Description | Priority | Estimate |
|------|-------------|----------|----------|
| T6.1 | Create VoiceCallProvider React context | P0 | 4h |
| T6.2 | Build call control UI components | P0 | 6h |
| T6.3 | Implement real-time transcript display | P1 | 4h |
| T6.4 | Add call history view | P2 | 3h |
| T6.5 | Build voice preferences settings page | P2 | 2h |

### Phase 7: Quality and Monitoring

| Task | Description | Priority | Estimate |
|------|-------------|----------|----------|
| T7.1 | Implement call quality metrics collection | P1 | 3h |
| T7.2 | Add latency monitoring and alerting | P1 | 3h |
| T7.3 | Build call analytics dashboard | P2 | 4h |
| T7.4 | Implement cost tracking per call | P1 | 2h |

---

## Security Considerations

### Audio Data Protection

1. **Encryption in Transit**: All audio streams encrypted using SRTP (Secure Real-time Transport Protocol)
2. **Encryption at Rest**: Recordings encrypted using AES-256 with customer-managed keys
3. **Access Control**: JWT-based authentication required for all voice endpoints
4. **Data Retention**: Configurable retention policies with automatic deletion

### Privacy Controls

1. **Consent**: Clear recording consent indicator in UI
2. **Opt-Out**: Users can disable recording per-call or globally
3. **Deletion**: GDPR-compliant deletion within 24 hours of request
4. **Access Logs**: Full audit trail of who accessed recordings

### Rate Limiting

```python
VOICE_RATE_LIMITS = {
    "calls_per_minute": 10,
    "calls_per_hour": 100,
    "concurrent_calls": 5,
    "recording_storage_gb": 10
}
```

---

## Success Metrics

### User Experience Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Call Setup Time | <2s | 95th percentile |
| Speech-to-Text Latency | <300ms | 95th percentile |
| End-to-End Response Latency | <500ms | 95th percentile |
| Transcription Accuracy | >95% | Word error rate |
| User Satisfaction | >4.0/5.0 | Post-call survey |

### System Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Availability | 99.9% | Monthly uptime |
| Concurrent Calls | 1000 | Peak capacity |
| Call Drop Rate | <1% | Unexpected disconnections |
| Recording Success | 99.5% | Calls successfully recorded |

### Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Voice Adoption | 30% | Users trying voice in first month |
| Voice Retention | 50% | Users continuing to use after trial |
| Task Completion via Voice | 80% | Tasks completed without text fallback |
| Cost per Minute | <$0.10 | Infrastructure + API costs |

---

## Appendix

### A. Supported Voice Commands

```
Navigation:
- "Go to [file]" - Open file in editor
- "Navigate to function [name]" - Jump to function definition
- "Show me the [component]" - Display component code

Search:
- "Find [pattern]" - Search codebase
- "Search for [text] in [file]" - Search within file
- "Where is [function] used?" - Find references

Actions:
- "Run the tests" - Execute test suite
- "Build the project" - Run build command
- "Show me the errors" - Display current errors

Context:
- "What was I working on?" - Resume previous context
- "Summarize this file" - Get file overview
- "Explain this function" - Code explanation
```

### B. Integration with Existing Systems

```
┌─────────────────────────────────────────────────────────┐
│                    OmoiOS Platform                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Telephony  │◄──►│    LLM      │◄──►│   Agent     │  │
│  │   Service   │    │   Service   │    │  Executor   │  │
│  └──────┬──────┘    └─────────────┘    └─────────────┘  │
│         │                                                │
│         │           ┌─────────────┐    ┌─────────────┐  │
│         └──────────►│   Memory    │◄──►│ Collaboration│  │
│                     │   Service   │    │   Service   │  │
│                     └─────────────┘    └─────────────┘  │
│                                                          │
│         ┌─────────────────────────────────────────┐     │
│         │              Event Bus (Redis)           │     │
│         │   VOICE_* events ◄──► Existing events   │     │
│         └─────────────────────────────────────────┘     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### C. Cost Estimation

| Component | Provider | Unit Cost | Est. Monthly Usage | Monthly Cost |
|-----------|----------|-----------|-------------------|--------------|
| STT | Deepgram | $0.0043/min | 10,000 min | $43 |
| TTS | ElevenLabs | $0.30/1K chars | 5M chars | $150 |
| Media Gateway | Twilio | $0.004/min | 10,000 min | $40 |
| Recording Storage | S3 | $0.023/GB | 100 GB | $2.30 |
| LLM (responses) | Claude | $0.015/1K tokens | 2M tokens | $30 |
| **Total** | | | | **~$265/mo** |

*Based on 1000 active users, 10 min avg call duration, 1 call/user/day*
