# X/Twitter Swipe File

**Purpose**: Ready-to-post content for X.com organized by theme and type.
**Total Posts**: 200+ across 16 themed files

## File Structure

Each file contains posts organized by a specific theme or format:

| File | Theme | Post Count | Best For |
|------|-------|------------|----------|
| `general_builder.md` | General SaaS/builder wisdom | 12 | Daily engagement |
| `spec_driven.md` | Spec-driven development value | 12 | Education |
| `agent_problems.md` | Why AI agents fail | 15 | Problem awareness |
| `vision_and_product.md` | What OmoiOS does | 15 | Product marketing |
| `cto_pain_points.md` | CTO/EM specific pain | 12 | Target audience |
| `build_in_public.md` | Honest progress updates | 12 | Trust building |
| `hot_takes.md` | Contrarian opinions | 15 | Engagement/reach |
| `technical_education.md` | How things work | 12 | Authority building |
| `stories.md` | Personal narratives | 15 | Relatability |
| `competitor_callouts.md` | Cursor/Antigravity contrast | 15 | Positioning |
| `threads.md` | Multi-tweet threads | 5 | Deep education |
| `customer_avatars.md` | First-person CTO/EM voice | 12 | Empathy |
| `memes_analogies.md` | Relatable comparisons | 15 | Virality |
| `use_cases.md` | Specific implementation examples | 12 | Proof |
| `failure_stories.md` | What broke and why | 12 | Authenticity |
| `engagement_questions.md` | Posts that invite replies | 15 | Community |
| `x_posts.md` | Original comprehensive file | 68 | Reference/archive |

## Frontmatter Schema

Each post file uses YAML frontmatter for scripting:

```yaml
---
title: "Post Title"
category: "theme-name"
tags: [ai-coding, saas, cto, agents]
status: draft | ready | posted
posted_date: null | 2026-01-15
engagement: null | {likes: 0, replies: 0, retweets: 0}
notes: "Any context about this post"
---
```

## Usage

### Finding posts by tag
```bash
grep -l "tags:.*cto" docs/marketing/swipe_file/*.md
```

### Finding ready posts
```bash
grep -l "status: ready" docs/marketing/swipe_file/*.md
```

### Counting posts per file
```bash
grep -c "^### " docs/marketing/swipe_file/*.md
```

## Content Calendar

| Day | Theme | File |
|-----|-------|------|
| Mon | Builder mindset | `general_builder.md` |
| Tue | Problem awareness | `agent_problems.md` |
| Wed | Product angle | `vision_and_product.md` |
| Thu | Competitor contrast | `competitor_callouts.md` |
| Fri | Build in public | `build_in_public.md` |
| Sat | Hot take | `hot_takes.md` |
| Sun | Story or thread | `stories.md` or `threads.md` |
