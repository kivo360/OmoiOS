# Guardian System Comparison: Hephaestus vs OmoiOS

**Created**: 2025-01-30  
**Status**: Analysis Document  
**Purpose**: Compare Hephaestus Guardian capabilities with OmoiOS's existing Guardian implementation

---

## Executive Summary

OmoiOS already has a sophisticated Guardian system (`IntelligentGuardian`) that implements many of the same core concepts as Hephaestus Guardian, including trajectory analysis, alignment scoring, and steering interventions. However, Hephaestus Guardian provides more explicit guidance on **constraint persistence**, **mandatory step validation**, and **specific steering types** (stuck, drifting, violating constraints, idle, missed steps) that could enhance OmoiOS's implementation.

---

## Core Capabilities Comparison

### ✅ Already Implemented in OmoiOS

#### 1. Trajectory Analysis & Alignment Scoring
- **OmoiOS**: `IntelligentGuardian.analyze_agent_trajectory()` performs LLM-powered trajectory analysis with `alignment_score` (0.0-1.0), `trajectory_aligned` boolean, and `trajectory_summary`
- **Hephaestus**: Similar trajectory analysis with alignment scores (0-100%)
- **Status**: ✅ **Fully implemented** - OmoiOS has equivalent capability

#### 2. Accumulated Context Building
- **OmoiOS**: `TrajectoryContext.build_accumulated_context()` builds complete understanding from entire conversation history, extracts:
  - Overall goal
  - Persistent constraints
  - Standing instructions
  - References and context markers
  - Journey tracking (phases completed, current focus, attempted approaches)
- **Hephaestus**: Similar accumulated context from past summaries timeline
- **Status**: ✅ **Fully implemented** - OmoiOS has equivalent capability

#### 3. Past Summaries Timeline
- **OmoiOS**: `IntelligentGuardian._get_past_summaries_timeline()` retrieves past trajectory summaries with timestamps, alignment scores, and summaries
- **Hephaestus**: Similar timeline of past summaries showing agent journey
- **Status**: ✅ **Fully implemented** - OmoiOS has equivalent capability

#### 4. Phase Context Integration
- **OmoiOS**: `IntelligentGuardian._get_phase_context()` loads phase definitions including `done_definitions`, `expected_outputs`, `phase_prompt`, `next_steps_guide`
- **Hephaestus**: Similar phase context loading with mandatory steps and done definitions
- **Status**: ✅ **Fully implemented** - OmoiOS has equivalent capability

#### 5. Steering Interventions
- **OmoiOS**: `IntelligentGuardian.decide_steering_interventions()` creates `SteeringIntervention` objects with `steering_type`, `message`, `reason`, `confidence`
- **Hephaestus**: Similar steering interventions sent to agents
- **Status**: ✅ **Fully implemented** - OmoiOS has equivalent capability

#### 6. Monitoring Loop
- **OmoiOS**: `MonitoringLoop` orchestrates Guardian analysis every 60 seconds (`guardian_interval_seconds: 60`)
- **Hephaestus**: Guardian runs every 60 seconds for all active agents
- **Status**: ✅ **Fully implemented** - OmoiOS has equivalent capability

#### 7. LLM-Powered Analysis
- **OmoiOS**: Uses `LLMService` with Jinja2 templates (`guardian_analysis.md.j2`) for trajectory analysis
- **Hephaestus**: Uses configurable LLM (recommends `gpt-oss:120b` via OpenRouter with Cerebras)
- **Status**: ✅ **Fully implemented** - OmoiOS has equivalent capability (LLM configurable)

---

## Gaps & Enhancement Opportunities

### 🔴 Missing: Explicit Constraint Persistence Validation

**Hephaestus**: Guardian explicitly validates that constraints persist throughout the entire session, even if mentioned 20 minutes ago. Example: "If you said 'no external libraries' at the start, Guardian enforces that throughout."

**OmoiOS**: `TrajectoryContext` extracts `persistent_constraints` and `lifted_constraints`, but the Guardian analysis template doesn't explicitly validate constraint violations as a primary check.

**Recommendation**: Enhance `guardian_analysis.md.j2` template to explicitly check constraint violations and provide specific violation messages like Hephaestus does.

### 🔴 Missing: Explicit Mandatory Step Validation

**Hephaestus**: Guardian explicitly checks if agents skipped mandatory steps from phase instructions. Example: "Phase instructions require: search_tickets() before creating new tickets. You created a ticket without searching."

**OmoiOS**: Template includes `missing_steps` in details, but doesn't explicitly validate mandatory steps as a primary steering trigger.

**Recommendation**: Add explicit mandatory step validation in Guardian analysis, checking phase instructions for `⚠️ MANDATORY:` markers or similar.

### 🟡 Partial: Specific Steering Types

**Hephaestus**: Five explicit steering types:
1. **Stuck** - Same error appearing 5+ times
2. **Drifting** - Working on unrelated areas
3. **Violating Constraints** - Breaking rules from earlier conversation
4. **Idle** - Agent finished but hasn't updated status
5. **Missed Steps** - Agent skipped mandatory phase instructions

