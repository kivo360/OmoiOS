# Sandbox Agents System

Documentation for running AI agents in isolated sandbox environments (Daytona) with full Git integration.

## Documents

| # | Document | Description |
|---|----------|-------------|
| 01 | [Architecture](./01_architecture.md) | System design for real-time agent communication, control, and sandbox introspection |
| 02 | [Gap Analysis](./02_gap_analysis.md) | What we have vs. what we need analysis |
| 03 | [Git Branch Workflow](./03_git_branch_workflow.md) | Branch management, PR workflow, and AI conflict resolution (codename: Musubi) |
| 04 | [Communication Patterns](./04_communication_patterns.md) | HTTP-based communication for reliability (replacing MCP for task management) |
| 05 | [HTTP API Migration](./05_http_api_migration.md) | **Complete guide**: MCP→HTTP mapping, new routes to add, SDK tool examples |

## Reading Order

1. **Architecture** - Understand the overall system design
2. **Gap Analysis** - See what's already built vs. what needs work
3. **Git Workflow** - Deep dive into branch/merge automation
4. **Communication Patterns** - Why HTTP over MCP
5. **HTTP API Migration** - ⭐ **Start here for implementation** - Complete mapping and code

## Key Concepts

- **Daytona**: Cloud sandbox technology for isolated agent execution
- **BranchWorkflowService**: Manages ticket → branch → PR → merge lifecycle
- **AI Branch Naming**: Generates descriptive branch names from ticket content
- **Conflict Resolution**: AI-powered merge conflict resolution
- **HTTP over MCP**: Use simple HTTP for task/status operations (more reliable)
- **27 MCP Tools → HTTP**: Full mapping of what exists (15) vs. needs adding (12)
