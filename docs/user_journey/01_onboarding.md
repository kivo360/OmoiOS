# 1 Onboarding

**Part of**: [User Journey Documentation](./README.md)

---
### Phase 1: Onboarding & First Project Setup

#### 1.1 Initial Registration & Authentication
```
1. User visits OmoiOS dashboard
   ↓
2. Registration Options:
   Option A: Email/Password Registration
   Option B: OAuth login (GitHub/GitLab)
   ↓
3. Email Verification (if email registration)
   - User receives verification email
   - Clicks verification link
   - Account activated
   ↓
4. First-time user sees onboarding tour
   ↓
5. Organization Setup (Multi-Tenant)
   - Create or join organization
   - Set organization name and slug
   - Configure resource limits (max agents, runtime hours)
   - Set billing email (optional)
   ↓
6. Dashboard shows empty state: "Create your first project"
```

**Key Actions:**
- **Authentication**:
  - Email/password registration with verification
  - OAuth login (GitHub/GitLab)
  - Password reset flow
  - API key generation for programmatic access
  - Session management
- **Organization Setup**:
  - Create organization with unique slug
  - Set resource limits (max concurrent agents, max runtime hours)
  - Configure organization settings (JSONB)
  - Invite team members (future)
- **Agent Configuration**:
  - Set number of parallel agents (1-5, limited by org limits)
  - Configure agent preferences (capabilities, phase assignments)
  - Set review requirements (auto-approve vs manual approval gates)
  - Configure agent types (Worker, Planner, Validator)
- **Workspace Configuration**:
  - Workspace root directory (default: `./workspaces`)
  - Worker directory path (default: `/tmp/omoi_os_workspaces`)
  - Workspace type selection (local, docker, kubernetes, remote)

#### 1.2 Project Creation Options

**Option A: AI-Assisted Project Exploration** (Recommended for new projects)
```
1. User clicks "Explore New Project"
   ↓
2. Enters initial idea: "I want to create an authentication system with plugins"
   ↓
3. AI asks clarifying questions:
   - "What authentication methods should be supported?"
   - "Should this support multi-tenant scenarios?"
   - "What technology stack do you prefer?"
   ↓
4. User answers questions in chat interface
   ↓
5. AI generates Requirements Document (EARS-style format)
   ↓
6. User reviews requirements → Approves/Rejects/Provides feedback
   ↓
7. AI refines requirements based on feedback
   ↓
8. User approves final requirements
   ↓
9. AI generates Design Document:
   - Architecture diagrams
   - Component design
   - Security design
   - Implementation plan
   ↓
10. User reviews design → Approves/Rejects/Provides feedback
   ↓
11. AI refines design
   ↓
12. User approves final design
   ↓
13. User clicks "Initialize Project"
   ↓
14. System creates:
    - Project record
    - Initial tickets (based on design phases)
    - Tasks for each ticket
    - Spec workspace (Requirements | Design | Tasks | Execution tabs)
   ↓
15. Project ready for development!
```

**Option B: Quick Start** (For existing projects)
```
1. User clicks "Create Project"
   ↓
2. Enters project name and description
   ↓
3. Connects GitHub repository
   ↓
4. System analyzes codebase
   ↓
5. User creates first ticket manually or via GitHub issue sync
   ↓
6. Project ready!
```

---


---

**Next**: See [README.md](./README.md) for complete documentation index.
