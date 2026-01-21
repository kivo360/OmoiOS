# Local Agent Simulation for Ticket Hierarchy Experiments

**Created**: 2026-01-19
**Purpose**: Run ticket hierarchy experiments locally without Daytona sandboxes using Claude Agent SDK
**Benefits**: Fast, cheap, reproducible, parallelizable

---

## Approach: Simulated Agent Execution

Instead of running full sandbox workflows, simulate agent's **decision-making process**:

### What We're Actually Testing

The core question is: **Does having ticket context help agents make better decisions?**

We can test this by:
1. Providing tasks with or without ticket context
2. Asking Claude to **plan and analyze** the task (no actual code execution)
3. Measuring how ticket context affects their reasoning, questions, and confidence

### Why This Works

- **Decision quality**: We care about context comprehension, not code execution
- **State tracking**: We can simulate status updates and dependency resolution
- **Discovery**: Claude can discover related tasks without executing them
- **Metrics**: All key metrics are measurable through analysis tasks

---

## Implementation Strategy

### Use Claude Agent SDK in Analysis Mode

```python
from claude_agent_sdk import ClaudeSDKClient
import asyncio
from typing import List, Dict, Any

class SimulatedAgent:
    """Simulates agent execution without sandbox"""

    def __init__(self, client: ClaudeSDKClient, agent_id: str):
        self.client = client
        self.agent_id = agent_id
        self.context_api_calls = 0
        self.questions_asked = 0
        self.decisions_made = 0

    async def analyze_task(
        self,
        task: Dict[str, Any],
        ticket_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze task and return plan without executing"""

        # Track if we accessed ticket context
        if ticket_context:
            self.context_api_calls += 1

        # Build prompt based on available context
        prompt = self._build_prompt(task, ticket_context)

        # Query Claude for analysis
        response = await self.client.query(
            user_message=prompt,
            agent_id=self.agent_id,
            tools=[],  # No tools needed for analysis
            stream=False
        )

        # Parse response
        result = self._parse_analysis(response)

        # Track metrics
        self.decisions_made += 1
        if result.get("clarifying_questions"):
            self.questions_asked += len(result["clarifying_questions"])

        return result

    def _build_prompt(
        self,
        task: Dict[str, Any],
        ticket_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt based on available context"""

        prompt = f"""
You are an AI agent planning work on a software development task.

TASK:
- ID: {task['id']}
- Type: {task['task_type']}
- Title: {task.get('title', '')}
- Description: {task.get('description', '')}
- Priority: {task.get('priority', '')}
- Phase: {task.get('phase_id', '')}
"""

        if ticket_context:
            prompt += f"""

TICKET CONTEXT (This task belongs to this feature):
- Ticket ID: {ticket_context['id']}
- Ticket Title: {ticket_context['title']}
- Ticket Description: {ticket_context.get('description', '')}
- Ticket Phase: {ticket_context.get('phase_id', '')}
- Ticket Status: {ticket_context.get('status', '')}
"""

        if task.get('dependencies'):
            prompt += f"""

DEPENDENCIES:
- This task depends on: {task['dependencies']}
"""

        prompt += """

Please analyze this task and provide:

1. **Understanding**: Briefly explain what you understand about this task

2. **Clarifying Questions**: List any questions you have (if you're confident, answer "none")

3. **Confidence Level**: Rate your understanding from 1-10
   - 1-3: Very uncertain, missing critical context
   - 4-6: Somewhat confident, have reasonable understanding
   - 7-10: Highly confident, complete understanding

4. **Related Work**: What other tasks or work items might be needed?
   - List specific tasks that should be created
   - For each, explain why it's needed

5. **Potential Issues**: What could go wrong or be confusing?

6. **Completion Criteria**: How will you know this task is done?

Answer in JSON format:
{
  "understanding": "...",
  "clarifying_questions": ["question1", "question2"],
  "confidence_level": 8,
  "related_work": [
    {"task_type": "...", "reason": "..."}
  ],
  "potential_issues": ["issue1", "issue2"],
  "completion_criteria": ["criterion1", "criterion2"]
}
"""
        return prompt

    def _parse_analysis(self, response: str) -> Dict[str, Any]:
        """Parse Claude's analysis response"""
        import json

        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        # Fallback: return parsed result manually
        return {
            "understanding": response[:200],
            "clarifying_questions": [],
            "confidence_level": 5,
            "related_work": [],
            "potential_issues": [],
            "completion_criteria": []
        }
```

---

## Experiment Implementation

### Experiment 1: Single-Feature Analysis

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from claude_agent_sdk import ClaudeSDKClient

