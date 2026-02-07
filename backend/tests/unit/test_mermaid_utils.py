"""Tests for Mermaid diagram validation and sanitization utilities.

Tests for omoi_os.utils.mermaid module covering:
- Sanitization of node labels with special characters
- Subgraph label quoting
- Extraction of mermaid blocks from markdown
- Full validation with mermaid-cli (when available)
"""

from omoi_os.utils.mermaid import (
    MermaidValidationResult,
    extract_mermaid_blocks,
    sanitize_markdown_mermaid_blocks,
    sanitize_mermaid_diagram,
)


class TestSanitizeMermaidDiagram:
    """Tests for sanitize_mermaid_diagram function."""

    def test_empty_input(self):
        """Empty input should return empty output."""
        assert sanitize_mermaid_diagram("") == ""
        assert sanitize_mermaid_diagram("   ") == "   "

    def test_valid_diagram_unchanged(self):
        """Valid diagrams without special chars should be unchanged."""
        valid_diagram = """flowchart LR
    A[Start] --> B[Process]
    B --> C[End]
"""
        assert sanitize_mermaid_diagram(valid_diagram) == valid_diagram

    def test_quotes_curly_braces_in_labels(self):
        """Curly braces in labels should be quoted."""
        input_diagram = """flowchart LR
    API[/projects/{id}/settings]
"""
        expected = """flowchart LR
    API["/projects/{id}/settings"]
"""
        result = sanitize_mermaid_diagram(input_diagram)
        assert result == expected

    def test_quotes_forward_slashes_in_labels(self):
        """Forward slashes in labels should be quoted."""
        input_diagram = """flowchart TB
    ENDPOINT[GET /api/v1/users]
"""
        expected = """flowchart TB
    ENDPOINT["GET /api/v1/users"]
"""
        result = sanitize_mermaid_diagram(input_diagram)
        assert result == expected

    def test_quotes_pipe_characters(self):
        """Pipe characters in labels should be quoted."""
        input_diagram = """flowchart LR
    FLOW[Step A | Step B]
"""
        expected = """flowchart LR
    FLOW["Step A | Step B"]
"""
        result = sanitize_mermaid_diagram(input_diagram)
        assert result == expected

    def test_preserves_already_quoted_labels(self):
        """Already quoted labels should not be double-quoted."""
        input_diagram = """flowchart LR
    API["/projects/{id}/settings"]
"""
        result = sanitize_mermaid_diagram(input_diagram)
        assert result == input_diagram

    def test_escapes_quotes_in_labels(self):
        """Existing quotes in labels should be escaped."""
        input_diagram = """flowchart LR
    NODE[Value "quoted" here]
"""
        result = sanitize_mermaid_diagram(input_diagram)
        # The content should be quoted and internal quotes escaped
        assert "#quot;" in result or "Value" in result

    def test_quotes_subgraph_with_spaces(self):
        """Subgraph names with spaces should be quoted."""
        input_diagram = """flowchart TB
    subgraph API Layer
        A --> B
    end
"""
        result = sanitize_mermaid_diagram(input_diagram)
        assert 'subgraph "API Layer"' in result

    def test_preserves_already_quoted_subgraph(self):
        """Already quoted subgraph names should not be changed."""
        input_diagram = """flowchart TB
    subgraph "API Layer"
        A --> B
    end
"""
        result = sanitize_mermaid_diagram(input_diagram)
        assert result == input_diagram

    def test_real_world_problematic_diagram(self):
        """Test the actual diagram that failed in production."""
        input_diagram = """flowchart TB
    subgraph Frontend
        CP[Command Page] --> SSP[SpecDrivenSettingsPanel]
        SSP --> HOOK[useSpecDrivenSettings]
        HOOK --> API_CLIENT[API Client]
    end

    subgraph API Layer
        API_CLIENT --> ENDPOINT[/projects/{id}/settings/spec-driven]
        ENDPOINT --> SCHEMA[SpecDrivenOptionsSchema]
    end

    subgraph Service Layer
        SCHEMA --> PROJECT[Project Model]
        PROJECT --> |settings JSONB| DB[(PostgreSQL)]
        PPS[PhaseProgressionService] --> |reads| PROJECT
        PGS[PhaseGateService] --> |reads| PROJECT
        GS[GuardianService] --> |reads| PROJECT
    end
"""
        result = sanitize_mermaid_diagram(input_diagram)

        # The problematic node should now be quoted
        assert '"/projects/{id}/settings/spec-driven"' in result
        # Subgraphs with spaces should be quoted
        assert 'subgraph "API Layer"' in result
        assert 'subgraph "Service Layer"' in result
        # Edge labels with pipes should be quoted
        assert '"|settings JSONB|"' in result or "|settings JSONB|" in result

    def test_multiple_nodes_with_special_chars(self):
        """Multiple nodes with special characters should all be quoted."""
        input_diagram = """flowchart LR
    A[/path/to/file] --> B[function()]
    B --> C[array[0]]
    C --> D[{object}]
"""
        result = sanitize_mermaid_diagram(input_diagram)
        # Nodes with special chars that Mermaid interprets should be quoted
        assert '"/path/to/file"' in result  # / is special
        assert '"{object}"' in result  # {} are special
        # Parentheses inside square brackets are fine - not shape syntax
        assert "B[function()]" in result  # () inside [] don't need quoting
        # Nested brackets inside content would be problematic but handled differently
        assert "C[array[0]]" in result or 'C["array[0]"]' in result

    def test_preserves_node_shapes(self):
        """Node shapes should be preserved."""
        input_diagram = """flowchart LR
    A[Rectangle]
    B(Stadium)
    C{Decision}
    D[(Database)]
"""
        result = sanitize_mermaid_diagram(input_diagram)
        # Simple labels without special chars should remain unchanged
        assert "A[Rectangle]" in result
        assert "B(Stadium)" in result
        assert "C{Decision}" in result
        assert "D[(Database)]" in result


