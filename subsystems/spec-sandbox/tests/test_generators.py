"""Tests for markdown generators."""

import pytest
from pathlib import Path
import yaml

from spec_sandbox.generators.markdown import (
    MarkdownGenerator,
    generate_requirements_markdown,
    generate_design_markdown,
    generate_tasks_index_markdown,
    generate_task_markdown,
    generate_spec_summary_markdown,
)


class TestGenerateRequirementsMarkdown:
    """Tests for requirements markdown generation."""

    def test_generates_frontmatter(self):
        """Should generate YAML frontmatter with required fields."""
        output = {
            "requirements": [
                {
                    "id": "REQ-001",
                    "type": "functional",
                    "category": "API",
                    "text": "THE SYSTEM SHALL validate user input",
                    "priority": "must",
                    "acceptance_criteria": ["Input is validated", "Errors returned"],
                }
            ],
            "assumptions": ["Users have valid credentials"],
        }

        markdown = generate_requirements_markdown(
            output=output,
            spec_id="test-spec",
            spec_title="Test Spec",
            created_date="2024-01-15",
        )

        # Should have frontmatter delimiters
        assert markdown.startswith("---\n")
        assert "\n---\n\n" in markdown

        # Extract frontmatter
        parts = markdown.split("---\n")
        frontmatter = yaml.safe_load(parts[1])

        # New template format uses different frontmatter fields
        assert "id" in frontmatter
        assert frontmatter["title"] == "Test Spec Requirements"
        assert frontmatter["feature"] == "test-spec"
        assert frontmatter["status"] == "draft"
        assert frontmatter["category"] == "API"

    def test_includes_requirements_content(self):
        """Should include requirement details in markdown body."""
        output = {
            "requirements": [
                {
                    "id": "REQ-001",
                    "type": "functional",
                    "category": "API",
                    "text": "THE SYSTEM SHALL validate user input",
                    "priority": "must",
                    "acceptance_criteria": ["Input is validated"],
                }
            ],
        }

        markdown = generate_requirements_markdown(
            output=output,
            spec_id="test-spec",
            spec_title="Test Spec",
            created_date="2024-01-15",
        )

        assert "REQ-001" in markdown
        assert "THE SYSTEM SHALL validate user input" in markdown
        assert "Input is validated" in markdown
        # New template format uses "Api Requirements" (title case from category)
        assert "Api Requirements" in markdown or "API" in markdown

    def test_includes_assumptions(self):
        """Should include assumptions section."""
        output = {
            "requirements": [],
            "assumptions": ["Users have accounts", "System is online"],
        }

        markdown = generate_requirements_markdown(
            output=output,
            spec_id="test-spec",
            spec_title="Test Spec",
            created_date="2024-01-15",
        )

        assert "## Assumptions" in markdown
        assert "Users have accounts" in markdown
        assert "System is online" in markdown


class TestGenerateDesignMarkdown:
    """Tests for design markdown generation."""

    def test_generates_mermaid_diagram(self):
        """Should generate Mermaid architecture diagram."""
        output = {
            "architecture_overview": "A microservices architecture",
            "components": [
                {
                    "name": "APIService",
                    "type": "service",
                    "responsibility": "Handle API requests",
                    "file_path": "src/api.py",
                    "dependencies": ["DatabaseService"],
                },
                {
                    "name": "DatabaseService",
                    "type": "service",
                    "responsibility": "Database operations",
                    "file_path": "src/db.py",
                    "dependencies": [],
                },
            ],
            "testing_strategy": "Unit and integration tests",
        }

        markdown = generate_design_markdown(
            output=output,
            spec_id="test-spec",
            spec_title="Test Spec",
            created_date="2024-01-15",
        )

        # Should have Mermaid diagram
        assert "```mermaid" in markdown
        assert "flowchart TD" in markdown
        assert "APIService" in markdown
        assert "DatabaseService" in markdown
        # Should have some form of component relationship in diagram
        # The new format uses "|calls|" style connections
        assert "-->" in markdown or "-->|" in markdown

    def test_includes_data_models(self):
        """Should include data models with SQL schema and Pydantic models."""
        output = {
            "architecture_overview": "Simple design",
            "components": [],
            "data_models": [
                {
                    "name": "User",
                    "purpose": "User account data",
                    "fields": {"id": "uuid", "name": "string", "email": "string"},
                }
            ],
            "testing_strategy": "Unit tests",
        }

        markdown = generate_design_markdown(
            output=output,
            spec_id="test-spec",
            spec_title="Test Spec",
            created_date="2024-01-15",
        )

        # Should have Data Models section
        assert "## Data Models" in markdown

        # Should have Database Schema with SQL
        assert "### Database Schema" in markdown
        assert "CREATE TABLE users" in markdown
        assert "id UUID PRIMARY KEY" in markdown

        # Should have Pydantic Models section
        assert "### Pydantic Models" in markdown
        assert "class User(BaseModel)" in markdown


