# Plan: Change Default Markdown Generator from "static" to "claude"

## Summary

Change the spec-sandbox subsystem's default markdown generator from "static" (template-based) to "claude" (Claude Agent SDK-based) to enable generating files with rich frontmatter and better contextual awareness.

## Current State

### Inconsistency Between CLI and Config

There's currently an inconsistency:

1. **CLI default** (`cli.py:101`): `default="claude"`
2. **Config default** (`config.py:87`): `default="static"`

When running via CLI, the generator defaults to "claude". But when using the config programmatically or via environment variables without explicit override, it defaults to "static".

### Generator Differences

| Feature | Static Generator | Claude Generator |
|---------|-----------------|------------------|
| Speed | Fast (no API calls) | Slower (API calls per file) |
| Cost | Free | ~$0.01-0.05 per file |
| Frontmatter | Basic/None | Rich, context-aware |
| Language Detection | File extension only | Intelligent detection |
| Content Quality | Template-based | AI-generated scaffolding |
| Spec Context | Minimal | Full requirement awareness |

## Proposed Changes

### File: `subsystems/spec-sandbox/src/spec_sandbox/config.py`

**Current (line 86-88):**
```python
markdown_generator: str = Field(
    default="static",
    description="Generator type: 'static' (template-based, fast) or 'claude' (Claude Agent SDK, slow)",
)
```

**Proposed:**
```python
markdown_generator: str = Field(
    default="claude",
    description="Generator type: 'claude' (Claude Agent SDK, rich frontmatter) or 'static' (template-based, fast, no API costs)",
)
```

### Environment Variable Override

The config already supports `SPEC_SANDBOX_MARKDOWN_GENERATOR` via Pydantic settings. Users can set:
```bash
export SPEC_SANDBOX_MARKDOWN_GENERATOR=static
```
to use the faster, cost-free generator when needed.

## Considerations

### Cost Implications

- Claude generator makes API calls for each generated file
- Estimated cost: $0.01-0.05 per file depending on complexity
- For a spec with 20 files: ~$0.20-1.00 per spec execution

### When to Use Static Generator

Users should consider `--generator static` when:
- Running many specs in rapid succession (development/testing)
- Cost-sensitive environments
- Files don't need rich frontmatter
- Speed is critical

### When Claude Generator Excels

The claude generator provides value when:
- Files need rich frontmatter with requirement traceability
- AI-generated scaffolding improves code quality
- Context-aware file generation is important
- Production spec executions where quality matters

## Migration Path

1. **No breaking changes** - Static generator still available via `--generator static`
2. **Environment override** - Teams can set `SPEC_SANDBOX_MARKDOWN_GENERATOR=static` globally
3. **Documentation update** - Update README to explain generator options

## Testing Required

1. Verify CLI and config now agree on default
2. Test claude generator works with current Claude Agent SDK version
3. Verify static generator still works when explicitly requested
4. Test environment variable override works

## Files to Modify

1. `subsystems/spec-sandbox/src/spec_sandbox/config.py` - Change default value
2. `subsystems/spec-sandbox/README.md` - Document generator options (if exists)

## Rollback Plan

If issues arise, simply revert the default in `config.py` back to "static". The change is localized to one line.
