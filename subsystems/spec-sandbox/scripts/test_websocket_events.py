#!/usr/bin/env python
"""Test WebSocket real-time events for spec-driven development.

This script:
1. Connects to the WebSocket endpoint
2. Sends a test event via HTTP to the sandbox events API
3. Verifies the event is received via WebSocket in real-time

Usage:
    # Get a token first
    python scripts/get_test_token.py --email=user@example.com --password=yourpassword

    # Then run this test
    python scripts/test_websocket_events.py --api-key="YOUR_TOKEN" --sandbox-id="test-sandbox-123"

    # Or with a real spec_id to filter events:
    python scripts/test_websocket_events.py --api-key="YOUR_TOKEN" --sandbox-id="test-sandbox-123" --spec-id="spec-uuid"
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone

import httpx
import websockets


API_URL = "http://localhost:18000"
WS_URL = "ws://localhost:18000"


async def test_websocket_events(
    api_key: str,
    sandbox_id: str,
    spec_id: str | None = None,
    timeout: float = 10.0,
) -> bool:
    """Test WebSocket event delivery.

    1. Connect to WebSocket endpoint
    2. POST a test event to sandbox events API
    3. Verify event is received via WebSocket

    Returns True if test passes.
    """
    print(f"\n{'='*60}")
    print("WebSocket Real-Time Events Test")
    print(f"{'='*60}")
    print(f"API URL: {API_URL}")
    print(f"WS URL: {WS_URL}")
    print(f"Sandbox ID: {sandbox_id}")
    print(f"Spec ID: {spec_id or 'None (will receive all events)'}")
    print()

    # Build WebSocket URL with filters
    ws_endpoint = f"{WS_URL}/api/v1/ws/events"
    # Filter by sandbox entity_id if we want specific events
    # Note: The WebSocket filters by entity_id, entity_type, event_type

    event_received = asyncio.Event()
    received_events = []

    async def listen_for_events():
        """Connect to WebSocket and listen for events."""
        try:
            print(f"[WS] Connecting to {ws_endpoint}...")
            async with websockets.connect(ws_endpoint) as ws:
                print("[WS] Connected! Waiting for events...")

                # Optionally subscribe to specific event types
                # await ws.send(json.dumps({
                #     "type": "subscribe",
                #     "entity_ids": [sandbox_id],
                # }))

                while True:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=timeout)
                        data = json.loads(message)

                        # Skip ping messages
                        if data.get("type") == "ping":
                            print("[WS] Received ping")
                            continue

                        print(f"[WS] Received event: {json.dumps(data, indent=2)}")
                        received_events.append(data)

                        # Check if this is our test event
                        payload = data.get("payload", {})
                        if payload.get("_test_marker") == "websocket_test":
                            print("[WS] ✅ Test event received!")
                            event_received.set()
                            break

                    except asyncio.TimeoutError:
                        print(f"[WS] No event received within {timeout}s timeout")
                        break

        except Exception as e:
            print(f"[WS] Error: {e}")

    async def send_test_event():
        """Send a test event via HTTP."""
        await asyncio.sleep(1)  # Wait for WebSocket to connect

        endpoint = f"{API_URL}/api/v1/sandboxes/{sandbox_id}/events"

        event_data = {
            "_test_marker": "websocket_test",
            "message": "Testing WebSocket real-time delivery",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if spec_id:
            event_data["spec_id"] = spec_id

        payload = {
            "event_type": "spec.progress",
            "event_data": event_data,
            "source": "agent",
        }

        print(f"\n[HTTP] Sending test event to {endpoint}")
        print(f"[HTTP] Payload: {json.dumps(payload, indent=2)}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )

            if response.status_code == 200:
                print(f"[HTTP] ✅ Event sent successfully: {response.json()}")
            else:
                print(f"[HTTP] ❌ Failed to send event: {response.status_code}")
                print(f"[HTTP] Response: {response.text}")
                return False

        return True

    # Run both tasks concurrently
    ws_task = asyncio.create_task(listen_for_events())
    http_task = asyncio.create_task(send_test_event())

    # Wait for HTTP to complete
    http_success = await http_task
    if not http_success:
        ws_task.cancel()
        return False

    # Wait for WebSocket event or timeout
    try:
        await asyncio.wait_for(event_received.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass

    # Cancel WebSocket listener
    ws_task.cancel()
    try:
        await ws_task
    except asyncio.CancelledError:
        pass

    # Report results
    print(f"\n{'='*60}")
    print("Test Results")
    print(f"{'='*60}")
    print(f"Events received via WebSocket: {len(received_events)}")

    if event_received.is_set():
        print("\n✅ SUCCESS: WebSocket real-time events are working!")
        print("   Events are delivered instantly via Redis Pub/Sub -> WebSocket")
        return True
    else:
        print("\n⚠️  WARNING: Test event was not received via WebSocket")
        print("   Possible reasons:")
        print("   1. Redis pub/sub not configured correctly")
        print("   2. EventBus not publishing to correct channel")
        print("   3. WebSocket manager not subscribed to events.* pattern")
        print()
        print("   However, polling fallback (5s interval) will still work.")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test WebSocket real-time events")
    parser.add_argument("--api-key", required=True, help="API bearer token")
    parser.add_argument("--sandbox-id", default="test-ws-sandbox", help="Sandbox ID to use")
    parser.add_argument("--spec-id", help="Optional spec ID to include in event")
    parser.add_argument("--api-url", default=API_URL, help=f"API URL (default: {API_URL})")
    parser.add_argument("--timeout", type=float, default=10.0, help="Timeout in seconds")
    args = parser.parse_args()

    global API_URL, WS_URL
    API_URL = args.api_url
    WS_URL = args.api_url.replace("http://", "ws://").replace("https://", "wss://")

    success = await test_websocket_events(
        api_key=args.api_key,
        sandbox_id=args.sandbox_id,
        spec_id=args.spec_id,
        timeout=args.timeout,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
