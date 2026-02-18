# Monorepo Migration Plan

**Created**: 2025-11-21
**Status**: Migration Plan
**Purpose**: Convert OmoiOS from single-repo to monorepo structure (backend + frontend)

---

## Target Structure

```
senior_sandbox/                    # Root (stays as workspace root)
├── README.md                      # Updated root README
├── docker-compose.yml             # Orchestrates backend + frontend
├── .gitignore                     # Updated for both backend/frontend
├── docs/                          # Shared documentation (stays at root)
│   ├── app_overview.md
│   ├── page_architecture.md
│   ├── design_system.md
│   ├── user_journey.md
│   ├── page_flow.md
│   ├── FRONTEND_PACKAGE.md
│   ├── frontend_implementation_guide.md
│   ├── design/
│   ├── requirements/
│   ├── architecture/
│   └── implementation/
│
├── backend/                       # Python FastAPI backend
│   ├── omoi_os/                   # Main package (moved from root)
│   ├── migrations/                # Alembic migrations (moved from root)
│   ├── tests/                     # Test suite (moved from root)
│   ├── scripts/                   # Utility scripts (moved from root)
│   ├── config/                    # YAML configs (moved from root)
│   ├── examples/                  # Python examples (moved from root)
│   ├── pyproject.toml             # Python deps (moved from root)
│   ├── uv.lock                    # Lock file (moved from root)
│   ├── alembic.ini                # Alembic config (moved from root)
│   ├── Justfile                   # Just commands (moved from root)
│   ├── pytest.ini                 # Pytest config (moved from root)
│   ├── docker/                    # Docker files (moved from root)
│   ├── Dockerfile.api             # (moved from root)
│   ├── Dockerfile.worker          # (moved from root)
│   ├── .env.example               # Environment template
│   ├── README.md                  # Backend-specific README
│   └── CLAUDE.md                  # Backend AI instructions (moved)
│
└── frontend/                      # Next.js 15 frontend
    ├── src/
    │   ├── app/                   # Next.js App Router pages
    │   ├── components/            # React components
    │   ├── hooks/                 # React Query hooks
    │   ├── stores/                # Zustand stores
    │   ├── providers/             # React providers
    │   ├── middleware/            # Zustand middleware
    │   ├── lib/                   # Utilities
    │   └── types/                 # TypeScript types
    ├── public/                    # Static assets
    ├── package.json               # Node deps
    ├── tsconfig.json              # TypeScript config
    ├── tailwind.config.ts         # Tailwind + Design System
    ├── next.config.js             # Next.js config
    ├── .env.local.example         # Environment template
    ├── README.md                  # Frontend-specific README
    └── docs/                      # Frontend-specific docs (symlink to ../docs/design/frontend)
```

---

## Migration Steps

### Phase 1: Backup & Safety (5 minutes)
```bash
# 1. Commit current state
git add -A
git commit -m "Pre-monorepo migration checkpoint"

# 2. Create migration branch
git checkout -b monorepo-migration

# 3. Backup (optional but recommended)
cp -r . ../senior_sandbox_backup
```

### Phase 2: Create Directory Structure (2 minutes)
```bash
# Create backend and frontend directories
mkdir -p backend frontend

# Create backend subdirectories
mkdir -p backend/{omoi_os,migrations,tests,scripts,config,examples,docker}

# Create frontend subdirectories  
mkdir -p frontend/{src,public,docs}
mkdir -p frontend/src/{app,components,hooks,stores,providers,middleware,lib,types}
```

