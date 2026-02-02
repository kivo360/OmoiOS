# OmoiOS Landing Pages

Standalone Next.js 15 landing pages for OmoiOS, deployable to Vercel.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Visit: http://localhost:3000
```

## Build & Deploy

```bash
# Build for production
npm run build

# Start production server
npm start
```

### Vercel Deployment

This project is configured for Vercel deployment:

1. Connect your Git repository to Vercel
2. Import the `landing-pages` directory
3. Vercel will automatically detect Next.js and configure deployment
4. Deploy on push to main branch

## Project Structure

```
landing-pages/
├── app/
│   ├── layout.tsx          # Root layout with SEO metadata
│   ├── page.tsx            # Main landing page
│   └── globals.css         # Global styles with Tailwind theme
├── components/
│   ├── marketing/           # Marketing sections (Hero, Features, Pricing, etc.)
│   │   ├── FloatingNavbar.tsx
│   │   ├── sections/       # Individual section components
│   │   └── index.ts       # Export barrel
│   └── ui/                # ShadCN UI components
│       ├── announcement.tsx
│       ├── badge.tsx
│       └── skeleton.tsx
├── lib/
│   └── utils.ts           # Utility functions (cn() for class merging)
├── public/
│   ├── fonts/             # Montserrat fonts
│   ├── screenshots/       # Product screenshots
│   ├── *.png, *.svg     # Favicons, icons, logo
│   └── site.webmanifest   # PWA manifest
└── package.json          # Dependencies
```

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **UI**: ShadCN UI (Radix UI + Tailwind CSS)
- **Styling**: Tailwind CSS v4
- **Icons**: Lucide React
- **Animations**: Framer Motion
- **Particles**: @tsparticles

## Environment Variables

Create `.env.local`:

```env
NEXT_PUBLIC_SITE_URL=https://omoios.dev
```

## Landing Page Sections

1. **Announcement Banner** - Sticky promo banner at top
2. **MarketingNavbar** - Floating navigation
3. **HeroSection** - Main CTA and value proposition
4. **PainPointsSection** - Problem statement
5. **LogoCloudSection** - Social proof
6. **WorkflowSection** - How it works
7. **ProductShowcaseSection** - Feature screenshots
8. **FeaturesSection** - Features bento grid
9. **NightShiftSection** - Overnight automation
10. **StatsSection** - Metrics and social proof
11. **PricingSection** - Pricing plans
12. **FAQSection** - Common questions
13. **WaitlistCTASection** - Final CTA
14. **FooterSection** - Links and info

## Scripts

```bash
npm run dev       # Start dev server (port 3000)
npm run build     # Build for production
npm run start     # Start production server
npm run lint      # Run ESLint
```

## Customization

### Theme Colors

Edit `app/globals.css` to customize:
- `--landing-accent` - Primary accent color
- `--landing-bg` - Background color
- `--landing-text` - Text color

### Content

Edit `app/page.tsx` to change landing page content, or modify individual section components in `components/marketing/sections/`.

## Original Source

This landing page is extracted from the main OmoiOS frontend (`frontend/`) and can be deployed independently as a standalone marketing site.