**OmoiOS**: Uses generic `steering_type` values: `"guidance"`, `"correction"`, `"emergency"` (from template). Doesn't explicitly categorize by root cause.

**Recommendation**: Add Hephaestus-style steering type categorization to provide more specific intervention messages.

### 🟡 Partial: Constraint Violation Detection

**Hephaestus**: Explicitly detects constraint violations with context: "You're installing 'jsonwebtoken' package, but the constraint from Phase 1 says 'no external auth libraries'. Use Node.js built-in crypto module instead."

**OmoiOS**: Template includes `constraint_violations` in details, but doesn't provide Hephaestus-style specific violation messages with context.

**Recommendation**: Enhance constraint violation detection to provide specific, actionable messages like Hephaestus.

### 🟡 Partial: Idle Detection

**Hephaestus**: Explicitly detects when agent completes work but hasn't called `update_task_status(status='done')`.

**OmoiOS**: May detect this through alignment analysis, but not explicitly as a steering type.

**Recommendation**: Add explicit idle detection when agent appears finished but hasn't updated status.

---

## Implementation Recommendations

### Priority 1: Enhance Steering Type Categorization

**Action**: Update `IntelligentGuardian` to categorize steering types explicitly:

```python
class SteeringType(Enum):
    STUCK = "stuck"  # Same error 5+ times
    DRIFTING = "drifting"  # Working on unrelated areas
    VIOLATING_CONSTRAINTS = "violating_constraints"  # Breaking rules
    IDLE = "idle"  # Finished but hasn't updated status
    MISSED_STEPS = "missed_steps"  # Skipped mandatory steps
    GUIDANCE = "guidance"  # Minor course correction
    CORRECTION = "correction"  # Significant redirection
    EMERGENCY = "emergency"  # Critical intervention
```

### Priority 2: Enhance Constraint Violation Detection

**Action**: Update `guardian_analysis.md.j2` template to explicitly check constraint violations:

```jinja2
{% if trajectory_data.persistent_constraints %}
## Constraint Validation
{% for constraint in trajectory_data.persistent_constraints %}
- [ ] Agent is not violating: "{{ constraint.description }}"
  {% if constraint.source %} (from {{ constraint.source }}){% endif %}
{% endfor %}
{% endif %}
```

### Priority 3: Add Mandatory Step Validation

**Action**: Parse phase instructions for `⚠️ MANDATORY:` markers and validate completion:

```python
def _extract_mandatory_steps(self, phase_context: Dict[str, Any]) -> List[str]:
    """Extract mandatory steps from phase instructions."""
    phase_prompt = phase_context.get("phase_prompt", "")
    # Look for MANDATORY markers
    mandatory_pattern = r"⚠️\s*MANDATORY:\s*(.+?)(?=\n|$)"
    # ... extract and return
```

### Priority 4: Enhance Intervention Messages

**Action**: Update intervention message generation to provide Hephaestus-style specific guidance:

```python
def _generate_intervention_message(
    self,
    steering_type: SteeringType,
    violation_details: Dict[str, Any],
) -> str:
    """Generate specific intervention message based on steering type."""
    if steering_type == SteeringType.VIOLATING_CONSTRAINTS:
        constraint = violation_details["constraint"]
        action = violation_details["action"]
        return (
            f"You're {action}, but the constraint from {constraint['source']} "
            f"says '{constraint['description']}'. {constraint['alternative']}"
        )
    # ... other types
```

---

## Alignment with Product Vision

The Hephaestus Guardian enhancements align perfectly with OmoiOS's product vision:

1. **"Self-Healing System"** - Enhanced constraint validation and mandatory step checking make workflows more self-healing
2. **"Strategic Oversight"** - Better steering type categorization helps users understand why interventions occur
3. **"Adaptive Monitoring"** - Explicit constraint persistence and mandatory step validation improve monitoring effectiveness
4. **"Mutual Agent Monitoring"** - More specific intervention types help Guardian provide better guidance

---

## Conclusion

OmoiOS already has a **sophisticated Guardian system** that implements the core concepts from Hephaestus Guardian. The main gaps are:

1. **Explicit constraint violation detection** with specific messages
2. **Mandatory step validation** from phase instructions
3. **Specific steering type categorization** (stuck, drifting, violating constraints, idle, missed steps)
4. **Idle detection** when agents finish but don't update status

These enhancements would make OmoiOS's Guardian even more effective at keeping agents on track, aligning with the product vision of a self-healing, adaptive monitoring system.

---

## Related Documents

- [Product Vision](./product_vision.md) - OmoiOS product vision
- [Intelligent Monitoring Enhancements](./implementation/monitoring/intelligent_monitoring_enhancements.md) - Current Guardian implementation
- [Hephaestus Workflow Enhancements](./implementation/workflows/hephaestus_workflow_enhancements.md) - Phase-based workflow system
