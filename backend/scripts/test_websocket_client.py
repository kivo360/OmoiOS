#!/usr/bin/env python3
"""Manual WebSocket client for testing the events endpoint.

Usage:
    python scripts/test_websocket_client.py

This script connects to the WebSocket endpoint and prints all received events.
You can modify the filters in the script to test different scenarios.
"""

import asyncio
import json
import sys
from typing import Optional

import websockets
from websockets.exceptions import ConnectionClosed


async def test_websocket_connection(
    url: str = "ws://localhost:18000/api/v1/ws/events",
    event_types: Optional[str] = None,
    entity_types: Optional[str] = None,
    entity_ids: Optional[str] = None,
):
    """Connect to WebSocket and print received events."""
    # Build URL with query parameters
    params = []
    if event_types:
        params.append(f"event_types={event_types}")
    if entity_types:
        params.append(f"entity_types={entity_types}")
    if entity_ids:
        params.append(f"entity_ids={entity_ids}")

    if params:
        url = f"{url}?{'&'.join(params)}"

    print(f"Connecting to {url}...")
    print("Press Ctrl+C to disconnect\n")

    try:
        async with websockets.connect(url) as websocket:
            print("✅ Connected! Waiting for events...\n")

            # Send a subscription update as an example
            await asyncio.sleep(1)
            subscription = {
                "type": "subscribe",
                "event_types": ["TASK_ASSIGNED", "TASK_COMPLETED", "AGENT_REGISTERED"],
            }
            await websocket.send(json.dumps(subscription))
            print(f"📤 Sent subscription: {subscription}\n")

            # Listen for events
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    data = json.loads(message)

                    if data.get("type") == "ping":
                        print("💓 Ping received (keepalive)")
                    elif "event_type" in data:
                        print("📨 Event received:")
                        print(f"   Event Type: {data['event_type']}")
                        print(f"   Entity Type: {data['entity_type']}")
                        print(f"   Entity ID: {data['entity_id']}")
                        print(f"   Payload: {json.dumps(data['payload'], indent=6)}")
                        print()
                    elif "status" in data:
                        print(f"✅ {data['status']}: {data.get('filters', {})}\n")
                    else:
                        print(f"📦 Message: {data}\n")

                except asyncio.TimeoutError:
                    print("⏱️  No events received in 60 seconds (timeout)")
                    break

    except ConnectionClosed:
        print("\n❌ Connection closed")
    except KeyboardInterrupt:
        print("\n👋 Disconnecting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Example: Filter by event types
    # asyncio.run(test_websocket_connection(event_types="TASK_ASSIGNED,TASK_COMPLETED"))

    # Example: Filter by entity type
    # asyncio.run(test_websocket_connection(entity_types="task"))

    # Example: All events (no filters)
    asyncio.run(test_websocket_connection())
