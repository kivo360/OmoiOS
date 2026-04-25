"""Unit tests for the spec §01 three-token AuthContext dispatcher."""

from __future__ import annotations

import pytest

from omoi_os.api.dependencies import _classify_token


pytestmark = pytest.mark.unit


class TestClassifyToken:
    """_classify_token picks the right bucket based on prefix only."""

    def test_session_bearer(self):
        assert _classify_token("sess_tok_deadbeef") == "session"

    def test_platform_live_key(self):
        assert _classify_token("rpk_live_abc") == "platform"
        assert _classify_token("sk_live_xyz") == "platform"

    def test_platform_test_key(self):
        assert _classify_token("rpk_test_abc") == "platform"
        assert _classify_token("sk_test_xyz") == "platform"

    def test_jwt_default(self):
        # JWT tokens start with 'eyJ' (base64 of '{"a') but the classifier
        # treats anything unrecognized as a user JWT. That's the conservative
        # fallback — the actual verifier still rejects malformed JWTs.
        assert _classify_token("eyJhbGciOiJIUzI1NiJ9.x.y") == "user"
        assert _classify_token("") == "user"  # empty routes to JWT verify, which fails
        assert _classify_token("random-string") == "user"
