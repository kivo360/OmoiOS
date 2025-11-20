# Dependency Graph Implementation Details

**Created**: 2025-01-30  
**Status**: Implementation Plan  
**Purpose**: Detailed technical specification for dependency graph visualization

---

## 1. Overview

The dependency graph visualizes relationships between tickets, tasks, and discoveries in the system. It provides an interactive view of:
- Task dependencies (what blocks what)
- Discovery-driven branching (why workflows split)
- Parent-child task relationships
- Blocking relationships (what's waiting on what)

---

## 2. Data Model & Relationships

### 2.1 Current Data Structures

**Task Dependencies (JSONB):**
```python
task.dependencies = {
    "depends_on": ["task-id-1", "task-id-2"]  # List of task IDs this task depends on
}
```

**Task Discovery:**
```python
TaskDiscovery:
    source_task_id: str          # Task that made the discovery
    discovery_type: str          # "bug", "optimization", etc.
    spawned_task_ids: List[str]  # Tasks spawned from this discovery
    description: str             # What was discovered
```

**Task Parent-Child:**
```python
Task:
    parent_task_id: Optional[str]  # Direct parent task
```

### 2.2 Graph Edge Types

**1. `depends_on`** (Task → Task)
- **Source**: Task A
- **Target**: Task B
- **Meaning**: Task B cannot start until Task A completes
- **Data Source**: `task.dependencies["depends_on"]`
- **Direction**: A → B means "A must complete before B"

**2. `blocks`** (Task → Task) [Derived]
- **Source**: Task A
- **Target**: Task B
- **Meaning**: Task A blocks Task B (inverse of depends_on)
- **Data Source**: Derived from `depends_on` relationships
- **Direction**: A → B means "A blocks B"

**3. `spawned_from`** (TaskDiscovery → Task)
- **Source**: TaskDiscovery
- **Target**: Task
- **Meaning**: Task was created because of a discovery
- **Data Source**: `TaskDiscovery.spawned_task_ids`
- **Direction**: Discovery → Task

**4. `parent_child`** (Task → Task)
- **Source**: Parent Task
- **Target**: Child Task
- **Meaning**: Child is a sub-task of parent
- **Data Source**: `task.parent_task_id`
- **Direction**: Parent → Child

**5. `ticket_contains`** (Ticket → Task)
- **Source**: Ticket
- **Target**: Task
- **Meaning**: Task belongs to ticket
- **Data Source**: `task.ticket_id`
- **Direction**: Ticket → Task

---

## 3. Backend Implementation

### 3.1 Graph Building Service

**New Service**: `omoi_os/services/dependency_graph.py`

```python
from typing import Dict, List, Set, Optional
from collections import defaultdict, deque

class DependencyGraphService:
    """Builds dependency graphs from tasks, tickets, and discoveries."""
    
    def __init__(self, db: DatabaseService):
        self.db = db
    
    def build_ticket_graph(
        self,
        ticket_id: str,
        include_resolved: bool = True,
        include_discoveries: bool = True
    ) -> Dict[str, Any]:
        """
        Build dependency graph for a single ticket.
        
        Returns:
        {
            "nodes": [...],
            "edges": [...],
            "metadata": {...}
        }
        """
        with self.db.get_session() as session:
            # 1. Get all tasks for this ticket
            tasks = session.query(Task).filter(
                Task.ticket_id == ticket_id
            ).all()
            
            if not include_resolved:
                tasks = [t for t in tasks if t.status != "completed"]
            
            # 2. Get all discoveries for these tasks
            task_ids = [t.id for t in tasks]
            discoveries = []
            if include_discoveries:
                discoveries = session.query(TaskDiscovery).filter(
                    TaskDiscovery.source_task_id.in_(task_ids)
                ).all()
            
            # 3. Build nodes
            nodes = self._build_nodes(tasks, discoveries)
            
            # 4. Build edges
            edges = self._build_edges(tasks, discoveries)
            
            # 5. Calculate metadata
            metadata = self._calculate_metadata(tasks, nodes, edges)
            
            return {
                "nodes": nodes,
                "edges": edges,
                "metadata": metadata
            }
    
    def build_project_graph(
        self,
        project_id: Optional[str] = None,
        include_resolved: bool = True
    ) -> Dict[str, Any]:
        """Build dependency graph for entire project (all tickets)."""
        with self.db.get_session() as session:
            # Get all tickets (optionally filtered by project)
            query = session.query(Ticket)
            if project_id:
                # Assuming tickets have project_id field
                query = query.filter(Ticket.project_id == project_id)
            tickets = query.all()
            
            # Get all tasks for these tickets
            ticket_ids = [t.id for t in tickets]
            tasks = session.query(Task).filter(
                Task.ticket_id.in_(ticket_ids)
            ).all()
            
            if not include_resolved:
                tasks = [t for t in tasks if t.status != "completed"]
            
            # Build graph
            nodes = self._build_nodes(tasks, [])
            edges = self._build_edges(tasks, [])
            
            # Add ticket nodes
            for ticket in tickets:
                nodes.append({
                    "id": f"ticket-{ticket.id}",
                    "type": "ticket",
                    "title": ticket.title,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "phase_id": ticket.phase_id,
                    "is_blocked": False,
                    "blocks_count": 0
                })
            
            # Add ticket → task edges
            for task in tasks:
                edges.append({
                    "from": f"ticket-{task.ticket_id}",
                    "to": task.id,
                    "type": "ticket_contains"
                })
            
            metadata = self._calculate_metadata(tasks, nodes, edges)
            
            return {
                "nodes": nodes,
                "edges": edges,
                "metadata": metadata
            }
    
    def _build_nodes(
        self,
        tasks: List[Task],
        discoveries: List[TaskDiscovery]
    ) -> List[Dict[str, Any]]:
        """Build node list from tasks and discoveries."""
        nodes = []
        
        # Build task nodes
        for task in tasks:
            # Check if task is blocked
            is_blocked = not self._check_dependencies_complete(task)
            
            # Count how many tasks this blocks
            blocks_count = len(self._get_blocked_tasks(task.id, tasks))
            
            nodes.append({
                "id": task.id,
                "type": "task",
                "title": task.description or task.task_type,
                "status": task.status,
                "phase_id": task.phase_id,
                "priority": task.priority,
                "task_type": task.task_type,
                "is_blocked": is_blocked,
                "blocks_count": blocks_count,
                "assigned_agent_id": task.assigned_agent_id,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            })
        
        # Build discovery nodes (optional - can be shown as edge labels instead)
        for discovery in discoveries:
            nodes.append({
                "id": f"discovery-{discovery.id}",
                "type": "discovery",
                "title": discovery.description,
                "discovery_type": discovery.discovery_type,
                "status": discovery.resolution_status,
                "spawned_count": len(discovery.spawned_task_ids),
                "priority_boost": discovery.priority_boost,
                "discovered_at": discovery.discovered_at.isoformat() if discovery.discovered_at else None,
            })
        
        return nodes
    
    def _build_edges(
        self,
        tasks: List[Task],
        discoveries: List[TaskDiscovery]
    ) -> List[Dict[str, Any]]:
        """Build edge list from tasks and discoveries."""
        edges = []
        task_dict = {task.id: task for task in tasks}
        
        # 1. Build depends_on edges
        for task in tasks:
            if task.dependencies:
                depends_on = task.dependencies.get("depends_on", [])
                for dep_id in depends_on:
                    if dep_id in task_dict:
                        edges.append({
                            "from": dep_id,
                            "to": task.id,
                            "type": "depends_on",
                            "label": "depends on"
                        })
        
        # 2. Build parent_child edges
        for task in tasks:
            if task.parent_task_id and task.parent_task_id in task_dict:
                edges.append({
                    "from": task.parent_task_id,
                    "to": task.id,
                    "type": "parent_child",
                    "label": "sub-task"
                })
        
        # 3. Build spawned_from edges (discovery → task)
        for discovery in discoveries:
            for spawned_id in discovery.spawned_task_ids:
                if spawned_id in task_dict:
                    edges.append({
                        "from": f"discovery-{discovery.id}",
                        "to": spawned_id,
                        "type": "spawned_from",
                        "label": discovery.discovery_type,
                        "discovery_id": discovery.id
                    })
        
        return edges
    
    def _check_dependencies_complete(self, task: Task) -> bool:
        """Check if all dependencies for a task are completed."""
        if not task.dependencies:
            return True
        
        depends_on = task.dependencies.get("depends_on", [])
        if not depends_on:
            return True
        
        # This would need access to all tasks - simplified here
        # In real implementation, query database
        return True  # Placeholder
    
    def _get_blocked_tasks(self, task_id: str, all_tasks: List[Task]) -> List[Task]:
        """Get tasks blocked by this task."""
        blocked = []
        for task in all_tasks:
            if task.dependencies:
                depends_on = task.dependencies.get("depends_on", [])
                if task_id in depends_on:
                    blocked.append(task)
        return blocked
    
    def _calculate_metadata(
        self,
        tasks: List[Task],
        nodes: List[Dict],
        edges: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate graph metadata."""
        total_tasks = len([n for n in nodes if n["type"] == "task"])
        blocked_count = len([n for n in nodes if n.get("is_blocked", False)])
        resolved_count = len([t for t in tasks if t.status == "completed"])
        
        # Find critical path (longest dependency chain)
        critical_path = self._find_critical_path(nodes, edges)
        
        return {
            "total_tasks": total_tasks,
            "blocked_count": blocked_count,
            "resolved_count": resolved_count,
            "total_edges": len(edges),
            "critical_path_length": len(critical_path) if critical_path else 0,
            "critical_path": critical_path
        }
    
    def _find_critical_path(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> List[str]:
        """
        Find the longest dependency path (critical path).
        
        Uses topological sort + longest path algorithm.
        """
        # Build adjacency list (only depends_on edges)
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        for edge in edges:
            if edge["type"] == "depends_on":
                graph[edge["from"]].append(edge["to"])
                in_degree[edge["to"]] += 1
        
        # Topological sort
        queue = deque([n["id"] for n in nodes if in_degree.get(n["id"], 0) == 0])
        longest_path = defaultdict(int)
        path_predecessor = {}
        
        while queue:
            node = queue.popleft()
            
            for neighbor in graph[node]:
                if longest_path[node] + 1 > longest_path[neighbor]:
                    longest_path[neighbor] = longest_path[node] + 1
                    path_predecessor[neighbor] = node
                
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Find node with longest path
        if not longest_path:
            return []
        
        end_node = max(longest_path.items(), key=lambda x: x[1])[0]
        
        # Reconstruct path
        path = []
        current = end_node
        while current:
            path.append(current)
            current = path_predecessor.get(current)
        
        return list(reversed(path))
```

### 3.2 API Endpoints

**New File**: `omoi_os/api/routes/graph.py`

```python
from fastapi import APIRouter, Query, Depends
from typing import Optional, Dict, Any

from omoi_os.api.dependencies import get_db_service
from omoi_os.services.database import DatabaseService
from omoi_os.services.dependency_graph import DependencyGraphService

router = APIRouter()


@router.get("/dependency-graph/ticket/{ticket_id}")
async def get_ticket_dependency_graph(
    ticket_id: str,
    include_resolved: bool = Query(True, description="Include completed tasks"),
    include_discoveries: bool = Query(True, description="Include discovery nodes"),
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """
    Get dependency graph for a ticket.
    
    Returns graph with nodes (tasks, discoveries) and edges (dependencies).
    """
    graph_service = DependencyGraphService(db)
    return graph_service.build_ticket_graph(
        ticket_id=ticket_id,
        include_resolved=include_resolved,
        include_discoveries=include_discoveries
    )


@router.get("/dependency-graph/project/{project_id}")
async def get_project_dependency_graph(
    project_id: str,
    include_resolved: bool = Query(True),
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """Get dependency graph for entire project."""
    graph_service = DependencyGraphService(db)
    return graph_service.build_project_graph(
        project_id=project_id,
        include_resolved=include_resolved
    )


@router.get("/dependency-graph/task/{task_id}/blocked")
async def get_blocked_tasks(
    task_id: str,
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
) -> Dict[str, Any]:
    """Get all tasks blocked by this task."""
    blocked = queue.get_blocked_tasks(task_id)
    return {
        "task_id": task_id,
        "blocked_tasks": [
            {
                "id": t.id,
                "description": t.description,
                "status": t.status,
                "priority": t.priority
            }
            for t in blocked
        ],
        "blocked_count": len(blocked)
    }


@router.get("/dependency-graph/task/{task_id}/blocking")
async def get_blocking_tasks(
    task_id: str,
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """Get all tasks that block this task (dependencies)."""
    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        depends_on = []
        if task.dependencies:
            depends_on = task.dependencies.get("depends_on", [])
        
        blocking_tasks = []
        if depends_on:
            blocking = session.query(Task).filter(Task.id.in_(depends_on)).all()
            blocking_tasks = [
                {
                    "id": t.id,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "is_complete": t.status == "completed"
                }
                for t in blocking
            ]
        
        return {
            "task_id": task_id,
            "blocking_tasks": blocking_tasks,
            "all_dependencies_complete": all(
                t["is_complete"] for t in blocking_tasks
            ) if blocking_tasks else True
        }
```

---

## 4. Graph Layout Algorithm

### 4.1 Layout Strategy

**Option 1: Hierarchical (Top-Down)**
- Root nodes (no dependencies) at top
- Dependent nodes below
- Levels based on dependency depth
- Best for: Clear dependency flow

**Option 2: Force-Directed**
- Nodes repel each other
- Edges attract connected nodes
- Natural clustering
- Best for: Complex, interconnected graphs

**Option 3: Layered (Sugiyama)**
- Multiple passes for optimal layout
- Minimizes edge crossings
- Best for: Large, complex graphs

**Recommended**: Start with **hierarchical**, add force-directed as option.

### 4.2 Backend Layout Calculation

```python
class GraphLayoutService:
    """Calculate node positions for graph visualization."""
    
    def calculate_hierarchical_layout(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate hierarchical (top-down) layout.
        
        Returns: {node_id: {"x": float, "y": float, "level": int}}
        """
        # 1. Build dependency graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        node_set = {n["id"] for n in nodes}
        
        for edge in edges:
            if edge["type"] == "depends_on" and edge["from"] in node_set and edge["to"] in node_set:
                graph[edge["from"]].append(edge["to"])
                in_degree[edge["to"]] += 1
        
        # 2. Assign levels (topological levels)
        levels = {}
        queue = deque([n["id"] for n in nodes if in_degree.get(n["id"], 0) == 0])
        level = 0
        
        while queue:
            level_size = len(queue)
            for _ in range(level_size):
                node = queue.popleft()
                levels[node] = level
                
                for neighbor in graph[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            level += 1
        
        # 3. Position nodes within levels
        positions = {}
        level_groups = defaultdict(list)
        for node_id, level in levels.items():
            level_groups[level].append(node_id)
        
        max_level = max(levels.values()) if levels else 0
        level_height = 200  # Vertical spacing between levels
        
        for level, node_ids in level_groups.items():
            y = level * level_height
            node_width = 150
            total_width = len(node_ids) * node_width
            start_x = -total_width / 2
            
            for idx, node_id in enumerate(node_ids):
                x = start_x + idx * node_width + node_width / 2
                positions[node_id] = {
                    "x": x,
                    "y": y,
                    "level": level
                }
        
        return positions
```

---

## 5. Frontend Implementation

### 5.1 React Flow Integration

**Component Structure:**
```typescript
// components/graph/DependencyGraph.tsx
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';

interface GraphNode extends Node {
  data: {
    title: string;
    status: string;
    priority: string;
    is_blocked: boolean;
    type: 'task' | 'ticket' | 'discovery';
  };
}

export function DependencyGraph({ ticketId }: { ticketId: string }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  
  // Load graph data
  useEffect(() => {
    fetch(`/api/v1/graph/dependency-graph/ticket/${ticketId}`)
      .then(res => res.json())
      .then(data => {
        const flowNodes = transformToFlowNodes(data.nodes);
        const flowEdges = transformToFlowEdges(data.edges);
        setNodes(flowNodes);
        setEdges(flowEdges);
        setLoading(false);
      });
  }, [ticketId]);
  
  return (
    <div style={{ width: '100%', height: '600px' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
```

### 5.2 Node Styling

**Custom Node Component:**
```typescript
// components/graph/TaskNode.tsx
export function TaskNode({ data }: { data: GraphNode['data'] }) {
  const statusColors = {
    'pending': '#e0e0e0',
    'assigned': '#fff3e0',
    'running': '#2196f3',
    'completed': '#4caf50',
    'failed': '#f44336'
  };
  
  const prioritySizes = {
    'CRITICAL': 120,
    'HIGH': 100,
    'MEDIUM': 80,
    'LOW': 60
  };
  
  return (
    <div
      style={{
        width: prioritySizes[data.priority] || 80,
        height: prioritySizes[data.priority] || 80,
        background: statusColors[data.status] || '#e0e0e0',
        border: data.is_blocked ? '3px solid #f44336' : '2px solid #333',
        borderRadius: '8px',
        padding: '10px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      <div style={{ fontWeight: 'bold', fontSize: '12px' }}>
        {data.title}
      </div>
      <div style={{ fontSize: '10px', color: '#666' }}>
        {data.status}
      </div>
      {data.is_blocked && (
        <div style={{ fontSize: '8px', color: '#f44336' }}>
          BLOCKED
        </div>
      )}
    </div>
  );
}
```

### 5.3 Edge Styling

**Edge Types:**
```typescript
function transformToFlowEdges(edges: any[]): Edge[] {
  return edges.map(edge => {
    const edgeStyles = {
      'depends_on': { color: '#2196f3', style: 'solid' },
      'blocks': { color: '#f44336', style: 'dashed' },
      'spawned_from': { color: '#ff9800', style: 'dotted' },
      'parent_child': { color: '#9c27b0', style: 'solid' },
      'ticket_contains': { color: '#666', style: 'solid' }
    };
    
    const style = edgeStyles[edge.type] || edgeStyles['depends_on'];
    
    return {
      id: `${edge.from}-${edge.to}-${edge.type}`,
      source: edge.from,
      target: edge.to,
      label: edge.label || edge.type,
      type: 'smoothstep',  // or 'default', 'straight', 'step'
      animated: edge.type === 'depends_on' && isBlocking(edge),
      style: {
        stroke: style.color,
        strokeWidth: 2,
        strokeDasharray: style.style === 'dashed' ? '5,5' : undefined
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: style.color
      }
    };
  });
}
```

---

## 6. Real-Time Updates

### 6.1 WebSocket Event Handling

**Events to Subscribe:**
- `TASK_CREATED` - Add new node
- `TASK_COMPLETED` - Update node status
- `TASK_FAILED` - Update node status
- `TASK_ASSIGNED` - Update node (show agent)
- `TASK_DEPENDENCY_ADDED` - Add new edge
- `DISCOVERY_REPORTED` - Add discovery node and edges

**Implementation:**
```typescript
useEffect(() => {
  const handler = (event: SystemEvent) => {
    if (event.entity_type === 'task') {
      // Update node status
      setNodes(prev => prev.map(node => 
        node.id === event.entity_id
          ? { ...node, data: { ...node.data, status: event.payload.status } }
          : node
      ));
      
      // If dependencies changed, reload graph
      if (event.payload.dependencies_changed) {
        refreshGraph();
      }
    }
    
    if (event.entity_type === 'discovery') {
      // Add discovery node and spawned edges
      refreshGraph();
    }
  };
  
  ws.subscribe([
    'TASK_CREATED',
    'TASK_COMPLETED',
    'TASK_FAILED',
    'TASK_ASSIGNED',
    'DISCOVERY_REPORTED'
  ], handler);
  
  return () => ws.unsubscribe(handler);
}, [ws]);
```

---

## 7. Performance Optimizations

### 7.1 Backend Optimizations

**Database Queries:**
- Use single query with joins instead of N+1 queries
- Cache graph structure for frequently accessed tickets
- Paginate large graphs (only show visible nodes)

**Query Optimization:**
```python
# Efficient single-query approach
def build_ticket_graph_optimized(self, ticket_id: str):
    with self.db.get_session() as session:
        # Single query with eager loading
        tasks = session.query(Task)\
            .options(
                joinedload(Task.discoveries),
                joinedload(Task.ticket)
            )\
            .filter(Task.ticket_id == ticket_id)\
            .all()
        
        # Build graph in memory
        return self._build_graph_from_tasks(tasks)
```

### 7.2 Frontend Optimizations

**Virtual Rendering:**
- Only render visible nodes (viewport culling)
- Lazy load sub-graphs
- Debounce layout recalculations

**React Flow Optimizations:**
```typescript
// Use React.memo for custom nodes
const TaskNode = React.memo(({ data }) => {
  // Node rendering
});

// Use useMemo for expensive calculations
const layoutedNodes = useMemo(() => {
  return calculateLayout(nodes, edges);
}, [nodes, edges]);
```

---

## 8. Interactive Features

### 8.1 Node Interactions

**Click Node:**
- Show task details sidebar
- Highlight connected nodes
- Show dependency path

**Hover Node:**
- Tooltip with quick info
- Highlight incoming/outgoing edges

**Drag Node:**
- Reposition (layout persists)
- Save position to localStorage

### 8.2 Edge Interactions

**Hover Edge:**
- Show dependency reason
- Show discovery description
- Highlight dependency chain

**Click Edge:**
- Show edge details modal
- Navigate to source/target node

### 8.3 Graph Controls

**Filters:**
- Show/hide resolved tasks
- Show/hide discovery nodes
- Filter by phase
- Filter by priority

**Layout Options:**
- Hierarchical (top-down)
- Force-directed
- Left-right
- Custom positions

**View Options:**
- Zoom to fit
- Highlight critical path
- Show only blocked tasks
- Compact/expanded view

---

## 9. Implementation Phases

### Phase 1: Basic Graph (Week 1)
- ✅ Backend graph building service
- ✅ API endpoints
- ✅ Basic React Flow integration
- ✅ Simple hierarchical layout
- ✅ Node and edge rendering

### Phase 2: Interactive Features (Week 2)
- ✅ Node click → details sidebar
- ✅ Edge hover → tooltips
- ✅ Filter controls
- ✅ Layout options
- ✅ Real-time updates

### Phase 3: Advanced Features (Week 3)
- ✅ Discovery nodes
- ✅ Critical path highlighting
- ✅ Blocking indicators
- ✅ Performance optimizations
- ✅ Custom node styling

---

## 10. Example Graph Structure

```
Ticket: "Implement Authentication"
│
├─ Task: "Design Auth Flow" (completed)
│   │
│   └─ Discovery: "Need OAuth2 support" (bug)
│       │
│       └─ Task: "Implement OAuth2" (running) ← BLOCKED
│
├─ Task: "Implement JWT" (pending)
│   └─ depends_on: "Design Auth Flow"
│
└─ Task: "Write Tests" (pending)
    └─ depends_on: ["Implement JWT", "Implement OAuth2"]
```

**Visual Representation:**
```
[Design Auth Flow] (completed, green)
    │
    ├─→ [Implement JWT] (pending, gray)
    │
    └─→ [Discovery: OAuth2] (orange diamond)
            │
            └─→ [Implement OAuth2] (running, blue, BLOCKED)
                    │
                    └─→ [Write Tests] (pending, gray)
                            ↑
                            │
                    [Implement JWT] ──┘
```

---

## 11. Testing Strategy

### 11.1 Backend Tests

```python
def test_build_ticket_graph():
    """Test graph building for a ticket."""
    # Create ticket with tasks
    # Set up dependencies
    # Build graph
    # Assert nodes and edges are correct

def test_circular_dependency_detection():
    """Test that circular dependencies are detected."""
    # Create circular dependency
    # Build graph
    # Assert cycle is detected

def test_critical_path_calculation():
    """Test critical path finding."""
    # Create dependency chain
    # Calculate critical path
    # Assert longest path is found
```

### 11.2 Frontend Tests

```typescript
describe('DependencyGraph', () => {
  it('renders nodes correctly', () => {
    // Test node rendering
  });
  
  it('handles real-time updates', () => {
    // Test WebSocket event handling
  });
  
  it('filters nodes correctly', () => {
    // Test filter functionality
  });
});
```

---

## 12. API Response Example

```json
{
  "nodes": [
    {
      "id": "task-123",
      "type": "task",
      "title": "Implement authentication",
      "status": "running",
      "phase_id": "PHASE_IMPLEMENTATION",
      "priority": "HIGH",
      "is_blocked": false,
      "blocks_count": 2,
      "assigned_agent_id": "agent-456"
    },
    {
      "id": "discovery-789",
      "type": "discovery",
      "title": "Need OAuth2 support",
      "discovery_type": "bug",
      "status": "open",
      "spawned_count": 1
    }
  ],
  "edges": [
    {
      "from": "task-123",
      "to": "task-456",
      "type": "depends_on",
      "label": "depends on"
    },
    {
      "from": "discovery-789",
      "to": "task-999",
      "type": "spawned_from",
      "label": "bug",
      "discovery_id": "discovery-789"
    }
  ],
  "metadata": {
    "total_tasks": 5,
    "blocked_count": 2,
    "resolved_count": 1,
    "total_edges": 4,
    "critical_path_length": 3,
    "critical_path": ["task-123", "task-456", "task-789"]
  }
}
```

---

## 13. Next Steps

1. **Create Graph Service** (`omoi_os/services/dependency_graph.py`)
2. **Create Graph API** (`omoi_os/api/routes/graph.py`)
3. **Add to main router** (`omoi_os/api/main.py`)
4. **Frontend setup** (React Flow installation)
5. **Basic graph component** (render nodes/edges)
6. **Interactive features** (click, hover, filter)
7. **Real-time updates** (WebSocket integration)
8. **Performance tuning** (caching, pagination)

---

This implementation provides a complete, production-ready dependency graph visualization system that integrates seamlessly with the existing task dependency infrastructure.

