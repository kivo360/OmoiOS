# Ticket vs Task Hierarchy Experiment Plan

**Created**: 2026-01-19
**Status**: Planned
**Purpose**: Determine whether the Ticket → Task hierarchy adds value to AI agents or creates unnecessary complexity.

---

## Problem Statement

The system currently uses a hierarchical structure:
- **Ticket**: High-level feature/work item
- **Task**: Atomic work unit for agents

**Concern**: For AI agents, this adds indirection:
- Agents must query both tickets and tasks to understand work
- Dual state tracking (ticket status + task status)
- Potential for confusion about completion and dependencies

**Question**: Does the ticket layer provide meaningful context that improves agent performance, or is it just redundant complexity?

---

## Hypotheses

### H1: Ticket layer is valuable
- Tickets provide necessary context about the larger feature
- Agents perform better when they understand the "story" behind tasks
- Task completion correlates with ticket-level alignment

### H2: Ticket layer is redundant
- Tasks already have phase_id and other context
- Additional indirection doesn't improve agent performance
- Simplified architecture reduces API calls and state confusion

---

## Experimental Design

### Approach: A/B Testing with Identical Tasks

Create test scenarios with the exact same feature requests, but with different structure:

**Group A: Flat Task Graph** (No tickets)
**Group B: Hierarchical** (Tasks within tickets)

---

## Experiment 1: Single-Feature Complexity

### Setup

Create 10 identical feature requests across both groups:

```python
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
    "Add API rate limiting"
]
```

**Group A (Flat)**:
```python
tasks = []
for feature in test_features:
    tasks.extend([
        Task(type="analyze_requirements", description=feature, ...),
        Task(type="design", description=feature, ...),
        Task(type="implement", description=feature, ...),
        Task(type="test", description=feature, ...)
    ])
```

**Group B (Hierarchical)**:
```python
for feature in test_features:
    ticket = Ticket(
        title=feature,
        description=feature,
        phase_id="PHASE_IMPLEMENTATION",
        ...
    )
    tasks = [
        Task(type="analyze_requirements", ticket_id=ticket.id, description=feature, ...),
        Task(type="design", ticket_id=ticket.id, description=feature, ...),
        Task(type="implement", ticket_id=ticket.id, description=feature, ...),
        Task(type="test", ticket_id=ticket.id, description=feature, ...)
    ]
    # Save ticket, then save tasks with ticket_id
```

### Execution

1. Both groups execute through the same agent workflow
2. Agents work through tasks sequentially or in parallel based on dependencies
3. Track all metrics throughout execution

### Metrics to Capture

#### Context API Calls
- Number of ticket lookups per task
- Number of ticket API calls per agent
- Time spent querying ticket context vs working on task

#### State Tracking Complexity
- Number of status checks (ticket status + task status)
- State machine transitions tracked
- Complexity of dependency resolution

#### Error Rates
- Context-related errors (missing ticket info, confusion about completion)
- Dependency resolution errors
- Execution failures

#### Performance
- Total execution time per feature
- API call overhead
- Database query count

#### Quality Metrics
- Task completion accuracy (does it match the feature?)
- Test failure rate
- Code quality scores
- Agent confidence in understanding requirements

#### Agent Experience (if trackable)
- Agent message length (more complex context = longer messages)
- Number of clarifying questions asked
- Agent self-correction rate

---

## Experiment 2: Nested vs Flat Task Graphs

### Setup

Test whether ticket-level nesting affects ability to work across features:

```python
test_features = [
    "Authentication system",
    "User profile management",
    "Data export functionality"
]
```

**Flat Graph**:
```
Task 1: Auth analyze
Task 2: Auth design
Task 3: Auth implement
Task 4: Auth test

Task 5: Profile analyze
Task 6: Profile design
Task 7: Profile implement
Task 8: Profile test

Task 9: Export analyze
Task 10: Export design
Task 11: Export implement
Task 12: Export test
```

**Nested Graph**:
```
Ticket 1: Authentication
  Task 1: Auth analyze
  Task 2: Auth design
  Task 3: Auth implement
  Task 4: Auth test

Ticket 2: Profile Management
  Task 5: Profile analyze
  Task 6: Profile design
  Task 7: Profile implement
  Task 8: Profile test

Ticket 3: Data Export
  Task 9: Export analyze
  Task 10: Export design
  Task 11: Export implement
  Task 12: Export test
```

