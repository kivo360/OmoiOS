# Authentication & Authorization System Requirements

**Status**: Draft  
**Created**: 2025-11-19  
**Updated**: 2025-11-19

## Executive Summary

Build a comprehensive multi-tenant authentication and authorization system from scratch using SQLAlchemy, replacing the Supabase approach. The system must support:
- Email/password authentication
- Multi-tenant organizations with RBAC
- Both human users and AI agents as actors
- OAuth integration with 20+ providers
- GitHub App integration for repository access
- Hybrid authorization (RBAC + ABAC + ReBAC)

## Core Requirements

### REQ-AUTH-001: User Authentication

**Priority**: P0 (Critical - Foundation)

**Description**: Email/password based authentication for human users.

**Acceptance Criteria**:
- Users can register with email and password
- Password hashing using bcrypt/argon2
- Email verification workflow
- Login returns JWT tokens (access + refresh)
- Token refresh mechanism
- Password reset flow
- Session management with expiration

**Database Entities**:
- `User`: email, hashed_password, is_verified, is_active
- `Session`: user_id, token_hash, expires_at, ip_address, user_agent

**API Endpoints**:
- `POST /auth/register` - Create account
- `POST /auth/login` - Authenticate
- `POST /auth/refresh` - Refresh tokens
- `POST /auth/logout` - Invalidate session
- `POST /auth/verify-email` - Verify email
- `POST /auth/forgot-password` - Request reset
- `POST /auth/reset-password` - Complete reset

---

### REQ-AUTH-002: Organization Multi-Tenancy

**Priority**: P0 (Critical - Foundation)

**Description**: Multi-tenant organization structure for resource isolation.

**Acceptance Criteria**:
- Users can create organizations
- Organizations have unique slugs
- Organization owners have full control
- Settings stored as JSONB for flexibility
- Soft delete support

**Database Entities**:
- `Organization`: name, slug, owner_id, billing_email, settings, is_active

**API Endpoints**:
- `POST /organizations` - Create org
- `GET /organizations` - List user's orgs
- `GET /organizations/{id}` - Get org details
- `PATCH /organizations/{id}` - Update org
- `DELETE /organizations/{id}` - Archive org

---

### REQ-AUTH-003: Organization Membership & RBAC

**Priority**: P0 (Critical - Foundation)

**Description**: Role-based access control within organizations.

**Acceptance Criteria**:
- Users can be members of multiple orgs
- Each membership has a role
- System roles: owner, admin, member, viewer
- Custom roles per organization
- Role inheritance support
- Wildcard permissions (e.g., `org:*`, `project:*`)

**Database Entities**:
- `OrganizationMembership`: user_id, organization_id, role_id, invited_by
- `Role`: name, permissions (JSONB array), is_system, inherits_from

**System Roles**:
```python
{
    "owner": ["org:*", "project:*"],
    "admin": ["org:read", "org:write", "org:members:*", "project:*"],
    "member": ["org:read", "project:read", "project:write"],
    "viewer": ["org:read", "project:read"]
}
```

**API Endpoints**:
- `POST /organizations/{id}/members` - Invite member
- `GET /organizations/{id}/members` - List members
- `PATCH /organizations/{id}/members/{user_id}` - Update role
- `DELETE /organizations/{id}/members/{user_id}` - Remove member
- `GET /organizations/{id}/roles` - List roles
- `POST /organizations/{id}/roles` - Create custom role

---

### REQ-AUTH-004: API Key Authentication

**Priority**: P0 (Critical - Foundation)

**Description**: Long-lived API keys for programmatic access.

**Acceptance Criteria**:
- Users can create multiple API keys
- Keys have names and scopes
- Keys can expire
- Last used timestamp tracking
- Key prefix visible (first 8 chars)
- Full key hashed for security
- Format: `sk_{env}_{random_32_chars}`

**Database Entities**:
- `APIKey`: user_id, name, key_prefix, hashed_key, scopes, expires_at, last_used_at

