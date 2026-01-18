#!/usr/bin/env python
"""Get a test token by logging in to the local API.

Usage:
    python scripts/get_test_token.py --email=user@example.com --password=yourpassword

This will print out the access token that can be used for testing.
"""

import argparse
import httpx
import sys


API_URL = "http://localhost:18000"


def get_token(email: str, password: str, api_url: str) -> str | None:
    """Login and get access token."""
    try:
        response = httpx.post(
            f"{api_url}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=30.0,
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Get test token from API")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--password", required=True, help="User password")
    parser.add_argument("--api-url", default=API_URL, help=f"API URL (default: {API_URL})")
    args = parser.parse_args()

    api_url = args.api_url
    token = get_token(args.email, args.password, api_url)

    if token:
        print(f"\nAccess Token:\n{token}\n")
        print("Use with sync test:")
        print(f'  uv run python scripts/test_sync_via_http.py --live --project-id=XXX --api-key="{token}"')
        return 0
    else:
        print("\nFailed to get token")
        return 1


if __name__ == "__main__":
    sys.exit(main())