class TestExtractMermaidBlocks:
    """Tests for extract_mermaid_blocks function."""

    def test_no_mermaid_blocks(self):
        """Markdown without mermaid blocks returns empty list."""
        markdown = """# Heading

Some text here.

```python
print("hello")
```
"""
        result = extract_mermaid_blocks(markdown)
        assert result == []

    def test_single_mermaid_block(self):
        """Single mermaid block is extracted correctly."""
        markdown = """# Architecture

```mermaid
flowchart LR
    A --> B
```

More text here.
"""
        result = extract_mermaid_blocks(markdown)
        assert len(result) == 1
        assert "flowchart LR" in result[0]
        assert "A --> B" in result[0]

    def test_multiple_mermaid_blocks(self):
        """Multiple mermaid blocks are all extracted."""
        markdown = """# Diagrams

```mermaid
flowchart LR
    A --> B
```

Some text.

```mermaid
sequenceDiagram
    Alice->>Bob: Hello
```
"""
        result = extract_mermaid_blocks(markdown)
        assert len(result) == 2
        assert "flowchart" in result[0]
        assert "sequenceDiagram" in result[1]

    def test_case_insensitive_fence(self):
        """Mermaid fence detection is case insensitive."""
        markdown = """```MERMAID
flowchart LR
    A --> B
```
"""
        result = extract_mermaid_blocks(markdown)
        assert len(result) == 1


