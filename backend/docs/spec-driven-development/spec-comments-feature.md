# Spec Comments Feature

**Created**: 2025-01-14
**Status**: Design (Not Implemented)
**Purpose**: Enable human-agent collaboration through discussion threads on specs

---

## Overview

The Spec Comments feature adds a dedicated discussion thread to each Spec, allowing users and agents to collaborate, ask questions, log decisions, and provide approval notes throughout the spec-driven workflow.

## Use Cases

1. **Human-Agent Collaboration**: Users can ask clarifying questions, agents can respond with recommendations
2. **Decision Logging**: Record "why did we choose X over Y?" for future reference
3. **Approval Notes**: Document approval decisions with context
4. **Requirement Clarification**: Discuss ambiguous requirements before implementation
5. **Design Feedback**: Provide feedback on proposed architecture/design

## User Stories

- As a user, I want to comment on a spec so that I can ask questions or provide feedback
- As a user, I want to see agent responses to my comments so that we can collaborate on decisions
- As a user, I want to see a chronological discussion thread so that I can follow the conversation
- As a user, I want to @mention specific requirements or tasks so that comments have context
- As an agent, I want to post comments explaining my decisions so that users understand my reasoning

---

## Data Model

### SpecComment Model

```python
# omoi_os/models/spec_comment.py

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class SpecComment(Base):
    """Comment on a spec for human-agent collaboration."""

    __tablename__ = "spec_comments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    spec_id: Mapped[str] = mapped_column(
        String, ForeignKey("specs.id", ondelete="CASCADE"), index=True
    )

    # Author can be a user_id or agent_id
    author_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="'user' or 'agent'"
    )
    author_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    author_name: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="Display name for UI"
    )

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional references to spec entities
    references: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="References: {requirement_ids: [], task_ids: [], design_section: ''}"
    )

    # Thread support (reply to another comment)
    parent_comment_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("spec_comments.id", ondelete="CASCADE"), nullable=True
    )

    # Metadata
    comment_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="'question', 'answer', 'decision', 'approval', 'feedback', 'note'"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=utc_now
    )
    is_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    spec: Mapped["Spec"] = relationship(back_populates="comments")
    replies: Mapped[list["SpecComment"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped[Optional["SpecComment"]] = relationship(
        back_populates="replies", remote_side=[id]
    )
```

### Update Spec Model

```python
# Add to omoi_os/models/spec.py

class Spec(Base):
    # ... existing fields ...

    # Add relationship
    comments: Mapped[list["SpecComment"]] = relationship(
        back_populates="spec", cascade="all, delete-orphan",
        order_by="SpecComment.created_at"
    )
```

---

## API Design

### Endpoints

```
GET    /api/v1/specs/{spec_id}/comments          # List comments (paginated)
POST   /api/v1/specs/{spec_id}/comments          # Create comment
GET    /api/v1/specs/{spec_id}/comments/{id}     # Get single comment
PATCH  /api/v1/specs/{spec_id}/comments/{id}     # Update comment
DELETE /api/v1/specs/{spec_id}/comments/{id}     # Delete comment (soft delete)
```

### Request/Response Schemas

```python
# Pydantic schemas

class SpecCommentCreate(BaseModel):
    content: str
    comment_type: Optional[str] = None  # question, answer, decision, etc.
    parent_comment_id: Optional[str] = None  # For threaded replies
    references: Optional[dict] = None  # {requirement_ids: [], task_ids: []}

class SpecCommentUpdate(BaseModel):
    content: Optional[str] = None
    comment_type: Optional[str] = None

class SpecCommentResponse(BaseModel):
    id: str
    spec_id: str
    author_type: str  # 'user' or 'agent'
    author_id: str
    author_name: Optional[str]
    content: str
    comment_type: Optional[str]
    references: Optional[dict]
    parent_comment_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    is_edited: bool
    reply_count: int  # Computed field

class SpecCommentsListResponse(BaseModel):
    spec_id: str
    comments: list[SpecCommentResponse]
    total_count: int
    has_more: bool
```

### Example API Usage

```bash
# Create a user comment
POST /api/v1/specs/spec-123/comments
{
  "content": "Should we use JWT or session-based auth for this feature?",
  "comment_type": "question",
  "references": {
    "requirement_ids": ["req-456"]
  }
}

# Agent replies
POST /api/v1/specs/spec-123/comments
{
  "content": "Based on the requirements for stateless API access, JWT is recommended...",
  "comment_type": "answer",
  "parent_comment_id": "comment-789"
}

# User approves
POST /api/v1/specs/spec-123/comments
{
  "content": "Approved. Let's proceed with JWT.",
  "comment_type": "approval"
}
```

---

## Frontend Design

### Comments Tab in Spec Detail Page

```
┌─────────────────────────────────────────────────────────────┐
│  Spec: User Authentication System                           │
├─────────────────────────────────────────────────────────────┤
│  [Requirements] [Design] [Tasks] [Comments (5)]             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 💬 Write a comment...                         [Send] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 👤 Kevin (User) • 2 hours ago          [Question]   │   │
│  │ Should we use JWT or session-based auth?            │   │
│  │ 📎 REQ-001: Authentication method                   │   │
│  │                                        [Reply]      │   │
│  │                                                     │   │
│  │   ┌─────────────────────────────────────────────┐  │   │
│  │   │ 🤖 Agent (Claude) • 1 hour ago    [Answer]  │  │   │
│  │   │ Based on the requirements for stateless API │  │   │
│  │   │ access, JWT is recommended because:         │  │   │
│  │   │ 1. Stateless - no server-side sessions      │  │   │
│  │   │ 2. Mobile-friendly                          │  │   │
│  │   │ 3. Microservice-ready                       │  │   │
│  │   └─────────────────────────────────────────────┘  │   │
│  │                                                     │   │
│  │   ┌─────────────────────────────────────────────┐  │   │
│  │   │ 👤 Kevin (User) • 30 min ago    [Approval]  │  │   │
│  │   │ Approved. Let's proceed with JWT.           │  │   │
│  │   └─────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🤖 Agent (Claude) • 15 min ago          [Decision]  │   │
│  │ Design phase completed. Proceeding with JWT-based   │   │
│  │ authentication using RS256 algorithm.               │   │
│  │ 📎 Design: Authentication Architecture              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### UI Components

```typescript
// components/spec/SpecComments.tsx

