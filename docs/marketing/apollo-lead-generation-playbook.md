# Apollo Lead Generation Playbook

> How to pull 1000s of engineering leader leads using Apollo API

---

## Overview

**Goal:** Build a targeted lead list of engineering leaders at funded startups who are likely experiencing the "backlog > headcount" pain.

**Timeline:**
- Week 1: Warm up email domains
- Week 2: Pull leads via API, start small batch outreach
- Week 3+: Scale outreach with winning messages

---

## Part 1: ICP Search Criteria

### Primary ICP: Engineering Leaders at Scaling Startups

| Filter | Values | Why |
|--------|--------|-----|
| **Job Titles** | VP Engineering, Engineering Manager, CTO, Head of Engineering, Director of Engineering, VP of Engineering, Head of Product Engineering | Decision makers who feel the pain |
| **Company Size** | 50-500 employees | Big enough to have scaling pain, small enough to move fast |
| **Funding Stage** | Series A, Series B, Series C | Have budget, actively scaling |
| **Industries** | SaaS, Software, B2B, Fintech, Developer Tools | Tech-forward, understand the problem |
| **Location** | US, Canada, UK, Germany (optional) | English-speaking, similar business culture |

### Secondary ICP: Agency Technical Leadership

| Filter | Values | Why |
|--------|--------|-----|
| **Job Titles** | Technical Director, CTO, Development Lead, Head of Engineering | Agency decision makers |
| **Company Size** | 20-200 employees | Typical agency size |
| **Industries** | Digital Agency, Software Development, IT Services | Agencies juggling multiple projects |

### Exclusion Criteria

Exclude these to avoid wasting outreach:

