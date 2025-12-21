---
name: doc-expander
description: Expand and enrich documentation using DeepWiki (GitHub repos) and Context7 (libraries). Use when the user wants to research a library/framework, expand existing docs, generate comprehensive documentation from questions, or fill gaps in markdown files. Generates research questions, queries multiple sources, and synthesizes findings into structured documentation.
---

# Doc Expander

Research and expand documentation using DeepWiki and Context7 MCP servers.

## Workflow Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  1. Analyze     │────>│  2. Generate     │────>│  3. Research    │
│  Existing Doc   │     │  Questions       │     │  (DeepWiki/C7)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  6. Output      │<────│  5. Structure    │<────│  4. Synthesize  │
│  Final Doc      │     │  Content         │     │  Findings       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Quick Start

### Expand Existing Documentation

```
User: Expand this README with more details about the API
```

1. Read the existing document
2. Identify gaps and generate questions
3. Research using DeepWiki/Context7
4. Synthesize and append findings

### Create New Documentation

```
User: Create comprehensive docs for the fastapi library
```

1. Generate foundational questions
2. Research architecture, patterns, examples
3. Structure into logical sections
4. Output complete documentation

## Research Tools

### DeepWiki (GitHub Repositories)

Best for: Repository architecture, implementation details, source code patterns

```python
# Get documentation structure
mcp__deepwiki-mcp__read_wiki_structure(repoName="owner/repo")

# Get full documentation
mcp__deepwiki-mcp__read_wiki_contents(repoName="owner/repo")

# Ask specific questions
mcp__deepwiki-mcp__ask_question(
    repoName="owner/repo",
    question="How does the authentication system work?"
)
```

**When to use DeepWiki:**
- Open source libraries on GitHub
- Understanding implementation details
- Finding code examples from source
- Architecture decisions and patterns

### Context7 (Library Documentation)

Best for: Official docs, API references, best practices

```python
# Resolve library ID first
mcp__context7-mcp__resolve-library-id(libraryName="fastapi")

# Then fetch documentation
mcp__context7-mcp__get-library-docs(
    context7CompatibleLibraryID="/tiangolo/fastapi",
    topic="dependency injection",
    mode="code"  # or "info" for conceptual content
)
```

**When to use Context7:**
- Official library documentation
- API references and signatures
- Best practices and guides
- Version-specific features

### Choosing the Right Source

| Need | Primary Source | Secondary |
|------|---------------|-----------|
| API reference | Context7 | DeepWiki |
| Code examples | DeepWiki | Context7 |
| Architecture | DeepWiki | - |
| Best practices | Context7 | DeepWiki |
| Troubleshooting | Both | - |
| Version changes | Context7 | DeepWiki |

## Question Generation

Generate targeted questions to guide research. See [references/questions.md](references/questions.md) for templates.

### Question Categories

1. **Foundation** - What is it? Core concepts?
2. **Architecture** - How is it structured? Key components?
3. **Usage** - How to use it? Common patterns?
4. **Integration** - How to integrate? Dependencies?
5. **Advanced** - Edge cases? Performance? Security?
6. **Troubleshooting** - Common issues? Debugging?

### Example Questions for a Library

```markdown
## Foundation
- What problem does {library} solve?
- What are the core concepts?
- How does it compare to alternatives?

## Architecture
- What is the high-level architecture?
- What are the main components/modules?
- How do components interact?

## Usage
- How do I install and configure it?
- What's the basic usage pattern?
- What are common use cases?

## Integration
- What are the dependencies?
- How does it integrate with {framework}?
- Are there official plugins/extensions?

## Advanced
- How do I handle {specific scenario}?
- What are performance considerations?
- What security practices are recommended?
```

## Research Strategy

For comprehensive documentation, use this multi-pass approach:

### Pass 1: Overview (Context7 info mode)
```python
mcp__context7-mcp__get-library-docs(
    context7CompatibleLibraryID=lib_id,
    mode="info"  # Conceptual overview
)
```

### Pass 2: Code Examples (Context7 code mode)
```python
mcp__context7-mcp__get-library-docs(
    context7CompatibleLibraryID=lib_id,
    topic="specific_topic",
    mode="code"  # API and examples
)
```

### Pass 3: Implementation Details (DeepWiki)
```python
mcp__deepwiki-mcp__ask_question(
    repoName="owner/repo",
    question="How is {feature} implemented internally?"
)
```

### Pass 4: Fill Gaps
For any remaining questions, query both sources with specific topics.

## Output Patterns

### Expanding Existing Docs

When expanding, preserve existing content and add:
- Missing sections identified from questions
- Code examples from research
- Links to official resources
- Troubleshooting tips

### Creating New Docs

Structure new documentation with:

```markdown
# {Library/Topic} Documentation

## Overview
[From Context7 info mode]

## Installation
[From Context7 code mode]

## Quick Start
[Synthesized from both sources]

## Core Concepts
[From both sources]

## API Reference
[From Context7 code mode]

## Examples
[From DeepWiki + Context7]

## Advanced Topics
[From DeepWiki questions]

## Troubleshooting
[From both sources]

## Resources
- [Official Docs](url)
- [GitHub](url)
```

## Best Practices

1. **Always resolve library ID first** before using Context7
2. **Use both sources** for comprehensive coverage
3. **Start broad, then specific** - overview first, then details
4. **Preserve existing content** when expanding
5. **Cite sources** with links when possible
6. **Use pagination** in Context7 (page=1, page=2) for more content
7. **Check multiple topics** for thorough coverage

## Workflow Scripts

Use `scripts/expand_docs.py` for automated expansion:

```bash
# Expand a markdown file
python scripts/expand_docs.py docs/api.md --library fastapi

# Generate new documentation
python scripts/expand_docs.py --new --library pydantic --output docs/pydantic.md

# Generate questions only
python scripts/expand_docs.py docs/readme.md --questions-only
```
