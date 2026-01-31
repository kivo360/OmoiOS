#!/usr/bin/env python3
"""
Debug script to verify environment file loading and settings configuration.

This script helps verify that .env.local takes priority over .env
and shows which environment files are being loaded.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def debug_env_files():
    """Debug which environment files are being loaded."""
    print("=" * 60)
    print("ENVIRONMENT FILES DEBUG")
    print("=" * 60)

    # Check for environment files
    env_files = []

    if os.path.exists(".env.local"):
        env_files.append(".env.local ✅")
        print("✅ .env.local exists (HIGHEST PRIORITY)")
    else:
        print("❌ .env.local not found")

    if os.path.exists(".env"):
        env_files.append(".env ✅")
        print("✅ .env exists (SECOND PRIORITY)")
    else:
        print("❌ .env not found")

    print(f"\nEnvironment files found: {len(env_files)}")
    print("Priority order: .env.local > .env > environment variables")


def debug_settings_loading():
    """Debug settings loading from different configuration classes."""
    print("\n" + "=" * 60)
    print("SETTINGS LOADING DEBUG")
    print("=" * 60)

    try:
        # Test main config settings
        from omoi_os.config import (
            load_database_settings,
            load_redis_settings,
            load_llm_settings,
            load_task_queue_settings,
            load_approval_settings,
        )

        print("\n📊 Main Configuration Settings:")
        print("-" * 40)

        # Database settings
        db_settings = load_database_settings()
        print(f"DATABASE_URL: {db_settings.url}")
        if "localhost" in db_settings.url or "127.0.0.1" in db_settings.url:
            print("✅ Using local database (docker-compose)")
        else:
            print("✅ Using remote database")

        # Redis settings
        redis_settings = load_redis_settings()
        print(f"REDIS_URL: {redis_settings.url}")

        # LLM settings
        llm_settings = load_llm_settings()
        print(f"LLM_MODEL: {llm_settings.model}")
        print(f"LLM_BASE_URL: {llm_settings.base_url or 'default'}")

        # Task queue settings
        tq_settings = load_task_queue_settings()
        print(f"TQ_AGE_CEILING: {tq_settings.age_ceiling}")

        # Approval settings
        approval_settings = load_approval_settings()
        print(f"APPROVAL_TICKET_HUMAN_REVIEW: {approval_settings.ticket_human_review}")

    except Exception as e:
        print(f"❌ Error loading main config: {e}")

        # Test validation config
        try:
            from omoi_os.config.validation import ValidationConfig

            print("\n📊 Validation Configuration:")
            print("-" * 40)
            validation_config = ValidationConfig()
            print(
                f"VALIDATION_ENABLED_BY_DEFAULT: {validation_config.enabled_by_default}"
            )
            print(f"VALIDATION_MAX_ITERATIONS: {validation_config.max_iterations}")
        except Exception as e:
            print(f"❌ Error loading validation config: {e}")

    try:
        # Test ticketing DB settings
        from omoi_os.ticketing.db import DBSettings

        print("\n📊 Ticketing DB Configuration:")
        print("-" * 40)
        db_settings = DBSettings()
        print(f"DB_HOST: {db_settings.host}")
        print(f"DB_PORT: {db_settings.port}")
        print(f"DB_NAME: {db_settings.name}")
        print(f"DB_URL: {db_settings.url()}")

    except Exception as e:
        print(f"❌ Error loading ticketing DB config: {e}")


def debug_environment_variables():
    """Debug key environment variables."""
    print("\n" + "=" * 60)
    print("ENVIRONMENT VARIABLES DEBUG")
    print("=" * 60)

    key_vars = [
        "DATABASE_URL",
        "REDIS_URL",
        "LLM_MODEL",
        "LLM_API_KEY",
        "TQ_AGE_CEILING",
        "VALIDATION_ENABLED_BY_DEFAULT",
    ]

    for var in key_vars:
        value = os.environ.get(var)
        if value:
            if "API_KEY" in var or "SECRET" in var or "PASSWORD" in var:
                # Mask sensitive values
                masked_value = value[:8] + "..." if len(value) > 8 else "***"
                print(f"{var}: {masked_value}")
            else:
                print(f"{var}: {value}")
        else:
            print(f"{var}: (not set)")


def test_priority_order():
    """Test that .env.local takes priority over .env."""
    print("\n" + "=" * 60)
    print("PRIORITY ORDER TEST")
    print("=" * 60)

    # Create a test setting to verify priority
    test_var = "DATABASE_HOST"

    print(f"Testing {test_var} priority:")

    # Check .env.local first
    if os.path.exists(".env.local"):
        with open(".env.local", "r") as f:
            content = f.read()
            if f"{test_var}=" in content:
                print("✅ Found in .env.local (will take priority)")
            else:
                print("❓ Not found in .env.local")

    # Check .env
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            content = f.read()
            if f"{test_var}=" in content:
                print("✅ Found in .env (lower priority than .env.local)")
            else:
                print("❓ Not found in .env")

    # Check final environment variable
    final_value = os.environ.get(test_var)
    if final_value:
        print(f"✅ Final {test_var}: {final_value}")
    else:
        print(f"❌ {test_var} not set in environment")


def main():
    """Run all debugging checks."""
    print("🔍 OMOiOS SETTINGS DEBUG TOOL")
    print("This tool helps verify environment file loading and settings configuration")

    debug_env_files()
    debug_settings_loading()
    debug_environment_variables()
    test_priority_order()

    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    print("=" * 60)
    print("📌 If .env.local exists, it should take priority over .env")
    print("📌 Local development should use docker-compose database")
    print("=" * 60)


if __name__ == "__main__":
    main()
