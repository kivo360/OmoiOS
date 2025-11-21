# OmoiOS Frontend

Next.js 15 frontend for OmoiOS autonomous engineering platform.

## Quick Start

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.local.example .env.local

# Start dev server
npm run dev

# Visit: http://localhost:3000
```

## Development

```bash
# Run linter
npm run lint

# Build for production
npm run build

# Start production server
npm start
```

## Project Structure

Based on `docs/design/frontend/frontend_architecture_shadcn_nextjs.md`:

```
frontend/
├── app/                  # Next.js App Router pages
├── components/           # React components
├── hooks/                # React Query hooks
├── stores/               # Zustand stores
├── providers/            # React providers
├── middleware/           # Zustand middleware
├── lib/                  # Utilities
└── types/                # TypeScript types
```

## Documentation

See parent `../docs/` directory:
- `FRONTEND_PACKAGE.md` - Complete code index with line numbers
- `frontend_implementation_guide.md` - Assembly instructions
- `design/frontend/` - Architecture and scaffolds

## Copy Code from Scaffolds

All pages, components, hooks, and stores are pre-built in documentation:

**Auth Pages**: Copy from `docs/design/auth/frontend_auth_scaffold.md`
**Components**: Copy from `docs/design/frontend/component_scaffold_guide.md`
**Hooks**: Copy from `docs/design/frontend/react_query_websocket.md`
**Stores**: Copy from `docs/design/frontend/zustand_middleware_reference.md`

See `../docs/FRONTEND_PACKAGE.md` for exact line numbers.

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **UI Library**: ShadCN UI (Radix UI + Tailwind CSS)
- **State**: Zustand + React Query
- **Real-Time**: WebSocket integration
- **Graph**: React Flow
- **Animations**: Framer Motion

