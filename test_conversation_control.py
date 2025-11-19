#!/usr/bin/env python3
"""
Prototype: OpenHands Conversation Control Test

This script demonstrates controlling OpenHands conversations:
- Creating conversations with persistence
- Accessing conversation state
- Sending interventions during execution
- Resuming conversations
- Monitoring state changes

Run: python test_conversation_control.py
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional

# OpenHands imports
from openhands.sdk import Conversation, LLM, AgentContext
from openhands.tools.preset.default import get_default_agent
from openhands.sdk.conversation.state import AgentExecutionStatus


class ConversationController:
    """Simple controller for testing OpenHands conversation management."""
    
    def __init__(self, workspace_dir: str = "./test_workspace"):
        """Initialize controller with workspace directory."""
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)
        
        # Setup LLM (requires OPENAI_API_KEY or ANTHROPIC_API_KEY)
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
        
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")  # Use cheap model for testing
        
        self.llm = LLM(model=model, api_key=api_key)
        self.agent = get_default_agent(llm=self.llm, cli_mode=True)
        
    def create_conversation(
        self, 
        conversation_id: Optional[str] = None,
        persistence_dir: Optional[str] = None
    ) -> Conversation:
        """
        Create a new conversation with persistence.
        
        Args:
            conversation_id: Optional ID (if None, OpenHands generates one)
            persistence_dir: Optional persistence directory
            
        Returns:
            Conversation object
        """
        if persistence_dir is None:
            persistence_dir = str(self.workspace_dir / "conversations")
        
        os.makedirs(persistence_dir, exist_ok=True)
        
        conversation = Conversation(
            agent=self.agent,
            workspace=str(self.workspace_dir),
            persistence_dir=persistence_dir,
            conversation_id=conversation_id,
        )
        
        print(f"✅ Created conversation: {conversation.state.id}")
        print(f"   Persistence dir: {persistence_dir}")
        return conversation
    
    def resume_conversation(
        self,
        conversation_id: str,
        persistence_dir: str,
        workspace_dir: Optional[str] = None
    ) -> Conversation:
        """
        Resume an existing conversation from persistence.
        
        Args:
            conversation_id: Conversation ID
            persistence_dir: Persistence directory
            workspace_dir: Optional workspace directory
            
        Returns:
            Resumed Conversation object
        """
        conversation = Conversation(
            conversation_id=conversation_id,
            persistence_dir=persistence_dir,
            agent=self.agent,
            workspace=workspace_dir or str(self.workspace_dir),
        )
        
        print(f"✅ Resumed conversation: {conversation.state.id}")
        print(f"   Events: {len(conversation.state.events)}")
        return conversation
    
    def get_conversation_state(self, conversation: Conversation) -> dict:
        """Get current conversation state information."""
        state = conversation.state
        return {
            "id": state.id,
            "agent_status": state.agent_status.value if hasattr(state.agent_status, 'value') else str(state.agent_status),
            "execution_status": state.execution_status.value if hasattr(state.execution_status, 'value') else str(state.execution_status),
            "event_count": len(state.events),
            "is_idle": state.agent_status == AgentExecutionStatus.IDLE,
            "is_running": state.agent_status == AgentExecutionStatus.RUNNING,
        }
    
    def print_state(self, conversation: Conversation, label: str = "State"):
        """Print conversation state in readable format."""
        state_info = self.get_conversation_state(conversation)
        print(f"\n📊 {label}:")
        print(f"   ID: {state_info['id']}")
        print(f"   Agent Status: {state_info['agent_status']}")
        print(f"   Execution Status: {state_info['execution_status']}")
        print(f"   Events: {state_info['event_count']}")
        print(f"   Is Idle: {state_info['is_idle']}")
        print(f"   Is Running: {state_info['is_running']}")
    
    def send_intervention(
        self,
        conversation: Conversation,
        message: str,
        wait_for_idle: bool = False
    ) -> bool:
        """
        Send an intervention message to a conversation.
        
        Args:
            conversation: Conversation object
            message: Intervention message
            wait_for_idle: If True, wait for agent to be idle before sending
            
        Returns:
            True if sent successfully
        """
        if wait_for_idle:
            print("⏳ Waiting for agent to be idle...")
            while conversation.state.agent_status != AgentExecutionStatus.IDLE:
                time.sleep(0.5)
        
        intervention_message = f"[INTERVENTION] {message}"
        print(f"\n📨 Sending intervention: {message}")
        
        try:
            conversation.send_message(intervention_message)
            
            # If idle, trigger processing
            if conversation.state.agent_status == AgentExecutionStatus.IDLE:
                print("   → Agent is idle, starting processing...")
                # Run in background thread to avoid blocking
                thread = threading.Thread(target=conversation.run, daemon=True)
                thread.start()
            else:
                print(f"   → Agent is {conversation.state.agent_status}, message queued")
            
            return True
        except Exception as e:
            print(f"❌ Failed to send intervention: {e}")
            return False
    
    def monitor_conversation(
        self,
        conversation: Conversation,
        duration: float = 10.0,
        interval: float = 1.0
    ):
        """
        Monitor conversation state for a duration.
        
        Args:
            conversation: Conversation to monitor
            duration: How long to monitor (seconds)
            interval: Check interval (seconds)
        """
        print(f"\n👀 Monitoring conversation for {duration}s (checking every {interval}s)...")
        start_time = time.time()
        last_event_count = len(conversation.state.events)
        
        while time.time() - start_time < duration:
            current_state = self.get_conversation_state(conversation)
            current_events = current_state['event_count']
            
            if current_events != last_event_count:
                print(f"   ⚡ New events detected: {current_events} (was {last_event_count})")
                last_event_count = current_events
            
            time.sleep(interval)
        
        print("   ✅ Monitoring complete")


def test_basic_conversation():
    """Test 1: Basic conversation creation and execution."""
    print("\n" + "="*60)
    print("TEST 1: Basic Conversation Creation and Execution")
    print("="*60)
    
    controller = ConversationController()
    
    # Create conversation
    conversation = controller.create_conversation(conversation_id="test-conv-1")
    controller.print_state(conversation, "Initial State")
    
    # Send initial task
    print("\n📝 Sending task: 'Write a simple hello world Python script'")
    conversation.send_message("Write a simple hello world Python script")
    
    # Run conversation
    print("\n🚀 Running conversation...")
    conversation.run()
    
    # Check final state
    controller.print_state(conversation, "Final State")
    
    # Save metadata for resumption test
    metadata = {
        "conversation_id": conversation.state.id,
        "persistence_dir": conversation.persistence_dir,
    }
    
    conversation.close()
    return metadata


def test_intervention_during_execution():
    """Test 2: Send intervention while conversation is running."""
    print("\n" + "="*60)
    print("TEST 2: Intervention During Execution")
    print("="*60)
    
    controller = ConversationController()
    
    # Create conversation
    conversation = controller.create_conversation(conversation_id="test-conv-2")
    
    # Send a longer task that will take time
    print("\n📝 Sending task: 'Write a Python function to calculate fibonacci numbers'")
    conversation.send_message("Write a Python function to calculate fibonacci numbers")
    
    # Start conversation in background thread
    print("\n🚀 Starting conversation in background...")
    def run_conversation():
        conversation.run()
    
    thread = threading.Thread(target=run_conversation, daemon=True)
    thread.start()
    
    # Wait a bit, then send intervention
    time.sleep(2)
    controller.print_state(conversation, "State Before Intervention")
    
    # Send intervention
    controller.send_intervention(
        conversation,
        "Please add docstrings to the function",
        wait_for_idle=False
    )
    
    # Monitor for a bit
    controller.monitor_conversation(conversation, duration=5.0)
    
    controller.print_state(conversation, "State After Intervention")
    
    conversation.close()


def test_conversation_resumption():
    """Test 3: Resume a conversation from persistence."""
    print("\n" + "="*60)
    print("TEST 3: Conversation Resumption")
    print("="*60)
    
    controller = ConversationController()
    
    # First, create and run a conversation
    print("Step 1: Create initial conversation...")
    conversation1 = controller.create_conversation(conversation_id="test-conv-3")
    conversation1.send_message("Create a simple Python function that adds two numbers")
    conversation1.run()
    
    controller.print_state(conversation1, "Conversation 1 State")
    
    # Save metadata
    conv_id = conversation1.state.id
    persistence_dir = conversation1.persistence_dir
    
    conversation1.close()
    
    # Now resume it
    print("\nStep 2: Resuming conversation...")
    conversation2 = controller.resume_conversation(
        conversation_id=conv_id,
        persistence_dir=persistence_dir
    )
    
    controller.print_state(conversation2, "Resumed Conversation State")
    
    # Send additional message
    print("\n📝 Sending follow-up: 'Now modify it to handle negative numbers'")
    conversation2.send_message("Now modify it to handle negative numbers")
    conversation2.run()
    
    controller.print_state(conversation2, "Final State After Resumption")
    
    conversation2.close()


def test_state_inspection():
    """Test 4: Inspect conversation state and events."""
    print("\n" + "="*60)
    print("TEST 4: State Inspection")
    print("="*60)
    
    controller = ConversationController()
    
    conversation = controller.create_conversation(conversation_id="test-conv-4")
    
    # Send task
    conversation.send_message("List the first 5 prime numbers")
    
    # Check state before running
    controller.print_state(conversation, "Before Run")
    print(f"   Events: {len(conversation.state.events)}")
    
    # Run
    conversation.run()
    
    # Check state after running
    controller.print_state(conversation, "After Run")
    print(f"   Events: {len(conversation.state.events)}")
    
    # Inspect events
    print("\n📋 Event Summary:")
    for i, event in enumerate(conversation.state.events[:5], 1):  # Show first 5
        event_type = type(event).__name__
        print(f"   {i}. {event_type}")
    
    if len(conversation.state.events) > 5:
        print(f"   ... and {len(conversation.state.events) - 5} more events")
    
    conversation.close()


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("OpenHands Conversation Control Prototype")
    print("="*60)
    print("\nThis script tests conversation control capabilities:")
    print("  1. Basic conversation creation and execution")
    print("  2. Intervention during execution")
    print("  3. Conversation resumption")
    print("  4. State inspection")
    print("\nMake sure OPENAI_API_KEY or ANTHROPIC_API_KEY is set!")
    print("="*60)
    
    try:
        # Run tests
        metadata = test_basic_conversation()
        time.sleep(1)
        
        test_intervention_during_execution()
        time.sleep(1)
        
        test_conversation_resumption()
        time.sleep(1)
        
        test_state_inspection()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)
        print(f"\nConversation data persisted in: {Path('./test_workspace/conversations').absolute()}")
        print("You can inspect the persistence directory to see conversation state files.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
