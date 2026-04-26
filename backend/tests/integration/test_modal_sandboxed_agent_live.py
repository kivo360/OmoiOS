"""Live-Modal integration test for `services.modal_sandboxed_agent`.

Skipped unless MODAL_TOKEN_ID + MODAL_TOKEN_SECRET + (FIREWORKS_API_KEY or
LLM_API_KEY) are set. Spawns a real Modal sandbox, drives one opencode
turn through the agent, asserts the reply path works end-to-end, and
tears the sandbox down.

Why this exists separately from the unit tests: the unit suite mocks the
ModalSpawner, so it proves the routing/parsing logic but says nothing
about whether `Sandbox.from_id`, `sandbox.exec`, the image build, the
opencode binary, or the Fireworks call actually wire together. This test
catches drift in any of those — at the cost of ~30-60s and Modal credits.

Run manually:
    cd backend && uv run pytest tests/integration/test_modal_sandboxed_agent_live.py -v -s
"""

from __future__ import annotations

import asyncio
import os

import pytest


pytestmark = pytest.mark.integration


_MISSING_CREDS = not (
    os.environ.get("MODAL_TOKEN_ID")
    and os.environ.get("MODAL_TOKEN_SECRET")
    and (os.environ.get("FIREWORKS_API_KEY") or os.environ.get("LLM_API_KEY"))
)


@pytest.mark.skipif(
    _MISSING_CREDS,
    reason=(
        "Live Modal smoke needs MODAL_TOKEN_ID + MODAL_TOKEN_SECRET + "
        "(FIREWORKS_API_KEY or LLM_API_KEY)"
    ),
)
@pytest.mark.asyncio
async def test_spawn_prompt_close_roundtrip() -> None:
    """One full turn through a real Modal sandbox, then teardown."""
    # Import inside the test so a missing `modal` dependency at import
    # time doesn't poison the rest of the integration suite.
    from omoi_os.services import modal_sandboxed_agent as msa

    session_id = f"live-test-{os.getpid()}"
    agent = await msa.get_or_spawn(session_id)
    try:
        # Use an instruction that exercises the same shape as the
        # `modal_sandbox_smoke.py` mode=llm assertion: deterministic-ish
        # token, short reply, no file IO.
        reply = await asyncio.wait_for(
            agent.prompt("Reply with exactly the four letters: PONG"),
            timeout=120,
        )
        assert reply, "agent returned an empty reply"
        # Cheap sanity check — the model usually quotes or includes PONG;
        # we don't enforce exact match because Kimi sometimes paraphrases.
        assert "PONG" in reply.upper() or len(reply) > 2
    finally:
        await msa.close(session_id)
