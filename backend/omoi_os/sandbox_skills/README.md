# Sandbox Agent Skills

This directory contains Claude skills that are uploaded to Daytona sandboxes for agent use.

## How It Works

1. **At sandbox creation**: The `DaytonaSpawnerService` uploads these skills to `~/.claude/skills/` in the sandbox
2. **At agent startup**: Claude SDK loads skills from `setting_sources=["user", "project"]`
3. **During execution**: Agent can invoke skills via the `Skill` tool

## Directory Structure

```
sandbox_skills/
├── README.md                    # This file
├── manifest.yaml                # Skill manifest with metadata
├── spec-driven-dev/             # Spec-driven development workflow
│   └── SKILL.md
├── code-review/                 # Code review patterns
│   └── SKILL.md
├── test-writer/                 # Test generation
│   └── SKILL.md
├── pr-creator/                  # Pull request creation
│   └── SKILL.md
├── git-workflow/                # Git branching and commits
│   └── SKILL.md
├── error-diagnosis/             # Error debugging and diagnosis
│   └── SKILL.md
└── refactor-planner/            # Safe refactoring planning
    └── SKILL.md
```

## Adding New Skills

1. Create a directory with the skill name (kebab-case)
2. Add a `SKILL.md` file with the skill content
3. Update `manifest.yaml` with the skill metadata
4. The spawner will automatically include it in new sandboxes

## Skill Format

Skills follow the Claude Code skill format:

```markdown
---
description: Short description for skill discovery
globs: ["**/*.py"]  # Optional file patterns
---

# Skill Title

Detailed instructions for the agent when this skill is invoked.
```

## Manifest Format

```yaml
version: "1.0"
skills:
  - name: skill-name
    description: What the skill does
    category: development|testing|workflow|documentation
    priority: high|medium|low
```
