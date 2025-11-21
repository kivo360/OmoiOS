# OmoiOS Monorepo - Quick Start

## ✅ Migration Complete!

Your project is now organized as a monorepo:
- `backend/` - Python FastAPI backend
- `frontend/` - Next.js 15 frontend  
- `docs/` - Shared documentation

---

## Run Backend

\`\`\`bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn omoi_os.api.main:app --reload

# Visit: http://localhost:8000/docs
\`\`\`

---

## Run Frontend

\`\`\`bash
cd frontend
npm install  # Already done
cp .env.local.example .env.local
npm run dev

# Visit: http://localhost:3000
\`\`\`

---

## Build Frontend from Scaffolds

You have 15,000+ lines of ready-to-copy code. See `docs/FRONTEND_PACKAGE.md` for complete index.

**Quick Assembly:**
1. Copy providers: `docs/design/auth/frontend_auth_scaffold.md` (lines 1789-1973)
2. Copy auth pages: Same doc (lines 11-593)
3. Copy kanban board: Same doc (lines 1030-1200)
4. Copy hooks: `docs/design/frontend/react_query_websocket.md`
5. Copy stores: `docs/design/frontend/zustand_middleware_reference.md`

**Time**: 1-2 weeks for complete app.

---

## Run Full Stack

\`\`\`bash
docker-compose up

# Backend: http://localhost:18000
# Frontend: http://localhost:3000
\`\`\`

---

## Documentation

- `docs/FRONTEND_PACKAGE.md` - Frontend code index (line-by-line copy instructions)
- `docs/frontend_implementation_guide.md` - Step-by-step assembly guide
- `docs/MONOREPO_MIGRATION_COMPLETE.md` - Migration summary
- `backend/README.md` - Backend instructions
- `frontend/README.md` - Frontend instructions

**You're ready to build!**
