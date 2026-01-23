"""Mermaid diagram validation and sanitization utilities.

This module provides tools for:
1. Sanitizing Mermaid diagrams to fix common syntax issues
2. Validating Mermaid syntax using mermaid-cli (if available)
3. Extracting Mermaid code blocks from markdown content

Common issues this handles:
- Unquoted special characters in node labels ({}, (), /, |, <, >)
- Missing quotes around subgraph names with spaces
- Curly braces being interpreted as rhombus shapes instead of literals
"""

import asyncio
import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Characters that require quoting in Mermaid node labels
# Note: () and [] are excluded because they're shape delimiters
# We only want to quote when these appear INSIDE the label content
SPECIAL_CHARS_IN_CONTENT = frozenset("{}/|<>")

# Pattern to match standard rectangle node definitions: ID[content]
# Captures: node_id, bracket_open, content, bracket_close
# Excludes special shape syntaxes like [( )], [[ ]], [/ \] where the special char
# is immediately followed by content and closing with the corresponding char
NODE_RECT_PATTERN = re.compile(
    r'(\b[A-Za-z_][A-Za-z0-9_]*)\s*(\[)(?!\[.*\]\]|\(.*\)\]|/.*\\\])([^\]]+)(\])'
)

# Pattern to match subgraph declarations without quotes
SUBGRAPH_PATTERN = re.compile(
    r'(subgraph\s+)([^"\n][^\n]*?)(\n|$)'
)

# Pattern to extract mermaid code blocks from markdown
MERMAID_BLOCK_PATTERN = re.compile(
    r'```mermaid\s*\n(.*?)\n```',
    re.DOTALL | re.IGNORECASE
)


@dataclass
class MermaidValidationResult:
    """Result of Mermaid diagram validation."""

    is_valid: bool
    error_message: Optional[str] = None
    sanitized_code: Optional[str] = None
    original_code: Optional[str] = None

    @property
    def needs_sanitization(self) -> bool:
        """Check if the code was modified during sanitization."""
        return (
            self.sanitized_code is not None
            and self.original_code is not None
            and self.sanitized_code != self.original_code
        )


def _needs_quoting(content: str) -> bool:
    """Check if a node label content needs to be quoted.

    Args:
        content: The text content inside a node label

    Returns:
        True if the content contains special characters and isn't already quoted
    """
    # Already quoted
    if content.startswith('"') and content.endswith('"'):
        return False
    if content.startswith("'") and content.endswith("'"):
        return False

    # Check for special characters that need quoting
    # These are characters that have special meaning in Mermaid syntax
    return any(char in content for char in SPECIAL_CHARS_IN_CONTENT)


def _quote_node_label(match: re.Match) -> str:
    """Quote a node label if it contains special characters.

    Args:
        match: Regex match object with groups (node_id, bracket_open, content, bracket_close)

    Returns:
        The node definition with quoted content if needed
    """
    node_id = match.group(1)
    bracket_open = match.group(2)
    content = match.group(3)
    bracket_close = match.group(4)

    if _needs_quoting(content):
        # Escape any existing double quotes in the content
        escaped_content = content.replace('"', '#quot;')
        return f'{node_id}{bracket_open}"{escaped_content}"{bracket_close}'

    return match.group(0)


def _quote_subgraph_label(match: re.Match) -> str:
    """Quote a subgraph label if it contains spaces or special characters.

    Args:
        match: Regex match object with groups (subgraph_keyword, label, trailing)

    Returns:
        The subgraph declaration with quoted label if needed
    """
    keyword = match.group(1)
    label = match.group(2).strip()
    trailing = match.group(3)

    # Already quoted
    if label.startswith('"') and label.endswith('"'):
        return match.group(0)

    # Contains spaces or special characters - needs quoting
    if ' ' in label or any(char in label for char in SPECIAL_CHARS_IN_CONTENT):
        return f'{keyword}"{label}"{trailing}'

    return match.group(0)


def sanitize_mermaid_diagram(code: str) -> str:
    """Sanitize a Mermaid diagram to fix common syntax issues.

    This function:
    1. Quotes node labels containing special characters ({}, (), /, |, <, >)
    2. Quotes subgraph names containing spaces or special characters
    3. Escapes existing quotes inside labels

    Args:
        code: Raw Mermaid diagram code

    Returns:
        Sanitized Mermaid diagram code

    Example:
        >>> code = '''flowchart LR
        ...     API[/projects/{id}/settings]
        ...     subgraph API Layer
        ...         API --> DB
        ...     end
        ... '''
        >>> sanitized = sanitize_mermaid_diagram(code)
        >>> # Result: API["/projects/{id}/settings"] and subgraph "API Layer"
    """
    if not code or not code.strip():
        return code

    # Step 1: Quote node labels with special characters
    sanitized = NODE_RECT_PATTERN.sub(_quote_node_label, code)

    # Step 2: Quote subgraph labels with spaces/special chars
    sanitized = SUBGRAPH_PATTERN.sub(_quote_subgraph_label, sanitized)

    return sanitized


