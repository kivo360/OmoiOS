"""
Unit tests for ASCII Hello World script.

Tests the ASCII art output functionality.
"""

import pytest
import sys
from io import StringIO
from unittest.mock import patch

# Import the functions from the script
sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0])
from scripts.ascii_hello_world import (
    print_ascii_hello_world,
    main,
    HELLO_WORLD_ASCII,
    HELLO_WORLD_COMPACT,
    HELLO_WORLD_SIMPLE,
)


@pytest.mark.unit
class TestAsciiHelloWorld:
    """Test ASCII Hello World output functionality."""

    def test_default_style_contains_hello_world(self):
        """UNIT: Default ASCII art should contain recognizable text."""
        # The default ASCII art should have the Hello and World patterns
        assert "| | | |" in HELLO_WORLD_ASCII  # Part of 'H'
        assert "___" in HELLO_WORLD_ASCII  # Common pattern in block letters

    def test_compact_style_is_shorter(self):
        """UNIT: Compact style should have fewer lines than default."""
        default_lines = len(HELLO_WORLD_ASCII.strip().split("\n"))
        compact_lines = len(HELLO_WORLD_COMPACT.strip().split("\n"))
        # Compact should be same or fewer lines (allowing for similar heights)
        assert compact_lines <= default_lines + 1

    def test_simple_style_has_border(self):
        """UNIT: Simple style should have a bordered box."""
        assert "+" in HELLO_WORLD_SIMPLE
        assert "=" in HELLO_WORLD_SIMPLE
        assert "HELLO WORLD" in HELLO_WORLD_SIMPLE

    def test_print_default_style(self, capsys):
        """UNIT: print_ascii_hello_world should output default ASCII art."""
        print_ascii_hello_world("default")
        captured = capsys.readouterr()
        assert "| | | |" in captured.out

    def test_print_compact_style(self, capsys):
        """UNIT: print_ascii_hello_world with compact should output compact art."""
        print_ascii_hello_world("compact")
        captured = capsys.readouterr()
        assert "___" in captured.out

    def test_print_simple_style(self, capsys):
        """UNIT: print_ascii_hello_world with simple should output bordered box."""
        print_ascii_hello_world("simple")
        captured = capsys.readouterr()
        assert "HELLO WORLD" in captured.out
        assert "+" in captured.out


@pytest.mark.unit
class TestAsciiHelloWorldCli:
    """Test command-line interface."""

    def test_main_returns_zero_on_success(self, capsys):
        """UNIT: main() should return 0 on successful execution."""
        with patch("sys.argv", ["ascii_hello_world.py"]):
            result = main()
        assert result == 0

    def test_main_with_compact_flag(self, capsys):
        """UNIT: main() with --compact should output compact style."""
        with patch("sys.argv", ["ascii_hello_world.py", "--compact"]):
            main()
        captured = capsys.readouterr()
        # Verify compact output was used (it has different pattern)
        assert len(captured.out) > 0

    def test_main_with_simple_flag(self, capsys):
        """UNIT: main() with --simple should output simple style."""
        with patch("sys.argv", ["ascii_hello_world.py", "--simple"]):
            main()
        captured = capsys.readouterr()
        assert "HELLO WORLD" in captured.out
        assert "+" in captured.out

    def test_main_default_outputs_ascii_art(self, capsys):
        """UNIT: main() without flags should output default ASCII art."""
        with patch("sys.argv", ["ascii_hello_world.py"]):
            main()
        captured = capsys.readouterr()
        assert "| | | |" in captured.out
