# Async Parallelization Opportunities

After migrating to async SQLAlchemy, many operations can be parallelized to improve performance. This document identifies specific opportunities and shows how they would be implemented.

---

## 1. Agent Trajectory Analysis (High Impact)

### Current: Sequential Analysis

**Location**: `omoi_os/services/intelligent_guardian.py`

**Current Pattern** (Sequential):
```python
def analyze_all_active_agents(self, force_analysis: bool = False) -> List[TrajectoryAnalysis]:
    """Analyze trajectories of all active agents."""
    active_agents = self.output_collector.get_active_agents()
    analyses = []

    for agent in active_agents:  # ❌ Sequential - one at a time
        analysis = self.analyze_agent_trajectory(agent.id, force_analysis)
        if analysis:
            analyses.append(analysis)

    return analyses
```

**Problem**: If you have 10 agents, and each analysis takes 2 seconds (DB queries + LLM call), total time = **20 seconds**.

### Parallelized Version

**After Async Migration**:
```python
async def analyze_all_active_agents(
    self, 
    force_analysis: bool = False,
    max_concurrent: int = 5
) -> List[TrajectoryAnalysis]:
    """Analyze trajectories of all active agents in parallel."""
    active_agents = await self.output_collector.get_active_agents()
    
    # Create tasks for all agents
    tasks = [
        self.analyze_agent_trajectory(agent.id, force_analysis)
        for agent in active_agents
    ]
    
    # Run up to max_concurrent analyses in parallel
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def analyze_with_limit(agent_id: str):
        async with semaphore:
            return await self.analyze_agent_trajectory(agent_id, force_analysis)
    
    # Execute all analyses concurrently
    results = await asyncio.gather(
        *[analyze_with_limit(agent.id) for agent in active_agents],
        return_exceptions=True
    )
    
    # Filter out None and exceptions
    analyses = [
        r for r in results 
        if r is not None and not isinstance(r, Exception)
    ]
    
    return analyses
```

**Performance Gain**: 10 agents × 2 seconds = **20 seconds** → **~4 seconds** (with max_concurrent=5)
**Speedup**: **5x faster**

---

## 2. Monitoring Cycle Operations (High Impact)

### Current: Sequential Steps

**Location**: `omoi_os/services/monitoring_loop.py`

**Current Pattern** (Sequential):
```python
async def run_single_cycle(self) -> MonitoringCycle:
    """Run a single complete monitoring cycle."""
    # Step 1: Guardian trajectory analysis
    guardian_analyses = await self._run_guardian_analysis()  # Wait for this
    
    # Step 2: Conductor system coherence analysis
    conductor_analysis = await self._run_conductor_analysis(cycle_id)  # Then wait for this
    
    # Step 3: Generate and execute steering interventions
    steering_interventions = await self._process_steering_interventions()  # Then this
    
    # Step 4: Update system state
    await self._update_system_state(guardian_analyses, conductor_analysis)
```

**Problem**: Each step waits for the previous one, even though some could run in parallel.

### Parallelized Version

**After Async Migration**:
```python
async def run_single_cycle(self) -> MonitoringCycle:
    """Run a single complete monitoring cycle with parallel operations."""
    cycle_id = uuid.uuid4()
    started_at = utc_now()
    
    # Run guardian and conductor analyses in parallel (they're independent)
    guardian_task = self._run_guardian_analysis()
    conductor_task = self._run_conductor_analysis(cycle_id)
    
    # Wait for both to complete
    guardian_analyses, conductor_analysis = await asyncio.gather(
        guardian_task,
        conductor_task
    )
    
    # Process steering interventions (depends on guardian_analyses)
    steering_interventions = await self._process_steering_interventions()
    
    # Update system state (can run in parallel with other operations)
    update_task = self._update_system_state(guardian_analyses, conductor_analysis)
    
    # Wait for state update
    await update_task
    
    # ... rest of cycle
```

**Performance Gain**: If guardian takes 5s and conductor takes 3s:
- **Sequential**: 5s + 3s = **8 seconds**
- **Parallel**: max(5s, 3s) = **5 seconds**
**Speedup**: **1.6x faster**

---

## 3. Emergency Analysis for Multiple Agents (High Impact)

### Current: Sequential Loop

**Location**: `omoi_os/services/monitoring_loop.py`

