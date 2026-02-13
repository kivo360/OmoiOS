# Current Tasks

> Active work items. Check off as completed.

---

## In Progress

### Live Preview — E2E Testing & Remaining Work
- [x] Implement backend changes (5 files): task_queue, tickets, daytona_spawner, preview routes, worker
- [x] Add capability detection to all 3 task creation paths (quick-mode, approval, direct API)
- [x] Write 42 unit/integration tests (capability detection, notify route, preview setup)
- [x] Verify `/notify` endpoint responds correctly via curl
- [x] Push to main: `81093c08`, `2a1e8aca`
- [ ] Start OmoiOS frontend on correct port (was conflicting with another project on 3000)
- [ ] Create frontend task ("Build a React counter component with Tailwind") from command page
- [ ] Verify DB: task has `required_capabilities` populated (e.g. `["react", "component", "tailwind"]`)
- [ ] Verify backend logs: `[PREVIEW] Preview enabled`, `[PREVIEW] Preview session created`
- [ ] Verify DB: `preview_sessions` has `status=pending`, `preview_url` pre-populated from Daytona SDK
- [ ] Wait for sandbox worker → watch for `[PREVIEW] Dev server ready` in logs
- [ ] Verify preview session transitions to READY in DB
- [ ] Verify frontend Preview tab appears with working iframe on sandbox page
- [ ] Negative test: "Write a Python data analysis script" → no capabilities, no preview session
- [ ] Address uncommitted change in `frontend/app/(auth)/callback/page.tsx`

### Landing Page Conversion Optimization
- [x] Remove fake social proof (DiceBear avatars, "500+ engineers", fake testimonial) — `7c469a8`
- [x] Reduce section whitespace ~25% across 5 sections — `7c469a8`
- [x] Fix dark mode rendering (nav white-on-white, invisible text across sections) — `ea3ce1e`
- [x] Verify dark mode section-by-section in Chrome (hero, pricing, FAQ, CTA, footer)
- [x] Verify light mode not broken
- [ ] Add real social proof once available (real testimonials, real user count)
- [ ] Replace NightShift stats with real metrics (currently hardcoded "2h 28m", "5 steps", "1 PR")
- [ ] Consider adding a short demo video/GIF instead of static product screenshots

### Landing Page — Next Conversion Wins
- [ ] Headline clarity: Current "Describe it. Wake up to real results" is better than before but still abstract — test a more specific variant (e.g., "Describe a feature. Wake up to a pull request.")
- [ ] Above-the-fold email capture: Test whether removing "Watch Demo" link and making email input more prominent improves signups
- [ ] Mobile CTA: The mobile nav has "Get Started Free" but no email capture — consider adding inline email input on mobile hero
- [ ] Page load speed: Check Core Web Vitals — lots of framer-motion animations may hurt LCP/CLS on mobile
- [ ] Add analytics events: Track scroll depth, CTA clicks, and section visibility to validate changes with data

### Outreach & Validation (from hypotheses-to-validate.md)
- [ ] Send first batch of outreach (target: 500+, current: 0)
- [ ] Get 10+ conversations with right-fit ICPs
- [ ] Track "holy shit" moments and willingness to pay
- [ ] Update hypotheses-to-validate.md with real signal data

---

## Backlog

### Frontend Polish
- [ ] Audit all components for remaining hardcoded `bg-white` / `text-black` that could break in dark mode
- [ ] Test landing page on actual mobile devices (not just responsive resize)
- [ ] Logo visibility at small sizes on white bg — SVG stroke-only gold gradient is faint

### Content
- [ ] Finish PostHog session teardown article (draft at `docs/marketing/launch-content-2026-01/posthog-landing-page-teardown.md`)
- [ ] Build in public post about removing fake social proof and what replaced it

---

## Completed

| Date | Task | Commit |
|------|------|--------|
| 2026-02-05 | Remove fake social proof (avatars, stars, "500+ engineers", fake testimonial) | `7c469a8` |
| 2026-02-05 | Reduce section padding ~25% across HeroSection, NightShift, Stats, FAQ, WaitlistCTA | `7c469a8` |
| 2026-02-05 | Fix dark mode: pin ShadCN vars in `.dark .landing-page`, swap `bg-white` → `bg-landing-bg` in nav | `ea3ce1e` |
| 2026-02-05 | Full dark mode visual verification (all sections, desktop + mobile) | — |
| 2026-02-08 | Implement live preview backend (5 files, 3 gaps closed) | `81093c08` |
| 2026-02-08 | Add capability detection to remaining task creation paths | `2a1e8aca` |
| 2026-02-08 | Write 42 tests for live preview (capability detection, notify route, preview setup) | `81093c08` |

---

## Review Notes

### 2026-02-05: Landing Page Session
- **PostHog data** (from teardown draft): 8s avg session, 23% scroll depth, 84% bounce rate. The page needs to hook people faster — headline and above-the-fold experience are the highest-leverage fixes.
- **Dark mode took 3 iterations** to get right. Root cause: Tailwind v4 `@theme` vars don't re-resolve from nested CSS scopes. Lesson captured in `tasks/lessons.md`.
- **Fake social proof removed.** The page now has zero unverifiable claims. Next step is replacing them with real data once available.
- **Pricing is live** ($0 / $299 / $999 tiers). FAQ covers billing, concurrent agents, BYOK, code safety.