- Companies < 20 employees (no budget, founder does everything)
- Companies > 1000 employees (procurement hell, long sales cycles)
- Bootstrapped/No funding (unless profitable and growing)
- Non-tech industries (won't understand the problem)

---

## Part 2: Apollo API Filters

### Primary ICP Query

```python
PRIMARY_ICP_FILTERS = {
    # Job titles - engineering leadership
    "person_titles": [
        "VP Engineering",
        "VP of Engineering",
        "Engineering Manager",
        "Senior Engineering Manager",
        "CTO",
        "Chief Technology Officer",
        "Head of Engineering",
        "Director of Engineering",
        "Director, Engineering",
        "Head of Product Engineering",
        "Principal Engineering Manager"
    ],

    # Company size - scaling startups
    "organization_num_employees_ranges": [
        "51,100",
        "101,200",
        "201,500"
    ],

    # Funding stage - have money to spend
    "organization_latest_funding_stage_cd": [
        "series_a",
        "series_b",
        "series_c"
    ],

    # Industries - tech-forward
    "organization_industry_tag_ids": [
        # You'll need to look up actual tag IDs in Apollo
        # These are examples - SaaS, Software, B2B
    ],

    # Location (optional - remove for global)
    "person_locations": [
        "United States",
        "Canada",
        "United Kingdom"
    ],

    # Pagination
    "page": 1,
    "per_page": 100  # Max 100 per request
}
```

### Secondary ICP Query (Agencies)

```python
AGENCY_ICP_FILTERS = {
    "person_titles": [
        "CTO",
        "Technical Director",
        "Head of Engineering",
        "Development Lead",
        "Director of Technology",
        "VP Engineering"
    ],

    "organization_num_employees_ranges": [
        "21,50",
        "51,100",
        "101,200"
    ],

    # Agency-specific industries
    "q_organization_keyword_tags": [
        "digital agency",
        "software development",
        "software consultancy",
        "IT services",
        "web development agency"
    ],

    "page": 1,
    "per_page": 100
}
```

---

## Part 3: Search Strategy

### Phase 1: Cast Wide Net (Week 1)

1. **Run primary ICP search** - Get total count
2. **Run secondary ICP search** - Get total count
3. **Sample 100 from each** - Review quality manually
4. **Refine filters** - Remove bad matches, tighten criteria

### Phase 2: Pull Full Lists (Week 2)

1. **Paginate through all results** - Up to 50,000 per search
2. **Dedupe** - Same person at multiple companies
3. **Enrich top matches** - Get verified emails
4. **Score leads** - Prioritize by fit signals

### Lead Scoring Criteria

| Signal | Score | Why |
|--------|-------|-----|
| Recently funded (< 6 months) | +3 | Active hiring, fresh pain |
| 10+ open engineering roles | +3 | Desperate for capacity |
| Series B specifically | +2 | Sweet spot for scaling pain |
| Posted about hiring challenges | +2 | Publicly acknowledged pain |
| Company growing fast (news) | +2 | Pain is acute |
| Has verified email | +1 | Can actually reach them |
| US-based | +1 | Same timezone, easier calls |

**Priority tiers:**
- Tier 1 (Score 8+): Reach out first, personalize heavily
- Tier 2 (Score 5-7): Second wave, semi-personalized
- Tier 3 (Score < 5): Automated sequences only

---

## Part 4: Email Warming Strategy

### Why Warm Up?

New domains/emails sending volume = spam folder. Warming builds reputation.

### Setup (Do This Now)

1. **Buy 2-3 domains** similar to your main domain
   - Example: `omoios.dev` → `omoiosmail.com`, `get-omoios.com`
   - Use Namecheap, Google Domains, or Cloudflare

2. **Set up Google Workspace or Outlook** on each domain
   - Create 2-3 email addresses per domain
   - `kevin@`, `k.hill@`, `team@`

3. **Configure DNS properly**
   - SPF record
   - DKIM record
   - DMARC record
   - All 3 required for deliverability

4. **Sign up for warming service**
   - Instantly.ai ($37/mo) - recommended
   - Warmbox.ai ($19/mo)
   - Lemwarm (part of Lemlist)

### Warming Timeline

| Week | Daily Send Volume | Notes |
|------|-------------------|-------|
| Week 1 | 5-10 emails/day | Warming service only |
| Week 2 | 15-25 emails/day | Mix of warm + real |
| Week 3 | 30-50 emails/day | Can start cold outreach |
| Week 4+ | 50-100 emails/day | Full scale per inbox |

**Important:** These limits are PER EMAIL ADDRESS. With 3 domains × 2 addresses = 6 inboxes = 300-600 emails/day at scale.

---

## Part 5: Outreach Sequence

### Sequence Structure

| Day | Email | Subject Line Style |
|-----|-------|-------------------|
| Day 1 | Initial outreach | Observation + Question |
| Day 3 | Bump | "Floating this up" |
| Day 7 | New angle | Different value prop |
| Day 14 | Breakup | "Closing the loop" |

### A/B Test Plan

Test these variables (one at a time):

1. **Subject lines** - Observation vs. Question vs. Pain point
2. **Opening line** - Compliment vs. Observation vs. Direct
3. **CTA** - "15 min chat?" vs. "Worth a look?" vs. "Open to sharing?"
4. **Length** - 50 words vs. 100 words

### Metrics to Track

| Metric | Target | Red Flag |
|--------|--------|----------|
| Open rate | 50%+ | < 30% (subject line or deliverability issue) |
| Reply rate | 5-15% | < 3% (message not resonating) |
| Positive reply rate | 2-5% | < 1% (wrong ICP or offer) |
| Bounce rate | < 3% | > 5% (bad data, stop sending) |

---

## Part 6: Tools Stack

| Purpose | Tool | Cost |
|---------|------|------|
| Lead data | Apollo.io | $49-99/mo |
| Email warming | Instantly.ai | $37/mo |
| Sending at scale | Instantly.ai or Smartlead | $37-99/mo |
| CRM / Tracking | HubSpot Free or Notion | Free |
| Email verification | NeverBounce or ZeroBounce | $0.008/email |

**Total cost to start:** ~$100-150/mo

---

## Part 7: Daily/Weekly Workflow

### Daily (15 min)

- [ ] Check replies, respond within 2 hours
- [ ] Log positive replies in CRM
- [ ] Check bounce rate, pause if > 5%

### Weekly (1 hour)

- [ ] Review metrics (open rate, reply rate)
- [ ] Adjust subject lines if open rate < 40%
- [ ] Adjust messaging if reply rate < 5%
- [ ] Pull fresh leads if running low
- [ ] Add positive conversations to "warm" list

### Monthly

- [ ] Analyze what's working, double down
- [ ] Retire underperforming sequences
- [ ] Refresh lead lists (new funding, new hires)
- [ ] Review ICP - still accurate?

---

## Compliance & Best Practices

### Do's

- ✅ Include physical address in email footer
- ✅ Include unsubscribe link
- ✅ Honor unsubscribe requests immediately
- ✅ Only email business addresses
- ✅ Provide value, not just pitches

### Don'ts

- ❌ Buy sketchy email lists
- ❌ Send more than 100/day per inbox (until warmed)
- ❌ Ignore bounce rates
- ❌ Email personal addresses (gmail, yahoo)
- ❌ Lie about why you're reaching out

---

## Quick Start Checklist

### This Week (Before API)

- [ ] Buy 2-3 sending domains
- [ ] Set up Google Workspace on each
- [ ] Configure SPF, DKIM, DMARC
- [ ] Sign up for Instantly.ai
- [ ] Start warming (takes 2-3 weeks)

### When You Get Apollo API

- [ ] Run test search with ICP filters
- [ ] Pull sample of 100 leads, review quality
- [ ] Refine filters based on sample
- [ ] Pull full lead list (1000-5000)
- [ ] Verify emails with NeverBounce
- [ ] Score and tier the leads
- [ ] Load Tier 1 into Instantly
- [ ] Start sending!

---

## Expected Results

Conservative estimates with good execution:

| Metric | Number |
|--------|--------|
| Leads pulled | 2,000 |
| Valid emails | 1,600 (80%) |
| Emails sent | 1,600 |
| Opens | 800 (50%) |
| Replies | 80-160 (5-10%) |
| Positive replies | 30-50 (2-3%) |
| Calls booked | 15-25 |
| Pilots started | 3-5 |

**Timeline:** 4-6 weeks from start to first pilots