class TicketHierarchyExperimentLocal:
    def __init__(self, num_parallel_agents=5):
        self.client = ClaudeSDKClient()
        self.num_parallel_agents = num_parallel_agents
        self.group_a_metrics = []
        self.group_b_metrics = []

    async def run_experiment_1(self, features: List[str]):
        """Run single-feature complexity test locally"""

        # Group A: Flat tasks (no tickets)
        print("Running Group A (Flat)...")
        group_a_tasks = []
        for feature in features:
            for phase in ["analyze", "design", "implement", "test"]:
                task = {
                    "id": f"{feature[:10]}-{phase}",
                    "task_type": f"{phase}_requirements",
                    "title": f"{phase.capitalize()} {feature}",
                    "description": feature,
                    "priority": "MEDIUM",
                    "phase_id": "PHASE_IMPLEMENTATION"
                }
                group_a_tasks.append((feature, task))

        # Run in parallel
        async with asyncio.Semaphore(self.num_parallel_agents):
            tasks = [
                self._analyze_task_with_simulated_agent(feature, task, ticket_context=None)
                for feature, task in group_a_tasks
            ]
            self.group_a_metrics = await asyncio.gather(*tasks)

        # Group B: Tasks with tickets
        print("Running Group B (Hierarchical)...")
        group_b_tasks = []
        for feature in features:
            ticket = {
                "id": f"TKT-{feature[:10]}",
                "title": feature,
                "description": f"Feature: {feature}",
                "phase_id": "PHASE_IMPLEMENTATION",
                "status": "building"
            }

            for phase in ["analyze", "design", "implement", "test"]:
                task = {
                    "id": f"{feature[:10]}-{phase}",
                    "task_type": f"{phase}_requirements",
                    "title": f"{phase.capitalize()} {feature}",
                    "description": feature,
                    "priority": "MEDIUM",
                    "phase_id": "PHASE_IMPLEMENTATION"
                }
                group_b_tasks.append((feature, task, ticket))

        # Run in parallel
        async with asyncio.Semaphore(self.num_parallel_agents):
            tasks = [
                self._analyze_task_with_simulated_agent(feature, task, ticket_context=ticket)
                for feature, task, ticket in group_b_tasks
            ]
            self.group_b_metrics = await asyncio.gather(*tasks)

        # Compare results
        self._compare_experiment_1_results()

    async def _analyze_task_with_simulated_agent(
        self,
        feature: str,
        task: Dict[str, Any],
        ticket_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze task with simulated agent"""

        agent = SimulatedAgent(self.client, agent_id=f"agent-{task['id']}")

        try:
            start_time = asyncio.get_event_loop().time()
            result = await agent.analyze_task(task, ticket_context)
            duration = asyncio.get_event_loop().time() - start_time

            # Track metrics
            return {
                "feature": feature,
                "task_id": task['id'],
                "task_type": task['task_type'],
                "had_ticket_context": ticket_context is not None,
                "confidence_level": result.get('confidence_level', 5),
                "questions_asked": agent.questions_asked,
                "context_api_calls": agent.context_api_calls,
                "related_work_count": len(result.get('related_work', [])),
                "potential_issues_count": len(result.get('potential_issues', [])),
                "duration_seconds": duration,
                "decisions_made": agent.decisions_made,
                "clarifying_questions": result.get('clarifying_questions', []),
                "understanding": result.get('understanding', '')
            }
        except Exception as e:
            print(f"Error analyzing task {task['id']}: {e}")
            return {
                "feature": feature,
                "task_id": task['id'],
                "error": str(e)
            }

    def _compare_experiment_1_results(self):
        """Compare Group A vs Group B results"""

        print("\n" + "="*80)
        print("EXPERIMENT 1 RESULTS: Single-Feature Analysis")
        print("="*80)

        # Filter successful results
        group_a = [m for m in self.group_a_metrics if 'error' not in m]
        group_b = [m for m in self.group_b_metrics if 'error' not in m]

        if not group_a or not group_b:
            print("Insufficient data for comparison")
            return

        # Calculate averages
        def avg(metrics, key):
            values = [m.get(key, 0) for m in metrics]
            return sum(values) / len(values) if values else 0

        print("\nGROUP A (Flat - No Tickets):")
        print(f"  Tasks analyzed: {len(group_a)}")
        print(f"  Avg confidence level: {avg(group_a, 'confidence_level'):.2f}/10")
        print(f"  Avg clarifying questions: {avg(group_a, 'questions_asked'):.2f}")
        print(f"  Avg related work discovered: {avg(group_a, 'related_work_count'):.2f}")
        print(f"  Avg potential issues identified: {avg(group_a, 'potential_issues_count'):.2f}")
        print(f"  Avg analysis duration: {avg(group_a, 'duration_seconds'):.2f}s")

        print("\nGROUP B (Hierarchical - With Tickets):")
        print(f"  Tasks analyzed: {len(group_b)}")
        print(f"  Avg confidence level: {avg(group_b, 'confidence_level'):.2f}/10")
        print(f"  Avg clarifying questions: {avg(group_b, 'questions_asked'):.2f}")
        print(f"  Avg related work discovered: {avg(group_b, 'related_work_count'):.2f}")
        print(f"  Avg potential issues identified: {avg(group_b, 'potential_issues_count'):.2f}")
        print(f"  Avg analysis duration: {avg(group_b, 'duration_seconds'):.2f}s")

        # Statistical comparison
        self._statistical_test(group_a, group_b, "confidence_level")
        self._statistical_test(group_a, group_b, "questions_asked")
        self._statistical_test(group_a, group_b, "related_work_count")

        print("\n" + "="*80)
        self._interpret_results()

    def _statistical_test(self, group_a, group_b, metric):
        """Run t-test between groups"""
        try:
            from scipy import stats
            import numpy as np

            a_values = [m.get(metric, 0) for m in group_a]
            b_values = [m.get(metric, 0) for m in group_b]

            t_stat, p_value = stats.ttest_ind(a_values, b_values)

            print(f"\n{metric.replace('_', ' ').title()}:")
            print(f"  t-statistic: {t_stat:.3f}")
            print(f"  p-value: {p_value:.4f}")

            if p_value < 0.05:
                direction = "higher" if np.mean(b_values) > np.mean(a_values) else "lower"
                print(f"  ✅ Statistically significant: Group B is {direction} than Group A")
            else:
                print(f"  ➖ No significant difference (p > 0.05)")

        except ImportError:
            print(f"\n{metric.replace('_', ' ').title()}: Install scipy for statistical testing")
        except Exception as e:
            print(f"\n{metric.replace('_', ' ').title()}: Error in statistical test: {e}")

    def _interpret_results(self):
        """Interpret the results and provide recommendation"""

        group_a = [m for m in self.group_a_metrics if 'error' not in m]
        group_b = [m for m in self.group_b_metrics if 'error' not in m]

        if not group_a or not group_b:
            return

        def avg(metrics, key):
            values = [m.get(key, 0) for m in metrics]
            return sum(values) / len(values) if values else 0

        a_conf = avg(group_a, 'confidence_level')
        b_conf = avg(group_b, 'confidence_level')
        a_questions = avg(group_a, 'questions_asked')
        b_questions = avg(group_b, 'questions_asked')
        a_related = avg(group_a, 'related_work_count')
        b_related = avg(group_b, 'related_work_count')

        print("\nINTERPRETATION:")
        print("-" * 80)

        # Ticket confidence
        if b_conf > a_conf + 0.5:
            print("✅ Tickets significantly improve agent confidence (+{:.1f})".format(b_conf - a_conf))
        elif b_conf < a_conf - 0.5:
            print("❌ Tickets reduce agent confidence (-{:.1f})".format(a_conf - b_conf))
        else:
            print("➖ Tickets don't affect confidence")

        # Questions (fewer is better)
        if b_questions < a_questions - 0.5:
            print("✅ Tickets reduce clarifying questions (-{:.1f})".format(a_questions - b_questions))
        elif b_questions > a_questions + 0.5:
            print("❌ Tickets increase clarifying questions (+{:.1f})".format(b_questions - a_questions))
        else:
            print("➖ Tickets don't affect question frequency")

        # Related work (more is better)
        if b_related > a_related + 0.5:
            print("✅ Tickets help discover more related work (+{:.1f})".format(b_related - a_related))
        elif b_related < a_related - 0.5:
            print("❌ Tickets reduce related work discovery (-{:.1f})".format(a_related - b_related))
        else:
            print("➖ Tickets don't affect related work discovery")

        print("\nRECOMMENDATION:")
        print("-" * 80)

        # Overall assessment
        ticket_benefits = 0
        ticket_harms = 0

        if b_conf > a_conf + 0.5: ticket_benefits += 1
        elif b_conf < a_conf - 0.5: ticket_harms += 1

        if b_questions < a_questions - 0.5: ticket_benefits += 1
        elif b_questions > a_questions + 0.5: ticket_harms += 1

        if b_related > a_related + 0.5: ticket_benefits += 1
        elif b_related < a_related - 0.5: ticket_harms += 1

        if ticket_benefits >= 2:
            print("🎯 STRONG RECOMMENDATION: Keep ticket hierarchy")
            print("   Tickets provide meaningful context to agents")
        elif ticket_harms >= 2:
            print("🎯 STRONG RECOMMENDATION: Remove ticket hierarchy")
            print("   Tickets add complexity without benefit")
        else:
            print("🎯 WEAK RECOMMENDATION: Results are mixed")
            print("   Consider human vs agent usability trade-off")
            print("   May need more data or different experiment design")

        print("="*80)
```

---

## Running the Experiments

### Setup

```bash
cd backend

# Install dependencies
uv sync --group test

# Activate virtual environment
source .venv/bin/activate
```

### Create Test Script

```python
# backend/tests/experiments/test_ticket_hierarchy_local.py
import asyncio
import sys

async def main():
    # Test features
    test_features = [
        "Add user authentication with JWT",
        "Implement database connection pooling",
        "Create rate limiting middleware",
        "Add email notification service",
        "Build file upload API endpoint",
        "Implement caching layer for API responses",
        "Add API documentation with OpenAPI",
        "Create admin dashboard page",
        "Implement search functionality",
        "Add API rate limits"
    ]

    # Create experiment
    experiment = TicketHierarchyExperimentLocal(num_parallel_agents=5)

    # Run Experiment 1
    await experiment.run_experiment_1(test_features)

    # Save results
    import json
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "experiment": "single_feature_analysis",
        "timestamp": timestamp,
        "group_a": experiment.group_a_metrics,
        "group_b": experiment.group_b_metrics
    }

    output_file = f"logs/experiments/ticket_hierarchy_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Execute

```bash
# Run experiment
python backend/tests/experiments/test_ticket_hierarchy_local.py

# With different parallelism
python -m experiments.ticket_hierarchy_local --parallel 3
python -m experiments.ticket_hierarchy_local --parallel 10
```

---

## Advantages of Local Simulation

### Speed

- **No sandbox spin-up**: Tests run in seconds vs minutes/hours
- **Parallel execution**: Run 5-10 agents simultaneously
- **No network overhead**: All Claude calls are local or API direct

### Cost

- **No Daytona costs**: No sandbox infrastructure
- **No storage costs**: No persisting large sandboxes
- **Claude API only**: Much cheaper than full execution

### Reproducibility

- **Deterministic**: Same prompts → same responses
- **No environment drift**: All tests in same environment
- **Easy debugging**: Can inspect every step

### Flexibility

- **Iterate quickly**: Change prompts and re-run
- **A/B test variations**: Test different ticket content formats
- **Scale up**: Add more features without waiting for sandboxes

---

## What We Can Measure Locally

### ✅ Measurable

1. **Decision Quality**
   - Confidence levels
   - Understanding accuracy
   - Plan completeness

2. **Context Usage**
   - How often ticket context is referenced
   - Clarifying questions asked
   - Missing information identification

3. **Discovery Effectiveness**
   - Related tasks identified
   - Potential issues spotted
   - Dependencies discovered

4. **Cognitive Load**
   - Time to analyze task
   - Message complexity
   - Question frequency

### ❌ Not Measurable

1. **Execution Success** (no real code runs)
2. **Code Quality** (no actual output)
3. **Runtime Performance** (no execution)
4. **Integration Issues** (no real systems)

### 🔍 Alternative Approach for Execution

If you want to test execution later:
1. **Mock execution**: Simulate pass/fail outcomes
2. **Small real execution**: 1-2 simple features with sandboxes
3. **Production telemetry**: Measure in real usage over time

---

## Parallel Execution Strategy

### Using asyncio

```python
async def run_batch_parallel(tasks, max_concurrent=10):
    """Run batch of tasks in parallel"""

    semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_with_limit(task):
        async with semaphore:
            return await analyze_task(task)

    results = await asyncio.gather(*[execute_with_limit(t) for t in tasks])
    return results
```

### Using Thread Pool

```python
from concurrent.futures import ThreadPoolExecutor
import threading

def run_batch_threaded(tasks, max_workers=10):
    """Run batch of tasks in thread pool"""

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(analyze_task_sync, tasks))

    return results
```

### Recommended: asyncio

- Native to Python 3.12+
- Efficient I/O-bound operations
- Better for API calls
- Easier error handling

---

## Cost Estimation

### Claude API Costs

Assume:
- 10 features × 4 phases = 40 tasks per group
- 2 groups = 80 total tasks
- ~5,000 tokens per task analysis
- $3 per million input tokens (Claude 3.5 Sonnet)

**Total tokens**: 80 × 5,000 = 400,000 tokens
**Total cost**: $1.20

### Time Estimation

- Single task: ~5-10 seconds
- 5 parallel agents: 80 tasks / 5 = 16 batches × 8 seconds = ~2-3 minutes

**Total experiment runtime**: 2-3 minutes vs several hours with sandboxes

---

## Next Steps

1. **Create test script** in `backend/tests/experiments/`
2. **Run small pilot** with 2-3 features to validate approach
3. **Scale to full test** with 10 features
4. **Analyze results** and compare
5. **Document findings** in experiment plan

This gives you fast, cheap, reproducible evidence about whether tickets help or hinder agent decision-making.
