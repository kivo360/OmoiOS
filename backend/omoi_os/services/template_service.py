"""Template service for generating text using Jinja2 templates."""

from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader


class TemplateService:
    """Service for rendering Jinja2 templates."""

    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize template service.

        Args:
            template_dir: Directory containing templates (defaults to omoi_os/templates)
        """
        if template_dir is None:
            # Default to omoi_os/templates relative to this file
            base_path = Path(__file__).parent.parent
            template_dir = str(base_path / "templates")

        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False,  # For markdown/text templates
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, **context: Any) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template file (e.g., "prompts/diagnostic.md.j2")
            **context: Variables to pass to the template

        Returns:
            Rendered template as string

        Raises:
            TemplateNotFound: If template doesn't exist
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def render_system_prompt(self, template_name: str, **context: Any) -> str:
        """
        Render a system prompt template.

        Convenience method that ensures proper formatting for system prompts.

        Args:
            template_name: Name of the template file
            **context: Variables to pass to the template

        Returns:
            Rendered system prompt
        """
        return self.render(template_name, **context).strip()

    def render_user_prompt(self, template_name: str, **context: Any) -> str:
        """
        Render a user prompt template.

        Convenience method that ensures proper formatting for user prompts.

        Args:
            template_name: Name of the template file
            **context: Variables to pass to the template

        Returns:
            Rendered user prompt
        """
        return self.render(template_name, **context).strip()


# Global singleton instance
_template_service: Optional[TemplateService] = None


def get_template_service(template_dir: Optional[str] = None) -> TemplateService:
    """
    Get the global template service instance (singleton pattern).

    Args:
        template_dir: Optional template directory (only used on first call)

    Returns:
        TemplateService instance
    """
    global _template_service
    if _template_service is None:
        _template_service = TemplateService(template_dir=template_dir)
    return _template_service


def reset_template_service():
    """Reset the global template service instance (useful for testing)."""
    global _template_service
    _template_service = None