**Current Pattern** (Sequential):
```python
async def trigger_emergency_analysis(self, agent_ids: List[str]) -> Dict[str, Any]:
    """Trigger emergency analysis for specific agents."""
    emergency_analyses = []
    
    for agent_id in agent_ids:  # ❌ Sequential
        analysis = await self.analyze_agent_trajectory(agent_id, force_analysis=True)
        if analysis:
            emergency_analyses.append(analysis)
```

**Problem**: Analyzing 5 agents sequentially = 5 × 2s = **10 seconds**.

### Parallelized Version

**After Async Migration**:
```python
async def trigger_emergency_analysis(self, agent_ids: List[str]) -> Dict[str, Any]:
    """Trigger emergency analysis for specific agents in parallel."""
    logger.info(f"Triggering emergency analysis for agents: {agent_ids}")
    
    # Analyze all agents in parallel
    analysis_tasks = [
        self.analyze_agent_trajectory(agent_id, force_analysis=True)
        for agent_id in agent_ids
    ]
    
    results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
    
    # Filter out None and exceptions
    emergency_analyses = [
        r for r in results 
        if r is not None and not isinstance(r, Exception)
    ]
    
    # Run conductor analysis in parallel with interventions
    conductor_task = self.conductor.analyze_system_coherence_response()
    
    # Generate emergency interventions
    emergency_interventions = []
    for analysis in emergency_analyses:
        if analysis.needs_steering and analysis.steering_recommendation:
            emergency_interventions.append({
                "agent_id": analysis.agent_id,
                "steering_type": analysis.steering_type,
                "message": analysis.steering_recommendation,
                "emergency": True,
            })
    
    conductor_response = await conductor_task
    
    return {
        "emergency_analyses": len(emergency_analyses),
        "system_coherence": conductor_response.coherence_score,
        "emergency_interventions": emergency_interventions,
        "triggered_at": utc_now().isoformat(),
    }
```

**Performance Gain**: 5 agents × 2s = **10 seconds** → **~2 seconds**
**Speedup**: **5x faster**

---

## 4. Database Queries for Multiple Entities (Medium Impact)

### Current: Sequential Queries

**Location**: `omoi_os/services/task_queue.py`, `omoi_os/services/agent_health.py`

**Current Pattern** (Sequential):
```python
def get_assigned_tasks(self, agent_id: str) -> list[Task]:
    """Get all tasks assigned to a specific agent."""
    with self.db.get_session() as session:
        tasks = (
            session.query(Task)
            .filter(
                Task.assigned_agent_id == agent_id,
                Task.status.in_(["assigned", "running"]),
            )
            .all()
        )
        # Then expunge each one sequentially
        for task in tasks:  # ❌ Sequential
            session.expunge(task)
        return tasks
```

**Problem**: If you need to get tasks for multiple agents, you do it sequentially.

### Parallelized Version

**After Async Migration**:
```python
async def get_assigned_tasks_batch(self, agent_ids: List[str]) -> Dict[str, List[Task]]:
    """Get assigned tasks for multiple agents in parallel."""
    async def get_tasks_for_agent(agent_id: str) -> List[Task]:
        async with self.db.get_session() as session:
            result = await session.execute(
                select(Task).where(
                    Task.assigned_agent_id == agent_id,
                    Task.status.in_(["assigned", "running"]),
                )
            )
            tasks = result.scalars().all()
            # Expunge all at once
            for task in tasks:
                session.expunge(task)
            return tasks
    
    # Get tasks for all agents in parallel
    results = await asyncio.gather(
        *[get_tasks_for_agent(agent_id) for agent_id in agent_ids]
    )
    
    # Return as dictionary
    return {
        agent_id: tasks 
        for agent_id, tasks in zip(agent_ids, results)
    }
```

**Performance Gain**: 10 agents × 0.1s per query = **1 second** → **~0.1 seconds**
**Speedup**: **10x faster**

---

## 5. Health Checks for Multiple Agents (Medium Impact)

### Current: Sequential Health Checks

**Location**: `omoi_os/services/agent_health.py`, `omoi_os/api/main.py`

**Current Pattern** (Sequential):
```python
async def heartbeat_monitoring_loop():
    """Check for missed heartbeats."""
    while True:
        # Check all agents sequentially
        agents_with_missed = heartbeat_protocol_service.check_missed_heartbeats()
        
        for agent_data, missed_count in agents_with_missed:  # ❌ Sequential
            agent_id = agent_data["id"]
            if missed_count >= 3:
                # Process restart sequentially
                await process_restart(agent_id)
```

