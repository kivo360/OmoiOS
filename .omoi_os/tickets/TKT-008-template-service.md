---
id: TKT-008
title: Template Service for New Repositories
created: 2026-01-09
updated: 2026-01-09
status: backlog
priority: HIGH
type: feature
feature: create-repository
estimate: M
requirements:
  - REQ-CREATE-REPO-FUNC-004
dependencies:
  blocked_by:
    - TKT-007
  blocks:
    - TKT-010
---

# TKT-008: Template Service for New Repositories

## Objective

Implement a service that applies starter templates (Next.js, FastAPI, React, Python Package) to newly created repositories, providing users with a solid foundation before agents add their features.

## Scope

### In Scope
- `TemplateService` class
- Template definitions for: Next.js, FastAPI, React+Vite, Python Package
- API endpoint to list available templates
- Apply template files to repo via GitHub API

### Out of Scope
- Custom user templates (future)
- Template from GitHub template repos (future)

## Acceptance Criteria

- [ ] `TemplateService` implemented
- [ ] 4 templates defined with complete boilerplate files
- [ ] `GET /api/v1/templates` returns available templates with descriptions
- [ ] Templates applied as commits after repo creation
- [ ] Files include: config files, .gitignore, basic structure
- [ ] Parallel file creation for performance
- [ ] Unit tests for template application

## Technical Notes

- Store template content as string constants or load from template directory
- Use GitHub Contents API (`PUT /repos/{owner}/{repo}/contents/{path}`)
- Apply files in parallel using asyncio.gather()
- Each file is a separate commit (or batch in single commit if possible)

## Templates to Implement

1. **Next.js App Router**
   - package.json, next.config.js, tsconfig.json
   - app/layout.tsx, app/page.tsx
   - .gitignore, .eslintrc.json

2. **FastAPI + PostgreSQL**
   - pyproject.toml
   - app/__init__.py, app/main.py, app/config.py
   - .gitignore

3. **React + Vite**
   - package.json, vite.config.ts, tsconfig.json
   - src/main.tsx, src/App.tsx
   - .gitignore

4. **Python Package**
   - pyproject.toml
   - src/{package}/__init__.py
   - tests/__init__.py
   - .gitignore

## Tasks

- TSK-015: Implement TemplateService class
- TSK-016: Define template file contents
- TSK-017: Add templates API endpoint
- TSK-018: Write tests for template application

## Estimate

**Size**: M (2-4 hours)
**Rationale**: Straightforward file operations, predefined content
