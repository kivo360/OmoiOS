"""Shared async-runner + SDK-error translator for omoios CLI subapps.

Every subcommand wants the same sequence:
  1. resolve config (flag > env > XDG file)
  2. open `AsyncOmoiOSClient` as a context manager
  3. run a coroutine
  4. translate `omoios.exceptions.*` into a `CliError` with a helpful hint

Putting the translation in one place keeps every subapp's error UX
consistent (and stops me from copy-pasting `_run_sdk` once per file).
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable

from omoios.cli._ui import CliError


def run_sdk(coro: Awaitable[Any]) -> Any:
    """Run a coroutine and translate SDK exceptions into CliError.

    Caller is expected to wrap whatever `AsyncOmoiOSClient` interaction
    they want inside the coro — this helper only owns the asyncio.run
    boundary and exception mapping.
    """
    from omoios.exceptions import (
        AuthError,
        NotFoundError,
        OmoiOSError,
        ValidationError,
    )

    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        raise
    except AuthError as exc:
        raise CliError(
            f"AuthError: {exc}\n"
            "  hint: run `omoios whoami` to confirm your key, or `omoios "
            "signup` to mint a fresh one."
        ) from exc
    except NotFoundError as exc:
        raise CliError(
            f"NotFoundError: {exc}\n"
            "  hint: double-check the resource ID; the matching `list` "
            "command shows what exists."
        ) from exc
    except ValidationError as exc:
        raise CliError(f"ValidationError: {exc}") from exc
    except OmoiOSError as exc:
        raise CliError(f"{type(exc).__name__}: {exc}") from exc