**Cross-feature dependencies**:
- Task 8 (Profile test) depends on Task 3 (Auth implement)
- Task 12 (Export test) depends on Task 7 (Profile implement)

### Metrics

1. **Dependency Resolution Time**
   - How long to resolve cross-ticket dependencies?
   - Does nested context help or hinder?

2. **Context Switching Cost**
   - Time to retrieve context for cross-feature dependencies
   - API call patterns

3. **Error Rate for Cross-Feature Issues**
   - Missing context about related features
   - Incomplete understanding of dependencies

---

## Experiment 3: Discovery and Branching

### Setup

Test how agents handle discovery workflows (similar to spec-driven development):

```python
test_features = [
    "Add dark mode toggle"
]
```

**Scenario**:
1. Agent starts analyzing "dark mode toggle"
2. Agent discovers it needs color scheme system first
3. Agent spawns new task: "Design color scheme system"

**Group A (Flat)**:
- Agent sees all tasks in flat list
- Must track context manually

**Group B (Hierarchical)**:
- Agent sees tasks within ticket
- Has automatic context of "dark mode toggle" project

### Metrics

1. **Discovery Effectiveness**
   - Did agents find necessary related work?
   - Did they miss anything?

2. **Context Accuracy**
   - Did they maintain correct context during discovery?
   - How often did they reference the original feature?

3. **Branching Performance**
   - Time to spawn and execute discovery tasks
   - Success rate of discovery branches

---

## Experiment 4: Scalability Test

### Setup

Test with increasing numbers of concurrent features:

**Group A**: 5, 10, 20, 50 concurrent features (all flat)
**Group B**: Same counts with ticket grouping

### Metrics

1. **System Load**
   - Database query count per feature
   - API call overhead per task

2. **Agent Bottlenecks**
   - Max concurrent agents that can work effectively
   - Queue buildup

3. **Memory/CPU Usage**
   - Context accumulation over time
   - State tracking overhead

---

## Implementation Approach

### Local Simulation (Recommended)

**See**: `ticket_hierarchy_local_simulation.md` for detailed guide

Run experiments locally using Claude Agent SDK in analysis mode:

**Benefits:**
- Fast: 2-3 minutes vs several hours
- Cheap: ~$1.20 vs $100+ for sandboxes
- Reproducible: Same prompts → same responses
- Parallel: Run 5-10 agents simultaneously

**What it tests:**
- Agent decision quality (confidence, understanding)
- Context usage (ticket references, clarifying questions)
- Discovery effectiveness (related tasks identified)
- Cognitive load (analysis time, message complexity)

**What it doesn't test:**
- Actual code execution (no real sandbox)
- Code quality (no output to measure)
- Integration issues (no real systems)

### Full Sandbox Execution (Optional)

If you want to test execution later:
1. Run small pilot: 1-2 simple features
2. Measure production telemetry over time
3. Compare local analysis vs actual execution results

---

## Implementation Details

### Local Test Framework (Simulation)

