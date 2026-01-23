"""Unit tests for SpecDrivenOptionsSchema.

Tests cover:
- Default values are correct
- Invalid strictness enum rejected
- Coverage < 0 rejected, > 100 rejected
- Partial updates work correctly
"""

import pytest
from pydantic import ValidationError

from omoi_os.schemas.spec_driven import (
    SpecDrivenOptionsSchema,
    SpecDrivenOptionsUpdate,
    StrictnessLevel,
)


@pytest.mark.unit
class TestSpecDrivenOptionsSchemaDefaults:
    """Test default values for SpecDrivenOptionsSchema."""

    def test_default_values_are_correct(self):
        """UNIT: Default values should match expected defaults."""
        schema = SpecDrivenOptionsSchema()

        assert schema.enabled is False
        assert schema.strictness == StrictnessLevel.MODERATE
        assert schema.require_spec_approval is True
        assert schema.min_test_coverage == 80.0

    def test_default_strictness_is_moderate(self):
        """UNIT: Strictness should default to 'moderate'."""
        schema = SpecDrivenOptionsSchema()
        assert schema.strictness == "moderate"

    def test_model_dump_returns_expected_structure(self):
        """UNIT: model_dump should return correct structure."""
        schema = SpecDrivenOptionsSchema()
        data = schema.model_dump()

        assert data == {
            "enabled": False,
            "strictness": "moderate",
            "require_spec_approval": True,
            "min_test_coverage": 80.0,
        }


