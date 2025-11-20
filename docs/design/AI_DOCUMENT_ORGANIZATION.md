# AI-Powered Document Organization

**Created**: 2025-11-20
**Status**: Active
**Purpose**: Guide for using AI to automatically organize documentation

---

## Overview

The `organize_docs.py` script uses instructor + async OpenAI to intelligently analyze and reorganize documentation based on content, not just filename.

### What It Does

1. **Analyzes** document content using GPT-4
2. **Categorizes** by type (requirements, design, architecture, etc.)
3. **Suggests** proper naming following snake_case conventions
4. **Detects** missing metadata (Created, Status, Purpose)
5. **Identifies** orphaned docs in wrong locations
6. **Recommends** archiving outdated content
7. **Finds** related documents for cross-referencing

---

## Installation

```bash
# Install dependencies
uv add instructor openai pydantic tqdm

# Set API key
export OPENAI_API_KEY=sk-your-key-here

# Or add to .env
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

---

## Usage

### Basic Usage (Dry Run)

```bash
# Analyze all documents (no changes)
python scripts/organize_docs.py

# Output shows:
# - Current location
# - Suggested location
# - Document type and category
# - Confidence score
# - Reasoning for changes
```

### Apply Changes

```bash
# Apply AI-suggested changes
python scripts/organize_docs.py --apply

# Will prompt for confirmation before making changes
```

### Export Reorganization Plan

```bash
# Export detailed plan to markdown
python scripts/organize_docs.py --export reorganization_plan.md

# Review plan before applying
cat reorganization_plan.md

# Then apply
python scripts/organize_docs.py --apply
```

### Batch Processing

```bash
# Use batch processor for faster analysis (concurrent API calls)
python scripts/organize_docs_batch.py --concurrent 10 --detailed

# Options:
#   --concurrent N    # Number of concurrent API calls (default: 5)
#   --detailed        # Show detailed report
#   --export file.md  # Export plan
#   --apply           # Apply changes
```

---

## Example Output

```
🔍 Found 87 documents to analyze

📄 Analyzing: PHASE5_MEMORY_COMPLETE.md
  Type: implementation
  Category: memory
  Confidence: 95%
  Status: Implemented
  ⚠️  Should Archive
  Actions: Archive to archive/phase5/phase5_memory_complete.md
  Reasoning: Completion log for Phase 5 memory work. Should be archived as historical.

📄 Analyzing: auth_system_notes.md
  Type: design
  Category: auth
  Confidence: 88%
  Status: Active
  ⚠️  Orphaned
  Actions: Move to design/services/auth_system_design.md, Add metadata: **Created**, **Status**
  Reasoning: Design document for authentication system. Should be in design/services/.

================================================================
📊 Organization Summary
================================================================

Total documents analyzed: 87
  📦 Need to move: 23
  📝 Need metadata: 45
  📁 Should archive: 12
  ✅ Already organized: 7

Document Types:
  architecture: 3
  design: 28
  implementation: 15
  requirements: 12
  summary: 8
  chat_log: 6
  other: 15

🔍 DRY RUN - No changes applied
Run with --apply to make changes
```

---

## How It Works

### 1. Content Analysis

The AI analyzes document content to determine:
- **Purpose**: What is this document for?
- **Type**: Requirements, design, implementation, etc.
- **Category**: Which domain (auth, workflows, frontend, etc.)?
- **Status**: Draft, approved, implemented, archived?

### 2. Categorization Rules

Based on content patterns:

```python
# Requirements: Contains REQ-* codes, describes "what"
if "REQ-" in content and "shall" in content.lower():
    document_type = "requirements"

# Design: Contains architecture, API specs, describes "how"
if "architecture" in content.lower() or "API" in content:
    document_type = "design"

# Implementation: Contains status updates, completion notes
if "complete" in content.lower() or "implemented" in content.lower():
    document_type = "implementation"