```python
# experiments/ticket_hierarchy_test.py
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.agent_manager import AgentManager

class TicketHierarchyExperiment:
    def __init__(self, experiment_id):
        self.experiment_id = experiment_id
        self.metrics = {
            "group_a": self.init_metrics(),
            "group_b": self.init_metrics()
        }

    def init_metrics(self):
        return {
            "context_api_calls": 0,
            "state_check_count": 0,
            "error_count": 0,
            "execution_time": 0,
            "completion_accuracy": 0,
            "discovery_branches": 0
        }

    def run_flat_experiment(self, features):
        """Run tasks without tickets"""
        for feature in features:
            tasks = self.create_flat_tasks(feature)
            for task in tasks:
                task_id = self.queue_task(task)
                self.metrics["group_a"]["context_api_calls"] += 1
                self.metrics["group_a"]["state_check_count"] += 2  # task + ticket status
                self.execute_task(task_id)

    def run_hierarchical_experiment(self, features):
        """Run tasks within tickets"""
        for feature in features:
            ticket = self.create_ticket(feature)
            tasks = self.create_hierarchical_tasks(feature, ticket)
            for task in tasks:
                task_id = self.queue_task(task, ticket_id=ticket.id)
                self.metrics["group_b"]["context_api_calls"] += 1
                self.metrics["group_b"]["state_check_count"] += 2  # task + ticket status
                self.execute_task(task_id)

    def execute_task(self, task_id):
        """Execute task and track metrics"""
        start = time.time()
        result = self.run_agent_on_task(task_id)
        duration = time.time() - start

        self.metrics["execution_time"] += duration
        if result["errors"]:
            self.metrics["error_count"] += 1

        if result["accuracy_score"]:
            self.metrics["completion_accuracy"] += result["accuracy_score"]

    def compare_groups(self):
        """Analyze and compare results"""
        for group in ["group_a", "group_b"]:
            metrics = self.metrics[group]

            print(f"\n{group.upper()} Results:")
            print(f"  Context API calls per task: {metrics['context_api_calls']}")
            print(f"  State checks per task: {metrics['state_check_count']}")
            print(f"  Errors: {metrics['error_count']}")
            print(f"  Avg execution time: {metrics['execution_time']:.2f}s")
            print(f"  Completion accuracy: {metrics['completion_accuracy']:.2%}")

        # Statistical significance
        self.compute_significance()

    def compute_significance(self):
        """Calculate statistical significance"""
        from scipy import stats

        # Simple comparison (would use proper statistical test in real implementation)
        a_errors = self.metrics["group_a"]["error_count"]
        b_errors = self.metrics["group_b"]["error_count"]

        print(f"\nSignificance analysis:")
        print(f"  Ticket layer changed error rate: {a_errors} → {b_errors}")

        # Determine if ticket layer is beneficial
        if b_errors < a_errors:
            print("  ✅ Ticket layer reduces errors")
        elif b_errors > a_errors:
            print("  ❌ Ticket layer increases errors")
        else:
            print("  ➖ No significant difference")
```

### Running Experiments (Local Simulation)

```bash
# Quick setup
cd backend
uv sync --group test
source .venv/bin/activate

# Run experiment (simulated, no sandboxes)
python tests/experiments/test_ticket_hierarchy_local.py

# With different parallelism
python tests/experiments/test_ticket_hierarchy_local.py --parallel 3
python tests/experiments/test_ticket_hierarchy_local.py --parallel 10
```

**Expected runtime**: 2-3 minutes for 10 features
**Expected cost**: ~$1.20 in Claude API calls
**Output**: `logs/experiments/ticket_hierarchy_YYYYMMDD_HHMMSS.json`

See `ticket_hierarchy_local_simulation.md` for full implementation details.

### Data Collection

Experiments will collect:

1. **Execution Logs** - Full execution traces
2. **API Call Metrics** - Ticket vs task API calls
3. **Agent Messages** - To analyze context usage
4. **Performance Metrics** - Timing and resource usage
5. **Error Logs** - Any failures or confusion

All data stored in:
- `logs/experiments/{experiment_id}/` directory
- Structured JSON + text logs

---

## Expected Outcomes

### If Tickets Add Value:

**Group B (Hierarchical)** should show:
- Lower error rates (better context understanding)
- Higher completion accuracy
- More efficient discovery workflows
- Clear correlation between task quality and ticket-level alignment

**Group A (Flat)** should show:
- Higher API call overhead (more separate context lookups)
- More context-related errors
- Higher state tracking complexity

### If Tickets are Redundant:

**Both Groups** should show:
- Similar performance metrics
- No significant difference in error rates
- Comparable quality scores
- Ticket layer only adds indirection

### Mixed Results:

- **Partial value**: Tickets help with some tasks but not others
  - Consider selective ticket usage
  - Differentiate between simple tasks (flat) vs complex features (tickets)

- **Architecture trade-offs**:
  - Tickets better for human organization
  - Tasks better for agent execution
  - Consider hybrid approach (tickets optional)

---

## Analysis Framework

### Statistical Analysis

Use proper statistical testing:
- **Chi-squared test** for categorical outcomes (errors, success/failure)
- **t-test** for continuous outcomes (execution time, accuracy)
- **ANOVA** for comparing multiple groups

### Effect Size

Calculate effect size to determine practical significance:
- Cohen's d for comparing two groups
- R-squared for regression analysis

### Qualitative Analysis

1. **Error Categorization**
   - Context-related errors (missing ticket info)
   - Dependency resolution errors
   - Execution errors (unrelated to hierarchy)

2. **Agent Behavior**
   - How often agents reference ticket context
   - Whether they ask clarifying questions about missing context
   - Message length and complexity patterns

