#!/usr/bin/env python3
"""
Quick API test for multi-tenant filtering endpoints.

Tests the protected endpoints with real authentication.
Run: uv run python scripts/test_multitenant_api.py
"""

import asyncio
import httpx
import json
from typing import Any


BASE_URL = "http://localhost:18000"
EMAIL = "kevin@autoworkz.org"
PASSWORD = "blueWhales44!"


def print_response(name: str, response: httpx.Response, show_data: bool = True):
    """Pretty print a response."""
    status_emoji = "✅" if response.status_code < 400 else "❌"
    print(f"\n{status_emoji} {name}: {response.status_code}")

    if show_data:
        try:
            data = response.json()
            if isinstance(data, list):
                print(f"   Items returned: {len(data)}")
                if data and len(data) <= 5:
                    for item in data:
                        if isinstance(item, dict):
                            # Show key fields
                            id_val = item.get("id", item.get("ticket_id", "?"))[:8] + "..."
                            name_val = item.get("title", item.get("name", item.get("description", "?")))
                            if isinstance(name_val, str) and len(name_val) > 40:
                                name_val = name_val[:40] + "..."
                            print(f"      - {id_val}: {name_val}")
                elif data and len(data) > 5:
                    print(f"   (showing first 5)")
                    for item in data[:5]:
                        if isinstance(item, dict):
                            id_val = str(item.get("id", item.get("ticket_id", "?")))[:8] + "..."
                            name_val = item.get("title", item.get("name", item.get("description", "?")))
                            if isinstance(name_val, str) and len(name_val) > 40:
                                name_val = name_val[:40] + "..."
                            print(f"      - {id_val}: {name_val}")
            elif isinstance(data, dict):
                if "total" in data:
                    print(f"   Total: {data.get('total', '?')}")
                if "projects" in data:
                    print(f"   Projects: {len(data['projects'])}")
                if "tickets" in data:
                    print(f"   Tickets: {len(data['tickets'])}")
                if "access_token" in data:
                    print(f"   Token received: {data['access_token'][:20]}...")
                if "error" in data or "detail" in data:
                    print(f"   Error: {data.get('error', data.get('detail', '?'))}")
        except Exception as e:
            print(f"   Raw: {response.text[:200]}")


async def main():
    print("=" * 60)
    print("🔐 Multi-Tenant API Endpoint Test")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"User: {EMAIL}")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Step 1: Login
        print("\n" + "-" * 40)
        print("📝 Step 1: Authentication")
        print("-" * 40)

        login_response = await client.post("/api/v1/auth/login", json={
            "email": EMAIL,
            "password": PASSWORD
        })
        print_response("Login", login_response)

        if login_response.status_code != 200:
            print("\n❌ Login failed - cannot continue tests")
            return

        token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Get current user info
        print("\n" + "-" * 40)
        print("👤 Step 2: Current User Info")
        print("-" * 40)

        me_response = await client.get("/api/v1/auth/me", headers=headers)
        print_response("Current User", me_response)
        if me_response.status_code == 200:
            user_data = me_response.json()
            print(f"   Email: {user_data.get('email')}")
            print(f"   Name: {user_data.get('full_name')}")
            print(f"   ID: {user_data.get('id')}")

        # Step 3: Test Projects endpoint (multi-tenant filtered)
        print("\n" + "-" * 40)
        print("📁 Step 3: Projects (Multi-Tenant Filtered)")
        print("-" * 40)

        projects_response = await client.get("/api/v1/projects", headers=headers)
        print_response("List Projects", projects_response)

        # Step 4: Test Tickets endpoint (multi-tenant filtered)
        print("\n" + "-" * 40)
        print("🎫 Step 4: Tickets (Multi-Tenant Filtered)")
        print("-" * 40)

        tickets_response = await client.get("/api/v1/tickets", headers=headers)
        print_response("List Tickets", tickets_response)

        # Step 5: Test Tasks endpoint (multi-tenant filtered)
        print("\n" + "-" * 40)
        print("📋 Step 5: Tasks (Multi-Tenant Filtered)")
        print("-" * 40)

        tasks_response = await client.get("/api/v1/tasks", headers=headers)
        print_response("List Tasks", tasks_response)

        # Step 6: Test Organizations endpoint
        print("\n" + "-" * 40)
        print("🏢 Step 6: Organizations")
        print("-" * 40)

        orgs_response = await client.get("/api/v1/organizations", headers=headers)
        print_response("List Organizations", orgs_response)

        # Step 7: Test without auth (should fail)
        print("\n" + "-" * 40)
        print("🚫 Step 7: Test Without Auth (Should Fail)")
        print("-" * 40)

        no_auth_response = await client.get("/api/v1/projects")
        print_response("Projects (No Auth)", no_auth_response)

        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)

        results = [
            ("Login", login_response.status_code == 200),
            ("Current User", me_response.status_code == 200),
            ("Projects", projects_response.status_code == 200),
            ("Tickets", tickets_response.status_code == 200),
            ("Tasks", tasks_response.status_code == 200),
            ("Organizations", orgs_response.status_code == 200),
            ("No Auth Blocked", no_auth_response.status_code == 401),
        ]

        for name, passed in results:
            emoji = "✅" if passed else "❌"
            print(f"   {emoji} {name}")

        passed_count = sum(1 for _, p in results if p)
        print(f"\n   Total: {passed_count}/{len(results)} passed")


if __name__ == "__main__":
    asyncio.run(main())
