"""Example usage of the Unified LLM Service."""

import asyncio
from pydantic import BaseModel, Field
from omoi_os.services.llm_service import get_llm_service


# Example 1: Simple text completion
async def example_simple_completion():
    """Simple text completion example."""
    llm = get_llm_service()
    
    response = await llm.complete("What is the capital of France?")
    print(f"Response: {response}")


# Example 2: Structured output
class SentimentAnalysis(BaseModel):
    """Sentiment analysis result."""
    sentiment: str = Field(..., description="Sentiment: positive, negative, or neutral")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(..., description="Brief explanation")


async def example_structured_output():
    """Structured output example."""
    llm = get_llm_service()
    
    result = await llm.structured_output(
        "Analyze the sentiment of: 'I absolutely love this new feature!'",
        output_type=SentimentAnalysis,
        system_prompt="You are a sentiment analysis expert."
    )
    
    print(f"Sentiment: {result.sentiment}")
    print(f"Confidence: {result.confidence}")
    print(f"Reasoning: {result.reasoning}")


# Example 3: Task execution (OpenHands)
async def example_task_execution():
    """Task execution example."""
    llm = get_llm_service()
    
    result = llm.execute_task(
        task_description="Create a Python function to calculate the factorial of a number",
        phase_id="PHASE_IMPLEMENTATION",
        workspace_dir="/tmp/test_workspace"
    )
    
    print(f"Status: {result['status']}")
    print(f"Events: {result['event_count']}")
    print(f"Cost: {result['cost']}")


# Example 4: Using in a service class
class TextAnalysisService:
    """Example service using the unified LLM service."""
    
    def __init__(self):
        self.llm = get_llm_service()
    
    async def analyze_sentiment(self, text: str) -> SentimentAnalysis:
        """Analyze sentiment of text."""
        return await self.llm.structured_output(
            f"Analyze the sentiment of: {text}",
            output_type=SentimentAnalysis,
            system_prompt="You are a sentiment analysis expert."
        )
    
    async def summarize(self, text: str) -> str:
        """Generate a summary."""
        return await self.llm.complete(
            f"Summarize this text in one paragraph: {text}",
            system_prompt="You are a summarization expert."
        )


async def example_service_class():
    """Example using a service class."""
    service = TextAnalysisService()
    
    # Analyze sentiment
    sentiment = await service.analyze_sentiment("This product is amazing!")
    print(f"Sentiment: {sentiment.sentiment}, Confidence: {sentiment.confidence}")
    
    # Generate summary
    summary = await service.summarize(
        "Python is a high-level programming language known for its simplicity and readability."
    )
    print(f"Summary: {summary}")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Unified LLM Service Examples")
    print("=" * 60)
    
    print("\n1. Simple Completion:")
    print("-" * 60)
    await example_simple_completion()
    
    print("\n2. Structured Output:")
    print("-" * 60)
    await example_structured_output()
    
    print("\n3. Service Class:")
    print("-" * 60)
    await example_service_class()
    
    # Note: Task execution example skipped as it requires a workspace
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

