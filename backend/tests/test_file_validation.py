"""Tests for file validation helpers."""

import os
import tempfile

import pytest

from omoi_os.services.validation_helpers import (
    MAX_FILE_SIZE_KB,
    read_markdown_file,
    validate_file_size,
    validate_markdown_format,
    validate_no_path_traversal,
)


def test_validate_file_size_under_limit():
    """Test file size validation with file under limit."""
    content = "# Test\n\nSmall file content."

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        # Should not raise
        validate_file_size(temp_path)
    finally:
        os.unlink(temp_path)


def test_validate_file_size_over_limit():
    """Test file size validation with file over 100KB limit."""
    # Create file larger than 100KB
    content = "A" * (MAX_FILE_SIZE_KB * 1024 + 1000)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="too large"):
            validate_file_size(temp_path)
    finally:
        os.unlink(temp_path)


def test_validate_markdown_format():
    """Test markdown format validation."""
    # Valid markdown
    validate_markdown_format("test.md")
    validate_markdown_format("/path/to/file.md")

    # Invalid formats
    with pytest.raises(ValueError, match="markdown"):
        validate_markdown_format("test.txt")

    with pytest.raises(ValueError, match="markdown"):
        validate_markdown_format("test.pdf")

    with pytest.raises(ValueError, match="markdown"):
        validate_markdown_format("test")


def test_validate_no_path_traversal():
    """Test path traversal protection."""
    # Valid paths
    validate_no_path_traversal("/tmp/result.md")
    validate_no_path_traversal("./results/output.md")
    validate_no_path_traversal("results/output.md")

    # Invalid paths with traversal
    with pytest.raises(ValueError, match="traversal"):
        validate_no_path_traversal("../../../etc/passwd")

    with pytest.raises(ValueError, match="traversal"):
        validate_no_path_traversal("/tmp/../etc/passwd.md")

    with pytest.raises(ValueError, match="traversal"):
        validate_no_path_traversal("results/../../sensitive.md")


def test_read_markdown_file_success():
    """Test reading a valid markdown file."""
    content = "# Test Results\n\n## Summary\n\nTest content here."

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        read_content = read_markdown_file(temp_path)
        assert read_content == content
    finally:
        os.unlink(temp_path)
