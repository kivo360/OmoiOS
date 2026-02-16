"""Unit tests for frontend capability detection.

Tests the keyword-matching logic that determines whether a task
needs live preview support based on ticket title and description.
"""

from omoi_os.api.routes.tickets import _detect_frontend_capabilities


class TestDetectFrontendCapabilities:
    """Tests for _detect_frontend_capabilities()."""

    # ================================================================
    # Positive cases — should detect frontend keywords
    # ================================================================

    def test_react_component_detected(self):
        """Tasks mentioning React should be detected as frontend."""
        result = _detect_frontend_capabilities("Build a React counter component", None)
        assert "react" in result
        assert "component" in result

    def test_tailwind_ui_detected(self):
        """Tasks mentioning Tailwind CSS should be detected."""
        result = _detect_frontend_capabilities(
            "Add Tailwind styling to dashboard",
            "Style the dashboard with Tailwind CSS classes",
        )
        assert "tailwind" in result
        assert "dashboard" in result
        assert "css" in result

    def test_vue_frontend_detected(self):
        """Tasks mentioning Vue should be detected."""
        result = _detect_frontend_capabilities(
            "Create Vue login form", "Build a responsive login form"
        )
        assert "vue" in result
        assert "form" in result
        assert "responsive" in result

    def test_next_vite_detected(self):
        """Tasks mentioning Next.js or Vite should be detected."""
        result = _detect_frontend_capabilities("Set up Next.js with Vite", None)
        assert "next" in result
        assert "vite" in result

    def test_description_only_detection(self):
        """Keywords in description (not title) should still match."""
        result = _detect_frontend_capabilities(
            "Implement feature",
            "Create a button component with React and styled-components",
        )
        assert "button" in result
        assert "component" in result
        assert "react" in result
        assert "styled" in result

    def test_case_insensitive(self):
        """Detection should be case-insensitive."""
        result = _detect_frontend_capabilities(
            "Build a REACT COMPONENT", "With TAILWIND CSS"
        )
        assert "react" in result
        assert "component" in result
        assert "tailwind" in result

    def test_angular_svelte_detected(self):
        """Other frontend frameworks should be detected."""
        result = _detect_frontend_capabilities("Create Angular component", None)
        assert "angular" in result
        assert "component" in result

    def test_html_layout_detected(self):
        """HTML/layout keywords should be detected."""
        result = _detect_frontend_capabilities(
            "Fix HTML layout", "The page layout is broken on mobile"
        )
        assert "html" in result
        assert "layout" in result
        assert "page" in result

    # ================================================================
    # Negative cases — should NOT detect frontend keywords
    # ================================================================

    def test_python_script_not_detected(self):
        """Pure Python tasks should return empty list."""
        result = _detect_frontend_capabilities(
            "Write a Python data analysis script",
            "Analyze CSV data and generate report using pandas",
        )
        assert result == []

    def test_backend_api_not_detected(self):
        """Backend API tasks should return empty list."""
        result = _detect_frontend_capabilities(
            "Add REST endpoint for user authentication",
            "Implement JWT token validation in FastAPI",
        )
        assert result == []

    def test_database_migration_not_detected(self):
        """Database tasks should return empty list."""
        result = _detect_frontend_capabilities(
            "Create database migration",
            "Add new columns to the tasks table for priority scoring",
        )
        assert result == []

    def test_empty_inputs(self):
        """Empty title and None description should return empty list."""
        result = _detect_frontend_capabilities("", None)
        assert result == []

    # ================================================================
    # Edge cases
    # ================================================================

    def test_mixed_frontend_backend(self):
        """Tasks with both frontend and backend keywords should detect frontend ones."""
        result = _detect_frontend_capabilities(
            "Add React frontend for API endpoint",
            "Build a dashboard UI that calls the REST API",
        )
        assert "react" in result
        assert "frontend" in result
        assert "dashboard" in result
        assert "ui" in result

    def test_substring_matching(self):
        """Keywords use substring matching — 'web' in 'webserver' matches."""
        # "web" is a substring of "webserver" so it matches
        # "page" is NOT a substring of "pagination" (p-a-g-i-n-a-t-i-o-n)
        result = _detect_frontend_capabilities("Add pagination to webserver", None)
        assert "web" in result
        assert "page" not in result  # "page" != substring of "pagination"

    def test_none_description_handled(self):
        """None description should not cause errors."""
        result = _detect_frontend_capabilities("Build a React app", None)
        assert "react" in result

    def test_returns_list_type(self):
        """Result should always be a list."""
        result = _detect_frontend_capabilities("test", None)
        assert isinstance(result, list)

    def test_no_duplicates_in_result(self):
        """Each keyword should appear at most once even if text repeats it."""
        result = _detect_frontend_capabilities(
            "React React React component component", None
        )
        # Each keyword appears once in the result
        assert result.count("react") == 1
        assert result.count("component") == 1