### Phase 3: Move Backend Files (10 minutes)
```bash
# Move Python package
mv omoi_os backend/

# Move migrations
mv migrations backend/

# Move tests
mv tests backend/

# Move scripts
mv scripts backend/

# Move config
mv config backend/

# Move examples (Python only, keep frontend prototype)
mv examples/*.py backend/examples/
mv examples/workspaces backend/examples/
# Keep examples/frontend at root for now (we'll use it as reference)

# Move Docker files
mv docker backend/
mv Dockerfile.* backend/

# Move Python config files
mv pyproject.toml backend/
mv uv.lock backend/
mv alembic.ini backend/
mv pytest.ini backend/
mv Justfile backend/

# Move Python-specific docs
mv CLAUDE.md backend/

# Move env example (create from .env if exists)
cp .env backend/.env.example  # Or create template

# Keep docs/ at root (shared between backend/frontend)
```

### Phase 4: Update Backend Import Paths (5 minutes)

**Good News**: Python imports stay the same!

Since we're moving the entire `omoi_os/` package to `backend/omoi_os/`, and we run commands from the `backend/` directory, all imports like `from omoi_os.models import Task` remain unchanged.

**Update Working Directory in Commands**:
```bash
# OLD (from root):
uv run pytest

# NEW (from backend/):
cd backend
uv run pytest
```