@pytest.mark.unit
class TestSpecDrivenOptionsSchemaValidation:
    """Test validation for SpecDrivenOptionsSchema."""

    def test_valid_strictness_values_accepted(self):
        """UNIT: All valid strictness values should be accepted."""
        for strictness in ["strict", "moderate", "relaxed"]:
            schema = SpecDrivenOptionsSchema(strictness=strictness)
            assert schema.strictness == strictness

    def test_valid_strictness_enum_values_accepted(self):
        """UNIT: StrictnessLevel enum values should be accepted."""
        for level in StrictnessLevel:
            schema = SpecDrivenOptionsSchema(strictness=level)
            assert schema.strictness == level.value

    def test_invalid_strictness_rejected(self):
        """UNIT: Invalid strictness value should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SpecDrivenOptionsSchema(strictness="invalid")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "strictness" in str(errors[0]["loc"])

    def test_coverage_below_zero_rejected(self):
        """UNIT: min_test_coverage < 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SpecDrivenOptionsSchema(min_test_coverage=-1)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "min_test_coverage" in str(errors[0]["loc"])

    def test_coverage_above_100_rejected(self):
        """UNIT: min_test_coverage > 100 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SpecDrivenOptionsSchema(min_test_coverage=101)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "min_test_coverage" in str(errors[0]["loc"])

    def test_coverage_at_boundaries_accepted(self):
        """UNIT: min_test_coverage at 0 and 100 should be accepted."""
        schema_zero = SpecDrivenOptionsSchema(min_test_coverage=0)
        assert schema_zero.min_test_coverage == 0

        schema_hundred = SpecDrivenOptionsSchema(min_test_coverage=100)
        assert schema_hundred.min_test_coverage == 100

    def test_coverage_decimal_values_accepted(self):
        """UNIT: Decimal values for coverage should be accepted."""
        schema = SpecDrivenOptionsSchema(min_test_coverage=75.5)
        assert schema.min_test_coverage == 75.5

    def test_enabled_boolean_only(self):
        """UNIT: enabled field should only accept boolean values."""
        schema_true = SpecDrivenOptionsSchema(enabled=True)
        assert schema_true.enabled is True

        schema_false = SpecDrivenOptionsSchema(enabled=False)
        assert schema_false.enabled is False

    def test_require_spec_approval_boolean_only(self):
        """UNIT: require_spec_approval should only accept boolean values."""
        schema_true = SpecDrivenOptionsSchema(require_spec_approval=True)
        assert schema_true.require_spec_approval is True

        schema_false = SpecDrivenOptionsSchema(require_spec_approval=False)
        assert schema_false.require_spec_approval is False


@pytest.mark.unit
class TestSpecDrivenOptionsSchemaFromDict:
    """Test creating schema from dictionary (simulating JSONB load)."""

    def test_full_dict_creates_valid_schema(self):
        """UNIT: Complete dictionary should create valid schema."""
        data = {
            "enabled": True,
            "strictness": "strict",
            "require_spec_approval": False,
            "min_test_coverage": 90.0,
        }

        schema = SpecDrivenOptionsSchema(**data)

        assert schema.enabled is True
        assert schema.strictness == "strict"
        assert schema.require_spec_approval is False
        assert schema.min_test_coverage == 90.0

    def test_partial_dict_uses_defaults(self):
        """UNIT: Partial dictionary should fill missing fields with defaults."""
        data = {"enabled": True}

        schema = SpecDrivenOptionsSchema(**data)

        assert schema.enabled is True
        assert schema.strictness == "moderate"  # default
        assert schema.require_spec_approval is True  # default
        assert schema.min_test_coverage == 80.0  # default

    def test_empty_dict_uses_all_defaults(self):
        """UNIT: Empty dictionary should use all defaults."""
        schema = SpecDrivenOptionsSchema(**{})

        assert schema.enabled is False
        assert schema.strictness == "moderate"
        assert schema.require_spec_approval is True
        assert schema.min_test_coverage == 80.0


@pytest.mark.unit
class TestSpecDrivenOptionsUpdate:
    """Test SpecDrivenOptionsUpdate for partial updates."""

    def test_all_fields_optional(self):
        """UNIT: All fields should be optional in update schema."""
        update = SpecDrivenOptionsUpdate()

        assert update.enabled is None
        assert update.strictness is None
        assert update.require_spec_approval is None
        assert update.min_test_coverage is None

    def test_partial_update_only_sets_provided_fields(self):
        """UNIT: Only provided fields should be set in update."""
        update = SpecDrivenOptionsUpdate(enabled=True, min_test_coverage=95.0)

        assert update.enabled is True
        assert update.strictness is None
        assert update.require_spec_approval is None
        assert update.min_test_coverage == 95.0

    def test_model_dump_exclude_unset(self):
        """UNIT: model_dump with exclude_unset should only include set fields."""
        update = SpecDrivenOptionsUpdate(strictness="strict")

        data = update.model_dump(exclude_unset=True)

        assert data == {"strictness": "strict"}

    def test_update_coverage_validation(self):
        """UNIT: Update schema should validate coverage bounds."""
        with pytest.raises(ValidationError):
            SpecDrivenOptionsUpdate(min_test_coverage=-5)

        with pytest.raises(ValidationError):
            SpecDrivenOptionsUpdate(min_test_coverage=105)

    def test_update_strictness_validation(self):
        """UNIT: Update schema should validate strictness enum."""
        with pytest.raises(ValidationError):
            SpecDrivenOptionsUpdate(strictness="invalid")

    def test_update_with_valid_strictness(self):
        """UNIT: Update with valid strictness should work."""
        for level in ["strict", "moderate", "relaxed"]:
            update = SpecDrivenOptionsUpdate(strictness=level)
            assert update.strictness == level


@pytest.mark.unit
class TestStrictnessLevelEnum:
    """Test StrictnessLevel enum."""

    def test_enum_values(self):
        """UNIT: Enum should have expected values."""
        assert StrictnessLevel.STRICT.value == "strict"
        assert StrictnessLevel.MODERATE.value == "moderate"
        assert StrictnessLevel.RELAXED.value == "relaxed"

    def test_enum_from_string(self):
        """UNIT: Enum should be creatable from string value."""
        assert StrictnessLevel("strict") == StrictnessLevel.STRICT
        assert StrictnessLevel("moderate") == StrictnessLevel.MODERATE
        assert StrictnessLevel("relaxed") == StrictnessLevel.RELAXED

    def test_enum_is_str_subclass(self):
        """UNIT: StrictnessLevel should be string-compatible."""
        level = StrictnessLevel.STRICT
        assert isinstance(level, str)
        assert level == "strict"
