"use client"

import { motion } from "framer-motion"
import { Check, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface PricingTier {
  name: string
  price: number | string
  period: string
  description: string
  features: string[]
  cta: string
  popular?: boolean
  href: string
}

const pricingTiers: PricingTier[] = [
  {
    name: "Free",
    price: 0,
    period: "/month",
    description: "Try autonomous engineering",
    features: [
      "1 concurrent agent",
      "5 workflows per month",
      "1 project",
      "Community support",
      "Work queues when limit hit",
    ],
    cta: "Start Free",
    href: "/register",
  },
  {
    name: "Pro",
    price: 50,
    period: "/month",
    description: "Ship faster with parallel agents",
    features: [
      "5 concurrent agents",
      "100 workflows per month",
      "5 projects",
      "Bring your own API keys",
      "Priority support",
      "Advanced analytics",
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
    features: [
      "10 concurrent agents",
      "500 workflows per month",
      "Unlimited projects",
      "Bring your own API keys",
      "Team collaboration",
      "Role-based access",
      "Dedicated support",
    ],
    cta: "Get Team",
    href: "/register?plan=team",
  },
]

interface PricingSectionProps {
  className?: string
  id?: string
}

export function PricingSection({ className, id }: PricingSectionProps) {
  return (
    <section id={id} className={cn("bg-landing-bg py-20 md:py-32", className)}>
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-16 max-w-2xl text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            Simple, Transparent Pricing
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            Start free, scale as you grow. No hidden fees.
          </p>
        </motion.div>

        {/* Pricing Cards */}
        <div className="mx-auto grid max-w-5xl gap-8 md:grid-cols-3">
          {pricingTiers.map((tier, index) => (
            <motion.div
              key={tier.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
            >
              <Card
                className={cn(
                  "relative flex h-full flex-col border-landing-border bg-white transition-all duration-300",
                  tier.popular
                    ? "border-landing-accent shadow-lg ring-2 ring-landing-accent/20"
                    : "hover:shadow-md"
                )}
              >
                {/* Popular Badge */}
                {tier.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-landing-accent text-white hover:bg-landing-accent/90">
                      <Zap className="mr-1 h-3 w-3" />
                      Most Popular
                    </Badge>
                  </div>
                )}

                <CardHeader className={cn(tier.popular && "pt-8")}>
                  <CardTitle className="text-xl text-landing-text">
                    {tier.name}
                  </CardTitle>
                  <CardDescription className="text-landing-text-muted">
                    {tier.description}
                  </CardDescription>
                </CardHeader>

                <CardContent className="flex-1">
                  {/* Price */}
                  <div className="mb-6">
                    <span className="text-4xl font-bold text-landing-text">
                      {typeof tier.price === "number" ? `$${tier.price}` : tier.price}
                    </span>
                    <span className="text-landing-text-muted">{tier.period}</span>
                  </div>

                  {/* Features */}
                  <ul className="space-y-3">
                    {tier.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-3">
                        <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-landing-accent" />
                        <span className="text-sm text-landing-text">{feature}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>

                <CardFooter>
                  <Button
                    className={cn(
                      "w-full",
                      tier.popular
                        ? "bg-landing-accent text-white hover:bg-landing-accent/90"
                        : "border-landing-border bg-white text-landing-text hover:bg-landing-bg-muted"
                    )}
                    variant={tier.popular ? "default" : "outline"}
                    asChild
                  >
                    <a href={tier.href}>{tier.cta}</a>
                  </Button>
                </CardFooter>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Enterprise CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mt-12 max-w-2xl text-center"
        >
          <p className="text-landing-text-muted">
            Need more?{" "}
            <a
              href="mailto:hello@omoios.dev"
              className="font-medium text-landing-accent underline-offset-4 hover:underline"
            >
              Contact us for Enterprise pricing
            </a>
          </p>
        </motion.div>
      </div>
    </section>
  )
}