**API Endpoints**:
- `POST /api-keys` - Create key (returns full key once)
- `GET /api-keys` - List user's keys
- `DELETE /api-keys/{id}` - Revoke key

---

### REQ-AUTH-005: AI Agent Support

**Priority**: P1 (High - Core Feature)

**Description**: AI agents as first-class actors alongside users.

**Acceptance Criteria**:
- Agents can be dynamically spawned
- Agents have lifecycle states (spawning, idle, working, terminated)
- Agents authenticate via API keys
- Agents can be organization and project members
- Track agent metrics (tasks completed, cost, tokens)
- Auto-termination after idle period
- Integration with OpenHands SDK

**Database Entities**:
- `Agent`: name, agent_type, status, spawned_by, organization_id, project_id, openhands_instance_id
- `AgentExecutionLog`: agent_id, task_id, level, message, iteration, tokens_used, cost_usd
- `AgentTerminalOutput`: agent_id, task_id, output_type, content, sequence_number

**Agent Types**:
- code_generator
- test_engineer
- code_reviewer
- documentation
- task_decomposer
- devops
- general

**API Endpoints**:
- `POST /agents` - Spawn agent
- `GET /agents` - List agents
- `DELETE /agents/{id}` - Terminate agent
- `POST /agents/{id}/pause` - Pause execution
- `POST /agents/{id}/resume` - Resume execution
- `GET /agents/{id}/output` - Get terminal output
- `WS /ws/agents/{id}/stream` - Real-time output stream

---

### REQ-AUTH-006: Project Management

**Priority**: P1 (High - Core Feature)

**Description**: Projects as containers for work items with GitHub integration.

**Acceptance Criteria**:
- Projects belong to organizations
- GitHub repository linking
- Project members (users + agents)
- Project-level roles (owner, maintainer, contributor, viewer)
- Documents within projects
- Status tracking (planning, active, on_hold, completed, archived)

**Database Entities**:
- `Project`: Enhanced with organization_id, created_by, github_repo_id, github_repo_full_name
- `ProjectMember`: project_id, user_id OR agent_id, role
- `Document`: project_id, title, doc_type, content, file_path, created_by

**API Endpoints**:
- `POST /organizations/{id}/projects` - Create project
- `GET /organizations/{id}/projects` - List projects
- `POST /projects/{id}/members` - Add member
- `POST /projects/{id}/documents` - Create document

---

### REQ-AUTH-007: Attribute-Based Access Control (ABAC)

**Priority**: P2 (Medium - Advanced Feature)

**Description**: Fine-grained, context-aware authorization policies.

**Acceptance Criteria**:
- Policies based on user/agent attributes
- Resource attributes
- Environmental conditions (time, location, etc.)
- Allow and deny effects
- Priority-based evaluation
- Support for complex conditions (comparisons, wildcards)

**Database Entities**:
- `Policy`: organization_id, name, effect, priority, subjects, resources, actions, conditions

**Policy Examples**:
```json
{
  "name": "Business Hours Only",
  "effect": "allow",
  "subjects": {"department": ["engineering"]},
  "resources": {"type": "project"},
  "actions": ["read", "write"],
  "conditions": {"time.hour": {">=": 9, "<=": 17}}
}
```

---

### REQ-AUTH-008: OAuth Integration

**Priority**: P2 (Medium - User Experience)

**Description**: OAuth 2.0 authentication with multiple providers.

**Acceptance Criteria**:
- Support 20+ OAuth providers (Google, GitHub, Microsoft, GitLab, etc.)
- PKCE support for enhanced security
- Token refresh automation
- Multiple accounts per user
- Organization-level provider configuration
- Auto-create users on OAuth login
- Link OAuth accounts to existing users

**Database Entities**:
- `OAuthProvider`: organization_id, provider_type, client_id, client_secret_encrypted, scopes
- `OAuthConnection`: user_id, provider_id, provider_user_id, access_token_encrypted, refresh_token_encrypted
- `OAuthState`: state, code_verifier, code_challenge (CSRF + PKCE)

