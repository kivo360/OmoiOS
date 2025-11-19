"""Dependency graph building service for visualization."""

from typing import Dict, List, Set, Optional, Any
from collections import defaultdict, deque

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.task_discovery import TaskDiscovery
from omoi_os.services.database import DatabaseService


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
        
        Args:
            ticket_id: Ticket ID to build graph for
            include_resolved: Whether to include completed tasks
            include_discoveries: Whether to include discovery nodes
        
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
            
            if not tasks:
                return {
                    "nodes": [],
                    "edges": [],
                    "metadata": {
                        "total_tasks": 0,
                        "blocked_count": 0,
                        "resolved_count": 0,
                        "total_edges": 0,
                        "critical_path_length": 0,
                        "critical_path": []
                    }
                }
            
            # 2. Get all discoveries for these tasks
            task_ids = [t.id for t in tasks]
            discoveries = []
            if include_discoveries:
                discoveries = session.query(TaskDiscovery).filter(
                    TaskDiscovery.source_task_id.in_(task_ids)
                ).all()
            
            # 3. Build nodes
            nodes = self._build_nodes(tasks, discoveries, session)
            
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
        """
        Build dependency graph for entire project (all tickets).
        
        Args:
            project_id: Optional project ID to filter tickets
            include_resolved: Whether to include completed tasks
        
        Returns:
            Graph structure with nodes and edges
        """
        with self.db.get_session() as session:
            # Get all tickets (optionally filtered by project)
            # Note: Assuming tickets might have project_id in future
            # For now, get all tickets
            tickets = session.query(Ticket).all()
            
            # Get all tasks for these tickets
            ticket_ids = [t.id for t in tickets]
            tasks = session.query(Task).filter(
                Task.ticket_id.in_(ticket_ids)
            ).all()
            
            if not include_resolved:
                tasks = [t for t in tasks if t.status != "completed"]
            
            # Build graph
            nodes = self._build_nodes(tasks, [], session)
            edges = self._build_edges(tasks, [])
            
            # Add ticket nodes
            for ticket in tickets:
                # Count tasks for this ticket
                ticket_tasks = [t for t in tasks if t.ticket_id == ticket.id]
                nodes.append({
                    "id": f"ticket-{ticket.id}",
                    "type": "ticket",
                    "title": ticket.title or "Untitled Ticket",
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "phase_id": ticket.phase_id,
                    "is_blocked": False,
                    "blocks_count": 0,
                    "task_count": len(ticket_tasks)
                })
            
            # Add ticket → task edges
            for task in tasks:
                edges.append({
                    "from": f"ticket-{task.ticket_id}",
                    "to": task.id,
                    "type": "ticket_contains",
                    "label": "contains"
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
        discoveries: List[TaskDiscovery],
        session: Session
    ) -> List[Dict[str, Any]]:
        """Build node list from tasks and discoveries."""
        nodes = []
        task_dict = {task.id: task for task in tasks}
        
        # Build task nodes
        for task in tasks:
            # Check if task is blocked
            is_blocked = not self._check_dependencies_complete(task, task_dict, session)
            
            # Count how many tasks this blocks
            blocks_count = len(self._get_blocked_tasks(task.id, tasks))
            
            nodes.append({
                "id": task.id,
                "type": "task",
                "title": task.description or task.task_type or "Untitled Task",
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
    
    def _check_dependencies_complete(
        self,
        task: Task,
        task_dict: Dict[str, Task],
        session: Session
    ) -> bool:
        """Check if all dependencies for a task are completed."""
        if not task.dependencies:
            return True
        
        depends_on = task.dependencies.get("depends_on", [])
        if not depends_on:
            return True
        
        # Check if all dependency tasks are completed
        for dep_id in depends_on:
            if dep_id in task_dict:
                dep_task = task_dict[dep_id]
                if dep_task.status != "completed":
                    return False
            else:
                # Dependency task not in our set - query it
                dep_task = session.query(Task).filter(Task.id == dep_id).first()
                if not dep_task or dep_task.status != "completed":
                    return False
        
        return True
    
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
        node_set = {n["id"] for n in nodes if n["type"] == "task"}
        
        for edge in edges:
            if edge["type"] == "depends_on" and edge["from"] in node_set and edge["to"] in node_set:
                graph[edge["from"]].append(edge["to"])
                in_degree[edge["to"]] += 1
        
        # Initialize longest path
        longest_path = defaultdict(int)
        path_predecessor = {}
        
        # Topological sort with longest path calculation
        queue = deque([n["id"] for n in nodes if n["type"] == "task" and in_degree.get(n["id"], 0) == 0])
        
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