class TestGenerateTasksIndexMarkdown:
    """Tests for tasks index markdown generation."""

    def test_generates_dependency_graph(self):
        """Should generate Mermaid dependency graph."""
        output = {
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "Create schema",
                    "type": "implementation",
                    "dependencies": [],
                    "estimated_hours": 2,
                },
                {
                    "id": "TASK-002",
                    "title": "Implement API",
                    "type": "implementation",
                    "dependencies": ["TASK-001"],
                    "estimated_hours": 4,
                },
            ],
            "critical_path": ["TASK-001", "TASK-002"],
            "total_estimated_hours": 6,
        }

        markdown = generate_tasks_index_markdown(
            output=output,
            spec_id="test-spec",
            spec_title="Test Spec",
            created_date="2024-01-15",
        )

        assert "```mermaid" in markdown
        assert "flowchart LR" in markdown
        assert "TASK_001" in markdown
        assert "TASK_002" in markdown
        # Should have dependency edge
        assert "TASK_001 --> TASK_002" in markdown

    def test_includes_summary_stats(self):
        """Should include summary statistics."""
        output = {
            "tasks": [
                {"id": "TASK-001", "title": "Task 1", "type": "implementation", "estimated_hours": 2},
                {"id": "TASK-002", "title": "Task 2", "type": "test", "estimated_hours": 1},
            ],
            "total_estimated_hours": 3,
            "critical_path": ["TASK-001"],
        }

        markdown = generate_tasks_index_markdown(
            output=output,
            spec_id="test-spec",
            spec_title="Test Spec",
            created_date="2024-01-15",
        )

        assert "**Total Tasks**: 2" in markdown
        assert "**Total Estimated Hours**: 3" in markdown


class TestGenerateTaskMarkdown:
    """Tests for individual task markdown generation."""

    def test_generates_task_frontmatter(self):
        """Should generate frontmatter with task metadata."""
        task = {
            "id": "TASK-001",
            "title": "Implement feature",
            "description": "Add the new feature",
            "type": "implementation",
            "files_to_create": ["src/feature.py"],
            "files_to_modify": ["src/main.py"],
            "dependencies": ["TASK-000"],
            "requirements_addressed": ["REQ-001"],
            "acceptance_criteria": ["Feature works", "Tests pass"],
            "estimated_hours": 3,
            "priority": 1,
        }

        markdown = generate_task_markdown(
            task=task,
            spec_id="test-spec",
            created_date="2024-01-15",
        )

        # Extract frontmatter
        parts = markdown.split("---\n")
        frontmatter = yaml.safe_load(parts[1])

        assert frontmatter["id"] == "TASK-001"
        assert frontmatter["title"] == "Implement feature"
        assert frontmatter["status"] == "pending"
        assert frontmatter["estimate"] == "M"  # 3 hours = Medium
        # New template format has nested dependencies
        assert "dependencies" in frontmatter
        assert frontmatter["dependencies"]["depends_on"] == ["TASK-000"]

    def test_includes_acceptance_criteria(self):
        """Should include acceptance criteria as checkboxes."""
        task = {
            "id": "TASK-001",
            "title": "Test task",
            "description": "A test",
            "type": "test",
            "acceptance_criteria": ["Criterion 1", "Criterion 2"],
            "estimated_hours": 1,
        }

        markdown = generate_task_markdown(
            task=task,
            spec_id="test-spec",
            created_date="2024-01-15",
        )

        assert "## Acceptance Criteria" in markdown
        assert "- [ ] Criterion 1" in markdown
        assert "- [ ] Criterion 2" in markdown


class TestMarkdownGenerator:
    """Tests for MarkdownGenerator class."""

    def test_generate_all_creates_files(self, tmp_path):
        """Should create all markdown files."""
        generator = MarkdownGenerator(
            output_dir=tmp_path,
            spec_id="test-spec",
            spec_title="Test Spec",
        )

        requirements = {
            "requirements": [
                {
                    "id": "REQ-001",
                    "type": "functional",
                    "category": "Core",
                    "text": "Test requirement",
                    "priority": "must",
                    "acceptance_criteria": ["Works"],
                }
            ],
        }

        design = {
            "architecture_overview": "Test architecture",
            "components": [
                {"name": "Service", "type": "service", "responsibility": "Do stuff"},
            ],
            "testing_strategy": "Test it",
        }

        tasks = {
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "Do task",
                    "description": "A task",
                    "type": "implementation",
                    "estimated_hours": 2,
                }
            ],
            "total_estimated_hours": 2,
            "critical_path": ["TASK-001"],
        }

        sync = {
            "validation_results": {"all_requirements_covered": True},
            "coverage_matrix": [{"requirement_id": "REQ-001", "covered_by_tasks": ["TASK-001"], "status": "fully_covered"}],
            "spec_summary": {"total_requirements": 1, "total_tasks": 1, "total_estimated_hours": 2},
            "ready_for_execution": True,
        }

        artifacts = generator.generate_all(
            requirements_output=requirements,
            design_output=design,
            tasks_output=tasks,
            sync_output=sync,
        )

        # Check files created
        assert "requirements" in artifacts
        assert "design" in artifacts
        assert "tasks_index" in artifacts
        assert "task:TASK-001" in artifacts
        assert "spec_summary" in artifacts

        # Check files exist
        assert (tmp_path / "requirements.md").exists()
        assert (tmp_path / "design.md").exists()
        assert (tmp_path / "tasks" / "index.md").exists()
        assert (tmp_path / "tasks" / "TASK-001.md").exists()
        assert (tmp_path / "SPEC_SUMMARY.md").exists()

    def test_generates_valid_yaml_frontmatter(self, tmp_path):
        """All generated files should have valid YAML frontmatter."""
        generator = MarkdownGenerator(
            output_dir=tmp_path,
            spec_id="test-spec",
            spec_title="Test Spec",
        )

        requirements = {
            "requirements": [{"id": "REQ-001", "type": "functional", "category": "Core", "text": "Test", "priority": "must"}],
        }

        artifacts = generator.generate_all(requirements_output=requirements)

        # Read and parse frontmatter
        content = (tmp_path / "requirements.md").read_text()
        parts = content.split("---\n")
        frontmatter = yaml.safe_load(parts[1])

        assert isinstance(frontmatter, dict)
        assert "id" in frontmatter
        assert "title" in frontmatter