**Supported Providers**:
- Google, GitHub, Microsoft, GitLab, Bitbucket
- Slack, Discord, LinkedIn
- Notion, Figma, Linear
- Auth0, Okta, AWS Cognito

**API Endpoints**:
- `GET /oauth/providers/available` - List available providers
- `POST /oauth/providers/configure` - Configure provider
- `GET /oauth/authorize` - Start OAuth flow
- `GET /oauth/callback` - Handle callback
- `GET /oauth/connections` - List connections
- `DELETE /oauth/connections/{id}` - Revoke connection

---

### REQ-AUTH-009: GitHub App Integration

**Priority**: P2 (Medium - Agent Execution)

**Description**: GitHub App for repository access and automation.

**Acceptance Criteria**:
- GitHub App installation flow
- Repository access via installation tokens
- Create branches, commits, PRs programmatically
- Webhook handling for GitHub events
- Agent-driven code commits
- PR creation from agent work

**Database Entities**:
- `GitHubInstallation`: organization_id, github_installation_id, permissions, events
- `GitHubRepository`: installation_id, project_id, github_repo_id, full_name
- `GitHubWebhookEvent`: project_id, event_type, payload, processed

**GitHub Operations**:
- Create/delete branches
- Read/write/delete files
- Create/update/merge PRs
- Create/update issues and comments
- Request reviewers
- Create PR reviews
- Search code

**API Endpoints**:
- `GET /github/installations` - List installations
- `GET /github/installations/{id}/repositories` - List repos
- `POST /github/repositories/{id}/branches` - Create branch
- `POST /github/repositories/{id}/commits` - Create commit
- `POST /github/repositories/{id}/pulls` - Create PR
- `POST /github/webhooks` - Webhook receiver

---

### REQ-AUTH-010: Agent Streaming & Monitoring

**Priority**: P2 (Medium - Observability)

**Description**: Real-time monitoring of agent execution.

**Acceptance Criteria**:
- Capture all agent terminal output (stdout, stderr, actions, thoughts)
- WebSocket streaming to frontend
- Full-text search across output
- Agent performance metrics
- Dashboard with aggregate statistics
- Pause/resume/stop agent controls

**Database Entities**:
- `AgentTerminalOutput`: Enhanced with sequence_number, iteration
- `AgentExecutionLog`: Enhanced with iteration, tokens_used, cost_usd

**Features**:
- xterm.js terminal display
- Color-coded output types
- Auto-scroll toggle
- Search with PostgreSQL full-text search
- Performance dashboard with charts
- Real-time agent status updates

**API Endpoints**:
- `GET /agents/{id}/output` - Get output (paginated)
- `POST /agents/{id}/search` - Search output
- `GET /agents/{id}/performance` - Performance metrics
- `GET /agents/performance/dashboard` - Aggregate metrics
- `WS /ws/agents/{id}/stream` - Real-time output
- `WS /ws/dashboard` - Dashboard updates

---

### REQ-AUTH-011: Task Assignment System

**Priority**: P1 (High - Core Feature)

**Description**: Assign tasks to users or agents.

**Acceptance Criteria**:
- Tasks can be assigned to users OR agents
- Track assignment timestamps (assigned, started, completed)
- Multiple assignments per task (collaborative)
- Agent capacity limits (max concurrent tasks)
- Task dependencies
- Task decomposition via AI

**Database Entities**:
- `TaskAssignment`: task_id, assignee_id OR agent_id, assigned_by, started_at, completed_at

**Enhanced Task Model**:
```python
- generated_by_ai: bool
- depends_on_task_ids: List[UUID]
- required_capabilities: List[str]
- execution_instructions: str
- execution_result: dict (JSONB)
- actual_iterations: int
```

---

### REQ-AUTH-012: Authorization Service

**Priority**: P0 (Critical - Security)

**Description**: Unified authorization engine.

