"""Simple test for LLM service - just verify we can call it and get results."""

import asyncio
from omoi_os.services.llm_service import get_llm_service


async def test_simple_completion():
    """Test simple text completion."""
    llm = get_llm_service()
    result = await llm.complete("Say hello in one word")
    print(f"✅ Simple completion: {result}")
    assert isinstance(result, str)
    assert len(result) > 0


async def test_structured_output():
    """Test structured output."""
    from pydantic import BaseModel, Field

    class SimpleOutput(BaseModel):
        message: str = Field(..., description="A greeting message")
        number: int = Field(..., description="A number between 1 and 10")

    llm = get_llm_service()
    result = await llm.structured_output(
        "Say hello and pick a number between 1 and 10", output_type=SimpleOutput
    )
    print(f"✅ Structured output: message={result.message}, number={result.number}")
    assert isinstance(result, SimpleOutput)
    assert 1 <= result.number <= 10


async def main():
    """Run tests."""
    print("Testing LLM Service...")
    await test_simple_completion()
    await test_structured_output()
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