**Files to Update**:
1. `backend/README.md` - Update command instructions to assume `backend/` as working directory
2. `backend/docker-compose.yml` - Update paths if you create backend-specific compose file
3. `backend/Justfile` - Paths should work as-is (they're relative)

### Phase 5: Create Frontend Structure (30 minutes)

```bash
cd frontend

# Initialize Next.js 15 project (in frontend/ directory)
npx create-next-app@latest . --typescript --tailwind --app --use-npm

# Initialize ShadCN
npx shadcn@latest init

# Install all dependencies from architecture doc
npm install \
  @tanstack/react-query@^5.0.0 \
  @tanstack/react-query-devtools@^5.0.0 \
  zustand@^4.5.0 \
  immer@^10.0.3 \
  zundo@^2.0.0 \
  zustand-pub@^1.0.0 \
  lz-string@^1.5.0 \
  @dnd-kit/core@^6.1.0 \
  @dnd-kit/sortable@^8.0.0 \
  reactflow@^11.10.0 \
  framer-motion@^11.0.0 \
  date-fns@^2.30.0 \
  recharts@^2.9.0 \
  react-syntax-highlighter@^15.5.0 \
  xterm@^5.3.0 \
  xterm-addon-fit@^0.8.0 \
  xterm-addon-web-links@^0.9.0 \
  next-themes@^0.2.1

# Create environment variables
cat > .env.local.example << EOF
NEXT_PUBLIC_API_URL=http://localhost:18000
NEXT_PUBLIC_WS_URL=ws://localhost:18000/ws
EOF

cp .env.local.example .env.local

# Create symlink to frontend docs
ln -s ../../docs/design/frontend docs/frontend-design
```

### Phase 6: Update Root-Level Files (10 minutes)

**Create**: `README.md` (at root)
```markdown
# OmoiOS - Autonomous Engineering Platform

Spec-driven multi-agent orchestration system.

## Monorepo Structure

- `backend/` - Python FastAPI backend
- `frontend/` - Next.js 15 frontend
- `docs/` - Shared documentation

## Quick Start

### Backend
\`\`\`bash
cd backend
uv sync
uv run uvicorn omoi_os.api.main:app --reload
\`\`\`

### Frontend
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

### Full Stack (Docker)
\`\`\`bash
docker-compose up
\`\`\`

See `docs/frontend_implementation_guide.md` for complete setup.
```

**Create**: `docker-compose.yml` (at root)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: omoios
      POSTGRES_PASSWORD: omoios
      POSTGRES_DB: omoios
    ports:
      - "15432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "16379:6379"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.api
    ports:
      - "18000:8000"
    environment:
      # pragma: allowlist secret
      - DATABASE_URL=postgresql://omoios:omoios@postgres:5432/omoios
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
    command: uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:18000
      - NEXT_PUBLIC_WS_URL=ws://localhost:18000/ws
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

volumes:
  postgres_data:
```

**Update**: `.gitignore` (at root)
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
.venv/
venv/
ENV/
.coverage
htmlcov/
.pytest_cache/

# Node
node_modules/
.next/
out/
build/
dist/
*.log

# Environment
.env
.env.local
.env.*.local
backend/.env
frontend/.env.local

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

---

## Validation Checklist

After migration, verify:

### Backend Still Works
```bash
cd backend

# Install deps
uv sync

# Run migrations
uv run alembic upgrade head

# Run tests
uv run pytest

# Start API
uv run uvicorn omoi_os.api.main:app --reload

# Check: http://localhost:18000/docs
```

### Frontend Builds
```bash
cd frontend

# Install deps
npm install

# Build
npm run build

# Start dev
npm run dev

# Check: http://localhost:3000
```

### Both Run Together
```bash
# From root
docker-compose up

# Check:
# Backend: http://localhost:18000/docs
# Frontend: http://localhost:3000
```

---

## Documentation Stays Accessible

**Shared Docs** (at root `docs/`):
- Product specs (app_overview, page_architecture, design_system)
- User flows (user_journey, page_flow)
- Architecture (design/frontend/, requirements/, implementation/)

**Backend-Specific Docs** (in `backend/`):
- CLAUDE.md (AI instructions for backend work)
- README.md (backend setup instructions)

**Frontend-Specific Docs** (in `frontend/docs/`):
- Symlink to `../../docs/design/frontend/` (no duplication)
- Can also copy key docs if preferred

**Result**: All documentation remains accessible from both backend and frontend contexts.

---

## Import Path Changes

### Backend Python Code: ✅ No Changes Needed

**Before (from root)**:
```python
from omoi_os.models import Task
from omoi_os.services import TaskQueueService
```

**After (from backend/)**:
```python
from omoi_os.models import Task  # Same!
from omoi_os.services import TaskQueueService  # Same!
```

**Why**: We're moving the entire package, so relative imports stay the same.

### Command Changes

**Before**:
```bash
# From root:
uv run pytest
uv run alembic upgrade head
uv run uvicorn omoi_os.api.main:app --reload
```

**After**:
```bash
# From backend/:
cd backend
uv run pytest
uv run alembic upgrade head
uv run uvicorn omoi_os.api.main:app --reload
```

**Or** with root-level orchestration:
```bash
# From root:
docker-compose up backend
docker-compose run backend pytest
```

---

## Benefits of Monorepo

1. ✅ Clear separation of concerns (backend vs frontend)
2. ✅ Easier to onboard frontend developers (isolated directory)
3. ✅ Can version frontend/backend independently
4. ✅ Docker Compose orchestrates both easily
5. ✅ Documentation stays shared (single source of truth)
6. ✅ Can deploy backend/frontend separately or together
7. ✅ Frontend developers don't see Python noise
8. ✅ Backend developers don't see Node noise

---

## Risks & Mitigations

### Risk 1: Broken Imports
**Mitigation**: Python imports don't change (package moves as a unit)

### Risk 2: Lost Files
**Mitigation**: Use `git mv` instead of `mv` to preserve history. Or commit before/after to track changes.

### Risk 3: CI/CD Breaks
**Mitigation**: Update CI paths to `backend/` for Python tests, `frontend/` for Node builds.

### Risk 4: Documentation Duplication
**Mitigation**: Keep docs at root, both backend/frontend reference them.

---

## Estimated Time

- **Planning**: 10 minutes (review this doc)
- **Execution**: 30 minutes (move files, update configs)
- **Validation**: 15 minutes (test backend, test frontend)
- **Cleanup**: 5 minutes (remove old files, commit)

**Total**: ~1 hour

---

## Rollback Plan

If anything breaks:
```bash
# Rollback to pre-migration commit
git reset --hard HEAD~1

# Or restore from backup
rm -rf senior_sandbox
cp -r senior_sandbox_backup senior_sandbox
```

---

## Next Steps

1. Review this plan
2. Approve migration
3. Execute migration (I can do this)
4. Validate both backend and frontend work
5. Commit changes

**Ready to proceed?**
