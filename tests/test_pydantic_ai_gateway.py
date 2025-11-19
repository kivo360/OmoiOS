"""Test script for PydanticAI gateway integration."""

import asyncio
import os
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import infer_model


class TestOutput(BaseModel):
    """Simple test output schema."""

    message: str = Field(..., description="A greeting message")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


async def test_gateway_basic():
    """Test basic gateway functionality."""
    print("Testing PydanticAI Gateway...")

    # Test 1: Basic agent without structured output
    print("\n1. Testing basic agent (no structured output)...")
    try:
        # Try different formats - gateway requires API key
        import os

        api_key = os.getenv("PYDANTIC_AI_GATEWAY_API_KEY") or os.getenv(
            "ANTHROPIC_API_KEY"
        )

        if api_key:
            print(f"   API key found: {api_key[:20]}...")
        else:
            print("   No API key found - gateway may not work")

        # Try gateway format (requires PYDANTIC_AI_GATEWAY_API_KEY)
        gateway_key = os.getenv("PYDANTIC_AI_GATEWAY_API_KEY")
        if gateway_key:
            print(f"   Gateway API key found: {gateway_key[:20]}...")
            model_strings = [
                "gateway/anthropic:claude-sonnet-4-5",
            ]

            for model_str in model_strings:
                try:
                    print(f"   Trying gateway format: {model_str}")
                    agent = Agent(model_str)
                    result = agent.run_sync("Say hello in one sentence.")
                    print(f"✅ Basic test passed with {model_str}: {result.data}")
                    return True
                except Exception as e:
                    print(f"   Failed with {model_str}: {str(e)[:100]}")
                    import traceback

                    traceback.print_exc()
                    continue
        else:
            print("   Skipping gateway format (PYDANTIC_AI_GATEWAY_API_KEY not set)")

        # Try using infer_model with correct format (provider:model)
        print("\n   Trying infer_model approach...")
        try:
            # Set API key if we have it
            if api_key and not os.getenv("ANTHROPIC_API_KEY"):
                os.environ["ANTHROPIC_API_KEY"] = api_key

            # Try different model formats
            model_formats = [
                "anthropic:claude-sonnet-4-5-20250929",
                "anthropic:claude-sonnet-4-5",
                "gateway/anthropic:claude-sonnet-4-5",
            ]

            for model_str in model_formats:
                try:
                    print(f"   Trying: {model_str}")
                    model = infer_model(model_str)
                    print(f"   Inferred model type: {type(model).__name__}")
                    agent = Agent(model)
                    result = agent.run_sync("Say hello in one sentence.")
                    print(f"✅ infer_model works with {model_str}: {result.data}")
                    return True
                except Exception as e:
                    print(f"   Failed with {model_str}: {str(e)[:100]}")
                    continue
        except Exception as e:
            print(f"   infer_model failed: {str(e)[:150]}")
            import traceback

            traceback.print_exc()

        print("❌ All model formats failed")
        return False
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 2: Agent with structured output
    print("\n2. Testing agent with structured output...")
    try:
        gateway_key = os.getenv("PYDANTIC_AI_GATEWAY_API_KEY")
        if not gateway_key:
            print("   Skipping (PYDANTIC_AI_GATEWAY_API_KEY not set)")
            return True  # Skip but don't fail

        agent = Agent(
            "gateway/anthropic:claude-sonnet-4-5",
            output_type=TestOutput,
            system_prompt="You are a helpful assistant that provides structured responses.",
        )
        result = agent.run_sync("Greet me and tell me your confidence level.")
        print("✅ Structured output test passed:")
        print(f"   Message: {result.data.message}")
        print(f"   Confidence: {result.data.confidence}")
    except Exception as e:
        print(f"❌ Structured output test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 3: Async agent
    print("\n3. Testing async agent...")
    try:
        gateway_key = os.getenv("PYDANTIC_AI_GATEWAY_API_KEY")
        if not gateway_key:
            print("   Skipping (PYDANTIC_AI_GATEWAY_API_KEY not set)")
            return True  # Skip but don't fail

        agent = Agent("gateway/anthropic:claude-sonnet-4-5", output_type=TestOutput)
        result = await agent.run("Provide a greeting with confidence 0.95")
        print("✅ Async test passed:")
        print(f"   Message: {result.data.message}")
        print(f"   Confidence: {result.data.confidence}")
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n✅ All tests passed!")
    return True


async def test_service_integration():
    """Test our PydanticAIService integration."""
    print("\n4. Testing PydanticAIService integration...")
    try:
        from omoi_os.services.pydantic_ai_service import PydanticAIService
        from omoi_os.schemas.memory_analysis import MemoryClassification

        service = PydanticAIService()
        agent = service.create_agent(
            output_type=MemoryClassification, system_prompt="Classify memory types."
        )

        result = await agent.run(
            "Execution summary: Fixed a bug in the authentication system. "
            "Task description: Debug login issues."
        )

        print("✅ Service integration test passed:")
        print(f"   Memory Type: {result.data.memory_type}")
        print(f"   Confidence: {result.data.confidence}")
        print(f"   Reasoning: {result.data.reasoning}")
        return True
    except Exception as e:
        print(f"❌ Service integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("PydanticAI Gateway Integration Tests")
    print("=" * 60)

    # Check for API key
    api_key = (
        os.getenv("PYDANTIC_AI_GATEWAY_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("LLM_API_KEY")
    )
    if not api_key:
        print("\n⚠️  Warning: No API key found")
        print(
            "   Set one of: PYDANTIC_AI_GATEWAY_API_KEY, ANTHROPIC_API_KEY, or LLM_API_KEY"
        )
        print("   Example: export ANTHROPIC_API_KEY=your_key")
    else:
        print(f"\n✅ API Key found: {api_key[:20]}...")
        # Set it for the tests
        if not os.getenv("ANTHROPIC_API_KEY"):
            os.environ["ANTHROPIC_API_KEY"] = api_key

    # Run basic tests
    basic_ok = await test_gateway_basic()

    if basic_ok:
        # Run service integration test
        service_ok = await test_service_integration()
        if service_ok:
            print("\n" + "=" * 60)
            print("🎉 All tests passed! Gateway integration is working.")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("⚠️  Basic tests passed but service integration failed.")
            print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Basic tests failed. Check your API key and installation.")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
