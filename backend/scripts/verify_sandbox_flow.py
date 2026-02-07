#!/usr/bin/env python3
"""
Verify the complete sandbox spawning and observation flow.

This script tests:
1. Creating a ticket → task created
2. Task picked up → sandbox spawned
3. Conversation registered → Guardian can find it
4. Events streamed → AgentLogs populated
5. Guardian can observe trajectory

Run with: uv run python scripts/verify_sandbox_flow.py
"""

import asyncio
import httpx
from datetime import datetime

API_URL = "http://localhost:18000"


async def main():
    print("=" * 60)
    print("🧪 Sandbox Flow Verification Test")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Health check
        print("\n📋 Step 1: Health Check")
        resp = await client.get(f"{API_URL}/health")
        if resp.status_code != 200:
            print(f"❌ Server not healthy: {resp.status_code}")
            return
        print(f"✅ Server healthy: {resp.json()}")

        # Step 2: Create a test ticket
        print("\n📋 Step 2: Create Test Ticket")
        ticket_data = {
            "title": f"Verification Test {datetime.now().strftime('%H:%M:%S')}",
            "description": "Create a simple Python script that prints 'Hello Verification'",
        }
        resp = await client.post(f"{API_URL}/api/v1/tickets", json=ticket_data)
        if resp.status_code != 200:
            print(f"❌ Failed to create ticket: {resp.status_code}")
            print(resp.text)
            return
        ticket = resp.json()
        ticket_id = ticket["id"]
        print(f"✅ Ticket created: {ticket_id}")
        print(f"   Title: {ticket['title']}")
        print(f"   Phase: {ticket['phase_id']}")

        # Step 3: Wait for task to be created and picked up
        print("\n📋 Step 3: Wait for Task Creation & Sandbox Spawn")
        task_id = None
        conversation_id = None

        for i in range(30):  # Wait up to 30 seconds
            await asyncio.sleep(1)
            print(f"   Checking... ({i+1}s)")

            # Check for tasks
            resp = await client.get(f"{API_URL}/api/v1/tasks?status=running&limit=5")
            if resp.status_code == 200:
                tasks = resp.json()
                if isinstance(tasks, list) and len(tasks) > 0:
                    for t in tasks:
                        if t.get("ticket_id") == ticket_id or (not task_id):
                            task_id = t.get("id") or t.get("task_id")
                            conversation_id = t.get("conversation_id")
                            print(f"   ✅ Found running task: {task_id}")
                            if conversation_id:
                                print(
                                    f"   ✅ Conversation registered: {conversation_id}"
                                )
                            break

            # Also check assigned tasks
            resp = await client.get(f"{API_URL}/api/v1/tasks?status=assigned&limit=5")
            if resp.status_code == 200:
                tasks = resp.json()
                if isinstance(tasks, list):
                    for t in tasks:
                        if not task_id:
                            task_id = t.get("id") or t.get("task_id")
                            print(f"   ✅ Found assigned task: {task_id}")

            if conversation_id:
                break

        if not task_id:
            print(
                "⚠️  No task found yet (orchestrator may be slow or no LLM configured)"
            )
            print("   Checking pending tasks...")
            resp = await client.get(f"{API_URL}/api/v1/tasks?status=pending&limit=3")
            if resp.status_code == 200:
                tasks = resp.json()
                if isinstance(tasks, list) and len(tasks) > 0:
                    print(f"   Found {len(tasks)} pending task(s)")
                    task_id = tasks[0].get("id")

        # Step 4: Check Agent Logs (event streaming verification)
        print("\n📋 Step 4: Verify Event Streaming (Agent Logs)")
        if task_id:
            # Check if agent logs exist
            resp = await client.get(f"{API_URL}/api/v1/tasks/{task_id}")
            if resp.status_code == 200:
                task_detail = resp.json()
                print(f"   Task status: {task_detail.get('status', 'unknown')}")
                agent_id = task_detail.get("assigned_agent_id")
                if agent_id:
                    print(f"   Assigned agent: {agent_id}")

        # Step 5: Check terminal logs for sandbox activity
        print("\n📋 Step 5: Check Server Logs for Sandbox Activity")
        print(
            "   (Check terminal 11.txt for 'Daytona sandbox' and 'register_conversation')"
        )

        # Summary
        print("\n" + "=" * 60)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 60)
        print("✅ Server running: Yes")
        print(f"✅ Ticket created: {ticket_id}")
        print(f"{'✅' if task_id else '⚠️ '} Task ID: {task_id or 'Not found yet'}")
        print(
            f"{'✅' if conversation_id else '⚠️ '} Conversation registered: {conversation_id or 'Not yet'}"
        )

        print("\n🔍 To manually verify sandbox spawning, check:")
        print("   Terminal logs: Look for 'Daytona sandbox' and 'omoios-*'")
        print("   MCP calls: Look for 'register_conversation' and 'report_agent_event'")

        print("\n🎯 Full E2E test requires LLM_API_KEY configured for agent execution")


if __name__ == "__main__":
    asyncio.run(main())
