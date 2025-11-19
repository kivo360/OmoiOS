#!/usr/bin/env python3
"""
DETAILED ANALYSIS: Test 1 - Basic Conversation Creation and Execution

This script breaks down Test 1 step-by-step with detailed explanations
and state inspection at each stage.
"""

import os
import time
from pathlib import Path

from openhands.sdk import Conversation, LLM
from openhands.tools.preset.default import get_default_agent
from openhands.sdk.conversation.state import AgentExecutionStatus


def print_separator(title: str):
    """Print a visual separator."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_state_details(conversation: Conversation, label: str):
    """Print detailed conversation state information."""
    state = conversation.state
    
    print(f"\n📊 {label}")
    print("-" * 70)
    print(f"Conversation ID:     {state.id}")
    print(f"Agent Status:        {state.agent_status}")
    print(f"Execution Status:    {state.execution_status}")
    print(f"Total Events:        {len(state.events)}")
    print(f"Is Idle:             {state.agent_status == AgentExecutionStatus.IDLE}")
    print(f"Is Running:          {state.agent_status == AgentExecutionStatus.RUNNING}")
    
    # Show event types
    if state.events:
        event_types = {}
        for event in state.events:
            event_type = type(event).__name__
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        print(f"\nEvent Breakdown:")
        for event_type, count in sorted(event_types.items()):
            print(f"  - {event_type}: {count}")
    
    # Show conversation stats if available
    if hasattr(conversation, 'conversation_stats'):
        stats = conversation.conversation_stats.get_combined_metrics()
        if hasattr(stats, 'accumulated_cost'):
            print(f"\nCost Metrics:")
            print(f"  Accumulated Cost: ${stats.accumulated_cost:.4f}")


def test_1_detailed():
    """
    DETAILED BREAKDOWN: Basic Conversation Creation and Execution
    
    This test demonstrates:
    1. Setting up workspace and persistence
    2. Creating a conversation with explicit ID
    3. Inspecting initial state
    4. Sending a task message
    5. Executing the conversation
    6. Inspecting final state and results
    7. Proper cleanup
    """
    
    print_separator("TEST 1: Basic Conversation Creation and Execution")
    print("\nThis test demonstrates the fundamental conversation lifecycle:")
    print("  • Creating conversations with persistence")
    print("  • Accessing conversation state")
    print("  • Executing tasks")
    print("  • Inspecting results")
    
    # ========================================================================
    # STEP 1: Setup
    # ========================================================================
    print_separator("STEP 1: Setup - Initialize Controller")
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
    
    # Setup workspace directory
    workspace_dir = Path("./test_workspace")
    workspace_dir.mkdir(exist_ok=True)
    print(f"✅ Workspace directory: {workspace_dir.absolute()}")
    
    # Setup persistence directory
    persistence_dir = workspace_dir / "conversations" / "test-conv-1"
    persistence_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Persistence directory: {persistence_dir.absolute()}")
    
    # Create LLM instance
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")  # Use cheap model for testing
    llm = LLM(model=model, api_key=api_key)
    print(f"✅ LLM initialized: {model}")
    
    # Create agent
    agent = get_default_agent(llm=llm, cli_mode=True)
    print(f"✅ Agent initialized")
    
    # ========================================================================
    # STEP 2: Create Conversation
    # ========================================================================
    print_separator("STEP 2: Create Conversation with Persistence")
    
    print("\nCreating conversation with:")
    print(f"  • conversation_id: 'test-conv-1'")
    print(f"  • persistence_dir: {persistence_dir}")
    print(f"  • workspace: {workspace_dir}")
    
    conversation = Conversation(
        agent=agent,
        workspace=str(workspace_dir),
        persistence_dir=str(persistence_dir),
        conversation_id="test-conv-1",  # Explicit ID for resumption
    )
    
    print("\n✅ Conversation created!")
    
    # Inspect initial state
    print_state_details(conversation, "Initial State (After Creation)")
    
    print("\n💡 Key Observations:")
    print("  • Conversation has an ID immediately")
    print("  • Agent status starts as IDLE (waiting for input)")
    print("  • No events yet (no messages sent)")
    print("  • Persistence directory is set up")
    
    # ========================================================================
    # STEP 3: Send Task Message
    # ========================================================================
    print_separator("STEP 3: Send Task Message")
    
    task_message = "Write a simple hello world Python script"
    print(f"\n📝 Sending task message:")
    print(f"   '{task_message}'")
    
    conversation.send_message(task_message)
    
    print("\n✅ Message sent!")
    
    # Check state after sending message
    print_state_details(conversation, "State After Sending Message")
    
    print("\n💡 Key Observations:")
    print("  • Agent status may still be IDLE (message queued)")
    print("  • Events count increased (message event added)")
    print("  • Conversation is ready to process")
    
    # ========================================================================
    # STEP 4: Execute Conversation
    # ========================================================================
    print_separator("STEP 4: Execute Conversation")
    
    print("\n🚀 Running conversation...")
    print("   (This will process the task message)")
    
    start_time = time.time()
    
    # Run the conversation - this is blocking
    conversation.run()
    
    execution_time = time.time() - start_time
    
    print(f"\n✅ Conversation execution completed in {execution_time:.2f} seconds")
    
    # ========================================================================
    # STEP 5: Inspect Final State
    # ========================================================================
    print_separator("STEP 5: Inspect Final State and Results")
    
    print_state_details(conversation, "Final State (After Execution)")
    
    print("\n💡 Key Observations:")
    print("  • Agent status is now IDLE (execution complete)")
    print("  • Execution status shows completion")
    print("  • Multiple events were generated (tool calls, responses, etc.)")
    print("  • Cost metrics are available")
    
    # Show some event details
    if conversation.state.events:
        print("\n📋 Sample Events (first 3):")
        for i, event in enumerate(conversation.state.events[:3], 1):
            event_type = type(event).__name__
            print(f"  {i}. {event_type}")
            # Try to get some details if available
            if hasattr(event, 'content'):
                content_preview = str(event.content)[:100]
                print(f"     Content: {content_preview}...")
    
    # ========================================================================
    # STEP 6: Access Results
    # ========================================================================
    print_separator("STEP 6: Access Conversation Results")
    
    # Get conversation statistics
    if hasattr(conversation, 'conversation_stats'):
        stats = conversation.conversation_stats.get_combined_metrics()
        print("\n📈 Conversation Statistics:")
        print(f"  Total Cost: ${stats.accumulated_cost:.4f}")
        if hasattr(stats, 'total_tokens'):
            print(f"  Total Tokens: {stats.total_tokens}")
    
    # Get last messages/events
    print("\n📨 Last Few Events:")
    for i, event in enumerate(conversation.state.events[-3:], 1):
        event_type = type(event).__name__
        print(f"  {i}. {event_type}")
    
    # ========================================================================
    # STEP 7: Save Metadata for Resumption
    # ========================================================================
    print_separator("STEP 7: Save Metadata for Future Resumption")
    
    metadata = {
        "conversation_id": conversation.state.id,
        "persistence_dir": str(persistence_dir),
        "workspace_dir": str(workspace_dir),
        "event_count": len(conversation.state.events),
        "execution_status": str(conversation.state.execution_status),
    }
    
    print("\n💾 Conversation Metadata (for resumption):")
    for key, value in metadata.items():
        print(f"  • {key}: {value}")
    
    print("\n💡 This metadata can be stored in database (Task model)")
    print("   to enable conversation resumption and intervention later.")
    
    # ========================================================================
    # STEP 8: Cleanup
    # ========================================================================
    print_separator("STEP 8: Cleanup")
    
    print("\n🧹 Closing conversation...")
    conversation.close()
    print("✅ Conversation closed")
    
    print("\n💡 Key Points:")
    print("  • Always close conversations to free resources")
    print("  • Persistence directory contains conversation state")
    print("  • Can resume later using conversation_id and persistence_dir")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print_separator("SUMMARY")
    
    print("\n✅ Test 1 Complete!")
    print("\nWhat we learned:")
    print("  1. Conversations can be created with explicit IDs")
    print("  2. State is accessible immediately via conversation.state")
    print("  3. Messages are sent with send_message()")
    print("  4. Execution happens with run() (blocking)")
    print("  5. State tracks agent_status, execution_status, and events")
    print("  6. Conversations persist automatically to disk")
    print("  7. Metadata (ID, persistence_dir) enables resumption")
    
    return metadata


def demonstrate_state_access():
    """Show how to access state at different points."""
    print_separator("BONUS: State Access Patterns")
    
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return
    
    workspace = Path("./test_workspace")
    workspace.mkdir(exist_ok=True)
    
    llm = LLM(model="gpt-4o-mini", api_key=api_key)
    agent = get_default_agent(llm=llm, cli_mode=True)
    
    conv = Conversation(
        agent=agent,
        workspace=str(workspace),
        persistence_dir=str(workspace / "conv-demo"),
        conversation_id="state-demo",
    )
    
    print("\n1. State access is always available:")
    print(f"   conv.state.id = {conv.state.id}")
    print(f"   conv.state.agent_status = {conv.state.agent_status}")
    
    print("\n2. State updates automatically:")
    conv.send_message("Say hello")
    print(f"   After send_message: {len(conv.state.events)} events")
    
    # Run in background to show state monitoring
    import threading
    def run():
        conv.run()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    
    print("\n3. State can be monitored during execution:")
    for i in range(3):
        time.sleep(0.5)
        status = conv.state.agent_status
        events = len(conv.state.events)
        print(f"   [{i+1}] Status: {status}, Events: {events}")
    
    conv.close()
    print("\n✅ State access demonstration complete")


if __name__ == "__main__":
    try:
        # Run detailed test
        metadata = test_1_detailed()
        
        # Show state access patterns
        demonstrate_state_access()
        
        print("\n" + "="*70)
        print("🎉 All demonstrations complete!")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
