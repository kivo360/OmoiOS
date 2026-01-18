"""Configuration for spec sandbox execution.

Uses Pydantic Settings v2 with extra="ignore" so unknown
environment variables are silently ignored. This makes the same
code work in all environments without errors.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SpecSandboxSettings(BaseSettings):
    """Configuration for spec sandbox execution.

    All settings can come from environment variables.
    Unknown variables are ignored (extra="ignore").
    """

    model_config = SettingsConfigDict(
        env_prefix="",  # No prefix - use exact var names
        extra="ignore",  # Ignore unknown env vars
        env_file=".env",  # Optional .env file
        env_file_encoding="utf-8",
    )

    # === Core Identity ===
    spec_id: str = Field(default="local-spec", description="Unique spec identifier")
    sandbox_id: Optional[str] = Field(default=None, description="Daytona sandbox ID")
    spec_phase: Optional[str] = Field(
        default=None,
        description="Current phase (explore/requirements/design/tasks/sync)",
    )

    # === Paths ===
    working_directory: str = Field(default=".", description="Workspace directory")
    context_file: Optional[Path] = Field(
        default=None, description="Path to context JSON"
    )
    output_directory: Path = Field(
        default=Path(".spec-output"), description="Output directory"
    )

    # === Reporter Mode ===
    reporter_mode: str = Field(
        default="jsonl",
        description="Reporter type: 'array' (test), 'jsonl' (local), 'http' (production)",
    )
    callback_url: Optional[str] = Field(
        default=None, description="HTTP callback URL (production)"
    )

    # === Claude Agent SDK ===
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key"
    )
    claude_code_oauth_token: Optional[str] = Field(
        default=None, description="OAuth token (preferred)"
    )
    anthropic_base_url: Optional[str] = Field(
        default=None, description="Custom API endpoint"
    )
    model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Model to use for phase execution",
    )
    cwd: Optional[Path] = Field(
        default=None,
        description="Working directory for Claude Agent (defaults to working_directory)",
    )

    # === Execution Limits ===
    max_turns: int = Field(default=50, description="Max turns per phase")
    max_budget_usd: float = Field(default=10.0, description="Max budget in USD")
    use_mock: bool = Field(
        default=False,
        description="Use mock executor (for testing without Claude SDK)",
    )
    heartbeat_interval: int = Field(
        default=30, description="Heartbeat interval in seconds"
    )

    # === Markdown Generation ===
    markdown_generator: str = Field(
        default="claude",
        description="Generator type: 'static' (template-based) or 'claude' (Claude Agent SDK)",
    )

    # === Phase Context (from previous phases) ===
    phase_context_b64: Optional[str] = Field(
        default=None, description="Base64 JSON of accumulated context"
    )
    session_transcript_b64: Optional[str] = Field(
        default=None, description="Resume from transcript"
    )

    # === Spec Content (for local testing or from orchestrator) ===
    spec_title: str = Field(default="Untitled Spec", description="Spec title")
    spec_description: str = Field(default="", description="Spec description")
    task_data_base64: Optional[str] = Field(
        default=None, description="Full task context (base64)"
    )

    # === GitHub ===
    github_token: Optional[str] = Field(default=None)
    github_repo: Optional[str] = Field(default=None)
    branch_name: Optional[str] = Field(default=None)

    # === OmoiOS Integration (Production) ===
    omoios_api_url: Optional[str] = Field(
        default=None, description="OmoiOS API URL for syncing"
    )
    omoios_project_id: Optional[str] = Field(
        default=None, description="Project ID for spec sync"
    )
    omoios_api_key: Optional[str] = Field(default=None, description="API key for auth")


def load_settings() -> SpecSandboxSettings:
    """Load settings from environment."""
    return SpecSandboxSettings()
