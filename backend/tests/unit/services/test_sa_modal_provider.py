"""Unit tests for OmoiOsModalProvider construction and configuration.

DB-free, modal-call-free tests focused on option wiring. Live Modal
sandbox lifecycle is covered by the smoke probe in Task #8.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sandboxagent.providers.modal import ModalProvider

from omoi_os.services.sa_modal_provider import (
    OMOI_APP_NAME,
    OMOI_DEFAULT_MEMORY_MIB,
    OMOI_DEFAULT_TIMEOUT_SECONDS,
    OmoiOsModalProvider,
)


pytestmark = pytest.mark.unit


def _fake_image() -> MagicMock:
    """Stand-in for a modal.Image so tests don't hit the real Modal SDK."""
    return MagicMock(name="FakeModalImage")


class TestOmoiOsModalProviderConstruction:
    def test_subclasses_modal_provider(self) -> None:
        provider = OmoiOsModalProvider(image=_fake_image())
        assert isinstance(provider, ModalProvider)

    def test_default_app_name(self) -> None:
        provider = OmoiOsModalProvider(image=_fake_image())
        assert provider.app_name == OMOI_APP_NAME

    def test_default_agent_port_3000(self) -> None:
        provider = OmoiOsModalProvider(image=_fake_image())
        assert provider.agent_port == 3000

    def test_provider_name_is_modal(self) -> None:
        provider = OmoiOsModalProvider(image=_fake_image())
        assert provider.name == "modal"

    def test_default_cwd_is_root(self) -> None:
        provider = OmoiOsModalProvider(image=_fake_image())
        assert provider.default_cwd == "/root"


class TestEnvVarWiring:
    def test_env_vars_passed_to_create_secrets(self) -> None:
        env = {"BROKER_URL": "https://broker.test", "SESSION_TOKEN": "tok-1"}
        provider = OmoiOsModalProvider(env_vars=env, image=_fake_image())
        # Inspect the wired ModalProviderOptions
        assert provider.options.create["secrets"] == env

    def test_no_env_vars_yields_empty_secrets(self) -> None:
        provider = OmoiOsModalProvider(image=_fake_image())
        assert provider.options.create["secrets"] == {}

    def test_env_vars_are_copied_not_referenced(self) -> None:
        env = {"K": "V"}
        provider = OmoiOsModalProvider(env_vars=env, image=_fake_image())
        env["MUTATION"] = "should-not-leak"
        assert "MUTATION" not in provider.options.create["secrets"]


class TestResourceDefaults:
    def test_default_memory_4gib(self) -> None:
        provider = OmoiOsModalProvider(image=_fake_image())
        assert provider.options.create["memory_mib"] == OMOI_DEFAULT_MEMORY_MIB

    def test_default_timeout_one_hour(self) -> None:
        provider = OmoiOsModalProvider(image=_fake_image())
        assert provider.options.create["timeout"] == OMOI_DEFAULT_TIMEOUT_SECONDS

    def test_memory_override(self) -> None:
        provider = OmoiOsModalProvider(memory_mib=8192, image=_fake_image())
        assert provider.options.create["memory_mib"] == 8192

    def test_timeout_override(self) -> None:
        provider = OmoiOsModalProvider(timeout_seconds=300, image=_fake_image())
        assert provider.options.create["timeout"] == 300


class TestEncryptedPorts:
    def test_default_no_extra_ports(self) -> None:
        provider = OmoiOsModalProvider(image=_fake_image())
        assert provider.options.create["encrypted_ports"] == []

    def test_extra_ports_propagated(self) -> None:
        provider = OmoiOsModalProvider(
            encrypted_ports=[8080, 9090], image=_fake_image()
        )
        assert provider.options.create["encrypted_ports"] == [8080, 9090]

    def test_ports_are_copied_not_referenced(self) -> None:
        ports = [8080]
        provider = OmoiOsModalProvider(encrypted_ports=ports, image=_fake_image())
        ports.append(9999)
        assert provider.options.create["encrypted_ports"] == [8080]


class TestImage:
    def test_explicit_image_propagated(self) -> None:
        img = _fake_image()
        provider = OmoiOsModalProvider(image=img)
        assert provider.options.image is img

    def test_app_name_override(self) -> None:
        provider = OmoiOsModalProvider(app_name="custom-app", image=_fake_image())
        assert provider.app_name == "custom-app"