interface SpecCommentsProps {
  specId: string
  isExecuting?: boolean  // Enable polling during execution
}

// Comment type badges
const commentTypeBadges = {
  question: { label: "Question", color: "blue", icon: HelpCircle },
  answer: { label: "Answer", color: "green", icon: MessageCircle },
  decision: { label: "Decision", color: "purple", icon: Gavel },
  approval: { label: "Approval", color: "green", icon: CheckCircle },
  feedback: { label: "Feedback", color: "yellow", icon: MessageSquare },
  note: { label: "Note", color: "gray", icon: StickyNote },
}

// Author type indicators
const authorIndicators = {
  user: { icon: User, label: "User" },
  agent: { icon: Bot, label: "Agent" },
}
```

### React Hooks

```typescript
// hooks/useSpecComments.ts

export function useSpecComments(specId: string, options?: {
  refetchInterval?: number | false
}) {
  return useQuery({
    queryKey: ['specs', specId, 'comments'],
    queryFn: () => getSpecComments(specId),
    refetchInterval: options?.refetchInterval,
  })
}

export function useCreateSpecComment(specId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: SpecCommentCreate) => createSpecComment(specId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['specs', specId, 'comments'])
    },
  })
}
```

---

## Agent Integration

### Auto-Generated Comments

Agents can automatically post comments at key moments:

```python
# In sandbox worker or state machine

async def post_agent_comment(
    spec_id: str,
    content: str,
    comment_type: str = "note",
    references: dict = None
):
    """Post a comment as the executing agent."""
    # Called at phase transitions, decisions, completions
```

### When Agents Post Comments

| Event | Comment Type | Example Content |
|-------|--------------|-----------------|
| Phase completed | `decision` | "Requirements phase completed. 5 requirements identified." |
| Design choice | `decision` | "Selected PostgreSQL over MongoDB for relational data needs." |
| Question for user | `question` | "The auth requirements are ambiguous. Should we support OAuth?" |
| Task blocked | `note` | "Task blocked: Missing GitHub credentials for PR creation." |
| Error recovery | `note` | "Retrying after transient API failure (attempt 2/3)." |

---

## Real-Time Updates

### Polling During Execution

```typescript
// Poll comments every 5s when spec is executing
const { data: comments } = useSpecComments(specId, {
  refetchInterval: spec?.status === "executing" ? 5000 : false,
})
```

### WebSocket Events (Future Enhancement)

```python
# Event types for real-time comment updates
"spec.comment_created"
"spec.comment_updated"
"spec.comment_deleted"
```

---

## Database Migration

```python
# alembic/versions/xxx_add_spec_comments.py

def upgrade():
    op.create_table(
        'spec_comments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('spec_id', sa.String(), nullable=False),
        sa.Column('author_type', sa.String(20), nullable=False),
        sa.Column('author_id', sa.String(), nullable=False),
        sa.Column('author_name', sa.String(200), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('references', JSONB, nullable=True),
        sa.Column('parent_comment_id', sa.String(), nullable=True),
        sa.Column('comment_type', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_edited', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['spec_id'], ['specs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_comment_id'], ['spec_comments.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_spec_comments_spec_id', 'spec_comments', ['spec_id'])
    op.create_index('idx_spec_comments_author', 'spec_comments', ['author_type', 'author_id'])
    op.create_index('idx_spec_comments_created_at', 'spec_comments', ['created_at'])


def downgrade():
    op.drop_table('spec_comments')
```

---

## Implementation Checklist

### Backend
- [ ] Create `SpecComment` model in `omoi_os/models/spec_comment.py`
- [ ] Add relationship to `Spec` model
- [ ] Create Alembic migration
- [ ] Add API routes in `omoi_os/api/routes/specs.py`
- [ ] Add Pydantic schemas for request/response
- [ ] Add service layer for comment operations
- [ ] Add agent comment posting capability to sandbox worker

### Frontend
- [ ] Create `SpecComments` component
- [ ] Create `CommentItem` component with threading
- [ ] Create `CommentComposer` component
- [ ] Add `useSpecComments` hook
- [ ] Add Comments tab to spec detail page
- [ ] Add comment count badge to tab
- [ ] Add real-time polling during execution

### Testing
- [ ] Unit tests for comment CRUD operations
- [ ] Integration tests for API endpoints
- [ ] Test threaded replies
- [ ] Test soft delete behavior
- [ ] Test agent auto-comments during execution

---

## Future Enhancements

1. **@Mentions**: Reference specific users, requirements, or tasks with autocomplete
2. **Reactions**: Quick emoji reactions to comments (thumbs up, etc.)
3. **Markdown Support**: Rich text formatting in comments
4. **File Attachments**: Attach screenshots or documents
5. **Email Notifications**: Notify users of new comments
6. **Search**: Search through comment history
7. **Export**: Export discussion thread as part of spec documentation
