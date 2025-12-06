# OmoiOS Page Flow & Navigation Documentation

**Created**: 2025-01-30  
**Status**: Page Flow Documentation  
**Purpose**: Detailed page-by-page flow for registration, project selection, agent management, and spec-driven workflow

This documentation has been split into focused sections for easier navigation and maintenance.

## Document Structure

### Core Navigation
- **[00_index.md](./00_index.md)** - Navigation Summary, Main Routes, and Quick Reference
- **[01_authentication.md](./01_authentication.md)** - Flow 1: Registration & First Login
- **[10_command_center.md](./10_command_center.md)** - Flows 33-37: Command Center (Primary Landing), Unified Project/Repo Selection, Recent Agents, Analytics Dashboard, System Health Access
- **[10a_monitoring_system.md](./10a_monitoring_system.md)** - Flows 38-41: System Health Dashboard, Trajectory Analysis, Intervention Management, Monitoring Configuration

### Project & Spec Management
- **[02_projects_specs.md](./02_projects_specs.md)** - Flows 2-3: Project Selection & Creation, Spec-Driven Workflow

### Agent & Workspace Management
- **[03_agents_workspaces.md](./03_agents_workspaces.md)** - Flows 4, 7: Agent Management & Spawning, Workspace Management & Isolation

### Ticket & Board Management
- **[04_kanban_tickets.md](./04_kanban_tickets.md)** - Flows 5, 17-21: Kanban Board, Ticket Management, Search, Creation, Status Transitions, Blocking, Board Configuration

### Organization & API
- **[05_organizations_api.md](./05_organizations_api.md)** - Flows 6, 8: Organization Management & Multi-Tenancy, API Key Management

### Visualization & Monitoring
- **[06_visualizations.md](./06_visualizations.md)** - Flows 9-12: Dependency Graph View, Spec Workspace Views, Statistics Dashboard, Activity Timeline View
- **[10a_monitoring_system.md](./10a_monitoring_system.md)** - Flows 38-41: Guardian & Monitoring System (System Health, Trajectories, Interventions, Configuration)

### Phase Management
- **[07_phases.md](./07_phases.md)** - Flows 13-15, 26-32: Phase Management & Configuration, Task Phase Management, Phase Gate Approval, Phase Overview Dashboard, Phase Configuration, Custom Phase Creation, Phase Metrics

### Collaboration & Integration
- **[08a_comments_collaboration.md](./08a_comments_collaboration.md)** - Flow 16: Comments & Collaboration
- **[08b_ticket_operations.md](./08b_ticket_operations.md)** - Flows 17-21: Ticket Search, Creation, Status Transitions, Blocking, Board Configuration
- **[08c_github_integration.md](./08c_github_integration.md)** - Flows 22-23: GitHub OAuth Authorization & Integration, GitHub Repository Connection

### Diagnostic & Reasoning
- **[09a_diagnostic_reasoning.md](./09a_diagnostic_reasoning.md)** - Flow 25: Diagnostic Reasoning View
- **[09b_phase_overview_graph.md](./09b_phase_overview_graph.md)** - Flows 26-27: Phase Overview Dashboard, Workflow Graph with Phasor Discoveries
- **[09c_phase_configuration.md](./09c_phase_configuration.md)** - Flows 28-32: Phase Configuration, Custom Phase Creation, Phase Gate Approval, Task Phase Management, Phase Metrics

## Quick Navigation

**Getting Started:**
1. [01_authentication.md](./01_authentication.md) - Registration and login flows
2. [10_command_center.md](./10_command_center.md) - Command Center (primary landing page)
3. [02_projects_specs.md](./02_projects_specs.md) - Creating projects and specs

**Core Workflows:**
- [10_command_center.md](./10_command_center.md) - Quick task creation with GitHub repo selection
- [03_agents_workspaces.md](./03_agents_workspaces.md) - Managing agents and workspaces
- [04_kanban_tickets.md](./04_kanban_tickets.md) - Kanban board and ticket management
- [07_phases.md](./07_phases.md) - Phase system and configuration

