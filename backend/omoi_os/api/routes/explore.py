"""
Code Exploration API Routes

AI-powered codebase Q&A and exploration for projects.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, ConfigDict

from omoi_os.api.dependencies import get_db_service
from omoi_os.models.explore import ExploreConversation, ExploreMessage
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


router = APIRouter(prefix="/explore", tags=["explore"])


# ============================================================================
# Pydantic Models
# ============================================================================


class Message(BaseModel):
    id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class Conversation(BaseModel):
    id: str
    project_id: str
    title: str
    last_message: Optional[str] = None
    messages: list[Message]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationSummary(BaseModel):
    id: str
    title: str
    last_message: Optional[str] = None
    timestamp: str


class ProjectFile(BaseModel):
    path: str
    type: str  # "file" or "directory"
    lines: Optional[int] = None
    description: Optional[str] = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    total_count: int


class ConversationResponse(BaseModel):
    conversation: Conversation


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    user_message: Message
    assistant_message: Message


class ProjectFilesResponse(BaseModel):
    project_id: str
    files: list[ProjectFile]
    total_count: int


class SuggestionsResponse(BaseModel):
    suggestions: list[str]


# ============================================================================
# Helper Functions
# ============================================================================


def _format_time_ago(dt: datetime) -> str:
    """Format datetime as relative time."""
    now = utc_now()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"


def _generate_ai_response(query: str, project_id: str) -> str:
    """
    Generate an AI response for the query.

    In a real implementation, this would call an LLM service.
    For now, provides contextual mock responses.
    """
    query_lower = query.lower()

    # Authentication-related queries
    if "auth" in query_lower or "login" in query_lower or "jwt" in query_lower:
        return """## Authentication Flow

The project uses **JWT-based authentication** with the following flow:

1. **Login Request**: User submits credentials to `POST /api/auth/login`
2. **Validation**: Server validates credentials against the database
3. **Token Generation**: On success, generates access + refresh tokens
4. **Token Storage**: Client stores tokens (access in memory, refresh in httpOnly cookie)

### Key Files:
- `src/auth/jwt.ts` - Token generation and validation
- `src/auth/middleware.ts` - Route protection middleware
- `src/api/routes/auth.ts` - Auth endpoints

### Security Features:
- Access tokens expire in 15 minutes
- Refresh tokens expire in 7 days
- Tokens are signed with RS256 algorithm"""

    # Database-related queries
    elif "database" in query_lower or "schema" in query_lower or "model" in query_lower:
        return """## Database Schema

The project uses **PostgreSQL** with SQLAlchemy ORM. Key models include:

### User Model
```python
class User:
    id: UUID (primary key)
    email: str (unique)
    password_hash: str
    created_at: datetime
    updated_at: datetime
```

### Project Model
```python
class Project:
    id: UUID (primary key)
    name: str
    owner_id: UUID (foreign key -> User)
    status: enum (active, archived)
```

### Relationships:
- User has many Projects (one-to-many)
- Projects have many Tickets (one-to-many)
- Tickets have many Tasks (one-to-many)"""

    # API-related queries
    elif "api" in query_lower or "endpoint" in query_lower or "route" in query_lower:
        return """## API Endpoints

