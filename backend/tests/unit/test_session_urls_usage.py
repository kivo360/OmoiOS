"""Unit tests for session response enrichment (Wave 2 Task 5)."""

from __future__ import annotations

from types import SimpleNamespace

from omoi_os.api.routes.sessions import _session_urls


def _req(base_url: str) -> SimpleNamespace:
    return SimpleNamespace(base_url=base_url)


def test_urls_include_sse_and_ws_shapes():
    urls = _session_urls(_req("https://api.omoios.dev/"), "sid-1", None)
    assert urls["events_sse"] == "https://api.omoios.dev/api/v1/sessions/sid-1/events"
    assert urls["websocket"] == "wss://api.omoios.dev/api/v1/sessions/sid-1/ws"
    assert urls["editor"] is None


def test_urls_downgrade_ws_scheme_for_http_base():
    urls = _session_urls(_req("http://localhost:18000/"), "sid-2", None)
    assert urls["websocket"].startswith("ws://")
    assert urls["events_sse"].startswith("http://")


def test_urls_prefer_8443_for_editor():
    urls = _session_urls(
        _req("https://api.omoios.dev/"),
        "sid-3",
        {
            "tunnel_urls": {
                "3000": "https://three.modal.run",
                "8443": "https://edit.modal.run",
            }
        },
    )
    assert urls["editor"] == "https://edit.modal.run"


def test_urls_fall_back_to_first_port_when_no_8443():
    urls = _session_urls(
        _req("https://api.omoios.dev/"),
        "sid-4",
        {"tunnel_urls": {"3000": "https://three.modal.run"}},
    )
    assert urls["editor"] == "https://three.modal.run"


def test_urls_editor_none_when_tunnel_urls_missing_or_wrong_type():
    urls = _session_urls(_req("https://api.omoios.dev/"), "sid-5", {})
    assert urls["editor"] is None
    urls = _session_urls(_req("https://api.omoios.dev/"), "sid-6", {"tunnel_urls": []})
    assert urls["editor"] is None