```

### 3. Naming Suggestions

Converts to proper snake_case:
```
PHASE5_MEMORY_COMPLETE.md  → phase5_memory_complete.md
AuthSystemDesign.md        → auth_system_design.md
memory-system.md           → memory_system.md
```

### 4. Location Suggestions

Places in appropriate category:
```
auth_system_notes.md       → design/services/auth_system_design.md
PHASE5_COMPLETE.md         → archive/phase5/phase5_complete.md
memory_requirements.md     → requirements/memory/memory_system_requirements.md
```

---

## AI Prompt Template

The script uses this prompt structure:

```
Analyze this documentation file and suggest proper organization.

Current filename: {filename}
Current location: {location}

Document content:
{content}

Determine:
1. Document type (requirements/design/architecture/implementation)
2. Category/domain (auth/workflows/frontend/monitoring)
3. Proper filename (snake_case)
4. Current status (Draft/Approved/Active/Implemented/Archived)
5. Is it orphaned or poorly organized?
6. Should it be archived?
7. Related documents to cross-reference

Standards:
- Requirements: What to build (REQ-* codes)
- Design: How to build (technical specs)
- Architecture: Why decisions made (ADRs)
- Implementation: Build status
- snake_case naming (except SUMMARY files)
```

---

## Configuration

### Model Selection

The script defaults to Fireworks AI for cost-effectiveness:

```bash
# Default (Fireworks AI)
FIREWORKS_API_KEY=your-key
FIREWORKS_MODEL=accounts/fireworks/models/gpt-oss-120b

# Or use OpenAI
OPENAI_API_KEY=sk-your-key
# Script will use gpt-4o by default if FIREWORKS not set

# Or override via command line
python scripts/organize_docs.py --model gpt-4-turbo --base-url https://api.openai.com/v1
```

**Supported Providers**:
- **Fireworks AI** (default) - Most cost-effective
  - Model: `accounts/fireworks/models/gpt-oss-120b`
  - Base URL: `https://api.fireworks.ai/inference/v1`
  - Cost: ~$0.0002/doc (very cheap!)

- **OpenAI**
  - Model: `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`
  - Base URL: `https://api.openai.com/v1`
  - Cost: ~$0.003-0.02/doc

- **Any OpenAI-compatible API**
  - Set `--base-url` and `--model` flags

### Concurrency Settings

```python
# Batch organizer (faster)
organizer = BatchDocumentOrganizer(
    max_concurrent=10,  # More concurrent = faster, but costs more
)
```

### Cost Estimation

**Per document** (~2,000 tokens total):

| Provider | Model | Cost/Doc | 100 Docs |
|----------|-------|----------|----------|
| **Fireworks AI** (default) | gpt-oss-120b | ~$0.0002 | ~$0.02 |
| OpenAI | GPT-3.5-Turbo | ~$0.003 | ~$0.30 |
| OpenAI | GPT-4-Turbo | ~$0.01 | ~$1.00 |
| OpenAI | GPT-4 | ~$0.02 | ~$2.00 |

**Recommendation**: Use Fireworks AI (default) - 100x cheaper than OpenAI!

---

## Advanced Usage

### Organize Specific Pattern

```bash
# Only PHASE*.md files
python scripts/organize_docs.py --pattern "PHASE*.md"

# Only files in specific directory
python scripts/organize_docs.py --pattern "design/*.md"
```

### Custom Skip Directories

```bash
# Skip multiple directories
python scripts/organize_docs.py --skip archive frontend requirements
```

### Integration with Justfile

```justfile
# Add to Justfile

# Organize docs with AI (dry-run)
docs-organize:
    python scripts/organize_docs.py --export reorganization_plan.md

# Organize and apply
docs-organize-apply:
    python scripts/organize_docs_batch.py --apply --detailed

# Organize specific pattern
docs-organize-pattern pattern:
    python scripts/organize_docs.py --pattern "{{pattern}}"
```

Then use:
```bash
just docs-organize               # Dry-run analysis
just docs-organize-apply         # Apply changes
just docs-organize-pattern "AUTH*"  # Specific pattern
```

---

## Output Files

### reorganization_plan.md

Example output:

```markdown
# Document Reorganization Plan

**Generated**: 2025-11-20
**Total Documents**: 87

---

## Files to Move

- `docs/auth_notes.md` → `docs/design/services/auth_system_design.md`
  - Reason: Design document for auth system should be in design/services/

- `docs/PHASE5_COMPLETE.md` → `docs/archive/phase5/phase5_complete.md`
  - Reason: Historical completion log should be archived

## Files Needing Metadata

- `memory_system.md`: Missing **Created**, **Status**
- `validation_workflow.md`: Missing **Purpose**

## Files to Archive

- `PHASE3_COMPLETE.md`
  - Reason: Historical phase completion, no longer active
```

---

## Safety Features

### Dry Run by Default

Always runs in dry-run mode unless `--apply` flag is used.

### Confirmation Prompt

Before applying changes:
```
⚠️  This will reorganize 23 documents
Continue? (y/N):
```

### Backup Recommendation

```bash
# Create backup before applying
git add -A
git commit -m "Backup before doc reorganization"

# Run organization
python scripts/organize_docs.py --apply

# If something wrong, rollback
git reset --hard HEAD~1
```

### Reversible Changes

All changes are file moves/renames - can be reverted:
```bash
git log --follow docs/design/services/memory_system.md  # Track file history
git checkout HEAD~1 -- docs/  # Restore all docs
```

---

## Best Practices

### 1. Start with Dry Run

```bash
# Always dry-run first
python scripts/organize_docs.py --export plan.md

# Review plan
cat plan.md

# Then apply if looks good
python scripts/organize_docs.py --apply
```

### 2. Organize in Batches

```bash
# Organize one category at a time
python scripts/organize_docs.py --pattern "design/*.md" --apply
python scripts/organize_docs.py --pattern "requirements/*.md" --apply
```

### 3. Review AI Suggestions

The AI is smart but not perfect:
- Review suggested locations
- Verify categorizations
- Check confidence scores (< 70% might need manual review)

### 4. Update Cross-References

After reorganizing:
```bash
# Find broken links
python scripts/check_doc_links.py

# Update references
# (manual or with find-and-replace)
```

---

## Troubleshooting

### API Key Issues

```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Or check .env
grep OPENAI_API_KEY .env

# Test API connection
python -c "from openai import AsyncOpenAI; import asyncio; asyncio.run(AsyncOpenAI().models.list())"
```

### Rate Limiting

```bash
# Reduce concurrency
python scripts/organize_docs_batch.py --concurrent 2

# Add delay between requests (edit script)
await asyncio.sleep(0.5)  # 500ms delay
```

### Unexpected Categorization

If AI miscategorizes:
1. Check confidence score (low = uncertain)
2. Review reasoning
3. Manually override if needed
4. Provide feedback via prompt adjustment

---

## Future Enhancements

### Planned Features

- [ ] Automatic link updating after reorganization
- [ ] Duplicate document detection
- [ ] Content summarization for README generation
- [ ] Broken link detection and fixing
- [ ] Automatic metadata extraction from content
- [ ] Integration with git for tracking moves
- [ ] Custom categorization rules/overrides
- [ ] Batch processing with progress resumption

### Potential Improvements

```python
# Add custom categorization rules
custom_rules = {
    "PHASE*": {"type": "implementation", "category": "phases"},
    "*_SUMMARY": {"type": "summary", "category": "root"},
}

# Add content-based detection
if "REQ-AUTH-" in content:
    category = "auth"
elif "REQ-MEM-" in content:
    category = "memory"
```

---

## Cost Management

### Tips for Reducing Costs

1. **Use GPT-3.5-Turbo** for simple categorization:
   ```python
   model="gpt-3.5-turbo"  # ~1/10th the cost of GPT-4
   ```

2. **Cache results** to avoid re-analyzing unchanged files:
   ```python
   # Check file modification time
   if file.stat().st_mtime < last_analysis_time:
       skip_analysis()
   ```

3. **Batch processing** - Process 10-20 docs at a time

4. **Local LLM option** - Use Ollama for free local processing:
   ```python
   # Use local model instead
   client = instructor.from_openai(
       OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
   )
   ```

---

This provides intelligent, AI-powered document organization that understands content and context!