The API follows RESTful conventions with versioning:

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/refresh` - Refresh access token

### Projects
- `GET /api/v1/projects` - List all projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project details
- `PATCH /api/v1/projects/{id}` - Update project

### Tickets
- `GET /api/v1/tickets` - List tickets
- `POST /api/v1/tickets` - Create ticket
- `PATCH /api/v1/tickets/{id}/status` - Update status

All endpoints require authentication via Bearer token."""

    # Test-related queries
    elif "test" in query_lower or "failing" in query_lower:
        return """## Test Status

Current test suite status:

### Unit Tests
- **Total**: 156 tests
- **Passing**: 152 ✅
- **Failing**: 4 ❌

### Failing Tests:
1. `test_token_refresh_expired` - Edge case with expired refresh tokens
2. `test_concurrent_updates` - Race condition in status updates
3. `test_large_payload` - Timeout on large file uploads
4. `test_websocket_reconnect` - Flaky reconnection logic

### Coverage:
- Overall: 78%
- Auth module: 92%
- API routes: 85%
- Database models: 71%"""

    # Security-related queries
    elif "security" in query_lower or "vulnerabil" in query_lower:
        return """## Security Analysis

### Potential Issues Found:

1. **SQL Injection Risk** (Low)
   - Location: `src/api/search.ts:45`
   - Issue: Dynamic query construction
   - Fix: Use parameterized queries

2. **Missing Rate Limiting** (Medium)
   - Location: Auth endpoints
   - Recommendation: Add rate limiting to prevent brute force

3. **Sensitive Data Logging** (Low)
   - Location: `src/utils/logger.ts`
   - Issue: Request bodies logged without filtering

### Recommendations:
- Enable CORS with specific origins
- Add CSP headers
- Implement request signing for webhooks"""

    # README generation
    elif "readme" in query_lower:
        return """## Generated README

# Project Name

A modern web application for project management.

## Features
- User authentication with JWT
- Project and ticket management
- Real-time updates via WebSocket
- AI-powered code exploration

## Getting Started

```bash
# Install dependencies
npm install

# Set up environment
cp .env.example .env

# Run migrations
npm run db:migrate