**Problem**: Processing 20 agents sequentially = 20 × 0.5s = **10 seconds**.

### Parallelized Version

**After Async Migration**:
```python
async def heartbeat_monitoring_loop():
    """Check for missed heartbeats with parallel processing."""
    while True:
        # Get all agents with missed heartbeats
        agents_with_missed = await heartbeat_protocol_service.check_missed_heartbeats()
        
        # Process all restarts in parallel (with limit)
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent restarts
        
        async def process_with_limit(agent_data, missed_count):
            async with semaphore:
                agent_id = agent_data["id"]
                if missed_count >= 3:
                    await process_restart(agent_id)
        
        # Process all agents in parallel
        await asyncio.gather(
            *[
                process_with_limit(agent_data, missed_count)
                for agent_data, missed_count in agents_with_missed
            ],
            return_exceptions=True
        )
        
        await asyncio.sleep(10)
```

**Performance Gain**: 20 agents × 0.5s = **10 seconds** → **~2 seconds** (with semaphore=5)
**Speedup**: **5x faster**

---

## 6. LLM API Calls (High Impact)

### Current: Sequential LLM Calls

**Location**: `omoi_os/services/intelligent_guardian.py`, `omoi_os/services/conductor.py`

**Current Pattern** (Sequential):
```python
def analyze_agent_trajectory(self, agent_id: str) -> TrajectoryAnalysis:
    """Analyze agent trajectory with LLM."""
    # Get context (DB query)
    context = self.trajectory_context.build_accumulated_context(agent_id)
    
    # Get agent output (DB query)
    output = self.output_collector.get_agent_output(agent_id)
    
    # Call LLM (API call - slow!)
    llm_response = self.llm_service.ainvoke(prompt)  # ❌ Sequential
    
    return analysis
```

**Problem**: If analyzing 5 agents, each with 2s LLM call = **10 seconds**.

### Parallelized Version

**After Async Migration**:
```python
async def analyze_agent_trajectory(self, agent_id: str) -> TrajectoryAnalysis:
    """Analyze agent trajectory with parallel DB queries and LLM."""
    # Run DB queries in parallel
    context_task = self.trajectory_context.build_accumulated_context(agent_id)
    output_task = self.output_collector.get_agent_output(agent_id)
    
    # Wait for both DB queries
    context, output = await asyncio.gather(context_task, output_task)
    
    # Call LLM (already async)
    llm_response = await self.llm_service.ainvoke(prompt)
    
    return analysis

# For multiple agents - parallelize LLM calls
async def analyze_all_active_agents(self):
    """Analyze all agents with parallel LLM calls."""
    active_agents = await self.output_collector.get_active_agents()
    
    # Create all LLM analysis tasks
    analysis_tasks = [
        self.analyze_agent_trajectory(agent.id)
        for agent in active_agents
    ]
    
    # Run all LLM calls in parallel (with semaphore to limit concurrent calls)
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent LLM calls
    
    async def analyze_with_limit(agent_id: str):
        async with semaphore:
            return await self.analyze_agent_trajectory(agent_id)
    
    results = await asyncio.gather(
        *[analyze_with_limit(agent.id) for agent in active_agents],
        return_exceptions=True
    )
    
    return [r for r in results if r is not None]
```

**Performance Gain**: 5 agents × 2s LLM call = **10 seconds** → **~4 seconds** (with semaphore=3)
**Speedup**: **2.5x faster**

---

## 7. Batch Task Operations (Medium Impact)

### Current: Sequential Updates

**Location**: `omoi_os/services/task_queue.py`

**Current Pattern** (Sequential):
```python
def get_next_tasks_batch(self, phase_id: str, limit: int = 10) -> List[Task]:
    """Get multiple tasks."""
    with self.db.get_session() as session:
        tasks = session.query(Task).filter(...).limit(limit).all()
        
        # Update scores sequentially
        for task in tasks:  # ❌ Sequential
            task.score = self.scorer.compute_score(task)
            session.query(Task).filter(Task.id == task.id).update({"score": task.score})
        
        session.commit()
        
        # Refresh sequentially
        for task in tasks:  # ❌ Sequential
            session.refresh(task)
        
        # Expunge sequentially
        for task in tasks:  # ❌ Sequential
            session.expunge(task)
        
        return tasks
```

**Problem**: 10 tasks × 0.1s per operation = **1 second**.

