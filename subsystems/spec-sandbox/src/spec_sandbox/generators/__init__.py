"""Generators for spec artifacts.

Generators convert phase outputs into various formats:
- Markdown with YAML frontmatter for rich documentation
- Individual task files
- Design documents with Mermaid diagrams

Two generator types are available:
- MarkdownGenerator: Static template-based generation (fast, no API calls)
- ClaudeMarkdownGenerator: Claude Agent SDK-based generation (intelligent, language-aware)
"""

from spec_sandbox.generators.markdown import (
    MarkdownGenerator,
    generate_requirements_markdown,
    generate_design_markdown,
    generate_tasks_index_markdown,
    generate_task_markdown,
    generate_spec_summary_markdown,
)
from spec_sandbox.generators.claude_generator import (
    ClaudeMarkdownGenerator,
    ClaudeGeneratorConfig,
)

__all__ = [
    # Static generators
    "MarkdownGenerator",
    "generate_requirements_markdown",
    "generate_design_markdown",
    "generate_tasks_index_markdown",
    "generate_task_markdown",
    "generate_spec_summary_markdown",
    # Claude-based generators
    "ClaudeMarkdownGenerator",
    "ClaudeGeneratorConfig",
]
