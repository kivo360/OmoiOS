# OpenClaw Landing Page

Standalone Next.js 16 landing page for OpenClaw autonomous bot deployment service, deployable to Vercel.

## Quick Start

```bash
# Navigate to landing-pages directory
cd landing-pages

# Install dependencies
npm install

# Start development server
npm run dev

# Visit: http://localhost:3000
# OpenClaw page: http://localhost:3000/openclaw
```

## Overview

OpenClaw is a **personal AI assistant** that you run on your own devices. This landing page showcases:

- **Autonomous bot deployment** without users needing to do the work themselves
- **Proactive interval timers** (Cron jobs) for bots to act on your behalf
- **Excellent configurations** for multi-agent, multi-channel setups
- **Consulting services** to solve real problems with expert configuration

## Key Features Highlighted

### 1. Multi-Channel Support
Connects to all major messaging platforms:
- WhatsApp, Telegram, Discord, Slack
- Google Chat, Signal, iMessage
- Microsoft Teams, Matrix, WebChat

### 2. Proactive Automation (Cron Jobs)
- **Morning briefs** - Summarize overnight updates
- **Daily check-ins** - Proactive status updates
- **Weekly analysis** - Deep project reviews
- **One-time reminders** - Important deadlines
- **Recurring tasks** - Automated workflows

### 3. Excellent Configurations
- **Multi-agent system** - Run multiple isolated agents
- **Per-channel settings** - Granular control for each platform
- **Security & access** - DM pair codes, allowlists, sandboxing
- **Skills platform** - Extensible with ClawHub community skills
- **Model configuration** - Anthropic Claude, OpenAI GPT-4, custom providers
- **Companion apps** - macOS, iOS, Android with Voice Wake & Talk Mode

### 4. Consulting Services
- **Personal setup & onboarding** - Complete installation (2-3 hours, $299+)
- **Workflow automation design** - Custom cron jobs (1-2 hours, $199+)
- **Multi-channel configuration** - Platform setup ($149+ per platform)
- **24/7 monitoring & support** - Ongoing support ($99/month)
- **Security hardening** - Access control setup (1-2 hours, $199+)
- **Performance optimization** - Tuning and optimization (1-2 hours, $149+)

## Page Structure

```
app/openclaw/
├── layout.tsx              # Root layout with OpenClaw-specific metadata
├── page.tsx                # Main OpenClaw landing page
├── globals.css             # Base styles
└── openclaw.css            # OpenClaw-specific branding colors

components/openclaw/
├── sections/
│   ├── HeroSection.tsx          # Hero with CTA and cron example
│   ├── FeaturesSection.tsx        # 6 key features (bento grid)
│   ├── CronSection.tsx           # Proactive interval timers showcase
│   ├── ConfigSection.tsx          # Excellent configurations display
│   └── ConsultingSection.tsx     # Consulting services with pricing
└── index.ts                 # Barrel export
```

## Tech Stack

- **Framework**: Next.js 16 (App Router) - Latest version
- **UI**: ShadCN UI (Radix UI + Tailwind CSS)
- **Styling**: Tailwind CSS v4 with OpenClaw teal/teal theme
- **Icons**: Lucide React
- **Animations**: Framer Motion

## OpenClaw Theme Colors

Custom teal/teal branding colors defined in `app/openclaw/openclaw.css`:

```css
:root {
  --openclaw-accent: 173 100% 30%;     /* #00BFA5 - Teal */
  --openclaw-accent-light: 173 100% 40%;  /* #66FFCC - Lighter teal */
  --openclaw-accent-dark: 173 100% 20%;    /* #00664D - Darker teal */
  --openclaw-success: 142 71% 45%;          /* #22C55E - Green */
}
```

## Environment Variables

No special environment variables required. Uses base URL from parent app.

## Deployment

### Vercel Deployment

OpenClaw page is ready for Vercel deployment:

1. Push `landing-pages` directory to your Git repository
2. Connect repository to Vercel
3. Vercel auto-detects Next.js 16
4. Deploy automatically on push to main
5. Access at: `https://your-domain.vercel.app/openclaw`

### Access Points

- **Main landing**: `https://your-domain.vercel.app/`
- **OpenClaw page**: `https://your-domain.vercel.app/openclaw`

## Customization

### Modify Content

Edit section components in `components/openclaw/sections/`:
- `HeroSection.tsx` - Main CTA and value prop
- `FeaturesSection.tsx` - Feature cards (6 items)
- `CronSection.tsx` - Cron job examples (4 examples)
- `ConfigSection.tsx` - Configuration categories (6 items)
- `ConsultingSection.tsx` - Services and pricing (6 services)

### Update Cron Examples

Edit `CronSection.tsx` to add or modify cron job examples:

```typescript
const cronJobs = [
  {
    icon: Calendar,
    title: "Morning Brief",
    description: "Your description",
    schedule: "0 7 * * *",
    timezone: "America/Los_Angeles",
    type: "Recurring",
  },
  // Add more examples...
]
```

### Update Consulting Services

Edit `ConsultingSection.tsx` to modify services:

```typescript
const services = [
  {
    icon: Users,
    title: "Service Name",
    description: "Description of service",
    duration: "Time estimate",
    price: "Pricing",
  },
  // Add more services...
]
```

## Scripts

```bash
npm run dev       # Start dev server (port 3000)
npm run build     # Build for production
npm run start     # Start production server
npm run lint      # Run ESLint
```

## Related Resources

- **OpenClaw GitHub**: [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)
- **Official Docs**: [docs.openclaw.ai](https://docs.openclaw.ai)
- **ClawHub Skills**: [clawhub.com](https://clawhub.com)
- **Discord Community**: [discord.gg/clawd](https://discord.gg/clawd)

## Design Principles

1. **Problem-First**: Emphasize solving real user problems with automation
2. **Proactive Focus**: Highlight interval timers and autonomous actions
3. **Configuration Excellence**: Show granular control and customization options
4. **Consulting Value**: Demonstrate expertise in setup and optimization
5. **Clean Aesthetics**: Use landing page palette with OpenClaw teal accents
6. **Mobile-First**: Responsive design with breakpoints (md: for tablets+)
7. **Animation-Driven**: Framer Motion for engaging scroll reveals