### Parallelized Version

**After Async Migration**:
```python
async def get_next_tasks_batch(self, phase_id: str, limit: int = 10) -> List[Task]:
    """Get multiple tasks with parallel score computation."""
    async with self.db.get_session() as session:
        result = await session.execute(
            select(Task).where(...).limit(limit)
        )
        tasks = result.scalars().all()
        
        # Compute scores in parallel (if scorer is async)
        score_tasks = [
            self.scorer.compute_score(task)
            for task in tasks
        ]
        scores = await asyncio.gather(*score_tasks)
        
        # Update all scores at once
        for task, score in zip(tasks, scores):
            task.score = score
        
        await session.commit()
        
        # Refresh all at once (if needed)
        for task in tasks:
            await session.refresh(task)
            session.expunge(task)
        
        return tasks
```

**Performance Gain**: If score computation is async and parallelizable, **2-3x faster**.

---

## 8. File I/O Operations (Low-Medium Impact)

### Current: Sequential File Reads

**Location**: `omoi_os/services/agent_output_collector.py`

**Current Pattern** (Sequential):
```python
def _get_workspace_output(self, agent_id: str, workspace_dir: str) -> str:
    """Scan workspace directory for recent activity."""
    output_files = ["output.log", "agent.log", "conversation.log", ...]
    
    for filename in output_files:  # ❌ Sequential file reads
        file_path = workspace_path / filename
        if file_path.exists():
            with open(file_path, 'r') as f:
                lines = f.readlines()[-20:]
                # Process lines
```

**Problem**: 5 files × 0.1s = **0.5 seconds**.

### Parallelized Version

**After Async Migration**:
```python
async def _get_workspace_output(self, agent_id: str, workspace_dir: str) -> str:
    """Scan workspace directory with parallel file reads."""
    output_files = ["output.log", "agent.log", "conversation.log", ...]
    
    async def read_file(file_path: Path) -> Optional[str]:
        if not file_path.exists():
            return None
        
        # Use aiofiles for async file I/O
        import aiofiles
        async with aiofiles.open(file_path, 'r') as f:
            lines = await f.readlines()
            return ''.join(lines[-20:])
    
    # Read all files in parallel
    file_tasks = [
        read_file(workspace_path / filename)
        for filename in output_files
    ]
    
    results = await asyncio.gather(*file_tasks, return_exceptions=True)
    
    # Combine results
    output_sections = [
        result for result in results 
        if result is not None and not isinstance(result, Exception)
    ]
    
    return '\n'.join(output_sections)
```

**Performance Gain**: 5 files × 0.1s = **0.5 seconds** → **~0.1 seconds**
**Speedup**: **5x faster**

---

## 9. External API Calls (High Impact)

### Current: Sequential API Calls

**Location**: `omoi_os/services/github_integration.py`

**Current Pattern** (Sequential):
```python
async def sync_multiple_repositories(self, repo_ids: List[str]):
    """Sync multiple repositories."""
    for repo_id in repo_ids:  # ❌ Sequential
        await self.sync_repository(repo_id)  # GitHub API call
```

**Problem**: 10 repos × 1s API call = **10 seconds**.

### Parallelized Version

**After Async Migration**:
```python
async def sync_multiple_repositories(
    self, 
    repo_ids: List[str],
    max_concurrent: int = 3
):
    """Sync multiple repositories in parallel."""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def sync_with_limit(repo_id: str):
        async with semaphore:
            return await self.sync_repository(repo_id)
    
    # Sync all repos in parallel
    results = await asyncio.gather(
        *[sync_with_limit(repo_id) for repo_id in repo_ids],
        return_exceptions=True
    )
    
    return results
```

**Performance Gain**: 10 repos × 1s = **10 seconds** → **~3.3 seconds** (with semaphore=3)
**Speedup**: **3x faster**

---

## 10. Dependency Graph Resolution (Medium Impact)

### Current: Sequential Dependency Checks

**Location**: `omoi_os/services/task_queue.py`

**Current Pattern** (Sequential):
```python
def get_next_task(self, phase_id: str) -> Task | None:
    """Get next task with dependency checking."""
    with self.db.get_session() as session:
        tasks = session.query(Task).filter(...).all()
        
        available_tasks = []
        for task in tasks:  # ❌ Sequential dependency checks
            if self._check_dependencies_complete(session, task):
                available_tasks.append(task)
```

