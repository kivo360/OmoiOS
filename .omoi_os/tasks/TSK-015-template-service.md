---
id: TSK-015
title: Implement TemplateService class
created: 2026-01-09
status: pending
priority: HIGH
type: implementation
parent_ticket: TKT-008
estimate: M
dependencies:
  depends_on:
    - TSK-012
  blocks:
    - TSK-016
---

# TSK-015: Implement TemplateService class

## Objective

Create the TemplateService that applies starter templates to newly created repositories.

## Deliverables

- [ ] `backend/omoi_os/services/template_service.py`

## Implementation Notes

```python
# backend/omoi_os/services/template_service.py

import base64
from typing import Dict, List
from omoi_os.services.repository_service import RepositoryService

class TemplateService:
    """Service for applying project templates to repositories."""

    def __init__(self, repo_service: RepositoryService):
        self.repo_service = repo_service

    async def apply_template(
        self,
        owner: str,
        repo: str,
        template: str
    ) -> int:
        """Apply template files to repository. Returns count of files created."""
        if template == "empty":
            return 0

        files = self._get_template_files(template)
        if not files:
            return 0

        # Apply files (could be parallelized)
        for file_info in files:
            content_b64 = base64.b64encode(
                file_info["content"].encode()
            ).decode()

            await self.repo_service.client.put(
                f"/repos/{owner}/{repo}/contents/{file_info['path']}",
                json={
                    "message": f"Add {file_info['path']} from {template} template",
                    "content": content_b64,
                }
            )

        return len(files)

    def _get_template_files(self, template: str) -> List[Dict[str, str]]:
        """Get files for a template."""
        from omoi_os.services.template_definitions import TEMPLATES
        return TEMPLATES.get(template, [])

    def list_templates(self) -> List[dict]:
        """List available templates with descriptions."""
        return [
            {"id": "empty", "name": "Empty", "description": "README only"},
            {"id": "nextjs", "name": "Next.js", "description": "Next.js 14+ App Router"},
            {"id": "fastapi", "name": "FastAPI", "description": "FastAPI + PostgreSQL"},
            {"id": "react-vite", "name": "React", "description": "React + Vite + TypeScript"},
            {"id": "python-package", "name": "Python Package", "description": "Python package with pyproject.toml"},
        ]
```

## Done When

- [ ] TemplateService implemented
- [ ] apply_template method works
- [ ] list_templates returns available options
- [ ] Integration with RepositoryService