**Acceptance Criteria**:
- Check authorization for any action
- Support users and agents
- Evaluation order: super_admin → ownership → project_role → org_role → abac → deny
- Return detailed explanation of authorization decision
- Cache authorization results (5 min)
- Batch authorization checks

**Authorization Checks**:
1. Super admin bypass (users only)
2. Resource ownership (creator)
3. Project membership (ReBAC)
4. Organization role (RBAC)
5. Attribute policies (ABAC)
6. Explicit deny policies

**Service Methods**:
```python
async def is_authorized(
    actor_id: UUID,
    actor_type: ActorType,
    action: str,
    organization_id: UUID,
    resource_type: Optional[str],
    resource_id: Optional[UUID]
) -> Tuple[bool, str, Dict]
```

---

## Feature Prioritization

### Phase 0: Foundation (P0 - Week 1)
**Goal**: Basic authentication and organizations

1. User model with password hashing
2. Email/password registration and login
3. JWT token generation and validation
4. Session management
5. Organization model
6. OrganizationMembership model
7. Basic Role model (system roles only)
8. Simple permission checking

**Deliverable**: Users can register, login, create orgs, invite members

---

### Phase 1: Core Authorization (P0-P1 - Week 2)
**Goal**: RBAC and project structure

1. Complete Role system with permissions
2. Authorization service (RBAC only)
3. Project model with org ownership
4. ProjectMember model
5. Ticket enhancements (link to projects, users)
6. Task enhancements (assignments)
7. TaskAssignment model
8. API middleware for permission checks

**Deliverable**: Full RBAC working, projects + tickets + tasks integrated

---

### Phase 2: Agent System (P1 - Week 3)
**Goal**: AI agents as actors

1. Agent model with lifecycle
2. Agent spawning via OpenHands
3. AgentExecutionLog model
4. AgentTerminalOutput model
5. Agent API key generation
6. Agent membership in orgs/projects
7. Agent role (agent_executor)
8. Task assignment to agents

**Deliverable**: Agents can be spawned, assigned tasks, execute in OpenHands

---

### Phase 3: Advanced Authorization (P2 - Week 4)
**Goal**: ABAC and fine-grained control

1. Policy model (ABAC)
2. Enhanced authorization service (ABAC + ReBAC)
3. Policy evaluation engine
4. Attribute evaluation with comparisons
5. Deny policies
6. Policy management API
7. Authorization caching

**Deliverable**: Complex attribute-based policies working

---

### Phase 4: OAuth Integration (P2 - Week 5)
**Goal**: Third-party authentication

1. OAuthProvider model
2. OAuthConnection model
3. OAuthState model (PKCE + CSRF)
4. OAuth service with 20+ providers
5. Provider registry
6. OAuth flow endpoints
7. Token refresh automation
8. Account linking

**Deliverable**: Users can login via OAuth providers

---

### Phase 5: GitHub Integration (P2 - Week 6)
**Goal**: Repository automation

1. GitHubInstallation model
2. GitHubRepository model
3. GitHubWebhookEvent model
4. GitHub App service (PyGithub)
5. Branch/commit/PR operations
6. Webhook handling
7. Agent GitHub operations
8. Project-repo linking

**Deliverable**: Agents can commit code, create PRs automatically

---

### Phase 6: Monitoring & Streaming (P2 - Week 7)
**Goal**: Real-time observability

1. WebSocket manager
2. Agent streaming service
3. Terminal output storage
4. Full-text search (PostgreSQL)
5. WebSocket endpoints
6. Frontend terminal component (xterm.js)
7. Performance dashboard
8. Agent control (pause/resume/stop)

**Deliverable**: Real-time agent monitoring with beautiful UI

---

## Out of Scope (Future Enhancements)

- Multi-factor authentication (TOTP, SMS, hardware keys)
- SAML/SSO integration
- Audit logging with tamper-proof storage
- Advanced notification system
- Team hierarchy within orgs
- Resource quotas and billing
- Advanced analytics and reporting
- Mobile app support
- Internationalization (i18n)

