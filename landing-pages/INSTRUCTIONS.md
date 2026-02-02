# OpenClaw Landing Page Setup Instructions

## Context

You are setting up a standalone Next.js 16 landing page for OpenClaw - an autonomous bot deployment service. The landing page showcases:

1. **Autonomous bot deployment** - Users don't have to configure anything themselves
2. **Proactive interval timers (Cron jobs)** - Bots act on schedules without prompts
3. **Excellent configurations** - Multi-agent, multi-channel setups
4. **Consulting services** - Expert help to solve real problems

## Project Location

The landing page code is in: `landing-pages/`

## What Needs to Be Done

### 1. Fix Build Issues

The current build fails because marketing components from the main frontend reference missing dependencies. You need to either:

**Option A: Copy missing components from frontend/**
- Copy all UI components from `frontend/components/ui/` to `landing-pages/components/ui/`
- Copy landing components from `frontend/components/landing/` to `landing-pages/components/landing/`

**Option B: Create simplified standalone versions**
- Remove the OmoiOS-specific sections that have missing dependencies
- Keep only the OpenClaw-specific sections which are self-contained

### 2. Fix OpenClaw Layout

The `landing-pages/app/openclaw/layout.tsx` has incorrect import paths:
- Change `import "./globals.css"` to `import "../globals.css"`
- Ensure `openclaw.css` exists at `landing-pages/app/openclaw/openclaw.css`

### 3. OpenClaw Components Location

OpenClaw-specific components are at:
```
landing-pages/components/openclaw/
├── index.ts                    # Barrel export
└── sections/
    ├── HeroSection.tsx         # Hero with cron example
    ├── FeaturesSection.tsx     # 6 key features
    ├── CronSection.tsx         # Proactive interval timers
    ├── ConfigSection.tsx       # Configuration showcase
    └── ConsultingSection.tsx   # Services + pricing
```

### 4. Run Build Test

After fixes, test with:
```bash
cd landing-pages
npm install
npm run build
```

### 5. Key Features to Highlight

**OpenClaw Capabilities:**
- Multi-channel: WhatsApp, Telegram, Discord, Slack, Signal, iMessage, Google Chat, Microsoft Teams
- Cron jobs: Morning briefs, daily check-ins, weekly analysis, one-time reminders
- Multi-agent: Run multiple isolated agents simultaneously
- Skills platform: Extensible with ClawHub community skills
- Companion apps: macOS, iOS, Android with Voice Wake and Talk Mode
- Security: DM pair codes, allowlists, sandbox isolation

**Consulting Services (suggested pricing):**
- Personal setup & onboarding: $299+ (2-3 hours)
- Workflow automation design: $199+ (1-2 hours)
- Multi-channel configuration: $149+ per platform
- 24/7 monitoring & support: $99/month
- Security hardening: $199+ (1-2 hours)
- Performance optimization: $149+ (1-2 hours)

### 6. Tech Stack

- Next.js 16 (App Router)
- Tailwind CSS v4
- Framer Motion for animations
- Lucide React for icons
- TypeScript

### 7. Deployment

Ready for Vercel deployment:
1. Push to Git repository
2. Connect to Vercel
3. Vercel auto-detects Next.js
4. Deploy automatically on push to main

## Quick Commands

```bash
# Install dependencies
cd landing-pages && npm install

# Run dev server
npm run dev
# Visit: http://localhost:3000/openclaw

# Build for production
npm run build

# Start production server
npm start
```

## Files Created

- `landing-pages/app/openclaw/page.tsx` - Main OpenClaw landing page
- `landing-pages/app/openclaw/layout.tsx` - OpenClaw-specific metadata/SEO
- `landing-pages/app/openclaw/openclaw.css` - OpenClaw branding colors
- `landing-pages/components/openclaw/` - All OpenClaw section components

## Notes

- All content must be in English
- Landing page focuses on the value proposition: "Deploy autonomous bots without lifting a finger"
- Emphasize proactive automation with interval timers
- Include consulting call-to-action for custom deployments
