# Sandbox Agents System

Documentation for running AI agents in isolated sandbox environments (Daytona) with full Git integration.

## Documents

| # | Document | Description |
|---|----------|-------------|
| 01 | [Architecture](./01_architecture.md) | System design for real-time agent communication, control, and sandbox introspection |
| 02 | [Gap Analysis](./02_gap_analysis.md) | What we have vs. what we need analysis |
| 03 | [Git Branch Workflow](./03_git_branch_workflow.md) | Branch management, PR workflow, and AI conflict resolution (codename: Musubi) |

## Reading Order

1. **Architecture** - Understand the overall system design
2. **Gap Analysis** - See what's already built vs. what needs work
3. **Git Workflow** - Deep dive into branch/merge automation

## Key Concepts

- **Daytona**: Cloud sandbox technology for isolated agent execution
- **BranchWorkflowService**: Manages ticket → branch → PR → merge lifecycle
- **AI Branch Naming**: Generates descriptive branch names from ticket content
- **Conflict Resolution**: AI-powered merge conflict resolution
