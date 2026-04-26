"""Async client context for poof probes.

Centralizes the AsyncOmoiOSClient construction so every probe has the
same auth + base URL without duplicating the import dance.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator


REPO = Path(__file__).resolve().parent.parent.parent
# Make sure the SDK + backend are importable when probes are run as
# `python -m scripts.poof.<probe>` from the repo root.
for path in (REPO / "sdk" / "python", REPO / "backend"):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


@asynccontextmanager
async def build_client() -> AsyncIterator[Any]:
    from omoios import AsyncOmoiOSClient  # noqa: PLC0415 — heavy SDK import

    from scripts.poof._settings import get_settings

    settings = get_settings()
    async with AsyncOmoiOSClient(
        base_url=settings.api_base_url,
        api_key=settings.platform_api_key,
        timeout=60.0,
    ) as client:
        yield client
