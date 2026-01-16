"""Pytest configuration and fixtures for spec-sandbox tests."""

import pytest
from pathlib import Path

from spec_sandbox.config import SpecSandboxSettings
from spec_sandbox.reporters.array import ArrayReporter


@pytest.fixture
def array_reporter():
    """Create an ArrayReporter for testing."""
    return ArrayReporter()


@pytest.fixture
def test_settings():
    """Create test settings."""
    return SpecSandboxSettings(
        spec_id="test-spec",
        spec_title="Test Spec",
        spec_description="Test description",
        reporter_mode="array",
    )


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
