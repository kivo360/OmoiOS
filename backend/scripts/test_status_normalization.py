#!/usr/bin/env python3
"""
Test status normalization to ensure all variations are handled.

Run this to verify the normalization map is complete.
"""

from organize_docs import normalize_status, STATUS_NORMALIZATION_MAP, ALLOWED_STATUSES


def test_all_mappings():
    """Test that all mapped statuses normalize correctly."""
    print("🧪 Testing status normalization...")
    print()

    failures = []

    for raw, expected in STATUS_NORMALIZATION_MAP.items():
        result = normalize_status(raw)

        if result != expected:
            failures.append(f"  ❌ '{raw}' → '{result}' (expected '{expected}')")

        if result not in ALLOWED_STATUSES:
            failures.append(f"  ❌ '{raw}' → '{result}' (not in ALLOWED_STATUSES)")

    if failures:
        print("❌ Normalization failures:")
        for failure in failures:
            print(failure)
        return False
    else:
        print(f"✅ All {len(STATUS_NORMALIZATION_MAP)} status mappings valid")
        return True


def test_common_variations():
    """Test common status variations."""
    print()
    print("Testing common variations:")
    print()

    test_cases = [
        ("Completed", "Implemented"),
        ("WIP", "Draft"),
        ("In Progress", "Draft"),
        ("Done", "Implemented"),
        ("Under Review", "Review"),
        ("Deprecated", "Archived"),
        (None, "Draft"),
        ("", "Draft"),
        ("Unknown Status", "Draft"),  # Should default
    ]

    all_passed = True

    for raw, expected in test_cases:
        result = normalize_status(raw)
        status = "✅" if result == expected else "❌"
        print(
            f"  {status} normalize_status({repr(raw)}) → '{result}' (expected '{expected}')"
        )

        if result != expected:
            all_passed = False

    return all_passed


def show_normalization_table():
    """Show normalization table by category."""
    print()
    print("📋 Status Normalization Reference:")
    print("=" * 60)

    for canonical in sorted(ALLOWED_STATUSES):
        variants = [
            raw
            for raw, norm in STATUS_NORMALIZATION_MAP.items()
            if norm == canonical and raw != canonical
        ]

        print(f"\n{canonical}:")
        for variant in sorted(variants, key=lambda x: str(x)):
            print(f"  - {repr(variant)}")


if __name__ == "__main__":
    all_passed = True

    # Run tests
    all_passed &= test_all_mappings()
    all_passed &= test_common_variations()

    # Show reference
    show_normalization_table()

    print()
    if all_passed:
        print("✅ All status normalization tests passed")
        exit(0)
    else:
        print("❌ Some tests failed")
        exit(1)
