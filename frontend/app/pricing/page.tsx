import { Metadata } from "next"
import { Check, Zap, Crown, Users, Building2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import Link from "next/link"

export const metadata: Metadata = {
  title: "Pricing - OmoiOS | Autonomous Engineering Platform",
  description:
    "Simple, transparent pricing for OmoiOS. Start free, scale as you grow. Pro at $50/month, Team at $150/month, or bring your own API keys for $19/month.",
  keywords: [
    "OmoiOS pricing",
    "AI coding tool pricing",
    "autonomous engineering pricing",
    "AI agent pricing",
    "Devin alternative pricing",
  ],
  openGraph: {
    title: "OmoiOS Pricing - Autonomous Engineering Platform",
    description:
      "Start free with 5 workflows/month. Pro $50/mo, Team $150/mo, or BYO keys at $19/mo.",
    url: "https://omoios.dev/pricing",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "OmoiOS Pricing",
    description:
      "Start free with 5 workflows/month. Pro $50/mo, Team $150/mo, or BYO keys at $19/mo.",
  },
  alternates: {
    canonical: "https://omoios.dev/pricing",
  },
}

// Structured data for SEO (JSON-LD)
const structuredData = {
  "@context": "https://schema.org",
  "@type": "Product",
  name: "OmoiOS",
  description:
    "Autonomous engineering platform that turns feature requests into shipped code using AI agents.",
  brand: {
    "@type": "Brand",
    name: "OmoiOS",
  },
  offers: [
    {
      "@type": "Offer",
      name: "Starter",
      price: "0",
      priceCurrency: "USD",
      priceValidUntil: "2026-12-31",
      availability: "https://schema.org/InStock",
      description: "1 agent, 5 workflows/month, community support",
      url: "https://omoios.dev/register",
    },
    {
      "@type": "Offer",
      name: "Pro",
      price: "50",
      priceCurrency: "USD",
      priceValidUntil: "2026-12-31",
      availability: "https://schema.org/InStock",
      description: "5 agents, 100 workflows/month, priority support, BYO API keys",
      url: "https://omoios.dev/register?plan=pro",
    },
    {
      "@type": "Offer",
      name: "Team",
      price: "150",
      priceCurrency: "USD",
      priceValidUntil: "2026-12-31",
      availability: "https://schema.org/InStock",
      description:
        "10 agents, 500 workflows/month, dedicated support, team collaboration",
      url: "https://omoios.dev/register?plan=team",
    },
    {
      "@type": "Offer",
      name: "BYO Platform",
      price: "19",
      priceCurrency: "USD",
      priceValidUntil: "2026-12-31",
      availability: "https://schema.org/InStock",
      description:
        "5 agents, unlimited workflows (user pays LLM), BYO API keys",
      url: "https://omoios.dev/register?plan=byo",
    },
    {
      "@type": "Offer",
      name: "Lifetime",
      price: "299",
      priceCurrency: "USD",
      priceValidUntil: "2026-12-31",
      availability: "https://schema.org/InStock",
      description:
        "5 agents, 50 workflows/month, one-time payment, no recurring charges",
      url: "https://omoios.dev/register?plan=lifetime",
    },
  ],
}

interface PricingTier {
  name: string
  price: number | string
  period: string
  description: string
  features: string[]
  cta: string
  popular?: boolean
  href: string
  icon: React.ReactNode
}

const pricingTiers: PricingTier[] = [
  {
    name: "Starter",
    price: 0,
    period: "/month",
    description: "Try autonomous engineering",
    icon: <Zap className="h-6 w-6" />,
    features: [
      "1 concurrent agent",
      "5 workflows per month",
      "2 GB storage",
      "Community support",
    ],
    cta: "Start Free",
    href: "/register",
  },
  {
    name: "Pro",
    price: 50,
    period: "/month",
    description: "Ship faster with parallel agents",
    icon: <Crown className="h-6 w-6" />,
    features: [
      "5 concurrent agents",
      "100 workflows per month",
      "50 GB storage",
      "Bring your own API keys",
      "Priority support",
      "Advanced analytics",
      "GitHub integration",
    ],
    cta: "Get Pro",
    popular: true,
    href: "/register?plan=pro",
  },
  {
    name: "Team",
    price: 150,
    period: "/month",
    description: "Scale your engineering output",
    icon: <Users className="h-6 w-6" />,
    features: [
      "10 concurrent agents",
      "500 workflows per month",
      "500 GB storage",
      "Bring your own API keys",
      "Team collaboration",
      "Role-based access control",
      "Dedicated support",
      "Custom integrations",
    ],
    cta: "Get Team",
    href: "/register?plan=team",
  },
]

export default function PricingPage() {
  return (
    <>
      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />

      <main className="min-h-screen bg-white">
        {/* Header */}
        <header className="border-b">
          <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            <Link href="/" className="text-xl font-bold">
              OmoiOS
            </Link>
            <nav className="flex items-center gap-6">
              <Link href="/docs" className="text-sm text-muted-foreground hover:text-foreground">
                Docs
              </Link>
              <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground">
                Blog
              </Link>
              <Link href="/pricing" className="text-sm font-medium">
                Pricing
              </Link>
              <Button asChild size="sm">
                <Link href="/register">Get Started</Link>
              </Button>
            </nav>
          </div>
        </header>

        {/* Hero */}
        <section className="py-16 md:py-24">
          <div className="container mx-auto px-4 text-center">
            <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
              Simple, Transparent Pricing
            </h1>
            <p className="mt-4 text-xl text-muted-foreground max-w-2xl mx-auto">
              Start free, scale as you grow. No hidden fees. Cancel anytime.
            </p>
          </div>
        </section>

        {/* Pricing Cards */}
        <section className="pb-16">
          <div className="container mx-auto px-4">
            <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-3">
              {pricingTiers.map((tier) => (
                <Card
                  key={tier.name}
                  className={cn(
                    "relative flex flex-col",
                    tier.popular && "border-primary shadow-lg ring-2 ring-primary/20"
                  )}
                >
                  {tier.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <Badge className="bg-primary text-primary-foreground">
                        Most Popular
                      </Badge>
                    </div>
                  )}

                  <CardHeader className={cn(tier.popular && "pt-8")}>
                    <div className="flex items-center gap-3 mb-2">
                      <div className="p-2 rounded-lg bg-muted">{tier.icon}</div>
                      <CardTitle className="text-xl">{tier.name}</CardTitle>
                    </div>
                    <CardDescription>{tier.description}</CardDescription>
                  </CardHeader>

                  <CardContent className="flex-1">
                    <div className="mb-6">
                      <span className="text-4xl font-bold">
                        {typeof tier.price === "number" ? `$${tier.price}` : tier.price}
                      </span>
                      <span className="text-muted-foreground">{tier.period}</span>
                    </div>

                    <ul className="space-y-3">
                      {tier.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-3">
                          <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
                          <span className="text-sm">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>

                  <CardFooter>
                    <Button
                      className="w-full"
                      variant={tier.popular ? "default" : "outline"}
                      asChild
                    >
                      <Link href={tier.href}>{tier.cta}</Link>
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Special Plans Section */}
        <section id="special-plans" className="py-16 bg-muted/30">
          <div className="container mx-auto px-4">
            <div className="max-w-4xl mx-auto space-y-8">
              {/* BYO Platform */}
              <Card className="p-8">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-lg bg-primary/10">
                      <Zap className="h-8 w-8 text-primary" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold">BYO Platform</h2>
                      <p className="text-muted-foreground mt-1">
                        Bring your own LLM API keys — unlimited workflows at the lowest price
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-bold">$19</p>
                    <p className="text-muted-foreground">/month</p>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-6 mt-8">
                  <div>
                    <ul className="space-y-2">
                      {[
                        "Unlimited workflows (you pay LLM costs)",
                        "5 concurrent agents",
                        "50 GB storage",
                        "Bring your own API keys",
                        "Community support",
                      ].map((feature) => (
                        <li key={feature} className="flex items-center gap-2 text-sm">
                          <Check className="h-4 w-4 text-primary" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="flex flex-col justify-center">
                    <p className="text-muted-foreground mb-4">
                      Already have an Anthropic or OpenAI API key? Get unlimited workflows for just $19/month.
                    </p>
                    <Button size="lg" asChild>
                      <Link href="/register?plan=byo">Get BYO Platform</Link>
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Lifetime Deal */}
              <Card className="p-8 border-primary/20">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-lg bg-primary/10">
                      <Crown className="h-8 w-8 text-primary" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold">Lifetime Deal</h2>
                      <p className="text-muted-foreground mt-1">
                        One-time payment — never pay again
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-bold">$299</p>
                    <p className="text-muted-foreground">one-time</p>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-6 mt-8">
                  <div>
                    <ul className="space-y-2">
                      {[
                        "50 workflows per month",
                        "5 concurrent agents",
                        "50 GB storage",
                        "Bring your own API keys",
                        "No recurring charges ever",
                        "Founding member badge",
                      ].map((feature) => (
                        <li key={feature} className="flex items-center gap-2 text-sm">
                          <Check className="h-4 w-4 text-primary" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="flex flex-col justify-center">
                    <p className="text-muted-foreground mb-4">
                      Lock in lifetime access at our founding price. Limited availability.
                    </p>
                    <Button size="lg" asChild>
                      <Link href="/register?plan=lifetime">Claim Lifetime Access</Link>
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Enterprise */}
              <Card className="p-8">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-lg bg-primary/10">
                      <Building2 className="h-8 w-8 text-primary" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold">Enterprise</h2>
                      <p className="text-muted-foreground mt-1">
                        For organizations that need maximum power and flexibility
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-bold">Custom</p>
                    <p className="text-muted-foreground">pricing</p>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-6 mt-8">
                  <div>
                    <h3 className="font-semibold mb-3">Everything in Team, plus:</h3>
                    <ul className="space-y-2">
                      {[
                        "Unlimited concurrent agents",
                        "Unlimited workflows",
                        "Unlimited storage",
                        "Dedicated infrastructure",
                        "Custom SLAs (99.9% uptime)",
                        "On-premise deployment option",
                        "Dedicated success manager",
                        "Training & onboarding",
                      ].map((feature) => (
                        <li key={feature} className="flex items-center gap-2 text-sm">
                          <Check className="h-4 w-4 text-primary" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="flex flex-col justify-center">
                    <p className="text-muted-foreground mb-4">
                      Get a custom quote based on your team size and requirements.
                    </p>
                    <Button size="lg" asChild>
                      <a href="mailto:enterprise@omoios.dev">Talk to Sales</a>
                    </Button>
                    <p className="text-xs text-muted-foreground mt-2">
                      Typically responds within 24 hours
                    </p>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </section>

        {/* FAQ Section for SEO */}
        <section className="py-16">
          <div className="container mx-auto px-4 max-w-3xl">
            <h2 className="text-2xl font-bold text-center mb-8">
              Frequently Asked Questions
            </h2>
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold">What counts as a workflow?</h3>
                <p className="text-muted-foreground mt-1">
                  A workflow is a complete feature spec that goes through the full
                  OmoiOS pipeline: Requirements → Design → Tasks → Execution. Each
                  spec you submit counts as one workflow.
                </p>
              </div>
              <div>
                <h3 className="font-semibold">Can I bring my own API keys?</h3>
                <p className="text-muted-foreground mt-1">
                  Yes! Pro, Team, and Enterprise plans support Bring Your Own Keys
                  (BYO). Connect your Anthropic, OpenAI, or other LLM provider keys
                  to use your own API credits.
                </p>
              </div>
              <div>
                <h3 className="font-semibold">What happens if I exceed my workflow limit?</h3>
                <p className="text-muted-foreground mt-1">
                  Your workflows will queue until the next billing cycle, or you can
                  upgrade your plan. The BYO Platform tier offers unlimited workflows
                  for just $19/month when you bring your own API keys.
                </p>
              </div>
              <div>
                <h3 className="font-semibold">Is there a free trial?</h3>
                <p className="text-muted-foreground mt-1">
                  The Starter plan is free forever with 5 workflows per month. For
                  Pro and Team plans, we offer a 14-day money-back guarantee.
                </p>
              </div>
              <div>
                <h3 className="font-semibold">How does OmoiOS compare to Devin?</h3>
                <p className="text-muted-foreground mt-1">
                  OmoiOS is spec-driven with full visibility into what agents are
                  doing. You approve the plan, see the dependency graph, and every
                  task traces back to requirements. Devin is $500/seat; OmoiOS Pro
                  starts at $50/month with 5 parallel agents.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16 bg-primary text-primary-foreground">
          <div className="container mx-auto px-4 text-center">
            <h2 className="text-3xl font-bold">Ready to ship faster?</h2>
            <p className="mt-2 text-primary-foreground/80 max-w-xl mx-auto">
              Start free and see your first autonomous PR in minutes.
            </p>
            <Button size="lg" variant="secondary" className="mt-6" asChild>
              <Link href="/register">Get Started Free</Link>
            </Button>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t py-8">
          <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
            <p>© 2026 OmoiOS. All rights reserved.</p>
            <div className="mt-2 flex justify-center gap-4">
              <Link href="/docs" className="hover:underline">
                Documentation
              </Link>
              <Link href="/blog" className="hover:underline">
                Blog
              </Link>
              <a href="mailto:hello@omoios.dev" className="hover:underline">
                Contact
              </a>
            </div>
          </div>
        </footer>
      </main>
    </>
  )
}