**Problem**: 100 tasks × 0.05s per check = **5 seconds**.

### Parallelized Version

**After Async Migration**:
```python
async def get_next_task(self, phase_id: str) -> Task | None:
    """Get next task with parallel dependency checks."""
    async with self.db.get_session() as session:
        result = await session.execute(select(Task).where(...))
        tasks = result.scalars().all()
        
        # Check all dependencies in parallel
        dependency_checks = [
            self._check_dependencies_complete(session, task)
            for task in tasks
        ]
        
        results = await asyncio.gather(*dependency_checks)
        
        # Filter available tasks
        available_tasks = [
            task for task, is_ready in zip(tasks, results)
            if is_ready
        ]
```

**Performance Gain**: 100 tasks × 0.05s = **5 seconds** → **~0.5 seconds** (with parallel checks)
**Speedup**: **10x faster**

---

## Summary: Parallelization Opportunities

| Operation | Current Time | Parallelized Time | Speedup | Impact |
|-----------|--------------|-------------------|---------|--------|
| **Agent Trajectory Analysis** (10 agents) | 20s | 4s | **5x** | 🔴 High |
| **Emergency Analysis** (5 agents) | 10s | 2s | **5x** | 🔴 High |
| **Monitoring Cycle** (guardian + conductor) | 8s | 5s | **1.6x** | 🟡 Medium |
| **LLM API Calls** (5 agents) | 10s | 4s | **2.5x** | 🔴 High |
| **Health Checks** (20 agents) | 10s | 2s | **5x** | 🟡 Medium |
| **Batch Task Queries** (10 agents) | 1s | 0.1s | **10x** | 🟡 Medium |
| **File I/O** (5 files) | 0.5s | 0.1s | **5x** | 🟢 Low |
| **GitHub API Calls** (10 repos) | 10s | 3.3s | **3x** | 🔴 High |
| **Dependency Checks** (100 tasks) | 5s | 0.5s | **10x** | 🟡 Medium |

---

## Implementation Strategy

### Phase 1: High-Impact Operations (Week 1)
1. ✅ Parallelize agent trajectory analysis
2. ✅ Parallelize emergency analysis
3. ✅ Parallelize LLM API calls

### Phase 2: Medium-Impact Operations (Week 2)
4. ✅ Parallelize monitoring cycle operations
5. ✅ Parallelize health checks
6. ✅ Parallelize batch database queries

### Phase 3: Low-Impact Operations (Week 3)
7. ✅ Parallelize file I/O
8. ✅ Parallelize dependency checks
9. ✅ Optimize with semaphores and limits

---

## Key Patterns to Use

### 1. `asyncio.gather()` for Independent Operations
```python
# Run multiple independent operations in parallel
results = await asyncio.gather(
    operation1(),
    operation2(),
    operation3(),
    return_exceptions=True  # Don't fail if one fails
)
```

### 2. Semaphore for Rate Limiting
```python
# Limit concurrent operations (e.g., API calls)
semaphore = asyncio.Semaphore(max_concurrent)

async def operation_with_limit():
    async with semaphore:
        return await expensive_operation()
```

### 3. Parallel Loops
```python
# Process list items in parallel
results = await asyncio.gather(
    *[process_item(item) for item in items],
    return_exceptions=True
)
```

---

## Expected Overall Performance Improvement

**Before Async Migration**:
- Monitoring cycle: ~30 seconds
- Agent analysis (10 agents): ~20 seconds
- Health checks (20 agents): ~10 seconds

**After Async Migration + Parallelization**:
- Monitoring cycle: ~15 seconds (**2x faster**)
- Agent analysis (10 agents): ~4 seconds (**5x faster**)
- Health checks (20 agents): ~2 seconds (**5x faster**)

**Overall System Performance**: **3-5x improvement** in I/O-bound operations.

---

## Conclusion

After async migration, **significant parallelization opportunities** exist:

1. **Agent operations** can run in parallel (analysis, health checks)
2. **Database queries** can run concurrently
3. **LLM API calls** can be parallelized (with rate limiting)
4. **External API calls** can run concurrently
5. **File I/O** can be parallelized

The biggest wins are in:
- **Agent trajectory analysis** (5x speedup)
- **Emergency analysis** (5x speedup)
- **LLM API calls** (2.5x speedup)
- **Batch database operations** (10x speedup)

These improvements will make the system **much more responsive** and able to handle **higher loads** with the same resources.
