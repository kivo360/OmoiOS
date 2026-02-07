"""Simple test for gateway format."""

import os
from pydantic_ai import Agent

# Set API key
os.environ["PYDANTIC_AI_GATEWAY_API_KEY"] = "paig_21vgfs95vzR54iBOpim5Smhq5S9zV3dz"
os.environ["ANTHROPIC_API_KEY"] = "paig_21vgfs95vzR54iBOpim5Smhq5S9zV3dz"

# Try gateway format directly
print("Testing gateway format...")
try:
    agent = Agent("gateway/anthropic:claude-sonnet-4-5")
    result = agent.run_sync("Hello world!")
    print(f"✅ Gateway format works: {result.data}")
except Exception as e:
    print(f"❌ Gateway format failed: {e}")
    print("\nTrying without gateway prefix...")
    # Try without gateway prefix
    try:
        agent = Agent("anthropic:claude-sonnet-4-5")
        result = agent.run_sync("Hello world!")
        # Check what attribute contains the output
        output = (
            result.output
            if hasattr(result, "output")
            else result.data if hasattr(result, "data") else str(result)
        )
        print(f"✅ Direct format works: {output}")
        print(
            "\nNote: Gateway prefix not supported in this version, but direct format works!"
        )
        print("   We'll strip 'gateway/' prefix in the service to make it work.")
    except Exception as e2:
        print(f"❌ Direct format also failed: {e2}")
        import traceback

        traceback.print_exc()
