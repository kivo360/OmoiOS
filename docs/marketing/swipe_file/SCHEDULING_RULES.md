---
title: "Tweet Scheduling Rules"
category: rules
tags: [scheduling, validation, rules, constraints]
description: "Rules and constraints for appropriate tweet scheduling"
last_updated: 2026-01-13
---

# Tweet Scheduling Rules

These rules ensure content is scheduled appropriately for maximum engagement and to avoid common mistakes.

---

## Category Rules

Each content category has specific timing constraints:

| Category | Best Days | Best Times | Min Gap (hours) | Max Per Day | Notes |
|----------|-----------|------------|-----------------|-------------|-------|
| `hot-takes` | Sat, Sun | 10 AM - 3 PM | 24 | 1 | Weekend leisure = more debate |
| `engagement-questions` | Mon-Fri | 12 PM, 6 PM | 12 | 2 | End of work sessions |
| `build-in-public` | Fri | 9 AM | 168 (weekly) | 1 | Weekly cadence |
| `stories` | Any | 9 AM, 6 PM | 24 | 2 | Morning/evening engagement |
| `threads` | Sun | 11 AM | 168 (weekly) | 1 | Deep content day |
| `technical-education` | Tue-Thu | 12 PM | 24 | 1 | Mid-week learning |
| `competitor-callouts` | Wed-Fri | 9 AM | 48 | 1 | Use sparingly |
| `memes-analogies` | Fri | 12 PM | 24 | 1 | End of week humor |
| `failure-stories` | Thu | 12 PM | 72 | 1 | Vulnerability, not too often |
| `cto-pain-points` | Tue, Thu | 9 AM | 48 | 1 | Target audience active |
| `customer-avatars` | Sat | 3 PM | 72 | 1 | Relatable weekend read |
| `vision-and-product` | Wed | 9 AM | 48 | 1 | Mid-week strategy |
| `spec-driven` | Tue | 12 PM | 48 | 1 | Educational |
| `use-cases` | Wed | 12 PM | 48 | 1 | Practical examples |
| `general-builder` | Mon | 9 AM | 24 | 2 | Start of week motivation |

---

## Content Mix Rules

### Daily Mix (3-5 posts/day)
- **Max 1 hot take** per day
- **Max 1 promotional/product** post per day
- **At least 1 engagement** post (question, story, or educational)
- **Never 2 of same category** back-to-back

### Weekly Mix
- **1 thread** per week (Sunday recommended)
- **1 build-in-public** update per week (Friday recommended)
- **2-3 hot takes** maximum per week
- **Mix categories** - don't repeat same source file 3 times in a week

---

## Time-Sensitive Content

Some content should NOT be scheduled far in advance:

| Content Type | Max Advance Schedule | Reason |
|--------------|---------------------|--------|
| "this week's progress" | 7 days | Refers to recent work |
| "woke up to..." | 3 days | Implies recent event |
| "yesterday..." | 1 day | Time reference |
| Build-in-public updates | 7 days | Should reflect actual progress |
| Competitor callouts | 14 days | Industry changes fast |

### Keywords that indicate time-sensitivity:
- "this week", "this month"
- "yesterday", "today", "last night"
- "just shipped", "just launched"
- "working on", "building"
- Current version numbers or dates

---

## Validation Checks

Before scheduling, validate:

### 1. Category Spacing
```
❌ BAD:  hot-take at 9 AM, hot-take at 12 PM (same day)
✅ GOOD: hot-take Saturday, hot-take Sunday
```

### 2. Content Diversity
```
❌ BAD:  3 posts from same source file in one day
✅ GOOD: Mix of stories, education, engagement
```

### 3. Time Slot Appropriateness
```
❌ BAD:  thread at 6 PM on Tuesday (too short attention)
✅ GOOD: thread at 11 AM on Sunday (leisure reading time)
```

### 4. Duplicate Content
```
❌ BAD:  Same post scheduled twice in 2 weeks
✅ GOOD: Content recycled after 30+ days
```

### 5. Time-Sensitive Staleness
```
❌ BAD:  "this week's progress" scheduled 3 weeks out
✅ GOOD: "this week's progress" scheduled for same week
```

---

## Recommended Weekly Schedule Template

| Day | 9 AM | 12 PM | 6 PM |
|-----|------|-------|------|
| **Monday** | general-builder | agent-problems | engagement-question |
| **Tuesday** | stories | spec-driven | cto-pain-points |
| **Wednesday** | vision-product | technical-education | engagement-question |
| **Thursday** | competitor-callout | failure-stories | hot-take |
| **Friday** | build-in-public | memes-analogies | stories |
| **Saturday** | hot-take (10 AM) | - | customer-avatars (3 PM) |
| **Sunday** | thread (11 AM) | - | - |

---

## Validation Error Levels

| Level | Action | Example |
|-------|--------|---------|
| `ERROR` | Block scheduling | 2 threads same day |
| `WARNING` | Show but allow | Hot take on Tuesday (not ideal) |
| `INFO` | Informational | Time-sensitive content > 7 days out |

---

## Script Integration

The `typefully_scheduler.py` should:

1. **`--validate`** - Check schedule against rules without posting
2. **`--strict`** - Fail on any WARNING or ERROR
3. **`--auto-fix`** - Suggest or apply fixes for violations
4. **Show violations** in dry-run output

Example output:
```
⚠️  WARNING: 2 hot-takes scheduled same day (Sat 10 AM, Sat 3 PM)
   Suggestion: Move second hot-take to Sunday

❌ ERROR: "this week's progress" scheduled 14 days in advance
   This content is time-sensitive, schedule within 7 days

✅ Schedule validated: 2 warnings, 0 errors
```
