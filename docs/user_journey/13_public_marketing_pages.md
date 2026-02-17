# 13 Public & Marketing Pages

**Part of**: [User Journey Documentation](./README.md)

---

## Overview

Public pages are accessible without authentication and serve as the acquisition funnel: visitors discover OmoiOS, evaluate pricing, explore documentation, read the blog, and convert to users. This document covers the visitor-to-user journey through these pages.

---

## 13.1 Landing Page — Visitor Conversion

```
Visitor arrives at omoios.dev (via search, referral, social, ad):
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Announcement Banner                                         │
│  "Free for Limited Time — Try our AI Prompt Generator →"    │
├─────────────────────────────────────────────────────────────┤
│  Floating Navbar                                             │
│  OmoiOS  [Why] [Product] [Features] [Pricing] [FAQ]        │
│                                    [Sign In] [Get Started]  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Hero: "Start a feature before bed. Wake up to a PR."       │
│  [Get Started Free]                                          │
│                                                              │
│  ↓ Scroll                                                    │
│  Pain Points → Logo Cloud → How It Works → Product Demo     │
│  → Features Grid → Night Shift → Stats → Pricing → FAQ     │
│  → Waitlist CTA → Footer                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Conversion Paths

```
Landing Page
   │
   ├── [Get Started Free] → /register
   ├── [Sign In] → /login
   ├── Nav [Pricing] → scroll to #pricing section
   ├── Pricing section CTA → /register?plan=<tier>
   ├── Announcement banner → prompt.omoios.dev (AI Prompt Generator)
   └── Footer links → /blog, /docs, GitHub, social media
```

### Section Purpose

| Section | Goal |
|---------|------|
| Announcement | Drive traffic to free AI Prompt Generator |
| Hero | Communicate core value prop in one sentence |
| Pain Points | Show you understand their problems |
| Logo Cloud | Social proof / trust signals |
| How It Works | Show simplicity (3 steps) |
| Product Showcase | Visual evidence of the product |
| Features Bento | Highlight capabilities |
| Night Shift | Emotional "set it and forget it" story |
| Stats | Quantitative proof |
| Pricing | Transparent tier comparison |
| FAQ | Address objections |
| Waitlist CTA | Final conversion push |

---

## 13.2 Pricing Evaluation

```
Visitor navigates to /pricing (from landing page or direct URL):
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Pricing — OmoiOS | Autonomous Engineering Platform          │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Starter  │ │ Pro      │ │ Team     │ │ Enterprise│      │
│  │ Free     │ │ $50/mo   │ │ $150/mo  │ │ Custom    │      │
│  │          │ │          │ │          │ │           │      │
│  │ 1 agent  │ │ 5 agents │ │ 25 agents│ │ Unlimited │      │
│  │ 5 flows  │ │ 100 flows│ │ 500 flows│ │ Unlimited │      │
│  │ Community│ │ Priority │ │ SSO/RBAC │ │ SLA       │      │
│  │          │ │ BYO keys │ │ BYO keys │ │ Dedicated │      │
│  │          │ │          │ │          │ │           │      │
│  │[Start    │ │[Start    │ │[Start    │ │[Contact   │      │
│  │ Free]    │ │ Pro]     │ │ Team]    │ │ Sales]    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                              │
│  BYO Keys: $19/month — Bring your own API keys              │
└─────────────────────────────────────────────────────────────┘
   ↓
Decision paths:
├── [Start Free] → /register
├── [Start Pro] → /register?plan=pro
├── [Start Team] → /register?plan=team
└── [Contact Sales] → mailto:sales@omoios.com
```

### SEO
- Server-rendered with custom metadata
- JSON-LD structured data (Product schema with Offer entries)
- Canonical URL, Open Graph, Twitter Cards
- Indexed by search engines for "OmoiOS pricing" queries

---

## 13.3 Blog Discovery

```
Visitor arrives at /blog (from search, social, or landing page):
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Blog | OmoiOS                                               │
│                                                              │
│  Featured Posts:                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  [Hero featured post with image]                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Categories:                                                 │
│  [📢 Announcements] [📖 Tutorials] [✨ Updates] [💡 Tips]   │
│                                                              │
│  All Posts (grid):                                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │  Post card   │ │  Post card   │ │  Post card   │       │
│  └──────────────┘ └──────────────┘ └──────────────┘       │
└─────────────────────────────────────────────────────────────┘

Navigation paths:
├── Click post → /blog/:slug (full article)
├── Click category → /blog/category/:category (filtered)
├── Click tag → /blog/tag/:tag (filtered)
└── RSS feed → /feed.xml
```

### Content Categories
| Category | Icon | Purpose |
|----------|------|---------|
| Announcements | Megaphone | Product launches, updates |
| Tutorials | BookOpen | How-to guides, walkthroughs |
| Updates | Sparkles | Feature updates, improvements |
| Tips | Lightbulb | Best practices, workflow tips |

### Blog → Conversion Path
```
Search/social → Blog post → Reads value → CTA at bottom → /register
```

---

## 13.4 Documentation Exploration

```
Visitor/user arrives at /docs (from landing page, blog, or direct):
   ↓
