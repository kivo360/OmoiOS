"""File validation helpers for result submission."""

import os

MAX_FILE_SIZE_KB = 100


def validate_file_size(file_path: str) -> None:
    """Ensure file is under 100KB.

    Args:
        file_path: Path to file to validate

    Raises:
        ValueError: If file exceeds size limit
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    size_kb = os.path.getsize(file_path) / 1024
    if size_kb > MAX_FILE_SIZE_KB:
        raise ValueError(
            f"File too large: {size_kb:.2f}KB exceeds maximum of {MAX_FILE_SIZE_KB}KB"
        )


def validate_markdown_format(file_path: str) -> None:
    """Ensure file is markdown format.

    Args:
        file_path: Path to file to validate

    Raises:
        ValueError: If file is not markdown
    """
    if not file_path.endswith(".md"):
        raise ValueError(f"File must be markdown (.md), got: {file_path}")


def validate_no_path_traversal(file_path: str) -> None:
    """Prevent directory traversal attacks.

    Args:
        file_path: Path to validate

    Raises:
        ValueError: If path contains traversal patterns
    """
    if ".." in file_path:
        raise ValueError("Directory traversal detected in file path")


def read_markdown_file(file_path: str) -> str:
    """Read and validate markdown file.

    Performs all validation checks and returns file content.

    Args:
        file_path: Path to markdown file

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file fails validation (size, format, security)
    """
    # Security checks first
    validate_no_path_traversal(file_path)
    validate_markdown_format(file_path)
    validate_file_size(file_path)

    # File existence check
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Markdown file not found: {file_path}")

    # Read content
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