3. **Discovery Effectiveness**
   - Quality of discovered work
   - Branching success rate

---

## Decision Matrix

Based on results, determine next steps:

### Scenario 1: Tickets Clearly Valuable (p < 0.05, large effect size)

**Recommendation**: Keep hierarchical structure
**Action**:
- Refine ticket context guidelines
- Optimize ticket query performance
- Add training data on ticket usage

### Scenario 2: Tickets Clearly Redundant (p < 0.05, large negative effect size)

**Recommendation**: Simplify to flat task graph
**Action**:
- Remove ticket model from task creation flow
- Update agent tools to work directly with tasks
- Modify frontend to display tasks directly

### Scenario 3: No Significant Difference (p > 0.05)

**Recommendation**: Based on other factors
**Decision criteria**:
- **Human usability**: Is ticket layer better for human organization?
- **Code maintainability**: Does it reduce complexity elsewhere?
- **Future flexibility**: Will it enable better features later?

**Action**:
- If human usability is priority → Keep tickets
- If agent performance is priority → Remove tickets
- If both are equal → Consider gradual deprecation

---

## Timeline

### Week 1: Setup and Validation

- [ ] Implement test framework
- [ ] Create sample test features
- [ ] Validate experiment infrastructure
- [ ] Run pilot test with 1-2 features

### Week 2: Execution

- [ ] Run Experiment 1 (single-feature complexity)
  - [ ] 10 features, Group A
  - [ ] 10 features, Group B

- [ ] Run Experiment 2 (nested vs flat)
  - [ ] 3 features with cross-ticket dependencies
  - [ ] Repeat 5 times for statistical significance

- [ ] Run Experiment 3 (discovery and branching)
  - [ ] 5 features with discovery workflows
  - [ ] Repeat 10 times

- [ ] Run Experiment 4 (scalability)
  - [ ] Gradually increase concurrent features
  - [ ] Monitor system behavior

### Week 3: Analysis and Decision

- [ ] Compile all metrics
- [ ] Statistical analysis
- [ ] Qualitative analysis
- [ ] Document findings
- [ ] Create decision recommendation
- [ ] Present results to stakeholders

---

## Success Criteria

Experiment is considered successful if:

1. **Clear statistical evidence**: p < 0.05 with practical effect size
2. **Actionable findings**: Results inform clear architectural decision
3. **Reproducible**: Results can be reproduced with slight variations
4. **Actionable recommendation**: Decision matrix provides clear path forward

If results are inconclusive:
- Recommend additional experiments
- Consider qualitative user feedback
- Pilot implementation of both approaches

---

## Risks and Mitigations

### Risk 1: Insufficient Statistical Power

**Mitigation**:
- Run experiments multiple times (10+ repetitions)
- Use power analysis to determine sample size
- Use appropriate statistical tests

### Risk 2: Agent Behavior Changes Between Runs

**Mitigation**:
- Fix agent seed for reproducibility
- Use consistent prompts and configurations
- Run multiple separate agent instances

### Risk 3: Ticket Context Not Properly Utilized

**Mitigation**:
- Ensure tickets have meaningful descriptions
- Verify agent tools can access ticket context
- Add monitoring to track actual ticket API usage

### Risk 4: Confounding Variables

**Mitigation**:
- Control for all other variables (prompts, tools, models)
- Randomize execution order
- Use consistent task types and complexity

---

## Future Extensions

After initial experiments:

1. **A/B Testing in Production**:
   - Deploy both systems to small user groups
   - Measure real-world impact

2. **Hybrid Approaches**:
   - Test tickets only for features above complexity threshold
   - Test flat structure for simple bug fixes

3. **Optimization Studies**:
   - How deep can ticket nesting go before confusion?
   - Optimal ticket granularity (5 tasks vs 10 tasks per ticket)

4. **Agent Training**:
   - Train agents specifically on flat vs hierarchical workflows
   - Compare performance improvement from training

---

## Conclusion

This experiment framework provides a rigorous, data-driven approach to determining whether the Ticket → Task hierarchy is worth the architectural complexity. By running controlled experiments with identical scenarios, we can make an evidence-based decision that optimizes for agent performance while maintaining human usability if that's a priority.

**Next Steps**:
1. Set up test environment
2. Run pilot test
3. Scale to full experiments
4. Analyze and decide