# Start development server
npm run dev
```

## Architecture
- Frontend: Next.js with TypeScript
- Backend: FastAPI with Python
- Database: PostgreSQL
- Cache: Redis"""

    # Code review
    elif "review" in query_lower or "improve" in query_lower:
        return """## Code Review Suggestions

### High Priority
1. **Extract duplicate logic** in `src/api/handlers/`
   - Multiple handlers have similar validation patterns
   - Create a shared validation utility

2. **Add error boundaries** in React components
   - Several components lack error handling
   - Could cause cascading failures

### Medium Priority
3. **Optimize database queries** in ticket listing
   - N+1 query detected in `/tickets` endpoint
   - Use eager loading with relationships

4. **Add retry logic** for external API calls
   - GitHub webhook delivery lacks retry mechanism

### Nice to Have
5. **Add JSDoc comments** to exported functions
6. **Implement request caching** for read-heavy endpoints"""

    # Default response
    else:
        return f"""## Analysis for: "{query}"

I've analyzed the codebase for your query. Here's what I found:

### Overview
The project follows a modern architecture pattern with clear separation between frontend and backend components.

### Relevant Files
Based on your query, these files may be relevant:
- `src/core/` - Core business logic
- `src/api/` - API route handlers
- `src/utils/` - Utility functions

### Suggestions
1. Check the documentation in `docs/` folder
2. Review related tests in `tests/` folder
3. Use the search feature to find specific implementations

Would you like me to dive deeper into any specific aspect?"""


def _model_to_conversation(conv: ExploreConversation) -> Conversation:
    """Convert database model to response."""
    messages = [
        Message(
            id=m.id,
            role=m.role,
            content=m.content,
            timestamp=m.timestamp,
        )
        for m in conv.messages
    ]

    return Conversation(
        id=conv.id,
        project_id=conv.project_id,
        title=conv.title,
        last_message=conv.last_message,
        messages=messages,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


def _create_welcome_conversation(session, project_id: str) -> ExploreConversation:
    """Create initial conversation with welcome message."""
    conv = ExploreConversation(
        project_id=project_id,
        title="Getting Started",
        last_message="Welcome! Ask me anything about this codebase.",
    )
    session.add(conv)
    session.flush()  # Get the ID

    welcome_msg = ExploreMessage(
        conversation_id=conv.id,
        role="assistant",
        content="""## Welcome to AI Explore! 👋

I can help you understand this codebase. Try asking:

- **"Explain the authentication flow"** - Understand how auth works
- **"Show me the database schema"** - See data models
- **"What tests are failing?"** - Check test status
- **"Find security issues"** - Run a security scan
- **"Suggest improvements"** - Get code review feedback

What would you like to explore?""",
    )
    session.add(welcome_msg)

    return conv


def _seed_demo_conversations(session, project_id: str) -> list[ExploreConversation]:
    """Seed demo conversations for a project."""
    from datetime import timedelta

    now = utc_now()
    conversations = []

    # First: Getting Started conversation
    conv1 = _create_welcome_conversation(session, project_id)
    conversations.append(conv1)

    # Second: Auth analysis conversation
    conv2 = ExploreConversation(
        project_id=project_id,
        title="Authentication flow analysis",
        last_message="The auth module uses JWT tokens with refresh...",
    )
    conv2.created_at = now - timedelta(hours=2)
    conv2.updated_at = now - timedelta(hours=2)
    session.add(conv2)
    conversations.append(conv2)

    # Third: Database questions conversation
    conv3 = ExploreConversation(
        project_id=project_id,
        title="Database schema questions",
        last_message="The user table has the following relations...",
    )
    conv3.created_at = now - timedelta(days=1)
    conv3.updated_at = now - timedelta(days=1)
    session.add(conv3)
    conversations.append(conv3)

    session.commit()
    for c in conversations:
        session.refresh(c)

    return conversations


# ============================================================================
# API Routes - Conversations
# ============================================================================


@router.get(
    "/project/{project_id}/conversations", response_model=ConversationListResponse
)
async def list_conversations(
    project_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: DatabaseService = Depends(get_db_service),
):
    """List conversations for a project."""
    with db.get_session() as session:
        # Check if any conversations exist
        count = (
            session.query(ExploreConversation)
            .filter(ExploreConversation.project_id == project_id)
            .count()
        )

        # Seed demo data if no conversations exist
        if count == 0:
            _seed_demo_conversations(session, project_id)

        # Get conversations sorted by updated_at
        conversations = (
            session.query(ExploreConversation)
            .filter(ExploreConversation.project_id == project_id)
            .order_by(ExploreConversation.updated_at.desc())
            .limit(limit)
            .all()
        )

        total = (
            session.query(ExploreConversation)
            .filter(ExploreConversation.project_id == project_id)
            .count()
        )

        summaries = [
            ConversationSummary(
                id=c.id,
                title=c.title,
                last_message=c.last_message,
                timestamp=_format_time_ago(c.updated_at),
            )
            for c in conversations
        ]

        return ConversationListResponse(
            conversations=summaries,
            total_count=total,
        )


@router.post("/project/{project_id}/conversations", response_model=ConversationResponse)
async def create_conversation(
    project_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Create a new conversation."""
    with db.get_session() as session:
        conv = _create_welcome_conversation(session, project_id)
        session.commit()
        session.refresh(conv)

        return ConversationResponse(conversation=_model_to_conversation(conv))


@router.get(
    "/project/{project_id}/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
async def get_conversation(
    project_id: str,
    conversation_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Get a conversation with all messages."""
    with db.get_session() as session:
        conv = (
            session.query(ExploreConversation)
            .filter(
                ExploreConversation.id == conversation_id,
                ExploreConversation.project_id == project_id,
            )
            .first()
        )

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return ConversationResponse(conversation=_model_to_conversation(conv))


@router.post(
    "/project/{project_id}/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
)
async def send_message(
    project_id: str,
    conversation_id: str,
    message: MessageCreate,
    db: DatabaseService = Depends(get_db_service),
):
    """Send a message and get AI response."""
    with db.get_session() as session:
        conv = (
            session.query(ExploreConversation)
            .filter(
                ExploreConversation.id == conversation_id,
                ExploreConversation.project_id == project_id,
            )
            .first()
        )

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        now = utc_now()

        # Create user message
        user_msg = ExploreMessage(
            conversation_id=conversation_id,
            role="user",
            content=message.content,
        )
        session.add(user_msg)
        session.flush()

        # Generate AI response
        ai_content = _generate_ai_response(message.content, project_id)
        ai_msg = ExploreMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_content,
        )
        session.add(ai_msg)
        session.flush()

        # Update conversation metadata
        conv.last_message = (
            ai_content[:100] + "..." if len(ai_content) > 100 else ai_content
        )

        # Update title if this is the first user message
        user_message_count = (
            session.query(ExploreMessage)
            .filter(
                ExploreMessage.conversation_id == conversation_id,
                ExploreMessage.role == "user",
            )
            .count()
        )

        if user_message_count == 1:
            conv.title = (
                message.content[:50] + "..."
                if len(message.content) > 50
                else message.content
            )

        session.commit()
        session.refresh(user_msg)
        session.refresh(ai_msg)

        return MessageResponse(
            user_message=Message(
                id=user_msg.id,
                role=user_msg.role,
                content=user_msg.content,
                timestamp=user_msg.timestamp,
            ),
            assistant_message=Message(
                id=ai_msg.id,
                role=ai_msg.role,
                content=ai_msg.content,
                timestamp=ai_msg.timestamp,
            ),
        )


@router.delete("/project/{project_id}/conversations/{conversation_id}")
async def delete_conversation(
    project_id: str,
    conversation_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Delete a conversation."""
    with db.get_session() as session:
        conv = (
            session.query(ExploreConversation)
            .filter(
                ExploreConversation.id == conversation_id,
                ExploreConversation.project_id == project_id,
            )
            .first()
        )

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        session.delete(conv)
        session.commit()

        return {"message": "Conversation deleted successfully"}


# ============================================================================
# API Routes - Files & Suggestions
# ============================================================================


@router.get("/project/{project_id}/files", response_model=ProjectFilesResponse)
async def list_project_files(
    project_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """List key files in a project for exploration."""
    # In a real implementation, this would scan the actual codebase
    # For now, return representative mock files
    files = [
        ProjectFile(
            path="src/auth/jwt.ts",
            type="file",
            lines=156,
            description="JWT token generation and validation",
        ),
        ProjectFile(
            path="src/auth/middleware.ts",
            type="file",
            lines=89,
            description="Authentication middleware",
        ),
        ProjectFile(
            path="src/api/routes.ts",
            type="file",
            lines=234,
            description="API route definitions",
        ),
        ProjectFile(
            path="src/db/models/user.ts",
            type="file",
            lines=67,
            description="User database model",
        ),
        ProjectFile(
            path="src/db/models/project.ts",
            type="file",
            lines=92,
            description="Project database model",
        ),
        ProjectFile(
            path="src/utils/logger.ts",
            type="file",
            lines=45,
            description="Logging utilities",
        ),
        ProjectFile(
            path="src/config/index.ts",
            type="file",
            lines=78,
            description="Application configuration",
        ),
    ]

    return ProjectFilesResponse(
        project_id=project_id,
        files=files,
        total_count=len(files),
    )


@router.get("/project/{project_id}/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    project_id: str,
    context: Optional[str] = Query(None, description="Context for suggestions"),
    db: DatabaseService = Depends(get_db_service),
):
    """Get query suggestions for the explore interface."""
    base_suggestions = [
        "Explain the authentication flow",
        "Show me the database schema",
        "What tests are failing?",
        "Find potential security issues",
        "Summarize recent changes",
        "Generate a README for this project",
        "Suggest code improvements",
        "List all API endpoints",
    ]

    # If context provided, filter/sort suggestions
    if context:
        context_lower = context.lower()
        # Prioritize suggestions matching context
        matching = [s for s in base_suggestions if context_lower in s.lower()]
        non_matching = [s for s in base_suggestions if context_lower not in s.lower()]
        return SuggestionsResponse(suggestions=matching + non_matching)

    return SuggestionsResponse(suggestions=base_suggestions)