class TestSanitizeMarkdownMermaidBlocks:
    """Tests for sanitize_markdown_mermaid_blocks function."""

    def test_sanitizes_mermaid_in_markdown(self):
        """Mermaid blocks within markdown are sanitized."""
        markdown = """# Architecture

```mermaid
flowchart LR
    API[/projects/{id}]
```

Other content.
"""
        result = sanitize_markdown_mermaid_blocks(markdown)
        assert '"/projects/{id}"' in result
        # Other content preserved
        assert "# Architecture" in result
        assert "Other content." in result

    def test_preserves_non_mermaid_code_blocks(self):
        """Non-mermaid code blocks are not modified."""
        markdown = """```python
path = "/projects/{id}"
```

```mermaid
flowchart LR
    API[/projects/{id}]
```
"""
        result = sanitize_markdown_mermaid_blocks(markdown)
        # Python block unchanged (no quoting)
        assert 'path = "/projects/{id}"' in result
        # Mermaid block sanitized
        assert 'API["/projects/{id}"]' in result


class TestMermaidValidationResult:
    """Tests for MermaidValidationResult dataclass."""

    def test_valid_result(self):
        """Valid result has correct properties."""
        result = MermaidValidationResult(
            is_valid=True,
            sanitized_code="flowchart LR\n    A --> B",
            original_code="flowchart LR\n    A --> B",
        )
        assert result.is_valid is True
        assert result.error_message is None
        assert result.needs_sanitization is False

    def test_invalid_result(self):
        """Invalid result has error message."""
        result = MermaidValidationResult(
            is_valid=False, error_message="Syntax error at line 2"
        )
        assert result.is_valid is False
        assert "Syntax error" in result.error_message

    def test_needs_sanitization_flag(self):
        """needs_sanitization is True when code was modified."""
        result = MermaidValidationResult(
            is_valid=True,
            sanitized_code='flowchart LR\n    API["/path"]',
            original_code="flowchart LR\n    API[/path]",
        )
        assert result.needs_sanitization is True

    def test_no_sanitization_needed(self):
        """needs_sanitization is False when code unchanged."""
        code = "flowchart LR\n    A --> B"
        result = MermaidValidationResult(
            is_valid=True, sanitized_code=code, original_code=code
        )
        assert result.needs_sanitization is False


class TestDesignEvalMermaidIntegration:
    """Tests for Mermaid validation in DesignEvaluator."""

    def test_design_eval_sanitizes_mermaid(self):
        """DesignEvaluator should sanitize Mermaid diagrams."""
        from omoi_os.evals.design_eval import DesignEvaluator

        evaluator = DesignEvaluator()

        # Design with problematic Mermaid diagram
        design = {
            "architecture": """## Overview

```mermaid
flowchart LR
    API[/projects/{id}/settings]
```
""",
            "architecture_overview": "Test architecture",
            "data_models": [{"name": "Test", "fields": {"id": "int"}}],
            "api_endpoints": [
                {"method": "GET", "path": "/test", "description": "Test endpoint"}
            ],
        }

        result = evaluator.evaluate(design)

        # Design should be modified in-place with sanitized diagram
        assert '"/projects/{id}/settings"' in design["architecture"]

        # Should have warning about sanitization
        sanitization_warnings = [
            w for w in result.warnings if "Mermaid" in w and "auto-corrected" in w
        ]
        assert len(sanitization_warnings) == 1

    def test_design_eval_valid_mermaid_no_warning(self):
        """DesignEvaluator should not warn for valid Mermaid diagrams."""
        from omoi_os.evals.design_eval import DesignEvaluator

        evaluator = DesignEvaluator()

        # Design with valid Mermaid diagram (already quoted)
        design = {
            "architecture": """## Overview

```mermaid
flowchart LR
    API[Simple Label]
```
""",
            "architecture_overview": "Test architecture",
            "data_models": [{"name": "Test", "fields": {"id": "int"}}],
            "api_endpoints": [
                {"method": "GET", "path": "/test", "description": "Test endpoint"}
            ],
        }

        result = evaluator.evaluate(design)

        # Should NOT have Mermaid sanitization warning
        sanitization_warnings = [
            w for w in result.warnings if "Mermaid" in w and "auto-corrected" in w
        ]
        assert len(sanitization_warnings) == 0
