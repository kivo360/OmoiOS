# Public Pages

**Part of**: [Page Flow Documentation](./README.md)

---

## Overview

Public pages are accessible without authentication and serve as the marketing, documentation, and content layer of OmoiOS. These include the landing page, pricing, blog, documentation site, and shareable showcase pages.

---

## Flow 61: Landing Page

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: / (Landing Page — unauthenticated)                   │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  🎉 Free for Limited Time — Try our AI Prompt Generator│ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Floating Navigation                                   │ │
│  │  OmoiOS  [Why] [Product] [Features] [Pricing] [FAQ]   │ │
│  │                              [Sign In] [Get Started]   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Sections (scrollable):                                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Hero Section                                          │ │
│  │  "Start a feature before bed. Wake up to a PR."        │ │
│  │  [Get Started Free]                                    │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Pain Points — Why teams struggle                      │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Logo Cloud — Trusted by / Built with                  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  How It Works — Workflow Steps                         │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Product Showcase — Screenshots / Demo                 │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Features — Bento Grid Layout                          │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Night Shift Section                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Stats Section — Numbers / Social Proof                │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Pricing Section — Tier Comparison                     │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  FAQ Section — Expandable Questions                    │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Waitlist CTA Section                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Footer — Links, Legal, Social                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/` (unauthenticated visitors)

### Purpose
Marketing landing page that converts visitors into users. Showcases the product value proposition, features, pricing, and social proof.

### Sections
| Section | Purpose |
|---------|---------|
| Announcement Banner | Promotes free AI Prompt Generator (links to prompt.omoios.dev) |
| MarketingNavbar | Floating navigation with section anchors + auth links |
| HeroSection | Main value proposition + CTA |
| PainPointsSection | Problem statement (why teams struggle) |
| LogoCloudSection | Social proof / partner logos |
| WorkflowSection | How it works step-by-step |
| ProductShowcaseSection | Screenshots / interactive demo |
| FeaturesSection | Bento grid of key features |
| NightShiftSection | Overnight automation story |
| StatsSection | Numbers and metrics |
| PricingSection | Tier comparison |
| FAQSection | Common questions |
| WaitlistCTASection | Final conversion CTA |
| FooterSection | Links, legal, social |

### User Actions
- **Navigate sections**: Click nav anchors (#why, #product, #features, #pricing, #faq)
- **Sign in / Sign up**: Navigate to `/login` or `/register`
- **View pricing**: Scroll to pricing section or click nav anchor
- **External links**: AI Prompt Generator (prompt.omoios.dev)

### Auth Redirect
Authenticated users hitting `/` are redirected to `/command` via the `(dashboard)` route group.

### Components
- `LandingPage` — Client component orchestrating all marketing sections
- `MarketingNavbar`, `HeroSection`, `PainPointsSection`, `LogoCloudSection`, `FeaturesSection`, `WorkflowSection`, `ProductShowcaseSection`, `NightShiftSection`, `StatsSection`, `PricingSection`, `FAQSection`, `WaitlistCTASection`, `FooterSection`

---

## Flow 62: Pricing Page

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /pricing                                             │
│                                                             │
│  Pricing — OmoiOS | Autonomous Engineering Platform         │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Starter  │ │ Pro      │ │ Team     │ │ Enterprise│      │
│  │ Free     │ │ $50/mo   │ │ $150/mo  │ │ Custom    │      │
│  │          │ │          │ │          │ │           │      │
│  │ 1 agent  │ │ 5 agents │ │ 25 agents│ │ Unlimited │      │
│  │ 5 flows  │ │ 100 flows│ │ 500 flows│ │ Unlimited │      │
│  │          │ │ Priority │ │ SSO, RBAC│ │ SLA       │      │
│  │          │ │ BYO keys │ │ BYO keys │ │ Dedicated │      │
│  │          │ │          │ │          │ │           │      │
│  │[Get      │ │[Start    │ │[Start    │ │[Contact   │      │
│  │ Started] │ │ Pro]     │ │ Team]    │ │ Sales]    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  Also: BYO Keys at $19/month                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/pricing`

### Purpose
Dedicated pricing page with SEO metadata and structured data (JSON-LD). Server-rendered for search indexing.

### User Actions
- **Compare tiers**: View feature comparison across Starter, Pro, Team, Enterprise
- **Sign up for tier**: Click CTA to navigate to `/register?plan=<tier>`
- **Contact sales**: Enterprise tier links to sales email

### SEO
- Custom Open Graph and Twitter Card metadata
- JSON-LD structured data (`Product` schema with `Offer` entries)
- Canonical URL: `https://omoios.dev/pricing`

---