---

## Technical Constraints

### Security Requirements
- All passwords hashed with bcrypt (cost factor 12)
- JWT tokens: 15min access, 7d refresh
- API keys hashed with SHA-256
- OAuth tokens encrypted at rest (AES-256)
- CSRF protection on all state-changing endpoints
- Rate limiting on auth endpoints (5 attempts/15min)
- CORS whitelisting in production

### Performance Requirements
- Authorization checks < 50ms (with caching)
- Token generation < 100ms
- Database indexes on all foreign keys
- GIN indexes on JSONB fields
- Materialized views for dashboards

### Database Requirements
- PostgreSQL 18+
- UUID primary keys
- JSONB for flexible schemas
- Timezone-aware timestamps (use `utc_now()`)
- Foreign key constraints with CASCADE
- Unique constraints where appropriate

---

## Migration Strategy

### Handling Existing User Model

Current `User` model is Supabase-based with:
- `id` (UUID, references auth.users)
- `email`, `email_confirmed_at`
- `role` (simple string)
- `user_metadata` (JSONB)

**Migration Path**:
1. Add new fields to existing `User` model:
   - `hashed_password`
   - `is_verified` (map from email_confirmed_at)
   - `is_super_admin`
   - `department`
   - `attributes` (rename from user_metadata)
   - `last_login_at` (map from last_sign_in_at)

2. Remove Supabase-specific fields:
   - Drop `phone`, `phone_confirmed_at`
   - Keep as nullable for backward compat if needed

3. Rename fields:
   - `name` → `full_name`
   - `user_metadata` → `attributes`
   - `last_sign_in_at` → `last_login_at`

---

## Dependencies

### Python Packages
```txt
# Authentication
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
python-multipart==0.0.6

# OAuth
authlib==1.3.0
httpx==0.25.2

# GitHub
PyGithub==2.1.1
PyJWT==2.8.0

# Password validation
zxcvbn==4.4.28

# Encryption
cryptography==41.0.7
```

### Environment Variables
```bash
# JWT
JWT_SECRET_KEY=<random_secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption
ENCRYPTION_KEY=<fernet_key>

# GitHub App
GITHUB_APP_ID=123456
GITHUB_CLIENT_ID=Iv1.xxx
GITHUB_CLIENT_SECRET=xxx
GITHUB_PRIVATE_KEY_PATH=/path/to/key.pem
GITHUB_WEBHOOK_SECRET=xxx

# OAuth (per provider)
OAUTH_GOOGLE_CLIENT_ID=xxx
OAUTH_GOOGLE_CLIENT_SECRET=xxx
# etc.
```

---

## Testing Strategy

### Unit Tests
- Password hashing and verification
- Token generation and validation
- Permission checking logic
- OAuth token exchange mocking
- Policy evaluation engine

### Integration Tests
- Full auth flow (register → verify → login)
- Organization CRUD
- Member invitation and role assignment
- API key authentication
- Agent spawning and execution
- GitHub operations

### E2E Tests
- User registration through UI
- OAuth login flow
- Agent task execution
- GitHub PR creation
- Real-time streaming

---

## Success Metrics

- Authentication latency < 200ms
- Authorization checks < 50ms (cached)
- Support 1000+ concurrent users
- Support 100+ concurrent agents
- Zero security vulnerabilities in auth layer
- 99.9% uptime for auth service

---

## Questions & Decisions

**Q: Use JWT or session tokens?**  
A: Both - JWT for stateless API access, sessions for web

**Q: Where to store encryption keys?**  
A: Environment variables + secret manager (AWS Secrets Manager, Vault)

**Q: How to handle agent costs?**  
A: Track in agent metrics, bill to organization

**Q: OAuth provider priority?**  
A: Start with GitHub, Google, Microsoft (most common)

**Q: GitHub App vs Personal Access Tokens?**  
A: GitHub App for better security and no user context needed

