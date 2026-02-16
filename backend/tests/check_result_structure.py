"""Check result structure for structured outputs."""

import os
from pydantic import BaseModel
from pydantic_ai import Agent

os.environ["ANTHROPIC_API_KEY"] = "paig_21vgfs95vzR54iBOpim5Smhq5S9zV3dz"


class Test(BaseModel):
    msg: str


agent = Agent("anthropic:claude-sonnet-4-5", output_type=Test)
result = agent.run_sync("Say hello in one word")

print(f"Has output: {hasattr(result, 'output')}")
print(f"Has data: {hasattr(result, 'data')}")
print(f"Result type: {type(result)}")
print(f"Result attributes: {[x for x in dir(result) if not x.startswith('_')]}")

if hasattr(result, "output"):
    print(f"Result.output: {result.output}")
    print(f"Result.output type: {type(result.output)}")
if hasattr(result, "data"):
    print(f"Result.data: {result.data}")