## Flow 63: Blog

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /blog                                                │
│                                                             │
│  Blog | OmoiOS                                              │
│                                                             │
│  Featured Posts:                                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  [Featured post card with image]                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Categories: [Announcements] [Tutorials] [Updates] [Tips]   │
│                                                             │
│  All Posts:                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │  Post card   │ │  Post card   │ │  Post card   │       │
│  │  Title       │ │  Title       │ │  Title       │       │
│  │  Excerpt     │ │  Excerpt     │ │  Excerpt     │       │
│  │  Date        │ │  Date        │ │  Date        │       │
│  └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Routes
| Route | Purpose |
|-------|---------|
| `/blog` | Blog index with featured posts and all posts |
| `/blog/[slug]` | Individual blog post |
| `/blog/category/[category]` | Posts filtered by category |
| `/blog/tag/[tag]` | Posts filtered by tag |

### Purpose
Content marketing blog with categories (Announcements, Tutorials, Updates, Tips), featured posts, and SEO metadata.

### User Actions
- **Browse posts**: Scroll through post cards
- **Filter by category**: Click category badges
- **Filter by tag**: Click tag links
- **Read post**: Click post card to open full article
- **RSS feed**: Available at `/feed.xml`

### Components
- Blog uses static generation from MDX content via `@/lib/blog`
- `BlogLayout` — Blog-specific layout
- Category icon mapping (Megaphone, BookOpen, Sparkles, Lightbulb)

---

## Flow 64: Documentation Site

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /docs/[[...slug]]                                    │
│                                                             │
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
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/docs/[[...slug]]` (catch-all optional segment)

### Purpose
Fumadocs-powered documentation site with sidebar navigation, table of contents, and MDX content including Mermaid diagram support.

### User Actions
- **Browse docs**: Navigate sidebar tree structure
- **Read documentation**: View MDX-rendered content with diagrams
- **Search docs**: (if Fumadocs search is configured)

### Technology
- **Fumadocs UI**: `DocsPage`, `DocsBody`, `DocsTitle`, `DocsDescription` components
- **MDX**: Extended with custom `Mermaid` component for diagram rendering
- **Static generation**: `generateStaticParams` pre-renders all doc pages

---

## Flow 65: Showcase Page

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /showcase/:token                                     │
│                                                             │
│  OmoiOS Showcase                                            │
│  Add Stripe Payments                                        │
│  Automated payment integration for the checkout flow        │
│  Project: acme-web                                          │
│                                                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │  12       │ │  28       │ │  26       │ │  94%      │  │
│  │  Require- │ │  Tasks    │ │  Completed│ │  Coverage │  │
│  │  ments    │ │           │ │           │ │           │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  🔀 Pull Request #42                           ↗      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  [Try OmoiOS]    [⭐ Star on GitHub]                        │
│                                                             │
│  Built with OmoiOS — spec-driven AI agents                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/showcase/[token]`

### Purpose
Public shareable page showing the results of an OmoiOS-automated feature. Designed for social sharing with Open Graph and Twitter Card metadata.

### User Actions
- **View stats**: Requirements, tasks, completion count, test coverage
- **Visit PR**: Click through to the GitHub pull request
- **Sign up**: "Try OmoiOS" CTA links to `/register`
- **Star repo**: Link to GitHub repository

### API Endpoints
- `GET /api/v1/public/showcase/:token` — Fetch showcase data (server-side, revalidated every 60s)

### SEO
- Dynamic `generateMetadata` with title, description, Open Graph, Twitter Card
- Designed for link sharing on social media

---

## Flow 66: Auth Callback

### Route
`/callback`

### Purpose
OAuth callback handler that processes tokens from GitHub/OAuth providers and redirects to the appropriate destination.

### Flows
| Scenario | Behavior |
|----------|----------|
| Login callback | Receives `access_token` + `refresh_token` → stores tokens → fetches user → checks onboarding → redirects to `/command` |
| Connect callback | GitHub connected during onboarding → invalidates queries → redirects to `/onboarding?step=repo` |
| Error callback | OAuth error → shows error message → redirects to `/login?error=<error>` |

### States
| State | Display |
|-------|---------|
| Loading | Spinner + "Completing sign in..." |
| Success | Green checkmark + "Sign in successful!" → auto-redirect |
| Error | Red X + error message → auto-redirect to login |

---

## Public Pages Route Summary

```
Public (no auth required):
├── /                              Landing page (marketing)
├── /pricing                       Pricing tiers (SEO-optimized)
├── /blog                          Blog index
│   ├── /blog/[slug]               Individual blog post
│   ├── /blog/category/[category]  Posts by category
│   └── /blog/tag/[tag]            Posts by tag
├── /docs/[[...slug]]              Documentation site (Fumadocs)
└── /showcase/[token]              Shareable feature showcase

Auth (public layout):
├── /login                         Email login
├── /register                      Email registration
├── /callback                      OAuth callback handler
├── /forgot-password               Password reset request
├── /reset-password                Password reset form
└── /verify-email                  Email verification
```

---

**Next**: See [17_activity_timeline.md](./17_activity_timeline.md) for real-time activity timeline.
