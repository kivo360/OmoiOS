"""omoios CLI — terminal-first surface for the OmoiOS platform.

Entry point declared as `[project.scripts] omoios = "omoios.cli.main:main"`
in `sdk/python/pyproject.toml`. After `uv sync` (or `pip install -e .`),
the binary is on $PATH as `omoios`.

Standing rule (memory:feedback_terminal_first): every capability —
provider management, GitHub auth, tenant onboarding — must work 100%
from this CLI before any UI is allowed to start. If a task says
"add a UI for X", first ask "is the CLI for X complete?".
"""
