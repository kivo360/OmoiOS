---
description: Generate comprehensive tests including unit, integration, and property-based tests
globs: ["**/test_*.py", "**/tests/**", "**/*.test.ts", "**/*.spec.ts"]
---

# Test Writer

Generate comprehensive tests following testing best practices.

## Test Types

| Type | Purpose | Speed | Isolation |
|------|---------|-------|-----------|
| **Unit** | Single function/class | Fast (<1s) | Complete |
| **Integration** | Multiple components | Medium (<10s) | Partial |
| **E2E** | Full workflow | Slow (<60s) | None |
| **Property** | Invariants over inputs | Varies | Complete |

## Python Testing with Pytest

### Unit Test Template

```python
"""Test {module} {component}.

Tests Requirements: REQ-{XXX}-001
"""
import pytest
from unittest.mock import Mock, patch

from module import Component


@pytest.fixture
def component():
    """Create component with test dependencies."""
    return Component(
        dependency=Mock(),
        config={"test": True}
    )


class TestComponent:
    """Tests for Component class."""

    def test_method_returns_expected_when_valid_input(self, component):
        """Method returns expected result for valid input."""
        # Arrange
        input_data = {"key": "value"}
        expected = {"result": "processed"}

        # Act
        result = component.method(input_data)

        # Assert
        assert result == expected

    def test_method_raises_when_invalid_input(self, component):
        """Method raises ValueError for invalid input."""
        with pytest.raises(ValueError, match="Invalid input"):
            component.method(None)

    @pytest.mark.parametrize("input_val,expected", [
        ("a", 1),
        ("b", 2),
        ("c", 3),
    ])
    def test_method_handles_various_inputs(self, component, input_val, expected):
        """Method handles different input values correctly."""
        assert component.method(input_val) == expected
```

### Integration Test Template

```python
"""Integration tests for {feature}.

Tests end-to-end flow of {workflow}.
"""
import pytest
from httpx import AsyncClient

from app.main import app
from app.database import get_db


@pytest.fixture
async def client():
    """Create test client with database."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def db_session():
    """Create isolated database session."""
    # Setup
    session = await create_test_session()
    yield session
    # Teardown
    await session.rollback()


class TestFeatureWorkflow:
    """Integration tests for feature workflow."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, client, db_session):
        """Test complete create-read-update-delete workflow."""
        # Create
        response = await client.post("/api/items", json={"name": "test"})
        assert response.status_code == 201
        item_id = response.json()["id"]

        # Read
        response = await client.get(f"/api/items/{item_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "test"

        # Update
        response = await client.put(
            f"/api/items/{item_id}",
            json={"name": "updated"}
        )
        assert response.status_code == 200

        # Delete
        response = await client.delete(f"/api/items/{item_id}")
        assert response.status_code == 204
```

### Property-Based Test Template

```python
"""Property-based tests for {module}.

Uses Hypothesis for generating test cases.
"""
from hypothesis import given, strategies as st, assume
import pytest

from module import function


class TestFunctionProperties:
    """Property-based tests for function."""

    @given(st.lists(st.integers()))
    def test_sort_is_idempotent(self, input_list):
        """Sorting twice gives same result as sorting once."""
        result1 = function(input_list)
        result2 = function(result1)
        assert result1 == result2

    @given(st.lists(st.integers(), min_size=1))
    def test_sort_preserves_length(self, input_list):
        """Sorting preserves list length."""
        result = function(input_list)
        assert len(result) == len(input_list)

    @given(st.text(min_size=1))
    def test_parse_roundtrip(self, text):
        """Parse and serialize are inverse operations."""
        assume(is_valid_format(text))
        parsed = parse(text)
        serialized = serialize(parsed)
        assert parsed == parse(serialized)
```

## TypeScript Testing with Jest/Vitest

### Unit Test Template

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Component } from './Component';

describe('Component', () => {
  let component: Component;
  let mockDependency: jest.Mock;

  beforeEach(() => {
    mockDependency = vi.fn();
    component = new Component(mockDependency);
  });

  describe('method', () => {
    it('should return expected result for valid input', () => {
      // Arrange
      const input = { key: 'value' };
      const expected = { result: 'processed' };
      mockDependency.mockReturnValue(expected);

      // Act
      const result = component.method(input);

      // Assert
      expect(result).toEqual(expected);
      expect(mockDependency).toHaveBeenCalledWith(input);
    });

    it('should throw for invalid input', () => {
      expect(() => component.method(null)).toThrow('Invalid input');
    });

    it.each([
      ['a', 1],
      ['b', 2],
      ['c', 3],
    ])('should handle input %s returning %i', (input, expected) => {
      expect(component.method(input)).toBe(expected);
    });
  });
});
```

### React Component Test Template

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Component } from './Component';

describe('Component', () => {
  it('should render initial state', () => {
    render(<Component />);
    expect(screen.getByText('Initial')).toBeInTheDocument();
  });

  it('should update on button click', async () => {
    render(<Component />);

    fireEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => {
      expect(screen.getByText('Updated')).toBeInTheDocument();
    });
  });

  it('should call callback with form data', async () => {
    const onSubmit = vi.fn();
    render(<Component onSubmit={onSubmit} />);

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'test' }
    });
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({ value: 'test' });
    });
  });
});
```

## Test Naming Convention

```
test_{what}_{scenario}_{expected_outcome}
```

Examples:
- `test_login_with_valid_credentials_returns_token`
- `test_create_user_with_duplicate_email_raises_conflict`
- `test_calculate_total_with_empty_cart_returns_zero`

## Coverage Requirements

| Category | Minimum Coverage |
|----------|-----------------|
| Business Logic | 90% |
| API Endpoints | 80% |
| Utilities | 70% |
| UI Components | 60% |

## Running Tests

```bash
# Python
pytest tests/                        # All tests
pytest tests/unit/                   # Unit tests only
pytest -x                            # Stop on first failure
pytest --cov=src --cov-report=html   # With coverage

# TypeScript
npm test                             # All tests
npm run test:unit                    # Unit tests only
npm run test:coverage                # With coverage
```
