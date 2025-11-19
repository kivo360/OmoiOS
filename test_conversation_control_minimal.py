#!/usr/bin/env python3
"""
Minimal Prototype: OpenHands Conversation Control

Simplest possible test of conversation control concepts.
Run: python test_conversation_control_minimal.py
"""

import os
import time
import threading
from pathlib import Path

from openhands.sdk import Conversation, LLM
from openhands.tools.preset.default import get_default_agent
from openhands.sdk.conversation.state import AgentExecutionStatus


def main():
    """Minimal test of conversation control."""
    
    # Setup
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        return
    
    workspace = Path("./test_workspace")
    workspace.mkdir(exist_ok=True)
    persistence_dir = str(workspace / "conv")
    
    llm = LLM(model="gpt-4o-mini", api_key=api_key)
    agent = get_default_agent(llm=llm, cli_mode=True)
    
    # Create conversation with persistence
    print("1️⃣ Creating conversation...")
    conv = Conversation(
        agent=agent,
        workspace=str(workspace),
        persistence_dir=persistence_dir,
        conversation_id="test-minimal",
    )
    print(f"   ID: {conv.state.id}")
    print(f"   Status: {conv.state.agent_status}")
    
    # Send task
    print("\n2️⃣ Sending task...")
    conv.send_message("Write a Python function that returns 'Hello World'")
    
    # Start in background
    print("\n3️⃣ Running conversation in background...")
    def run():
        conv.run()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    
    # Monitor state
    print("\n4️⃣ Monitoring state...")
    for i in range(5):
        time.sleep(1)
        status = conv.state.agent_status
        events = len(conv.state.events)
        print(f"   [{i+1}s] Status: {status}, Events: {events}")
    
    # Send intervention
    print("\n5️⃣ Sending intervention...")
    conv.send_message("[INTERVENTION] Please add a docstring to the function")
    
    # Check if we need to trigger processing
    if conv.state.agent_status == AgentExecutionStatus.IDLE:
        print("   → Agent idle, triggering processing...")
        threading.Thread(target=conv.run, daemon=True).start()
    
    # Monitor more
    print("\n6️⃣ Monitoring after intervention...")
    for i in range(3):
        time.sleep(1)
        events = len(conv.state.events)
        print(f"   [{i+1}s] Events: {events}")
    
    # Final state
    print("\n7️⃣ Final state:")
    print(f"   Status: {conv.state.agent_status}")
    print(f"   Events: {len(conv.state.events)}")
    print(f"   Execution: {conv.state.execution_status}")
    
    # Resume test
    print("\n8️⃣ Testing resumption...")
    conv.close()
    
    conv2 = Conversation(
        conversation_id="test-minimal",
        persistence_dir=persistence_dir,
        agent=agent,
        workspace=str(workspace),
    )
    print(f"   Resumed ID: {conv2.state.id}")
    print(f"   Previous events: {len(conv2.state.events)}")
    
    conv2.close()
    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
