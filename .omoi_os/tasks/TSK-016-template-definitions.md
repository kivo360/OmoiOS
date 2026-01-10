---
id: TSK-016
title: Define template file contents
created: 2026-01-09
status: pending
priority: HIGH
type: implementation
parent_ticket: TKT-008
estimate: M
dependencies:
  depends_on:
    - TSK-015
  blocks: []
---

# TSK-016: Define template file contents

## Objective

Create the actual file contents for each starter template (Next.js, FastAPI, React+Vite, Python Package).

## Deliverables

- [ ] `backend/omoi_os/services/template_definitions.py`

## Implementation Notes

```python
# backend/omoi_os/services/template_definitions.py

TEMPLATES = {
    "nextjs": [
        {
            "path": "package.json",
            "content": '''{
  "name": "{{repo_name}}",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.0.0",
    "typescript": "^5.0.0"
  }
}'''
        },
        {
            "path": "tsconfig.json",
            "content": '''{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}'''
        },
        {
            "path": "app/layout.tsx",
            "content": '''export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}'''
        },
        {
            "path": "app/page.tsx",
            "content": '''export default function Home() {
  return (
    <main>
      <h1>Welcome to your new project</h1>
      <p>Built with OmoiOS</p>
    </main>
  )
}'''
        },
        {
            "path": ".gitignore",
            "content": '''node_modules/
.next/
out/
.env*.local
'''
        },
    ],

    "fastapi": [
        {
            "path": "pyproject.toml",
            "content": '''[project]
name = "{{repo_name}}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.23.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "httpx>=0.24.0",
]
'''
        },
        {
            "path": "app/__init__.py",
            "content": ""
        },
        {
            "path": "app/main.py",
            "content": '''from fastapi import FastAPI

app = FastAPI(title="{{repo_name}}")

@app.get("/")
async def root():
    return {"message": "Welcome to {{repo_name}}"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
'''
        },
        {
            "path": ".gitignore",
            "content": '''__pycache__/
*.py[cod]
.venv/
.env
'''
        },
    ],

    "react-vite": [
        {
            "path": "package.json",
            "content": '''{
  "name": "{{repo_name}}",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0"
  }
}'''
        },
        {
            "path": "vite.config.ts",
            "content": '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
'''
        },
        {
            "path": "src/main.tsx",
            "content": '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
'''
        },
        {
            "path": "src/App.tsx",
            "content": '''function App() {
  return (
    <div>
      <h1>Welcome to {{repo_name}}</h1>
      <p>Built with OmoiOS</p>
    </div>
  )
}

export default App
'''
        },
        {
            "path": ".gitignore",
            "content": '''node_modules/
dist/
.env
'''
        },
    ],

    "python-package": [
        {
            "path": "pyproject.toml",
            "content": '''[project]
name = "{{repo_name}}"
version = "0.1.0"
description = "A Python package"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 88
'''
        },
        {
            "path": "src/{{repo_name}}/__init__.py",
            "content": '''"""{{repo_name}} package."""

__version__ = "0.1.0"
'''
        },
        {
            "path": "tests/__init__.py",
            "content": ""
        },
        {
            "path": ".gitignore",
            "content": '''__pycache__/
*.py[cod]
dist/
*.egg-info/
.venv/
'''
        },
    ],
}
```

## Done When

- [ ] All 4 templates defined with complete files
- [ ] Files are valid and would work if cloned
- [ ] Proper .gitignore for each
- [ ] Placeholder {{repo_name}} for customization
