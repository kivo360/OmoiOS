# AI-Powered Document Organization

## Quick Start

### 1. Install Dependencies

```bash
# Install instructor, OpenAI, and utilities
uv add instructor openai pydantic tqdm
```

### 2. Set API Key

```bash
# Option A: Fireworks AI (recommended - 100x cheaper!)
export FIREWORKS_API_KEY=your-fireworks-key-here

# Option B: OpenAI
export OPENAI_API_KEY=sk-your-key-here

# Option C: Add to .env
cat >> .env << 'EOF'
FIREWORKS_API_KEY=your-fireworks-key-here
FIREWORKS_MODEL=accounts/fireworks/models/gpt-oss-120b
EOF
```

### 3. Run Organization

```bash
# Dry-run with parallel batch processing (default: 5 concurrent)
just docs-organize

# Use more concurrent workers for faster processing
just docs-organize 10

# Apply changes
just docs-organize-apply
```

---

## What It Does

The AI analyzes each document's **content** (not just filename) to:

✅ Determine document type (requirements/design/architecture)
✅ Categorize by domain (auth/workflows/frontend/memory)
✅ Suggest proper snake_case naming
✅ Detect missing metadata (Created, Status, Purpose)
✅ Identify orphaned docs in wrong locations
✅ Recommend archiving outdated content
✅ Find related documents for cross-linking

---

## Example

### Before
```
docs/
├── AuthSystemNotes.md               # ❌ Wrong name, wrong location
├── PHASE5-MEMORY-COMPLETE.md        # ❌ Should be archived
├── memory-requirements.md           # ❌ Hyphens, wrong location
└── design/
    └── notes.md                     # ❌ Too generic
```

### After (AI-Organized)
```
docs/
├── requirements/
│   └── memory/
│       └── memory_system_requirements.md  # ✅ Moved and renamed
├── design/
│   └── services/
│       └── auth_system_design.md          # ✅ Moved and renamed
└── archive/
    └── phase5/
        └── phase5_memory_complete.md      # ✅ Archived
```

---

## Commands

### Basic (Now Uses Batch Processing!)
```bash
just docs-organize               # Analyze all docs (5 concurrent workers)
just docs-organize 10            # Use 10 concurrent workers (faster!)
just docs-organize-apply         # Apply AI suggestions
```

### Advanced
```bash
# Specific pattern (batch)
just docs-organize-pattern "PHASE*.md"

# Specific pattern with more workers
just docs-organize-pattern "PHASE*.md" 10

# Single file (non-batch, for testing)
just docs-organize-single "AUTH_SYSTEM.md"

# Direct script usage
python scripts/organize_docs_batch.py --concurrent 10 --detailed
python scripts/organize_docs.py --help
```

---

## Cost

| Provider | Cost/Doc | 100 Docs |
|----------|----------|----------|
| **Fireworks AI** (default) | ~$0.0002 | ~$0.02 |
| OpenAI GPT-3.5 | ~$0.003 | ~$0.30 |
| OpenAI GPT-4 | ~$0.02 | ~$2.00 |

**Using Fireworks AI by default** - 100x cheaper than OpenAI!

---

## Safety

- ✅ Dry-run by default
- ✅ Confirmation prompt before applying
- ✅ Git-reversible (all changes are file moves)
- ✅ Exports plan for review before applying

---

**See**: `docs/design/AI_DOCUMENT_ORGANIZATION.md` for complete guide