**Monitoring & Analysis:**
- [06_visualizations.md](./06_visualizations.md) - Graphs, statistics, and activity timelines
- [10_command_center.md](./10_command_center.md) - Analytics Dashboard (secondary page)
- [10a_monitoring_system.md](./10a_monitoring_system.md) - Guardian & System Health monitoring
- [09a_diagnostic_reasoning.md](./09a_diagnostic_reasoning.md) - Understanding why decisions were made

**Administration:**
- [05_organizations_api.md](./05_organizations_api.md) - Organization and API management
- [08a_comments_collaboration.md](./08a_comments_collaboration.md) - Collaboration features
- [08c_github_integration.md](./08c_github_integration.md) - GitHub integration

## Flow Reference

| Flow # | Topic | Document |
|--------|-------|----------|
| 1 | Registration & First Login | [01_authentication.md](./01_authentication.md) |
| 2 | Project Selection & Creation | [02_projects_specs.md](./02_projects_specs.md) |
| 3 | Spec-Driven Workflow | [02_projects_specs.md](./02_projects_specs.md) |
| 4 | Agent Management & Spawning | [03_agents_workspaces.md](./03_agents_workspaces.md) |
| 5 | Kanban Board & Ticket Management | [04_kanban_tickets.md](./04_kanban_tickets.md) |
| 6 | Organization Management | [05_organizations_api.md](./05_organizations_api.md) |
| 7 | Workspace Management | [03_agents_workspaces.md](./03_agents_workspaces.md) |
| 8 | API Key Management | [05_organizations_api.md](./05_organizations_api.md) |
| 9 | Dependency Graph View | [06_visualizations.md](./06_visualizations.md) |
| 10 | Spec Workspace Views | [06_visualizations.md](./06_visualizations.md) |
| 11 | Statistics Dashboard | [06_visualizations.md](./06_visualizations.md) |
| 12 | Activity Timeline View | [06_visualizations.md](./06_visualizations.md) |
| 13-15 | Phase Management | [07_phases.md](./07_phases.md) |
| 16 | Comments & Collaboration | [08a_comments_collaboration.md](./08a_comments_collaboration.md) |
| 17-21 | Ticket Operations | [08b_ticket_operations.md](./08b_ticket_operations.md) |
| 22-23 | GitHub Integration | [08c_github_integration.md](./08c_github_integration.md) |
| 25 | Diagnostic Reasoning | [09a_diagnostic_reasoning.md](./09a_diagnostic_reasoning.md) |
| 26-27 | Phase Overview & Graph | [09b_phase_overview_graph.md](./09b_phase_overview_graph.md) |
| 28-32 | Phase Configuration | [09c_phase_configuration.md](./09c_phase_configuration.md) |
| 33 | Command Center (Primary Landing) | [10_command_center.md](./10_command_center.md) |
| 34 | Unified Project/Repo Selection | [10_command_center.md](./10_command_center.md) |
| 35 | Recent Agents Sidebar | [10_command_center.md](./10_command_center.md) |
| 36 | Analytics Dashboard (Secondary) | [10_command_center.md](./10_command_center.md) |
| 37 | System Health Access | [10_command_center.md](./10_command_center.md) |
| 38 | System Health Dashboard | [10a_monitoring_system.md](./10a_monitoring_system.md) |
| 39 | Trajectory Analysis View | [10a_monitoring_system.md](./10a_monitoring_system.md) |
| 40 | Intervention Management | [10a_monitoring_system.md](./10a_monitoring_system.md) |
| 41 | Monitoring Configuration | [10a_monitoring_system.md](./10a_monitoring_system.md) |

## Related Documentation

- [User Journey Documentation](../user_journey/README.md) - Complete user journey from onboarding to completion
- [Page Architecture](../page_architecture.md) - Complete page architecture specifications
- [Design System](../design_system.md) - UI/UX design system guide
- [App Overview](../app_overview.md) - High-level application overview

