# AI-Powered Document Organization

## Quick Start

### 1. Install Dependencies

```bash
# Install instructor, OpenAI, and utilities
uv add instructor openai pydantic tqdm
```

### 2. Set API Key

```bash
# Option A: Environment variable
export OPENAI_API_KEY=sk-your-key-here

# Option B: Add to .env
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### 3. Run Organization

```bash
# Dry-run (analyze only, no changes)
just docs-organize

# Batch with progress bar
just docs-organize-batch

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

### Basic
```bash
just docs-organize               # Analyze all docs
just docs-organize-apply         # Apply AI suggestions
```

### Advanced
```bash
# Specific pattern
just docs-organize-pattern "PHASE*.md"

# Direct script usage
python scripts/organize_docs.py --help
python scripts/organize_docs_batch.py --concurrent 10 --detailed
```

---

## Cost

**Per document**: ~$0.003 (GPT-4-Turbo) or ~$0.02 (GPT-4)
**For 100 docs**: ~$0.30 (GPT-4-Turbo) or ~$2.00 (GPT-4)

---

## Safety

- ✅ Dry-run by default
- ✅ Confirmation prompt before applying
- ✅ Git-reversible (all changes are file moves)
- ✅ Exports plan for review before applying

---

**See**: `docs/design/AI_DOCUMENT_ORGANIZATION.md` for complete guide

