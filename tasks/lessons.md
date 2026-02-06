# Lessons Learned

> Patterns to avoid. Rules learned from corrections. Review at session start.

---

## Rules

### Never override `--landing-*` CSS variables in `.dark` scope
- **What went wrong**: The `.dark` block in `globals.css` overrode all `--landing-*` variables to dark values. This broke the landing page because it's a self-contained light design with *intentional* dark sections (WaitlistCTA, footer). Forcing everything dark made those intentional sections look wrong, and forcing everything light broke them too.
- **How to prevent it**: Landing page variables should only be defined at `:root` and never touched by `.dark`. If ShadCN components (Card, Accordion, Button) look wrong inside the landing page in dark mode, pin only the ShadCN variables (`--card`, `--border`, `--muted`, etc.) inside `.dark .landing-page` — don't touch the landing-specific variables.

### Don't use hardcoded `bg-white` in components that live inside themed pages
- **What went wrong**: `FloatingNavbar.tsx` and `floating-navbar.tsx` used `bg-white` and `bg-white/80`. When the app toggled to dark mode, the nav background stayed white but text colors flipped to light, making text invisible (white on white).
- **How to prevent it**: Use semantic color variables (`bg-landing-bg`, `bg-landing-bg/80`) instead of hardcoded `bg-white` in any component that lives inside the landing page wrapper. Hardcoded colors don't respond to theme changes.

### Tailwind v4 `@theme` variables don't re-resolve from nested scopes
- **What went wrong**: Attempted to fix dark mode by overriding `--landing-bg` inside `.dark .landing-page`. The CSS variable was correctly set to the light value, but `--color-landing-bg` (registered by Tailwind v4's `@theme` block at `:root`) still resolved to the dark value. Tailwind v4 compiles `@theme` variables at registration time, not dynamically.
- **How to prevent it**: Don't try to override Tailwind `@theme`-registered variables from nested selectors. Instead, prevent the variable from being overridden in the first place (remove it from `.dark` block), or use `--color-*` overrides directly (but this is fragile).

### Remove fake social proof early — don't wait for it to become embarrassing
- **What went wrong**: Landing page had "Trusted by 500+ engineers" with DiceBear-generated avatars and a fake testimonial from "Engineering Lead, Series A Startup." These are obvious fabrications that erode trust.
- **How to prevent it**: Never add social proof that can't be attributed to a real person or verified metric. If you don't have real testimonials yet, leave that section out entirely.

---

## Patterns to Avoid

### The "force everything light/dark" CSS override
Trying to fix dark mode issues by adding a massive CSS block that overrides every variable is fragile and breaks intentional design decisions. Scope fixes narrowly — only pin the variables that are actually misbehaving.

### Iterating visually without screenshots
The dark mode bug required 3 iterations to fix because the first two attempts weren't fully verified visually. Always scroll through the entire page and screenshot each section after CSS changes.

### Padding as afterthought
Section padding (`py-20 md:py-32`) accumulated across sections without considering the total page height. The page ended up ~11,600px tall with dead zones. Review total scroll height after adding sections.

---

## Session Log

| Date | Lesson | Source |
|------|--------|--------|
| 2026-02-05 | Landing page `--landing-*` vars must never flip in `.dark` — pin only ShadCN vars inside `.dark .landing-page` | Dark mode fix iteration (3 attempts) |
| 2026-02-05 | Replace `bg-white` with `bg-landing-bg` in nav components inside themed pages | Mobile nav white-on-white bug |
| 2026-02-05 | Tailwind v4 `@theme` vars compile at `:root`, don't dynamically resolve from nested overrides | Failed CSS override attempt |
| 2026-02-05 | Remove fake social proof (DiceBear avatars, unattributed testimonials) — they erode trust | Landing page conversion audit |
| 2026-02-05 | Reduce section padding ~25% when page exceeds ~10,000px total height | Whitespace reduction pass |
