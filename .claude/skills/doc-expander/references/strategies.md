# Research Strategies

Detailed strategies for using DeepWiki and Context7 effectively.

## Table of Contents

1. [Source Selection](#source-selection)
2. [DeepWiki Strategies](#deepwiki-strategies)
3. [Context7 Strategies](#context7-strategies)
4. [Combined Strategies](#combined-strategies)
5. [Troubleshooting Research](#troubleshooting-research)

---

## Source Selection

### Decision Matrix

| Research Goal | DeepWiki | Context7 | Notes |
|---------------|----------|----------|-------|
| Official API docs | ❌ | ✅ | Context7 has curated docs |
| Source code examples | ✅ | ⚠️ | DeepWiki for real implementation |
| Architecture overview | ✅ | ⚠️ | DeepWiki analyzes full repo |
| Best practices | ⚠️ | ✅ | Context7 has official guides |
| Configuration options | ✅ | ✅ | Both useful, cross-reference |
| Recent changes | ✅ | ⚠️ | DeepWiki has latest source |
| Migration guides | ⚠️ | ✅ | Official docs preferred |
| Error messages | ✅ | ⚠️ | Search source for context |

### Library Type Recommendations

**Well-documented popular libraries** (React, FastAPI, etc.):
- Start with Context7 for official docs
- Use DeepWiki for implementation details

**Less-documented libraries**:
- Start with DeepWiki to understand source
- Context7 may have limited content

**GitHub-only projects**:
- Use DeepWiki primarily
- Context7 may not have content

---

## DeepWiki Strategies

### Getting Started

Always start with the wiki structure to understand available topics:

```python
mcp__deepwiki-mcp__read_wiki_structure(repoName="owner/repo")
```

This returns available documentation topics to guide further queries.

### Question Patterns

**Architecture questions:**
```python
mcp__deepwiki-mcp__ask_question(
    repoName="owner/repo",
    question="What is the high-level architecture and how do the main components interact?"
)
```

**Implementation questions:**
```python
mcp__deepwiki-mcp__ask_question(
    repoName="owner/repo",
    question="How is {feature} implemented? Show the relevant code."
)
```

**Usage questions:**
```python
mcp__deepwiki-mcp__ask_question(
    repoName="owner/repo",
    question="How do I use {feature}? Provide examples from the codebase."
)
```

**Configuration questions:**
```python
mcp__deepwiki-mcp__ask_question(
    repoName="owner/repo",
    question="What configuration options are available and what are the defaults?"
)
```

### Effective Question Formulation

**Good questions:**
- Specific and focused
- Ask for code examples
- Reference specific features
- Ask about interactions between components

**Examples:**
```
✅ "How does the authentication middleware validate JWT tokens?"
✅ "What is the data flow when processing a webhook event?"
✅ "Show me how the caching layer is implemented."

❌ "Tell me about authentication" (too vague)
❌ "How does everything work?" (too broad)
```

### Multi-Step Research

For complex topics, break into steps:

1. **Overview first:**
   ```python
   ask_question("What are the main components of the {system}?")
   ```

2. **Then dive deeper:**
   ```python
   ask_question("How does {component_1} work internally?")
   ask_question("How does {component_1} communicate with {component_2}?")
   ```

3. **Finally, specifics:**
   ```python
   ask_question("What are the edge cases in {component_1}?")
   ```

---

## Context7 Strategies

### Library ID Resolution

Always resolve the library ID first:

```python
# This returns matching libraries with IDs
mcp__context7-mcp__resolve-library-id(libraryName="fastapi")

# Returns something like:
# /tiangolo/fastapi - Official FastAPI documentation
```

### Mode Selection

**Code mode** (`mode="code"`):
- API references
- Code examples
- Function signatures
- Configuration snippets

**Info mode** (`mode="info"`):
- Conceptual explanations
- Architecture overviews
- Best practices
- Tutorial content

### Topic-Based Queries

Focus queries with specific topics:

```python
# Broad overview
mcp__context7-mcp__get-library-docs(
    context7CompatibleLibraryID="/tiangolo/fastapi",
    mode="info"
)

# Specific topic
mcp__context7-mcp__get-library-docs(
    context7CompatibleLibraryID="/tiangolo/fastapi",
    topic="dependency injection",
    mode="code"
)
```

### Pagination for Depth

Context7 supports pagination for comprehensive coverage:

```python
# First page (default)
mcp__context7-mcp__get-library-docs(
    context7CompatibleLibraryID=lib_id,
    topic="authentication",
    page=1
)

# More content
mcp__context7-mcp__get-library-docs(
    context7CompatibleLibraryID=lib_id,
    topic="authentication",
    page=2
)
```

### Common Topics to Query

For comprehensive documentation, query these topics:

```python
topics = [
    "getting started",
    "installation",
    "configuration",
    "authentication",
    "error handling",
    "testing",
    "deployment",
    "performance",
    "security",
    "migration",
]
```

---

## Combined Strategies

### Comprehensive Library Documentation

**Phase 1: Overview (Context7)**
```python
# Get conceptual overview
get-library-docs(lib_id, mode="info")
```

**Phase 2: API Details (Context7)**
```python
# Get API reference
get-library-docs(lib_id, mode="code", topic="api reference")
```

**Phase 3: Implementation (DeepWiki)**
```python
# Understand internals
ask_question(repo, "How is the core functionality implemented?")
```

**Phase 4: Examples (Both)**
```python
# Context7 for official examples
get-library-docs(lib_id, topic="examples", mode="code")

# DeepWiki for real-world patterns
ask_question(repo, "Show me example usage patterns from the codebase")
```

### Expanding Existing Documentation

1. **Identify gaps** by analyzing current content
2. **Generate questions** for missing topics
3. **Query Context7** for official information
4. **Query DeepWiki** for implementation details
5. **Cross-reference** findings from both sources
6. **Synthesize** into cohesive documentation

### Troubleshooting Documentation

```python
# Context7 for official troubleshooting
get-library-docs(lib_id, topic="troubleshooting", mode="info")

# DeepWiki for error handling code
ask_question(repo, "What are common error conditions and how are they handled?")

# DeepWiki for debugging
ask_question(repo, "How can I debug issues with {feature}?")
```

---

## Troubleshooting Research

### Context7 Issues

**"Library not found":**
- Try alternative names (e.g., "react" vs "reactjs")
- Check if library is popular enough to be indexed
- Fall back to DeepWiki if available on GitHub

**"Limited content":**
- Use pagination (page=2, page=3)
- Try different topics
- Switch mode (code vs info)

### DeepWiki Issues

**"Repository not found":**
- Verify exact owner/repo format
- Check if repository is public
- Check for typos

**"Vague answers":**
- Ask more specific questions
- Break complex questions into parts
- Reference specific files or features

### General Tips

1. **Cross-validate** - If one source gives incomplete info, check the other
2. **Iterate** - Refine questions based on initial answers
3. **Combine** - Best results come from using both sources
4. **Verify** - Especially for version-specific information
5. **Update** - Research may need refresh for active projects

---

## Research Workflow Template

```markdown
## Research Plan for {library}

### 1. Initial Discovery
- [ ] Resolve Context7 library ID
- [ ] Check DeepWiki wiki structure
- [ ] Identify available documentation

### 2. Foundation Research
- [ ] Context7: Overview (info mode)
- [ ] Context7: Installation (code mode)
- [ ] DeepWiki: Architecture question

### 3. Core Documentation
- [ ] Context7: API reference (code mode)
- [ ] Context7: Common topics (paginated)
- [ ] DeepWiki: Implementation details

### 4. Advanced Topics
- [ ] DeepWiki: Edge cases
- [ ] DeepWiki: Performance considerations
- [ ] Context7: Best practices

### 5. Synthesis
- [ ] Combine findings
- [ ] Identify remaining gaps
- [ ] Additional targeted queries
- [ ] Final documentation structure
```