def extract_mermaid_blocks(markdown_content: str) -> list[str]:
    """Extract all Mermaid code blocks from markdown content.

    Args:
        markdown_content: Markdown text potentially containing ```mermaid blocks

    Returns:
        List of Mermaid diagram code strings (without the fence markers)
    """
    matches = MERMAID_BLOCK_PATTERN.findall(markdown_content)
    return [match.strip() for match in matches]


def sanitize_markdown_mermaid_blocks(markdown_content: str) -> str:
    """Sanitize all Mermaid blocks within markdown content.

    Args:
        markdown_content: Markdown text containing ```mermaid blocks

    Returns:
        Markdown with sanitized Mermaid blocks
    """
    def replace_block(match: re.Match) -> str:
        original_code = match.group(1)
        sanitized_code = sanitize_mermaid_diagram(original_code)
        return f'```mermaid\n{sanitized_code}\n```'

    return MERMAID_BLOCK_PATTERN.sub(replace_block, markdown_content)


def _check_mermaid_cli_available() -> bool:
    """Check if mermaid-cli is available via npx."""
    try:
        # Check if npx is available
        result = subprocess.run(
            ['npx', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


async def validate_mermaid_with_cli(
    code: str,
    timeout_seconds: float = 10.0
) -> MermaidValidationResult:
    """Validate Mermaid diagram syntax using mermaid-cli.

    This function uses the official mermaid-cli (via npx) to validate
    the diagram syntax. It requires Node.js to be installed.

    Args:
        code: Mermaid diagram code to validate
        timeout_seconds: Maximum time to wait for validation

    Returns:
        MermaidValidationResult with validation status and any error messages

    Note:
        If mermaid-cli is not available, returns a result indicating
        the validation could not be performed (is_valid=True with a warning).
    """
    if not code or not code.strip():
        return MermaidValidationResult(
            is_valid=False,
            error_message="Empty diagram code",
            original_code=code
        )

    # First, try sanitizing the code
    sanitized = sanitize_mermaid_diagram(code)

    # Check if CLI is available
    if not _check_mermaid_cli_available():
        logger.warning(
            "mermaid-cli not available. Install with: npm install -g @mermaid-js/mermaid-cli"
        )
        return MermaidValidationResult(
            is_valid=True,  # Can't validate, assume valid
            error_message="mermaid-cli not available for validation",
            sanitized_code=sanitized,
            original_code=code
        )

    # Create temp file for input
    input_file = None
    output_file = None

    try:
        # Write diagram to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.mmd',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(sanitized)
            input_file = f.name

        # Create temp output path
        output_file = tempfile.mktemp(suffix='.svg')

        # Run mermaid-cli
        process = await asyncio.create_subprocess_exec(
            'npx', '@mermaid-js/mermaid-cli',
            '-i', input_file,
            '-o', output_file,
            '--quiet',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return MermaidValidationResult(
                is_valid=False,
                error_message="Mermaid validation timed out",
                sanitized_code=sanitized,
                original_code=code
            )

        if process.returncode == 0:
            return MermaidValidationResult(
                is_valid=True,
                sanitized_code=sanitized,
                original_code=code
            )
        else:
            error_output = stderr.decode('utf-8') if stderr else stdout.decode('utf-8')
            # Clean up error message
            error_lines = [
                line for line in error_output.split('\n')
                if line.strip() and not line.startswith('Generating')
            ]
            error_message = '\n'.join(error_lines) or "Unknown validation error"

            return MermaidValidationResult(
                is_valid=False,
                error_message=error_message,
                sanitized_code=sanitized,
                original_code=code
            )

    except Exception as e:
        logger.exception("Error during Mermaid validation")
        return MermaidValidationResult(
            is_valid=False,
            error_message=f"Validation error: {str(e)}",
            sanitized_code=sanitized,
            original_code=code
        )
    finally:
        # Cleanup temp files
        if input_file and os.path.exists(input_file):
            try:
                os.unlink(input_file)
            except OSError:
                pass
        if output_file and os.path.exists(output_file):
            try:
                os.unlink(output_file)
            except OSError:
                pass


def validate_mermaid_sync(
    code: str,
    timeout_seconds: float = 10.0
) -> MermaidValidationResult:
    """Synchronous version of validate_mermaid_with_cli.

    Use this when you're not in an async context.

    Args:
        code: Mermaid diagram code to validate
        timeout_seconds: Maximum time to wait for validation

    Returns:
        MermaidValidationResult with validation status and any error messages
    """
    return asyncio.run(validate_mermaid_with_cli(code, timeout_seconds))


# Convenience aliases
sanitize = sanitize_mermaid_diagram
validate = validate_mermaid_with_cli
validate_sync = validate_mermaid_sync