┌─────────────────────────────────────────────────────────────┐
│  ┌──────────┐ ┌────────────────────────────────────────────┐│
│  │ Sidebar  │ │  Docs Page                                 ││
│  │          │ │                                            ││
│  │ Getting  │ │  Title                                     ││
│  │ Started  │ │  Description                               ││
│  │          │ │                                            ││
│  │ Guides   │ │  [MDX Content with Mermaid diagrams]       ││
│  │          │ │                                            ││
│  │ API      │ │  Table of Contents (right side)            ││
│  │ Ref      │ │                                            ││
│  └──────────┘ └────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘

Technology:
- Fumadocs UI (DocsPage, DocsBody, DocsTitle, DocsDescription)
- MDX content with custom Mermaid diagram support
- Static generation via generateStaticParams
- Sidebar navigation tree from content source
```

### Docs → Conversion Path
```
Search → Docs page → Understands product → Sign up → /register
```

---

## 13.5 Showcase Sharing

```
User completes a feature with OmoiOS:
   ↓
System generates shareable showcase link:
   /showcase/:token
   ↓
User shares link on social media / in Slack / via email:
   ↓
Recipient opens link (no auth required):
   ↓
┌─────────────────────────────────────────────────────────────┐
│  OmoiOS Showcase                                             │
│  "Add Stripe Payments"                                       │
│  Automated payment integration for checkout                  │
│  Project: acme-web                                           │
│                                                              │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │  12       │ │  28       │ │  26       │ │  94%      │  │
│  │  Require- │ │  Tasks    │ │  Completed│ │  Coverage │  │
│  │  ments    │ │           │ │           │ │           │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│                                                              │
│  🔀 Pull Request #42                                ↗       │
│                                                              │
│  [Try OmoiOS]    [⭐ Star on GitHub]                         │
│                                                              │
│  Built with OmoiOS — spec-driven AI agents                   │
└─────────────────────────────────────────────────────────────┘
```

### Showcase → Conversion Path
```
Share link → Recipient views stats → Clicks "Try OmoiOS" → /register
                                  → Clicks PR link → GitHub PR (proof of work)
                                  → Clicks Star → GitHub repo
```

### SEO & Social
- Dynamic Open Graph metadata (title, description from showcase data)
- Twitter Card support
- Server-rendered with 60s revalidation
- View count tracked via API

---

## 13.6 OAuth Callback Flow

```
User clicks "Sign in with GitHub" (from /login or /onboarding):
   ↓
Redirected to GitHub OAuth (grant permissions):
   ↓
GitHub redirects back to /callback with tokens:
   ↓
┌─ Login flow:
│   ↓
│   /callback?access_token=...&refresh_token=...
│   ↓
│   1. Store tokens
│   2. Fetch user info (GET /api/v1/auth/me)
│   3. Check onboarding status
│   4. Set onboarding cookie
│   5. Redirect to /command
│
├─ Connect flow (linking GitHub during onboarding):
│   ↓
│   /callback?connect=true&connected=true&username=kivo360
│   ↓
│   1. Invalidate OAuth queries
│   2. Redirect to /onboarding?step=repo&github_connected=true
│
└─ Error flow:
    ↓
    /callback?error=access_denied
    ↓
    1. Show error message
    2. Auto-redirect to /login?error=access_denied (3s delay)
```

---

## Public Pages Journey Summary

```
                    ┌──────────────┐
                    │  Search /    │
                    │  Social /    │
                    │  Referral    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
              ┌─────│   Landing    │─────┐
              │     │   Page (/)   │     │
              │     └──────┬───────┘     │
              │            │             │
       ┌──────▼──┐  ┌─────▼─────┐  ┌───▼────┐
       │  Blog   │  │  Pricing  │  │  Docs  │
       │ /blog   │  │ /pricing  │  │ /docs  │
       └────┬────┘  └─────┬─────┘  └───┬────┘
            │             │             │
            └──────┬──────┴──────┬──────┘
                   │             │
            ┌──────▼──────┐  ┌──▼──────────┐
            │  Register   │  │  Showcase   │
            │ /register   │  │ /showcase/* │
            └──────┬──────┘  └─────────────┘
                   │
            ┌──────▼──────┐
            │  Onboarding │
            │ /onboarding │
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │  Command    │
            │  Center     │
            └─────────────┘
```

---

**Related**: See [page_flows/16_public_pages.md](../page_flows/16_public_pages.md) for detailed page-level flow documentation.
