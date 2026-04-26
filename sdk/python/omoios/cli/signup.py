"""`omoios signup` — placeholder for tenant onboarding.

Planned shape (per tasks/next-session-instructions.md §5):
  1. Prompt for email + password (or accept --email/--password flags)
  2. POST /api/v1/auth/register
  3. Login + mint platform API key via /api/v1/auth/api-keys
  4. Optionally trigger `omoios auth github` to connect GitHub
  5. Write the config file via `_config.write_config`

The mechanics already exist in `scripts/setup_local_smoke_account.py`
and `scripts/setup_prod_smoke_account.py`; this command will absorb
that logic so users don't have to know about the helper scripts.
"""

from __future__ import annotations

import click


@click.command("signup")
def signup() -> None:
    """Interactive tenant signup: register, mint API key, write config (planned)."""
    raise click.ClickException(
        "`omoios signup` is not implemented yet. The interactive "
        "registration flow ships next per tasks/next-session-instructions.md "
        "§5. For now use scripts/setup_local_smoke_account.py or "
        "scripts/setup_prod_smoke_account.py for the mechanics."
    )
