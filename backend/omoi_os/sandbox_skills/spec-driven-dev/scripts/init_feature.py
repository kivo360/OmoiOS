#!/usr/bin/env python3
"""
Initialize directory structure for a new feature in .omoi_os/.

Usage:
    python init_feature.py <feature-name>

Example:
    python init_feature.py collaboration-system

Creates:
    .omoi_os/requirements/<feature-name>.md
    .omoi_os/designs/<feature-name>.md
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path


def get_project_root() -> Path:
    """Find project root by looking for .omoi_os or common markers."""
    current = Path.cwd()

    # Look for .omoi_os directory
    for parent in [current] + list(current.parents):
        if (parent / ".omoi_os").exists():
            return parent
        if (parent / ".git").exists():
            return parent

    return current


def create_requirements_stub(feature_name: str, output_path: Path) -> None:
    """Create a requirements document stub."""
    domain = feature_name.upper().replace("-", "_")[:6]
    today = datetime.now().strftime("%Y-%m-%d")

    content = f"""# {feature_name.replace("-", " ").title()} Requirements

**Created**: {today}
**Status**: Draft
**Purpose**: Requirements specification for {feature_name.replace("-", " ")}.
**Related**:

---

## Document Overview

{{2-3 sentence overview of what this requirements document covers}}

---

## 1. Core Requirements

#### REQ-{domain}-CORE-001: {{Requirement Title}}
THE SYSTEM SHALL {{normative requirement statement}}.

{{Additional details, rationale, or constraints}}

---

## 2. State Machine (If Applicable)

#### REQ-{domain}-SM-001: States
{{Feature}} SHALL support the following states:

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> active : Start
    active --> completed : Complete
    completed --> [*]
```

---

## 3. Data Model Requirements

### 3.1 Primary Entity
#### REQ-{domain}-DM-001
{{Entity}} SHALL include the following fields:
- `id: str` (unique identifier)
- `status: StatusEnum` (current state)
- `created_at: datetime` (creation timestamp)
- `updated_at: datetime` (last update timestamp)

---

## 4. API Requirements

| Endpoint | Method | Purpose | Request Body | Responses |
|----------|--------|---------|--------------|-----------|
| /api/{{resource}} | POST | Create resource | `{{ field1, field2 }}` | 200: `{{ id, status }}`; 400: `{{ error }}` |

---

## Related Documents

- [Design Document](../designs/{feature_name}.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | {today} | Claude | Initial stub |
"""

    output_path.write_text(content)
    print(f"Created: {output_path}")


def create_design_stub(feature_name: str, output_path: Path) -> None:
    """Create a design document stub."""
    today = datetime.now().strftime("%Y-%m-%d")

    content = f"""# {feature_name.replace("-", " ").title()} - Product Design Document

**Created**: {today}
**Status**: Draft
**Purpose**: Design specification for {feature_name.replace("-", " ")}.
**Related**: [Requirements](../requirements/{feature_name}.md)

---

## Document Overview

{{Description of the feature/system being designed}}

- **Purpose & Scope**
  - {{Goal 1}}
  - {{Goal 2}}

- **Target Audience**
  - Implementation teams
  - System architects

---

## Architecture Overview

### High-Level Architecture

```mermaid
flowchart TD
    subgraph Feature[{feature_name.replace("-", " ").title()}]
        C1[Component 1]
        C2[Component 2]
    end

    C1 -->|action| C2
```

### Component Responsibilities

| Component | Layer | Responsibilities |
|-----------|-------|------------------|
| Component 1 | Service | {{Primary responsibilities}} |
| Component 2 | Data | {{Primary responsibilities}} |

---

## Data Models

### Pydantic Models

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class StatusEnum(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


class Entity(BaseModel):
    id: str
    status: StatusEnum
    created_at: datetime
    updated_at: datetime
```

---

## API Specifications

### REST Endpoints

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| POST | `/api/{{resource}}` | Create | `EntityCreate` | `Entity` |
| GET | `/api/{{resource}}/{{id}}` | Get | - | `Entity` |

---

## Related Documents

- **Requirements**: `../requirements/{feature_name}.md`

---

## Quality Checklist

- [ ] All requirements addressed
- [ ] Architecture diagram included
- [ ] API specifications complete
- [ ] Database schemas defined

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | {today} | Claude | Initial stub |
"""

    output_path.write_text(content)
    print(f"Created: {output_path}")


def init_feature(feature_name: str) -> None:
    """Initialize directory structure for a new feature."""
    root = get_project_root()
    omoi_dir = root / ".omoi_os"

    # Create directories if they don't exist
    dirs = ["requirements", "designs", "tickets", "tasks"]
    for d in dirs:
        (omoi_dir / d).mkdir(parents=True, exist_ok=True)

    # Create stub files
    req_path = omoi_dir / "requirements" / f"{feature_name}.md"
    design_path = omoi_dir / "designs" / f"{feature_name}.md"

    if req_path.exists():
        print(f"Warning: {req_path} already exists, skipping")
    else:
        create_requirements_stub(feature_name, req_path)

    if design_path.exists():
        print(f"Warning: {design_path} already exists, skipping")
    else:
        create_design_stub(feature_name, design_path)

    print(f"\nFeature '{feature_name}' initialized in {omoi_dir}")
    print("\nNext steps:")
    print(f"  1. Edit requirements: {req_path}")
    print(f"  2. Edit design: {design_path}")
    print("  3. Create tickets with generate_ids.py")


def main():
    parser = argparse.ArgumentParser(
        description="Initialize directory structure for a new feature"
    )
    parser.add_argument(
        "feature_name",
        help="Name of the feature (kebab-case, e.g., 'collaboration-system')",
    )

    args = parser.parse_args()

    # Validate feature name
    feature_name = args.feature_name.lower().replace("_", "-")
    if not feature_name.replace("-", "").isalnum():
        print(f"Error: Invalid feature name '{feature_name}'")
        print("Use alphanumeric characters and hyphens only")
        sys.exit(1)

    init_feature(feature_name)


if __name__ == "__main__":
    main()
